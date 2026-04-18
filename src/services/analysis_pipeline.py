"""Core LLM-native analysis pipeline orchestrator."""
import json
import re
import sqlite3
import uuid
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

from src.prompts.templates import (
    ISSUE_ANALYSIS_SYSTEM,
    issue_analysis_user,
    PATTERN_DETECTION_SYSTEM,
    pattern_detection_user,
    SCARCITY_PRIORITIZATION_SYSTEM,
    scarcity_prioritization_user,
    EVIDENCE_GROUNDING_SYSTEM,
    evidence_grounding_user,
)
from src.services.web_grounding import WebGrounding

logger = logging.getLogger(__name__)
LEGACY_SIGNAL_FINGERPRINT = "__legacy_signal_fingerprint_missing__"


def extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM response text.

    Handles: raw JSON, ```json blocks, ```blocks, partial wrapping.
    """
    if isinstance(text, dict):
        return text

    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Extract from markdown code blocks
    patterns = [
        r"```json\s*\n?(.*?)```",
        r"```\s*\n?(.*?)```",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                continue

    # Find first { ... } or [ ... ] block
    for open_ch, close_ch in [("{", "}"), ("[", "]")]:
        start = text.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_ch:
                depth += 1
            elif text[i] == close_ch:
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break

    return {}


class AnalysisPipeline:
    """Three-stage LLM analysis: analyze → cluster → prioritize."""

    def __init__(self, conn: sqlite3.Connection, adapter, config: Optional[dict] = None):
        self.conn = conn
        self.adapter = adapter
        self.config = config or {}
        self.grounder = self._build_grounder()
        self._ensure_tables()

    def _build_grounder(self):
        if self.config.get("grounder") is not None:
            return self.config["grounder"]

        grounding_cfg = self.config.get("grounding", {})
        if not isinstance(grounding_cfg, dict):
            grounding_cfg = {}

        repo = grounding_cfg.get("repo", self.config.get("grounding_repo"))
        timeout = grounding_cfg.get("timeout", self.config.get("grounding_timeout", 10))
        enabled = grounding_cfg.get(
            "enabled",
            self.config.get("grounding_enabled", repo is not None),
        )
        if not enabled:
            return None

        return WebGrounding(repo=repo, timeout=timeout)

    def _ensure_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS issue_analyses (
                issue_number INTEGER PRIMARY KEY,
                title TEXT,
                severity_tier TEXT,
                affected_scope TEXT,
                failure_mode TEXT,
                blast_radius TEXT,
                system_layer TEXT,
                p_happy_if_fixed REAL,
                p_failure_cascade REAL,
                is_symptom INTEGER,
                suspected_root TEXT,
                confidence REAL,
                raw_response TEXT,
                analyzed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS root_cause_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_cause TEXT NOT NULL,
                mechanism TEXT,
                severity TEXT,
                confidence REAL,
                issue_numbers TEXT,
                run_id TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS prioritization_runs (
                id TEXT PRIMARY KEY,
                budget INTEGER,
                chosen TEXT,
                deferred TEXT,
                systemic_insight TEXT,
                run_at TEXT
            );
        """)
        self._ensure_columns(
            "issue_analyses",
            {
                "system_layer": "TEXT",
                "signal_id": "TEXT",
                "signal_type": "TEXT",
                "source": "TEXT",
                "metadata": "TEXT",
                "signal_fingerprint": "TEXT",
            },
        )
        self._ensure_columns(
            "root_cause_clusters",
            {
                "signal_ids": "TEXT",
                "original_severity": "TEXT",
                "original_confidence": "REAL",
                "grounding_query": "TEXT",
                "grounding_evidence": "TEXT",
                "supporting_evidence": "TEXT",
                "grounding_confidence_change": "TEXT",
                "grounded_at": "TEXT",
            },
        )
        self._ensure_columns(
            "prioritization_runs",
            {
                "systemic_insight": "TEXT",
                "predictions_json": "TEXT",
                "outcomes_json": "TEXT",
                "evaluation_json": "TEXT",
            },
        )
        issue_columns = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in self.conn.execute("PRAGMA table_info(issue_analyses)")
        }
        if "architectural_layer" in issue_columns and "system_layer" in issue_columns:
            self.conn.execute(
                """UPDATE issue_analyses
                   SET system_layer = architectural_layer
                   WHERE (system_layer IS NULL OR system_layer = '')
                     AND architectural_layer IS NOT NULL
                     AND architectural_layer != ''"""
            )
        prio_columns = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in self.conn.execute("PRAGMA table_info(prioritization_runs)")
        }
        if "architectural_insight" in prio_columns and "systemic_insight" in prio_columns:
            self.conn.execute(
                """UPDATE prioritization_runs
                   SET systemic_insight = architectural_insight
                   WHERE (systemic_insight IS NULL OR systemic_insight = '')
                     AND architectural_insight IS NOT NULL
                     AND architectural_insight != ''"""
            )
        self.conn.execute(
            "UPDATE issue_analyses SET signal_id = CAST(issue_number AS TEXT) WHERE signal_id IS NULL"
        )
        self.conn.execute(
            "UPDATE issue_analyses SET signal_type = 'issue' WHERE signal_type IS NULL OR signal_type = ''"
        )
        self.conn.execute(
            "UPDATE issue_analyses SET source = '' WHERE source IS NULL"
        )
        self.conn.execute(
            "UPDATE issue_analyses SET metadata = '{}' WHERE metadata IS NULL OR metadata = ''"
        )
        self.conn.execute(
            """UPDATE issue_analyses
               SET signal_fingerprint = ?
               WHERE signal_id IS NOT NULL
                 AND (signal_fingerprint IS NULL OR signal_fingerprint = '')""",
            (LEGACY_SIGNAL_FINGERPRINT,),
        )
        try:
            self.conn.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_issue_analyses_signal_id
                   ON issue_analyses(signal_id)"""
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Existing issue_analyses rows contain duplicate signal_id values; reanalyze or deduplicate them before continuing."
            ) from exc
        self.conn.commit()

    def _ensure_columns(self, table_name: str, columns: dict[str, str]):
        existing = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table_name})")
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                self.conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )
        self.conn.commit()

    # ── Stage 1 ─────────────────────────────────────────────────────

    def analyze_issues(self, issues: list[dict], batch_size: int = 5) -> list[dict]:
        """Backward-compatible wrapper for issue-shaped inputs."""
        return self.analyze_signals(issues, batch_size=batch_size, legacy_issue_mode=True)

    def analyze_signals(
        self, signals: list[dict], batch_size: int = 5, legacy_issue_mode: bool = False
    ) -> list[dict]:
        """Analyze each normalized signal individually via LLM, batched for efficiency."""
        results = []
        normalized_signals = self._ensure_unique_signal_ids([
            self._normalize_to_signal(signal, index + 1, legacy_issue_mode=legacy_issue_mode)
            for index, signal in enumerate(signals)
        ])
        for i in range(0, len(normalized_signals), batch_size):
            batch = normalized_signals[i : i + batch_size]
            for signal in batch:
                analyzed = self._analyze_single_issue(signal)
                if analyzed:
                    results.append(analyzed)
        return results

    def _normalize_labels(self, raw_labels) -> list[str]:
        if raw_labels is None:
            return []
        if isinstance(raw_labels, list):
            return [str(label).strip() for label in raw_labels if str(label).strip()]
        if isinstance(raw_labels, str):
            return [raw_labels.strip()] if raw_labels.strip() else []
        return [str(raw_labels).strip()]

    def _is_numeric_identifier(self, value) -> bool:
        return bool(re.fullmatch(r"-?\d+", str(value).strip()))

    def _first_present_value(self, record: dict, keys: list[str]):
        for key in keys:
            if key in record and record[key] is not None:
                return record[key]
        return None

    def _normalize_source(self, value) -> str:
        return str(value).strip().lower()

    def _ensure_unique_signal_ids(self, signals: list[dict]) -> list[dict]:
        unique_signals = []
        seen_fingerprints = {}
        for signal in signals:
            signal_id = signal["signal_id"]
            fingerprint = self._signal_fingerprint(signal)
            if signal_id in seen_fingerprints:
                if seen_fingerprints[signal_id] != fingerprint:
                    raise ValueError(
                        f"Ambiguous signal_id '{signal_id}'. Provide a stable source or canonical signal_id."
                    )
                continue
            seen_fingerprints[signal_id] = fingerprint
            unique_signals.append(signal)
        return unique_signals

    def _is_legacy_issue_record(self, record: dict) -> bool:
        return (
            record.get("number") is not None
            and not any(
                key in record and record[key] is not None
                for key in ("signal_id", "id", "source", "repo", "origin")
            )
        )

    def _signal_fingerprint(self, signal: dict) -> str:
        labels = sorted(
            {str(label).strip() for label in signal.get("labels", []) if str(label).strip()},
            key=str.casefold,
        )
        return json.dumps(
            {
                "signal_type": signal.get("signal_type"),
                "source": signal.get("source"),
                "title": signal.get("title"),
                "body": signal.get("body"),
                "labels": labels,
                "metadata": signal.get("metadata", {}),
            },
            sort_keys=True,
        )

    def _normalize_to_signal(
        self, record: dict, default_index: int, legacy_issue_mode: bool = False
    ) -> dict:
        labels = self._normalize_labels(record.get("labels") or record.get("tags"))
        metadata = record.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        source = self._normalize_source(record.get("source") or record.get("repo") or record.get("origin") or "")
        raw_number = record.get("number")
        raw_signal_id = self._first_present_value(record, ["signal_id", "id"])
        if raw_signal_id is None and raw_number is None and not source and not legacy_issue_mode:
            raise ValueError(
                "Generalized signals must provide signal_id/id or a canonical source-scoped identifier."
            )
        if (
            raw_number is not None
            and raw_signal_id is None
            and not source
            and not legacy_issue_mode
        ):
            raise ValueError(
                "Source-less numeric 'number' inputs must use analyze_issues() or include a canonical source/signal_id."
            )
        if raw_signal_id is None:
            raw_signal_id = raw_number if raw_number is not None else f"signal-{default_index}"
        if raw_signal_id is not None and self._is_numeric_identifier(raw_signal_id) and not source and (
            "signal_id" in record or "id" in record
        ):
            raise ValueError(
                "Numeric external signal identifiers require a source for stable canonicalization."
            )
        signal_id = str(raw_signal_id)
        if ":" in signal_id:
            namespace, remainder = signal_id.split(":", 1)
            canonical_namespace = self._normalize_source(namespace)
            signal_id = f"{canonical_namespace}:{remainder.strip()}"
            if source and source != canonical_namespace:
                raise ValueError(
                    f"Signal source '{source}' does not match namespaced signal_id '{signal_id}'."
                )
            source = source or canonical_namespace
        if source and ":" not in signal_id and self._is_numeric_identifier(signal_id):
            signal_id = f"{source}:{signal_id}"
        signal_type = str(
            record.get("signal_type")
            or record.get("source_type")
            or ("issue" if raw_signal_id == raw_number and raw_number is not None else "other")
        )
        title = (
            record.get("title")
            or record.get("summary")
            or record.get("headline")
            or f"Signal {signal_id}"
        )
        body = (
            record.get("body")
            or record.get("description")
            or record.get("text")
            or record.get("content")
            or ""
        )
        reference_number = raw_number
        if raw_number is None:
            number = self._stable_signal_number(signal_id)
        else:
            try:
                reference_number = int(raw_number)
            except (TypeError, ValueError):
                number = self._stable_signal_number(signal_id)
                reference_number = raw_number
            else:
                if signal_id == str(reference_number):
                    number = reference_number
                else:
                    number = self._stable_signal_number(signal_id)

        normalized = dict(record)
        normalized.update({
            "number": number,
            "reference_number": reference_number,
            "signal_id": signal_id,
            "signal_type": signal_type,
            "source": source,
            "title": title,
            "body": body,
            "labels": labels,
            "metadata": metadata,
        })
        return normalized

    def _stable_signal_number(self, signal_id: str) -> int:
        digest = hashlib.sha1(signal_id.encode("utf-8")).hexdigest()[:15]
        return -(int(digest, 16) + 1)

    def _signal_lookup(self, analyzed_issues: list[dict]) -> dict:
        return {
            issue.get("number"): issue.get("signal_id", str(issue.get("number")))
            for issue in analyzed_issues
        }

    def _analyze_single_issue(self, signal: dict, retries: int = 1) -> Optional[dict]:
        user_prompt = issue_analysis_user(signal)
        for attempt in range(retries + 1):
            try:
                if hasattr(self.adapter, "analyze"):
                    raw = self.adapter.analyze(ISSUE_ANALYSIS_SYSTEM, user_prompt)
                    parsed = raw if isinstance(raw, dict) else extract_json(str(raw))
                else:
                    raw = self.adapter.generate(user_prompt, system=ISSUE_ANALYSIS_SYSTEM, temperature=0.3)
                    parsed = extract_json(raw)

                if not parsed:
                    continue

                record = {
                    **parsed,
                    "number": signal.get("number"),
                    "signal_id": signal.get("signal_id"),
                    "signal_type": signal.get("signal_type"),
                    "source": signal.get("source", ""),
                    "title": signal.get("title", ""),
                    "labels": signal.get("labels", []),
                    "metadata": signal.get("metadata", {}),
                }
                self._store_issue_analysis(record, raw)
                return record
            except ValueError:
                raise
            except Exception as e:
                logger.warning("Issue %s analysis attempt %d failed: %s", signal.get("number"), attempt, e)

        # Fallback: minimal record
        fallback_record = {
            "number": signal.get("number"),
            "signal_id": signal.get("signal_id"),
            "signal_type": signal.get("signal_type"),
            "source": signal.get("source", ""),
            "title": signal.get("title", ""),
            "labels": signal.get("labels", []),
            "metadata": signal.get("metadata", {}),
            "severity_tier": "moderate",
            "affected_scope": "edge_case",
            "failure_mode_if_unfixed": "unknown",
            "blast_radius": "none",
            "system_layer": "unknown",
            "p_happy_if_fixed": 0.5,
            "p_failure_cascade_if_unfixed": 0.1,
            "is_symptom_of_deeper_issue": False,
            "suspected_root_category": "unknown",
            "confidence": 0.1,
        }
        self._store_issue_analysis(fallback_record, {"fallback": True, "signal_id": signal.get("signal_id")})
        return fallback_record

    def _store_issue_analysis(self, record: dict, raw_response):
        now = datetime.now(timezone.utc).isoformat()
        signal_fingerprint = self._signal_fingerprint(record)
        signal_id = record.get("signal_id")
        raw_response_text = json.dumps(raw_response) if not isinstance(raw_response, str) else raw_response
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            existing = self.conn.execute(
                """SELECT issue_number, signal_fingerprint
                   FROM issue_analyses
                   WHERE signal_id = ?""",
                (signal_id,),
            ).fetchone()
            if existing:
                existing_fingerprint = existing["signal_fingerprint"] if isinstance(existing, sqlite3.Row) else existing[1]
                if not existing_fingerprint or existing_fingerprint == LEGACY_SIGNAL_FINGERPRINT:
                    raise ValueError(
                        f"Legacy signal_id '{signal_id}' must be reanalyzed before updates."
                    )
                if existing_fingerprint != signal_fingerprint:
                    raise ValueError(
                        f"Conflicting content for signal_id '{signal_id}'."
                    )
                record["number"] = existing["issue_number"] if isinstance(existing, sqlite3.Row) else existing[0]
                self.conn.execute(
                    """UPDATE issue_analyses
                       SET title = ?, severity_tier = ?, affected_scope = ?, failure_mode = ?,
                           blast_radius = ?, system_layer = ?, p_happy_if_fixed = ?,
                           p_failure_cascade = ?, is_symptom = ?, suspected_root = ?,
                           confidence = ?, raw_response = ?, analyzed_at = ?, issue_number = ?,
                           signal_type = ?, source = ?, metadata = ?, signal_fingerprint = ?
                       WHERE signal_id = ?""",
                    (
                        record.get("title", ""),
                        record.get("severity_tier", "moderate"),
                        record.get("affected_scope", "edge_case"),
                        record.get("failure_mode_if_unfixed", ""),
                        record.get("blast_radius", "none"),
                        record.get("system_layer", "unknown"),
                        record.get("p_happy_if_fixed", 0.5),
                        record.get("p_failure_cascade_if_unfixed", 0.1),
                        1 if record.get("is_symptom_of_deeper_issue") else 0,
                        record.get("suspected_root_category", "unknown"),
                        record.get("confidence", 0.5),
                        raw_response_text,
                        now,
                        record.get("number"),
                        record.get("signal_type"),
                        record.get("source", ""),
                        json.dumps(record.get("metadata", {})),
                        signal_fingerprint,
                        signal_id,
                    ),
                )
            else:
                self.conn.execute(
                    """INSERT INTO issue_analyses
                       (issue_number, title, severity_tier, affected_scope, failure_mode,
                        blast_radius, system_layer, p_happy_if_fixed, p_failure_cascade,
                        is_symptom, suspected_root, confidence, raw_response, analyzed_at,
                        signal_id, signal_type, source, metadata, signal_fingerprint)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        record.get("number"),
                        record.get("title", ""),
                        record.get("severity_tier", "moderate"),
                        record.get("affected_scope", "edge_case"),
                        record.get("failure_mode_if_unfixed", ""),
                        record.get("blast_radius", "none"),
                        record.get("system_layer", "unknown"),
                        record.get("p_happy_if_fixed", 0.5),
                        record.get("p_failure_cascade_if_unfixed", 0.1),
                        1 if record.get("is_symptom_of_deeper_issue") else 0,
                        record.get("suspected_root_category", "unknown"),
                        record.get("confidence", 0.5),
                        raw_response_text,
                        now,
                        signal_id,
                        record.get("signal_type"),
                        record.get("source", ""),
                        json.dumps(record.get("metadata", {})),
                        signal_fingerprint,
                    ),
                )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ── Stage 2 ─────────────────────────────────────────────────────

    def detect_patterns(self, analyzed_issues: list[dict], batch_size: int = 30) -> dict:
        """Feed analyzed issues to LLM for root-cause clustering."""
        if len(analyzed_issues) <= batch_size:
            return self._detect_patterns_batch(analyzed_issues)

        # Merge clusters from batches
        all_clusters = []
        all_unclustered = []
        all_unclustered_signal_ids = []
        for i in range(0, len(analyzed_issues), batch_size):
            batch = analyzed_issues[i : i + batch_size]
            result = self._detect_patterns_batch(batch)
            all_clusters.extend(result.get("clusters", []))
            all_unclustered.extend(result.get("unclustered_issues", []))
            all_unclustered_signal_ids.extend(result.get("unclustered_signal_ids", []))

        merged = {
            "clusters": all_clusters,
            "unclustered_issues": all_unclustered,
            "unclustered_signal_ids": all_unclustered_signal_ids,
        }
        return merged

    def _detect_patterns_batch(self, issues: list[dict]) -> dict:
        user_prompt = pattern_detection_user(issues)
        signal_lookup = self._signal_lookup(issues)
        try:
            if hasattr(self.adapter, "analyze"):
                raw = self.adapter.analyze(PATTERN_DETECTION_SYSTEM, user_prompt)
                parsed = raw if isinstance(raw, dict) else extract_json(str(raw))
            else:
                raw = self.adapter.generate(user_prompt, system=PATTERN_DETECTION_SYSTEM, temperature=0.3)
                parsed = extract_json(raw)
        except Exception as e:
            logger.warning("Pattern detection failed: %s", e)
            parsed = {}

        if not parsed or "clusters" not in parsed:
            parsed = {"clusters": [], "unclustered_issues": [i.get("number") for i in issues]}

        for cluster in parsed.get("clusters", []):
            cluster["signal_ids"] = [
                signal_lookup.get(issue_number, str(issue_number))
                for issue_number in cluster.get("issue_numbers", [])
            ]
        parsed["unclustered_signal_ids"] = [
            signal_lookup.get(issue_number, str(issue_number))
            for issue_number in parsed.get("unclustered_issues", [])
        ]

        run_id = str(uuid.uuid4())[:8]
        for cluster in parsed.get("clusters", []):
            cluster["_run_id"] = run_id
        self._store_clusters(parsed, run_id)
        return parsed

    def _store_clusters(self, result: dict, run_id: str):
        now = datetime.now(timezone.utc).isoformat()
        for cluster in result.get("clusters", []):
            self.conn.execute(
                """INSERT INTO root_cause_clusters
                   (root_cause, mechanism, severity, confidence, issue_numbers, run_id, created_at,
                    signal_ids, original_severity, original_confidence, grounding_query, grounding_evidence,
                    supporting_evidence, grounding_confidence_change, grounded_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    cluster.get("root_cause", ""),
                    cluster.get("mechanism", ""),
                    cluster.get("severity_if_unaddressed", "moderate"),
                    cluster.get("confidence", 0.5),
                    json.dumps(cluster.get("issue_numbers", [])),
                    run_id,
                    now,
                    json.dumps(cluster.get("signal_ids", [])),
                    cluster.get("severity_if_unaddressed", "moderate"),
                    cluster.get("confidence", 0.5),
                    "",
                    json.dumps([]),
                    json.dumps([]),
                    "unchanged",
                    "",
                ),
            )
        self.conn.commit()

    def _build_grounding_query(self, cluster: dict) -> str:
        parts = [
            cluster.get("root_cause", ""),
            cluster.get("mechanism", ""),
        ]
        tags = cluster.get("signal_ids", [])[:3]
        if tags:
            parts.append(" ".join(str(tag) for tag in tags))
        return " ".join(part.strip() for part in parts if str(part).strip())

    def _ground_single_cluster(self, cluster: dict) -> dict:
        grounded = dict(cluster)
        grounding_query = self._build_grounding_query(cluster)
        evidence = self.grounder.search_evidence(grounding_query) if grounding_query else []
        grounded["grounding_query"] = grounding_query
        grounded["grounding_evidence"] = evidence
        grounded["original_severity"] = cluster.get(
            "original_severity",
            cluster.get("severity_if_unaddressed", "moderate"),
        )
        grounded["original_confidence"] = cluster.get(
            "original_confidence",
            cluster.get("confidence", 0.5),
        )
        grounded["supporting_evidence"] = cluster.get("supporting_evidence", [])
        grounded["grounding_confidence_change"] = cluster.get(
            "grounding_confidence_change",
            "unchanged",
        )
        grounded["grounded_at"] = datetime.now(timezone.utc).isoformat()

        if not evidence:
            return grounded

        user_prompt = evidence_grounding_user(cluster, evidence)
        try:
            if hasattr(self.adapter, "analyze"):
                raw = self.adapter.analyze(EVIDENCE_GROUNDING_SYSTEM, user_prompt)
                parsed = raw if isinstance(raw, dict) else extract_json(str(raw))
            else:
                raw = self.adapter.generate(
                    user_prompt,
                    system=EVIDENCE_GROUNDING_SYSTEM,
                    temperature=0.2,
                )
                parsed = extract_json(raw)
        except Exception as exc:
            logger.warning("Evidence grounding failed for %s: %s", cluster.get("root_cause", "?"), exc)
            parsed = {}

        if parsed:
            grounded["severity_if_unaddressed"] = parsed.get(
                "revised_severity",
                grounded.get("severity_if_unaddressed", "moderate"),
            )
            grounded["confidence"] = parsed.get(
                "new_confidence",
                grounded.get("confidence", 0.5),
            )
            grounded["supporting_evidence"] = parsed.get("supporting_evidence", [])
            grounded["grounding_confidence_change"] = parsed.get(
                "confidence_change",
                "unchanged",
            )

        return grounded

    def _update_grounded_cluster(self, cluster: dict):
        run_id = cluster.get("_run_id")
        if not run_id:
            return

        self.conn.execute(
            """UPDATE root_cause_clusters
               SET severity = ?,
                   confidence = ?,
                   signal_ids = ?,
                   original_severity = ?,
                   original_confidence = ?,
                   grounding_query = ?,
                   grounding_evidence = ?,
                   supporting_evidence = ?,
                   grounding_confidence_change = ?,
                   grounded_at = ?
               WHERE run_id = ? AND root_cause = ? AND issue_numbers = ?""",
            (
                cluster.get("severity_if_unaddressed", "moderate"),
                cluster.get("confidence", 0.5),
                json.dumps(cluster.get("signal_ids", [])),
                cluster.get("original_severity", cluster.get("severity_if_unaddressed", "moderate")),
                cluster.get("original_confidence", cluster.get("confidence", 0.5)),
                cluster.get("grounding_query", ""),
                json.dumps(cluster.get("grounding_evidence", [])),
                json.dumps(cluster.get("supporting_evidence", [])),
                cluster.get("grounding_confidence_change", "unchanged"),
                cluster.get("grounded_at", ""),
                run_id,
                cluster.get("root_cause", ""),
                json.dumps(cluster.get("issue_numbers", [])),
            ),
        )
        self.conn.commit()

    def ground_clusters_with_evidence(self, clusters: dict) -> dict:
        if not self.grounder or not clusters.get("clusters"):
            return clusters

        grounded_clusters = []
        for cluster in clusters.get("clusters", []):
            grounded = self._ground_single_cluster(cluster)
            grounded_clusters.append(grounded)
            self._update_grounded_cluster(grounded)

        grounded_result = dict(clusters)
        grounded_result["clusters"] = grounded_clusters
        grounded_result["grounded"] = True
        return grounded_result

    # ── Stage 3 ─────────────────────────────────────────────────────

    def prioritize_under_scarcity(
        self, clusters: dict, analyzed_issues: list[dict], budget: int = 5
    ) -> dict:
        """Scarcity-driven prioritization via LLM."""
        user_prompt = scarcity_prioritization_user(clusters, analyzed_issues, budget)
        signal_lookup = self._signal_lookup(analyzed_issues)
        try:
            if hasattr(self.adapter, "analyze"):
                raw = self.adapter.analyze(SCARCITY_PRIORITIZATION_SYSTEM, user_prompt)
                parsed = raw if isinstance(raw, dict) else extract_json(str(raw))
            else:
                raw = self.adapter.generate(
                    user_prompt, system=SCARCITY_PRIORITIZATION_SYSTEM, temperature=0.3
                )
                parsed = extract_json(raw)
        except Exception as e:
            logger.warning("Prioritization failed: %s", e)
            parsed = {}

        if not parsed or "chosen" not in parsed:
            parsed = {
                "chosen": [],
                "deferred": [],
                "systemic_insight": "Unable to determine — LLM call failed.",
            }

        for choice in parsed.get("chosen", []):
            choice["signal_ids_resolved"] = [
                signal_lookup.get(issue_number, str(issue_number))
                for issue_number in choice.get("issues_resolved", [])
            ]

        parsed["predictions"] = self._build_prediction_records(parsed, clusters)
        parsed["outcomes"] = parsed.get("outcomes", [])

        self._store_prioritization(parsed, budget)
        return parsed

    def _build_prediction_records(self, prioritization: dict, clusters: dict) -> list[dict]:
        cluster_lookup = {
            cluster.get("root_cause"): cluster
            for cluster in clusters.get("clusters", [])
        }
        predictions = []
        for choice in prioritization.get("chosen", []):
            cluster = cluster_lookup.get(choice.get("target"), {})
            predictions.append(
                {
                    "target": choice.get("target", ""),
                    "signal_ids": choice.get("signal_ids_resolved", []),
                    "issue_numbers": choice.get("issues_resolved", []),
                    "tier": choice.get("tier", cluster.get("severity_if_unaddressed", "moderate")),
                    "confidence": cluster.get("confidence", 0.5),
                    "rationale": choice.get("why", ""),
                    "predicted_outcome": choice.get(
                        "predicted_outcome",
                        choice.get(
                            "blast_radius_prevented",
                            f"Mitigates {len(choice.get('signal_ids_resolved', []))} related signals",
                        ),
                    ),
                    "supporting_evidence": cluster.get("supporting_evidence", []),
                    "grounding_query": cluster.get("grounding_query", ""),
                }
            )
        return predictions

    def _store_prioritization(self, result: dict, budget: int):
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO prioritization_runs
               (id, budget, chosen, deferred, systemic_insight, run_at, predictions_json, outcomes_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                run_id,
                budget,
                json.dumps(result.get("chosen", [])),
                json.dumps(result.get("deferred", [])),
                result.get("systemic_insight", ""),
                now,
                json.dumps(result.get("predictions", [])),
                json.dumps(result.get("outcomes", [])),
            ),
        )
        self.conn.commit()
        result["run_id"] = run_id

    def record_outcomes(self, run_id: str, outcomes: list[dict]):
        self.conn.execute(
            "UPDATE prioritization_runs SET outcomes_json = ? WHERE id = ?",
            (json.dumps(outcomes), run_id),
        )
        self.conn.commit()

    def _prediction_matches_outcome(self, prediction: dict, outcome: dict) -> bool:
        predicted_target = str(prediction.get("target", "")).strip().lower()
        exact_target = str(outcome.get("target", "")).strip().lower()
        if exact_target and predicted_target == exact_target:
            return True

        contains = outcome.get("target_contains", [])
        if isinstance(contains, str):
            contains = [contains]
        contains = [str(term).strip().lower() for term in contains if str(term).strip()]
        if contains:
            return all(term in predicted_target for term in contains)

        return False

    def score_predictions(self, run_id: str, observed_outcomes: list[dict]) -> dict:
        row = self.conn.execute(
            "SELECT predictions_json FROM prioritization_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Prioritization run '{run_id}' not found.")

        predictions = json.loads(row["predictions_json"] or "[]")
        observed_outcomes = observed_outcomes or []
        self.record_outcomes(run_id, observed_outcomes)

        matched_positive_outcomes = set()
        hits = 0
        scored_predictions = []
        for prediction in predictions:
            matched_outcome = None
            matched_index = None
            for index, outcome in enumerate(observed_outcomes):
                if not self._prediction_matches_outcome(prediction, outcome):
                    continue
                if outcome.get("observed", True):
                    if index in matched_positive_outcomes:
                        continue
                    matched_outcome = outcome
                    matched_index = index
                    break
                if matched_outcome is None:
                    matched_outcome = outcome
                    matched_index = index

            observed = bool(matched_outcome and matched_outcome.get("observed", True))
            counted_hit = observed and matched_index not in matched_positive_outcomes
            if counted_hit and matched_index is not None:
                matched_positive_outcomes.add(matched_index)
                hits += 1

            scored_predictions.append(
                {
                    **prediction,
                    "outcome_matched": counted_hit,
                    "observed_outcome": matched_outcome,
                }
            )

        observed_positive_count = sum(
            1 for outcome in observed_outcomes if outcome.get("observed", True)
        )
        misses = len(predictions) - hits
        evaluation = {
            "run_id": run_id,
            "hit_count": hits,
            "miss_count": misses,
            "observed_positive_count": observed_positive_count,
            "precision": round(hits / len(predictions), 3) if predictions else 0.0,
            "recall": round(hits / observed_positive_count, 3) if observed_positive_count else 0.0,
            "scored_predictions": scored_predictions,
            "unmatched_outcomes": [
                outcome
                for index, outcome in enumerate(observed_outcomes)
                if outcome.get("observed", True) and index not in matched_positive_outcomes
            ],
        }
        self.conn.execute(
            "UPDATE prioritization_runs SET evaluation_json = ? WHERE id = ?",
            (json.dumps(evaluation), run_id),
        )
        self.conn.commit()
        return evaluation

    # ── Full Pipeline ───────────────────────────────────────────────

    def run_full_pipeline(self, issues: list[dict], budget: int = 5) -> dict:
        """Run all stages end-to-end for issue-shaped or generalized signal inputs."""
        if issues and all(self._is_legacy_issue_record(issue) for issue in issues):
            analyzed = self.analyze_issues(issues)
        else:
            analyzed = self.analyze_signals(issues)
        clusters = self.detect_patterns(analyzed)
        grounded_clusters = self.ground_clusters_with_evidence(clusters)
        priorities = self.prioritize_under_scarcity(grounded_clusters, analyzed, budget)

        return {
            "analyzed_issues": analyzed,
            "clusters": grounded_clusters,
            "prioritization": priorities,
            "summary": {
                "total_issues": len(issues),
                "total_signals": len(issues),
                "analyzed": len(analyzed),
                "clusters_found": len(grounded_clusters.get("clusters", [])),
                "budget": budget,
                "chosen_count": len(priorities.get("chosen", [])),
            },
        }

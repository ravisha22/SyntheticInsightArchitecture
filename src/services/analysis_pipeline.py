"""Core LLM-native analysis pipeline orchestrator."""
import json
import re
import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from src.prompts.templates import (
    ISSUE_ANALYSIS_SYSTEM,
    issue_analysis_user,
    PATTERN_DETECTION_SYSTEM,
    pattern_detection_user,
    SCARCITY_PRIORITIZATION_SYSTEM,
    scarcity_prioritization_user,
)

logger = logging.getLogger(__name__)


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
        self._ensure_tables()

    def _ensure_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS issue_analyses (
                issue_number INTEGER PRIMARY KEY,
                title TEXT,
                severity_tier TEXT,
                affected_scope TEXT,
                failure_mode TEXT,
                blast_radius TEXT,
                architectural_layer TEXT,
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
                architectural_insight TEXT,
                run_at TEXT
            );
        """)

    # ── Stage 1 ─────────────────────────────────────────────────────

    def analyze_issues(self, issues: list[dict], batch_size: int = 5) -> list[dict]:
        """Analyze each issue individually via LLM, batched for efficiency."""
        results = []
        for i in range(0, len(issues), batch_size):
            batch = issues[i : i + batch_size]
            for issue in batch:
                analyzed = self._analyze_single_issue(issue)
                if analyzed:
                    results.append(analyzed)
        return results

    def _analyze_single_issue(self, issue: dict, retries: int = 1) -> Optional[dict]:
        user_prompt = issue_analysis_user(issue)
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
                    "number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "labels": issue.get("labels", []),
                    **parsed,
                }
                self._store_issue_analysis(record, raw)
                return record
            except Exception as e:
                logger.warning("Issue %s analysis attempt %d failed: %s", issue.get("number"), attempt, e)

        # Fallback: minimal record
        return {
            "number": issue.get("number"),
            "title": issue.get("title", ""),
            "labels": issue.get("labels", []),
            "severity_tier": "moderate",
            "affected_scope": "edge_case",
            "failure_mode_if_unfixed": "unknown",
            "blast_radius": "none",
            "architectural_layer": "unknown",
            "p_happy_if_fixed": 0.5,
            "p_failure_cascade_if_unfixed": 0.1,
            "is_symptom_of_deeper_issue": False,
            "suspected_root_category": "unknown",
            "confidence": 0.1,
        }

    def _store_issue_analysis(self, record: dict, raw_response):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT OR REPLACE INTO issue_analyses
               (issue_number, title, severity_tier, affected_scope, failure_mode,
                blast_radius, architectural_layer, p_happy_if_fixed, p_failure_cascade,
                is_symptom, suspected_root, confidence, raw_response, analyzed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record.get("number"),
                record.get("title", ""),
                record.get("severity_tier", "moderate"),
                record.get("affected_scope", "edge_case"),
                record.get("failure_mode_if_unfixed", ""),
                record.get("blast_radius", "none"),
                record.get("architectural_layer", "unknown"),
                record.get("p_happy_if_fixed", 0.5),
                record.get("p_failure_cascade_if_unfixed", 0.1),
                1 if record.get("is_symptom_of_deeper_issue") else 0,
                record.get("suspected_root_category", "unknown"),
                record.get("confidence", 0.5),
                json.dumps(raw_response) if not isinstance(raw_response, str) else raw_response,
                now,
            ),
        )
        self.conn.commit()

    # ── Stage 2 ─────────────────────────────────────────────────────

    def detect_patterns(self, analyzed_issues: list[dict], batch_size: int = 30) -> dict:
        """Feed analyzed issues to LLM for root-cause clustering."""
        if len(analyzed_issues) <= batch_size:
            return self._detect_patterns_batch(analyzed_issues)

        # Merge clusters from batches
        all_clusters = []
        all_unclustered = []
        for i in range(0, len(analyzed_issues), batch_size):
            batch = analyzed_issues[i : i + batch_size]
            result = self._detect_patterns_batch(batch)
            all_clusters.extend(result.get("clusters", []))
            all_unclustered.extend(result.get("unclustered_issues", []))

        merged = {"clusters": all_clusters, "unclustered_issues": all_unclustered}
        return merged

    def _detect_patterns_batch(self, issues: list[dict]) -> dict:
        user_prompt = pattern_detection_user(issues)
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

        run_id = str(uuid.uuid4())[:8]
        self._store_clusters(parsed, run_id)
        return parsed

    def _store_clusters(self, result: dict, run_id: str):
        now = datetime.now(timezone.utc).isoformat()
        for cluster in result.get("clusters", []):
            self.conn.execute(
                """INSERT INTO root_cause_clusters
                   (root_cause, mechanism, severity, confidence, issue_numbers, run_id, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    cluster.get("root_cause", ""),
                    cluster.get("mechanism", ""),
                    cluster.get("severity_if_unaddressed", "moderate"),
                    cluster.get("confidence", 0.5),
                    json.dumps(cluster.get("issue_numbers", [])),
                    run_id,
                    now,
                ),
            )
        self.conn.commit()

    # ── Stage 3 ─────────────────────────────────────────────────────

    def prioritize_under_scarcity(
        self, clusters: dict, analyzed_issues: list[dict], budget: int = 5
    ) -> dict:
        """Scarcity-driven prioritization via LLM."""
        user_prompt = scarcity_prioritization_user(clusters, analyzed_issues, budget)
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
                "architectural_insight": "Unable to determine — LLM call failed.",
            }

        self._store_prioritization(parsed, budget)
        return parsed

    def _store_prioritization(self, result: dict, budget: int):
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO prioritization_runs
               (id, budget, chosen, deferred, architectural_insight, run_at)
               VALUES (?,?,?,?,?,?)""",
            (
                run_id,
                budget,
                json.dumps(result.get("chosen", [])),
                json.dumps(result.get("deferred", [])),
                result.get("architectural_insight", ""),
                now,
            ),
        )
        self.conn.commit()

    # ── Full Pipeline ───────────────────────────────────────────────

    def run_full_pipeline(self, issues: list[dict], budget: int = 5) -> dict:
        """Run all stages end-to-end. Return final report."""
        analyzed = self.analyze_issues(issues)
        clusters = self.detect_patterns(analyzed)
        priorities = self.prioritize_under_scarcity(clusters, analyzed, budget)

        return {
            "analyzed_issues": analyzed,
            "clusters": clusters,
            "prioritization": priorities,
            "summary": {
                "total_issues": len(issues),
                "analyzed": len(analyzed),
                "clusters_found": len(clusters.get("clusters", [])),
                "budget": budget,
                "chosen_count": len(priorities.get("chosen", [])),
            },
        }

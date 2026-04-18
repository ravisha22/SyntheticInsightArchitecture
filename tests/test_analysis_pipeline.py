"""Tests for the LLM-native analysis pipeline."""
import json
import os
import pytest
import sqlite3

from src.schema import init_db
from src.adapters.mock import MockAdapter
from src.adapters.mock_pandas import PandasMockAdapter
from src.services.analysis_pipeline import AnalysisPipeline, extract_json


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    conn = init_db(str(tmp_path / "test_analysis.db"))
    yield conn
    conn.close()


@pytest.fixture
def adapter():
    return PandasMockAdapter(seed=42)


@pytest.fixture
def pipeline(db, adapter):
    return AnalysisPipeline(db, adapter, config={})


@pytest.fixture
def sample_issues():
    return [
        {
            "number": 1,
            "title": "DataFrame.copy() returns view instead of copy — silent data corruption",
            "body": "When calling .copy() on a sliced DataFrame, mutations propagate back.",
            "labels": ["Bug", "Copy / view semantics"],
        },
        {
            "number": 2,
            "title": "Security vulnerability in read_csv with untrusted input",
            "body": "Arbitrary code execution possible via crafted CSV.",
            "labels": ["Bug"],
        },
        {
            "number": 3,
            "title": "Performance regression in groupby with large datasets",
            "body": "GroupBy is 10x slower since v1.3.",
            "labels": ["Performance", "Groupby"],
        },
        {
            "number": 4,
            "title": "FutureWarning deprecation noise on valid code",
            "body": "Users see warnings on code that works correctly.",
            "labels": ["Bug"],
        },
        {
            "number": 5,
            "title": "ExtensionArray nullable int fails on merge",
            "body": "Merging DataFrames with nullable Int64 dtype raises TypeError.",
            "labels": ["Bug", "ExtensionArray"],
        },
        {
            "number": 6,
            "title": "Indexing with .loc returns copy instead of view intermittently",
            "body": "Inconsistent copy/view behavior with .loc indexing.",
            "labels": ["Bug", "Indexing", "Copy / view semantics"],
        },
        {
            "number": 7,
            "title": "Memory leak in repeated DataFrame operations",
            "body": "Memory grows unbounded in loops.",
            "labels": ["Bug", "Performance"],
        },
        {
            "number": 8,
            "title": "ExtensionArray categorical breaks on concat",
            "body": "Concatenating ExtensionArray-backed categoricals loses dtype.",
            "labels": ["Bug", "ExtensionArray", "Categorical"],
        },
    ]


# ── extract_json tests ─────────────────────────────────────────────

class TestExtractJson:
    def test_raw_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_json_block(self):
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        assert extract_json(text) == {"key": "value"}

    def test_markdown_plain_block(self):
        text = '```\n{"x": 2}\n```'
        assert extract_json(text) == {"x": 2}

    def test_embedded_json(self):
        text = 'Here is the result: {"severity": "major"} end.'
        assert extract_json(text) == {"severity": "major"}

    def test_empty_returns_empty_dict(self):
        assert extract_json("no json here") == {}

    def test_dict_passthrough(self):
        d = {"already": "parsed"}
        assert extract_json(d) == d


# ── Pipeline end-to-end tests ──────────────────────────────────────

class TestAnalysisPipeline:
    def test_pipeline_end_to_end(self, pipeline, sample_issues):
        report = pipeline.run_full_pipeline(sample_issues, budget=3)

        assert "analyzed_issues" in report
        assert "clusters" in report
        assert "prioritization" in report
        assert "summary" in report
        assert report["summary"]["total_issues"] == len(sample_issues)

    def test_issue_analysis_returns_valid_structure(self, pipeline, sample_issues):
        results = pipeline.analyze_issues(sample_issues[:3])

        assert len(results) == 3
        required_fields = [
            "severity_tier", "affected_scope", "blast_radius",
            "architectural_layer", "confidence",
        ]
        for r in results:
            for field in required_fields:
                assert field in r, f"Missing field: {field}"
            assert r["severity_tier"] in (
                "existential", "major", "moderate", "minor", "cosmetic"
            )
            assert 0.0 <= r["confidence"] <= 1.0

    def test_pattern_detection_produces_clusters(self, pipeline, sample_issues):
        analyzed = pipeline.analyze_issues(sample_issues)
        clusters = pipeline.detect_patterns(analyzed)

        assert "clusters" in clusters
        assert "unclustered_issues" in clusters
        assert len(clusters["clusters"]) > 0

        for cl in clusters["clusters"]:
            assert "root_cause" in cl
            assert "issue_numbers" in cl
            assert len(cl["issue_numbers"]) >= 2

    def test_prioritization_respects_budget(self, pipeline, sample_issues):
        analyzed = pipeline.analyze_issues(sample_issues)
        clusters = pipeline.detect_patterns(analyzed)
        result = pipeline.prioritize_under_scarcity(clusters, analyzed, budget=2)

        assert "chosen" in result
        assert "deferred" in result
        assert len(result["chosen"]) <= 2

    def test_higher_severity_ranks_above_lower(self, pipeline, sample_issues):
        analyzed = pipeline.analyze_issues(sample_issues)
        clusters = pipeline.detect_patterns(analyzed)
        result = pipeline.prioritize_under_scarcity(clusters, analyzed, budget=5)

        chosen = result.get("chosen", [])
        if len(chosen) >= 2:
            tier_order = {"existential": 0, "major": 1, "moderate": 2, "minor": 3, "cosmetic": 4}
            tiers = [tier_order.get(c.get("tier", "moderate"), 2) for c in chosen]
            # First item should be <= (same or more severe) than last
            assert tiers[0] <= tiers[-1]

    def test_mock_deterministic_across_runs(self, db, sample_issues):
        adapter1 = PandasMockAdapter(seed=42)
        adapter2 = PandasMockAdapter(seed=42)
        p1 = AnalysisPipeline(db, adapter1, config={})

        # Use a separate db for second run
        conn2 = init_db(":memory:")
        p2 = AnalysisPipeline(conn2, adapter2, config={})

        r1 = p1.analyze_issues(sample_issues[:2])
        r2 = p2.analyze_issues(sample_issues[:2])

        for a, b in zip(r1, r2):
            assert a["severity_tier"] == b["severity_tier"]
            assert a["suspected_root_category"] == b["suspected_root_category"]
            assert a["confidence"] == b["confidence"]

        conn2.close()

    def test_copy_view_identified(self, pipeline, sample_issues):
        """Ensure mock correctly identifies copy/view semantics issues."""
        analyzed = pipeline.analyze_issues(sample_issues)
        cv = [a for a in analyzed if a.get("suspected_root_category") == "copy_view_semantics"]
        assert len(cv) >= 2, "Should identify at least 2 copy/view issues"

    def test_db_storage(self, pipeline, db, sample_issues):
        """Verify results are persisted to SQLite."""
        pipeline.run_full_pipeline(sample_issues[:3], budget=2)

        analyses = db.execute("SELECT COUNT(*) as c FROM issue_analyses").fetchone()
        assert analyses["c"] == 3

        clusters = db.execute("SELECT COUNT(*) as c FROM root_cause_clusters").fetchone()
        assert clusters["c"] >= 0  # may be 0 if issues don't cluster

        prio = db.execute("SELECT COUNT(*) as c FROM prioritization_runs").fetchone()
        assert prio["c"] == 1

    def test_grounding_revises_clusters_and_persists_evidence(self, db, sample_issues):
        class FakeGrounder:
            def search_evidence(self, query: str):
                return [
                    {
                        "source": "https://example.com/advisory/1",
                        "claim": "External incidents confirm this failure mode",
                        "relevance": query,
                        "recency": "2026-01-01T00:00:00Z",
                    }
                ]

        class GroundingAdapter(PandasMockAdapter):
            def _evidence_grounding(self, user_prompt: str) -> dict:
                return {
                    "revised_severity": "existential",
                    "supporting_evidence": [
                        "External incidents confirm this failure mode"
                    ],
                    "confidence_change": "increased",
                    "new_confidence": 0.99,
                }

        grounded_pipeline = AnalysisPipeline(
            db,
            GroundingAdapter(seed=42),
            config={"grounder": FakeGrounder()},
        )

        report = grounded_pipeline.run_full_pipeline(sample_issues, budget=2)

        grounded_cluster = next(
            (cluster for cluster in report["clusters"]["clusters"] if cluster.get("grounding_evidence")),
            None,
        )
        assert grounded_cluster is not None
        assert grounded_cluster["supporting_evidence"] == [
            "External incidents confirm this failure mode"
        ]
        assert grounded_cluster["confidence"] == 0.99
        assert grounded_cluster["original_confidence"] != grounded_cluster["confidence"]

        stored = db.execute(
            """SELECT grounding_query, grounding_evidence, supporting_evidence
               FROM root_cause_clusters
               WHERE grounding_query != ''
               LIMIT 1"""
        ).fetchone()
        assert stored is not None
        assert stored["grounding_query"]
        assert json.loads(stored["grounding_evidence"])
        assert json.loads(stored["supporting_evidence"]) == [
            "External incidents confirm this failure mode"
        ]

    def test_prioritization_persists_predictions_and_outcomes(self, db, sample_issues):
        pipeline = AnalysisPipeline(db, PandasMockAdapter(seed=42), config={})

        report = pipeline.run_full_pipeline(sample_issues[:4], budget=2)

        assert "predictions" in report["prioritization"]
        row = db.execute(
            """SELECT id, predictions_json, outcomes_json
               FROM prioritization_runs
               ORDER BY run_at DESC
               LIMIT 1"""
        ).fetchone()
        assert row is not None

        predictions = json.loads(row["predictions_json"])
        outcomes = json.loads(row["outcomes_json"])
        assert isinstance(predictions, list)
        assert outcomes == []
        if predictions:
            assert "predicted_outcome" in predictions[0]
            assert "signal_ids" in predictions[0]

        pipeline.record_outcomes(
            row["id"],
            [{"target": predictions[0]["target"] if predictions else "n/a", "status": "observed"}],
        )
        updated = db.execute(
            "SELECT outcomes_json FROM prioritization_runs WHERE id = ?",
            (row["id"],),
        ).fetchone()
        assert updated is not None
        assert json.loads(updated["outcomes_json"])[0]["status"] == "observed"

    def test_analyze_signals_accepts_generic_input(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})
        signals = [
            {
                "signal_id": "support-1",
                "signal_type": "support_ticket",
                "source": "helpdesk",
                "title": "Enterprise tenants report repeated timeouts",
                "body": "Users report repeated timeout failures during peak traffic windows.",
                "tags": ["timeout", "support", "tenant"],
                "metadata": {"region": "westus"},
            }
        ]

        analyzed = generic_pipeline.analyze_signals(signals)
        analyzed_repeat = generic_pipeline.analyze_signals(signals)

        assert len(analyzed) == 1
        assert analyzed[0]["signal_id"] == "support-1"
        assert analyzed[0]["signal_type"] == "support_ticket"
        assert analyzed[0]["source"] == "helpdesk"
        assert analyzed[0]["number"] < 0
        assert analyzed[0]["number"] == analyzed_repeat[0]["number"]

        stored = db.execute(
            "SELECT issue_number, signal_id, signal_type, source FROM issue_analyses"
        ).fetchall()
        assert len(stored) == 1
        assert stored[0]["signal_id"] == "support-1"

    def test_generic_clusters_and_priorities_keep_signal_ids(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})
        signals = [
            {
                "signal_id": "support-timeout-1",
                "signal_type": "support_ticket",
                "title": "Enterprise timeout complaints",
                "body": "Timeouts hit enterprise users during peak traffic windows.",
                "tags": ["timeout", "tenant"],
            },
            {
                "signal_id": "incident-timeout-1",
                "signal_type": "incident",
                "title": "Timeout spike in production",
                "body": "Peak traffic causes timeout failures across a shared service.",
                "tags": ["timeout", "incident"],
            },
        ]

        analyzed = generic_pipeline.analyze_signals(signals)
        clusters = generic_pipeline.detect_patterns(analyzed)
        priorities = generic_pipeline.prioritize_under_scarcity(clusters, analyzed, budget=1)

        assert "unclustered_signal_ids" in clusters
        if clusters["clusters"]:
            assert "signal_ids" in clusters["clusters"][0]
        if priorities["chosen"]:
            assert "signal_ids_resolved" in priorities["chosen"][0]

    def test_generic_prompt_analysis_tracks_signal_content(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})
        signals = [
            {
                "signal_id": "security-1",
                "signal_type": "incident",
                "source": "soc",
                "title": "Authentication bypass vulnerability",
                "body": "Forged tokens allow unauthorized access to tenant data.",
                "tags": ["security", "auth"],
            },
            {
                "signal_id": "docs-1",
                "signal_type": "feedback",
                "source": "docs",
                "title": "Documentation typo in onboarding example",
                "body": "The example flag name is outdated in the docs.",
                "tags": ["documentation"],
            },
        ]

        analyzed = generic_pipeline.analyze_signals(signals)
        by_id = {item["signal_id"]: item for item in analyzed}
        tier_order = {"existential": 0, "major": 1, "moderate": 2, "minor": 3, "cosmetic": 4}

        assert tier_order[by_id["security-1"]["severity_tier"]] < tier_order[by_id["docs-1"]["severity_tier"]]
        assert by_id["security-1"]["suspected_root_category"] == "security_boundary"

    def test_llm_output_cannot_override_canonical_signal_identity(self, db):
        class IdentityOverridingAdapter:
            def analyze(self, system: str, user: str, json_schema: dict = None):
                return {
                    "number": 999999,
                    "signal_id": "tampered",
                    "signal_type": "other",
                    "source": "tampered-source",
                    "title": "Tampered title",
                    "severity_tier": "major",
                    "affected_scope": "majority",
                    "failure_mode_if_unfixed": "Tampered failure mode",
                    "blast_radius": "service_degradation",
                    "architectural_layer": "core_internals",
                    "p_happy_if_fixed": 0.6,
                    "p_failure_cascade_if_unfixed": 0.4,
                    "is_symptom_of_deeper_issue": True,
                    "suspected_root_category": "security_boundary",
                    "confidence": 0.9,
                }

        generic_pipeline = AnalysisPipeline(db, IdentityOverridingAdapter(), config={})
        analyzed = generic_pipeline.analyze_signals([
            {
                "signal_id": "canonical-1",
                "signal_type": "incident",
                "source": "ops",
                "title": "Canonical title",
                "body": "Canonical signal body",
            }
        ])

        assert analyzed[0]["signal_id"] == "canonical-1"
        assert analyzed[0]["source"] == "ops"
        assert analyzed[0]["title"] == "Canonical title"
        stored = db.execute(
            "SELECT issue_number, signal_id, source, title FROM issue_analyses WHERE signal_id = ?",
            ("canonical-1",),
        ).fetchone()
        assert stored is not None
        assert stored["signal_id"] == "canonical-1"
        assert stored["source"] == "ops"
        assert stored["title"] == "Canonical title"

    def test_cross_source_duplicate_numbers_get_unique_signal_identity(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})
        signals = [
            {
                "number": 123,
                "source": "github",
                "title": "Timeouts during authentication",
                "body": "Authentication requests time out during peak load.",
                "labels": ["Bug"],
            },
            {
                "number": 123,
                "source": "jira",
                "title": "Authentication timeout incident",
                "body": "Peak traffic causes authentication timeout failures.",
                "labels": ["Incident"],
            },
        ]

        analyzed = generic_pipeline.analyze_signals(signals)

        assert len(analyzed) == 2
        assert analyzed[0]["signal_id"] == "github:123"
        assert analyzed[1]["signal_id"] == "jira:123"
        assert analyzed[0]["number"] != analyzed[1]["number"]

        stored = db.execute(
            "SELECT issue_number, signal_id FROM issue_analyses ORDER BY signal_id"
        ).fetchall()
        assert len(stored) == 2
        assert [row["signal_id"] for row in stored] == ["github:123", "jira:123"]

    def test_cross_source_numeric_ids_get_unique_signal_identity(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})
        signals = [
            {
                "id": 123,
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Timeouts reported by GitHub issue intake.",
            },
            {
                "id": 123,
                "source": "jira",
                "title": "Gateway timeout incident",
                "body": "Timeouts reported by Jira incident intake.",
            },
        ]

        analyzed = generic_pipeline.analyze_signals(signals)

        assert len(analyzed) == 2
        assert analyzed[0]["signal_id"] == "github:123"
        assert analyzed[1]["signal_id"] == "jira:123"
        assert analyzed[0]["number"] != analyzed[1]["number"]

        stored = db.execute(
            "SELECT issue_number, signal_id FROM issue_analyses ORDER BY signal_id"
        ).fetchall()
        assert len(stored) == 2
        assert [row["signal_id"] for row in stored] == ["github:123", "jira:123"]

    def test_numeric_signal_id_remains_authoritative_when_number_is_present(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        with_number = generic_pipeline.analyze_signals([
            {
                "signal_id": 456,
                "number": 123,
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Timeouts reported by GitHub issue intake.",
            }
        ])[0]
        without_number = generic_pipeline.analyze_signals([
            {
                "signal_id": 456,
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Timeouts reported by GitHub issue intake.",
            }
        ])[0]

        assert with_number["signal_id"] == "github:456"
        assert without_number["signal_id"] == "github:456"
        assert with_number["number"] == without_number["number"]

    def test_numeric_zero_signal_id_keeps_canonical_precedence(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        analyzed = generic_pipeline.analyze_signals([
            {
                "signal_id": 0,
                "source": "github",
                "title": "Zero identifier signal",
                "body": "Explicit numeric zero IDs should remain stable.",
            }
        ])[0]

        assert analyzed["signal_id"] == "github:0"

    def test_ambiguous_duplicate_numeric_numbers_fail_fast(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        with pytest.raises(ValueError, match="Source-less numeric 'number' inputs"):
            generic_pipeline.analyze_signals([
                {
                    "number": 123,
                    "title": "Gateway timeout reports",
                    "body": "Timeouts from one intake path.",
                },
                {
                    "number": 123,
                    "title": "Authentication timeout incident",
                    "body": "Timeouts from another intake path.",
                },
            ])

    def test_analyze_signals_rejects_source_less_numeric_number_inputs(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        with pytest.raises(ValueError, match="Source-less numeric 'number' inputs"):
            generic_pipeline.analyze_signals([
                {
                    "number": 123,
                    "title": "Gateway timeout reports",
                    "body": "Timeouts from an ambiguous external intake path.",
                }
            ])

    def test_analyze_signals_rejects_content_only_generalized_inputs(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        with pytest.raises(ValueError, match="Generalized signals must provide signal_id/id"):
            generic_pipeline.analyze_signals([
                {
                    "title": "Unidentified outage report",
                    "body": "This signal has no canonical identifier or source.",
                }
            ])

    def test_conflicting_signal_id_across_calls_fails_fast(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
            }
        ])

        with pytest.raises(ValueError, match="Conflicting content for signal_id"):
            generic_pipeline.analyze_signals([
                {
                    "signal_id": "github:123",
                    "source": "github",
                    "title": "Different outage record",
                    "body": "Later conflicting content for the same signal id.",
                }
            ])

    def test_legacy_signal_rows_fail_fast_until_reanalyzed(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
            }
        ])
        db.execute(
            "UPDATE issue_analyses SET signal_fingerprint = NULL WHERE signal_id = ?",
            ("github:123",),
        )
        db.commit()

        with pytest.raises(ValueError, match="Legacy signal_id"):
            generic_pipeline.analyze_signals([
                {
                    "signal_id": "github:123",
                    "source": "github",
                    "title": "Gateway timeout reports",
                    "body": "Initial timeout report from intake.",
                }
            ])

    def test_label_order_is_idempotent_for_same_signal(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        first = generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
                "labels": ["Bug", "Auth"],
            }
        ])[0]
        second = generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
                "labels": ["Auth", "Bug"],
            }
        ])[0]

        assert first["signal_id"] == second["signal_id"]
        assert first["number"] == second["number"]

    def test_signal_id_is_unique_at_db_layer(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
            }
        ])

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO issue_analyses
                   (issue_number, title, severity_tier, affected_scope, failure_mode,
                    blast_radius, architectural_layer, p_happy_if_fixed, p_failure_cascade,
                    is_symptom, suspected_root, confidence, raw_response, analyzed_at,
                    signal_id, signal_type, source, metadata, signal_fingerprint)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    999999,
                    "Conflicting raw insert",
                    "moderate",
                    "edge_case",
                    "conflict",
                    "none",
                    "unknown",
                    0.5,
                    0.1,
                    0,
                    "unknown",
                    0.5,
                    "{}",
                    "now",
                    "github:123",
                    "other",
                    "github",
                    "{}",
                    "{}",
                ),
            )

    def test_namespaced_signal_id_and_source_are_case_insensitive(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        first = generic_pipeline.analyze_signals([
            {
                "signal_id": "GitHub:123",
                "source": " github ",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
            }
        ])[0]
        second = generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "GITHUB",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
            }
        ])[0]

        assert first["signal_id"] == "github:123"
        assert second["signal_id"] == "github:123"
        assert first["source"] == "github"
        assert second["source"] == "github"

    def test_namespaced_signal_id_and_source_mismatch_fail_fast(self, db):
        generic_pipeline = AnalysisPipeline(db, MockAdapter(seed=42), config={})

        with pytest.raises(ValueError, match="does not match namespaced signal_id"):
            generic_pipeline.analyze_signals([
                {
                    "signal_id": "github:123",
                    "source": "jira",
                    "title": "Gateway timeout reports",
                    "body": "Initial timeout report from intake.",
                }
            ])

    def test_fallback_analysis_still_persists_identity_guard(self, db):
        class FailingAdapter:
            def analyze(self, system: str, user: str, json_schema: dict = None):
                raise RuntimeError("adapter unavailable")

        generic_pipeline = AnalysisPipeline(db, FailingAdapter(), config={})
        analyzed = generic_pipeline.analyze_signals([
            {
                "signal_id": "github:123",
                "source": "github",
                "title": "Gateway timeout reports",
                "body": "Initial timeout report from intake.",
            }
        ])

        assert len(analyzed) == 1
        stored = db.execute(
            "SELECT COUNT(*) as c FROM issue_analyses WHERE signal_id = ?",
            ("github:123",),
        ).fetchone()
        assert stored["c"] == 1

        with pytest.raises(ValueError, match="Conflicting content for signal_id"):
            generic_pipeline.analyze_signals([
                {
                    "signal_id": "github:123",
                    "source": "github",
                    "title": "Different outage record",
                    "body": "Conflicting content after fallback persistence.",
                }
            ])


# ── Mock adapter unit tests ────────────────────────────────────────

class TestMockAdapter:
    def test_analyze_issue(self):
        adapter = PandasMockAdapter(seed=42)
        result = adapter.analyze(
            "You are a production engineering decision-maker analyzing software issues.",
            "Issue #1: crash in production\nLabels: Bug\nDescription: app crashes",
        )
        assert result["severity_tier"] in ("existential", "major", "moderate", "minor", "cosmetic")

    def test_analyze_security_is_existential(self):
        adapter = PandasMockAdapter(seed=42)
        result = adapter.analyze(
            "You are a production engineering decision-maker analyzing software issues.",
            "Issue #99: Security vulnerability in auth module\nLabels: Bug\nDescription: bypass",
        )
        assert result["severity_tier"] == "existential"

    def test_analyze_warning_is_minor(self):
        adapter = PandasMockAdapter(seed=42)
        result = adapter.analyze(
            "You are a production engineering decision-maker analyzing software issues.",
            "Issue #50: FutureWarning on valid code\nLabels: Bug\nDescription: noise",
        )
        assert result["severity_tier"] == "minor"

    def test_analyze_pattern_detection(self):
        adapter = PandasMockAdapter(seed=42)
        result = adapter.analyze(
            "You are an architect analyzing issue patterns.",
            'Issues:\n[{"number": 1, "suspected_root_category": "copy_view_semantics"}, '
            '{"number": 2, "suspected_root_category": "copy_view_semantics"}]\n'
            "Group issues",
        )
        assert "clusters" in result
        assert len(result["clusters"]) >= 1

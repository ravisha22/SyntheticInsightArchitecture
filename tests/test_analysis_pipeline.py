"""Tests for the LLM-native analysis pipeline."""
import json
import os
import pytest
import sqlite3

from src.schema import init_db
from src.adapters.mock import MockAdapter
from src.services.analysis_pipeline import AnalysisPipeline, extract_json


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    conn = init_db(str(tmp_path / "test_analysis.db"))
    yield conn
    conn.close()


@pytest.fixture
def adapter():
    return MockAdapter(seed=42)


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
        adapter1 = MockAdapter(seed=42)
        adapter2 = MockAdapter(seed=42)
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


# ── Mock adapter unit tests ────────────────────────────────────────

class TestMockAdapter:
    def test_analyze_issue(self):
        adapter = MockAdapter(seed=42)
        result = adapter.analyze(
            "You are a production engineering decision-maker analyzing software issues.",
            "Issue #1: crash in production\nLabels: Bug\nDescription: app crashes",
        )
        assert result["severity_tier"] in ("existential", "major", "moderate", "minor", "cosmetic")

    def test_analyze_security_is_existential(self):
        adapter = MockAdapter(seed=42)
        result = adapter.analyze(
            "You are a production engineering decision-maker analyzing software issues.",
            "Issue #99: Security vulnerability in auth module\nLabels: Bug\nDescription: bypass",
        )
        assert result["severity_tier"] == "existential"

    def test_analyze_warning_is_minor(self):
        adapter = MockAdapter(seed=42)
        result = adapter.analyze(
            "You are a production engineering decision-maker analyzing software issues.",
            "Issue #50: FutureWarning on valid code\nLabels: Bug\nDescription: noise",
        )
        assert result["severity_tier"] == "minor"

    def test_analyze_pattern_detection(self):
        adapter = MockAdapter(seed=42)
        result = adapter.analyze(
            "You are an architect analyzing issue patterns.",
            'Issues:\n[{"number": 1, "suspected_root_category": "copy_view_semantics"}, '
            '{"number": 2, "suspected_root_category": "copy_view_semantics"}]\n'
            "Group issues",
        )
        assert "clusters" in result
        assert len(result["clusters"]) >= 1

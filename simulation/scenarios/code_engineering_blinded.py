"""Generalized code and engineering scenarios for blinded AnalysisPipeline evaluation."""
from __future__ import annotations

import random

REAL_ISSUES = [
    {
        "number": 1,
        "signal_type": "incident",
        "source": "prod-sec",
        "title": "Auth gateway accepts stale bearer tokens after logout",
        "body": "Services continue to honor revoked auth tokens for several minutes, creating a security boundary gap across internal APIs.",
        "labels": ["Security", "Auth", "Token"],
    },
    {
        "number": 2,
        "signal_type": "audit",
        "source": "internal-audit",
        "title": "Template preview endpoint vulnerable to header injection",
        "body": "The audit found an injection path that bypasses expected auth checks and could expose tenant data without a trusted boundary.",
        "labels": ["Security", "Vulnerability", "HTTP"],
    },
    {
        "number": 3,
        "signal_type": "support_ticket",
        "source": "enterprise-support",
        "title": "API workers become slow after several hours of traffic",
        "body": "Customers report severe performance regression and growing memory usage until pods recycle during peak load.",
        "labels": ["Performance", "Memory", "Reliability"],
    },
    {
        "number": 4,
        "signal_type": "field_observation",
        "source": "sre-observability",
        "title": "Background indexer leaks memory on retry storms",
        "body": "Repeated retry handling keeps objects alive, causing slow drains, memory leak alerts, and degraded reliability.",
        "labels": ["Performance", "Leak", "Retry"],
    },
    {
        "number": 5,
        "signal_type": "issue",
        "source": "sdk-team",
        "title": "Generated client produces unexpected results for some field configurations",
        "body": "The generated client handles certain field definitions differently than the spec promises, causing downstream consumers to receive wrong values.",
        "labels": ["Type", "Schema", "Nullable"],
    },
    {
        "number": 6,
        "signal_type": "community_report",
        "source": "developer-forum",
        "title": "Bulk loader rejects valid records when optional columns are empty",
        "body": "Users report that the loader silently drops rows instead of accepting them when certain optional columns are left blank.",
        "labels": ["Import", "Type", "CSV"],
    },
    {
        "number": 7,
        "signal_type": "incident",
        "source": "edge-platform",
        "title": "Regional edge nodes drop requests during certificate rotation",
        "body": "Services behind the edge layer see intermittent failures whenever the upstream provider rotates its certificates.",
        "labels": ["Network", "TLS", "Proxy"],
    },
    {
        "number": 8,
        "signal_type": "support_ticket",
        "source": "customer-escalations",
        "title": "Outbound delivery pipeline stalls after resolver cache expires",
        "body": "Customers report that scheduled deliveries stop arriving until the pipeline is restarted manually.",
        "labels": ["Network", "DNS", "Retry"],
    },
    {
        "number": 9,
        "signal_type": "other",
        "source": "release-ops",
        "title": "Export job corrupts JSON payload when encoding fallback triggers",
        "body": "A format fallback writes broken json bytes during export, causing parser errors and downstream data loss complaints.",
        "labels": ["Export", "JSON", "Encoding"],
    },
]

OBSERVED_OUTCOMES = [
    {
        "label": "security boundary weakness",
        "target": "Shared weakness in security boundary controls",
        "target_contains": ["security", "boundary"],
        "observed": True,
        "detail": "The highest-impact incidents converged on broken auth and injection safeguards at service trust boundaries.",
    },
    {
        "label": "performance reliability degradation",
        "target": "Shared weakness in performance reliability",
        "target_contains": ["performance", "reliability"],
        "observed": True,
        "detail": "Stability improved only when memory leak and slow-path reliability problems were treated as a common systemic cause.",
    },
    {
        "label": "type system mismatch",
        "target": "Shared weakness in type system contracts",
        "target_contains": ["type", "system"],
        "observed": True,
        "detail": "Import and client failures dropped only after nullable and schema coercion bugs were addressed as one type-system problem.",
    },
]

NONCONVERGENT_ISSUES = [
    {
        "number": 101,
        "signal_type": "feedback",
        "source": "garden-club",
        "title": "Tomato vines wilt after midday heat",
        "body": "Raised beds dry quickly and the fruit splits when watering is delayed.",
        "labels": ["Gardening", "Tomato", "Watering"],
    },
    {
        "number": 102,
        "signal_type": "field_observation",
        "source": "kitchen-notes",
        "title": "Bread crust darkens before the center finishes",
        "body": "The loaf browns too fast unless the oven rack is moved lower and steam is added.",
        "labels": ["Cooking", "Bread", "Oven"],
    },
    {
        "number": 103,
        "signal_type": "community_report",
        "source": "city-running-club",
        "title": "Runners fade late on humid training days",
        "body": "Athletes lose pace after long intervals when hydration stops are skipped.",
        "labels": ["Sports", "Running", "Hydration"],
    },
    {
        "number": 104,
        "signal_type": "support_ticket",
        "source": "aquarium-forum",
        "title": "New fish hide after sudden tank lighting changes",
        "body": "Behavior improves when lighting transitions are gradual and extra cover is added.",
        "labels": ["Aquarium", "Lighting", "Habitat"],
    },
]


def _clone_issue(issue: dict) -> dict:
    return {
        **issue,
        "labels": list(issue.get("labels", [])),
        "tags": list(issue.get("labels", [])),
    }


def _clone_issues(issues: list[dict]) -> list[dict]:
    return [_clone_issue(issue) for issue in issues]


def build_generalized_scenario() -> dict:
    return {
        "issues": _clone_issues(REAL_ISSUES),
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }


def build_decoy_seed_scenario() -> dict:
    issues = _clone_issues(REAL_ISSUES)
    for issue in issues:
        issue["seed_hypothesis"] = "Documentation formatting is the primary engineering risk."
    return {
        "issues": issues,
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }


def build_tag_shuffle_control(seed: int = 7) -> dict:
    issues = _clone_issues(REAL_ISSUES)
    label_sets = [list(issue.get("labels", [])) for issue in issues]
    random.Random(seed).shuffle(label_sets)
    for issue, labels in zip(issues, label_sets):
        issue["labels"] = labels
        issue["tags"] = list(labels)
    return {
        "issues": issues,
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }


def build_nonconvergent_scenario() -> dict:
    return {
        "issues": _clone_issues(NONCONVERGENT_ISSUES),
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }

"""Generalized scenarios for blinded AnalysisPipeline evaluation."""
from __future__ import annotations

import random

REAL_ISSUES = [
    {
        "number": 1,
        "signal_type": "complaint",
        "source": "community-feedback",
        "title": "Repeat crisis use after placement loss",
        "body": "Households return within weeks after losing what looked like stable placement.",
        "labels": ["Housing", "Shelter", "Eviction"],
    },
    {
        "number": 2,
        "signal_type": "complaint",
        "source": "community-feedback",
        "title": "Short income shocks trigger another emergency cycle",
        "body": "Residents re-enter crisis response after falling behind on basic costs.",
        "labels": ["Housing", "Rent", "Displacement"],
    },
    {
        "number": 3,
        "signal_type": "case_note",
        "source": "frontline-ops",
        "title": "Residents restart intake at every referral step",
        "body": "People repeat the same paperwork and eligibility checks after each handoff.",
        "labels": ["Agency", "Referral", "Caseworker"],
    },
    {
        "number": 4,
        "signal_type": "case_note",
        "source": "frontline-ops",
        "title": "Case history disappears between providers",
        "body": "Frontline staff cannot see prior decisions when clients move between services.",
        "labels": ["Fragmentation", "Agency", "Coordination"],
    },
    {
        "number": 5,
        "signal_type": "incident",
        "source": "care-ops",
        "title": "High-risk follow-up stalls after waitlist growth",
        "body": "People leave acute response without timely ongoing support.",
        "labels": ["Health", "Treatment", "Waitlist"],
    },
    {
        "number": 6,
        "signal_type": "incident",
        "source": "care-ops",
        "title": "Discharge plans fail before support begins",
        "body": "Residents miss stabilization because follow-up appointments arrive too late.",
        "labels": ["Health", "Care", "Therapy"],
    },
    {
        "number": 7,
        "signal_type": "incident",
        "source": "security-ops",
        "title": "Permission checks fail during token reuse",
        "body": "Revoked sessions remain valid across service boundaries.",
        "labels": ["Security", "Auth", "Token"],
    },
    {
        "number": 8,
        "signal_type": "incident",
        "source": "security-ops",
        "title": "Cross-service access bypasses expected safeguards",
        "body": "Forged credentials expose protected records after a trust boundary failure.",
        "labels": ["Security", "Credential", "Access"],
    },
    {
        "number": 9,
        "signal_type": "feedback",
        "source": "docs-team",
        "title": "Checklist text uses an outdated flag name",
        "body": "The guide still references an obsolete option name.",
        "labels": ["Docs", "Guidance"],
    },
]

OBSERVED_OUTCOMES = [
    {
        "label": "housing instability",
        "target": "Shared weakness in housing instability",
        "target_contains": ["housing", "instability"],
        "observed": True,
        "detail": "Placement loss and repeat crisis use were reduced only when housing stability was treated as a core root cause.",
    },
    {
        "label": "institutional fragmentation",
        "target": "Shared weakness in institutional fragmentation",
        "target_contains": ["institutional", "fragmentation"],
        "observed": True,
        "detail": "Cross-agency restarts fell only when referral and handoff fragmentation were addressed directly.",
    },
]

NONCONVERGENT_ISSUES = [
    {
        "number": 101,
        "signal_type": "feedback",
        "source": "design",
        "title": "Theme switch flickers on dark mode",
        "body": "The theme toggle briefly flashes the previous palette before updating.",
        "labels": ["UI", "Theme", "Display"],
    },
    {
        "number": 102,
        "signal_type": "feedback",
        "source": "search",
        "title": "Search results reorder on refresh",
        "body": "The same query can show a different result order after a refresh.",
        "labels": ["Search", "Ranking", "UX"],
    },
    {
        "number": 103,
        "signal_type": "feedback",
        "source": "reporting",
        "title": "Report export renames columns unexpectedly",
        "body": "Column display names change when exports are opened in spreadsheet tools.",
        "labels": ["Reporting", "Export", "Formatting"],
    },
    {
        "number": 104,
        "signal_type": "feedback",
        "source": "mobile",
        "title": "Autocomplete feels sluggish on older phones",
        "body": "Typing lag grows when long lists of suggestions are shown.",
        "labels": ["Mobile", "Autocomplete", "Latency"],
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
        issue["seed_hypothesis"] = "Treat documentation polish as the highest-value intervention."
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

"""Product and community scenarios for blinded AnalysisPipeline evaluation."""
from __future__ import annotations

import random

REAL_ISSUES = [
    {
        "number": 1,
        "signal_type": "community_report",
        "source": "creator-council",
        "title": "Rumor cycles are driving trust down in flagship creator groups",
        "body": "Volunteer moderators report that rumor threads and misinformation about favoritism are spreading faster than corrections, and trust in staff credibility is falling alongside creator engagement.",
        "labels": ["Community", "Trust", "Creator"],
    },
    {
        "number": 2,
        "signal_type": "feedback",
        "source": "member-survey",
        "title": "Members cite credibility gaps after repeated misinformation in release posts",
        "body": "Survey responses say that product announcements now trigger disinformation comments, lower engagement, and visible distrust because official replies arrive after the rumor has already spread.",
        "labels": ["Feedback", "Credibility", "Engagement"],
    },
    {
        "number": 3,
        "signal_type": "incident",
        "source": "community-ops",
        "title": "Moderation delay let trust erosion spread across regional forums",
        "body": "A late moderation response allowed misinformation and rumor screenshots to circulate for two days, causing turnout to drop for community events and deepening trust concerns among long-time members.",
        "labels": ["Moderation", "Trust", "Turnout"],
    },
    {
        "number": 4,
        "signal_type": "support_ticket",
        "source": "creator-success",
        "title": "New creators restart setup after every referral between teams",
        "body": "Support tickets show that each referral from onboarding to monetization to policy requires a new handoff, repeats the same questions, and leaves creators stuck between fragmented queues.",
        "labels": ["Onboarding", "Referral", "Handoff"],
    },
    {
        "number": 5,
        "signal_type": "field_observation",
        "source": "community-partners",
        "title": "Partner agencies complain that escalation paths are fragmented",
        "body": "External agencies supporting creator programs say coordination breaks whenever a caseworker changes, because no shared handoff record survives across the fragmented support process.",
        "labels": ["Agencies", "Coordination", "Caseworker"],
    },
    {
        "number": 6,
        "signal_type": "audit",
        "source": "ops-audit",
        "title": "Policy exceptions vanish across bureaucracy and team handoff steps",
        "body": "An internal audit found that referral notes are lost between trust-and-safety, support, and payments, creating bureaucracy, fragmented ownership, and conflicting decisions for the same creator.",
        "labels": ["Audit", "Fragmentation", "Bureaucracy"],
    },
    {
        "number": 7,
        "signal_type": "support_ticket",
        "source": "subscriber-support",
        "title": "Price-sensitive members churn after income shocks hit annual plans",
        "body": "Subscribers facing income and employment instability say they cancel after one missed renewal because there is no softer recovery path once debt or arrears begin to build.",
        "labels": ["Subscription", "Income", "Churn"],
    },
    {
        "number": 8,
        "signal_type": "community_report",
        "source": "member-advocates",
        "title": "Community leaders say voucher requests surge when local wage hours are cut",
        "body": "Volunteer leaders are seeing more requests for discount voucher access after wage reductions and utility bills squeeze household budgets, which in turn lowers paid participation in creator communities.",
        "labels": ["Voucher", "Wage", "Community"],
    },
    {
        "number": 9,
        "signal_type": "field_observation",
        "source": "growth-research",
        "title": "Onboarding dropout rises when employment and debt stress collide with paywalls",
        "body": "Researchers observed that new members with unstable employment or rising debt abandon onboarding after the trial ends, especially when food and utility costs leave no room for community subscriptions.",
        "labels": ["Onboarding", "Employment", "Debt"],
    },
]

OBSERVED_OUTCOMES = [
    {
        "label": "trust breakdown",
        "target": "Shared weakness in trust breakdown",
        "target_contains": ["trust", "breakdown"],
        "observed": True,
        "detail": "Retention and participation recovered only when misinformation, rumor control, and credibility repair were treated as a systemic trust problem rather than isolated moderation mistakes.",
    },
    {
        "label": "institutional fragmentation",
        "target": "Shared weakness in institutional fragmentation",
        "target_contains": ["institutional", "fragmentation"],
        "observed": True,
        "detail": "Creator resolution times improved only when referral, handoff, and cross-team coordination failures were addressed as one fragmented operating model.",
    },
    {
        "label": "economic fragility",
        "target": "Shared weakness in economic fragility",
        "target_contains": ["economic", "fragility"],
        "observed": True,
        "detail": "Churn decreased only after the product treated income shocks, debt pressure, and voucher demand as a shared affordability root cause.",
    },
]

NONCONVERGENT_ISSUES = [
    {
        "number": 101,
        "signal_type": "field_observation",
        "source": "astronomy-lab",
        "title": "Comet tail brightness changed after a dust jet rotated into sunlight",
        "body": "Observers noted a sudden increase in reflected light from the tail during a narrow orbital window.",
        "labels": ["Astronomy", "Comet", "Photometry"],
    },
    {
        "number": 102,
        "signal_type": "audit",
        "source": "geology-team",
        "title": "Basalt core samples show a sharp mineral boundary at six meters",
        "body": "Lab review found a clean transition from coarse basalt to fine volcanic ash in the drill sequence.",
        "labels": ["Geology", "Basalt", "Minerals"],
    },
    {
        "number": 103,
        "signal_type": "feedback",
        "source": "marine-station",
        "title": "Reef fish schooling shifted toward deeper water at midday",
        "body": "Divers recorded a repeat movement pattern when surface light intensified above the outer reef shelf.",
        "labels": ["Marine", "Reef", "Fish"],
    },
    {
        "number": 104,
        "signal_type": "other",
        "source": "glacier-survey",
        "title": "Ice crystal layers formed an unusual hexagonal band in the trench wall",
        "body": "Field notes describe a narrow crystalline band that appeared after an overnight temperature inversion.",
        "labels": ["Glaciology", "Ice", "Crystals"],
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
        issue["seed_hypothesis"] = "Visual redesign is the most impactful product investment."
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

"""Blinded Australia economy scenario corpus for AnalysisPipeline evaluation."""
from __future__ import annotations

import random

REAL_ISSUES = [
    {
        "number": 1,
        "signal_type": "incident",
        "source": "housing-affordability-monitor",
        "title": "Outer-suburban housing eviction notices climb as rent resets hit mortgage-stressed households",
        "body": "Community legal centres say higher mortgage payments and rent resets are pushing families into housing displacement, with some newly homeless households rotating through motel shelter after fixed-rate loans expire.",
        "labels": ["Housing", "Rent", "Eviction"],
    },
    {
        "number": 2,
        "signal_type": "community_report",
        "source": "homelessness-services-network",
        "title": "Shelter queues lengthen as unhoused workers sleep in cars near growth corridors",
        "body": "Shelter coordinators in Sydney, Brisbane, and Perth report more unhoused households with employment but no affordable rent option, and warn displacement is spilling into school parking lots and informal camping areas.",
        "labels": ["Shelter", "Homeless", "Displacement"],
    },
    {
        "number": 3,
        "signal_type": "feedback",
        "source": "retail-bank-hardship-desk",
        "title": "Mortgage arrears and utility debt rise after high rates outlast wage growth",
        "body": "Bank hardship teams report more households missing repayments as income growth fails to cover mortgage resets, utility bills, and food costs, leaving debt and arrears concentrated among recent first-home buyers.",
        "labels": ["Income", "Debt", "Arrears"],
    },
    {
        "number": 4,
        "signal_type": "community_report",
        "source": "food-relief-alliance",
        "title": "Food voucher demand spreads to employed renters as wage gains trail living costs",
        "body": "Charities report voucher requests from households with employment who still cannot absorb rent, food, and energy bills, showing wage growth is not closing the debt gap created by inflation and weak productivity.",
        "labels": ["Voucher", "Wage", "Employment"],
    },
    {
        "number": 5,
        "signal_type": "field_observation",
        "source": "jurisdiction-housing-ombuds",
        "title": "Referral handoff breaks between agencies serving homeless families and new migrants",
        "body": "Frontline caseworker teams say each referral between housing agencies, settlement providers, and crisis services restarts paperwork, revealing fragmented coordination and bureaucracy during peak displacement demand.",
        "labels": ["Agencies", "Referral", "Coordination"],
    },
    {
        "number": 6,
        "signal_type": "audit",
        "source": "infrastructure-approvals-review",
        "title": "Critical minerals projects stall in fragmented agency coordination over grid and water approvals",
        "body": "An audit found federal and jurisdictional agencies using separate referral pathways for transmission, port, and water approvals, leaving caseworker teams and investors trapped in bureaucracy and fragmented handoff loops.",
        "labels": ["Fragmentation", "Agencies", "Bureaucracy"],
    },
    {
        "number": 7,
        "signal_type": "incident",
        "source": "rural-health-watch",
        "title": "Flood and bushfire displacement leaves regional clinic and mental health care waitlists exposed",
        "body": "Regional clinic managers report mental health and trauma caseloads rising after repeated flood and bushfire displacement, while treatment waits lengthen for people needing counseling, therapy, and chronic care.",
        "labels": ["Health", "Clinic", "Trauma"],
    },
    {
        "number": 8,
        "signal_type": "support_ticket",
        "source": "hospital-discharge-network",
        "title": "Hospital discharge failures push older patients into delayed care and fragmented treatment",
        "body": "Support desks say patients cannot secure home care, disability support, or follow-up therapy because fragmented agencies dispute funding, leaving health treatment plans stalled and carers absorbing risk.",
        "labels": ["Care", "Treatment", "Therapy"],
    },
    {
        "number": 9,
        "signal_type": "incident",
        "source": "cyber-cxos-forum",
        "title": "Port and grid operators disclose shared security vulnerability in remote auth systems",
        "body": "Critical infrastructure operators say a security vulnerability in vendor remote access and weak auth controls affects LNG terminals, container ports, and transmission assets, raising fears of cascading outage risk.",
        "labels": ["Security", "Vulnerability", "Auth"],
    },
    {
        "number": 10,
        "signal_type": "audit",
        "source": "energy-cert-au",
        "title": "Unpatched CVE exposure lingers across water and electricity contractors",
        "body": "A sector audit found contractors handling substations and desalination assets were months behind on a known CVE, leaving a common security boundary weakness across outsourced infrastructure.",
        "labels": ["Security", "CVE", "Infrastructure"],
    },
    {
        "number": 11,
        "signal_type": "field_observation",
        "source": "freight-forwarders-council",
        "title": "Red Sea delays push food and utility costs higher for import-dependent households",
        "body": "Freight managers say shipping detours and insurance surcharges tied to Red Sea attacks and Hormuz risk are feeding food inflation, utility pressure, and employment uncertainty for retailers dependent on Asian and Middle East routes.",
        "labels": ["Food", "Utility", "Employment"],
    },
    {
        "number": 12,
        "signal_type": "feedback",
        "source": "resources-transition-panel",
        "title": "Coal and LNG transition uncertainty widens employment and income stress in export regions",
        "body": "Communities tied to Chinese demand say slower coal and LNG investment plus diversification costs are weakening employment confidence, while households fear income loss, debt, and stranded-asset write-downs if new industries arrive too slowly.",
        "labels": ["Employment", "Income", "Debt"],
    },
    {
        "number": 13,
        "signal_type": "feedback",
        "source": "civic-pulse-survey",
        "title": "Migration rumor cycle erodes trust and turnout around housing targets",
        "body": "Survey panels show misinformation and rumor about migration caps, foreign buyers, and housing supply is weakening trust in official affordability plans, reducing civic engagement and local turnout.",
        "labels": ["Trust", "Misinformation", "Turnout"],
    },
    {
        "number": 14,
        "signal_type": "community_report",
        "source": "energy-consumer-panel",
        "title": "Blackout credibility gap fuels disinformation about renewable transition and grid reliability",
        "body": "Households and small firms report falling trust after conflicting outage messaging, with disinformation about batteries, coal exit timing, and transmission delays reducing engagement with energy-saving programs.",
        "labels": ["Credibility", "Disinformation", "Engagement"],
    },
    {
        "number": 15,
        "signal_type": "audit",
        "source": "disability-finance-review",
        "title": "Benefit reassessment backlog leaves disability providers carrying debt and fragmented care referrals",
        "body": "The review found NDIS payment delays and benefit reassessment disputes pushing small providers into debt while participants cycle through fragmented referral queues for therapy, clinic visits, and personal care.",
        "labels": ["Benefit", "Debt", "Referral"],
    },
    {
        "number": 16,
        "signal_type": "field_observation",
        "source": "defence-workforce-brief",
        "title": "AUKUS shipyard hiring intensifies housing pressure and care shortages near defence hubs",
        "body": "Local officials warn that defence spending and shipyard expansion are lifting rent and housing costs around Adelaide and Perth, while health care employers lose staff to higher-paying projects and agencies struggle to coordinate training pipelines.",
        "labels": ["Housing", "Care", "Agencies"],
    },
    {
        "number": 17,
        "signal_type": "field_observation",
        "source": "pacific-development-network",
        "title": "Pacific coordination gaps weaken trust in Australia's infrastructure credibility against China offers",
        "body": "Regional agencies say fragmented coordination between Canberra, subnational governments, and contractors slows energy and port pledges, harming trust, credibility, and local engagement as Pacific governments compare faster Chinese financing.",
        "labels": ["Trust", "Coordination", "Credibility"],
    },
]

OBSERVED_OUTCOMES = [
    {
        "label": "housing instability",
        "target": "Shared weakness in housing instability",
        "target_contains": ["housing", "instability"],
        "observed": True,
        "detail": "Australia's sharpest household stress is likely to emerge where rent, mortgage resets, and shelter shortages turn affordability pressure into durable displacement and homelessness.",
    },
    {
        "label": "care access gap",
        "target": "Shared weakness in care access gap",
        "target_contains": ["care", "access"],
        "observed": True,
        "detail": "Health, mental health, disability, and discharge bottlenecks amplify economic shocks by leaving vulnerable households without timely clinic, treatment, and home-care support.",
    },
    {
        "label": "security boundary",
        "target": "Shared weakness in security boundary",
        "target_contains": ["security", "boundary"],
        "observed": True,
        "detail": "Cyber weakness in ports, grids, water, and contractors could turn a geopolitical or trade shock into an existential infrastructure failure for Australia's economy.",
    },
    {
        "label": "trust breakdown",
        "target": "Shared weakness in trust breakdown",
        "target_contains": ["trust", "breakdown"],
        "observed": True,
        "detail": "Policy execution becomes materially harder when misinformation around housing, migration, and energy erodes trust, credibility, engagement, and turnout.",
    },
]

NONCONVERGENT_ISSUES = [
    {
        "number": 101,
        "signal_type": "field_observation",
        "source": "marine-ecology-station",
        "title": "Kelp canopy rebound changes juvenile fish shelter depth on the south reef",
        "body": "Marine biologists recorded more juvenile wrasse sheltering deeper in the water column after a dense kelp season altered light and predator cover.",
        "labels": ["Marine", "Kelp", "Fish"],
    },
    {
        "number": 102,
        "signal_type": "audit",
        "source": "paleontology-dig-team",
        "title": "Triassic bone bed reveals a denser ash layer above the fossil horizon",
        "body": "Site notes show the new trench cut through an unusually compact ash band that may help date the vertebrate layer with better precision.",
        "labels": ["Paleontology", "Triassic", "Ash"],
    },
    {
        "number": 103,
        "signal_type": "feedback",
        "source": "coral-larvae-lab",
        "title": "Coral larvae drift window lengthens during an early warm-current pulse",
        "body": "Researchers observed larvae remaining suspended for longer than usual after a short-lived current shift changed near-surface temperature gradients.",
        "labels": ["Marine", "Coral", "Larvae"],
    },
    {
        "number": 104,
        "signal_type": "other",
        "source": "desert-fossil-survey",
        "title": "Sauropod trackway spacing suggests a slower gait across the dune margin",
        "body": "Track measurements indicate the herd crossed softer sediment than earlier surveys had assumed, changing estimates of body sway and speed.",
        "labels": ["Paleontology", "Sauropod", "Trackway"],
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
        issue["seed_hypothesis"] = "Social media regulation is Australia's primary economic lever."
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

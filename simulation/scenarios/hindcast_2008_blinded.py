"""Blinded hindcast corpus using only signals public before January 2007."""
from __future__ import annotations

import random

REAL_ISSUES = [
    {
        "number": 1,
        "signal_type": "audit",
        "source": "inside-mortgage-finance",
        "title": "Subprime share of new mortgage originations nears one-fifth of the market",
        "body": "Trade tallies show subprime production rising from roughly 8 percent of originations in 2003 to nearly 20 percent in 2006 as lenders reach borrowers with thinner credit files, thinner cushions, and weaker documentation.",
        "labels": ["Mortgage", "Debt", "Income"],
    },
    {
        "number": 2,
        "signal_type": "field_observation",
        "source": "broker-channel-survey",
        "title": "Low-documentation and so-called NINJA loans spread beyond niche programs",
        "body": "Mortgage brokers report wider use of loans requiring little verification of borrower pay, work history, or assets, especially in refinance and investor channels.",
        "labels": ["Income", "Employment", "Mortgage"],
    },
    {
        "number": 3,
        "signal_type": "audit",
        "source": "mortgage-bankers-association",
        "title": "Subprime delinquency and foreclosure starts move higher in late 2006",
        "body": "MBA fourth-quarter data show subprime delinquency above 13 percent, with arrears rising fastest on recent vintages as borrowers struggle to meet monthly debt service.",
        "labels": ["Arrears", "Debt", "Mortgage"],
    },
    {
        "number": 4,
        "signal_type": "audit",
        "source": "federal-reserve-household-credit",
        "title": "Large wave of scheduled payment resets due over the next two years",
        "body": "Industry estimates indicate millions of adjustable loans will recast, lifting monthly obligations for borrowers already stretched on carrying costs and thin buffers.",
        "labels": ["Housing", "Income", "Mortgage"],
    },
    {
        "number": 5,
        "signal_type": "audit",
        "source": "s-and-p-case-shiller",
        "title": "Home-price gauges flatten after a long run-up",
        "body": "Case-Shiller and local market reports show several formerly hot metro areas rolling over after peaking in mid-2006, with year-over-year gains narrowing and some markets posting declines.",
        "labels": ["Housing", "Prices", "Market"],
    },
    {
        "number": 6,
        "signal_type": "audit",
        "source": "national-association-of-realtors",
        "title": "Months of unsold supply rises as buyer demand softens",
        "body": "Realtors report a marked rise in the stock of listed properties and longer selling times, suggesting demand is no longer clearing the market at recent levels.",
        "labels": ["Housing", "Inventory", "Sales"],
    },
    {
        "number": 7,
        "signal_type": "field_observation",
        "source": "realtytrac-investor-watch",
        "title": "Speculative flipping and condo assignment sales remain elevated in boom markets",
        "body": "Analysts tracking Las Vegas, Miami, Phoenix, and inland California say investor turnover remains unusually high, leaving these markets exposed if credit terms tighten.",
        "labels": ["Housing", "Speculation", "Investors"],
    },
    {
        "number": 8,
        "signal_type": "audit",
        "source": "census-housing-vacancy-survey",
        "title": "Record ownership rate sustained by easier underwriting",
        "body": "Researchers note the record rate has been supported by looser standards, allowing borrowers with modest resources and little savings to take on larger obligations.",
        "labels": ["Housing", "Income", "Debt"],
    },
    {
        "number": 9,
        "signal_type": "audit",
        "source": "dealer-balance-sheet-watch",
        "title": "Major dealers operate with leverage ratios that leave little room for error",
        "body": "Balance-sheet reviews show several investment banks financing large structured-finance inventories with leverage above 30 to 1, relying on short-term funding and thin common equity.",
        "labels": ["Security", "Leverage", "Funding"],
    },
    {
        "number": 10,
        "signal_type": "audit",
        "source": "ifr-structured-credit",
        "title": "Structured-credit issuance climbs past half a trillion dollars in 2006",
        "body": "Market tallies put CDO issuance above $500 billion for the year as Wall Street packages mortgage risk into ever more complex securities for yield-hungry buyers.",
        "labels": ["Security", "CDO", "Structured Credit"],
    },
    {
        "number": 11,
        "signal_type": "audit",
        "source": "abx-market-close",
        "title": "ABX subprime mortgage-backed indexes soften into year-end",
        "body": "The lower-rated ABX home-equity tranches began to trade down in late 2006, an early sign that buyers are demanding wider spreads on subprime paper.",
        "labels": ["Security", "ABX", "Pricing"],
    },
    {
        "number": 12,
        "signal_type": "audit",
        "source": "ratings-industry-watch",
        "title": "Senior tranches backed by subprime collateral continue to win triple-A marks",
        "body": "Investors and former ratings staff note that pools of weaker loans are still being carved into top-rated paper, leaving many buyers dependent on model assumptions about limited correlation.",
        "labels": ["Security", "Ratings", "Structured Credit"],
    },
    {
        "number": 13,
        "signal_type": "audit",
        "source": "banking-conduits-monitor",
        "title": "Conduits and SIVs add to off-balance-sheet exposure at major institutions",
        "body": "Banks are sponsoring structured investment vehicles and other conduits that hold mortgage paper beyond the main balance sheet, increasing opaque exposure to funding pressure.",
        "labels": ["Security", "SIV", "Funding"],
    },
    {
        "number": 14,
        "signal_type": "incident",
        "source": "fbi-press-briefing",
        "title": "FBI says mortgage fraud is becoming an epidemic problem",
        "body": "Federal investigators warn that misstatement of income, employment, occupancy, and appraisal values is spreading through the mortgage market and could produce broader credit losses.",
        "labels": ["Income", "Employment", "Fraud"],
    },
    {
        "number": 15,
        "signal_type": "community_report",
        "source": "market-commentary-roundup",
        "title": "Housing correction warnings broaden as a few funds buy protection on subprime paper",
        "body": "Public commentary from Robert Shiller and Nouriel Roubini questions the soft-landing view, while a small number of hedge funds are reportedly buying protection against subprime mortgage-backed paper and weaker home finance.",
        "labels": ["Housing", "Security", "Warning"],
    },
]

OBSERVED_OUTCOMES = [
    {
        "label": "housing instability",
        "target": "Shared weakness in housing instability",
        "target_contains": ["housing", "instability"],
        "observed": True,
        "detail": "The housing bubble burst caused millions of foreclosures, home price drops of 30%+, and mass displacement of homeowners who had been pushed into unsustainable mortgages.",
    },
    {
        "label": "economic fragility",
        "target": "Shared weakness in economic fragility",
        "target_contains": ["economic", "fragility"],
        "observed": True,
        "detail": "Household debt burden, wage stagnation, and income-to-mortgage ratios made millions unable to absorb the rate reset, triggering a consumer spending collapse and deep recession.",
    },
    {
        "label": "security boundary weakness",
        "target": "Shared weakness in security boundary",
        "target_contains": ["security", "boundary"],
        "observed": True,
        "detail": "The financial system's trust boundaries failed — CDO ratings were fraudulent, counterparty risk was opaque, and bank leverage exceeded safe limits, causing cascading institutional failure.",
    },
]

NONCONVERGENT_ISSUES = [
    {
        "number": 101,
        "signal_type": "field_observation",
        "source": "wetland-ecology-notes",
        "title": "Sedge cover thickens along the eastern marsh after a mild autumn",
        "body": "Field teams recorded denser sedge stands and slower open-water flow across the shallow eastern plots during the October survey.",
        "labels": ["Botany", "Wetland", "Sedges"],
    },
    {
        "number": 102,
        "signal_type": "community_report",
        "source": "orchid-conservation-circle",
        "title": "Native orchid flowering window arrived earlier on shaded slopes",
        "body": "Volunteers observed the first blooms nearly two weeks ahead of the usual schedule on the cooler side of the reserve.",
        "labels": ["Botany", "Orchid", "Phenology"],
    },
    {
        "number": 103,
        "signal_type": "field_observation",
        "source": "forest-canopy-survey",
        "title": "Moss recovery improves moisture retention on old cedar trunks",
        "body": "Surveyors noted a thicker moss layer on mature cedar bark after the wet season, with insects lingering longer beneath the canopy.",
        "labels": ["Ecology", "Moss", "Forest"],
    },
    {
        "number": 104,
        "signal_type": "other",
        "source": "prairie-seed-trial",
        "title": "Switchgrass plots showed stronger germination in the cooler north field",
        "body": "Seed-trial notes indicate more even emergence where spring temperatures stayed below the southern plots for several extra days.",
        "labels": ["Ecology", "Grassland", "Seeds"],
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
        issue["seed_hypothesis"] = "Y2K-era IT infrastructure upgrades are the primary systemic risk."
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

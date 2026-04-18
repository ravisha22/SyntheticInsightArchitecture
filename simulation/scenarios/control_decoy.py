"""Decoy-seed control for blinded SIA experiments."""
from __future__ import annotations

from simulation.scenarios.pandas_real import (
    DEFAULT_LIMIT,
    build_seed_events,
    build_pandas_scenario,
    derive_neutral_seed_tags,
    estimate_seed_cycle,
)

WRONG_SEEDS = [
    {
        "description": "pandas should switch to Dask for parallel processing",
        "tags": ["performance", "memory", "parallel", "scale"],
        "cycle": 6,
    },
    {
        "description": "pandas should adopt SQLAlchemy-style ORM for DataFrames",
        "tags": ["indexing", "API", "semantics", "query"],
        "cycle": 10,
    },
    {
        "description": "pandas should deprecate DataFrame and use only Series",
        "tags": ["API", "dtype", "semantics", "indexing"],
        "cycle": 14,
    },
]
NEUTRAL_DESCRIPTIONS = [
    "pandas internal memory model needs rethinking",
    "indexing API has too many inconsistent code paths",
    "dtype coercion rules need unification",
]


def build_decoy_seed_scenario(limit: int = DEFAULT_LIMIT) -> dict:
    base = build_pandas_scenario(limit=limit, include_data_derived_seeds=False, shuffle_tags=False)
    issues = base["issues"]

    neutral_specs = []
    for offset, description in enumerate(NEUTRAL_DESCRIPTIONS, start=1):
        tags = derive_neutral_seed_tags(issues, description)
        neutral_specs.append(
            {
                "description": description,
                "tags": tags,
                "cycle": estimate_seed_cycle(issues, tags, fallback=4 + offset * 4),
            }
        )

    events = list(base["events"])
    events.extend(build_seed_events(WRONG_SEEDS))
    events.extend(build_seed_events(neutral_specs))
    events.sort(key=lambda event: (event["cycle"], event["type"] != "tension"))

    return {
        "issues": issues,
        "events": events,
        "wrong_seeds": WRONG_SEEDS,
        "neutral_seeds": neutral_specs,
    }

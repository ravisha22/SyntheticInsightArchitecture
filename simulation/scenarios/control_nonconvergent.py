"""Non-convergent corpus control for blinded SIA experiments."""
from __future__ import annotations

from simulation.scenarios.pandas_real import (
    build_data_derived_seed_specs,
    build_seed_events,
    fetch_closed_issues,
    issue_to_event,
)


def build_nonconvergent_scenario(limit: int = 100) -> dict:
    issues = fetch_closed_issues(
        repo="psf/requests",
        limit=limit,
        cache_name=f"requests_real_{limit}",
    )
    seed_specs = build_data_derived_seed_specs(issues, max_seeds=6, min_support=4)
    events = [issue_to_event(issue) for issue in issues]
    events.extend(build_seed_events(seed_specs))
    events.sort(key=lambda event: (event["cycle"], event["type"] != "tension"))
    return {
        "issues": issues,
        "events": events,
        "seed_specs": seed_specs,
    }

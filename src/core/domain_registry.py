"""Domain profile registry."""

from __future__ import annotations

from pathlib import Path

import yaml

from .persona_ensemble import DIMENSIONS


def load_domain_profile(domain_name: str) -> dict:
    """Load a YAML domain profile by name."""

    path = Path(__file__).parents[2] / "configs" / "domains" / f"{domain_name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown domain profile {domain_name!r} at {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Domain profile {domain_name!r} must deserialize to a mapping")

    if payload.get("domain") != domain_name:
        raise ValueError(f"Domain profile {path.name} declares domain {payload.get('domain')!r}, expected {domain_name!r}")

    if "expert_persona" not in payload:
        raise ValueError(f"Domain profile {domain_name!r} is missing expert_persona")

    expert_prior = payload.get("expert_prior")
    if not isinstance(expert_prior, dict):
        raise ValueError(f"Domain profile {domain_name!r} is missing a valid expert_prior map")

    missing_dimensions = [dimension for dimension in DIMENSIONS if dimension not in expert_prior]
    extra_dimensions = [dimension for dimension in expert_prior if dimension not in DIMENSIONS]
    if missing_dimensions or extra_dimensions:
        raise ValueError(
            f"Domain profile {domain_name!r} has invalid expert_prior keys "
            f"(missing={missing_dimensions}, extra={extra_dimensions})"
        )

    normalized = dict(payload)
    normalized["expert_prior"] = {dimension: float(expert_prior[dimension]) for dimension in DIMENSIONS}
    if "benchmark" not in normalized and "primary_endpoint" in normalized:
        normalized["benchmark"] = normalized["primary_endpoint"]
    if "primary_endpoint" not in normalized and "benchmark" in normalized:
        normalized["primary_endpoint"] = normalized["benchmark"]
    return normalized

"""Domain profile registry."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_domain_profile(domain_name: str) -> dict:
    """Load a YAML domain profile by name."""

    path = Path(__file__).parents[2] / "configs" / "domains" / f"{domain_name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))

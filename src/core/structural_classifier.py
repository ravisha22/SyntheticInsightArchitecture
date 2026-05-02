"""Structural signal classifiers for SIA Phase 2."""

from __future__ import annotations

import re
from typing import Any

from .persona_ensemble import DIMENSIONS, META_FEATURES


class MockClassifier:
    """Deterministic classifier using keyword rules."""

    DIMENSION_KEYWORDS = {
        "physical_safety": {
            "positive": [
                "peace",
                "ceasefire",
                "safety",
                "protection",
                "rescue",
                "secure",
                "recovered",
                "vaccin*",
                "evacuat*",
            ],
            "negative": [
                "war",
                "death",
                "violence",
                "attack",
                "bomb",
                "shooting",
                "kill",
                "injury",
                "outbreak",
                "missile",
                "shell*",
                "explosion",
                "epidem*",
                "cyberattack",
            ],
        },
        "economic_stability": {
            "positive": ["growth", "jobs", "stable", "investment", "affordable", "recovery", "profit", "stabiliz*", "wage*"],
            "negative": [
                "inflation",
                "layoff",
                "debt",
                "recession",
                "unemployment",
                "bankrupt",
                "poverty",
                "sanction*",
                "tariff*",
                "default",
            ],
        },
        "institutional_trust": {
            "positive": [
                "reliable",
                "compliance",
                "transparent",
                "court",
                "audit",
                "verified",
                "governance",
                "oversight",
                "accountab*",
            ],
            "negative": ["corruption", "fraud", "breach", "failure", "outage", "scandal", "misconduct", "coup", "cover-up"],
        },
        "social_cohesion": {
            "positive": ["community", "solidarity", "cooperation", "support", "inclusion", "unity", "reconciliation"],
            "negative": ["polarization", "riot", "hate", "division", "discrimination", "conflict", "sectarian"],
        },
        "individual_autonomy": {
            "positive": [
                "rights",
                "freedom",
                "privacy",
                "choice",
                "agency",
                "consent",
                "self-determination",
                "legali*",
                "decriminali*",
            ],
            "negative": ["ban", "censorship", "surveillance", "restriction", "coercion", "detention", "curfew", "shutdown"],
        },
        "collective_welfare": {
            "positive": ["equity", "care", "access", "benefit", "welfare", "coverage", "aid", "relief", "shelter"],
            "negative": ["exclusion", "shortage", "inequality", "hunger", "homelessness", "neglect", "famine", "displac*"],
        },
        "knowledge_capability": {
            "positive": ["research", "education", "innovation", "science", "fix", "learning", "tooling", "breakthrough", "patch"],
            "negative": ["bug", "regression", "misinformation", "ignorance", "failure", "broken", "crash", "exploit", "vulnera*"],
        },
        "environmental_continuity": {
            "positive": ["conservation", "renewable", "clean", "sustainable", "restoration", "biodiversity", "reforest*"],
            "negative": [
                "pollution",
                "wildfire",
                "flood",
                "drought",
                "emission",
                "contamination",
                "collapse",
                "heatwave",
                "deforestation",
                "oil spill",
            ],
        },
    }

    META_KEYWORDS = {
        "urgency": ["urgent", "immediate", "breaking", "now", "critical", "today", "alert", "emergency", "deadline"],
        "scale": ["global", "nationwide", "widespread", "millions", "systemic", "platform-wide", "all users", "regional"],
        "irreversibility": ["irreversible", "permanent", "long-term", "extinction", "fatal", "destroyed", "locked-in"],
        "cascade_risk": ["cascade", "spillover", "domino", "chain reaction", "dependency", "propagat", "knock-on", "ripple"],
        "evidence_quality": ["study", "report", "data", "official", "confirmed", "verified", "peer-reviewed", "analysis", "survey"],
        "actionability": ["plan", "deploy", "mitigate", "respond", "fix", "intervention", "roadmap", "rollback", "patch"],
    }

    def _combine_text(self, signal: dict[str, Any]) -> str:
        title = str(signal.get("title", ""))
        body = str(signal.get("body", ""))
        tags = " ".join(str(tag) for tag in signal.get("tags", []))
        return f"{title} {body} {tags}".lower()

    def _count_matches(self, text: str, keywords: list[str]) -> int:
        total = 0
        for keyword in keywords:
            if keyword.endswith("*"):
                stem = keyword[:-1]
                total += len(re.findall(rf"\b{re.escape(stem)}\w*\b", text))
            elif " " in keyword or "-" in keyword or keyword == "propagat":
                total += len(re.findall(re.escape(keyword), text))
            else:
                total += len(re.findall(rf"\b{re.escape(keyword)}\w*\b", text))
        return total

    def _score_dimension(self, text: str, positive: list[str], negative: list[str]) -> float:
        pos = self._count_matches(text, positive)
        neg = self._count_matches(text, negative)
        if pos == 0 and neg == 0:
            return 0.0
        return max(-1.0, min(1.0, (pos - neg) / (pos + neg)))

    def _score_meta(self, text: str, keywords: list[str]) -> float:
        matches = self._count_matches(text, keywords)
        if matches == 0:
            return 0.0
        return min(1.0, 0.35 + matches * 0.2)

    def classify(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Return dimension and meta vectors."""

        text = self._combine_text(signal)
        dimensions = {
            dimension: self._score_dimension(text, rules["positive"], rules["negative"])
            for dimension, rules in self.DIMENSION_KEYWORDS.items()
        }
        meta = {feature: self._score_meta(text, keywords) for feature, keywords in self.META_KEYWORDS.items()}
        return {
            "signal_id": signal.get("signal_id") or signal.get("id") or signal.get("title", "signal"),
            "title": signal.get("title", ""),
            "body": signal.get("body", ""),
            "tags": signal.get("tags", []),
            "dimensions": dimensions,
            "meta": meta,
        }


class LLMClassifier:
    """LLM-backed structural classifier."""

    def __init__(self, llm_adapter):
        self.llm_adapter = llm_adapter

    def _clamp(self, value: Any, lower: float, upper: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return max(lower, min(upper, numeric))

    def classify(self, signal: dict[str, Any]) -> dict[str, Any]:
        system_prompt = (
            "You are a structural signal classifier for Synthetic Insight Architecture. "
            "Return JSON with two objects: dimensions and meta. "
            "Dimensions must include the 8 keys "
            f"{', '.join(DIMENSIONS)} with values in [-1.0, 1.0]. "
            "Meta must include the 6 keys "
            f"{', '.join(META_FEATURES)} with values in [0.0, 1.0]."
        )
        user_prompt = (
            f"Title: {signal.get('title', '')}\n"
            f"Body: {signal.get('body', '')}\n"
            f"Tags: {', '.join(str(tag) for tag in signal.get('tags', []))}\n"
            "Assess direct impact direction on each dimension plus urgency, scale, irreversibility, "
            "cascade risk, evidence quality, and actionability."
        )
        response = self.llm_adapter.analyze(
            system_prompt,
            user_prompt,
            json_schema={
                "type": "object",
                "properties": {
                    "dimensions": {"type": "object"},
                    "meta": {"type": "object"},
                },
                "required": ["dimensions", "meta"],
            },
        )
        response = response if isinstance(response, dict) else {}
        dimensions = response.get("dimensions", response)
        meta = response.get("meta", {})
        if not isinstance(dimensions, dict):
            dimensions = {}
        if not isinstance(meta, dict):
            meta = {}
        return {
            "signal_id": signal.get("signal_id") or signal.get("id") or signal.get("title", "signal"),
            "title": signal.get("title", ""),
            "body": signal.get("body", ""),
            "tags": signal.get("tags", []),
            "dimensions": {
                dimension: self._clamp(dimensions.get(dimension, 0.0), -1.0, 1.0) for dimension in DIMENSIONS
            },
            "meta": {feature: self._clamp(meta.get(feature, 0.0), 0.0, 1.0) for feature in META_FEATURES},
        }

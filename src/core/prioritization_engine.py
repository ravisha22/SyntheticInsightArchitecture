"""Phase 2 prioritisation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .persona_ensemble import DIMENSIONS, META_FEATURES, PersonaEnsemble

IMPACT_WEIGHTS = {
    "urgency": 0.25,
    "scale": 0.20,
    "irreversibility": 0.20,
    "cascade_risk": 0.20,
    "evidence_quality": 0.15,
}


@dataclass
class PrioritizationResult:
    ranked_signals: list[dict[str, Any]]
    selected_signals: list[dict[str, Any]]
    portfolio_mood: dict[str, Any]


def normalize_prior(expert_prior: dict[str, float] | None) -> dict[str, float]:
    """Normalize expert priors to mean 1.0."""

    prior = {dimension: float((expert_prior or {}).get(dimension, 1.0)) for dimension in DIMENSIONS}
    mean_value = float(np.mean(list(prior.values()))) if prior else 1.0
    if mean_value == 0:
        return {dimension: 1.0 for dimension in DIMENSIONS}
    return {dimension: value / mean_value for dimension, value in prior.items()}


class PrioritizationEngine:
    """Scores classified signals with expert priors and persona diversity."""

    def __init__(self, ensemble: PersonaEnsemble, domain_profile: dict):
        self.ensemble = ensemble
        self.domain_profile = domain_profile
        self.expert_prior = normalize_prior(domain_profile.get("expert_prior", {}))
        self._expert_prior_vector = np.array([self.expert_prior[dimension] for dimension in DIMENSIONS], dtype=float)

    def _zscore(self, values: list[float]) -> list[float]:
        array = np.array(values, dtype=float)
        if len(array) == 0:
            return []
        std = float(np.std(array))
        if std == 0:
            return [0.0 for _ in array]
        mean = float(np.mean(array))
        return [float((value - mean) / std) for value in array]

    def _impact(self, meta: dict[str, float]) -> float:
        return float(sum(IMPACT_WEIGHTS[key] * float(meta.get(key, 0.0)) for key in IMPACT_WEIGHTS))

    def _cluster_breakdown(self, scores: dict[str, float]) -> dict[str, Any]:
        cluster_means = self.ensemble.cluster_means(scores)
        highest = max(cluster_means.items(), key=lambda item: item[1])
        lowest = min(cluster_means.items(), key=lambda item: item[1])
        return {
            "means": cluster_means,
            "highest_cluster": {"name": highest[0], "score": float(highest[1])},
            "lowest_cluster": {"name": lowest[0], "score": float(lowest[1])},
        }

    def _portfolio_mood(self, ranked_signals: list[dict[str, Any]]) -> dict[str, Any]:
        alpha = 2.0 / (7.0 + 1.0)
        ema = 0.0
        contested_share = 0.0
        if ranked_signals:
            contested_share = sum(1 for signal in ranked_signals if signal["category"] == "contested_priority") / len(
                ranked_signals
            )
        for signal in ranked_signals:
            polarity = float(signal["polarity"])
            confidence = float(signal["sign_agreement"])
            trend_effect = polarity * float(signal["priority_raw"]) * confidence
            ema = alpha * trend_effect + (1.0 - alpha) * ema
        if contested_share > 0.4:
            label = "transitional"
        elif ema >= 0.25:
            label = "constructive"
        elif ema <= -0.25:
            label = "concerning"
        else:
            label = "cautious"
        return {"score": float(ema), "label": label, "contested_share": float(contested_share)}

    def prioritize(self, classified_signals: list[dict], budget: int = 10) -> PrioritizationResult:
        """Prioritize a batch of classified signals."""

        raw_results: list[dict[str, Any]] = []
        for signal in classified_signals:
            signal_vector = np.array([float(signal["dimensions"].get(dimension, 0.0)) for dimension in DIMENSIONS], dtype=float)
            meta_vector = np.array([float(signal["meta"].get(feature, 0.0)) for feature in META_FEATURES], dtype=float)
            expert_weighted_signal = signal_vector * self._expert_prior_vector
            scores = self.ensemble.score_signal(expert_weighted_signal, meta_vector)
            score_values = np.array(list(scores.values()), dtype=float)
            central_tendency = self.ensemble.compute_convergence(scores)
            contestedness = self.ensemble.compute_contestedness(scores)
            sign_agreement = self.ensemble.compute_sign_agreement(scores)
            impact = self._impact(signal["meta"])
            actionability = float(signal["meta"].get("actionability", 0.0))
            polarity = int(np.sign(np.median(score_values)))
            raw_results.append(
                {
                    "signal_id": signal.get("signal_id") or signal.get("id") or signal.get("title", "signal"),
                    "title": signal.get("title", ""),
                    "priority_raw": float(central_tendency * impact * actionability),
                    "contest_raw": float(contestedness * impact),
                    "central_tendency": float(central_tendency),
                    "contestedness": float(contestedness),
                    "sign_agreement": float(sign_agreement),
                    "impact": float(impact),
                    "actionability": float(actionability),
                    "polarity": polarity,
                    "scores": scores,
                    "cluster_breakdown": self._cluster_breakdown(scores),
                    "expert_weighted_dimensions": {
                        dimension: float(value) for dimension, value in zip(DIMENSIONS, expert_weighted_signal)
                    },
                }
            )

        priority_scores = self._zscore([result["priority_raw"] for result in raw_results])
        contest_scores = self._zscore([result["contest_raw"] for result in raw_results])

        ranked_signals: list[dict[str, Any]] = []
        for result, priority_score, contest_score in zip(raw_results, priority_scores, contest_scores):
            enriched = dict(result)
            enriched["priority_score"] = float(priority_score)
            enriched["contest_score"] = float(contest_score)
            enriched["category"] = self.ensemble.classify_signal(priority_score, contest_score, enriched["sign_agreement"])
            ranked_signals.append(enriched)

        ranked_signals.sort(key=lambda signal: (signal["priority_score"], signal["priority_raw"]), reverse=True)
        selected_signals = ranked_signals[:budget]
        return PrioritizationResult(
            ranked_signals=ranked_signals,
            selected_signals=selected_signals,
            portfolio_mood=self._portfolio_mood(ranked_signals),
        )

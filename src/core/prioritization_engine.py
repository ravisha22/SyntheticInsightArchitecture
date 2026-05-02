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

    def _uncertainty_vector(self, signal: dict[str, Any], key: str, labels: list[str]) -> np.ndarray:
        values = signal.get(key) or {}
        return np.array([float(values.get(label, 0.0)) for label in labels], dtype=float)

    def _cluster_breakdown(self, scores: dict[str, float]) -> dict[str, Any]:
        cluster_means = self.ensemble.cluster_means(scores)
        highest = max(cluster_means.items(), key=lambda item: item[1])
        lowest = min(cluster_means.items(), key=lambda item: item[1])
        return {
            "means": cluster_means,
            "highest_cluster": {"name": highest[0], "score": float(highest[1])},
            "lowest_cluster": {"name": lowest[0], "score": float(lowest[1])},
        }

    def _final_uncertainty(self, signal: dict[str, Any]) -> float:
        dimension_uncertainty = self._uncertainty_vector(signal, "dimension_uncertainty", DIMENSIONS)
        meta_uncertainty = self._uncertainty_vector(signal, "meta_uncertainty", META_FEATURES)
        if not np.any(dimension_uncertainty) and not np.any(meta_uncertainty):
            return 0.0

        effective_dimension_weights = self.ensemble.dimension_matrix * self._expert_prior_vector[np.newaxis, :]
        raw_uncertainty = np.sqrt(
            (effective_dimension_weights**2) @ (dimension_uncertainty**2)
            + (self.ensemble.meta_matrix**2) @ (meta_uncertainty**2)
        )
        return float(np.sqrt(np.mean(raw_uncertainty**2)))

    def _rank_intervals(self, raw_results: list[dict[str, Any]]) -> dict[str, tuple[float, float] | None]:
        if not raw_results:
            return {}

        uncertainties = np.array([float(result["final_uncertainty"]) for result in raw_results], dtype=float)
        if not np.any(uncertainties):
            return {str(result["signal_id"]): None for result in raw_results}

        means = np.array([float(result["priority_raw"]) for result in raw_results], dtype=float)
        rng = np.random.default_rng(0)
        samples = rng.normal(loc=means, scale=uncertainties, size=(1000, len(raw_results)))
        ranks = np.empty_like(samples, dtype=float)
        for sample_idx, sample in enumerate(samples):
            ordering = np.argsort(-sample, kind="stable")
            sample_ranks = np.empty(len(raw_results), dtype=float)
            sample_ranks[ordering] = np.arange(1, len(raw_results) + 1, dtype=float)
            ranks[sample_idx] = sample_ranks

        return {
            str(result["signal_id"]): (
                float(np.percentile(ranks[:, idx], 5)),
                float(np.percentile(ranks[:, idx], 95)),
            )
            for idx, result in enumerate(raw_results)
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

        if budget < 0:
            raise ValueError("budget must be non-negative")

        raw_results: list[dict[str, Any]] = []
        for signal in classified_signals:
            dimensions = signal.get("dimensions") or {}
            meta = signal.get("meta") or {}
            signal_vector = np.array([float(dimensions.get(dimension, 0.0)) for dimension in DIMENSIONS], dtype=float)
            meta_vector = np.array([float(meta.get(feature, 0.0)) for feature in META_FEATURES], dtype=float)
            expert_weighted_signal = signal_vector * self._expert_prior_vector
            scores = self.ensemble.score_signal(expert_weighted_signal, meta_vector)
            score_values = np.array(list(scores.values()), dtype=float)
            cluster_breakdown = self._cluster_breakdown(scores)
            central_tendency = self.ensemble.compute_central_tendency(scores)
            convergence = self.ensemble.compute_convergence(scores)
            contestedness = self.ensemble.compute_contestedness(scores)
            sign_agreement = self.ensemble.compute_sign_agreement(scores)
            impact = self._impact(meta)
            actionability = float(meta.get("actionability", 0.0))
            polarity = int(np.sign(np.median(score_values)))
            raw_results.append(
                {
                    "signal_id": signal.get("signal_id") or signal.get("id") or signal.get("title", "signal"),
                    "title": signal.get("title", ""),
                    "priority_raw": float(central_tendency * impact * actionability),
                    "contest_raw": float(contestedness * impact),
                    "central_tendency": float(central_tendency),
                    "convergence": float(convergence),
                    "contestedness": float(contestedness),
                    "sign_agreement": float(sign_agreement),
                    "impact": float(impact),
                    "actionability": float(actionability),
                    "polarity": polarity,
                    "scores": scores,
                    "cluster_breakdown": cluster_breakdown,
                    "cluster_means": cluster_breakdown["means"],
                    "final_uncertainty": self._final_uncertainty(signal),
                    "expert_weighted_dimensions": {
                        dimension: float(value) for dimension, value in zip(DIMENSIONS, expert_weighted_signal)
                    },
                }
            )

        priority_scores = self._zscore([result["priority_raw"] for result in raw_results])
        contest_scores = self._zscore([result["contest_raw"] for result in raw_results])
        central_tendency_scores = self._zscore([result["central_tendency"] for result in raw_results])
        impact_scores = self._zscore([result["impact"] for result in raw_results])
        cluster_score_matrix = {
            cluster: self._zscore([result["cluster_means"][cluster] for result in raw_results])
            for cluster in self.ensemble.cluster_members
        }
        rank_intervals = self._rank_intervals(raw_results)

        ranked_signals: list[dict[str, Any]] = []
        for idx, (result, priority_score, contest_score, central_tendency_score, impact_score) in enumerate(
            zip(raw_results, priority_scores, contest_scores, central_tendency_scores, impact_scores)
        ):
            enriched = dict(result)
            cluster_mean_scores = {
                cluster: float(cluster_score_matrix[cluster][idx]) for cluster in self.ensemble.cluster_members
            }
            max_cluster_score = max(cluster_mean_scores.values(), default=0.0)
            enriched["priority_score"] = float(priority_score)
            enriched["contest_score"] = float(contest_score)
            enriched["central_tendency_score"] = float(central_tendency_score)
            enriched["impact_score"] = float(impact_score)
            enriched["cluster_mean_scores"] = cluster_mean_scores
            enriched["max_cluster_score"] = float(max_cluster_score)
            enriched["rank_interval_5_95"] = rank_intervals.get(str(result["signal_id"]))
            enriched["category"] = self.ensemble.classify_signal(
                central_tendency_score=float(central_tendency_score),
                impact_score=float(impact_score),
                sign_agreement=enriched["sign_agreement"],
                max_cluster_score=float(max_cluster_score),
            )
            ranked_signals.append(enriched)

        ranked_signals.sort(key=lambda signal: (signal["priority_score"], signal["priority_raw"]), reverse=True)
        selected_signals = ranked_signals[:budget]
        return PrioritizationResult(
            ranked_signals=ranked_signals,
            selected_signals=selected_signals,
            portfolio_mood=self._portfolio_mood(ranked_signals),
        )

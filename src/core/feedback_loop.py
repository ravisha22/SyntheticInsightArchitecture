"""Outcome feedback and calibration for later phases."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import exp

import numpy as np

from .persona_ensemble import PersonaEnsemble


@dataclass(frozen=True)
class OutcomeRecord:
    signal_id: str
    outcome_score: float
    archetype_scores: dict[str, float]
    observed_at: datetime


class FeedbackLoop:
    """Domain-local bounded multiplicative weight updates with cluster projection."""

    def __init__(
        self,
        ensemble: PersonaEnsemble,
        learning_rate: float = 0.1,
        weight_floor: float = 0.02,
        weight_cap: float = 0.05,
        min_observations: int = 10,
    ):
        self.ensemble = ensemble
        self.learning_rate = float(learning_rate)
        self.weight_floor = float(weight_floor)
        self.weight_cap = float(weight_cap)
        self.min_observations = int(min_observations)
        self.outcomes: dict[str, list[OutcomeRecord]] = defaultdict(list)
        self.domain_weights: dict[str, dict[str, float]] = {}
        self.update_history: dict[str, list[dict[str, object]]] = defaultdict(list)

    def _baseline_weights(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        target_cluster_weight = 1.0 / self.ensemble.cluster_count
        for cluster, archetype_ids in self.ensemble.cluster_members.items():
            if not archetype_ids:
                raise ValueError(f"Cluster {cluster!r} has no archetypes")
            per_archetype_weight = target_cluster_weight / len(archetype_ids)
            for archetype_id in archetype_ids:
                weights[archetype_id] = float(per_archetype_weight)
        return weights

    def _ensure_domain_weights(self, domain: str) -> dict[str, float]:
        if domain not in self.domain_weights:
            self.domain_weights[domain] = self._baseline_weights()
        return dict(self.domain_weights[domain])

    def _normalize_archetype_scores(self, archetype_scores: dict[str, float] | None) -> dict[str, float]:
        if archetype_scores is None:
            return {}

        missing = [archetype_id for archetype_id in self.ensemble.archetype_ids if archetype_id not in archetype_scores]
        extra = [archetype_id for archetype_id in archetype_scores if archetype_id not in self.ensemble.archetype_ids]
        if missing or extra:
            raise ValueError(f"archetype_scores must contain all and only ensemble archetypes (missing={missing}, extra={extra})")

        return {
            archetype_id: float(archetype_scores[archetype_id]) for archetype_id in self.ensemble.archetype_ids
        }

    def record_outcome(
        self,
        signal_id: str,
        outcome_score: float,
        domain: str = "default",
        archetype_scores: dict[str, float] | None = None,
        observed_at: datetime | None = None,
    ):
        """Record an observed outcome and optional per-archetype scores for calibration."""

        self.outcomes[domain].append(
            OutcomeRecord(
                signal_id=signal_id,
                outcome_score=float(outcome_score),
                archetype_scores=self._normalize_archetype_scores(archetype_scores),
                observed_at=observed_at or datetime.now(UTC),
            )
        )

    def _pearson_reward(self, predictions: list[float], outcomes: list[float]) -> float:
        if len(predictions) < 2:
            return 0.0

        prediction_array = np.array(predictions, dtype=float)
        outcome_array = np.array(outcomes, dtype=float)
        if np.isclose(float(np.std(prediction_array)), 0.0) or np.isclose(float(np.std(outcome_array)), 0.0):
            return 0.0

        correlation = np.corrcoef(prediction_array, outcome_array)[0, 1]
        if np.isnan(correlation):
            return 0.0
        return float(correlation)

    def update_weights(self, window_days: int = 30, domain: str = "default", as_of: datetime | None = None):
        """Update persona weights from the rolling outcome window."""

        if window_days <= 0:
            raise ValueError("window_days must be positive")

        current_weights = self._ensure_domain_weights(domain)
        cutoff = (as_of or datetime.now(UTC)) - timedelta(days=window_days)
        window_records = [
            record for record in self.outcomes.get(domain, []) if record.observed_at >= cutoff and record.archetype_scores
        ]
        if len(window_records) < self.min_observations:
            return {
                "window_days": int(window_days),
                "observed_signals": len(window_records),
                "status": "insufficient_data",
                "domain": domain,
                "w_old": current_weights,
                "w_final": current_weights,
            }

        outcomes = [record.outcome_score for record in window_records]
        rewards = {
            archetype_id: self._pearson_reward(
                [record.archetype_scores[archetype_id] for record in window_records],
                outcomes,
            )
            for archetype_id in self.ensemble.archetype_ids
        }
        w_raw = {
            archetype_id: float(current_weights[archetype_id] * exp(self.learning_rate * rewards[archetype_id]))
            for archetype_id in self.ensemble.archetype_ids
        }
        w_clipped = {
            archetype_id: float(min(self.weight_cap, max(self.weight_floor, w_raw[archetype_id])))
            for archetype_id in self.ensemble.archetype_ids
        }

        w_final: dict[str, float] = {}
        target_cluster_weight = 1.0 / self.ensemble.cluster_count
        for cluster, archetype_ids in self.ensemble.cluster_members.items():
            cluster_sum = float(sum(w_clipped[archetype_id] for archetype_id in archetype_ids))
            if np.isclose(cluster_sum, 0.0):
                projected = target_cluster_weight / len(archetype_ids)
                for archetype_id in archetype_ids:
                    w_final[archetype_id] = float(projected)
                continue

            projection = target_cluster_weight / cluster_sum
            for archetype_id in archetype_ids:
                w_final[archetype_id] = float(w_clipped[archetype_id] * projection)

        audit_record = {
            "window_days": int(window_days),
            "observed_signals": len(window_records),
            "status": "updated",
            "domain": domain,
            "w_old": current_weights,
            "reward": rewards,
            "w_raw": w_raw,
            "w_clipped": w_clipped,
            "w_final": w_final,
        }
        self.domain_weights[domain] = dict(w_final)
        self.update_history[domain].append(audit_record)
        return audit_record

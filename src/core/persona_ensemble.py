"""Persona ensemble loading, validation, and scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import yaml

DIMENSIONS = [
    "physical_safety",
    "economic_stability",
    "institutional_trust",
    "social_cohesion",
    "individual_autonomy",
    "collective_welfare",
    "knowledge_capability",
    "environmental_continuity",
]

META_FEATURES = [
    "urgency",
    "scale",
    "irreversibility",
    "cascade_risk",
    "evidence_quality",
    "actionability",
]

SCHWARTZ_DIMENSION_LOADINGS = {
    "Self-Direction": {"individual_autonomy": 0.9, "knowledge_capability": 0.8, "institutional_trust": 0.2},
    "Stimulation": {"individual_autonomy": 0.8, "knowledge_capability": 0.6, "economic_stability": 0.2},
    "Hedonism": {"individual_autonomy": 0.6, "economic_stability": 0.3, "social_cohesion": 0.1},
    "Achievement": {
        "economic_stability": 0.7,
        "knowledge_capability": 0.7,
        "institutional_trust": 0.3,
        "individual_autonomy": 0.3,
    },
    "Power": {"institutional_trust": 0.7, "economic_stability": 0.6, "physical_safety": 0.4, "social_cohesion": 0.2},
    "Security": {"physical_safety": 0.9, "economic_stability": 0.8, "institutional_trust": 0.6, "social_cohesion": 0.3},
    "Conformity": {
        "institutional_trust": 0.8,
        "social_cohesion": 0.7,
        "physical_safety": 0.4,
        "collective_welfare": 0.3,
    },
    "Tradition": {
        "social_cohesion": 0.6,
        "environmental_continuity": 0.6,
        "institutional_trust": 0.5,
        "collective_welfare": 0.3,
    },
    "Benevolence": {
        "collective_welfare": 0.9,
        "social_cohesion": 0.8,
        "physical_safety": 0.4,
        "institutional_trust": 0.2,
    },
    "Universalism": {
        "collective_welfare": 0.9,
        "environmental_continuity": 0.8,
        "institutional_trust": 0.6,
        "social_cohesion": 0.5,
        "individual_autonomy": 0.4,
    },
}

DOMINANCE_COEFFICIENTS = {
    1: (1.0,),
    2: (0.6, 0.4),
    3: (0.5, 0.3, 0.2),
}

VALIDATION_TOLERANCE = 1e-9


@dataclass(frozen=True)
class PersonaArchetype:
    """One scored persona in the ensemble."""

    archetype_id: str
    name: str
    cluster: str
    dominant_values: list[str]
    dimension_weights: dict[str, float]
    dimension_adjustments: dict[str, float]
    meta_weights: dict[str, float]


class PersonaEnsemble:
    """Matrix-backed persona ensemble."""

    def __init__(
        self,
        archetypes: list[PersonaArchetype],
        clusters: dict[str, list[str]],
        dimensions: Iterable[str] = DIMENSIONS,
        meta_features: Iterable[str] = META_FEATURES,
        framework: str = "schwartz_10_value",
    ):
        self.dimensions = list(dimensions)
        self.meta_features = list(meta_features)
        self.framework = framework
        self.archetypes = archetypes
        self.cluster_members = {cluster: list(ids) for cluster, ids in clusters.items()}
        self.archetype_ids = [archetype.archetype_id for archetype in archetypes]
        self.archetype_index = {archetype_id: idx for idx, archetype_id in enumerate(self.archetype_ids)}

        self.dimension_matrix = np.array(
            [[archetype.dimension_weights[dimension] for dimension in self.dimensions] for archetype in archetypes],
            dtype=float,
        )
        self.meta_matrix = np.array(
            [[archetype.meta_weights[feature] for feature in self.meta_features] for archetype in archetypes],
            dtype=float,
        )
        self.cluster_indices = {
            cluster: np.array([self.archetype_index[archetype_id] for archetype_id in archetype_ids], dtype=int)
            for cluster, archetype_ids in self.cluster_members.items()
        }

    @property
    def cluster_count(self) -> int:
        return len(self.cluster_members)

    def _coerce_vector(self, values: dict[str, float] | Iterable[float], labels: list[str]) -> np.ndarray:
        if isinstance(values, dict):
            return np.array([float(values.get(label, 0.0)) for label in labels], dtype=float)
        array = np.array(list(values), dtype=float)
        if array.shape[0] != len(labels):
            raise ValueError(f"Expected {len(labels)} values, got {array.shape[0]}")
        return array

    def score_signal(
        self,
        signal_vector: dict[str, float] | Iterable[float],
        meta_vector: dict[str, float] | Iterable[float],
    ) -> dict[str, float]:
        """Return per-archetype scores for one signal."""

        signal = self._coerce_vector(signal_vector, self.dimensions)
        meta = self._coerce_vector(meta_vector, self.meta_features)
        scores = self.dimension_matrix @ signal + self.meta_matrix @ meta
        return {archetype_id: float(score) for archetype_id, score in zip(self.archetype_ids, scores)}

    def cluster_means(self, scores: dict[str, float] | Iterable[float]) -> dict[str, float]:
        """Mean score per cluster."""

        score_vector = self._coerce_vector(scores, self.archetype_ids)
        return {
            cluster: float(np.mean(score_vector[indices])) if len(indices) else 0.0
            for cluster, indices in self.cluster_indices.items()
        }

    def compute_convergence(self, scores: dict[str, float] | Iterable[float]) -> float:
        """Mean signed cluster agreement per the Phase 2 spec."""

        cluster_values = np.array(list(self.cluster_means(scores).values()), dtype=float)
        return float(np.mean(cluster_values))

    def compute_central_tendency(self, scores: dict[str, float] | Iterable[float]) -> float:
        """Mean absolute archetype concern per the Phase 2 spec."""

        score_vector = self._coerce_vector(scores, self.archetype_ids)
        return float(np.mean(np.abs(score_vector)))

    def compute_contestedness(self, scores: dict[str, float] | Iterable[float]) -> float:
        """Median absolute deviation across cluster means."""

        cluster_values = np.array(list(self.cluster_means(scores).values()), dtype=float)
        median = float(np.median(cluster_values))
        return float(np.median(np.abs(cluster_values - median)))

    def compute_sign_agreement(self, scores: dict[str, float] | Iterable[float]) -> float:
        """Proportion of personas sharing the median sign."""

        score_vector = self._coerce_vector(scores, self.archetype_ids)
        median = float(np.median(score_vector))
        median_sign = np.sign(median)
        if median_sign == 0:
            return float(np.mean(np.isclose(score_vector, 0.0, atol=1e-9)))
        score_signs = np.sign(score_vector)
        return float(np.mean(score_signs == median_sign))

    def classify_signal(
        self,
        central_tendency_score: float,
        impact_score: float,
        sign_agreement: float,
        max_cluster_score: float,
    ) -> str:
        """Classify a signal into one of the four Phase 2 categories."""

        if central_tendency_score >= 0.5 and impact_score >= 0.5 and sign_agreement >= 0.75:
            return "convergent_priority"
        if central_tendency_score >= 0.5 and impact_score >= 0.5 and sign_agreement <= 0.55:
            return "contested_priority"
        if central_tendency_score < 0.0 and impact_score >= 0.5 and max_cluster_score >= 1.0:
            return "niche_concern"
        return "background_noise"


def derive_dimension_weights(
    dominant_values: Iterable[str],
    dimensions: Iterable[str] = DIMENSIONS,
    adjustments: dict[str, float] | None = None,
) -> dict[str, float]:
    """Derive a persona's signed dimension weights from the pre-registered seed mapping."""

    dominant = list(dominant_values)
    if not dominant:
        raise ValueError("Persona must declare at least one dominant Schwartz value")

    coefficients = DOMINANCE_COEFFICIENTS.get(len(dominant))
    if coefficients is None:
        raise ValueError(f"Expected 1-3 dominant values, got {len(dominant)}")

    dimension_list = list(dimensions)
    raw_weights = {dimension: 0.0 for dimension in dimension_list}
    for coefficient, value_name in zip(coefficients, dominant):
        if value_name not in SCHWARTZ_DIMENSION_LOADINGS:
            raise ValueError(f"Unsupported Schwartz value {value_name!r}")
        for dimension, loading in SCHWARTZ_DIMENSION_LOADINGS[value_name].items():
            if dimension in raw_weights:
                raw_weights[dimension] += coefficient * float(loading)

    for dimension, adjustment in (adjustments or {}).items():
        if dimension in raw_weights:
            raw_weights[dimension] = float(adjustment)

    total = sum(abs(weight) for weight in raw_weights.values())
    if np.isclose(total, 0.0, atol=VALIDATION_TOLERANCE):
        raise ValueError(f"Dominant values {dominant!r} produced an all-zero weight vector")

    return {dimension: weight / total for dimension, weight in raw_weights.items()}


def _validate_weight_sum(weights: dict[str, float], expected_total: float, label: str):
    total = float(sum(weights.values()))
    if not np.isclose(total, expected_total, rtol=VALIDATION_TOLERANCE, atol=VALIDATION_TOLERANCE):
        raise ValueError(f"{label} must sum to {expected_total}, got {total}")


def _validate_absolute_weight_sum(weights: dict[str, float], expected_total: float, label: str):
    total = float(sum(abs(weight) for weight in weights.values()))
    if not np.isclose(total, expected_total, rtol=VALIDATION_TOLERANCE, atol=VALIDATION_TOLERANCE):
        raise ValueError(f"{label} absolute weights must sum to {expected_total}, got {total}")


def load_ensemble(config_path: str | Path | None = None) -> PersonaEnsemble:
    """Load the persona ensemble YAML config."""

    if config_path is None:
        config_path = Path(__file__).parents[2] / "configs" / "persona_ensemble.yaml"
    path = Path(config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    dimensions = payload.get("dimensions", DIMENSIONS)
    meta_features = payload.get("meta_features", META_FEATURES)
    clusters = payload["clusters"]

    archetypes: list[PersonaArchetype] = []
    cluster_members: dict[str, list[str]] = {}
    for cluster_name, cluster_payload in clusters.items():
        archetype_block = cluster_payload.get("archetypes", {})
        cluster_members[cluster_name] = list(archetype_block.keys())
        for archetype_id, archetype_payload in archetype_block.items():
            dominant_values = list(archetype_payload.get("dominant_values", []))
            dimension_weights = {
                dimension: float(archetype_payload.get("dimension_weights", {}).get(dimension, 0.0))
                for dimension in dimensions
            }
            dimension_adjustments = {
                dimension: float(archetype_payload.get("dimension_adjustments", {}).get(dimension, 0.0))
                for dimension in dimensions
                if dimension in archetype_payload.get("dimension_adjustments", {})
            }
            meta_weights = {
                feature: float(archetype_payload.get("meta_weights", {}).get(feature, 0.0))
                for feature in meta_features
            }

            _validate_absolute_weight_sum(dimension_weights, 1.0, f"{archetype_id} dimension weights")
            _validate_weight_sum(meta_weights, 1.0, f"{archetype_id} meta weights")
            if dominant_values:
                expected_dimension_weights = derive_dimension_weights(dominant_values, dimensions, dimension_adjustments)
                mismatched_dimensions = [
                    dimension
                    for dimension in dimensions
                    if not np.isclose(
                        dimension_weights[dimension],
                        expected_dimension_weights[dimension],
                        rtol=VALIDATION_TOLERANCE,
                        atol=VALIDATION_TOLERANCE,
                    )
                ]
                if mismatched_dimensions:
                    mismatch_text = ", ".join(
                        f"{dimension}: expected {expected_dimension_weights[dimension]:.12f}, got {dimension_weights[dimension]:.12f}"
                        for dimension in mismatched_dimensions
                    )
                    raise ValueError(f"{archetype_id} does not match the canonical encoding procedure ({mismatch_text})")

            archetypes.append(
                PersonaArchetype(
                    archetype_id=archetype_id,
                    name=archetype_payload["name"],
                    cluster=cluster_name,
                    dominant_values=dominant_values,
                    dimension_weights=dimension_weights,
                    dimension_adjustments=dimension_adjustments,
                    meta_weights=meta_weights,
                )
            )

    return PersonaEnsemble(
        archetypes=archetypes,
        clusters=cluster_members,
        dimensions=dimensions,
        meta_features=meta_features,
        framework=payload.get("framework", "schwartz_10_value"),
    )

"""Persona ensemble loading and scoring."""

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


@dataclass(frozen=True)
class PersonaArchetype:
    """One scored persona in the ensemble."""

    archetype_id: str
    name: str
    cluster: str
    dominant_values: list[str]
    dimension_weights: dict[str, float]
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
        """Central tendency of ensemble concern."""

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

    def classify_signal(self, priority: float, contestedness: float, sign_agreement: float) -> str:
        """Classify a signal into one of the four Phase 2 categories."""

        if priority >= 0.5 and sign_agreement >= 0.75:
            return "convergent_priority"
        if priority >= 0.5 and sign_agreement <= 0.55:
            return "contested_priority"
        if priority < 0.0 and contestedness >= 0.5:
            return "niche_concern"
        return "background_noise"


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
            archetypes.append(
                PersonaArchetype(
                    archetype_id=archetype_id,
                    name=archetype_payload["name"],
                    cluster=cluster_name,
                    dominant_values=list(archetype_payload.get("dominant_values", [])),
                    dimension_weights={
                        dimension: float(archetype_payload.get("dimension_weights", {}).get(dimension, 0.0))
                        for dimension in dimensions
                    },
                    meta_weights={
                        feature: float(archetype_payload.get("meta_weights", {}).get(feature, 0.0))
                        for feature in meta_features
                    },
                )
            )

    return PersonaEnsemble(
        archetypes=archetypes,
        clusters=cluster_members,
        dimensions=dimensions,
        meta_features=meta_features,
        framework=payload.get("framework", "schwartz_10_value"),
    )

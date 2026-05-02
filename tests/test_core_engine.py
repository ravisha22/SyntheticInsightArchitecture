"""Tests for the SIA Phase 2 core prioritisation engine."""

from pathlib import Path

import pytest

from src.core.domain_registry import load_domain_profile
from src.core.persona_ensemble import DIMENSIONS, META_FEATURES, load_ensemble
from src.core.prioritization_engine import PrioritizationEngine
from src.core.structural_classifier import MockClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENSEMBLE_PATH = PROJECT_ROOT / "configs" / "persona_ensemble.yaml"


@pytest.fixture
def ensemble():
    return load_ensemble(ENSEMBLE_PATH)


def test_persona_ensemble_loads_correctly(ensemble):
    assert len(ensemble.archetypes) == 36
    assert ensemble.cluster_count == 9


def test_dimension_weights_sum_to_one(ensemble):
    for archetype in ensemble.archetypes:
        assert sum(archetype.dimension_weights.values()) == pytest.approx(1.0)


def test_meta_weights_sum_to_one(ensemble):
    for archetype in ensemble.archetypes:
        assert sum(archetype.meta_weights.values()) == pytest.approx(1.0)


def test_mock_classifier_produces_dimension_and_meta_vectors():
    classifier = MockClassifier()
    signal = {
        "signal_id": "s1",
        "title": "Urgent hospital outbreak prompts emergency response",
        "body": "Official report confirms widespread infection risk and immediate mitigation plan.",
        "tags": ["health", "urgent"],
    }
    classified = classifier.classify(signal)
    assert set(classified["dimensions"]) == set(DIMENSIONS)
    assert set(classified["meta"]) == set(META_FEATURES)
    assert all(-1.0 <= value <= 1.0 for value in classified["dimensions"].values())
    assert all(0.0 <= value <= 1.0 for value in classified["meta"].values())


def test_prioritization_engine_produces_ranked_results(ensemble):
    engine = PrioritizationEngine(ensemble, load_domain_profile("world_affairs"))
    signals = [
        {
            "signal_id": "high",
            "title": "Severe conflict escalates",
            "dimensions": {
                "physical_safety": -0.9,
                "economic_stability": -0.7,
                "institutional_trust": -0.5,
                "social_cohesion": -0.5,
                "individual_autonomy": -0.2,
                "collective_welfare": -0.6,
                "knowledge_capability": -0.1,
                "environmental_continuity": -0.2,
            },
            "meta": {
                "urgency": 1.0,
                "scale": 0.9,
                "irreversibility": 0.8,
                "cascade_risk": 0.9,
                "evidence_quality": 0.9,
                "actionability": 0.9,
            },
        },
        {
            "signal_id": "low",
            "title": "Minor local event",
            "dimensions": {dimension: 0.0 for dimension in DIMENSIONS},
            "meta": {feature: 0.1 for feature in META_FEATURES},
        },
    ]
    result = engine.prioritize(signals, budget=1)
    assert len(result.ranked_signals) == 2
    assert len(result.selected_signals) == 1
    assert "priority_score" in result.ranked_signals[0]
    assert "contest_score" in result.ranked_signals[0]


def test_convergent_signals_score_higher_priority_than_noise(ensemble):
    engine = PrioritizationEngine(ensemble, load_domain_profile("world_affairs"))
    convergent = {
        "signal_id": "convergent",
        "title": "Crisis affects safety and stability",
        "dimensions": {
            "physical_safety": -0.9,
            "economic_stability": -0.8,
            "institutional_trust": -0.7,
            "social_cohesion": -0.6,
            "individual_autonomy": -0.3,
            "collective_welfare": -0.7,
            "knowledge_capability": -0.1,
            "environmental_continuity": -0.2,
        },
        "meta": {
            "urgency": 1.0,
            "scale": 1.0,
            "irreversibility": 0.9,
            "cascade_risk": 1.0,
            "evidence_quality": 0.9,
            "actionability": 0.9,
        },
    }
    noise = {
        "signal_id": "noise",
        "title": "Tiny update",
        "dimensions": {dimension: 0.0 for dimension in DIMENSIONS},
        "meta": {feature: 0.05 for feature in META_FEATURES},
    }
    result = engine.prioritize([convergent, noise], budget=2)
    by_id = {entry["signal_id"]: entry for entry in result.ranked_signals}
    assert by_id["convergent"]["priority_raw"] > by_id["noise"]["priority_raw"]
    assert by_id["convergent"]["priority_score"] > by_id["noise"]["priority_score"]


def test_contested_signals_produce_high_contest_score(ensemble):
    engine = PrioritizationEngine(ensemble, load_domain_profile("code_repo"))
    contested = {
        "signal_id": "contested",
        "title": "Security lock-down breaks contributor access",
        "dimensions": {
            "physical_safety": 0.9,
            "economic_stability": -0.6,
            "institutional_trust": 0.7,
            "social_cohesion": -0.6,
            "individual_autonomy": -0.9,
            "collective_welfare": -0.3,
            "knowledge_capability": 0.7,
            "environmental_continuity": 0.0,
        },
        "meta": {
            "urgency": 0.9,
            "scale": 0.8,
            "irreversibility": 0.6,
            "cascade_risk": 0.8,
            "evidence_quality": 0.9,
            "actionability": 0.8,
        },
    }
    steady = {
        "signal_id": "steady",
        "title": "Widely beneficial bug fix",
        "dimensions": {
            "physical_safety": 0.8,
            "economic_stability": 0.1,
            "institutional_trust": 0.7,
            "social_cohesion": 0.2,
            "individual_autonomy": 0.2,
            "collective_welfare": 0.4,
            "knowledge_capability": 0.9,
            "environmental_continuity": 0.0,
        },
        "meta": {
            "urgency": 0.7,
            "scale": 0.7,
            "irreversibility": 0.4,
            "cascade_risk": 0.6,
            "evidence_quality": 0.8,
            "actionability": 0.9,
        },
    }
    low = {
        "signal_id": "low",
        "title": "Documentation typo",
        "dimensions": {dimension: 0.0 for dimension in DIMENSIONS},
        "meta": {feature: 0.1 for feature in META_FEATURES},
    }
    result = engine.prioritize([contested, steady, low], budget=3)
    by_id = {entry["signal_id"]: entry for entry in result.ranked_signals}
    assert by_id["contested"]["contest_score"] > 0.0
    assert by_id["contested"]["contestedness"] > by_id["steady"]["contestedness"]


def test_expert_prior_amplifies_relevant_dimensions(ensemble):
    signal = {
        "signal_id": "shared",
        "title": "Critical reliability regression",
        "dimensions": {
            "physical_safety": 0.9,
            "economic_stability": 0.1,
            "institutional_trust": 0.8,
            "social_cohesion": 0.0,
            "individual_autonomy": -0.1,
            "collective_welfare": 0.2,
            "knowledge_capability": 0.9,
            "environmental_continuity": 0.0,
        },
        "meta": {
            "urgency": 0.8,
            "scale": 0.7,
            "irreversibility": 0.5,
            "cascade_risk": 0.8,
            "evidence_quality": 0.9,
            "actionability": 0.9,
        },
    }
    code_engine = PrioritizationEngine(ensemble, load_domain_profile("code_repo"))
    world_engine = PrioritizationEngine(ensemble, load_domain_profile("world_affairs"))
    code_result = code_engine.prioritize([signal], budget=1)
    world_result = world_engine.prioritize([signal], budget=1)
    assert code_result.ranked_signals[0]["priority_raw"] > world_result.ranked_signals[0]["priority_raw"]


def test_portfolio_mood_is_computable(ensemble):
    engine = PrioritizationEngine(ensemble, load_domain_profile("community_health"))
    signals = [
        {
            "signal_id": "negative",
            "title": "Outbreak worsens",
            "dimensions": {
                "physical_safety": -0.9,
                "economic_stability": -0.3,
                "institutional_trust": -0.4,
                "social_cohesion": -0.3,
                "individual_autonomy": -0.1,
                "collective_welfare": -0.8,
                "knowledge_capability": -0.2,
                "environmental_continuity": 0.0,
            },
            "meta": {
                "urgency": 1.0,
                "scale": 0.9,
                "irreversibility": 0.8,
                "cascade_risk": 0.9,
                "evidence_quality": 0.8,
                "actionability": 0.7,
            },
        },
        {
            "signal_id": "positive",
            "title": "Vaccination drive succeeds",
            "dimensions": {
                "physical_safety": 0.8,
                "economic_stability": 0.3,
                "institutional_trust": 0.6,
                "social_cohesion": 0.4,
                "individual_autonomy": 0.1,
                "collective_welfare": 0.8,
                "knowledge_capability": 0.3,
                "environmental_continuity": 0.0,
            },
            "meta": {
                "urgency": 0.7,
                "scale": 0.8,
                "irreversibility": 0.4,
                "cascade_risk": 0.5,
                "evidence_quality": 0.9,
                "actionability": 0.9,
            },
        },
    ]
    result = engine.prioritize(signals, budget=2)
    assert "score" in result.portfolio_mood
    assert result.portfolio_mood["label"] in {"constructive", "cautious", "concerning", "transitional"}


def test_domain_profiles_load_correctly():
    for domain_name in ("world_affairs", "code_repo", "community_health"):
        profile = load_domain_profile(domain_name)
        assert profile["domain"] == domain_name
        assert "expert_prior" in profile
        assert set(profile["expert_prior"]) == set(DIMENSIONS)

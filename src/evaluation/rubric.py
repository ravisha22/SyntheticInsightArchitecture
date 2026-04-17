"""Scoring rubric definitions for SIA evaluation."""
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class RubricItem:
    name: str
    description: str
    weight: float
    min_score: float = 0.0
    max_score: float = 1.0

@dataclass
class Rubric:
    name: str
    items: List[RubricItem] = field(default_factory=list)
    
    def add_item(self, name: str, description: str, weight: float,
                 min_score: float = 0.0, max_score: float = 1.0):
        self.items.append(RubricItem(name, description, weight, min_score, max_score))
    
    def score(self, scores: Dict[str, float]) -> float:
        total_weight = sum(item.weight for item in self.items)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(
            item.weight * scores.get(item.name, 0.0)
            for item in self.items
        )
        return weighted_sum / total_weight

# Pre-defined rubrics
INSIGHT_RUBRIC = Rubric("insight_quality")
INSIGHT_RUBRIC.add_item("compression", "How much does the insight compress/unify prior knowledge?", 0.30)
INSIGHT_RUBRIC.add_item("constraint_satisfaction", "Does it satisfy all known constraints?", 0.25)
INSIGHT_RUBRIC.add_item("novelty", "Is it genuinely new, not just restated?", 0.20)
INSIGHT_RUBRIC.add_item("cross_domain_distance", "Does it bridge distant domains?", 0.15)
INSIGHT_RUBRIC.add_item("verifier_agreement", "Do independent checks confirm it?", 0.10)

PROCESS_RUBRIC = Rubric("process_fidelity")
PROCESS_RUBRIC.add_item("trace_similarity", "Does the process trace match human cognitive patterns?", 0.30)
PROCESS_RUBRIC.add_item("temporal_dynamics", "Do timings match human insight timelines?", 0.20)
PROCESS_RUBRIC.add_item("intervention_match", "Do interventions produce expected effects?", 0.20)
PROCESS_RUBRIC.add_item("tradeoff_match", "Does scarcity force realistic tradeoffs?", 0.15)
PROCESS_RUBRIC.add_item("outcome_robustness", "Are outcomes robust across parameter variations?", 0.15)

"""Fidelity scoring framework."""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class FidelityScore:
    component: str
    trace_similarity: float  # 0-1
    temporal_dynamics: float  # 0-1
    intervention_match: float  # 0-1
    tradeoff_match: float  # 0-1
    outcome_robustness: float  # 0-1
    
    @property
    def overall(self) -> float:
        return (
            0.30 * self.trace_similarity +
            0.20 * self.temporal_dynamics +
            0.20 * self.intervention_match +
            0.15 * self.tradeoff_match +
            0.15 * self.outcome_robustness
        )

class FidelityEvaluator:
    COMPONENTS = [
        "immersion", "tension", "accumulation", "incubation",
        "serendipity", "collision", "crystallization", "verification",
        "integration", "world_model", "urgency", "dream",
        "scarcity", "affect", "body", "social", "goal_formation"
    ]
    
    def __init__(self):
        self.scores: Dict[str, FidelityScore] = {}
    
    def score_component(self, component: str, trace_sim: float, temporal: float,
                        intervention: float, tradeoff: float, outcome: float) -> FidelityScore:
        score = FidelityScore(component, trace_sim, temporal, intervention, tradeoff, outcome)
        self.scores[component] = score
        return score
    
    def overall_fidelity(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.overall for s in self.scores.values()) / len(self.scores)
    
    def report(self) -> str:
        lines = ["SIA Fidelity Report", "=" * 60]
        for comp, score in sorted(self.scores.items()):
            lines.append(f"{comp:25s} {score.overall:.2f}  "
                        f"(trace={score.trace_similarity:.2f} temp={score.temporal_dynamics:.2f} "
                        f"intv={score.intervention_match:.2f} trade={score.tradeoff_match:.2f} "
                        f"out={score.outcome_robustness:.2f})")
        lines.append("-" * 60)
        lines.append(f"{'OVERALL':25s} {self.overall_fidelity():.2f}")
        return "\n".join(lines)

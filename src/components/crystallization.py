"""Crystallization Detector — insight emergence detection."""
import uuid
from datetime import datetime
from ..schema import log_event, Event, EventType

class CrystallizationDetector:
    def __init__(self, conn, config: dict):
        self.conn = conn
        self.weights = config.get("crystallization", {}).get("weights", {})
        self.gates = config.get("crystallization", {}).get("gates", {})
    
    def score_insight(self, description: str, compression: float, constraint: float,
                      novelty: float, distance: float, verifier: float) -> dict:
        final = (
            self.weights.get("compression", 0.30) * compression +
            self.weights.get("constraint_satisfaction", 0.25) * constraint +
            self.weights.get("novelty", 0.20) * novelty +
            self.weights.get("cross_domain_distance", 0.15) * distance +
            self.weights.get("verifier_agreement", 0.10) * verifier
        )
        return {
            "compression": compression,
            "constraint": constraint,
            "novelty": novelty,
            "distance": distance,
            "verifier": verifier,
            "final": final
        }
    
    def check_gates(self, scores: dict) -> bool:
        if scores["verifier"] < self.gates.get("min_verifier", 0.80):
            return False
        if scores["constraint"] < self.gates.get("min_constraint", 0.70):
            return False
        if scores["compression"] < self.gates.get("min_compression", 0.55):
            return False
        novelty_range = self.gates.get("novelty_range", [0.35, 0.90])
        if not (novelty_range[0] <= scores["novelty"] <= novelty_range[1]):
            return False
        return True
    
    def register_candidate(self, tension_id: str, description: str,
                           scores: dict, cycle: int = 0) -> str:
        insight_id = f"I-{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO insights (id, source_tension_id, description,
               compression_score, constraint_score, novelty_score, distance_score,
               verifier_score, final_score, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate', ?)""",
            (insight_id, tension_id, description,
             scores["compression"], scores["constraint"], scores["novelty"],
             scores["distance"], scores["verifier"], scores["final"], now)
        )
        log_event(self.conn, Event(
            event_type=EventType.INSIGHT_CANDIDATE.value,
            entity_id=insight_id,
            payload={"tension_id": tension_id, "scores": scores},
            cycle=cycle
        ))
        self.conn.commit()
        return insight_id

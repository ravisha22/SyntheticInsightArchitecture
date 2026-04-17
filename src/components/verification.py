"""Verification Harness — multi-angle insight verification."""
from ..schema import log_event, Event, EventType

class VerificationHarness:
    def __init__(self, conn, model_adapter):
        self.conn = conn
        self.model = model_adapter
    
    def verify_insight(self, insight_id: str, cycle: int = 0) -> dict:
        insight = self.conn.execute(
            "SELECT * FROM insights WHERE id = ?", (insight_id,)
        ).fetchone()
        if not insight:
            return {"verified": False, "reason": "not_found"}
        
        description = insight["description"]
        
        # Multi-angle verification
        checks = {
            "logical_consistency": self._check_logical(description),
            "constraint_satisfaction": insight["constraint_score"],
            "novelty_bounds": self._check_novelty_bounds(insight["novelty_score"]),
            "compression_quality": insight["compression_score"] >= 0.55,
        }
        
        passed = sum(1 for v in checks.values() if v) / len(checks)
        verified = passed >= 0.75
        
        status = "verified" if verified else "rejected"
        self.conn.execute(
            "UPDATE insights SET status = ?, verifier_score = ? WHERE id = ?",
            (status, passed, insight_id)
        )
        
        event_type = EventType.INSIGHT_VERIFIED.value if verified else EventType.INSIGHT_REJECTED.value
        log_event(self.conn, Event(
            event_type=event_type,
            entity_id=insight_id,
            payload={"checks": {k: bool(v) for k, v in checks.items()}, "pass_rate": passed},
            cycle=cycle
        ))
        self.conn.commit()
        
        return {"verified": verified, "checks": checks, "pass_rate": passed}
    
    def _check_logical(self, description: str) -> bool:
        structure = self.model.extract_structure(description)
        return len(structure.get("entities", [])) > 0
    
    def _check_novelty_bounds(self, novelty: float) -> bool:
        return 0.35 <= novelty <= 0.90

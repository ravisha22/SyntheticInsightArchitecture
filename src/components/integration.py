"""Integration Engine — verified insight absorption into world model."""
from datetime import datetime
from ..schema import log_event, Event, EventType

class IntegrationEngine:
    def __init__(self, conn):
        self.conn = conn
    
    def integrate_insight(self, insight_id: str, cycle: int = 0) -> bool:
        insight = self.conn.execute(
            "SELECT * FROM insights WHERE id = ? AND status = 'verified'",
            (insight_id,)
        ).fetchone()
        if not insight:
            return False
        
        # Mark as integrated
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE insights SET status = 'integrated' WHERE id = ?",
            (insight_id,)
        )
        
        # Resolve the source tension if it exists
        if insight["source_tension_id"]:
            self.conn.execute(
                "UPDATE tensions SET status = 'resolved', updated_at = ? WHERE id = ?",
                (now, insight["source_tension_id"])
            )
            log_event(self.conn, Event(
                event_type=EventType.TENSION_RESOLVED.value,
                entity_id=insight["source_tension_id"],
                payload={"resolved_by": insight_id},
                cycle=cycle
            ))
        
        log_event(self.conn, Event(
            event_type=EventType.INSIGHT_INTEGRATED.value,
            entity_id=insight_id,
            payload={"source_tension": insight["source_tension_id"]},
            cycle=cycle
        ))
        self.conn.commit()
        return True

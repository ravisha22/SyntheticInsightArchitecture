"""Social Ledger — relationship and norm tracking."""
import uuid
from datetime import datetime
from ..schema import log_event, Event, EventType

class SocialLedger:
    def __init__(self, conn):
        self.conn = conn
    
    def add_relationship(self, entity: str, trust: float = 0.5) -> str:
        rel_id = f"R-{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO relationships (id, entity, trust_score, last_interaction) VALUES (?, ?, ?, ?)",
            (rel_id, entity, trust, now)
        )
        self.conn.commit()
        return rel_id
    
    def update_trust(self, entity: str, delta: float, cycle: int = 0):
        rel = self.conn.execute(
            "SELECT * FROM relationships WHERE entity = ?", (entity,)
        ).fetchone()
        if rel:
            new_trust = max(0.0, min(1.0, rel["trust_score"] + delta))
            now = datetime.utcnow().isoformat()
            self.conn.execute(
                "UPDATE relationships SET trust_score = ?, last_interaction = ? WHERE entity = ?",
                (new_trust, now, entity)
            )
            log_event(self.conn, Event(
                event_type=EventType.SOCIAL_EVENT.value,
                entity_id=entity,
                payload={"trust_delta": delta, "new_trust": new_trust},
                cycle=cycle
            ))
            self.conn.commit()
    
    def get_social_resistance(self, entity: str) -> float:
        rel = self.conn.execute(
            "SELECT * FROM relationships WHERE entity = ?", (entity,)
        ).fetchone()
        if not rel:
            return 0.5
        return 1.0 - rel["trust_score"] + rel["norm_debt"]

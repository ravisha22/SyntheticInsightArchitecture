"""Tension Register — first-class unsolved problem objects."""
import uuid
from datetime import datetime
from ..schema import init_db, log_event, Event, EventType, TensionStatus

class TensionRegister:
    def __init__(self, conn):
        self.conn = conn
    
    def create_tension(self, title: str, description: str = "",
                       stake_weight: float = 1.0, cycle: int = 0) -> str:
        tension_id = f"T-{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO tensions (id, title, description, status, stake_weight, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tension_id, title, description, TensionStatus.OPEN.value, stake_weight, now, now)
        )
        log_event(self.conn, Event(
            event_type=EventType.TENSION_CREATED.value,
            entity_id=tension_id,
            payload={"title": title, "description": description, "stake_weight": stake_weight},
            cycle=cycle
        ))
        return tension_id
    
    def add_claim(self, tension_id: str, claim: str, role: str = "contradicts",
                  confidence: float = 0.5, source: str = ""):
        self.conn.execute(
            "INSERT INTO tension_claims (tension_id, claim, role, confidence, source) VALUES (?, ?, ?, ?, ?)",
            (tension_id, claim, role, confidence, source)
        )
        if role == "contradicts":
            self.conn.execute(
                "UPDATE tensions SET contradiction_count = contradiction_count + 1, updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), tension_id)
            )
        self.conn.commit()
    
    def record_failure(self, tension_id: str, cycle: int = 0):
        self.conn.execute(
            "UPDATE tensions SET failed_attempts = failed_attempts + 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), tension_id)
        )
        self.conn.commit()
    
    def record_near_miss(self, tension_id: str, cycle: int = 0):
        self.conn.execute(
            "UPDATE tensions SET near_misses = near_misses + 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), tension_id)
        )
        self.conn.commit()
    
    def resolve(self, tension_id: str, cycle: int = 0):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE tensions SET status = ?, updated_at = ? WHERE id = ?",
            (TensionStatus.RESOLVED.value, now, tension_id)
        )
        log_event(self.conn, Event(
            event_type=EventType.TENSION_RESOLVED.value,
            entity_id=tension_id,
            payload={},
            cycle=cycle
        ))
    
    def get_active_tensions(self):
        return self.conn.execute(
            "SELECT * FROM tensions WHERE status IN ('open', 'incubating', 'monitoring') ORDER BY priority DESC"
        ).fetchall()
    
    def get_tension(self, tension_id: str):
        return self.conn.execute("SELECT * FROM tensions WHERE id = ?", (tension_id,)).fetchone()

"""Failure Journal — structured learning from failed attempts."""
import uuid
import json
from datetime import datetime
from ..schema import log_event, Event, EventType

class FailureJournal:
    def __init__(self, conn):
        self.conn = conn
    
    def log_failure(self, tension_id: str, summary: str, why_chain: list = None,
                    outcome: str = "", severity: float = 0.5,
                    reusable_fragment: str = "", cycle: int = 0) -> str:
        failure_id = f"F-{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """INSERT INTO failures (id, tension_id, summary, why_chain, outcome, severity, reusable_fragment, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (failure_id, tension_id, summary, json.dumps(why_chain or []),
             outcome, severity, reusable_fragment, now)
        )
        log_event(self.conn, Event(
            event_type=EventType.FAILURE_LOGGED.value,
            entity_id=failure_id,
            payload={"tension_id": tension_id, "summary": summary, "severity": severity},
            cycle=cycle
        ))
        return failure_id
    
    def get_failures_for_tension(self, tension_id: str):
        return self.conn.execute(
            "SELECT * FROM failures WHERE tension_id = ? ORDER BY created_at DESC",
            (tension_id,)
        ).fetchall()
    
    def get_reusable_fragments(self):
        return self.conn.execute(
            "SELECT * FROM failures WHERE reusable_fragment != '' ORDER BY severity DESC"
        ).fetchall()

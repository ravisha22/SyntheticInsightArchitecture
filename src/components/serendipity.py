"""Serendipity Engine — controlled randomness injection."""
import uuid
import random
from datetime import datetime
from ..schema import log_event, Event, EventType

class SerendipityEngine:
    def __init__(self, conn, model_adapter, seed: int = 42):
        self.conn = conn
        self.model = model_adapter
        self.rng = random.Random(seed)
    
    def inject_stimulus(self, domain: str = "", cycle: int = 0) -> str:
        stimulus_id = f"S-{uuid.uuid4().hex[:8]}"
        
        # Get current tensions for context
        tensions = self.conn.execute(
            "SELECT title FROM tensions WHERE status IN ('open', 'incubating') ORDER BY pressure DESC LIMIT 5"
        ).fetchall()
        
        context = " | ".join(t["title"] for t in tensions)
        stimulus = self.model.generate(
            f"Generate a surprising connection or analogy related to: {context}",
            system="You are a creative cross-domain thinker."
        )
        
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO concepts (id, label, domain, abstraction_level, created_at) VALUES (?, ?, ?, 'intermediate', ?)",
            (stimulus_id, stimulus[:200], domain or "serendipity", now)
        )
        
        log_event(self.conn, Event(
            event_type=EventType.STIMULUS_INJECTED.value,
            entity_id=stimulus_id,
            payload={"stimulus": stimulus[:500], "domain": domain},
            cycle=cycle
        ))
        self.conn.commit()
        return stimulus_id

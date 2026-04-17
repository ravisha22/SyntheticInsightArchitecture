"""Synthetic Valence Homeostat — functional affect simulation."""
from datetime import datetime
from ..schema import log_event, Event, EventType

class AffectHomeostat:
    def __init__(self, conn, config: dict):
        self.conn = conn
        self.cfg = config.get("affect", {})
        self.distress_decay = self.cfg.get("distress_decay", 0.95)
        self.relief_decay = self.cfg.get("relief_decay", 0.90)
        self.wireheading_penalty = self.cfg.get("wireheading_penalty", 0.5)
        self.slack_threshold = self.cfg.get("slack_loss_threshold", 0.7)
    
    def compute_distress(self, cycle: int) -> float:
        # Distress from unresolved tensions weighted by pressure and age
        tensions = self.conn.execute(
            "SELECT pressure, urgency, days_open FROM tensions WHERE status IN ('open', 'incubating')"
        ).fetchall()
        distress = sum(t["pressure"] * t["urgency"] * (1 + t["days_open"] * 0.01) for t in tensions)
        
        # Add distress from failed attempts
        recent_failures = self.conn.execute(
            "SELECT COUNT(*) as c FROM events WHERE event_type = 'failure_logged' AND cycle >= ?",
            (max(0, cycle - 3),)
        ).fetchone()["c"]
        distress += recent_failures * 0.15
        
        return min(distress, 5.0)  # cap
    
    def compute_relief(self, cycle: int) -> float:
        # Relief from recently resolved tensions
        recent_resolutions = self.conn.execute(
            "SELECT COUNT(*) as c FROM events WHERE event_type = 'tension_resolved' AND cycle >= ?",
            (max(0, cycle - 3),)
        ).fetchone()["c"]
        
        # Relief from verified insights
        recent_insights = self.conn.execute(
            "SELECT COUNT(*) as c FROM events WHERE event_type = 'insight_verified' AND cycle >= ?",
            (max(0, cycle - 3),)
        ).fetchone()["c"]
        
        return recent_resolutions * 0.3 + recent_insights * 0.5
    
    def update(self, cycle: int):
        distress = self.compute_distress(cycle)
        relief = self.compute_relief(cycle)
        net_valence = relief - distress
        
        # Deliberative slack: reduces when chronic distress is high
        deliberative_slack = max(0.1, 1.0 - (distress * 0.15))
        
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO affect_state (cycle, distress, relief, net_valence, deliberative_slack, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (cycle, distress, relief, net_valence, deliberative_slack, now)
        )
        
        log_event(self.conn, Event(
            event_type=EventType.AFFECT_UPDATE.value,
            entity_id="affect",
            payload={"distress": distress, "relief": relief, "net_valence": net_valence, "slack": deliberative_slack},
            cycle=cycle
        ))
        self.conn.commit()
        
        return {"distress": distress, "relief": relief, "net_valence": net_valence, "slack": deliberative_slack}

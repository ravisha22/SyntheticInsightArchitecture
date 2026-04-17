"""Pressure and Urgency scoring."""
import math
from datetime import datetime
from ..schema import log_event, Event, EventType

class PressureScorer:
    def __init__(self, conn, config: dict):
        self.conn = conn
        self.pw = config.get("pressure", {}).get("weights", {})
        self.uw = config.get("urgency", {}).get("weights", {})
        self.thresholds = config.get("pressure", {}).get("thresholds", {})
    
    def sigmoid(self, x):
        return 1.0 / (1.0 + math.exp(-x))
    
    def compute_pressure(self, tension) -> float:
        raw = (
            self.pw.get("uncertainty", 1.4) * (1.0 - min(tension["near_misses"] * 0.1, 0.9)) +
            self.pw.get("impact", 1.2) * tension["stake_weight"] +
            self.pw.get("contradiction", 1.0) * min(tension["contradiction_count"] * 0.2, 2.0) +
            self.pw.get("deadline", 0.8) * 0.5 +  # placeholder
            self.pw.get("blockers", 0.6) * math.log1p(tension["failed_attempts"]) +
            self.pw.get("recent_failures", 0.5) * min(tension["failed_attempts"] * 0.15, 1.5) +
            self.pw.get("known_solution", -0.9) * 0.0  # no known solution by default
        )
        return self.sigmoid(raw)
    
    def compute_urgency(self, tension) -> float:
        days = tension["days_open"]
        raw = (
            self.uw.get("impact", 1.0) * tension["stake_weight"] +
            self.uw.get("severity", 1.0) * min(tension["contradiction_count"] * 0.3, 2.0) +
            self.uw.get("elapsed_days", 0.5) * math.log1p(days) +
            self.uw.get("deadline_pressure", 1.5) * 0.3 +  # placeholder
            self.uw.get("dependency_centrality", 0.8) * 0.5 +
            self.uw.get("deterioration", 0.7) * (tension["failed_attempts"] / max(days, 1)) +
            self.uw.get("reversibility", -0.5) * 0.5
        )
        return self.sigmoid(raw)
    
    def update_all(self, cycle: int = 0):
        tensions = self.conn.execute(
            "SELECT * FROM tensions WHERE status IN ('open', 'incubating', 'monitoring')"
        ).fetchall()
        
        for t in tensions:
            t_dict = dict(t)
            pressure = self.compute_pressure(t_dict)
            urgency = self.compute_urgency(t_dict)
            priority = pressure * urgency
            
            now = datetime.utcnow().isoformat()
            self.conn.execute(
                "UPDATE tensions SET pressure = ?, urgency = ?, priority = ?, updated_at = ? WHERE id = ?",
                (pressure, urgency, priority, now, t_dict["id"])
            )
            
            # Update status based on thresholds
            if pressure >= self.thresholds.get("incubate", 0.72):
                self.conn.execute("UPDATE tensions SET status = 'incubating' WHERE id = ? AND status = 'open'",
                                  (t_dict["id"],))
            
            log_event(self.conn, Event(
                event_type=EventType.PRESSURE_UPDATED.value,
                entity_id=t_dict["id"],
                payload={"pressure": pressure, "urgency": urgency, "priority": priority},
                cycle=cycle
            ))
        
        self.conn.commit()

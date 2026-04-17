"""Synthetic Body Budget — real resource scarcity enforcement."""
from datetime import datetime
from ..schema import log_event, Event, EventType

class BodyBudget:
    def __init__(self, conn, config: dict):
        self.conn = conn
        self.budgets = config.get("budgets", {})
    
    def initialize_budgets(self):
        now = datetime.utcnow().isoformat()
        for resource, budget in self.budgets.items():
            self.conn.execute(
                """INSERT OR REPLACE INTO resource_state (resource, budget, spent, remaining, shadow_price, last_updated)
                   VALUES (?, ?, 0, ?, 0, ?)""",
                (resource, budget, budget, now)
            )
        self.conn.commit()
    
    def spend(self, resource: str, amount: float, cycle: int = 0) -> bool:
        state = self.conn.execute(
            "SELECT * FROM resource_state WHERE resource = ?", (resource,)
        ).fetchone()
        if not state:
            return False
        
        remaining = state["remaining"] - amount
        if remaining < 0:
            log_event(self.conn, Event(
                event_type=EventType.RESOURCE_DEPLETED.value,
                entity_id=resource,
                payload={"requested": amount, "remaining": state["remaining"]},
                cycle=cycle
            ))
            return False
        
        now = datetime.utcnow().isoformat()
        spent = state["spent"] + amount
        # Shadow price increases as resource depletes
        utilization = spent / state["budget"] if state["budget"] > 0 else 1.0
        shadow_price = utilization ** 2  # quadratic increase
        
        self.conn.execute(
            "UPDATE resource_state SET spent = ?, remaining = ?, shadow_price = ?, last_updated = ? WHERE resource = ?",
            (spent, remaining, shadow_price, now, resource)
        )
        
        log_event(self.conn, Event(
            event_type=EventType.RESOURCE_SPENT.value,
            entity_id=resource,
            payload={"amount": amount, "remaining": remaining, "shadow_price": shadow_price},
            cycle=cycle
        ))
        self.conn.commit()
        return True
    
    def get_scarcity_level(self) -> float:
        states = self.conn.execute("SELECT * FROM resource_state").fetchall()
        if not states:
            return 0.0
        ratios = [s["spent"] / s["budget"] if s["budget"] > 0 else 1.0 for s in states]
        return sum(ratios) / len(ratios)
    
    def is_resource_available(self, resource: str, amount: float) -> bool:
        state = self.conn.execute(
            "SELECT remaining FROM resource_state WHERE resource = ?", (resource,)
        ).fetchone()
        return state and state["remaining"] >= amount

"""Case study replay framework for SIA validation."""
from pathlib import Path
from src.engine import SIAEngine
from src.evaluation.trace_logger import TraceLogger
from src.evaluation.fidelity import FidelityEvaluator

class CaseStudyReplay:
    """Replays a historical breakthrough as a sequence of events fed to SIA."""
    
    def __init__(self, engine: SIAEngine, name: str):
        self.engine = engine
        self.name = name
        self.tracer = TraceLogger(engine.conn)
        self.evaluator = FidelityEvaluator()
        self.events = []
    
    def add_event(self, cycle: int, event_type: str, data: dict):
        self.events.append({"cycle": cycle, "type": event_type, "data": data})
    
    def replay(self):
        self.engine.initialize()
        
        for event in sorted(self.events, key=lambda e: e["cycle"]):
            # Advance engine to the event's cycle
            while self.engine.cycle < event["cycle"]:
                self.engine.run_cycle()
            
            # Inject the event
            self._inject_event(event)
        
        # Run a few more cycles to let the system settle
        for _ in range(5):
            self.engine.run_cycle()
    
    def _inject_event(self, event):
        etype = event["type"]
        data = event["data"]
        
        if etype == "new_information":
            # New domain knowledge arrives
            pass  # handled by immersion engine when implemented
        
        elif etype == "tension":
            self.engine.tensions.create_tension(
                data["title"], data.get("description", ""),
                data.get("stake_weight", 1.0), event["cycle"]
            )
        
        elif etype == "contradiction":
            self.engine.tensions.add_claim(
                data["tension_id"], data["claim"], "contradicts",
                data.get("confidence", 0.7)
            )
        
        elif etype == "failure":
            self.engine.tensions.record_failure(data["tension_id"], event["cycle"])
        
        elif etype == "near_miss":
            self.engine.tensions.record_near_miss(data["tension_id"], event["cycle"])
        
        elif etype == "seed":
            self.engine.goals.plant_seed(
                data["description"], data.get("tags", []),
                data.get("tension_ids", []), event["cycle"]
            )
        
        elif etype == "resource_pressure":
            self.engine.body.spend(data["resource"], data["amount"], event["cycle"])
    
    def get_results(self) -> dict:
        summary = self.engine.get_state_summary()
        
        # Get full event log
        events = self.engine.conn.execute(
            "SELECT * FROM events ORDER BY id"
        ).fetchall()
        
        # Get goal states
        goals = self.engine.conn.execute(
            "SELECT * FROM goal_seeds ORDER BY commitment_pressure DESC"
        ).fetchall()
        
        return {
            "summary": summary,
            "total_events": len(events),
            "goals": [dict(g) for g in goals],
            "event_types": {}
        }

"""SIA Main Orchestrator Engine."""
import yaml
from pathlib import Path
from .schema import init_db
from .components.tension_register import TensionRegister
from .components.pressure_scorer import PressureScorer
from .components.goal_pipeline import GoalPipeline
from .components.affect_homeostat import AffectHomeostat
from .components.body_budget import BodyBudget
from .adapters.mock import MockAdapter

class SIAEngine:
    def __init__(self, db_path: str = "sia_state.db", config_path: str = None):
        self.conn = init_db(db_path)
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
        
        # Initialize components
        self.tensions = TensionRegister(self.conn)
        self.pressure = PressureScorer(self.conn, self.config)
        self.goals = GoalPipeline(self.conn, self.config)
        self.affect = AffectHomeostat(self.conn, self.config)
        self.body = BodyBudget(self.conn, self.config)
        
        # Initialize model adapter
        backend = self.config.get("model", {}).get("backend", "mock")
        if backend == "mock":
            self.model = MockAdapter()
        else:
            from .adapters.ollama import OllamaAdapter
            self.model = OllamaAdapter(self.config.get("model", {}))
        
        self.cycle = 0
    
    def initialize(self):
        self.body.initialize_budgets()
    
    def run_cycle(self):
        self.cycle += 1
        
        # 1. Update pressure and urgency for all tensions
        self.pressure.update_all(self.cycle)
        
        # 2. Update affect state
        affect_state = self.affect.update(self.cycle)
        
        # 3. Process goal pipeline
        seeds = self.conn.execute(
            "SELECT * FROM goal_seeds WHERE stage NOT IN ('committed', 'abandoned')"
        ).fetchall()
        for seed in seeds:
            s = dict(seed)
            if s["stage"] == "incubating" or s["stage"] == "pattern_detected":
                self.goals.incubate(s["id"], self.cycle)
                self.goals.test_threshold(s["id"], self.cycle)
        
        # 4. Report cycle state
        return self.get_state_summary()
    
    def get_state_summary(self) -> dict:
        active_tensions = self.conn.execute(
            "SELECT COUNT(*) as c FROM tensions WHERE status IN ('open', 'incubating')"
        ).fetchone()["c"]
        
        committed_goals = self.conn.execute(
            "SELECT COUNT(*) as c FROM goal_seeds WHERE stage = 'committed'"
        ).fetchone()["c"]
        
        affect = self.conn.execute(
            "SELECT * FROM affect_state ORDER BY cycle DESC LIMIT 1"
        ).fetchone()
        
        scarcity = self.body.get_scarcity_level()
        
        return {
            "cycle": self.cycle,
            "active_tensions": active_tensions,
            "committed_goals": committed_goals,
            "distress": affect["distress"] if affect else 0,
            "relief": affect["relief"] if affect else 0,
            "deliberative_slack": affect["deliberative_slack"] if affect else 1.0,
            "scarcity_level": scarcity,
        }

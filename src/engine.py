"""SIA Main Orchestrator Engine."""
import json
import yaml
from pathlib import Path
from .schema import init_db, log_event, Event, EventType
from .components.tension_register import TensionRegister
from .components.pressure_scorer import PressureScorer
from .components.goal_pipeline import GoalPipeline
from .components.affect_homeostat import AffectHomeostat
from .components.body_budget import BodyBudget
from .components.serendipity import SerendipityEngine
from .components.dream_engine import DreamEngine
from .components.collision_search import CollisionSearch
from .components.crystallization import CrystallizationDetector
from .components.failure_journal import FailureJournal
from .adapters.mock import MockAdapter

class SIAEngine:
    def __init__(self, db_path: str = "sia_state.db", config_path: str = None):
        self.conn = init_db(db_path)
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
        
        # Initialize model adapter
        backend = self.config.get("model", {}).get("backend", "mock")
        if backend == "mock":
            self.model = MockAdapter()
        else:
            from .adapters.ollama import OllamaAdapter
            self.model = OllamaAdapter(self.config.get("model", {}))
        
        # Initialize all components
        self.tensions = TensionRegister(self.conn)
        self.pressure = PressureScorer(self.conn, self.config)
        self.goals = GoalPipeline(self.conn, self.config)
        self.affect = AffectHomeostat(self.conn, self.config)
        self.body = BodyBudget(self.conn, self.config)
        self.serendipity = SerendipityEngine(self.conn, self.model)
        self.dreams = DreamEngine(self.conn, self.model)
        self.collisions = CollisionSearch(self.conn, self.model)
        self.crystallization = CrystallizationDetector(self.conn, self.config)
        self.failures = FailureJournal(self.conn)
        
        self.cycle = 0
    
    def initialize(self):
        self.body.initialize_budgets()
    
    def run_cycle(self):
        self.cycle += 1
        
        # 1. Update pressure and urgency for all tensions
        self.pressure.update_all(self.cycle)
        
        # 2. Update affect state
        affect_state = self.affect.update(self.cycle)
        
        # 3. Cluster related seeds by shared tags — drives accumulation
        self._cluster_seeds()
        
        # 4. Process goal pipeline stages
        seeds = self.conn.execute(
            "SELECT * FROM goal_seeds WHERE stage NOT IN ('committed', 'abandoned')"
        ).fetchall()
        for seed in seeds:
            s = dict(seed)
            if s["stage"] == "seed":
                # Check if recurrence threshold met for accumulation
                pass  # recurrence updated by _cluster_seeds
            elif s["stage"] == "accumulating":
                # Try to detect pattern if coherence is high enough
                coherence = self._compute_seed_coherence(s)
                if coherence > 0.5:
                    self.goals.detect_pattern(s["id"], coherence, self.cycle)
            elif s["stage"] in ("pattern_detected", "incubating"):
                self.goals.incubate(s["id"], self.cycle)
                self.goals.test_threshold(s["id"], self.cycle)
        
        # 5. Creative pipeline (every 3 cycles to simulate incubation spacing)
        if self.cycle % 3 == 0:
            self._run_creative_pipeline()
        
        # 6. Report cycle state
        return self.get_state_summary()
    
    def _cluster_seeds(self):
        """Find seeds with overlapping tags and bump their recurrence."""
        seeds = self.conn.execute(
            "SELECT * FROM goal_seeds WHERE stage IN ('seed', 'accumulating')"
        ).fetchall()
        
        if len(seeds) < 2:
            return
        
        # Build tag-to-seed index
        tag_index = {}
        for seed in seeds:
            tags = json.loads(seed["tags"]) if seed["tags"] else []
            for tag in tags:
                tag_index.setdefault(tag, []).append(seed["id"])
        
        # Find seeds that share tags — each shared tag = evidence of recurrence
        boosted = set()
        for tag, seed_ids in tag_index.items():
            if len(seed_ids) > 1:
                for sid in seed_ids:
                    if sid not in boosted:
                        self.goals.update_recurrence(sid, self.cycle)
                        boosted.add(sid)
        
        # Also link seeds to related tensions by keyword overlap
        tensions = self.conn.execute(
            "SELECT id, title, description FROM tensions WHERE status IN ('open', 'incubating')"
        ).fetchall()
        
        for seed in seeds:
            tags = set(json.loads(seed["tags"]) if seed["tags"] else [])
            for t in tensions:
                t_words = set((t["title"] + " " + (t["description"] or "")).lower().split())
                if tags & t_words:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO seed_tensions (seed_id, tension_id) VALUES (?, ?)",
                        (seed["id"], t["id"])
                    )
        self.conn.commit()
    
    def _compute_seed_coherence(self, seed: dict) -> float:
        """How coherent is this seed cluster? Based on linked tension count and tag overlap."""
        linked = self.conn.execute(
            "SELECT COUNT(*) as c FROM seed_tensions WHERE seed_id = ?",
            (seed["id"],)
        ).fetchone()["c"]
        
        recurrence = seed["recurrence"]
        # Coherence grows with linked tensions and recurrence
        return min((linked * 0.2 + recurrence * 0.15), 1.0)
    
    def _run_creative_pipeline(self):
        """Serendipity → Dream → Collision → Crystallization."""
        slack = 1.0
        affect = self.conn.execute(
            "SELECT deliberative_slack FROM affect_state ORDER BY cycle DESC LIMIT 1"
        ).fetchone()
        if affect:
            slack = affect["deliberative_slack"]
        
        # Under high distress (low slack), dreams become more focused
        # Under normal slack, serendipity runs broader
        
        # Inject a cross-domain stimulus
        if slack > 0.3:
            self.serendipity.inject_stimulus("cross-domain", self.cycle)
        
        # Run dream recombination on high-pressure tensions
        recombinations = self.dreams.run_dream_cycle(self.cycle)
        
        # Search for structural collisions across domains
        collisions = self.collisions.search_collisions(self.cycle)
        
        # Evaluate any collisions as potential insights
        for collision in collisions:
            if collision["similarity"] > 0.2:
                scores = self.crystallization.score_insight(
                    description=f"Collision: {collision['domain_a']} x {collision['domain_b']}",
                    compression=min(collision["similarity"] * 1.5, 1.0),
                    constraint=0.7,
                    novelty=1.0 - collision["similarity"],
                    distance=0.8 if collision["domain_a"] != collision["domain_b"] else 0.2,
                    verifier=0.6
                )
                if self.crystallization.check_gates(scores):
                    self.crystallization.register_candidate(
                        tension_id=None,
                        description=f"Cross-domain insight: {collision['domain_a']} ↔ {collision['domain_b']}",
                        scores=scores,
                        cycle=self.cycle
                    )
    
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

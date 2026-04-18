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
    
    # Stop words that appear in almost every issue and carry no signal
    STOP_WORDS = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "out", "off",
        "over", "under", "again", "further", "then", "once", "here", "there",
        "when", "where", "why", "how", "all", "each", "every", "both", "few",
        "more", "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "so", "than", "too", "very", "just", "don", "doesn",
        "didn", "won", "wouldn", "shouldn", "couldn", "isn", "aren", "wasn",
        "weren", "hasn", "haven", "hadn", "it", "its", "this", "that", "these",
        "those", "i", "me", "my", "we", "our", "you", "your", "he", "him",
        "she", "her", "they", "them", "their", "what", "which", "who", "whom",
        "and", "but", "or", "if", "while", "because", "until", "about",
        "pandas", "dataframe", "series", "column", "row", "data", "value",
        "values", "using", "like", "also", "e.g", "etc", "use", "used",
        "get", "set", "one", "two", "new", "see", "way", "make", "still",
        "even", "work", "works", "bug", "issue", "error", "expected", "actual",
        "0", "1", "2", "3", "4", "5", "128", "64", "none", "true", "false",
    })

    def _clean_tokenize(self, text):
        """Extract meaningful tokens from text, stripping punctuation."""
        import re
        # Split on non-alphanumeric, lowercase, filter stop words and short tokens
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_-]*', text.lower())
        return {t for t in tokens if t not in self.STOP_WORDS and len(t) > 2}

    def _split_tag(self, tag):
        """Split multi-word tags into individual tokens."""
        import re
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_-]*', tag.lower())
        return {t for t in tokens if t not in self.STOP_WORDS and len(t) > 2}

    def _cluster_seeds(self):
        """Find seeds with overlapping tags and bump recurrence.
        
        Uses STRONG matching: requires minimum tag overlap ratio,
        filters stop words, and links to tensions only on meaningful terms.
        """
        seeds = self.conn.execute(
            "SELECT * FROM goal_seeds WHERE stage IN ('seed', 'accumulating')"
        ).fetchall()
        
        if len(seeds) < 2:
            return
        
        # Build tag sets per seed — split multi-word labels into individual tokens
        seed_tags = {}
        for seed in seeds:
            raw_tags = json.loads(seed["tags"]) if seed["tags"] else []
            clean = set()
            for tag in raw_tags:
                clean.update(self._split_tag(tag))
            seed_tags[seed["id"]] = clean
        
        # Cluster seeds by tag overlap — require >= 2 shared meaningful tags
        min_shared = self.config.get("goal_pipeline", {}).get("min_shared_tags", 2)
        boosted = set()
        seed_list = list(seed_tags.items())
        for i in range(len(seed_list)):
            for j in range(i + 1, len(seed_list)):
                sid_a, tags_a = seed_list[i]
                sid_b, tags_b = seed_list[j]
                shared = tags_a & tags_b
                if len(shared) >= min_shared:
                    for sid in (sid_a, sid_b):
                        if sid not in boosted:
                            self.goals.update_recurrence(sid, self.cycle)
                            boosted.add(sid)
        
        # Link seeds to tensions — match seed tags against tension title+description words
        tensions = self.conn.execute(
            "SELECT id, title, description FROM tensions WHERE status IN ('open', 'incubating')"
        ).fetchall()
        
        total_tensions = len(tensions)
        
        for seed in seeds:
            tags = seed_tags.get(seed["id"], set())
            if not tags:
                continue
            matched_count = 0
            for t in tensions:
                t_words = self._clean_tokenize(
                    (t["title"] or "") + " " + (t["description"] or "")
                )
                overlap = tags & t_words
                if len(overlap) >= 1:  # 1 meaningful match to link
                    self.conn.execute(
                        "INSERT OR IGNORE INTO seed_tensions (seed_id, tension_id) VALUES (?, ?)",
                        (seed["id"], t["id"])
                    )
                    matched_count += 1
            
            # Store hit rate for evidence quality gating
            hit_rate = matched_count / total_tensions if total_tensions > 0 else 0.0
            self.conn.execute(
                "UPDATE goal_seeds SET social_resistance = ? WHERE id = ?",
                (1.0 - hit_rate, seed["id"])
            )
        
        self.conn.commit()
    
    def _compute_seed_coherence(self, seed: dict) -> float:
        """How coherent is this seed cluster?
        
        Coherence combines:
        - linked tension count (but penalized if it links to EVERYTHING)
        - recurrence from independent tag clustering
        - exclusivity: a seed that matches 90% of tensions is generic, not insightful
        """
        linked = self.conn.execute(
            "SELECT COUNT(*) as c FROM seed_tensions WHERE seed_id = ?",
            (seed["id"],)
        ).fetchone()["c"]
        
        total_tensions = self.conn.execute(
            "SELECT COUNT(*) as c FROM tensions WHERE status IN ('open', 'incubating')"
        ).fetchone()["c"]
        
        if total_tensions == 0:
            return 0.0
        
        # Hit rate: fraction of tensions this seed is linked to
        hit_rate = linked / total_tensions
        
        # Exclusivity penalty: seeds that match everything are generic
        # Sweet spot is 20-60% of tensions — specific enough to be meaningful
        if hit_rate > 0.8:
            exclusivity = 0.2  # very generic, penalize heavily
        elif hit_rate > 0.6:
            exclusivity = 0.5
        elif hit_rate > 0.3:
            exclusivity = 0.9  # sweet spot
        elif hit_rate > 0.1:
            exclusivity = 0.7  # somewhat narrow but valid
        else:
            exclusivity = 0.3  # too narrow, weak evidence
        
        recurrence = seed["recurrence"]
        
        # Coherence = evidence strength × exclusivity
        raw_coherence = (linked * 0.15 + recurrence * 0.1) * exclusivity
        return min(raw_coherence, 1.0)
    
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

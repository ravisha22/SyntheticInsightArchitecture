"""Pressure-to-Commitment Pipeline — autonomous goal formation."""
import uuid
from datetime import datetime
from ..schema import log_event, Event, EventType, GoalStage

class GoalPipeline:
    def __init__(self, conn, config: dict):
        self.conn = conn
        self.cfg = config.get("goal_pipeline", {})
    
    def plant_seed(self, description: str, tags: list, tension_ids: list = None, cycle: int = 0) -> str:
        seed_id = f"G-{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        import json
        self.conn.execute(
            """INSERT INTO goal_seeds (id, description, tags, stage, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (seed_id, description, json.dumps(tags), GoalStage.SEED.value, now, now)
        )
        if tension_ids:
            for tid in tension_ids:
                self.conn.execute(
                    "INSERT OR IGNORE INTO seed_tensions (seed_id, tension_id) VALUES (?, ?)",
                    (seed_id, tid)
                )
        log_event(self.conn, Event(
            event_type=EventType.SEED_PLANTED.value,
            entity_id=seed_id,
            payload={"description": description, "tags": tags},
            cycle=cycle
        ))
        self.conn.commit()
        return seed_id
    
    def update_recurrence(self, seed_id: str, cycle: int = 0):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE goal_seeds SET recurrence = recurrence + 1, updated_at = ? WHERE id = ?",
            (now, seed_id)
        )
        seed = self.conn.execute("SELECT * FROM goal_seeds WHERE id = ?", (seed_id,)).fetchone()
        if seed and seed["recurrence"] >= self.cfg.get("min_recurrence", 5):
            if seed["stage"] == GoalStage.SEED.value:
                self.conn.execute(
                    "UPDATE goal_seeds SET stage = ? WHERE id = ?",
                    (GoalStage.ACCUMULATING.value, seed_id)
                )
        self.conn.commit()
    
    def detect_pattern(self, seed_id: str, coherence: float, cycle: int = 0):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE goal_seeds SET stage = ?, pattern_coherence = ?, updated_at = ? WHERE id = ?",
            (GoalStage.PATTERN_DETECTED.value, coherence, now, seed_id)
        )
        log_event(self.conn, Event(
            event_type=EventType.PATTERN_DETECTED.value,
            entity_id=seed_id,
            payload={"coherence": coherence},
            cycle=cycle
        ))
        self.conn.commit()
    
    def incubate(self, seed_id: str, cycle: int = 0):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """UPDATE goal_seeds SET stage = ?, incubation_cycles = incubation_cycles + 1, 
               updated_at = ? WHERE id = ?""",
            (GoalStage.INCUBATING.value, now, seed_id)
        )
        self.conn.commit()
    
    def test_threshold(self, seed_id: str, cycle: int = 0) -> bool:
        seed = dict(self.conn.execute("SELECT * FROM goal_seeds WHERE id = ?", (seed_id,)).fetchone())
        
        # Count linked tensions' total pressure and count
        linked = self.conn.execute(
            """SELECT SUM(t.pressure) as total_pressure, COUNT(*) as count
               FROM seed_tensions st JOIN tensions t ON st.tension_id = t.id
               WHERE st.seed_id = ?""",
            (seed_id,)
        ).fetchone()
        
        total_tensions = self.conn.execute(
            "SELECT COUNT(*) as c FROM tensions WHERE status IN ('open', 'incubating')"
        ).fetchone()["c"]
        
        linked_count = linked["count"] or 0
        linked_pressure = linked["total_pressure"] or 0
        
        # === GATE 1: Minimum evidence threshold ===
        # Must be linked to at least min_linked_tensions tensions
        min_linked = self.cfg.get("min_linked_tensions", 3)
        if linked_count < min_linked:
            self._reset_threshold(seed_id)
            return False
        
        # === GATE 2: Hit rate check ===
        # Hit rate = fraction of tensions this seed is relevant to
        # Too high (>0.8) = generic, too low (<0.1) = no evidence
        hit_rate = linked_count / total_tensions if total_tensions > 0 else 0.0
        min_hit_rate = self.cfg.get("min_hit_rate", 0.15)
        max_hit_rate = self.cfg.get("max_hit_rate", 0.80)
        
        if hit_rate < min_hit_rate or hit_rate > max_hit_rate:
            self._reset_threshold(seed_id)
            return False
        
        # === GATE 3: Pattern coherence check ===
        min_coherence = self.cfg.get("min_coherence", 0.3)
        if seed["pattern_coherence"] < min_coherence:
            self._reset_threshold(seed_id)
            return False
        
        # === Compute commitment pressure (only if gates pass) ===
        accumulated_friction = linked_pressure * seed["recurrence"]
        pattern_coherence = seed["pattern_coherence"]
        scarcity_weight = 1.0  # can be modulated by body budget
        expected_relief = min(accumulated_friction * 0.3, 1.0)
        
        # Exclusivity bonus: seeds in the sweet spot (20-60% hit rate) get more credit
        exclusivity_bonus = 1.0
        if 0.2 <= hit_rate <= 0.6:
            exclusivity_bonus = 1.5  # sweet spot
        elif hit_rate > 0.6:
            exclusivity_bonus = 0.5  # too generic
        
        social_resistance = seed["social_resistance"] * self.cfg.get("social_resistance_weight", 0.3)
        switch_cost = seed["switch_cost"] * self.cfg.get("switch_cost_weight", 0.2)
        
        commitment_pressure = (
            accumulated_friction * pattern_coherence * scarcity_weight * expected_relief * exclusivity_bonus
        ) - social_resistance - switch_cost
        
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "UPDATE goal_seeds SET commitment_pressure = ?, updated_at = ? WHERE id = ?",
            (commitment_pressure, now, seed_id)
        )
        
        threshold = self.cfg.get("commitment_threshold", 0.65)
        if commitment_pressure >= threshold:
            seed_data = dict(self.conn.execute("SELECT * FROM goal_seeds WHERE id = ?", (seed_id,)).fetchone())
            cycles_above = seed_data["threshold_cycles_above"] + 1
            self.conn.execute(
                "UPDATE goal_seeds SET threshold_cycles_above = ? WHERE id = ?",
                (cycles_above, seed_id)
            )
            
            min_cycles = self.cfg.get("min_incubation_cycles", 3)
            if cycles_above >= min_cycles:
                self.conn.execute(
                    "UPDATE goal_seeds SET stage = ? WHERE id = ?",
                    (GoalStage.COMMITTED.value, seed_id)
                )
                log_event(self.conn, Event(
                    event_type=EventType.GOAL_COMMITTED.value,
                    entity_id=seed_id,
                    payload={
                        "commitment_pressure": commitment_pressure,
                        "cycles_above": cycles_above,
                        "hit_rate": hit_rate,
                        "linked_tensions": linked_count,
                        "exclusivity_bonus": exclusivity_bonus,
                    },
                    cycle=cycle
                ))
                self.conn.commit()
                return True
        else:
            self._reset_threshold(seed_id)
        
        self.conn.commit()
        return False
    
    def _reset_threshold(self, seed_id: str):
        """Reset threshold counter when seed falls below commitment threshold."""
        self.conn.execute(
            "UPDATE goal_seeds SET threshold_cycles_above = 0 WHERE id = ?",
            (seed_id,)
        )
        self.conn.commit()

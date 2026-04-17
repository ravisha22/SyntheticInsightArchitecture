"""Dream Engine — offline recombination and incubation."""
import random
from datetime import datetime
from ..schema import log_event, Event, EventType

class DreamEngine:
    def __init__(self, conn, model_adapter, seed: int = 42):
        self.conn = conn
        self.model = model_adapter
        self.rng = random.Random(seed)
    
    def run_dream_cycle(self, cycle: int = 0) -> list:
        # Gather high-pressure tensions and recent concepts
        tensions = self.conn.execute(
            "SELECT id, title, description FROM tensions WHERE status = 'incubating' ORDER BY pressure DESC LIMIT 5"
        ).fetchall()
        
        concepts = self.conn.execute(
            "SELECT id, label, domain FROM concepts ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        
        recombinations = []
        if tensions and concepts:
            # Random recombination of tension-concept pairs
            for t in tensions:
                if concepts:
                    c = self.rng.choice(concepts)
                    similarity = self.model.score_similarity(t["title"], c["label"])
                    recombinations.append({
                        "tension_id": t["id"],
                        "concept_id": c["id"],
                        "similarity": similarity,
                        "blend": f"{t['title']} × {c['label']}"
                    })
        
        log_event(self.conn, Event(
            event_type=EventType.DREAM_RUN.value,
            entity_id="dream",
            payload={"recombinations": len(recombinations)},
            cycle=cycle
        ))
        self.conn.commit()
        
        return recombinations

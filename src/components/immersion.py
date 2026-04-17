"""Deep Immersion Engine — domain knowledge absorption."""
import uuid
from datetime import datetime
from ..schema import log_event, Event, EventType

class ImmersionEngine:
    def __init__(self, conn, model_adapter):
        self.conn = conn
        self.model = model_adapter
    
    def absorb(self, text: str, domain: str = "general", cycle: int = 0) -> list:
        structure = self.model.extract_structure(text)
        now = datetime.utcnow().isoformat()
        concept_ids = []
        
        for entity in structure.get("entities", []):
            cid = f"C-{uuid.uuid4().hex[:8]}"
            self.conn.execute(
                "INSERT OR IGNORE INTO concepts (id, label, domain, abstraction_level, created_at) VALUES (?, ?, ?, 'concrete', ?)",
                (cid, entity, domain, now)
            )
            concept_ids.append(cid)
        
        # Create relations between co-occurring concepts
        for i in range(len(concept_ids)):
            for j in range(i + 1, len(concept_ids)):
                self.conn.execute(
                    "INSERT OR IGNORE INTO relations (src, dst, rel_type, weight) VALUES (?, ?, 'co_occurs', 1.0)",
                    (concept_ids[i], concept_ids[j])
                )
        
        self.conn.commit()
        return concept_ids

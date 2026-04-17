"""Collision Search — cross-domain structural mapping."""
from ..schema import log_event, Event, EventType

class CollisionSearch:
    def __init__(self, conn, model_adapter):
        self.conn = conn
        self.model = model_adapter
    
    def search_collisions(self, cycle: int = 0) -> list:
        # Get concepts from different domains
        domains = self.conn.execute(
            "SELECT DISTINCT domain FROM concepts WHERE domain IS NOT NULL"
        ).fetchall()
        
        if len(domains) < 2:
            return []
        
        collisions = []
        concepts_by_domain = {}
        for d in domains:
            concepts_by_domain[d["domain"]] = self.conn.execute(
                "SELECT * FROM concepts WHERE domain = ?", (d["domain"],)
            ).fetchall()
        
        domain_list = list(concepts_by_domain.keys())
        for i in range(len(domain_list)):
            for j in range(i + 1, len(domain_list)):
                d1, d2 = domain_list[i], domain_list[j]
                for c1 in concepts_by_domain[d1][:3]:
                    for c2 in concepts_by_domain[d2][:3]:
                        sim = self.model.score_similarity(c1["label"], c2["label"])
                        if sim > 0.15:
                            collisions.append({
                                "concept_a": c1["id"],
                                "concept_b": c2["id"],
                                "domain_a": d1,
                                "domain_b": d2,
                                "similarity": sim,
                            })
                            log_event(self.conn, Event(
                                event_type=EventType.COLLISION_DETECTED.value,
                                entity_id=f"{c1['id']}:{c2['id']}",
                                payload={"similarity": sim, "domains": [d1, d2]},
                                cycle=cycle
                            ))
        
        self.conn.commit()
        return collisions

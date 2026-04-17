"""Deterministic mock adapter — no LLM required."""
import hashlib
import random
from typing import List, Dict, Any
from .base import ModelAdapter

class MockAdapter(ModelAdapter):
    """Deterministic adapter that uses hashing and rules instead of LLM calls.
    Enables full system testing without any model dependency."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
    
    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        h = hashlib.sha256((prompt + system).encode()).hexdigest()[:8]
        return f"[mock-generated-{h}] Response to: {prompt[:100]}"
    
    def score_similarity(self, text_a: str, text_b: str) -> float:
        # Simple word overlap similarity
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0
    
    def extract_structure(self, text: str) -> Dict[str, Any]:
        words = text.lower().split()
        return {
            "entities": list(set(w for w in words if len(w) > 5))[:10],
            "relations": [],
            "key_terms": words[:5],
            "hash": hashlib.sha256(text.encode()).hexdigest()[:16]
        }
    
    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        scores = {}
        words = set(text.lower().split())
        for cat in categories:
            cat_words = set(cat.lower().split())
            overlap = len(words & cat_words)
            scores[cat] = min(0.3 + overlap * 0.2, 1.0)
        return scores

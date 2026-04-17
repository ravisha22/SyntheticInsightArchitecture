"""Ollama adapter — optional LLM integration."""
import requests
from typing import List, Dict, Any
from .base import ModelAdapter

class OllamaAdapter(ModelAdapter):
    """Adapter for local Ollama LLM server."""
    
    def __init__(self, config: dict):
        self.model = config.get("ollama_model", "llama3.1:8b-instruct")
        self.base_url = config.get("ollama_url", "http://localhost:11434")
        self.temperature = config.get("temperature", 0.7)
    
    def generate(self, prompt: str, system: str = "", temperature: float = None) -> str:
        temp = temperature if temperature is not None else self.temperature
        try:
            resp = requests.post(f"{self.base_url}/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "temperature": temp,
                "stream": False
            }, timeout=60)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            return f"[ollama-error] {e}"
    
    def score_similarity(self, text_a: str, text_b: str) -> float:
        prompt = f"Rate the semantic similarity between these two texts on a scale of 0 to 1:\nText A: {text_a}\nText B: {text_b}\nRespond with only a number between 0 and 1."
        result = self.generate(prompt, temperature=0.0)
        try:
            return float(result.strip())
        except ValueError:
            return 0.5
    
    def extract_structure(self, text: str) -> Dict[str, Any]:
        prompt = f"Extract entities, relations, and key terms from this text as JSON:\n{text}"
        result = self.generate(prompt, temperature=0.0)
        try:
            import json
            return json.loads(result)
        except (ValueError, Exception):
            return {"entities": [], "relations": [], "key_terms": [], "raw": result}
    
    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        cats = ", ".join(categories)
        prompt = f"Classify this text into these categories with confidence scores (0-1) as JSON:\nCategories: {cats}\nText: {text}"
        result = self.generate(prompt, temperature=0.0)
        try:
            import json
            return json.loads(result)
        except (ValueError, Exception):
            return {cat: 0.5 for cat in categories}

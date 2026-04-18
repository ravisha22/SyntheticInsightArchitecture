"""Ollama adapter — optional LLM integration."""
import json
import re
import requests
from typing import List, Dict, Any
from .base import ModelAdapter


def _extract_json_from_text(text: str) -> dict:
    """Extract JSON from LLM text that may include markdown blocks."""
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    for pat in [r"```json\s*\n?(.*?)```", r"```\s*\n?(.*?)```"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                continue
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break
    return {}


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
            return json.loads(result)
        except (ValueError, Exception):
            return {"entities": [], "relations": [], "key_terms": [], "raw": result}
    
    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        cats = ", ".join(categories)
        prompt = f"Classify this text into these categories with confidence scores (0-1) as JSON:\nCategories: {cats}\nText: {text}"
        result = self.generate(prompt, temperature=0.0)
        try:
            return json.loads(result)
        except (ValueError, Exception):
            return {cat: 0.5 for cat in categories}

    def analyze(self, system: str, user: str, json_schema: dict = None) -> dict:
        """Send system+user prompt to Ollama and parse structured JSON response."""
        try:
            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": user,
                "system": system,
                "temperature": 0.3,
                "stream": False,
            }
            # Request JSON mode if available (Ollama ≥0.1.24)
            if json_schema:
                payload["format"] = "json"
            else:
                payload["format"] = "json"

            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            raw_text = resp.json().get("response", "")
            return _extract_json_from_text(raw_text)
        except Exception as e:
            return {"error": str(e)}

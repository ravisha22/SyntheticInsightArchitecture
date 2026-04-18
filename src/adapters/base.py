"""Abstract model adapter interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        """Generate text completion."""
        pass
    
    @abstractmethod
    def score_similarity(self, text_a: str, text_b: str) -> float:
        """Score semantic similarity between two texts (0-1)."""
        pass
    
    @abstractmethod
    def extract_structure(self, text: str) -> Dict[str, Any]:
        """Extract structural representation from text."""
        pass
    
    @abstractmethod
    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        """Classify text into categories with confidence scores."""
        pass

    @abstractmethod
    def analyze(self, system: str, user: str, json_schema: dict = None) -> dict:
        """Generate a structured JSON response."""
        pass

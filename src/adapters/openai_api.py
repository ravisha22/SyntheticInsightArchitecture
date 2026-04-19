"""OpenAI-compatible API adapter — works with any provider that supports /v1/chat/completions."""
import json
import os
import re
import time
from typing import Any, Dict, List

import requests

from .base import ModelAdapter


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM text that may include markdown blocks."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    for pat in [r"```json\s*\n?(.*?)```", r"```\s*\n?(.*?)```"]:
        match = re.search(pat, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    start = text.find("{")
    if start != -1:
        depth = 0
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : index + 1])
                except json.JSONDecodeError:
                    break
    return {}


class OpenAIAdapter(ModelAdapter):
    """Adapter for any OpenAI-compatible API (OpenAI, Azure, Groq, Together, vLLM, LM Studio, Ollama)."""

    def __init__(self, config: dict):
        self.api_key = config.get("api_key") or os.environ.get("SIA_API_KEY", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        self.model = config.get("model", "gpt-4o")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 4096)
        self.timeout = config.get("timeout", 120)
        self.api_version = config.get("api_version", "2024-02-15-preview")

    def _is_azure(self) -> bool:
        return "openai.azure.com" in self.base_url and "/openai/deployments/" in self.base_url

    def _endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            endpoint = self.base_url
        else:
            endpoint = f"{self.base_url}/chat/completions"

        if self._is_azure() and "api-version=" not in endpoint:
            separator = "&" if "?" in endpoint else "?"
            endpoint = f"{endpoint}{separator}api-version={self.api_version}"
        return endpoint

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
            return "".join(parts).strip()
        if content is None:
            return ""
        return str(content)

    def _chat(self, messages: list, temperature: float = None, json_mode: bool = False) -> str:
        """Send a chat completion request with retry."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            if self._is_azure():
                headers["api-key"] = self.api_key
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        transient_statuses = {408, 429, 500, 502, 503, 504}

        for attempt in range(3):
            try:
                response = requests.post(
                    self._endpoint(),
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code in transient_statuses:
                    raise requests.HTTPError(
                        f"Transient HTTP {response.status_code}: {response.text[:200]}",
                        response=response,
                    )
                response.raise_for_status()
                body = response.json()
                choices = body.get("choices") or []
                if not choices:
                    return ""
                message = choices[0].get("message", {})
                return self._content_to_text(message.get("content", ""))
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError):
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return ""
            except Exception:
                return ""

        return ""

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._chat(messages, temperature=temperature)

    def score_similarity(self, text_a: str, text_b: str) -> float:
        prompt = (
            "Rate the semantic similarity between these two texts on a scale of 0 to 1.\n"
            f"Text A: {text_a}\n"
            f"Text B: {text_b}\n"
            "Respond with only a number between 0 and 1."
        )
        result = self.generate(prompt, temperature=0.0)
        match = re.search(r"-?\d+(?:\.\d+)?", result or "")
        if not match:
            return 0.5
        try:
            return max(0.0, min(1.0, float(match.group(0))))
        except ValueError:
            return 0.5

    def extract_structure(self, text: str) -> Dict[str, Any]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract entities, relations, and key terms from the user text. "
                    "Return only a JSON object with keys entities, relations, and key_terms."
                ),
            },
            {"role": "user", "content": text},
        ]
        result = self._chat(messages, temperature=0.0, json_mode=True)
        parsed = _extract_json(result)
        if parsed:
            parsed.setdefault("entities", [])
            parsed.setdefault("relations", [])
            parsed.setdefault("key_terms", [])
            return parsed
        return {"entities": [], "relations": [], "key_terms": [], "raw": result}

    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        messages = [
            {
                "role": "system",
                "content": (
                    "Classify the user text into the provided categories. "
                    "Return only a JSON object whose keys are the categories and whose values are confidence scores from 0 to 1."
                ),
            },
            {
                "role": "user",
                "content": f"Categories: {categories}\nText: {text}",
            },
        ]
        result = self._chat(messages, temperature=0.0, json_mode=True)
        parsed = _extract_json(result)
        if not parsed:
            return {category: 0.5 for category in categories}

        scores = {}
        for category in categories:
            try:
                scores[category] = max(0.0, min(1.0, float(parsed.get(category, 0.5))))
            except (TypeError, ValueError):
                scores[category] = 0.5
        return scores

    def analyze(self, system: str, user: str, json_schema: dict = None) -> dict:
        try:
            system_prompt = f"{system}\nReturn only a valid JSON object."
            if json_schema:
                system_prompt += f"\nMatch this schema as closely as possible:\n{json.dumps(json_schema, indent=2)}"

            result = self._chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                json_mode=True,
            )
            return _extract_json(result)
        except Exception:
            return {}

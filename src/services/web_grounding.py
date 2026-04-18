"""Web grounding — search external evidence to validate risk assessments."""
import requests
from typing import List, Dict


class WebGrounding:
    """MVP: searches GitHub Issues API for corroborating evidence."""

    def __init__(self, repo: str = "pandas-dev/pandas", timeout: int = 10):
        self.repo = repo
        self.base_url = "https://api.github.com/search/issues"
        self.timeout = timeout

    def search_evidence(self, query: str) -> List[Dict]:
        """Search GitHub issues for evidence about a pattern/issue.

        Returns list of {source, claim, relevance, recency}.
        """
        params = {
            "q": f"{query} repo:{self.repo}",
            "per_page": 5,
            "sort": "reactions",
            "order": "desc",
        }
        headers = {"Accept": "application/vnd.github.v3+json"}

        try:
            resp = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception:
            return []

        results = []
        for item in items[:5]:
            body = (item.get("body") or "")[:200]
            results.append({
                "source": item.get("html_url", ""),
                "claim": item.get("title", ""),
                "relevance": body,
                "recency": item.get("created_at", ""),
            })
        return results

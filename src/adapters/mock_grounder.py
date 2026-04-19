"""Deterministic grounding adapter for evaluation flows."""

from __future__ import annotations


class MockGrounder:
    """Deterministic mock grounder for evaluation."""

    def __init__(self, evidence_keywords=None):
        """
        evidence_keywords: list of keyword strings. If a search query contains
        any of these keywords, return mock evidence. Otherwise return empty list.
        This lets us selectively boost "right" clusters.
        """
        self.evidence_keywords = [kw.lower() for kw in (evidence_keywords or [])]

    def search_evidence(self, query: str) -> list[dict]:
        query_lower = query.lower()
        if not self.evidence_keywords or any(kw in query_lower for kw in self.evidence_keywords):
            return [
                {
                    "source": "https://example.com/evidence/1",
                    "claim": f"Corroborating evidence for: {query[:60]}",
                    "relevance": "Multiple independent sources confirm this pattern",
                    "recency": "2026-01-15T00:00:00Z",
                },
                {
                    "source": "https://example.com/evidence/2",
                    "claim": f"Supporting analysis of: {query[:60]}",
                    "relevance": "Prior interventions targeting this root cause showed measurable improvement",
                    "recency": "2025-11-01T00:00:00Z",
                },
            ]
        return []

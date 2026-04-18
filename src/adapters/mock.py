"""Deterministic mock adapter — no LLM required."""
import hashlib
import json
import random
import re
from typing import List, Dict, Any
from .base import ModelAdapter

# Severity keyword heuristics
_SEVERITY_RULES = [
    (r"security|vulnerability|injection|auth|CVE", "existential"),
    (r"crash|error|fail|broken|corrupt|data.?loss", "major"),
    (r"performance|slow|memory|leak|regression", "major"),
    (r"warning|deprecat|FutureWarning", "minor"),
    (r"typo|doc|documentation|example", "cosmetic"),
]

_TIER_ORDER = {"existential": 0, "major": 1, "moderate": 2, "minor": 3, "cosmetic": 4}

_GENERIC_ROOT_RULES = [
    {
        "pattern": r"security|vulnerability|injection|auth|cve|xss|csrf|credential|token|permission|bypass",
        "root": "security_boundary",
        "layer": "core_internals",
        "severity": "existential",
        "mechanism": "Weak security boundaries allow failures to cascade across the system",
        "blast_radius": "cascading",
    },
    {
        "pattern": r"copy|view|shared memory|mutation|consistency|chained.?assign|state",
        "root": "state_semantics",
        "layer": "core_internals",
        "severity": "major",
        "mechanism": "Ambiguous state or mutation semantics cause inconsistent behavior across operations",
        "blast_radius": "feature_broken",
    },
    {
        "pattern": r"performance|slow|memory|leak|latency|throughput|regression|oom|deadlock|timeout",
        "root": "performance_reliability",
        "layer": "core_internals",
        "severity": "major",
        "mechanism": "Performance and reliability weaknesses degrade service quality under load",
        "blast_radius": "service_degradation",
    },
    {
        "pattern": r"nullable|null|none|type|dtype|schema|coercion|serialization|deserialization",
        "root": "type_system",
        "layer": "core_internals",
        "severity": "major",
        "mechanism": "Type-system inconsistencies create fragile behavior at data boundaries",
        "blast_radius": "feature_broken",
    },
    {
        "pattern": r"network|connection|socket|proxy|dns|http|tls|ssl|retry|request|response",
        "root": "network_reliability",
        "layer": "integration",
        "severity": "major",
        "mechanism": "Network and protocol handling weaknesses break integration reliability",
        "blast_radius": "service_degradation",
    },
    {
        "pattern": r"index|query|lookup|search|filter|path|routing",
        "root": "access_path_logic",
        "layer": "api_surface",
        "severity": "moderate",
        "mechanism": "Access-path logic is inconsistent across similar usage patterns",
        "blast_radius": "feature_broken",
    },
    {
        "pattern": r"parse|parser|csv|json|io|import|export|encoding|format",
        "root": "io_contract",
        "layer": "integration",
        "severity": "moderate",
        "mechanism": "I/O contract mismatches cause parsing and interoperability failures",
        "blast_radius": "feature_broken",
    },
]

_GENERIC_RULE_INDEX = {rule["root"]: rule for rule in _GENERIC_ROOT_RULES}


class MockAdapter(ModelAdapter):
    """Deterministic adapter that uses hashing and rules instead of LLM calls.
    Enables full system testing without any model dependency."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
    
    def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        h = hashlib.sha256((prompt + system).encode()).hexdigest()[:8]
        return f"[mock-generated-{h}] Response to: {prompt[:100]}"
    
    def score_similarity(self, text_a: str, text_b: str) -> float:
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

    # ── Structured analysis for the LLM pipeline ───────────────────

    def analyze(self, system: str, user: str, json_schema: dict = None) -> dict:
        """Produce deterministic structured JSON based on prompt content."""
        system_lower = system.lower()
        # Detect which stage we're in from the system prompt
        if "analyzing software issues" in system_lower:
            return self._analyze_issue(user)
        elif "issue patterns" in system_lower or "signal patterns" in system_lower:
            return self._detect_patterns(user)
        elif "scarcity" in system_lower:
            return self._prioritize(user)
        elif "validating risk" in system_lower:
            return self._evidence_grounding(user)

        return {"error": "unrecognized prompt type"}

    def _match_generic_rule(self, text: str) -> dict | None:
        for rule in _GENERIC_ROOT_RULES:
            if re.search(rule["pattern"], text, re.IGNORECASE):
                return rule
        return None

    def _analyze_issue(self, user_prompt: str) -> dict:
        title_match = re.search(r"Issue #-?\d+:\s*(.+)", user_prompt)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title_match = re.search(r"Title:\s*(.+)", user_prompt)
            title = title_match.group(1).strip() if title_match else ""
        desc_match = re.search(
            r"Description(?: \(snippet\))?:\s*(.*?)(?:\nMetadata:|\nReturn a single JSON object|$)",
            user_prompt,
            re.DOTALL,
        )
        description = desc_match.group(1).strip() if desc_match else ""
        labels_match = re.search(r"Labels:\s*(.+)", user_prompt)
        labels_str = labels_match.group(1).strip() if labels_match else ""
        labels = [l.strip() for l in labels_str.split(",") if l.strip()]
        combined = " ".join(part for part in (title, description, labels_str) if part)

        # Determine severity from generic issue cues
        severity = "moderate"
        for pattern, tier in _SEVERITY_RULES:
            if re.search(pattern, combined, re.IGNORECASE):
                severity = tier
                break

        rule = self._match_generic_rule(combined)
        root = rule["root"] if rule else "general"
        architectural_layer = rule["layer"] if rule else "api_surface"
        blast_radius = rule["blast_radius"] if rule else {
            "existential": "cascading",
            "major": "service_degradation",
            "moderate": "feature_broken",
            "minor": "inconvenience",
            "cosmetic": "none",
        }.get(severity, "none")
        failure_mode = rule["mechanism"] if rule else f"Ongoing failures in {root.replace('_', ' ')}"
        is_symptom = bool(labels) and root != "general"
        affected_scope = {
            "existential": "all_users",
            "major": "majority",
            "moderate": "significant_minority",
            "minor": "edge_case",
            "cosmetic": "developer_only",
        }.get(severity, "edge_case")

        # Deterministic confidence from hash
        h = int(hashlib.sha256(title.encode()).hexdigest()[:4], 16)
        confidence = 0.6 + (h % 35) / 100.0

        return {
            "severity_tier": severity,
            "affected_scope": affected_scope,
            "failure_mode_if_unfixed": failure_mode,
            "blast_radius": blast_radius,
            "architectural_layer": architectural_layer,
            "p_happy_if_fixed": round(0.4 + _TIER_ORDER.get(severity, 2) * -0.05 + 0.3, 2),
            "p_failure_cascade_if_unfixed": round(max(0.0, 0.5 - _TIER_ORDER.get(severity, 2) * 0.1), 2),
            "is_symptom_of_deeper_issue": is_symptom,
            "suspected_root_category": root,
            "confidence": round(confidence, 2),
        }

    def _detect_patterns(self, user_prompt: str) -> dict:
        # Parse issues from the user prompt JSON
        try:
            json_match = re.search(r"Issues:\s*(\[.*?\])\s*\nGroup", user_prompt, re.DOTALL)
            if json_match:
                issues = json.loads(json_match.group(1))
            else:
                issues = []
        except (json.JSONDecodeError, AttributeError):
            issues = []

        # Group by suspected_root_category
        groups: Dict[str, list] = {}
        unclustered = []
        for iss in issues:
            root = iss.get("suspected_root_category", "general")
            if root and root != "general" and root != "unknown":
                groups.setdefault(root, []).append(iss.get("number"))
            else:
                unclustered.append(iss.get("number"))

        clusters = []
        for root, nums in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
            if len(nums) >= 2:
                rule = _GENERIC_RULE_INDEX.get(root)
                severity = rule["severity"] if rule else "moderate"
                mechanism = rule["mechanism"] if rule else f"Issues in {root.replace('_', ' ')} subsystem"
                clusters.append({
                    "root_cause": f"Shared weakness in {root.replace('_', ' ')}",
                    "mechanism": mechanism,
                    "issue_numbers": nums,
                    "severity_if_unaddressed": severity,
                    "confidence": round(0.65 + min(len(nums), 10) * 0.03, 2),
                })
            else:
                unclustered.extend(nums)

        return {"clusters": clusters, "unclustered_issues": unclustered}

    def _prioritize(self, user_prompt: str) -> dict:
        # Parse budget
        budget_match = re.search(r"budget of (\d+)", user_prompt)
        budget = int(budget_match.group(1)) if budget_match else 5

        # Parse clusters from prompt
        try:
            cluster_match = re.search(
                r"Root-Cause Clusters:\s*(\{.*?\})\s*\nAll analyzed",
                user_prompt,
                re.DOTALL,
            )
            if cluster_match:
                cluster_data = json.loads(cluster_match.group(1))
            else:
                cluster_data = {"clusters": []}
        except (json.JSONDecodeError, AttributeError):
            cluster_data = {"clusters": []}

        clusters = cluster_data.get("clusters", [])

        # Sort by severity then by issue count
        def cluster_score(c):
            sev = {"existential": 0, "major": 1, "moderate": 2, "minor": 3}
            return (sev.get(c.get("severity_if_unaddressed", "moderate"), 2), -len(c.get("issue_numbers", [])))

        sorted_clusters = sorted(clusters, key=cluster_score)

        chosen = []
        deferred = []
        for i, cluster in enumerate(sorted_clusters):
            entry_target = cluster.get("root_cause", "unknown")
            entry_issues = cluster.get("issue_numbers", [])
            sev = cluster.get("severity_if_unaddressed", "moderate")
            if i < budget:
                chosen.append({
                    "target": entry_target,
                    "why": f"Addresses {len(entry_issues)} issues with {sev} severity",
                    "issues_resolved": entry_issues,
                    "tier": sev,
                    "blast_radius_prevented": f"Prevents {sev} failures in {entry_target}",
                })
            else:
                deferred.append({
                    "target": entry_target,
                    "risk_of_deferral": f"{len(entry_issues)} issues remain unresolved",
                    "why_deferred": f"Lower priority ({sev}) given budget constraints",
                })

        insight = (
            "The highest-leverage architectural change is to address the top-ranked root cause "
            "that combines the highest severity with the broadest issue coverage under current scarcity."
        )
        if chosen:
            insight = (
                f"The highest-leverage architectural change is to address {chosen[0]['target']}, "
                f"because it combines {chosen[0]['tier']} severity with the broadest issue coverage "
                "under current scarcity."
            )

        return {
            "chosen": chosen,
            "deferred": deferred,
            "architectural_insight": insight,
        }

    def _evidence_grounding(self, user_prompt: str) -> dict:
        return {
            "revised_severity": "major",
            "supporting_evidence": [
                "Multiple community reports confirm this pattern",
                "Similar issues found in related projects",
            ],
            "confidence_change": "increased",
            "new_confidence": 0.85,
        }

"""Pandas-specific deterministic mock adapter for the evaluation harness."""
import hashlib
import json
import re

from .mock import MockAdapter, _SEVERITY_RULES, _TIER_ORDER

# Label-to-root-cause mapping for the pandas evaluation corpus
_LABEL_ROOT_CAUSE = {
    "Copy / view semantics": "copy_view_semantics",
    "Copy/View": "copy_view_semantics",
    "ExtensionArray": "extension_array_internals",
    "Performance": "performance_internals",
    "Indexing": "indexing_api",
    "Categorical": "categorical_internals",
    "Timedelta": "datetime_internals",
    "Datetime": "datetime_internals",
    "Missing-data": "missing_data_handling",
    "NA": "missing_data_handling",
    "Nullable": "extension_array_internals",
    "Dtype Conversions": "dtype_conversion",
    "MultiIndex": "indexing_api",
    "Reshaping": "reshaping_internals",
    "Groupby": "groupby_internals",
    "IO CSV": "io_internals",
    "IO JSON": "io_internals",
}


class PandasMockAdapter(MockAdapter):
    """Deterministic test double tuned to the pandas evaluation corpus."""

    def _analyze_issue(self, user_prompt: str) -> dict:
        title_match = re.search(r"Issue #-?\d+:\s*(.+)", user_prompt)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title_match = re.search(r"Title:\s*(.+)", user_prompt)
            title = title_match.group(1).strip() if title_match else ""
        labels_match = re.search(r"Labels:\s*(.+)", user_prompt)
        labels_str = labels_match.group(1).strip() if labels_match else ""
        labels = [l.strip() for l in labels_str.split(",") if l.strip()]

        severity = "moderate"
        for pattern, tier in _SEVERITY_RULES:
            if re.search(pattern, title, re.IGNORECASE):
                severity = tier
                break

        root = "general"
        priority_labels = [
            "Copy / view semantics", "Copy/View", "ExtensionArray",
            "Performance", "Missing-data", "NA", "Nullable",
        ]
        for plabel in priority_labels:
            if plabel in labels and plabel in _LABEL_ROOT_CAUSE:
                root = _LABEL_ROOT_CAUSE[plabel]
                break
        else:
            for label in labels:
                if label in _LABEL_ROOT_CAUSE:
                    root = _LABEL_ROOT_CAUSE[label]
                    break

        if root == "general" and re.search(r"copy|view|settingwithcopy|chained.?assign", title, re.IGNORECASE):
            root = "copy_view_semantics"

        is_bug = "Bug" in labels
        is_symptom = is_bug and root != "general"

        scope_map = {
            "existential": "all_users",
            "major": "majority",
            "moderate": "significant_minority",
            "minor": "edge_case",
            "cosmetic": "developer_only",
        }
        blast_map = {
            "existential": "cascading",
            "major": "service_degradation",
            "moderate": "feature_broken",
            "minor": "inconvenience",
            "cosmetic": "none",
        }
        layer_map = {
            "copy_view_semantics": "core_internals",
            "extension_array_internals": "core_internals",
            "performance_internals": "core_internals",
            "indexing_api": "api_surface",
            "datetime_internals": "core_internals",
            "missing_data_handling": "core_internals",
            "dtype_conversion": "core_internals",
            "categorical_internals": "core_internals",
            "groupby_internals": "api_surface",
            "io_internals": "integration",
            "reshaping_internals": "api_surface",
        }

        h = int(hashlib.sha256(title.encode()).hexdigest()[:4], 16)
        confidence = 0.6 + (h % 35) / 100.0

        return {
            "severity_tier": severity,
            "affected_scope": scope_map.get(severity, "edge_case"),
            "failure_mode_if_unfixed": f"Ongoing failures in {root.replace('_', ' ')}",
            "blast_radius": blast_map.get(severity, "none"),
            "architectural_layer": layer_map.get(root, "api_surface"),
            "p_happy_if_fixed": round(0.4 + _TIER_ORDER.get(severity, 2) * -0.05 + 0.3, 2),
            "p_failure_cascade_if_unfixed": round(max(0.0, 0.5 - _TIER_ORDER.get(severity, 2) * 0.1), 2),
            "is_symptom_of_deeper_issue": is_symptom,
            "suspected_root_category": root,
            "confidence": round(confidence, 2),
        }

    def _detect_patterns(self, user_prompt: str) -> dict:
        try:
            json_match = re.search(r"Issues:\s*(\[.*?\])\s*\nGroup", user_prompt, re.DOTALL)
            if json_match:
                issues = json.loads(json_match.group(1))
            else:
                issues = []
        except (json.JSONDecodeError, AttributeError):
            issues = []

        groups: dict[str, list] = {}
        unclustered = []
        for iss in issues:
            root = iss.get("suspected_root_category", "general")
            if root and root != "general" and root != "unknown":
                groups.setdefault(root, []).append(iss.get("number"))
            else:
                unclustered.append(iss.get("number"))

        clusters = []
        severity_map = {
            "copy_view_semantics": "existential",
            "extension_array_internals": "major",
            "performance_internals": "major",
            "indexing_api": "moderate",
            "datetime_internals": "moderate",
            "missing_data_handling": "major",
            "dtype_conversion": "moderate",
            "groupby_internals": "moderate",
            "io_internals": "minor",
        }
        mechanism_map = {
            "copy_view_semantics": "Ambiguous copy vs view semantics cause silent data corruption",
            "extension_array_internals": "ExtensionArray dispatch failures break nullable dtype operations",
            "performance_internals": "Inefficient internal operations cause memory and speed regressions",
            "indexing_api": "Inconsistent indexing API leads to unexpected slicing behavior",
            "datetime_internals": "Datetime/timedelta edge cases in offset and frequency logic",
            "missing_data_handling": "Inconsistent NA propagation across operations",
            "dtype_conversion": "Lossy or incorrect dtype conversions on assignment and merge",
            "groupby_internals": "Groupby dispatch inconsistencies across dtypes",
            "io_internals": "Parser inconsistencies across file format readers",
        }

        for root, nums in sorted(groups.items(), key=lambda item: len(item[1]), reverse=True):
            if len(nums) >= 2:
                clusters.append({
                    "root_cause": f"Shared weakness in {root.replace('_', ' ')}",
                    "mechanism": mechanism_map.get(root, f"Issues in {root.replace('_', ' ')} subsystem"),
                    "issue_numbers": nums,
                    "severity_if_unaddressed": severity_map.get(root, "moderate"),
                    "confidence": round(0.65 + min(len(nums), 10) * 0.03, 2),
                })
            else:
                unclustered.extend(nums)

        return {"clusters": clusters, "unclustered_issues": unclustered}

    def _prioritize(self, user_prompt: str) -> dict:
        budget_match = re.search(r"budget of (\d+)", user_prompt)
        budget = int(budget_match.group(1)) if budget_match else 5

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

        def cluster_score(cluster):
            sev = {"existential": 0, "major": 1, "moderate": 2, "minor": 3}
            return (
                sev.get(cluster.get("severity_if_unaddressed", "moderate"), 2),
                -len(cluster.get("issue_numbers", [])),
            )

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
            "Resolving copy/view semantics ambiguity would eliminate the largest class "
            "of silent data corruption bugs and is the single highest-leverage architectural change."
        )
        if chosen and "copy" not in str(chosen[0].get("target", "")).lower():
            insight = (
                "The most impactful architectural change is to address the root cause "
                "with the highest severity and broadest issue coverage."
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

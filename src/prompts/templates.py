"""Prompt templates for LLM-native analysis pipeline.

Each template returns (system_prompt, user_prompt) pairs.
The prompts ARE the logic layer — they encode reasoning, not Python code.
"""
import json


# ── Stage 1: Individual Issue Analysis ──────────────────────────────

ISSUE_ANALYSIS_SYSTEM = (
    "You are a production engineering decision-maker analyzing software issues and operational signals. "
    "You assess risk, scope, and architectural significance. "
    "Respond ONLY with valid JSON, no commentary."
)


def issue_analysis_user(issue: dict) -> str:
    title = issue.get("title", "")
    body = (issue.get("body", "") or "")[:500]
    labels = ", ".join(issue.get("labels", []))
    number = issue.get("number", "?")
    reference_number = issue.get("reference_number", number)
    signal_id = issue.get("signal_id", number)
    signal_type = issue.get("signal_type", "issue")
    source = issue.get("source", "") or "unknown"
    metadata = json.dumps(issue.get("metadata", {}), indent=1)[:500]

    return f"""Analyze this software issue or operational signal and assess its engineering risk.

Issue #{reference_number}: {title}
Title: {title}
Signal ID: {signal_id}
Signal Type: {signal_type}
Source: {source}
Labels: {labels}
Description (snippet): {body}
Metadata: {metadata}

Return a single JSON object with these fields:
{{
  "severity_tier": "existential|major|moderate|minor|cosmetic",
  "affected_scope": "all_users|majority|significant_minority|edge_case|developer_only",
  "failure_mode_if_unfixed": "description of what breaks",
  "blast_radius": "cascading|service_degradation|feature_broken|inconvenience|none",
  "architectural_layer": "core_internals|api_surface|integration|tooling|documentation",
  "p_happy_if_fixed": <float 0.0-1.0>,
  "p_failure_cascade_if_unfixed": <float 0.0-1.0>,
  "is_symptom_of_deeper_issue": <true or false>,
  "suspected_root_category": "<short string describing root cause category>",
  "confidence": <float 0.0-1.0>
}}"""


# ── Stage 2: Pattern / Root-Cause Clustering ────────────────────────

PATTERN_DETECTION_SYSTEM = (
    "You are an architect analyzing issue and signal patterns. You identify shared root causes "
    "by mechanism, not by wording. Two signals about different features can share a "
    "root cause if they stem from the same design decision. "
    "Respond ONLY with valid JSON, no commentary."
)


def pattern_detection_user(analyzed_issues: list[dict]) -> str:
    summaries = []
    for iss in analyzed_issues:
        summaries.append({
            "number": iss.get("number"),
            "signal_id": iss.get("signal_id", iss.get("number")),
            "signal_type": iss.get("signal_type", "issue"),
            "source": iss.get("source", ""),
            "title": iss.get("title", ""),
            "severity_tier": iss.get("severity_tier", "moderate"),
            "suspected_root_category": iss.get("suspected_root_category", "unknown"),
            "architectural_layer": iss.get("architectural_layer", "unknown"),
            "is_symptom_of_deeper_issue": iss.get("is_symptom_of_deeper_issue", False),
            "labels": iss.get("labels", []),
        })

    return f"""Below are {len(summaries)} analyzed software issues or operational signals. Identify shared root causes by mechanism.

Issues:
{json.dumps(summaries, indent=1)}

Group issues that share a root architectural weakness. Return JSON:
{{
  "clusters": [
    {{
      "root_cause": "description of shared architectural weakness",
      "mechanism": "how the root cause manifests as bugs",
      "issue_numbers": [<list of issue numbers in this cluster>],
      "signal_ids": [<list of canonical signal ids in this cluster>],
      "severity_if_unaddressed": "existential|major|moderate|minor",
      "confidence": <float 0.0-1.0>
    }}
  ],
  "unclustered_issues": [<issue numbers that are genuinely independent>],
  "unclustered_signal_ids": [<canonical signal ids that are genuinely independent>]
}}"""


# ── Stage 3: Scarcity-Driven Prioritization ─────────────────────────

SCARCITY_PRIORITIZATION_SYSTEM = (
    "You are making triage decisions under extreme resource scarcity. "
    "You can only address N problems. Every choice means something else doesn't get fixed. "
    "Think about: what is existential? What cascades? What affects the most users? "
    "What is a single fix that resolves multiple symptoms? "
    "Respond ONLY with valid JSON, no commentary."
)


def scarcity_prioritization_user(
    clusters: dict, analyzed_issues: list[dict], budget: int
) -> str:
    issue_summary = []
    for iss in analyzed_issues:
        issue_summary.append({
            "number": iss.get("number"),
            "signal_id": iss.get("signal_id", iss.get("number")),
            "signal_type": iss.get("signal_type", "issue"),
            "title": iss.get("title", ""),
            "severity_tier": iss.get("severity_tier", "moderate"),
            "blast_radius": iss.get("blast_radius", "none"),
        })

    return f"""You have a budget of {budget} fixes. Choose wisely.

Root-Cause Clusters:
{json.dumps(clusters, indent=1)}

All analyzed issues (summary):
{json.dumps(issue_summary, indent=1)}

Return JSON:
{{
  "chosen": [
    {{
      "target": "what to fix (cluster root cause or individual issue)",
      "why": "reasoning",
      "issues_resolved": [<issue numbers>],
      "signal_ids_resolved": [<canonical signal ids>],
      "tier": "existential|major|moderate",
      "blast_radius_prevented": "description",
      "predicted_outcome": "what should improve if this prioritization is correct"
    }}
  ],
  "deferred": [
    {{
      "target": "what's not being fixed",
      "risk_of_deferral": "description",
      "why_deferred": "reasoning"
    }}
  ],
  "architectural_insight": "The single most impactful architectural change that would prevent the most recurring failures"
}}"""


# ── Stage 4: Evidence Grounding ─────────────────────────────────────

EVIDENCE_GROUNDING_SYSTEM = (
    "You are validating risk assessments against external evidence. "
    "Given search results about known failure patterns, CVEs, and industry practices, "
    "revise your assessment. "
    "Respond ONLY with valid JSON, no commentary."
)


def evidence_grounding_user(cluster: dict, evidence: list[dict]) -> str:
    return f"""Validate this root-cause assessment against external evidence.

Cluster:
{json.dumps(cluster, indent=1)}

External evidence:
{json.dumps(evidence, indent=1)}

Return JSON:
{{
  "revised_severity": "existential|major|moderate|minor",
  "supporting_evidence": ["list of evidence that confirms or changes the assessment"],
  "confidence_change": "increased|decreased|unchanged",
  "new_confidence": <float 0.0-1.0>
}}"""

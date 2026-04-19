"""A/B test: SIA pipeline vs raw LLM prompt on the same signals."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulation.scenarios.hindcast_2008_blinded import (
    OBSERVED_OUTCOMES,
    REAL_ISSUES,
    build_generalized_scenario,
)
from simulation.run_blinded_test import BUDGET, RANDOM_SEED, run_condition, score_text_predictions


def run_pipeline_path():
    """Run signals through the full SIA pipeline and score."""
    scenario = build_generalized_scenario()
    return run_condition("Pipeline", scenario, "ab_pipeline")


def build_raw_prompt():
    """Build the exact prompt a user would paste into a raw LLM."""
    prompt_lines = [
        "You are an analyst. Below are signals collected from public sources available before January 2007.",
        "Analyze them for systemic root causes, cluster shared weaknesses,",
        "and prioritize the top interventions under scarcity.",
        "",
        "Signals:",
        "",
    ]
    for issue in REAL_ISSUES:
        prompt_lines.append(f"Signal {issue['number']}: {issue['title']}")
        prompt_lines.append(f"Source: {issue['source']}")
        prompt_lines.append(f"Type: {issue['signal_type']}")
        prompt_lines.append(f"Body: {issue['body']}")
        prompt_lines.append(f"Labels: {', '.join(issue['labels'])}")
        prompt_lines.append("")

    prompt_lines.extend([
        "Tasks:",
        "1. What are the shared systemic root causes across these signals?",
        "2. Rank the top 3-5 root causes by severity and breadth.",
        "3. For each root cause, what intervention would address it?",
        "4. What is the most dangerous compounding loop?",
        "",
        "Respond with structured JSON containing:",
        '{"root_causes": [{"name": "...", "severity": "...", "signals": [...], "intervention": "...", "predicted_outcome": "..."}]}',
    ])
    return "\n".join(prompt_lines)


def main():
    print("=" * 60)
    print("A/B Test: SIA Pipeline vs Raw LLM Prompt")
    print("Scenario: 2008 Financial Crisis Hindcast")
    print("=" * 60)
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Budget: {BUDGET}")

    print("\n### Pipeline path")
    result = run_pipeline_path()
    score = result["score"]
    print(f"Hits: {score['hit_count']}")
    print(f"Precision: {score['precision']:.3f}")
    print(f"Recall: {score['recall']:.3f}")

    choices = result["report"]["prioritization"].get("chosen", [])
    print(f"\nPipeline identified {len(choices)} root causes:")
    for choice in choices:
        print(
            f"  - {choice['target']} "
            f"(tier: {choice['tier']}, issues: {len(choice.get('issues_resolved', []))})"
        )

    prompt = build_raw_prompt()
    prompt_path = ROOT / "validation" / "ab_raw_prompt.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")

    print("\n### Raw LLM prompt")
    print(prompt)
    print(f"\n### Raw LLM prompt saved to: {prompt_path}")
    raw_response_path = ROOT / "validation" / "ab_raw_response.json"
    print("Send this prompt to any LLM and save the response to:")
    print(f"  {raw_response_path}")
    print("Then rerun this script to score both paths.\n")

    if raw_response_path.exists():
        raw_response = json.loads(raw_response_path.read_text(encoding="utf-8"))
        raw_targets = [rc.get("name", "") for rc in raw_response.get("root_causes", [])]
        raw_score = score_text_predictions(raw_targets, [dict(o) for o in OBSERVED_OUTCOMES])
        print("### Raw LLM path")
        print(f"Root causes identified: {raw_targets}")
        print(f"Hits: {raw_score['hit_count']}")
        print(f"Precision: {raw_score['precision']:.3f}")
        print(f"Recall: {raw_score['recall']:.3f}")
        print()
        print("### Comparison")
        print(f"Pipeline precision: {score['precision']:.3f}")
        print(f"Raw LLM precision: {raw_score['precision']:.3f}")
        print(f"Pipeline recall: {score['recall']:.3f}")
        print(f"Raw LLM recall: {raw_score['recall']:.3f}")
        delta_p = score["precision"] - raw_score["precision"]
        delta_r = score["recall"] - raw_score["recall"]
        print(f"Precision delta (pipeline - raw): {delta_p:+.3f}")
        print(f"Recall delta (pipeline - raw): {delta_r:+.3f}")
    else:
        print("(Raw LLM response not yet available — send the prompt to an LLM first)")


if __name__ == "__main__":
    main()

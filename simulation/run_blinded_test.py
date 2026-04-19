"""Run blinded generalized AnalysisPipeline tests against cross-domain signal corpora."""
from __future__ import annotations

import importlib
import json
import os
import random
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation.baselines import run_baselines
from src.adapters.mock import MockAdapter
from src.schema import init_db
from src.services.analysis_pipeline import AnalysisPipeline

# Domain registry — each entry maps to a scenario module that exports the
# standard builder contract (build_generalized_scenario, build_decoy_seed_scenario,
# build_tag_shuffle_control, build_nonconvergent_scenario).
DOMAIN_REGISTRY: list[dict] = [
    {
        "slug": "social_civic",
        "label": "Social / Civic",
        "module": "simulation.scenarios.generalized_blinded",
    },
    {
        "slug": "code_engineering",
        "label": "Code / Engineering",
        "module": "simulation.scenarios.code_engineering_blinded",
    },
    {
        "slug": "product_community",
        "label": "Product / Community",
        "module": "simulation.scenarios.product_community_blinded",
    },
]

RANDOM_SEED = 7
BUDGET = 5
OUTPUT_DIR = ROOT / "simulation" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def set_reproducible_seed() -> None:
    random.seed(RANDOM_SEED)
    if np is not None:
        np.random.seed(RANDOM_SEED)


def grounding_config() -> dict:
    enabled = os.getenv("SIA_ENABLE_GROUNDING", "").strip().lower() in {"1", "true", "yes"}
    repo = os.getenv("SIA_GROUNDING_REPO", "").strip()
    if not enabled or not repo:
        return {}
    return {"grounding": {"enabled": True, "repo": repo}}


def scenario_to_signals(issues: list[dict], slug: str) -> list[dict]:
    signals = []
    for issue in issues:
        labels = list(issue.get("labels", []))
        source = issue.get("source", "scenario")
        signals.append(
            {
                "signal_id": str(issue.get("signal_id", f"{source}:{issue['number']}")),
                "signal_type": issue.get("signal_type", "other"),
                "source": source,
                "title": issue["title"],
                "body": issue.get("body", ""),
                "tags": list(issue.get("tags", labels)),
                "metadata": {
                    "labels": labels,
                    "seed_hypothesis": issue.get("seed_hypothesis", ""),
                },
            }
        )
    return signals


def run_condition(
    name: str,
    scenario: dict,
    slug: str,
    observed_outcomes: list[dict] | None = None,
) -> dict:
    db_path = OUTPUT_DIR / f"{slug}.db"
    if db_path.exists():
        db_path.unlink()

    conn = init_db(str(db_path))
    pipeline = AnalysisPipeline(
        conn,
        MockAdapter(seed=RANDOM_SEED),
        config=grounding_config(),
    )
    report = pipeline.run_full_pipeline(
        scenario_to_signals(scenario["issues"], slug),
        budget=BUDGET,
    )
    scoped_outcomes = [dict(outcome) for outcome in (observed_outcomes or scenario.get("observed_outcomes", []))]
    run_id = report["prioritization"].get("run_id")
    score = (
        pipeline.score_predictions(run_id, scoped_outcomes)
        if run_id
        else {
            "run_id": None,
            "hit_count": 0,
            "miss_count": 0,
            "observed_positive_count": len(scoped_outcomes),
            "precision": 0.0,
            "recall": 0.0,
            "scored_predictions": [],
            "unmatched_outcomes": scoped_outcomes,
        }
    )
    conn.close()

    return {
        "name": name,
        "issues": scenario["issues"],
        "report": report,
        "score": score,
        "observed_outcomes": scoped_outcomes,
        "db_path": str(db_path),
        "grounding_enabled": bool(grounding_config()),
    }


def chosen_targets(result: dict) -> list[str]:
    return [choice.get("target", "") for choice in result["report"]["prioritization"].get("chosen", [])]


def condition_a_pass(result: dict) -> bool:
    expected_hits = result["score"]["observed_positive_count"]
    return expected_hits > 0 and result["score"]["hit_count"] == expected_hits


def condition_b_pass(real_result: dict, decoy_result: dict) -> tuple[bool, list[str]]:
    real_targets = chosen_targets(real_result)
    decoy_targets = chosen_targets(decoy_result)
    drift = sorted(set(real_targets) ^ set(decoy_targets))
    return real_targets == decoy_targets, drift


def condition_c_pass(real_result: dict, shuffled_result: dict) -> bool:
    return (
        shuffled_result["score"]["hit_count"] < real_result["score"]["hit_count"]
        or shuffled_result["score"]["precision"] < real_result["score"]["precision"]
    )


def condition_d_pass(real_result: dict, nonconv_result: dict) -> bool:
    return nonconv_result["score"]["hit_count"] == 0


def _prediction_matches_outcome(target: str, outcome: dict) -> bool:
    normalized_target = str(target).strip().lower()
    exact_target = str(outcome.get("target", "")).strip().lower()
    if exact_target and normalized_target == exact_target:
        return True

    contains = outcome.get("target_contains", [])
    if isinstance(contains, str):
        contains = [contains]
    contains = [str(term).strip().lower() for term in contains if str(term).strip()]
    if contains:
        return all(term in normalized_target for term in contains)

    return False


def score_text_predictions(predicted_targets: list[str], observed_outcomes: list[dict]) -> dict:
    matched_indices = set()
    hits = 0
    for target in predicted_targets:
        matched_outcome = None
        matched_index = None
        for index, outcome in enumerate(observed_outcomes):
            if not _prediction_matches_outcome(target, outcome):
                continue
            if outcome.get("observed", True):
                if index in matched_indices:
                    continue
                matched_outcome = outcome
                matched_index = index
                break
            if matched_outcome is None:
                matched_outcome = outcome
                matched_index = index

        if matched_outcome and matched_outcome.get("observed", True) and matched_index is not None:
            matched_indices.add(matched_index)
            hits += 1

    observed_positive_count = sum(1 for outcome in observed_outcomes if outcome.get("observed", True))
    return {
        "hit_count": hits,
        "precision": round(hits / len(predicted_targets), 3) if predicted_targets else 0.0,
        "recall": round(hits / observed_positive_count, 3) if observed_positive_count else 0.0,
    }


def baseline_advantage(real_result: dict, baselines: dict) -> tuple[bool, dict]:
    predicted_targets = [
        group["term"] for group in baselines["keyword_frequency"]["groups"]
    ] + [
        " ".join(cluster["labels"]) for cluster in baselines["label_cooccurrence"]["clusters"]
    ]
    baseline_score = score_text_predictions(predicted_targets, real_result["observed_outcomes"])
    pipeline_score = real_result["score"]
    return (
        pipeline_score["hit_count"] > baseline_score["hit_count"]
        or pipeline_score["precision"] > baseline_score["precision"]
    ), baseline_score


def write_report(report: str) -> Path:
    report_path = OUTPUT_DIR / "blinded_test_report.txt"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def top_choice_lines(result: dict) -> list[str]:
    choices = result["report"]["prioritization"].get("chosen", [])[:3]
    if not choices:
        return ["- No chosen priorities"]
    return [
        f"- {choice.get('target', '?')} | tier={choice.get('tier', '?')} | issues={len(choice.get('issues_resolved', []))}"
        for choice in choices
    ]


def score_lines(result: dict) -> list[str]:
    score = result["score"]
    matched = [
        scored.get("observed_outcome", {}).get("label")
        for scored in score.get("scored_predictions", [])
        if scored.get("outcome_matched")
    ]
    return [
        f"- Hits: {score['hit_count']}",
        f"- Precision: {score['precision']:.3f}",
        f"- Recall: {score['recall']:.3f}",
        "- Matched outcomes: " + (", ".join(matched) if matched else "none"),
    ]


def outcome_summary_lines(observed_outcomes: list[dict]) -> list[str]:
    """Dynamically build scored-outcome summary from the corpus."""
    lines = []
    for outcome in observed_outcomes:
        label = outcome.get("label", "?")
        detail = outcome.get("detail", "")
        short = detail[:80] if detail else label
        lines.append(f"- {label} -> {short}")
    return lines


def evaluate_domain(
    domain: dict,
    random_seed: int = RANDOM_SEED,
    budget: int = BUDGET,
) -> dict:
    """Run all 5 blinded conditions for a single domain corpus.

    Returns a dict with verdicts, scores, and report lines.
    """
    mod = importlib.import_module(domain["module"])
    label = domain["label"]
    slug = domain["slug"]

    real_scenario = mod.build_generalized_scenario()
    decoy_scenario = mod.build_decoy_seed_scenario()
    shuffled_scenario = mod.build_tag_shuffle_control(seed=random_seed)
    nonconvergent = mod.build_nonconvergent_scenario()
    observed_outcomes = real_scenario["observed_outcomes"]

    baselines = run_baselines(real_scenario["issues"])
    result_a = run_condition("Condition A", real_scenario, f"{slug}_a")
    result_b = run_condition("Condition B", decoy_scenario, f"{slug}_b")
    result_c = run_condition("Condition C", shuffled_scenario, f"{slug}_c")
    result_d = run_condition(
        "Condition D",
        nonconvergent,
        f"{slug}_d",
        observed_outcomes=observed_outcomes,
    )

    verdict_a = condition_a_pass(result_a)
    verdict_b, target_drift = condition_b_pass(result_a, result_b)
    verdict_c = condition_c_pass(result_a, result_c)
    verdict_d = condition_d_pass(result_a, result_d)
    verdict_baseline, baseline_score = baseline_advantage(result_a, baselines)

    all_pass = all([verdict_a, verdict_b, verdict_c, verdict_d, verdict_baseline])

    report_lines = [
        f"## {label} Domain",
        f"- Grounding enabled: {'YES' if result_a['grounding_enabled'] else 'NO'}",
        "",
        "### Scored observed outcomes",
        *outcome_summary_lines(observed_outcomes),
        "",
        "### Condition A (Real signals on AnalysisPipeline)",
        f"Pass: {'YES' if verdict_a else 'NO'}",
        *score_lines(result_a),
        *top_choice_lines(result_a),
        "",
        "### Condition B (Decoy metadata invariance)",
        f"Pass: {'YES' if verdict_b else 'NO'}",
        "- Target drift: " + (", ".join(target_drift) if target_drift else "none"),
        *score_lines(result_b),
        *top_choice_lines(result_b),
        "",
        "### Condition C (Tag-shuffle control)",
        f"Pass: {'YES' if verdict_c else 'NO'}",
        f"- Real hits: {result_a['score']['hit_count']}",
        f"- Shuffled hits: {result_c['score']['hit_count']}",
        f"- Real precision: {result_a['score']['precision']:.3f}",
        f"- Shuffled precision: {result_c['score']['precision']:.3f}",
        *top_choice_lines(result_c),
        "",
        "### Condition D (Non-convergent corpus vs observed outcomes)",
        f"Pass: {'YES' if verdict_d else 'NO'}",
        f"- Real hits: {result_a['score']['hit_count']}",
        f"- Non-convergent hits: {result_d['score']['hit_count']}",
        f"- Real precision: {result_a['score']['precision']:.3f}",
        f"- Non-convergent precision: {result_d['score']['precision']:.3f}",
        *top_choice_lines(result_d),
        "",
        "### Baseline comparison",
        f"Pass: {'YES' if verdict_baseline else 'NO'}",
        f"- Pipeline hits: {result_a['score']['hit_count']}",
        f"- Baseline hits: {baseline_score['hit_count']}",
        f"- Pipeline precision: {result_a['score']['precision']:.3f}",
        f"- Baseline precision: {baseline_score['precision']:.3f}",
        "- Top keyword terms: " + ", ".join(item["term"] for item in baselines["keyword_frequency"]["top_terms"][:10]),
        "- Top keyword groups: "
        + "; ".join(f"{group['term']} ({group['count']})" for group in baselines["keyword_frequency"]["groups"][:5]),
        "- Top label clusters: "
        + "; ".join(
            f"{' + '.join(cluster['labels'])} ({cluster['count']})"
            for cluster in baselines["label_cooccurrence"]["clusters"]
        ),
        "",
        "### Domain verdict",
        f"- Condition A: {'PASS' if verdict_a else 'FAIL'}",
        f"- Condition B: {'PASS' if verdict_b else 'FAIL'}",
        f"- Condition C: {'PASS' if verdict_c else 'FAIL'}",
        f"- Condition D: {'PASS' if verdict_d else 'FAIL'}",
        f"- Baseline comparison: {'PASS' if verdict_baseline else 'FAIL'}",
        f"- **{label}: {'ALL PASS' if all_pass else 'FAIL'}**",
    ]

    return {
        "label": label,
        "slug": slug,
        "all_pass": all_pass,
        "verdicts": {
            "a": verdict_a,
            "b": verdict_b,
            "c": verdict_c,
            "d": verdict_d,
            "baseline": verdict_baseline,
        },
        "scores": {
            "a": result_a["score"],
            "baseline": baseline_score,
        },
        "report_lines": report_lines,
    }


def main() -> None:
    set_reproducible_seed()

    # Discover available domains — skip modules that aren't installed yet
    available_domains = []
    for domain in DOMAIN_REGISTRY:
        try:
            importlib.import_module(domain["module"])
            available_domains.append(domain)
        except ImportError:
            print(f"[SKIP] {domain['label']}: module {domain['module']} not found")

    if not available_domains:
        print("ERROR: No domain corpora available.")
        sys.exit(1)

    all_report_lines = ["# Multi-Domain Blinded Report", ""]
    domain_results = []

    for domain in available_domains:
        print(f"\n{'='*60}")
        print(f"Evaluating: {domain['label']}")
        print(f"{'='*60}")
        result = evaluate_domain(domain)
        domain_results.append(result)
        all_report_lines.extend(result["report_lines"])
        all_report_lines.append("")

    # Aggregate summary
    passed_count = sum(1 for r in domain_results if r["all_pass"])
    total_count = len(domain_results)

    all_report_lines.extend([
        "# Cross-Domain Summary",
        f"- Domains evaluated: {total_count}",
        f"- Domains passed (5/5): {passed_count}/{total_count}",
        "",
    ])
    for r in domain_results:
        all_report_lines.append(
            f"- {r['label']}: {'PASS' if r['all_pass'] else 'FAIL'}"
        )

    gate_met = passed_count >= 3
    all_report_lines.extend([
        "",
        f"**Phase 1 gate (>= 3 domains pass): {'MET' if gate_met else 'NOT MET'}**",
    ])

    report_text = "\n".join(all_report_lines)
    report_path = write_report(report_text)
    print("\n" + report_text)
    print(f"\nSaved report to: {report_path}")


if __name__ == "__main__":
    main()

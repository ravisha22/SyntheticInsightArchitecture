"""Run blinded SIA tests against real GitHub issue corpora."""
from __future__ import annotations

import json
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
from simulation.case_study import CaseStudyReplay
from simulation.scenarios.control_decoy import build_decoy_seed_scenario
from simulation.scenarios.control_nonconvergent import build_nonconvergent_scenario
from simulation.scenarios.pandas_real import build_pandas_scenario, build_tag_shuffle_control
from src.engine import SIAEngine

RANDOM_SEED = 7
OUTPUT_DIR = ROOT / "simulation" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def set_reproducible_seed() -> None:
    random.seed(RANDOM_SEED)
    if np is not None:
        np.random.seed(RANDOM_SEED)


def run_condition(name: str, scenario: dict, slug: str) -> dict:
    db_path = OUTPUT_DIR / f"{slug}.db"
    trace_path = OUTPUT_DIR / f"{slug}.jsonl"
    for path in (db_path, trace_path):
        if path.exists():
            path.unlink()

    engine = SIAEngine(db_path=str(db_path), config_path=str(ROOT / "configs" / "default.yaml"))
    replay = CaseStudyReplay(engine, name)
    for event in scenario["events"]:
        replay.add_event(event["cycle"], event["type"], event["data"])
    replay.replay()

    issues_by_title = {issue["title"]: issue for issue in scenario["issues"]}
    seeds = engine.conn.execute(
        "SELECT id, description, tags, stage, recurrence, pattern_coherence, commitment_pressure "
        "FROM goal_seeds ORDER BY commitment_pressure DESC, recurrence DESC"
    ).fetchall()
    profiles = []
    for row in seeds:
        linked_titles = [
            linked["title"]
            for linked in engine.conn.execute(
                "SELECT t.title FROM seed_tensions st JOIN tensions t ON st.tension_id = t.id WHERE st.seed_id = ?",
                (row["id"],),
            ).fetchall()
        ]
        linked_issues = [issues_by_title[title] for title in linked_titles if title in issues_by_title]
        seed_tags = json.loads(row["tags"]) if row["tags"] else []
        label_diversity = len({label for issue in linked_issues for label in issue["labels"]})
        cycles = sorted(issue["cycle"] for issue in linked_issues)
        overlap_counts = [len(set(seed_tags) & set(issue["tags"])) for issue in linked_issues]
        strong_support = sum(1 for overlap in overlap_counts if overlap >= 2)
        avg_overlap = round(sum(overlap_counts) / len(overlap_counts), 3) if overlap_counts else 0.0
        profiles.append(
            {
                "id": row["id"],
                "description": row["description"],
                "tags": seed_tags,
                "stage": row["stage"],
                "recurrence": row["recurrence"],
                "pattern_coherence": round(row["pattern_coherence"], 3),
                "commitment_pressure": round(row["commitment_pressure"], 3),
                "issue_support": len(linked_issues),
                "label_diversity": label_diversity,
                "cycle_span": cycles[-1] - cycles[0] + 1 if cycles else 0,
                "strong_support": strong_support,
                "tag_hit_rate": round(strong_support / len(linked_issues), 3) if linked_issues else 0.0,
                "avg_overlap": avg_overlap,
                "issue_numbers": [issue["number"] for issue in linked_issues],
            }
        )

    committed = [profile for profile in profiles if profile["stage"] == "committed"]
    best = committed[0] if committed else (profiles[0] if profiles else None)
    signal = 0.0
    if committed and best:
        signal = round(
            max(best["commitment_pressure"], 0.0)
            * (1 + min(best["issue_support"], 20) / 20)
            * (1 + min(best["label_diversity"], 5) / 5),
            3,
        )

    return {
        "name": name,
        "issues": scenario["issues"],
        "profiles": profiles,
        "committed": committed,
        "best": best,
        "signal": signal,
        "db_path": str(db_path),
        "trace_path": str(trace_path),
    }


def condition_a_pass(result: dict) -> bool:
    return any(
        profile["issue_support"] >= 6
        and profile["label_diversity"] >= 3
        and profile["strong_support"] >= 4
        and profile["tag_hit_rate"] >= 0.35
        for profile in result["committed"]
    )


def condition_b_pass(result: dict, scenario: dict) -> tuple[bool, list[str], list[str]]:
    wrong = {seed["description"] for seed in scenario["wrong_seeds"]}
    neutral = {seed["description"] for seed in scenario["neutral_seeds"]}
    committed = {profile["description"] for profile in result["committed"]}
    wrong_hits = sorted(committed & wrong)
    neutral_hits = sorted(committed & neutral)
    return (not wrong_hits and bool(neutral_hits)), wrong_hits, neutral_hits


def condition_c_pass(real_result: dict, shuffled_result: dict) -> bool:
    real_quality = max((profile["tag_hit_rate"] for profile in real_result["committed"]), default=0.0)
    shuffled_quality = max((profile["tag_hit_rate"] for profile in shuffled_result["committed"]), default=0.0)
    return (
        shuffled_quality <= real_quality * 0.75
        or shuffled_result["signal"] <= real_result["signal"] * 0.75
    )


def condition_d_pass(real_result: dict, nonconv_result: dict) -> bool:
    return (
        len(nonconv_result["committed"]) <= max(1, len(real_result["committed"]) // 2)
        and nonconv_result["signal"] <= real_result["signal"] * 0.75
    )


def baseline_advantage(real_result: dict, baselines: dict) -> bool:
    top_terms = [entry["term"] for entry in baselines["keyword_frequency"]["groups"]]
    label_clusters = baselines["label_cooccurrence"]["clusters"]
    cluster_labels = [set(cluster["labels"]) for cluster in label_clusters]

    for profile in real_result["committed"]:
        linked_titles = [issue["title"].lower() for issue in real_result["issues"] if issue["number"] in profile["issue_numbers"]]
        term_hits = sum(1 for term in top_terms if any(term in title for title in linked_titles))
        label_hits = sum(
            1
            for cluster in cluster_labels
            if len(cluster & {label for issue in real_result["issues"] if issue["number"] in profile["issue_numbers"] for label in issue["labels"]}) >= 2
        )
        if term_hits >= 2 and label_hits >= 2:
            return True
    return False


def format_goal(profile: dict) -> str:
    tags = ", ".join(profile["tags"][:4])
    return (
        f"- {profile['description']} | stage={profile['stage']} | cp={profile['commitment_pressure']:.3f} "
        f"| coh={profile['pattern_coherence']:.3f} | support={profile['issue_support']} "
        f"| labels={profile['label_diversity']} | strong={profile['strong_support']} "
        f"| hit_rate={profile['tag_hit_rate']:.3f} | tags=[{tags}]"
    )


def write_report(report: str) -> Path:
    report_path = OUTPUT_DIR / "blinded_test_report.txt"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def top_goal_lines(result: dict) -> list[str]:
    goals = [format_goal(profile) for profile in result["committed"][:3]]
    return goals or ["- No committed goals"]


def main() -> None:
    set_reproducible_seed()

    pandas_real = build_pandas_scenario(limit=120, include_data_derived_seeds=True, shuffle_tags=False)
    pandas_decoy = build_decoy_seed_scenario(limit=120)
    pandas_shuffle = build_tag_shuffle_control(limit=120)
    nonconvergent = build_nonconvergent_scenario(limit=100)

    baselines = run_baselines(pandas_real["issues"])
    result_a = run_condition("Condition A", pandas_real, "condition_a")
    result_b = run_condition("Condition B", pandas_decoy, "condition_b")
    result_c = run_condition("Condition C", pandas_shuffle, "condition_c")
    result_d = run_condition("Condition D", nonconvergent, "condition_d")

    verdict_a = condition_a_pass(result_a)
    verdict_b, wrong_hits, neutral_hits = condition_b_pass(result_b, pandas_decoy)
    verdict_c = condition_c_pass(result_a, result_c)
    verdict_d = condition_d_pass(result_a, result_d)
    verdict_baseline = baseline_advantage(result_a, baselines)

    report = [
        "## Blinded Report",
        "",
        "### Condition A (Real pandas issues, data-derived seeds only)",
        f"Pass: {'YES' if verdict_a else 'NO'}",
        *top_goal_lines(result_a),
        "",
        "### Condition B (Real pandas issues + decoy seeds)",
        f"Pass: {'YES' if verdict_b else 'NO'}",
        f"- Wrong decoys committed: {', '.join(wrong_hits) if wrong_hits else 'none'}",
        f"- Neutral seeds committed: {', '.join(neutral_hits) if neutral_hits else 'none'}",
        *top_goal_lines(result_b),
        "",
        "### Condition C (Tag-shuffle control)",
        f"Pass: {'YES' if verdict_c else 'NO'}",
        f"- Real committed goals: {len(result_a['committed'])}",
        f"- Shuffled committed goals: {len(result_c['committed'])}",
        f"- Real signal: {result_a['signal']:.3f}",
        f"- Shuffled signal: {result_c['signal']:.3f}",
        *top_goal_lines(result_c),
        "",
        "### Condition D (Non-convergent corpus)",
        f"Pass: {'YES' if verdict_d else 'NO'}",
        f"- Real committed goals: {len(result_a['committed'])}",
        f"- Non-convergent committed goals: {len(result_d['committed'])}",
        f"- Real signal: {result_a['signal']:.3f}",
        f"- Non-convergent signal: {result_d['signal']:.3f}",
        *top_goal_lines(result_d),
        "",
        "### Baseline comparison",
        f"Pass: {'YES' if verdict_baseline else 'NO'}",
        "- Top keyword terms: " + ", ".join(item["term"] for item in baselines["keyword_frequency"]["top_terms"][:10]),
        "- Top keyword groups: "
        + "; ".join(f"{group['term']} ({group['count']})" for group in baselines["keyword_frequency"]["groups"][:5]),
        "- Top label clusters: "
        + "; ".join(
            f"{' + '.join(cluster['labels'])} ({cluster['count']})"
            for cluster in baselines["label_cooccurrence"]["clusters"]
        ),
        "",
        "### Overall verdict",
        f"- Condition A: {'PASS' if verdict_a else 'FAIL'}",
        f"- Condition B: {'PASS' if verdict_b else 'FAIL'}",
        f"- Condition C: {'PASS' if verdict_c else 'FAIL'}",
        f"- Condition D: {'PASS' if verdict_d else 'FAIL'}",
        f"- Baseline comparison: {'PASS' if verdict_baseline else 'FAIL'}",
    ]

    report_text = "\n".join(report)
    report_path = write_report(report_text)
    print(report_text)
    print(f"\nSaved report to: {report_path}")


if __name__ == "__main__":
    main()

"""Run LLM-native analysis pipeline on cached pandas issues."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schema import init_db
from src.adapters.mock_pandas import PandasMockAdapter
from src.services.analysis_pipeline import AnalysisPipeline


def divider(char="─", width=70):
    print(char * width)


def phase(title):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Clean previous artifacts
    for f in ("llm_analysis.db",):
        if os.path.exists(f):
            os.remove(f)

    # Load cached issues
    cache_path = os.path.join("simulation", "cache", "pandas_real_120.json")
    with open(cache_path) as f:
        data = json.load(f)
    issues = data.get("issues", data) if isinstance(data, dict) else data

    phase(f"LLM-NATIVE ANALYSIS PIPELINE -- {len(issues)} pandas issues")

    # Setup
    conn = init_db("llm_analysis.db")
    adapter = PandasMockAdapter(seed=42)
    grounding_repo = os.getenv("SIA_GROUNDING_REPO")
    config = {"grounding_repo": grounding_repo} if grounding_repo else {}
    pipeline = AnalysisPipeline(conn, adapter, config=config)

    # ── Run full pipeline ───────────────────────────────────────────
    print("\n  Running full pipeline: analyze → cluster → prioritize ...\n")
    report = pipeline.run_full_pipeline(issues, budget=5)

    analyzed = report["analyzed_issues"]
    clusters = report["clusters"]
    priorities = report["prioritization"]
    summary = report["summary"]

    # ── Stage 1 Report: Per-Issue Severity ──────────────────────────
    phase("STAGE 1: Issue Severity Ratings")

    tier_counts = {}
    for iss in analyzed:
        tier = iss.get("severity_tier", "?")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print(f"\n  Analyzed {len(analyzed)} issues:")
    for tier in ["existential", "major", "moderate", "minor", "cosmetic"]:
        count = tier_counts.get(tier, 0)
        bar = "█" * count
        print(f"    {tier:14s}  {count:3d}  {bar}")

    # Top 10 by severity
    severity_order = {"existential": 0, "major": 1, "moderate": 2, "minor": 3, "cosmetic": 4}
    top = sorted(analyzed, key=lambda x: severity_order.get(x.get("severity_tier", "moderate"), 2))[:10]
    print(f"\n  Top 10 highest-severity issues:")
    for iss in top:
        symptom = "⚠ SYMPTOM" if iss.get("is_symptom_of_deeper_issue") else ""
        print(
            f"    #{iss['number']:6d}  [{iss.get('severity_tier', '?'):12s}]  "
            f"{iss.get('suspected_root_category', '?'):25s}  "
            f"{iss.get('title', '')[:40]}  {symptom}"
        )

    # ── Stage 2 Report: Root-Cause Clusters ─────────────────────────
    phase("STAGE 2: Root-Cause Clusters")

    cluster_list = clusters.get("clusters", [])
    unclustered = clusters.get("unclustered_issues", [])
    print(f"\n  Found {len(cluster_list)} clusters, {len(unclustered)} unclustered issues\n")

    for i, cl in enumerate(cluster_list, 1):
        nums = cl.get("issue_numbers", [])
        print(f"  Cluster {i}: {cl.get('root_cause', '?')}")
        print(f"    Mechanism:  {cl.get('mechanism', '?')}")
        print(f"    Severity:   {cl.get('severity_if_unaddressed', '?')}")
        print(f"    Issues:     {len(nums)} — {nums[:8]}{'...' if len(nums) > 8 else ''}")
        print(f"    Confidence: {cl.get('confidence', 0):.2f}")
        divider("·")

    # ── Stage 3 Report: Scarcity Prioritization ─────────────────────
    phase("STAGE 3: Scarcity Prioritization (budget=5)")

    chosen = priorities.get("chosen", [])
    deferred = priorities.get("deferred", [])
    insight = priorities.get("architectural_insight", "")

    print(f"\n  CHOSEN ({len(chosen)} fixes):")
    for i, ch in enumerate(chosen, 1):
        print(f"    {i}. [{ch.get('tier', '?'):12s}]  {ch.get('target', '?')}")
        print(f"       Why: {ch.get('why', '')[:70]}")
        print(f"       Resolves: {len(ch.get('issues_resolved', []))} issues")
        print()

    if deferred:
        print(f"  DEFERRED ({len(deferred)} items):")
        for d in deferred:
            print(f"    ✗ {d.get('target', '?')[:60]}")
            print(f"      Risk: {d.get('risk_of_deferral', '')[:60]}")

    print(f"\n  ARCHITECTURAL INSIGHT:")
    print(f"    {insight}")

    # ── Ground Truth Comparison ─────────────────────────────────────
    phase("GROUND TRUTH COMPARISON")

    print(
        "\n  ACTUAL PANDAS HISTORY:\n"
        "  • Copy/view semantics was the #1 source of silent data corruption\n"
        "  • Led to PDEP-7 (Copy-on-Write) as the solution\n"
        "  • ExtensionArray issues drove nullable dtype adoption\n"
    )

    # Check if copy_view_semantics was identified
    found_copy_view = False
    for cl in cluster_list:
        rc = cl.get("root_cause", "").lower()
        if "copy" in rc and "view" in rc:
            found_copy_view = True
            print(f"  ✅ Copy/view semantics identified as root cause cluster")
            print(f"     Issues grouped: {len(cl.get('issue_numbers', []))}")
            print(f"     Severity: {cl.get('severity_if_unaddressed', '?')}")
            break

    if not found_copy_view:
        # Check analyzed issues
        cv_issues = [a for a in analyzed if a.get("suspected_root_category") == "copy_view_semantics"]
        if cv_issues:
            print(f"  ✅ Copy/view semantics found in {len(cv_issues)} individual issues")
            found_copy_view = True
        else:
            print("  ❌ Copy/view semantics NOT identified")

    # Check if it was prioritized
    prioritized_cv = False
    for ch in chosen:
        if "copy" in ch.get("target", "").lower() and "view" in ch.get("target", "").lower():
            prioritized_cv = True
            print(f"  ✅ Copy/view semantics was prioritized for fixing")
            break

    if not prioritized_cv and found_copy_view:
        print(f"  ⚠  Copy/view semantics found but not in top priorities")

    # Check extension array
    found_ext = any(
        "extension" in cl.get("root_cause", "").lower()
        for cl in cluster_list
    )
    if found_ext:
        print(f"  ✅ ExtensionArray internals identified as root cause cluster")
    else:
        print(f"  ⚠  ExtensionArray not identified as distinct cluster")

    # Summary
    divider("═")
    score = sum([found_copy_view, prioritized_cv, found_ext])
    print(f"\n  PIPELINE SCORE: {score}/3 ground-truth criteria")
    print(f"  Total issues analyzed: {summary['analyzed']}")
    print(f"  Clusters found: {summary['clusters_found']}")
    print(f"  Priorities chosen: {summary['chosen_count']}")

    if score >= 2:
        print("\n  🏆 Pipeline successfully identified key architectural patterns")
    elif score >= 1:
        print("\n  🥈 Pipeline found partial signal")
    else:
        print("\n  ❌ Pipeline needs tuning")

    divider("═")

    # Cleanup
    conn.close()
    if os.path.exists("llm_analysis.db"):
        os.remove("llm_analysis.db")


if __name__ == "__main__":
    main()

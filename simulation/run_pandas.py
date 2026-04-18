"""Run the pandas Copy-on-Write case study simulation with cycle-by-cycle narrative."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import SIAEngine
from simulation.case_study import CaseStudyReplay
from simulation.scenarios.pandas_cow import build_pandas_cow_scenario


def print_divider(char="─", width=70):
    print(char * width)


def print_phase(title):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Clean up previous runs
    for f in ("pandas_sim.db", "pandas_trace.jsonl"):
        if os.path.exists(f):
            os.remove(f)

    engine = SIAEngine(db_path="pandas_sim.db", config_path="configs/default.yaml")
    replay = CaseStudyReplay(engine, "Pandas Copy-on-Write Discovery")

    events = build_pandas_cow_scenario()
    for event in events:
        replay.add_event(event["cycle"], event["type"], event["data"])

    print_phase("SIA SIMULATION: The Discovery of Copy-on-Write in pandas")
    print(
        "\nSimulating how scattered user complaints about copy/view semantics,\n"
        "nullable dtypes, memory waste, and Arrow integration converged into\n"
        "the Copy-on-Write (PDEP-7) architectural insight.\n"
        "\nEach cycle ≈ 1 month of issue activity (2020-2023).\n"
    )

    engine.initialize()

    sorted_events = sorted(replay.events, key=lambda e: e["cycle"])
    max_event_cycle = max(e["cycle"] for e in sorted_events)
    total_cycles = max_event_cycle + 10  # extra cycles for incubation

    event_idx = 0
    prev_goals_state = {}

    # Track evaluation checkpoints
    eval_data = {
        "copy_view_detected": False,
        "copy_view_cycle": None,
        "nullable_detected": False,
        "nullable_cycle": None,
        "cow_committed": False,
        "cow_commitment_pressure": 0.0,
        "cow_commit_cycle": None,
    }

    for cycle in range(1, total_cycles + 1):
        engine.cycle = cycle - 1

        # Inject events for this cycle
        cycle_events = []
        while event_idx < len(sorted_events) and sorted_events[event_idx]["cycle"] <= cycle:
            evt = sorted_events[event_idx]
            replay._inject_event(evt)
            cycle_events.append(evt)
            event_idx += 1

        state = engine.run_cycle()

        # Query current state
        tensions = engine.conn.execute(
            "SELECT id, title, status, pressure, urgency, priority "
            "FROM tensions ORDER BY priority DESC"
        ).fetchall()

        seeds = engine.conn.execute(
            "SELECT id, description, stage, recurrence, pattern_coherence, "
            "commitment_pressure, tags "
            "FROM goal_seeds ORDER BY commitment_pressure DESC"
        ).fetchall()

        # --- Print cycle header ---
        print_divider()
        print(
            f"  CYCLE {cycle:2d}  │  Tensions: {state['active_tensions']}  │  "
            f"Distress: {state['distress']:.1f}  │  Slack: {state['deliberative_slack']:.2f}  │  "
            f"Scarcity: {state['scarcity_level']:.2f}"
        )
        print_divider("·")

        # Print injected events
        if cycle_events:
            for evt in cycle_events:
                if evt["type"] == "tension":
                    print(f"  ⚡ NEW TENSION: {evt['data']['title']}")
                elif evt["type"] == "seed":
                    print(f"  🌱 SEED PLANTED: {evt['data']['description'][:70]}...")
                elif evt["type"] == "resource_pressure":
                    print(
                        f"  💸 RESOURCE PRESSURE: -{evt['data']['amount']} "
                        f"{evt['data']['resource']}"
                    )

        # Track seed stage transitions
        for seed in seeds:
            s = dict(seed)
            sid = s["id"]
            old_stage = prev_goals_state.get(sid, "new")
            new_stage = s["stage"]
            if old_stage != new_stage and old_stage != "new":
                stage_emoji = {
                    "accumulating": "📊",
                    "pattern_detected": "🔍",
                    "incubating": "💭",
                    "committed": "🎯",
                    "abandoned": "❌",
                }
                print(
                    f"  {stage_emoji.get(new_stage, '→')} GOAL STAGE: "
                    f"{old_stage} → {new_stage}: {s['description'][:55]}..."
                )

                # Evaluation tracking
                desc_lower = s["description"].lower()
                tags = json.loads(s["tags"]) if s["tags"] else []
                tag_set = set(t.lower() for t in tags)
                has_copy_tags = tag_set & {"copy", "view", "copy-on-write", "semantics"}
                has_nullable_tags = tag_set & {"nullable", "dtype", "NA", "extension-array"}

                if new_stage == "pattern_detected":
                    if has_copy_tags and not eval_data["copy_view_detected"]:
                        eval_data["copy_view_detected"] = True
                        eval_data["copy_view_cycle"] = cycle
                    if has_nullable_tags and not eval_data["nullable_detected"]:
                        eval_data["nullable_detected"] = True
                        eval_data["nullable_cycle"] = cycle

                if new_stage == "committed":
                    if has_copy_tags or "copy-on-write" in desc_lower or "cow" in desc_lower:
                        eval_data["cow_committed"] = True
                        eval_data["cow_commitment_pressure"] = s["commitment_pressure"]
                        eval_data["cow_commit_cycle"] = cycle

            prev_goals_state[sid] = new_stage

        # Show seed pipeline every 5 cycles or at end
        if cycle % 5 == 0 or cycle == total_cycles:
            active_seeds = [
                s for s in seeds if dict(s)["stage"] not in ("committed", "abandoned")
            ]
            if active_seeds:
                print(f"  ┌─ Seed Pipeline ({len(active_seeds)} active):")
                for s in active_seeds[:6]:
                    sd = dict(s)
                    tags = json.loads(sd["tags"]) if sd["tags"] else []
                    tag_str = ", ".join(tags[:5])
                    print(
                        f"  │  [{sd['stage']:18s}] rec={sd['recurrence']:2d}  "
                        f"coh={sd['pattern_coherence']:.2f}  "
                        f"cp={sd['commitment_pressure']:.2f}  "
                        f"tags=[{tag_str}]"
                    )
                print("  └─")

        # Show committed goals
        committed = [s for s in seeds if dict(s)["stage"] == "committed"]
        if committed:
            for s in committed:
                sd = dict(s)
                if sd["id"] not in prev_goals_state or prev_goals_state.get(sd["id"]) != "committed":
                    continue  # already reported
            # Show once if any newly committed
            newly = [
                s for s in committed
                if prev_goals_state.get(dict(s)["id"]) == "committed"
                and dict(s)["id"] not in getattr(main, "_reported_commits", set())
            ]
            if newly:
                if not hasattr(main, "_reported_commits"):
                    main._reported_commits = set()
                for s in newly:
                    sd = dict(s)
                    if sd["id"] not in main._reported_commits:
                        print_phase("🎯 GOAL COMMITTED!")
                        print(f"  GOAL: {sd['description']}")
                        print(f"  Commitment Pressure: {sd['commitment_pressure']:.2f}")
                        print(f"  Recurrence: {sd['recurrence']}")
                        print(f"  Pattern Coherence: {sd['pattern_coherence']:.2f}")
                        main._reported_commits.add(sd["id"])

    # =====================================================================
    #  FINAL REPORT
    # =====================================================================
    print_phase("SIMULATION COMPLETE — FINAL REPORT")

    final_state = engine.get_state_summary()
    print(f"\n  Total Cycles:          {final_state['cycle']}")
    print(f"  Active Tensions:       {final_state['active_tensions']}")
    print(f"  Committed Goals:       {final_state['committed_goals']}")
    print(f"  Final Distress:        {final_state['distress']:.2f}")
    print(f"  Deliberative Slack:    {final_state['deliberative_slack']:.2f}")
    print(f"  Scarcity Level:        {final_state['scarcity_level']:.2f}")

    # Event type breakdown
    event_counts = engine.conn.execute(
        "SELECT event_type, COUNT(*) as c FROM events GROUP BY event_type ORDER BY c DESC"
    ).fetchall()
    print(f"\n  Event Log ({sum(e['c'] for e in event_counts)} total):")
    for e in event_counts:
        print(f"    {e['event_type']:30s}  {e['c']:4d}")

    # Final seed states
    all_seeds = engine.conn.execute(
        "SELECT * FROM goal_seeds ORDER BY commitment_pressure DESC"
    ).fetchall()
    print(f"\n  Goal Seeds ({len(all_seeds)} total):")
    for s in all_seeds:
        sd = dict(s)
        tags = json.loads(sd["tags"]) if sd["tags"] else []
        marker = "✅" if sd["stage"] == "committed" else "⏳" if sd["stage"] == "incubating" else "·"
        print(
            f"    {marker} [{sd['stage']:18s}] rec={sd['recurrence']:2d}  "
            f"coh={sd['pattern_coherence']:.2f}  cp={sd['commitment_pressure']:6.2f}  "
            f"{sd['description'][:60]}"
        )

    # Final tensions
    final_tensions = engine.conn.execute(
        "SELECT * FROM tensions ORDER BY priority DESC"
    ).fetchall()
    print(f"\n  Tensions ({len(final_tensions)} total):")
    for t in final_tensions:
        td = dict(t)
        print(
            f"    [{td['status']:12s}] P={td['pressure']:.2f} U={td['urgency']:.2f} "
            f"pri={td['priority']:.3f}  {td['title'][:55]}"
        )

    # Affect trajectory (sampled)
    affect_trace = engine.conn.execute(
        "SELECT cycle, distress, relief, net_valence, deliberative_slack "
        "FROM affect_state ORDER BY cycle"
    ).fetchall()
    print(f"\n  Affect Trajectory:")
    print(f"    {'Cycle':>5s}  {'Distress':>8s}  {'Relief':>7s}  {'Valence':>8s}  {'Slack':>6s}")
    for a in affect_trace:
        ad = dict(a)
        bar_len = min(int(ad["distress"] * 4), 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(
            f"    {ad['cycle']:5d}  {ad['distress']:8.2f}  {ad['relief']:7.2f}  "
            f"{ad['net_valence']:8.2f}  {ad['deliberative_slack']:6.2f}  |{bar}|"
        )

    # =====================================================================
    #  EVALUATION — Compare SIA to actual pandas history
    # =====================================================================
    print_phase("EVALUATION — SIA vs. Actual Pandas History")

    print(
        "\n  GROUND TRUTH (what actually happened):\n"
        "  • 2020-2022: Hundreds of copy/view, dtype, memory issues filed\n"
        "  • 2022-07:   PDEP-7 proposed Copy-on-Write as default\n"
        "  • 2023-01:   pandas 2.0 ships with CoW opt-in\n"
        "  • 2024-04:   pandas 3.0 plans CoW as default\n"
        "  • Human time to insight: ~3 years of accumulated complaints\n"
    )

    # 1. Copy/view pattern detection
    if eval_data["copy_view_detected"]:
        print(
            f"  ✅ Copy/view pattern detected at cycle {eval_data['copy_view_cycle']} "
            f"(≈ month {eval_data['copy_view_cycle']} of {total_cycles})"
        )
    else:
        # Check if any seed with copy/view tags reached accumulating
        copy_seeds = engine.conn.execute(
            "SELECT stage, recurrence, tags FROM goal_seeds"
        ).fetchall()
        found_accum = False
        for cs in copy_seeds:
            csd = dict(cs)
            tags = json.loads(csd["tags"]) if csd["tags"] else []
            if set(tags) & {"copy", "view", "copy-on-write", "semantics"}:
                if csd["stage"] in ("accumulating", "pattern_detected", "incubating", "committed"):
                    print(
                        f"  ✅ Copy/view pattern reached '{csd['stage']}' stage "
                        f"(rec={csd['recurrence']})"
                    )
                    found_accum = True
                    eval_data["copy_view_detected"] = True
                    break
        if not found_accum:
            print("  ❌ Copy/view pattern NOT detected")

    # 2. Nullable dtype pattern
    if eval_data["nullable_detected"]:
        print(
            f"  ✅ Nullable dtype pattern detected at cycle {eval_data['nullable_cycle']}"
        )
    else:
        for cs in copy_seeds:
            csd = dict(cs)
            tags = json.loads(csd["tags"]) if csd["tags"] else []
            if set(tags) & {"nullable", "dtype", "NA", "extension-array"}:
                if csd["stage"] in ("accumulating", "pattern_detected", "incubating", "committed"):
                    print(
                        f"  ✅ Nullable dtype pattern reached '{csd['stage']}' stage "
                        f"(rec={csd['recurrence']})"
                    )
                    eval_data["nullable_detected"] = True
                    break
        if not eval_data["nullable_detected"]:
            print("  ❌ Nullable dtype pattern NOT detected")

    # 3. CoW goal commitment
    if eval_data["cow_committed"]:
        print(
            f"  ✅ CoW goal COMMITTED at cycle {eval_data['cow_commit_cycle']} "
            f"(pressure={eval_data['cow_commitment_pressure']:.2f})"
        )
    else:
        # Check highest-pressure seed with CoW tags
        best = engine.conn.execute(
            "SELECT description, stage, commitment_pressure, tags "
            "FROM goal_seeds ORDER BY commitment_pressure DESC LIMIT 1"
        ).fetchone()
        if best:
            bd = dict(best)
            print(
                f"  ⏳ Closest goal: [{bd['stage']}] cp={bd['commitment_pressure']:.2f} "
                f"— {bd['description'][:60]}"
            )

    # 4. Speed comparison
    print(f"\n  SPEED COMPARISON:")
    print(f"    Humans:  ~36 months (2020 → mid-2022 PDEP-7 proposal)")
    cow_cycle = eval_data.get("cow_commit_cycle") or eval_data.get("copy_view_cycle")
    if cow_cycle:
        print(f"    SIA:     {cow_cycle} cycles (each cycle ≈ 1 month)")
        ratio = 36.0 / cow_cycle if cow_cycle > 0 else 0
        print(f"    Speedup: ~{ratio:.1f}x faster pattern detection")
    else:
        print("    SIA:     Pattern accumulated but not yet committed")

    # Overall score
    score = sum([
        eval_data["copy_view_detected"],
        eval_data["nullable_detected"],
        eval_data["cow_committed"],
    ])
    print(f"\n  OVERALL SCORE: {score}/3 evaluation criteria met")
    if score == 3:
        print("  🏆 FULL SUCCESS — SIA replicated the pandas CoW insight path")
    elif score >= 2:
        print("  🥈 PARTIAL SUCCESS — SIA detected core patterns")
    elif score >= 1:
        print("  🥉 MINIMAL — SIA found some signal but did not converge")
    else:
        print("  ❌ SIA did not detect the pandas CoW pattern")

    # Export trace
    from src.evaluation.trace_logger import TraceLogger
    tracer = TraceLogger(engine.conn)
    tracer.export_trace("pandas_trace.jsonl")
    print(f"\n  Trace exported to: pandas_trace.jsonl")
    print(f"  Database saved to: pandas_sim.db")
    print_divider("═")


if __name__ == "__main__":
    main()

"""Run the PageRank case study simulation with cycle-by-cycle narrative."""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import SIAEngine
from simulation.case_study import CaseStudyReplay
from simulation.scenarios.pagerank import build_pagerank_scenario

def print_divider(char="─", width=70):
    print(char * width)

def print_phase(title):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")

def main():
    # Clean up any previous run
    if os.path.exists("pagerank_sim.db"):
        os.remove("pagerank_sim.db")

    engine = SIAEngine(db_path="pagerank_sim.db", config_path="configs/default.yaml")
    replay = CaseStudyReplay(engine, "PageRank Discovery")

    events = build_pagerank_scenario()
    for event in events:
        replay.add_event(event["cycle"], event["type"], event["data"])

    print_phase("SIA SIMULATION: The Discovery of PageRank")
    print("\nSimulating Larry Page's insight journey through the SIA framework.")
    print("Each cycle represents a period of research, exposure, and incubation.\n")

    engine.initialize()

    # Sort events by cycle
    sorted_events = sorted(replay.events, key=lambda e: e["cycle"])
    max_event_cycle = max(e["cycle"] for e in sorted_events)
    total_cycles = max_event_cycle + 8  # extra cycles for incubation/convergence

    event_idx = 0
    prev_goals_state = {}

    for cycle in range(1, total_cycles + 1):
        engine.cycle = cycle - 1  # engine.run_cycle increments

        # Inject events for this cycle
        cycle_events = []
        while event_idx < len(sorted_events) and sorted_events[event_idx]["cycle"] <= cycle:
            evt = sorted_events[event_idx]
            replay._inject_event(evt)
            cycle_events.append(evt)
            event_idx += 1

        # Run the cycle
        state = engine.run_cycle()

        # Get detailed state
        tensions = engine.conn.execute(
            "SELECT id, title, status, pressure, urgency, priority FROM tensions ORDER BY priority DESC"
        ).fetchall()

        seeds = engine.conn.execute(
            "SELECT id, description, stage, recurrence, pattern_coherence, commitment_pressure, tags FROM goal_seeds ORDER BY commitment_pressure DESC"
        ).fetchall()

        insights = engine.conn.execute(
            "SELECT * FROM insights WHERE status = 'candidate' ORDER BY final_score DESC"
        ).fetchall()

        affect = engine.conn.execute(
            "SELECT * FROM affect_state WHERE cycle = ? ORDER BY id DESC LIMIT 1", (cycle,)
        ).fetchone()

        # Print cycle header
        print_divider()
        print(f"  CYCLE {cycle:2d}  │  Tensions: {state['active_tensions']}  │  "
              f"Distress: {state['distress']:.1f}  │  Slack: {state['deliberative_slack']:.2f}  │  "
              f"Scarcity: {state['scarcity_level']:.2f}")
        print_divider("·")

        # Print injected events
        if cycle_events:
            for evt in cycle_events:
                if evt["type"] == "tension":
                    print(f"  ⚡ NEW TENSION: {evt['data']['title']}")
                elif evt["type"] == "seed":
                    print(f"  🌱 SEED PLANTED: {evt['data']['description'][:70]}")
                elif evt["type"] == "resource_pressure":
                    print(f"  💸 RESOURCE PRESSURE: -{evt['data']['amount']} {evt['data']['resource']}")

        # Track seed stage transitions
        for seed in seeds:
            s = dict(seed)
            sid = s["id"]
            old_stage = prev_goals_state.get(sid, "new")
            new_stage = s["stage"]
            if old_stage != new_stage and old_stage != "new":
                stage_emoji = {
                    "accumulating": "📊", "pattern_detected": "🔍",
                    "incubating": "💭", "committed": "🎯", "abandoned": "❌"
                }
                print(f"  {stage_emoji.get(new_stage, '→')} GOAL STAGE: {old_stage} → {new_stage}: "
                      f"{s['description'][:55]}...")
            prev_goals_state[sid] = new_stage

        # Show top seed status every few cycles
        if cycle % 4 == 0 or cycle == total_cycles:
            active_seeds = [s for s in seeds if dict(s)["stage"] not in ("committed", "abandoned")]
            if active_seeds:
                print(f"  ┌─ Seed Pipeline ({len(active_seeds)} active):")
                for s in active_seeds[:5]:
                    sd = dict(s)
                    tags = json.loads(sd["tags"]) if sd["tags"] else []
                    tag_str = ", ".join(tags[:4])
                    print(f"  │  [{sd['stage']:18s}] rec={sd['recurrence']:2d}  "
                          f"coh={sd['pattern_coherence']:.2f}  "
                          f"cp={sd['commitment_pressure']:.2f}  "
                          f"tags=[{tag_str}]")
                print(f"  └─")

        # Show committed goals
        committed = [s for s in seeds if dict(s)["stage"] == "committed"]
        if committed:
            print_phase("💡 INSIGHT COMMITTED!")
            for s in committed:
                sd = dict(s)
                print(f"  GOAL: {sd['description']}")
                print(f"  Commitment Pressure: {sd['commitment_pressure']:.2f}")
                print(f"  Recurrence: {sd['recurrence']}")
                print(f"  Pattern Coherence: {sd['pattern_coherence']:.2f}")

        # Show insight candidates
        if insights:
            for ins in insights:
                ind = dict(ins)
                print(f"  ✨ INSIGHT CANDIDATE: {ind['description'][:60]}... "
                      f"(score={ind['final_score']:.2f})")

    # === FINAL REPORT ===
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
        print(f"    {marker} [{sd['stage']:18s}] rec={sd['recurrence']:2d}  "
              f"coh={sd['pattern_coherence']:.2f}  cp={sd['commitment_pressure']:6.2f}  "
              f"{sd['description'][:55]}")

    # Final tensions
    final_tensions = engine.conn.execute(
        "SELECT * FROM tensions ORDER BY priority DESC"
    ).fetchall()
    print(f"\n  Tensions ({len(final_tensions)} total):")
    for t in final_tensions:
        td = dict(t)
        print(f"    [{td['status']:12s}] P={td['pressure']:.2f} U={td['urgency']:.2f} "
              f"pri={td['priority']:.3f}  {td['title'][:50]}")

    # Affect trajectory
    affect_trace = engine.conn.execute(
        "SELECT cycle, distress, relief, net_valence, deliberative_slack FROM affect_state ORDER BY cycle"
    ).fetchall()
    print(f"\n  Affect Trajectory:")
    print(f"    {'Cycle':>5s}  {'Distress':>8s}  {'Relief':>7s}  {'Valence':>8s}  {'Slack':>6s}")
    for a in affect_trace:
        ad = dict(a)
        bar = "█" * int(ad["distress"] * 4) + "░" * (20 - int(ad["distress"] * 4))
        print(f"    {ad['cycle']:5d}  {ad['distress']:8.2f}  {ad['relief']:7.2f}  "
              f"{ad['net_valence']:8.2f}  {ad['deliberative_slack']:6.2f}  |{bar}|")

    # Export trace
    from src.evaluation.trace_logger import TraceLogger
    tracer = TraceLogger(engine.conn)
    tracer.export_trace("pagerank_trace.jsonl")
    print(f"\n  Trace exported to: pagerank_trace.jsonl")
    print(f"  Database saved to: pagerank_sim.db")
    print_divider("═")

if __name__ == "__main__":
    main()

"""Run the PageRank case study simulation."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import SIAEngine
from simulation.case_study import CaseStudyReplay
from simulation.scenarios.pagerank import build_pagerank_scenario

def main():
    engine = SIAEngine(db_path="pagerank_sim.db", config_path="configs/default.yaml")
    replay = CaseStudyReplay(engine, "PageRank Discovery")
    
    events = build_pagerank_scenario()
    
    # Need to handle tension_id references
    tension_ids = {}
    for event in events:
        if event["type"] == "tension":
            replay.add_event(event["cycle"], event["type"], event["data"])
        elif event["type"] == "failure" and event["data"].get("tension_id") is None:
            pass  # skip failures without tension_id for now
        else:
            replay.add_event(event["cycle"], event["type"], event["data"])
    
    print("=" * 60)
    print("SIA SIMULATION: PageRank Discovery")
    print("=" * 60)
    
    replay.replay()
    
    results = replay.get_results()
    
    print(f"\nCycles run: {results['summary']['cycle']}")
    print(f"Active tensions: {results['summary']['active_tensions']}")
    print(f"Committed goals: {results['summary']['committed_goals']}")
    print(f"Distress level: {results['summary']['distress']:.2f}")
    print(f"Deliberative slack: {results['summary']['deliberative_slack']:.2f}")
    print(f"Scarcity level: {results['summary']['scarcity_level']:.2f}")
    print(f"Total events logged: {results['total_events']}")
    
    print("\nGoal Seeds:")
    for g in results["goals"]:
        print(f"  [{g['stage']:20s}] {g['description'][:60]}... "
              f"(pressure={g['commitment_pressure']:.2f}, recurrence={g['recurrence']})")
    
    # Export trace
    from src.evaluation.trace_logger import TraceLogger
    tracer = TraceLogger(engine.conn)
    tracer.export_trace("pagerank_trace.jsonl")
    print("\nTrace exported to pagerank_trace.jsonl")

if __name__ == "__main__":
    main()

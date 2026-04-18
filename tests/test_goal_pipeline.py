"""Test Goal Pipeline — pressure-to-commitment."""
import pytest
from src.schema import init_db
from src.components.tension_register import TensionRegister
from src.components.goal_pipeline import GoalPipeline
from src.components.pressure_scorer import PressureScorer

@pytest.fixture
def setup(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    config = {
        "goal_pipeline": {
            "min_recurrence": 3,
            "min_incubation_cycles": 2,
            "commitment_threshold": 0.3,
            "social_resistance_weight": 0.1,
            "switch_cost_weight": 0.1
        },
        "pressure": {
            "weights": {"uncertainty": 1.4, "impact": 1.2, "contradiction": 1.0,
                       "deadline": 0.8, "blockers": 0.6, "recent_failures": 0.5, "known_solution": -0.9},
            "thresholds": {"incubate": 0.72, "monitor": 0.45, "archive": 0.35, "archive_cycles": 3}
        },
        "urgency": {"weights": {"impact": 1.0, "severity": 1.0, "elapsed_days": 0.5,
                                "deadline_pressure": 1.5, "dependency_centrality": 0.8,
                                "deterioration": 0.7, "reversibility": -0.5}}
    }
    tensions = TensionRegister(conn)
    goals = GoalPipeline(conn, config)
    pressure = PressureScorer(conn, config)
    return conn, tensions, goals, pressure

def test_seed_to_accumulate(setup):
    conn, tensions, goals, pressure = setup
    sid = goals.plant_seed("Recurring frustration", ["frustration"])
    for _ in range(3):
        goals.update_recurrence(sid)
    seed = conn.execute("SELECT * FROM goal_seeds WHERE id = ?", (sid,)).fetchone()
    assert seed["stage"] == "accumulating"

def test_full_pipeline_to_commitment(setup):
    conn, tensions, goals, pressure = setup
    
    # Create enough tensions to build meaningful hit rate (need >= 15% hit rate)
    # With 10 tensions and 3 linked, hit_rate = 0.3 (in sweet spot)
    tension_ids = []
    for i in range(10):
        tid = tensions.create_tension(f"Issue {i}", stake_weight=1.5 + (i % 3) * 0.3)
        tensions.add_claim(tid, "Contradiction", "contradicts", 0.9)
        tensions.record_failure(tid)
        tension_ids.append(tid)
    
    # Update pressure for all
    pressure.update_all(1)
    
    # Plant seed linked to 3 of the 10 tensions (hit_rate = 0.3, in sweet spot)
    sid = goals.plant_seed("Structural misfit", ["misfit"], tension_ids[:3])
    
    # Accumulate enough recurrence
    for _ in range(6):
        goals.update_recurrence(sid)
    
    # Detect pattern with good coherence
    goals.detect_pattern(sid, coherence=0.85)
    
    # Incubate and test threshold
    for cycle in range(8):
        goals.incubate(sid, cycle)
        committed = goals.test_threshold(sid, cycle)
        if committed:
            break
    
    seed = conn.execute("SELECT * FROM goal_seeds WHERE id = ?", (sid,)).fetchone()
    assert seed["stage"] == "committed", f"Expected committed, got {seed['stage']} (cp={seed['commitment_pressure']:.2f})"

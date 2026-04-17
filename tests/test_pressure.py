"""Test Pressure Scorer."""
import pytest
from src.schema import init_db
from src.components.tension_register import TensionRegister
from src.components.pressure_scorer import PressureScorer

@pytest.fixture
def setup(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    config = {
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
    pressure = PressureScorer(conn, config)
    return conn, tensions, pressure

def test_compute_pressure(setup):
    conn, tensions, pressure = setup
    tid = tensions.create_tension("Test", stake_weight=1.5)
    tensions.add_claim(tid, "Contradiction", "contradicts", 0.9)
    t = tensions.get_tension(tid)
    p = pressure.compute_pressure(dict(t))
    assert 0.0 < p < 1.0

def test_compute_urgency(setup):
    conn, tensions, pressure = setup
    tid = tensions.create_tension("Test", stake_weight=2.0)
    t = tensions.get_tension(tid)
    u = pressure.compute_urgency(dict(t))
    assert 0.0 < u < 1.0

def test_update_all(setup):
    conn, tensions, pressure = setup
    tid = tensions.create_tension("High pressure", stake_weight=2.0)
    tensions.add_claim(tid, "Contradiction 1", "contradicts", 0.9)
    tensions.add_claim(tid, "Contradiction 2", "contradicts", 0.8)
    tensions.record_failure(tid)
    
    pressure.update_all(cycle=1)
    
    t = tensions.get_tension(tid)
    assert t["pressure"] > 0
    assert t["urgency"] > 0
    assert t["priority"] > 0

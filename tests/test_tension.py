"""Test Tension Register."""
import pytest
from src.schema import init_db
from src.components.tension_register import TensionRegister

@pytest.fixture
def tension_reg(tmp_path):
    conn = init_db(str(tmp_path / "test.db"))
    return TensionRegister(conn)

def test_create_tension(tension_reg):
    tid = tension_reg.create_tension("Test tension", "Description", stake_weight=1.5)
    assert tid.startswith("T-")
    t = tension_reg.get_tension(tid)
    assert t["title"] == "Test tension"
    assert t["stake_weight"] == 1.5
    assert t["status"] == "open"

def test_add_contradiction(tension_reg):
    tid = tension_reg.create_tension("Test")
    tension_reg.add_claim(tid, "This contradicts", "contradicts", 0.8)
    t = tension_reg.get_tension(tid)
    assert t["contradiction_count"] == 1

def test_record_failure(tension_reg):
    tid = tension_reg.create_tension("Test")
    tension_reg.record_failure(tid)
    tension_reg.record_failure(tid)
    t = tension_reg.get_tension(tid)
    assert t["failed_attempts"] == 2

def test_resolve(tension_reg):
    tid = tension_reg.create_tension("Test")
    tension_reg.resolve(tid)
    t = tension_reg.get_tension(tid)
    assert t["status"] == "resolved"

def test_active_tensions(tension_reg):
    tension_reg.create_tension("Active 1")
    tension_reg.create_tension("Active 2")
    tid3 = tension_reg.create_tension("Resolved")
    tension_reg.resolve(tid3)
    active = tension_reg.get_active_tensions()
    assert len(active) == 2

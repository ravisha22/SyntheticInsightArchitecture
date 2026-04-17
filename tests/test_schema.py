"""Test database schema initialization."""
import os
import pytest
from src.schema import init_db, log_event, Event, EventType

def test_init_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    
    # Verify tables exist
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {t["name"] for t in tables}
    
    assert "events" in table_names
    assert "tensions" in table_names
    assert "failures" in table_names
    assert "goal_seeds" in table_names
    assert "insights" in table_names
    assert "affect_state" in table_names
    assert "resource_state" in table_names
    assert "relationships" in table_names
    assert "concepts" in table_names
    assert "traces" in table_names
    conn.close()

def test_log_event(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    
    event = Event(
        event_type=EventType.TENSION_CREATED.value,
        entity_id="T-001",
        payload={"title": "Test tension"}
    )
    log_event(conn, event)
    
    result = conn.execute("SELECT * FROM events").fetchone()
    assert result["event_type"] == "tension_created"
    assert result["entity_id"] == "T-001"
    conn.close()

"""SIA Database Schema and Event Types."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional

class EventType(Enum):
    TENSION_CREATED = "tension_created"
    TENSION_UPDATED = "tension_updated"
    TENSION_RESOLVED = "tension_resolved"
    TENSION_ARCHIVED = "tension_archived"
    FAILURE_LOGGED = "failure_logged"
    ATTEMPT_MADE = "attempt_made"
    PRESSURE_UPDATED = "pressure_updated"
    URGENCY_UPDATED = "urgency_updated"
    SEED_PLANTED = "seed_planted"
    PATTERN_DETECTED = "pattern_detected"
    GOAL_INCUBATING = "goal_incubating"
    GOAL_COMMITTED = "goal_committed"
    GOAL_ABANDONED = "goal_abandoned"
    INSIGHT_CANDIDATE = "insight_candidate"
    INSIGHT_VERIFIED = "insight_verified"
    INSIGHT_REJECTED = "insight_rejected"
    INSIGHT_INTEGRATED = "insight_integrated"
    STIMULUS_INJECTED = "stimulus_injected"
    COLLISION_DETECTED = "collision_detected"
    DREAM_RUN = "dream_run"
    INCUBATION_RUN = "incubation_run"
    AFFECT_UPDATE = "affect_update"
    BODY_STATE_UPDATE = "body_state_update"
    SOCIAL_EVENT = "social_event"
    RESOURCE_SPENT = "resource_spent"
    RESOURCE_DEPLETED = "resource_depleted"
    SCARCITY_TRIGGERED = "scarcity_triggered"
    SACRIFICE_MADE = "sacrifice_made"

class TensionStatus(Enum):
    OPEN = "open"
    INCUBATING = "incubating"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    ARCHIVED = "archived"

class GoalStage(Enum):
    SEED = "seed"
    ACCUMULATING = "accumulating"
    PATTERN_DETECTED = "pattern_detected"
    INCUBATING = "incubating"
    THRESHOLD_TESTING = "threshold_testing"
    COMMITTED = "committed"
    ABANDONED = "abandoned"


class SignalType(Enum):
    BUG_REPORT = "bug_report"
    INCIDENT = "incident"
    FEEDBACK = "feedback"
    SUPPORT_TICKET = "support_ticket"
    AUDIT = "audit"
    NEWS = "news"
    TREND = "trend"
    ISSUE = "issue"
    OTHER = "other"

@dataclass
class Event:
    event_type: str
    entity_id: str
    payload: dict
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cycle: int = 0


@dataclass
class Signal:
    signal_id: str
    signal_type: str = SignalType.OTHER.value
    source: str = ""
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

DB_SCHEMA = """
-- Core event log (append-only, canonical source of truth)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON
    timestamp TEXT NOT NULL,
    cycle INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_cycle ON events(cycle);

-- Tensions
CREATE TABLE IF NOT EXISTS tensions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    pressure REAL DEFAULT 0.0,
    urgency REAL DEFAULT 0.0,
    priority REAL DEFAULT 0.0,
    contradiction_count INTEGER DEFAULT 0,
    failed_attempts INTEGER DEFAULT 0,
    near_misses INTEGER DEFAULT 0,
    days_open REAL DEFAULT 0.0,
    stake_weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Tension claims (what supports/contradicts)
CREATE TABLE IF NOT EXISTS tension_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tension_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    role TEXT NOT NULL,  -- supports | contradicts | blocks
    confidence REAL DEFAULT 0.5,
    source TEXT,
    FOREIGN KEY (tension_id) REFERENCES tensions(id)
);

-- Failures
CREATE TABLE IF NOT EXISTS failures (
    id TEXT PRIMARY KEY,
    tension_id TEXT,
    summary TEXT NOT NULL,
    why_chain TEXT,  -- JSON array
    outcome TEXT,
    severity REAL DEFAULT 0.5,
    reusable_fragment TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tension_id) REFERENCES tensions(id)
);

-- Goal seeds
CREATE TABLE IF NOT EXISTS goal_seeds (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    tags TEXT,  -- JSON array
    stage TEXT DEFAULT 'seed',
    recurrence INTEGER DEFAULT 1,
    pattern_coherence REAL DEFAULT 0.0,
    commitment_pressure REAL DEFAULT 0.0,
    social_resistance REAL DEFAULT 0.5,
    switch_cost REAL DEFAULT 0.5,
    incubation_cycles INTEGER DEFAULT 0,
    threshold_cycles_above INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Seed-tension links
CREATE TABLE IF NOT EXISTS seed_tensions (
    seed_id TEXT NOT NULL,
    tension_id TEXT NOT NULL,
    PRIMARY KEY (seed_id, tension_id)
);

-- Insight candidates
CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    source_tension_id TEXT,
    description TEXT NOT NULL,
    compression_score REAL DEFAULT 0.0,
    constraint_score REAL DEFAULT 0.0,
    novelty_score REAL DEFAULT 0.0,
    distance_score REAL DEFAULT 0.0,
    verifier_score REAL DEFAULT 0.0,
    stability_score REAL DEFAULT 0.0,
    final_score REAL DEFAULT 0.0,
    status TEXT DEFAULT 'candidate',  -- candidate | verified | rejected | integrated
    created_at TEXT NOT NULL
);

-- Affect state
CREATE TABLE IF NOT EXISTS affect_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle INTEGER NOT NULL,
    distress REAL DEFAULT 0.0,
    relief REAL DEFAULT 0.0,
    net_valence REAL DEFAULT 0.0,
    deliberative_slack REAL DEFAULT 1.0,
    timestamp TEXT NOT NULL
);

-- Body state / resources
CREATE TABLE IF NOT EXISTS resource_state (
    resource TEXT PRIMARY KEY,
    budget REAL NOT NULL,
    spent REAL DEFAULT 0.0,
    remaining REAL NOT NULL,
    shadow_price REAL DEFAULT 0.0,
    last_updated TEXT NOT NULL
);

-- Social relationships
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    trust_score REAL DEFAULT 0.5,
    norm_debt REAL DEFAULT 0.0,
    bond_strength REAL DEFAULT 0.0,
    last_interaction TEXT
);

-- Sacrifices (what was dropped and why)
CREATE TABLE IF NOT EXISTS sacrifices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dropped_entity_id TEXT NOT NULL,
    dropped_type TEXT NOT NULL,  -- tension | goal | exploration
    reason TEXT,
    opportunity_cost REAL DEFAULT 0.0,
    cycle INTEGER,
    timestamp TEXT NOT NULL
);

-- Concept graph nodes
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    domain TEXT,
    abstraction_level TEXT,  -- concrete | intermediate | abstract
    confidence REAL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

-- Concept graph edges
CREATE TABLE IF NOT EXISTS relations (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    confidence REAL DEFAULT 0.5,
    PRIMARY KEY (src, dst, rel_type),
    FOREIGN KEY (src) REFERENCES concepts(id),
    FOREIGN KEY (dst) REFERENCES concepts(id)
);

-- Fidelity traces
CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle INTEGER NOT NULL,
    component TEXT NOT NULL,
    action TEXT NOT NULL,
    input_state TEXT,  -- JSON
    output_state TEXT,  -- JSON
    score REAL,
    timestamp TEXT NOT NULL
);

-- FTS5 for full-text search across events and tensions
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    content, entity_id, source_type
);

-- LLM issue analyses
CREATE TABLE IF NOT EXISTS issue_analyses (
    issue_number INTEGER PRIMARY KEY,
    title TEXT,
    severity_tier TEXT,
    affected_scope TEXT,
    failure_mode TEXT,
    blast_radius TEXT,
    architectural_layer TEXT,
    p_happy_if_fixed REAL,
    p_failure_cascade REAL,
    is_symptom INTEGER,
    suspected_root TEXT,
    confidence REAL,
    raw_response TEXT,
    analyzed_at TEXT,
    signal_id TEXT,
    signal_type TEXT,
    source TEXT,
    metadata TEXT,
    signal_fingerprint TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_issue_analyses_signal_id ON issue_analyses(signal_id);

-- Root cause clusters
CREATE TABLE IF NOT EXISTS root_cause_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_cause TEXT NOT NULL,
    mechanism TEXT,
    severity TEXT,
    confidence REAL,
    issue_numbers TEXT,  -- JSON array
    signal_ids TEXT,  -- JSON array
    original_severity TEXT,
    original_confidence REAL,
    grounding_query TEXT,
    grounding_evidence TEXT,  -- JSON array
    supporting_evidence TEXT,  -- JSON array
    grounding_confidence_change TEXT,
    grounded_at TEXT,
    run_id TEXT,
    created_at TEXT
);

-- Prioritization runs
CREATE TABLE IF NOT EXISTS prioritization_runs (
    id TEXT PRIMARY KEY,
    budget INTEGER,
    chosen TEXT,  -- JSON
    deferred TEXT,  -- JSON
    architectural_insight TEXT,
    run_at TEXT,
    predictions_json TEXT,  -- JSON
    outcomes_json TEXT  -- JSON
);
"""

def init_db(db_path: str = "sia_state.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(DB_SCHEMA)
    return conn

def log_event(conn: sqlite3.Connection, event: Event):
    conn.execute(
        "INSERT INTO events (event_type, entity_id, payload, timestamp, cycle) VALUES (?, ?, ?, ?, ?)",
        (event.event_type, event.entity_id, json.dumps(event.payload), event.timestamp, event.cycle)
    )
    conn.commit()

"""SQLite storage layer.

Single source of truth.  Every read/write goes through Pydantic validation.
Claude never touches the DB directly — only via orchestrator CLI calls.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from core.models import (
    AuditGap,
    Constraint,
    Decision,
    DeferredFinding,
    Milestone,
    Phase,
    PhaseStatus,
    Pipeline,
    ReflexionEntry,
    ReviewFinding,
    ReviewResult,
    Task,
    TaskEval,
    TaskStatus,
    TestResults,
    _now,
)

DB_NAME = "state.db"
SCHEMA_VERSION = 7


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class DataError(Exception):
    """Raised when stored data is corrupted or unparseable."""


# ---------------------------------------------------------------------------
# Phase dependency graph — prerequisite enforcement
# ---------------------------------------------------------------------------
# Each phase lists what must be completed OR skipped before it can start.
# Empty list = no prerequisites (can start anytime).

PHASE_DEPS: dict[str, list[str]] = {
    "plan": [],
    "specialist/domain":       ["plan"],
    "specialist/competition":  ["plan"],
    "specialist/architecture": ["plan"],
    "specialist/branding":     ["plan"],
    "specialist/backend":      ["plan", "specialist/architecture"],
    "specialist/frontend":     ["plan", "specialist/architecture"],
    "specialist/design":       ["plan", "specialist/branding"],
    "specialist/security":     ["plan", "specialist/architecture"],
    "specialist/testing":      ["plan", "specialist/architecture"],
    "specialist/devops":       ["plan", "specialist/architecture"],
    "specialist/uix":          ["plan", "specialist/frontend"],
    "specialist/legal":        ["plan"],
    "specialist/pricing":      ["plan"],
    "specialist/llm":          ["plan", "specialist/architecture"],
    "specialist/scraping":     ["plan", "specialist/architecture"],
    "specialist/data-ml":      ["plan", "specialist/architecture"],
    "synthesize":              ["plan"],  # specialists are optional
    "execute":                 ["synthesize"],
    "retro":                   ["execute"],
}

# ---------------------------------------------------------------------------
# Default pipeline phases (greenfield)
# ---------------------------------------------------------------------------

GREENFIELD_PHASES: list[dict[str, Any]] = [
    {"id": "plan", "label": "Planning", "order_index": 0},
    {"id": "specialist/domain", "label": "Domain Specialist", "order_index": 1},
    {"id": "specialist/competition", "label": "Competition Specialist", "order_index": 2},
    {"id": "specialist/architecture", "label": "Architecture Specialist", "order_index": 3},
    {"id": "specialist/branding", "label": "Branding Specialist", "order_index": 4},
    {"id": "specialist/backend", "label": "Backend Specialist", "order_index": 5},
    {"id": "specialist/frontend", "label": "Frontend Specialist", "order_index": 6},
    {"id": "specialist/design", "label": "Design Specialist", "order_index": 7},
    {"id": "specialist/security", "label": "Security Specialist", "order_index": 8},
    {"id": "specialist/testing", "label": "Testing Specialist", "order_index": 9},
    {"id": "specialist/devops", "label": "DevOps Specialist", "order_index": 10},
    {"id": "specialist/uix", "label": "UIX Specialist", "order_index": 11},
    {"id": "specialist/legal", "label": "Legal Specialist", "order_index": 12},
    {"id": "specialist/pricing", "label": "Pricing Specialist", "order_index": 13},
    {"id": "specialist/llm", "label": "LLM Specialist", "order_index": 14},
    {"id": "specialist/scraping", "label": "Scraping Specialist", "order_index": 15},
    {"id": "specialist/data-ml", "label": "Data/ML Specialist", "order_index": 16},
    {"id": "synthesize", "label": "Task Synthesis", "order_index": 17},
    {"id": "execute", "label": "Execution", "order_index": 18},
    {"id": "retro", "label": "Retrospective", "order_index": 19},
]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    project_name TEXT NOT NULL,
    project_summary TEXT NOT NULL DEFAULT '',
    current_phase TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phases (
    id          TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    order_index INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    prefix      TEXT NOT NULL,
    number      INTEGER NOT NULL,
    title       TEXT NOT NULL,
    rationale   TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions_history (
    rowid_h     INTEGER PRIMARY KEY AUTOINCREMENT,
    id          TEXT NOT NULL,
    prefix      TEXT NOT NULL,
    number      INTEGER NOT NULL,
    title       TEXT NOT NULL,
    rationale   TEXT NOT NULL,
    created_by  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    replaced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS constraints (
    id          TEXT PRIMARY KEY,
    category    TEXT NOT NULL,
    description TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS milestones (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    goal        TEXT NOT NULL DEFAULT '',
    order_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    milestone       TEXT NOT NULL REFERENCES milestones(id),
    status          TEXT NOT NULL DEFAULT 'pending',
    goal            TEXT NOT NULL DEFAULT '',
    depends_on      TEXT NOT NULL DEFAULT '[]',
    decision_refs   TEXT NOT NULL DEFAULT '[]',
    files_create    TEXT NOT NULL DEFAULT '[]',
    files_modify    TEXT NOT NULL DEFAULT '[]',
    acceptance_criteria TEXT NOT NULL DEFAULT '[]',
    verification_cmd TEXT,
    artifact_refs   TEXT NOT NULL DEFAULT '[]',
    parent_task     TEXT
);

CREATE TABLE IF NOT EXISTS events (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT '',
    action      TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id   TEXT NOT NULL DEFAULT '',
    detail      TEXT NOT NULL DEFAULT '',
    phase       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reflexion_entries (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    task_id         TEXT NOT NULL REFERENCES tasks(id),
    tags            TEXT NOT NULL DEFAULT '[]',
    category        TEXT NOT NULL,
    severity        TEXT NOT NULL,
    what_happened   TEXT NOT NULL,
    root_cause      TEXT NOT NULL,
    lesson          TEXT NOT NULL,
    applies_to      TEXT NOT NULL DEFAULT '[]',
    preventive_action TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS task_evals (
    task_id         TEXT PRIMARY KEY REFERENCES tasks(id),
    milestone       TEXT NOT NULL REFERENCES milestones(id),
    status          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    review_cycles   INTEGER NOT NULL DEFAULT 0,
    security_review INTEGER NOT NULL DEFAULT 0,
    test_total      INTEGER NOT NULL DEFAULT 0,
    test_passed     INTEGER NOT NULL DEFAULT 0,
    test_failed     INTEGER NOT NULL DEFAULT 0,
    test_skipped    INTEGER NOT NULL DEFAULT 0,
    files_planned   TEXT NOT NULL DEFAULT '[]',
    files_touched   TEXT NOT NULL DEFAULT '[]',
    scope_violations INTEGER NOT NULL DEFAULT 0,
    reflexion_entries_created INTEGER NOT NULL DEFAULT 0,
    notes           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS review_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL REFERENCES tasks(id),
    reviewer        TEXT NOT NULL,
    verdict         TEXT NOT NULL,
    cycle           INTEGER NOT NULL DEFAULT 1,
    criteria_assessed INTEGER NOT NULL DEFAULT 0,
    criteria_passed   INTEGER NOT NULL DEFAULT 0,
    criteria_failed   INTEGER NOT NULL DEFAULT 0,
    findings        TEXT NOT NULL DEFAULT '[]',
    scope_issues    TEXT NOT NULL DEFAULT '[]',
    decision_compliance TEXT NOT NULL DEFAULT '{}',
    raw_output      TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deferred_findings (
    id              TEXT PRIMARY KEY,
    discovered_in   TEXT NOT NULL REFERENCES tasks(id),
    category        TEXT NOT NULL,
    affected_area   TEXT NOT NULL,
    files_likely    TEXT NOT NULL DEFAULT '[]',
    spec_reference  TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS audit_gaps (
    id              TEXT PRIMARY KEY,
    category        TEXT NOT NULL,
    severity        TEXT NOT NULL,
    layer           TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    trigger_ref     TEXT NOT NULL DEFAULT '',
    evidence        TEXT NOT NULL DEFAULT '[]',
    recommendation  TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'open',
    resolved_by     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS artifacts (
    type        TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_milestone ON tasks(milestone);
CREATE INDEX IF NOT EXISTS idx_review_results_task_id ON review_results(task_id);
CREATE INDEX IF NOT EXISTS idx_events_phase ON events(phase);
CREATE INDEX IF NOT EXISTS idx_reflexion_task_id ON reflexion_entries(task_id);
CREATE INDEX IF NOT EXISTS idx_deferred_findings_status ON deferred_findings(status);
CREATE INDEX IF NOT EXISTS idx_audit_gaps_status ON audit_gaps(status);
"""


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db(db_path: str | Path = DB_NAME) -> sqlite3.Connection:
    """Open a connection with WAL mode and foreign keys.

    Checks schema version on connect — raises if DB is from a newer version.
    """
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _check_schema_version(conn)
    return conn


def _check_schema_version(conn: sqlite3.Connection) -> None:
    """Verify the DB schema version is compatible."""
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.OperationalError:
        # meta table doesn't exist — pre-versioning DB or brand new
        return
    if not row:
        return
    db_version = int(row["value"])
    if db_version > SCHEMA_VERSION:
        raise RuntimeError(
            f"DB schema version {db_version} is newer than supported {SCHEMA_VERSION}. "
            f"Upgrade the orchestrator."
        )
    if db_version < SCHEMA_VERSION:
        _migrate(conn, db_version)


def _migrate(conn: sqlite3.Connection, from_version: int) -> None:
    """Run incremental migrations from from_version to SCHEMA_VERSION."""
    if from_version < 2:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS reflexion_entries (
                    id              TEXT PRIMARY KEY,
                    timestamp       TEXT NOT NULL,
                    task_id         TEXT NOT NULL REFERENCES tasks(id),
                    tags            TEXT NOT NULL DEFAULT '[]',
                    category        TEXT NOT NULL,
                    severity        TEXT NOT NULL,
                    what_happened   TEXT NOT NULL,
                    root_cause      TEXT NOT NULL,
                    lesson          TEXT NOT NULL,
                    applies_to      TEXT NOT NULL DEFAULT '[]',
                    preventive_action TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS task_evals (
                    task_id         TEXT PRIMARY KEY REFERENCES tasks(id),
                    milestone       TEXT NOT NULL REFERENCES milestones(id),
                    status          TEXT NOT NULL,
                    started_at      TEXT NOT NULL,
                    completed_at    TEXT,
                    review_cycles   INTEGER NOT NULL DEFAULT 0,
                    security_review INTEGER NOT NULL DEFAULT 0,
                    test_total      INTEGER NOT NULL DEFAULT 0,
                    test_passed     INTEGER NOT NULL DEFAULT 0,
                    test_failed     INTEGER NOT NULL DEFAULT 0,
                    test_skipped    INTEGER NOT NULL DEFAULT 0,
                    files_planned   TEXT NOT NULL DEFAULT '[]',
                    files_touched   TEXT NOT NULL DEFAULT '[]',
                    scope_violations INTEGER NOT NULL DEFAULT 0,
                    reflexion_entries_created INTEGER NOT NULL DEFAULT 0,
                    notes           TEXT NOT NULL DEFAULT ''
                );
            """)
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(2),),
            )

    if from_version < 3:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS review_results (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id         TEXT NOT NULL REFERENCES tasks(id),
                    reviewer        TEXT NOT NULL,
                    verdict         TEXT NOT NULL,
                    cycle           INTEGER NOT NULL DEFAULT 1,
                    criteria_assessed INTEGER NOT NULL DEFAULT 0,
                    criteria_passed   INTEGER NOT NULL DEFAULT 0,
                    criteria_failed   INTEGER NOT NULL DEFAULT 0,
                    findings        TEXT NOT NULL DEFAULT '[]',
                    scope_issues    TEXT NOT NULL DEFAULT '[]',
                    decision_compliance TEXT NOT NULL DEFAULT '{}',
                    raw_output      TEXT NOT NULL DEFAULT '',
                    created_at      TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deferred_findings (
                    id              TEXT PRIMARY KEY,
                    discovered_in   TEXT NOT NULL REFERENCES tasks(id),
                    category        TEXT NOT NULL,
                    affected_area   TEXT NOT NULL,
                    files_likely    TEXT NOT NULL DEFAULT '[]',
                    spec_reference  TEXT NOT NULL DEFAULT '',
                    description     TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'open'
                );
            """)
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(3),),
            )

    if from_version < 4:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    type        TEXT PRIMARY KEY,
                    content     TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );
            """)
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(4),),
            )

    if from_version < 5:
        with conn:
            # Add artifact_refs and parent_task columns to tasks table
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN artifact_refs TEXT NOT NULL DEFAULT '[]'"
            )
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN parent_task TEXT"
            )
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(5),),
            )

    if from_version < 6:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS audit_gaps (
                    id              TEXT PRIMARY KEY,
                    category        TEXT NOT NULL,
                    severity        TEXT NOT NULL,
                    layer           TEXT NOT NULL,
                    title           TEXT NOT NULL,
                    description     TEXT NOT NULL,
                    trigger_ref     TEXT NOT NULL DEFAULT '',
                    evidence        TEXT NOT NULL DEFAULT '[]',
                    recommendation  TEXT NOT NULL DEFAULT '',
                    status          TEXT NOT NULL DEFAULT 'open',
                    resolved_by     TEXT NOT NULL DEFAULT ''
                );
            """)
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(6),),
            )

    if from_version < 7:
        with conn:
            # Add project_summary column if it doesn't exist
            try:
                conn.execute(
                    "ALTER TABLE pipeline ADD COLUMN project_summary TEXT NOT NULL DEFAULT ''"
                )
            except sqlite3.OperationalError:
                pass  # Column already exists (DB created with current schema)

            # Add indexes for frequently queried columns
            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_milestone ON tasks(milestone);
                CREATE INDEX IF NOT EXISTS idx_review_results_task_id ON review_results(task_id);
                CREATE INDEX IF NOT EXISTS idx_events_phase ON events(phase);
                CREATE INDEX IF NOT EXISTS idx_reflexion_task_id ON reflexion_entries(task_id);
                CREATE INDEX IF NOT EXISTS idx_deferred_findings_status ON deferred_findings(status);
                CREATE INDEX IF NOT EXISTS idx_audit_gaps_status ON audit_gaps(status);
            """)
            conn.execute(
                "UPDATE meta SET value = ? WHERE key = 'schema_version'",
                (str(SCHEMA_VERSION),),
            )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def init_db(project_name: str, db_path: str | Path = DB_NAME) -> Path:
    """Create the DB file with schema and default pipeline phases."""
    path = Path(db_path)
    conn = sqlite3.connect(str(path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    with conn:
        conn.executescript(SCHEMA_SQL)

        # Schema version
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )

        # Pipeline singleton row
        pipe = Pipeline(project_name=project_name, current_phase="plan")
        conn.execute(
            "INSERT OR REPLACE INTO pipeline "
            "(id, project_name, project_summary, current_phase, created_at, updated_at) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (pipe.project_name, pipe.project_summary, pipe.current_phase,
             pipe.created_at, pipe.updated_at),
        )

        # Default greenfield phases
        for p in GREENFIELD_PHASES:
            phase = Phase(**p)
            conn.execute(
                "INSERT OR IGNORE INTO phases (id, label, status, order_index, started_at, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (phase.id, phase.label, phase.status.value, phase.order_index, None, None),
            )

        # First event
        _log_event(conn, "init", "pipeline", project_name,
                   f"Project initialised with {len(GREENFIELD_PHASES)} phases")

    conn.close()
    return path


# ---------------------------------------------------------------------------
# Pipeline operations
# ---------------------------------------------------------------------------

def get_pipeline(conn: sqlite3.Connection) -> Pipeline:
    row = conn.execute("SELECT * FROM pipeline WHERE id = 1").fetchone()
    if not row:
        raise RuntimeError("Pipeline not initialised — run 'orchestrator.py init' first")
    return Pipeline(
        project_name=row["project_name"],
        project_summary=row["project_summary"] or "",
        current_phase=row["current_phase"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def set_current_phase(conn: sqlite3.Connection, phase_id: str | None) -> None:
    with conn:
        conn.execute(
            "UPDATE pipeline SET current_phase = ?, updated_at = ? WHERE id = 1",
            (phase_id, _now()),
        )


def set_project_summary(conn: sqlite3.Connection, summary: str) -> None:
    """Store the executive summary produced at end of planning.

    Validates through the Pipeline model's field constraints before writing.
    """
    from core.models import Pipeline

    # Validate by running the value through the Pipeline model
    pipeline = get_pipeline(conn)
    Pipeline.model_validate({**pipeline.model_dump(), "project_summary": summary})

    with conn:
        conn.execute(
            "UPDATE pipeline SET project_summary = ?, updated_at = ? WHERE id = 1",
            (summary, _now()),
        )
        _log_event(conn, "store_summary", "pipeline", detail=f"len={len(summary)}")


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------

def _log_event(
    conn: sqlite3.Connection,
    action: str,
    target_type: str,
    target_id: str = "",
    detail: str = "",
    actor: str = "orchestrator",
) -> None:
    """Append an event to the log.  Called inside an existing transaction."""
    pipeline_row = conn.execute(
        "SELECT current_phase FROM pipeline WHERE id = 1"
    ).fetchone()
    phase = pipeline_row["current_phase"] if pipeline_row else ""
    conn.execute(
        "INSERT INTO events (timestamp, actor, action, target_type, target_id, detail, phase) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (_now(), actor, action, target_type, target_id, detail, phase or ""),
    )


def get_events(
    conn: sqlite3.Connection,
    limit: int = 50,
    phase: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent events, optionally filtered by phase."""
    if phase:
        rows = conn.execute(
            "SELECT * FROM events WHERE phase = ? ORDER BY seq DESC LIMIT ?",
            (phase, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY seq DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Phase operations
# ---------------------------------------------------------------------------

def get_phases(conn: sqlite3.Connection) -> list[Phase]:
    rows = conn.execute(
        "SELECT * FROM phases ORDER BY order_index"
    ).fetchall()
    return [Phase(**dict(r)) for r in rows]


def get_phase(conn: sqlite3.Connection, phase_id: str) -> Phase | None:
    row = conn.execute("SELECT * FROM phases WHERE id = ?", (phase_id,)).fetchone()
    return Phase(**dict(row)) if row else None


class PhaseGuardError(Exception):
    """Raised when phase prerequisites are not met."""

    def __init__(self, phase_id: str, unmet: list[str]):
        self.phase_id = phase_id
        self.unmet = unmet
        super().__init__(
            f"Cannot start '{phase_id}': prerequisites not met: {', '.join(unmet)}"
        )


def check_phase_prereqs(conn: sqlite3.Connection, phase_id: str) -> list[str]:
    """Return list of unmet prerequisites for a phase.  Empty = OK to start."""
    deps = PHASE_DEPS.get(phase_id, [])
    if not deps:
        return []

    unmet: list[str] = []
    for dep_id in deps:
        dep_phase = get_phase(conn, dep_id)
        if not dep_phase:
            unmet.append(f"{dep_id} (not found)")
        elif dep_phase.status not in (PhaseStatus.COMPLETED, PhaseStatus.SKIPPED):
            unmet.append(f"{dep_id} (status: {dep_phase.status.value})")
    return unmet


def start_phase(conn: sqlite3.Connection, phase_id: str) -> Phase:
    """Start a phase — enforces prerequisite guard."""
    # Guard: check prerequisites
    unmet = check_phase_prereqs(conn, phase_id)
    if unmet:
        raise PhaseGuardError(phase_id, unmet)

    now = _now()
    with conn:
        conn.execute(
            "UPDATE phases SET status = ?, started_at = ? WHERE id = ?",
            (PhaseStatus.ACTIVE.value, now, phase_id),
        )
        conn.execute(
            "UPDATE pipeline SET current_phase = ?, updated_at = ? WHERE id = 1",
            (phase_id, _now()),
        )
        _log_event(conn, "start_phase", "phase", phase_id)
    return get_phase(conn, phase_id)  # type: ignore[return-value]


def complete_phase(conn: sqlite3.Connection, phase_id: str) -> Phase:
    phase = get_phase(conn, phase_id)
    if not phase:
        raise DataError(f"Phase '{phase_id}' not found")
    now = _now()
    with conn:
        conn.execute(
            "UPDATE phases SET status = ?, completed_at = ? WHERE id = ?",
            (PhaseStatus.COMPLETED.value, now, phase_id),
        )
        _log_event(conn, "complete_phase", "phase", phase_id)
    return get_phase(conn, phase_id)  # type: ignore[return-value]


def skip_phase(conn: sqlite3.Connection, phase_id: str) -> None:
    phase = get_phase(conn, phase_id)
    if not phase:
        raise DataError(f"Phase '{phase_id}' not found")
    with conn:
        conn.execute(
            "UPDATE phases SET status = ? WHERE id = ?",
            (PhaseStatus.SKIPPED.value, phase_id),
        )
        _log_event(conn, "skip_phase", "phase", phase_id)


def add_phase(
    conn: sqlite3.Connection, phase_id: str, label: str, after: str | None = None,
) -> Phase:
    """Insert a new phase.  If *after* is given, place it right after that phase."""
    order = 0
    if after:
        ref = get_phase(conn, after)
        if ref:
            order = ref.order_index + 1
    else:
        row = conn.execute("SELECT MAX(order_index) AS m FROM phases").fetchone()
        order = (row["m"] or 0) + 1

    phase = Phase(id=phase_id, label=label, order_index=order)
    with conn:
        if after and get_phase(conn, after):
            conn.execute(
                "UPDATE phases SET order_index = order_index + 1 "
                "WHERE order_index >= ?",
                (order,),
            )
        conn.execute(
            "INSERT INTO phases (id, label, status, order_index) VALUES (?, ?, ?, ?)",
            (phase.id, phase.label, phase.status.value, phase.order_index),
        )
    return phase


# ---------------------------------------------------------------------------
# Decision operations
# ---------------------------------------------------------------------------

def store_decisions(conn: sqlite3.Connection, decisions: list[Decision]) -> int:
    """Validate and store decisions.  Overwrites are saved to history."""
    with conn:
        for d in decisions:
            # Archive existing version before overwrite
            existing = conn.execute(
                "SELECT * FROM decisions WHERE id = ?", (d.id,)
            ).fetchone()
            if existing:
                conn.execute(
                    "INSERT INTO decisions_history "
                    "(id, prefix, number, title, rationale, created_by, created_at, replaced_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (existing["id"], existing["prefix"], existing["number"],
                     existing["title"], existing["rationale"],
                     existing["created_by"], existing["created_at"], _now()),
                )

            conn.execute(
                "INSERT OR REPLACE INTO decisions "
                "(id, prefix, number, title, rationale, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (d.id, d.prefix.value, d.number, d.title, d.rationale,
                 d.created_by, d.created_at),
            )
        _log_event(conn, "store_decisions", "decision", "",
                   f"Stored {len(decisions)}: {', '.join(d.id for d in decisions)}")
    return len(decisions)


def get_decisions(
    conn: sqlite3.Connection,
    prefixes: list[str] | None = None,
) -> list[Decision]:
    """Fetch decisions, optionally filtered by prefix list."""
    if prefixes is not None:
        if not prefixes:
            return []  # Empty prefix list = no results (avoids invalid SQL)
        placeholders = ",".join("?" for _ in prefixes)
        rows = conn.execute(
            f"SELECT * FROM decisions WHERE prefix IN ({placeholders}) ORDER BY prefix, number",
            prefixes,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY prefix, number"
        ).fetchall()
    return [Decision(**dict(r)) for r in rows]


def get_decision(conn: sqlite3.Connection, decision_id: str) -> Decision | None:
    row = conn.execute(
        "SELECT * FROM decisions WHERE id = ?", (decision_id,)
    ).fetchone()
    return Decision(**dict(row)) if row else None


def count_decisions(conn: sqlite3.Connection) -> dict[str, int]:
    """Return {prefix: count} for all stored decisions."""
    rows = conn.execute(
        "SELECT prefix, COUNT(*) as cnt FROM decisions GROUP BY prefix"
    ).fetchall()
    return {r["prefix"]: r["cnt"] for r in rows}


# ---------------------------------------------------------------------------
# Artifact operations
# ---------------------------------------------------------------------------

def store_artifact(conn: sqlite3.Connection, artifact_type: str, content: str) -> None:
    """Store or replace a named artifact (brand-guide, style-guide, etc.)."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO artifacts (type, content, updated_at) "
            "VALUES (?, ?, ?)",
            (artifact_type, content, _now()),
        )
        _log_event(conn, "store_artifact", "artifact", artifact_type,
                   f"Stored artifact: {artifact_type} ({len(content)} chars)")


def get_artifact(conn: sqlite3.Connection, artifact_type: str) -> str | None:
    """Retrieve a named artifact by type. Returns None if not found."""
    row = conn.execute(
        "SELECT content FROM artifacts WHERE type = ?", (artifact_type,)
    ).fetchone()
    return row["content"] if row else None


def list_artifacts(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Return all stored artifact types with their update timestamps."""
    rows = conn.execute(
        "SELECT type, updated_at FROM artifacts ORDER BY type"
    ).fetchall()
    return [{"type": r["type"], "updated_at": r["updated_at"]} for r in rows]


# ---------------------------------------------------------------------------
# Constraint operations
# ---------------------------------------------------------------------------

def store_constraints(conn: sqlite3.Connection, constraints: list[Constraint]) -> int:
    with conn:
        for c in constraints:
            conn.execute(
                "INSERT OR REPLACE INTO constraints (id, category, description, source) "
                "VALUES (?, ?, ?, ?)",
                (c.id, c.category, c.description, c.source),
            )
        _log_event(conn, "store_constraints", "constraint", "",
                   f"Stored {len(constraints)}: {', '.join(c.id for c in constraints)}")
    return len(constraints)


def get_constraints(conn: sqlite3.Connection) -> list[Constraint]:
    rows = conn.execute("SELECT * FROM constraints ORDER BY id").fetchall()
    return [Constraint(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Milestone operations
# ---------------------------------------------------------------------------

def store_milestones(conn: sqlite3.Connection, milestones: list[Milestone]) -> int:
    with conn:
        for m in milestones:
            conn.execute(
                "INSERT OR REPLACE INTO milestones (id, name, goal, order_index) "
                "VALUES (?, ?, ?, ?)",
                (m.id, m.name, m.goal, m.order_index),
            )
        _log_event(conn, "store_milestones", "milestone", "",
                   f"Stored {len(milestones)}: {', '.join(m.id for m in milestones)}")
    return len(milestones)


def get_milestones(conn: sqlite3.Connection) -> list[Milestone]:
    rows = conn.execute(
        "SELECT * FROM milestones ORDER BY order_index"
    ).fetchall()
    return [Milestone(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Task operations
# ---------------------------------------------------------------------------

def store_tasks(conn: sqlite3.Connection, tasks: list[Task]) -> int:
    with conn:
        for t in tasks:
            conn.execute(
                "INSERT OR REPLACE INTO tasks "
                "(id, title, milestone, status, goal, depends_on, decision_refs, "
                "files_create, files_modify, acceptance_criteria, verification_cmd, "
                "artifact_refs, parent_task) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    t.id, t.title, t.milestone, t.status.value, t.goal,
                    json.dumps(t.depends_on),
                    json.dumps(t.decision_refs),
                    json.dumps(t.files_create),
                    json.dumps(t.files_modify),
                    json.dumps(t.acceptance_criteria),
                    t.verification_cmd,
                    json.dumps(t.artifact_refs),
                    t.parent_task,
                ),
            )
        _log_event(conn, "store_tasks", "task", "",
                   f"Stored {len(tasks)}: {', '.join(t.id for t in tasks)}")
    return len(tasks)


def get_tasks(
    conn: sqlite3.Connection,
    status: TaskStatus | None = None,
    milestone: str | None = None,
) -> list[Task]:
    """Fetch tasks, optionally filtered."""
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status.value)
    if milestone:
        clauses.append("milestone = ?")
        params.append(milestone)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM tasks{where} ORDER BY id", params
    ).fetchall()
    return [_row_to_task(r) for r in rows]


def get_task(conn: sqlite3.Connection, task_id: str) -> Task | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def update_task_status(conn: sqlite3.Connection, task_id: str, status: TaskStatus) -> None:
    with conn:
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status.value, task_id),
        )
        _log_event(conn, f"task_{status.value}", "task", task_id)


def next_pending_task(conn: sqlite3.Connection) -> Task | None:
    """Return the first pending task whose dependencies are all completed."""
    # Fetch completed IDs directly (avoids constructing full Task objects)
    completed_ids = {
        r["id"] for r in
        conn.execute(
            "SELECT id FROM tasks WHERE status = ?",
            (TaskStatus.COMPLETED.value,),
        ).fetchall()
    }
    pending = get_tasks(conn, status=TaskStatus.PENDING)
    for task in pending:
        if all(dep in completed_ids for dep in task.depends_on):
            return task
    return None


def delete_task(conn: sqlite3.Connection, task_id: str) -> None:
    """Delete a task and its FK-dependent child rows.

    Cascades to: review_results, task_evals, reflexion_entries, deferred_findings.
    Note: deferred_findings uses 'discovered_in' as its FK column.
    """
    with conn:
        # Delete FK-dependent children first (no ON DELETE CASCADE in schema)
        for child_table in ("review_results", "task_evals", "reflexion_entries"):
            conn.execute(f"DELETE FROM {child_table} WHERE task_id = ?", (task_id,))  # noqa: S608
        conn.execute("DELETE FROM deferred_findings WHERE discovered_in = ?", (task_id,))
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount > 0:
            _log_event(conn, "task_deleted", "task", task_id)


def rewire_task_deps(
    conn: sqlite3.Connection,
    old_dep: str,
    new_dep: str,
) -> int:
    """Replace *old_dep* with *new_dep* in every task's depends_on list.

    Returns the number of tasks whose deps were rewritten.
    """
    rewritten = 0
    with conn:
        rows = conn.execute("SELECT id, depends_on FROM tasks").fetchall()
        for row in rows:
            deps: list[str] = json.loads(row["depends_on"])
            if old_dep in deps:
                new_deps = list(dict.fromkeys(
                    new_dep if d == old_dep else d for d in deps
                ))
                conn.execute(
                    "UPDATE tasks SET depends_on = ? WHERE id = ?",
                    (json.dumps(new_deps), row["id"]),
                )
                rewritten += 1
        if rewritten:
            _log_event(
                conn, "rewire_deps", "task",
                detail=f"old={old_dep} new={new_dep} count={rewritten}",
            )
    return rewritten


# ---------------------------------------------------------------------------
# Checkpoints — snapshot DB before each phase for rollback
# ---------------------------------------------------------------------------

CHECKPOINT_DIR = "checkpoints"


def create_checkpoint(db_path: str | Path, label: str) -> Path:
    """Copy the DB file as a checkpoint before a phase starts.

    Stored as checkpoints/<label>.db alongside the main state.db.
    """
    db_path = Path(db_path)
    ckpt_dir = db_path.parent / CHECKPOINT_DIR
    ckpt_dir.mkdir(exist_ok=True)

    # Sanitise label for filename
    safe_label = label.replace("/", "_").replace(" ", "_")
    ckpt_path = ckpt_dir / f"{safe_label}.db"

    # Close WAL before copy to get a consistent snapshot
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.OperationalError:
        logger.warning(
            "WAL checkpoint failed before snapshot — checkpoint may be incomplete"
        )
    finally:
        conn.close()

    shutil.copy2(str(db_path), str(ckpt_path))
    return ckpt_path


def rollback_to_checkpoint(db_path: str | Path, label: str) -> bool:
    """Restore DB from a checkpoint.  Returns True if restored."""
    db_path = Path(db_path)
    safe_label = label.replace("/", "_").replace(" ", "_")
    ckpt_path = db_path.parent / CHECKPOINT_DIR / f"{safe_label}.db"

    if not ckpt_path.exists():
        return False

    shutil.copy2(str(ckpt_path), str(db_path))
    # Remove stale WAL/SHM files to prevent replaying old transactions
    for suffix in ("-wal", "-shm"):
        stale = Path(str(db_path) + suffix)
        if stale.exists():
            stale.unlink()
    return True


def list_checkpoints(db_path: str | Path) -> list[str]:
    """Return available checkpoint labels."""
    db_path = Path(db_path)
    ckpt_dir = db_path.parent / CHECKPOINT_DIR
    if not ckpt_dir.exists():
        return []
    return sorted(
        p.stem.replace("_", "/", 1) for p in ckpt_dir.glob("*.db")
    )


# ---------------------------------------------------------------------------
# Reflexion operations
# ---------------------------------------------------------------------------

def next_reflexion_id(conn: sqlite3.Connection) -> str:
    """Generate the next reflexion ID: R001, R002, ..."""
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 2) AS INTEGER)) AS max_num "
        "FROM reflexion_entries"
    ).fetchone()
    if not row or row["max_num"] is None:
        return "R001"
    num = row["max_num"] + 1
    return f"R{num:03d}"


def store_reflexion_entry(conn: sqlite3.Connection, entry: ReflexionEntry) -> str:
    """Validate and store a reflexion entry.  Returns the entry ID."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO reflexion_entries "
            "(id, timestamp, task_id, tags, category, severity, "
            "what_happened, root_cause, lesson, applies_to, preventive_action) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id, entry.timestamp, entry.task_id,
                json.dumps(entry.tags), entry.category.value, entry.severity.value,
                entry.what_happened, entry.root_cause, entry.lesson,
                json.dumps(entry.applies_to), entry.preventive_action,
            ),
        )
        _log_event(conn, "store_reflexion", "reflexion", entry.id,
                   f"cat={entry.category.value} sev={entry.severity.value}")
    return entry.id


def get_reflexion_entries(
    conn: sqlite3.Connection,
    task_id: str | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[ReflexionEntry]:
    """Fetch reflexion entries, optionally filtered by task/category."""
    clauses: list[str] = []
    params: list[Any] = []
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    if category:
        clauses.append("category = ?")
        params.append(category)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"SELECT * FROM reflexion_entries{where} ORDER BY id DESC LIMIT ?",
        params,
    ).fetchall()
    return [_row_to_reflexion_entry(r) for r in rows]


def search_reflexion(
    conn: sqlite3.Connection,
    tags: list[str] | None = None,
    category: str | None = None,
) -> list[ReflexionEntry]:
    """Search reflexion entries by tag overlap using json_each()."""
    if not tags and not category:
        return get_reflexion_entries(conn)

    clauses: list[str] = []
    params: list[Any] = []

    if tags:
        # Match entries that have ANY of the given tags
        tag_placeholders = ",".join("?" for _ in tags)
        clauses.append(
            f"id IN (SELECT re.id FROM reflexion_entries re, json_each(re.tags) jt "
            f"WHERE jt.value IN ({tag_placeholders}))"
        )
        params.extend(tags)

    if category:
        clauses.append("category = ?")
        params.append(category)

    where = " WHERE " + " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM reflexion_entries{where} ORDER BY id DESC",
        params,
    ).fetchall()
    return [_row_to_reflexion_entry(r) for r in rows]


# ---------------------------------------------------------------------------
# Task eval operations
# ---------------------------------------------------------------------------

def store_task_eval(conn: sqlite3.Connection, eval_: TaskEval) -> str:
    """Validate and store a task eval.  Returns the task_id."""
    tr = eval_.test_results
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO task_evals "
            "(task_id, milestone, status, started_at, completed_at, "
            "review_cycles, security_review, test_total, test_passed, "
            "test_failed, test_skipped, files_planned, files_touched, "
            "scope_violations, reflexion_entries_created, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                eval_.task_id, eval_.milestone, eval_.status.value,
                eval_.started_at, eval_.completed_at,
                eval_.review_cycles, int(eval_.security_review),
                tr.total, tr.passed, tr.failed, tr.skipped,
                json.dumps(eval_.files_planned), json.dumps(eval_.files_touched),
                eval_.scope_violations, eval_.reflexion_entries_created,
                eval_.notes,
            ),
        )
        _log_event(conn, "store_eval", "task_eval", eval_.task_id,
                   f"cycles={eval_.review_cycles} tests={tr.total}")
    return eval_.task_id


def get_task_eval(conn: sqlite3.Connection, task_id: str) -> TaskEval | None:
    """Fetch a single task eval by task_id."""
    row = conn.execute(
        "SELECT * FROM task_evals WHERE task_id = ?", (task_id,)
    ).fetchone()
    return _row_to_task_eval(row) if row else None


def get_task_evals(
    conn: sqlite3.Connection,
    milestone: str | None = None,
    status: str | None = None,
) -> list[TaskEval]:
    """Fetch task evals, optionally filtered."""
    clauses: list[str] = []
    params: list[Any] = []
    if milestone:
        clauses.append("milestone = ?")
        params.append(milestone)
    if status:
        clauses.append("status = ?")
        params.append(status)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM task_evals{where} ORDER BY task_id", params
    ).fetchall()
    return [_row_to_task_eval(r) for r in rows]


# ---------------------------------------------------------------------------
# Review result operations
# ---------------------------------------------------------------------------

def store_review_result(conn: sqlite3.Connection, result: ReviewResult) -> int:
    """Validate and store a review result. Returns the auto-generated rowid."""
    with conn:
        cursor = conn.execute(
            "INSERT INTO review_results "
            "(task_id, reviewer, verdict, cycle, criteria_assessed, "
            "criteria_passed, criteria_failed, findings, scope_issues, "
            "decision_compliance, raw_output, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result.task_id, result.reviewer, result.verdict.value,
                result.cycle, result.criteria_assessed,
                result.criteria_passed, result.criteria_failed,
                json.dumps([f.model_dump() for f in result.findings]),
                json.dumps(result.scope_issues),
                json.dumps(result.decision_compliance),
                result.raw_output, result.created_at,
            ),
        )
        _log_event(conn, "store_review", "review", result.task_id,
                   f"reviewer={result.reviewer} verdict={result.verdict.value} cycle={result.cycle}")
    result_id: int = cursor.lastrowid  # type: ignore[assignment]
    return result_id


def get_review_results(
    conn: sqlite3.Connection,
    task_id: str,
    cycle: int | None = None,
) -> list[ReviewResult]:
    """Fetch review results for a task, optionally filtered by cycle."""
    if cycle is not None:
        rows = conn.execute(
            "SELECT * FROM review_results WHERE task_id = ? AND cycle = ? ORDER BY id",
            (task_id, cycle),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM review_results WHERE task_id = ? ORDER BY id",
            (task_id,),
        ).fetchall()
    return [_row_to_review_result(r) for r in rows]


def get_latest_review_cycle(conn: sqlite3.Connection, task_id: str) -> int:
    """Return the highest cycle number for a task. 0 if no reviews exist."""
    row = conn.execute(
        "SELECT MAX(cycle) AS max_cycle FROM review_results WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if not row or row["max_cycle"] is None:
        return 0
    max_cycle: int = row["max_cycle"]
    return max_cycle


# ---------------------------------------------------------------------------
# Deferred finding operations
# ---------------------------------------------------------------------------

def next_deferred_finding_id(conn: sqlite3.Connection) -> str:
    """Generate the next deferred finding ID: DF-01, DF-02, ..."""
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) AS max_num "
        "FROM deferred_findings"
    ).fetchone()
    if not row or row["max_num"] is None:
        return "DF-01"
    num = row["max_num"] + 1
    return f"DF-{num:02d}"


def store_deferred_finding(conn: sqlite3.Connection, finding: DeferredFinding) -> str:
    """Validate and store a deferred finding. Returns the finding ID."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO deferred_findings "
            "(id, discovered_in, category, affected_area, files_likely, "
            "spec_reference, description, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                finding.id, finding.discovered_in, finding.category.value,
                finding.affected_area, json.dumps(finding.files_likely),
                finding.spec_reference, finding.description, finding.status.value,
            ),
        )
        _log_event(conn, "store_deferred", "deferred_finding", finding.id,
                   f"cat={finding.category.value} in={finding.discovered_in}")
    return finding.id


def get_deferred_findings(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[DeferredFinding]:
    """Fetch deferred findings, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM deferred_findings WHERE status = ? ORDER BY id",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM deferred_findings ORDER BY id"
        ).fetchall()
    return [_row_to_deferred_finding(r) for r in rows]


def update_deferred_finding_status(
    conn: sqlite3.Connection,
    finding_id: str,
    status: str,
) -> None:
    """Update the status of a deferred finding."""
    from core.models import DeferredFindingStatus
    valid = {s.value for s in DeferredFindingStatus}
    if status not in valid:
        raise DataError(f"Invalid deferred finding status: {status!r} (valid: {sorted(valid)})")
    with conn:
        conn.execute(
            "UPDATE deferred_findings SET status = ? WHERE id = ?",
            (status, finding_id),
        )
        _log_event(conn, "update_deferred", "deferred_finding", finding_id,
                   f"status={status}")


def get_deferred_findings_for_files(
    conn: sqlite3.Connection,
    files: list[str],
) -> list[DeferredFinding]:
    """Find deferred findings whose files_likely overlap with the given file list.

    Uses json_each() to match against the JSON array stored in the column.
    """
    if not files:
        return []
    placeholders = ",".join("?" for _ in files)
    rows = conn.execute(
        f"SELECT DISTINCT df.* FROM deferred_findings df, json_each(df.files_likely) jf "
        f"WHERE jf.value IN ({placeholders}) ORDER BY df.id",
        files,
    ).fetchall()
    return [_row_to_deferred_finding(r) for r in rows]


# ---------------------------------------------------------------------------
# Audit gap operations
# ---------------------------------------------------------------------------

def next_gap_id(conn: sqlite3.Connection) -> str:
    """Generate the next audit gap ID: GAP-01, GAP-02, ..."""
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 5) AS INTEGER)) AS max_num "
        "FROM audit_gaps"
    ).fetchone()
    if not row or row["max_num"] is None:
        return "GAP-01"
    num = row["max_num"] + 1
    return f"GAP-{num:02d}"


def store_audit_gap(conn: sqlite3.Connection, gap: AuditGap) -> str:
    """Validate and store an audit gap. Returns the gap ID."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO audit_gaps "
            "(id, category, severity, layer, title, description, "
            "trigger_ref, evidence, recommendation, status, resolved_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                gap.id, gap.category.value, gap.severity.value,
                gap.layer, gap.title, gap.description,
                gap.trigger, json.dumps(gap.evidence),
                gap.recommendation, gap.status, gap.resolved_by,
            ),
        )
        _log_event(conn, "store_audit_gap", "audit_gap", gap.id,
                   f"cat={gap.category.value} sev={gap.severity.value} layer={gap.layer}")
    return gap.id


def get_audit_gaps(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[AuditGap]:
    """Fetch audit gaps, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM audit_gaps WHERE status = ? ORDER BY id",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM audit_gaps ORDER BY id"
        ).fetchall()
    return [_row_to_audit_gap(r) for r in rows]


def update_audit_gap_status(
    conn: sqlite3.Connection,
    gap_id: str,
    status: str,
    resolved_by: str = "",
) -> None:
    """Update the status (and optionally resolved_by) of an audit gap."""
    from core.models import _VALID_GAP_STATUSES
    if status not in _VALID_GAP_STATUSES:
        raise DataError(f"Invalid audit gap status: {status!r} (valid: {sorted(_VALID_GAP_STATUSES)})")
    with conn:
        conn.execute(
            "UPDATE audit_gaps SET status = ?, resolved_by = ? WHERE id = ?",
            (status, resolved_by, gap_id),
        )
        _log_event(conn, "update_audit_gap", "audit_gap", gap_id,
                   f"status={status}" + (f" resolved_by={resolved_by}" if resolved_by else ""))


def clear_audit_gaps(conn: sqlite3.Connection) -> int:
    """Delete open audit gaps. Preserves accepted/dismissed gaps.

    Returns count of deleted rows.
    """
    with conn:
        cursor = conn.execute(
            "DELETE FROM audit_gaps WHERE status = 'open'"
        )
        count: int = cursor.rowcount
        _log_event(conn, "clear_audit_gaps", "audit_gap", "",
                   f"Cleared {count} open gaps")
    return count


def log_audit_completed(conn: sqlite3.Connection, gap_count: int) -> None:
    """Record that a full audit cycle completed successfully.

    Called at the END of cmd_audit, after all gaps are stored.
    check_synthesize_readiness() looks for this event as proof the audit ran.
    """
    with conn:
        _log_event(conn, "audit_completed", "audit_gap", "",
                   f"Audit completed: {gap_count} gaps found")


def check_synthesize_readiness(conn: sqlite3.Connection) -> dict[str, Any]:
    """Check whether the synthesize phase can be completed.

    Returns a structured dict with hard blockers and advisory warnings.
    Hard blockers prevent complete-phase; warnings are informational.
    """
    blockers: list[str] = []
    warnings: list[str] = []

    # 1. Tasks must exist
    task_count_row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM tasks"
    ).fetchone()
    task_count: int = task_count_row["cnt"] if task_count_row else 0
    if task_count == 0:
        blockers.append("No tasks stored. Run 'store-tasks' first.")

    # 2. Audit must have completed (check for audit_completed event, logged at end)
    audit_event = conn.execute(
        "SELECT COUNT(*) AS cnt FROM events WHERE action = 'audit_completed'"
    ).fetchone()
    audit_run = bool(audit_event and audit_event["cnt"] > 0)
    if not audit_run:
        blockers.append(
            "Completeness audit has not been run. "
            "Run 'audit' then resolve gaps with 'audit-accept'/'audit-dismiss'."
        )

    # 3. No open audit gaps (all must be accepted or dismissed)
    open_gaps_row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM audit_gaps WHERE status = 'open'"
    ).fetchone()
    open_gaps: int = open_gaps_row["cnt"] if open_gaps_row else 0
    if open_gaps > 0:
        blockers.append(
            f"{open_gaps} open audit gap(s) remain. "
            f"Resolve with 'audit-accept' or 'audit-dismiss' before proceeding."
        )

    # 4. Decomposition — advisory only (per-task check, not global boolean)
    decomp_row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM tasks t "
        "WHERE t.id LIKE 'T%' AND t.id NOT LIKE 'T%.%' "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM tasks sub WHERE sub.id LIKE t.id || '.%'"
        ")"
    ).fetchone()
    undecomposed: int = decomp_row["cnt"] if decomp_row else 0
    if undecomposed > 0:
        warnings.append(
            f"{undecomposed} parent task(s) could be decomposed. "
            f"Run 'decompose-list' to review. (Optional — not blocking.)"
        )

    return {
        "ready": len(blockers) == 0,
        "task_count": task_count,
        "audit_run": audit_run,
        "open_gaps": open_gaps,
        "blockers": blockers,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Deterministic analytics (pure SQL)
# ---------------------------------------------------------------------------

def get_review_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Aggregate review metrics from task evals."""
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            COALESCE(AVG(review_cycles), 0) as avg_cycles,
            SUM(CASE WHEN review_cycles = 0 THEN 1 ELSE 0 END) as first_try,
            SUM(scope_violations) as total_scope_violations,
            SUM(test_total) as total_tests,
            SUM(test_passed) as total_passed,
            SUM(test_failed) as total_failed
        FROM task_evals
    """).fetchone()
    total = row["total"]
    return {
        "total": total,
        "avg_cycles": round(row["avg_cycles"], 2),
        "first_try_pass_rate": round(row["first_try"] / total, 2) if total else 0,
        "total_scope_violations": row["total_scope_violations"] or 0,
        "total_tests": row["total_tests"] or 0,
        "total_passed": row["total_passed"] or 0,
        "total_failed": row["total_failed"] or 0,
    }


def get_scope_drift(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Compare planned vs touched files per task — detect scope creep."""
    rows = conn.execute(
        "SELECT task_id, files_planned, files_touched FROM task_evals"
    ).fetchall()
    result: list[dict[str, Any]] = []
    for r in rows:
        try:
            planned = set(json.loads(r["files_planned"]))
            touched = set(json.loads(r["files_touched"]))
        except (json.JSONDecodeError, TypeError):
            continue
        unplanned = touched - planned
        if unplanned:
            result.append({
                "task_id": r["task_id"],
                "planned": len(planned),
                "touched": len(touched),
                "unplanned_files": sorted(unplanned),
                "drift_score": round(len(unplanned) / max(len(planned), 1), 2),
            })
    return result


def get_milestone_velocity(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Compute average task duration per milestone using julianday()."""
    rows = conn.execute("""
        SELECT
            milestone,
            COUNT(*) as task_count,
            AVG(
                (julianday(completed_at) - julianday(started_at)) * 86400
            ) as avg_duration_seconds
        FROM task_evals
        WHERE completed_at IS NOT NULL
        GROUP BY milestone
        ORDER BY milestone
    """).fetchall()
    return [
        {
            "milestone": r["milestone"],
            "task_count": r["task_count"],
            "avg_duration_seconds": round(r["avg_duration_seconds"] or 0, 1),
        }
        for r in rows
    ]


def get_reflexion_patterns(conn: sqlite3.Connection) -> dict[str, Any]:
    """Detect patterns in reflexion entries: top categories, tags, systemic issues."""
    # Top categories
    cat_rows = conn.execute("""
        SELECT category, COUNT(*) as cnt
        FROM reflexion_entries
        GROUP BY category
        ORDER BY cnt DESC
    """).fetchall()

    # Top tags via json_each
    tag_rows = conn.execute("""
        SELECT jt.value as tag, COUNT(*) as cnt
        FROM reflexion_entries re, json_each(re.tags) jt
        GROUP BY jt.value
        ORDER BY cnt DESC
        LIMIT 20
    """).fetchall()

    # Systemic issues: category+tag combos with 3+ occurrences
    systemic_rows = conn.execute("""
        SELECT re.category, jt.value as tag, COUNT(*) as cnt
        FROM reflexion_entries re, json_each(re.tags) jt
        GROUP BY re.category, jt.value
        HAVING COUNT(*) >= 3
        ORDER BY cnt DESC
    """).fetchall()

    return {
        "top_categories": [
            {"category": r["category"], "count": r["cnt"]} for r in cat_rows
        ],
        "top_tags": [
            {"tag": r["tag"], "count": r["cnt"]} for r in tag_rows
        ],
        "systemic_issues": [
            {"category": r["category"], "tag": r["tag"], "count": r["cnt"]}
            for r in systemic_rows
        ],
    }


# ---------------------------------------------------------------------------
# Decision history
# ---------------------------------------------------------------------------

def get_decision_history(conn: sqlite3.Connection, decision_id: str) -> list[dict[str, Any]]:
    """Return past versions of a decision (most recent first)."""
    rows = conn.execute(
        "SELECT * FROM decisions_history WHERE id = ? ORDER BY replaced_at DESC",
        (decision_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _row_to_review_result(row: sqlite3.Row) -> ReviewResult:
    """Convert a DB row to a ReviewResult, with safe JSON parsing."""
    d = dict(row)
    for field in ("findings", "scope_issues", "decision_compliance"):
        try:
            d[field] = json.loads(d[field])
        except (json.JSONDecodeError, TypeError) as e:
            raise DataError(
                f"Corrupted JSON in review_result row {d.get('id', '?')}.{field}: {e}"
            ) from e
    # Convert raw findings dicts to ReviewFinding models
    try:
        d["findings"] = [ReviewFinding(**f) for f in d["findings"]]
    except (ValueError, TypeError) as e:
        raise DataError(
            f"Invalid finding in review_result {d.get('task_id', '?')}: {e}"
        ) from e
    # Remove the auto-increment id — ReviewResult model doesn't have it
    d.pop("id", None)
    return ReviewResult(**d)


def _row_to_audit_gap(row: sqlite3.Row) -> AuditGap:
    """Convert a DB row to an AuditGap, with safe JSON parsing."""
    d = dict(row)
    try:
        d["evidence"] = json.loads(d["evidence"])
    except (json.JSONDecodeError, TypeError) as e:
        raise DataError(
            f"Corrupted JSON in audit_gap {d.get('id', '?')}.evidence: {e}"
        ) from e
    # DB column is trigger_ref, model field is trigger
    d["trigger"] = d.pop("trigger_ref")
    return AuditGap(**d)


def _row_to_deferred_finding(row: sqlite3.Row) -> DeferredFinding:
    """Convert a DB row to a DeferredFinding, with safe JSON parsing."""
    d = dict(row)
    try:
        d["files_likely"] = json.loads(d["files_likely"])
    except (json.JSONDecodeError, TypeError) as e:
        raise DataError(
            f"Corrupted JSON in deferred_finding {d.get('id', '?')}.files_likely: {e}"
        ) from e
    return DeferredFinding(**d)


def _row_to_task(row: sqlite3.Row) -> Task:
    """Convert a DB row to a Task, with safe JSON parsing."""
    d = dict(row)
    json_fields = [
        "depends_on", "decision_refs", "files_create", "files_modify",
        "acceptance_criteria", "artifact_refs",
    ]
    for field in json_fields:
        try:
            d[field] = json.loads(d[field])
        except (json.JSONDecodeError, TypeError) as e:
            raise DataError(
                f"Corrupted JSON in task {d.get('id', '?')}.{field}: {e}"
            ) from e
    return Task(**d)


def _row_to_reflexion_entry(row: sqlite3.Row) -> ReflexionEntry:
    """Convert a DB row to a ReflexionEntry, with safe JSON parsing."""
    d = dict(row)
    for field in ("tags", "applies_to"):
        try:
            d[field] = json.loads(d[field])
        except (json.JSONDecodeError, TypeError) as e:
            raise DataError(
                f"Corrupted JSON in reflexion {d.get('id', '?')}.{field}: {e}"
            ) from e
    return ReflexionEntry(**d)


def _row_to_task_eval(row: sqlite3.Row) -> TaskEval:
    """Convert a DB row to a TaskEval, reconstructing nested TestResults."""
    d = dict(row)
    for field in ("files_planned", "files_touched"):
        try:
            d[field] = json.loads(d[field])
        except (json.JSONDecodeError, TypeError) as e:
            raise DataError(
                f"Corrupted JSON in task_eval {d.get('task_id', '?')}.{field}: {e}"
            ) from e
    # Reconstruct nested TestResults from flat columns
    d["test_results"] = TestResults(
        total=d.pop("test_total"),
        passed=d.pop("test_passed"),
        failed=d.pop("test_failed"),
        skipped=d.pop("test_skipped"),
    )
    # Convert SQLite int to bool
    d["security_review"] = bool(d["security_review"])
    return TaskEval(**d)

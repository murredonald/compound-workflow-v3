"""Tests for the completeness audit system.

Covers:
  - AuditGap model validation (IDs, enums, layers, statuses)
  - Feature implication rules (auth, RAG, CRUD, no false positives)
  - Cross-task contract checks (frontend→backend gaps)
  - Prompt building (template rendering, content)
  - LLM output parsing (valid, invalid, edge cases)
  - DB operations (schema v6, CRUD, clear)
  - Orchestrator CLI commands (audit, audit-validate, audit-accept, audit-dismiss)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core import db
from core.models import (
    AuditGap,
    AuditGapCategory,
    AuditGapSeverity,
    Decision,
    DecisionPrefix,
    Milestone,
    Task,
)
from engine.completeness import (
    IMPLICATION_RULES,
    _run_and_renumber_deterministic,
    _strip_markdown_fences,
    check_cross_task_contracts,
    check_decision_cross_refs,
    check_decision_implications,
    check_feature_implications,
    parse_audit_output,
    run_deterministic_audit,
    run_full_audit,
    run_specialist_exit_check,
)
from engine.renderer import get_audit_schema
from orchestrator import main as orch_main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary DB with schema and return (db_path, conn)."""
    db_path = tmp_path / "state.db"
    db.init_db("TestProject", db_path)
    conn = db.get_db(db_path)
    yield db_path, conn
    conn.close()


def _make_decision(id: str, prefix: str, number: int, title: str, rationale: str = "test") -> Decision:
    return Decision(id=id, prefix=DecisionPrefix(prefix), number=number, title=title, rationale=rationale)


def _make_task(id: str, title: str, milestone: str = "M1", goal: str = "", **kwargs) -> Task:
    return Task(id=id, title=title, milestone=milestone, goal=goal, **kwargs)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestAuditGapModel:
    def test_valid_gap(self):
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Missing logout",
            description="Auth without logout",
        )
        assert gap.id == "GAP-01"
        assert gap.status == "open"
        assert gap.resolved_by == ""

    def test_bad_gap_id(self):
        with pytest.raises(ValueError, match="GAP-NN"):
            AuditGap(
                id="BAD-01",
                category=AuditGapCategory.IMPLIED_FEATURE,
                severity=AuditGapSeverity.HIGH,
                layer="implication",
                title="Test",
                description="Test",
            )

    def test_bad_layer(self):
        with pytest.raises(ValueError, match="Layer"):
            AuditGap(
                id="GAP-01",
                category=AuditGapCategory.IMPLIED_FEATURE,
                severity=AuditGapSeverity.HIGH,
                layer="invalid",
                title="Test",
                description="Test",
            )

    def test_bad_status(self):
        with pytest.raises(ValueError, match="Status"):
            AuditGap(
                id="GAP-01",
                category=AuditGapCategory.IMPLIED_FEATURE,
                severity=AuditGapSeverity.HIGH,
                layer="implication",
                title="Test",
                description="Test",
                status="invalid",
            )

    def test_all_categories(self):
        cats = [c.value for c in AuditGapCategory]
        assert "implied-feature" in cats
        assert "dead-reference" in cats
        assert "missing-api-contract" in cats
        assert "incomplete-journey" in cats
        assert "missing-state" in cats
        assert "orphaned-component" in cats

    def test_all_severities(self):
        sevs = [s.value for s in AuditGapSeverity]
        assert sevs == ["critical", "high", "medium", "low"]


# ---------------------------------------------------------------------------
# Implication rule tests
# ---------------------------------------------------------------------------

class TestFeatureImplications:
    def test_auth_detects_missing_logout(self):
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT authentication", "Use JWT for auth")]
        tasks = [_make_task("T01", "Implement login page", goal="Build login form with JWT auth")]
        gaps = check_feature_implications(decisions, tasks)
        titles = [g.title for g in gaps]
        assert any("logout" in t.lower() for t in titles)

    def test_auth_no_gap_when_logout_exists(self):
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT authentication")]
        tasks = [
            _make_task("T01", "Implement login page", goal="Build login form"),
            _make_task("T02", "Implement logout endpoint", goal="Logout and clear session"),
        ]
        gaps = check_feature_implications(decisions, tasks)
        logout_gaps = [g for g in gaps if "logout" in g.title.lower()]
        assert len(logout_gaps) == 0

    def test_rag_detects_missing_chunking(self):
        decisions = [_make_decision("ARCH-01", "ARCH", 1, "Use RAG for knowledge base")]
        tasks = [_make_task("T01", "Set up RAG pipeline", goal="Build retrieval augmented generation")]
        gaps = check_feature_implications(decisions, tasks)
        titles = [g.title.lower() for g in gaps]
        assert any("chunking" in t or "chunk" in t for t in titles)

    def test_rag_no_gap_when_all_covered(self):
        decisions = [_make_decision("ARCH-01", "ARCH", 1, "Use RAG for knowledge base")]
        tasks = [
            _make_task("T01", "Document chunking", goal="Split documents into chunks for embedding"),
            _make_task("T02", "Embedding pipeline", goal="Vectorize chunks using embedding model"),
            _make_task("T03", "Vector store setup", goal="Set up ChromaDB vector store"),
            _make_task("T04", "Retrieval endpoint", goal="Build retrieval search endpoint"),
        ]
        gaps = check_feature_implications(decisions, tasks)
        # Should have no critical/high RAG gaps
        rag_gaps = [g for g in gaps if "rag" in g.trigger.lower() and g.severity.value in ("critical", "high")]
        assert len(rag_gaps) == 0

    def test_crud_detects_missing_empty_state(self):
        decisions = []
        tasks = [
            _make_task("T01", "Create resource", goal="CRUD operations for items"),
        ]
        gaps = check_feature_implications(decisions, tasks)
        titles = [g.title.lower() for g in gaps]
        assert any("empty state" in t for t in titles)

    def test_no_false_positives_empty_project(self):
        decisions = []
        tasks = [_make_task("T01", "Set up project structure", goal="Initialize the repo")]
        gaps = check_feature_implications(decisions, tasks)
        # A generic project setup should not trigger feature rules
        assert len(gaps) == 0

    def test_multiple_triggers_activated(self):
        decisions = [
            _make_decision("BACK-01", "BACK", 1, "JWT authentication"),
            _make_decision("ARCH-01", "ARCH", 1, "RAG knowledge base"),
        ]
        tasks = [
            _make_task("T01", "Login page", goal="Implement JWT login"),
            _make_task("T02", "RAG pipeline", goal="Build RAG for knowledge base"),
        ]
        gaps = check_feature_implications(decisions, tasks)
        # Should find gaps from both auth and RAG domains
        layers = {g.trigger for g in gaps}
        assert any("authentication" in l for l in layers)
        assert any("rag" in l for l in layers)

    def test_case_insensitive_matching(self):
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT AUTHENTICATION")]
        tasks = [_make_task("T01", "LOGIN page", goal="Build LOGIN form")]
        gaps = check_feature_implications(decisions, tasks)
        assert any("logout" in g.title.lower() for g in gaps)

    def test_gap_ids_sequential(self):
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT auth")]
        tasks = [_make_task("T01", "Login", goal="Login with JWT auth")]
        gaps = check_feature_implications(decisions, tasks)
        ids = [g.id for g in gaps]
        for i, gid in enumerate(ids, 1):
            assert gid == f"GAP-{i:02d}"


# ---------------------------------------------------------------------------
# Cross-task contract tests
# ---------------------------------------------------------------------------

class TestContractChecks:
    def test_frontend_api_call_no_backend(self):
        tasks = [
            _make_task("T01", "User form", goal="Frontend form POSTs to /api/users",
                       decision_refs=["FRONT-01"]),
        ]
        decisions = [_make_decision("FRONT-01", "FRONT", 1, "React form")]
        gaps = check_cross_task_contracts(tasks, decisions)
        assert len(gaps) > 0
        assert any("api" in g.title.lower() or "backend" in g.title.lower() for g in gaps)

    def test_frontend_api_with_backend_no_gap(self):
        tasks = [
            _make_task("T01", "User form", goal="Frontend form POSTs to /api/users",
                       decision_refs=["FRONT-01"]),
            _make_task("T02", "Users API endpoint", goal="Create /api/users REST endpoint",
                       decision_refs=["BACK-01"]),
        ]
        decisions = [
            _make_decision("FRONT-01", "FRONT", 1, "React form"),
            _make_decision("BACK-01", "BACK", 1, "Express API"),
        ]
        gaps = check_cross_task_contracts(tasks, decisions)
        # The specific /api/users path should be found in backend
        path_gaps = [g for g in gaps if "/api/users" in g.title]
        assert len(path_gaps) == 0

    def test_no_tasks_no_crash(self):
        gaps = check_cross_task_contracts([], [])
        assert gaps == []

    def test_specific_api_path_mismatch(self):
        tasks = [
            _make_task("T01", "Dashboard", goal="Frontend calls /api/analytics/summary",
                       decision_refs=["FRONT-01"]),
            _make_task("T02", "Users API", goal="Create /api/users endpoint",
                       decision_refs=["BACK-01"]),
        ]
        decisions = [
            _make_decision("FRONT-01", "FRONT", 1, "Dashboard UI"),
            _make_decision("BACK-01", "BACK", 1, "User API"),
        ]
        gaps = check_cross_task_contracts(tasks, decisions)
        path_gaps = [g for g in gaps if "/api/analytics" in g.title]
        assert len(path_gaps) > 0

    def test_backend_only_no_crash(self):
        tasks = [
            _make_task("T01", "API setup", goal="Create backend API endpoints",
                       decision_refs=["BACK-01"]),
        ]
        decisions = [_make_decision("BACK-01", "BACK", 1, "Express API")]
        gaps = check_cross_task_contracts(tasks, decisions)
        # Backend-only project should not crash
        assert isinstance(gaps, list)


# ---------------------------------------------------------------------------
# Prompt building tests
# ---------------------------------------------------------------------------

class TestPromptBuilding:
    def test_prompt_contains_project_name(self, tmp_db):
        _, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_tasks(conn, [_make_task("T01", "Setup", goal="Init project")])
        from engine.completeness import build_audit_prompt
        prompt = build_audit_prompt(conn)
        assert "TestProject" in prompt

    def test_prompt_contains_tasks(self, tmp_db):
        _, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_tasks(conn, [_make_task("T01", "Setup project", goal="Initialize everything")])
        from engine.completeness import build_audit_prompt
        prompt = build_audit_prompt(conn)
        assert "T01" in prompt
        assert "Setup project" in prompt

    def test_prompt_contains_audit_schema(self, tmp_db):
        _, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_tasks(conn, [_make_task("T01", "Setup", goal="Init")])
        from engine.completeness import build_audit_prompt
        prompt = build_audit_prompt(conn)
        assert '"journeys"' in prompt
        assert '"gaps"' in prompt

    def test_audit_schema_valid_json(self):
        schema_str = get_audit_schema()
        parsed = json.loads(schema_str)
        assert "journeys" in parsed
        assert "gaps" in parsed


# ---------------------------------------------------------------------------
# Parse/validate LLM output tests
# ---------------------------------------------------------------------------

class TestParseAuditOutput:
    def test_valid_output(self):
        data = {
            "journeys": [{"name": "Registration", "steps": []}],
            "gaps": [
                {
                    "category": "implied-feature",
                    "severity": "critical",
                    "title": "Missing email verification",
                    "description": "Registration has no email verification",
                    "trigger": "T01",
                    "evidence": ["T01 creates user", "No verify email task"],
                    "recommendation": "Add email verification task",
                }
            ],
        }
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 1
        assert len(errors) == 0
        assert gaps[0].id == "GAP-01"
        assert gaps[0].category == AuditGapCategory.IMPLIED_FEATURE
        assert gaps[0].layer == "journey"

    def test_bad_json(self):
        gaps, errors = parse_audit_output("not json at all")
        assert len(gaps) == 0
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_numbering_from_existing(self):
        data = {
            "gaps": [
                {
                    "category": "missing-state",
                    "severity": "medium",
                    "title": "No loading state",
                    "description": "Missing loading indicator",
                }
            ],
        }
        gaps, errors = parse_audit_output(json.dumps(data), existing_gap_count=5)
        assert gaps[0].id == "GAP-06"

    def test_invalid_category(self):
        data = {
            "gaps": [
                {
                    "category": "nonexistent",
                    "severity": "high",
                    "title": "Test",
                    "description": "Test",
                }
            ],
        }
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 0
        assert len(errors) == 1
        assert "invalid category" in errors[0]

    def test_invalid_severity(self):
        data = {
            "gaps": [
                {
                    "category": "implied-feature",
                    "severity": "ultra-high",
                    "title": "Test",
                    "description": "Test",
                }
            ],
        }
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 0
        assert len(errors) == 1
        assert "invalid severity" in errors[0]

    def test_missing_title(self):
        data = {"gaps": [{"category": "implied-feature", "severity": "high", "description": "Test"}]}
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 0
        assert len(errors) == 1

    def test_empty_gaps_list(self):
        data = {"journeys": [], "gaps": []}
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 0
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# DB tests
# ---------------------------------------------------------------------------

class TestAuditGapDB:
    def test_schema_v7_has_audit_gaps(self, tmp_db):
        _, conn = tmp_db
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        assert row["value"] == "7"
        # Table exists
        conn.execute("SELECT COUNT(*) FROM audit_gaps")

    def test_store_and_read_gap(self, tmp_db):
        _, conn = tmp_db
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Missing logout",
            description="Auth without logout",
            trigger="rule:authentication",
            evidence=["Login found", "No logout task"],
            recommendation="Add logout task",
        )
        db.store_audit_gap(conn, gap)
        stored = db.get_audit_gaps(conn)
        assert len(stored) == 1
        assert stored[0].id == "GAP-01"
        assert stored[0].evidence == ["Login found", "No logout task"]
        assert stored[0].trigger == "rule:authentication"

    def test_update_gap_status(self, tmp_db):
        _, conn = tmp_db
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Test",
            description="Test",
        )
        db.store_audit_gap(conn, gap)
        db.update_audit_gap_status(conn, "GAP-01", "accepted", resolved_by="T05")
        stored = db.get_audit_gaps(conn)
        assert stored[0].status == "accepted"
        assert stored[0].resolved_by == "T05"

    def test_filter_by_status(self, tmp_db):
        _, conn = tmp_db
        for i in range(3):
            gap = AuditGap(
                id=f"GAP-{i+1:02d}",
                category=AuditGapCategory.IMPLIED_FEATURE,
                severity=AuditGapSeverity.HIGH,
                layer="implication",
                title=f"Gap {i+1}",
                description=f"Description {i+1}",
            )
            db.store_audit_gap(conn, gap)
        db.update_audit_gap_status(conn, "GAP-02", "dismissed")
        open_gaps = db.get_audit_gaps(conn, status="open")
        assert len(open_gaps) == 2

    def test_clear_gaps(self, tmp_db):
        _, conn = tmp_db
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Test",
            description="Test",
        )
        db.store_audit_gap(conn, gap)
        count = db.clear_audit_gaps(conn)
        assert count == 1
        assert len(db.get_audit_gaps(conn)) == 0

    def test_next_gap_id(self, tmp_db):
        _, conn = tmp_db
        assert db.next_gap_id(conn) == "GAP-01"
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Test",
            description="Test",
        )
        db.store_audit_gap(conn, gap)
        assert db.next_gap_id(conn) == "GAP-02"

    def test_migration_v5_to_v7(self, tmp_path):
        """Create a v5 DB, then open with current code — all migrations should run."""
        db_path = tmp_path / "migrate.db"
        # Create a v5 DB manually
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        # Create minimal schema (meta + pipeline + phases + milestones + tasks)
        conn.executescript("""
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE pipeline (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                project_name TEXT NOT NULL,
                project_summary TEXT NOT NULL DEFAULT '',
                current_phase TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE phases (
                id TEXT PRIMARY KEY, label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                order_index INTEGER NOT NULL DEFAULT 0,
                started_at TEXT, completed_at TEXT
            );
            CREATE TABLE milestones (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                goal TEXT NOT NULL DEFAULT '', order_index INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                milestone TEXT NOT NULL REFERENCES milestones(id),
                status TEXT NOT NULL DEFAULT 'pending',
                goal TEXT NOT NULL DEFAULT '',
                depends_on TEXT NOT NULL DEFAULT '[]',
                decision_refs TEXT NOT NULL DEFAULT '[]',
                files_create TEXT NOT NULL DEFAULT '[]',
                files_modify TEXT NOT NULL DEFAULT '[]',
                acceptance_criteria TEXT NOT NULL DEFAULT '[]',
                verification_cmd TEXT,
                artifact_refs TEXT NOT NULL DEFAULT '[]',
                parent_task TEXT
            );
            CREATE TABLE events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL, actor TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL, target_type TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '',
                phase TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE decisions (
                id TEXT PRIMARY KEY, prefix TEXT NOT NULL, number INTEGER NOT NULL,
                title TEXT NOT NULL, rationale TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            );
            CREATE TABLE decisions_history (
                rowid_h INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL, prefix TEXT NOT NULL, number INTEGER NOT NULL,
                title TEXT NOT NULL, rationale TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                replaced_at TEXT NOT NULL
            );
            CREATE TABLE constraints (
                id TEXT PRIMARY KEY, category TEXT NOT NULL,
                description TEXT NOT NULL, source TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE reflexion_entries (
                id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
                task_id TEXT NOT NULL REFERENCES tasks(id),
                tags TEXT NOT NULL DEFAULT '[]', category TEXT NOT NULL,
                severity TEXT NOT NULL, what_happened TEXT NOT NULL,
                root_cause TEXT NOT NULL, lesson TEXT NOT NULL,
                applies_to TEXT NOT NULL DEFAULT '[]',
                preventive_action TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE task_evals (
                task_id TEXT PRIMARY KEY REFERENCES tasks(id),
                milestone TEXT NOT NULL REFERENCES milestones(id),
                status TEXT NOT NULL, started_at TEXT NOT NULL,
                completed_at TEXT, review_cycles INTEGER NOT NULL DEFAULT 0,
                security_review INTEGER NOT NULL DEFAULT 0,
                test_total INTEGER NOT NULL DEFAULT 0,
                test_passed INTEGER NOT NULL DEFAULT 0,
                test_failed INTEGER NOT NULL DEFAULT 0,
                test_skipped INTEGER NOT NULL DEFAULT 0,
                files_planned TEXT NOT NULL DEFAULT '[]',
                files_touched TEXT NOT NULL DEFAULT '[]',
                scope_violations INTEGER NOT NULL DEFAULT 0,
                reflexion_entries_created INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE review_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL REFERENCES tasks(id),
                reviewer TEXT NOT NULL, verdict TEXT NOT NULL,
                cycle INTEGER NOT NULL DEFAULT 1,
                criteria_assessed INTEGER NOT NULL DEFAULT 0,
                criteria_passed INTEGER NOT NULL DEFAULT 0,
                criteria_failed INTEGER NOT NULL DEFAULT 0,
                findings TEXT NOT NULL DEFAULT '[]',
                scope_issues TEXT NOT NULL DEFAULT '[]',
                decision_compliance TEXT NOT NULL DEFAULT '{}',
                raw_output TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            );
            CREATE TABLE deferred_findings (
                id TEXT PRIMARY KEY,
                discovered_in TEXT NOT NULL REFERENCES tasks(id),
                category TEXT NOT NULL, affected_area TEXT NOT NULL,
                files_likely TEXT NOT NULL DEFAULT '[]',
                spec_reference TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open'
            );
            CREATE TABLE artifacts (
                type TEXT PRIMARY KEY, content TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("INSERT INTO meta VALUES ('schema_version', '5')")
        conn.execute(
            "INSERT INTO pipeline VALUES (1, 'MigrateTest', '', 'plan', "
            "'2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
        conn.commit()
        conn.close()

        # Now open with our code — all migrations should run (v5→v6→v7)
        conn2 = db.get_db(db_path)
        # Verify audit_gaps table exists and version is current
        row = conn2.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        assert row["value"] == "7"
        conn2.execute("SELECT COUNT(*) FROM audit_gaps")
        conn2.close()


# ---------------------------------------------------------------------------
# Orchestrator CLI tests
# ---------------------------------------------------------------------------

class TestOrchestratorAudit:
    def test_audit_command(self, tmp_db, capsys, monkeypatch):
        db_path, conn = tmp_db
        conn.close()

        # Set up milestones + tasks with auth trigger but no logout
        conn = db.get_db(db_path)
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_decisions(conn, [_make_decision("BACK-01", "BACK", 1, "JWT authentication")])
        db.store_tasks(conn, [_make_task("T01", "Login page", goal="Build login with JWT auth")])
        conn.close()

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["audit"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "ok"
        assert output["gap_count"] > 0
        # LLM prompt goes to stderr
        assert "TestProject" in captured.err

    def test_audit_validate_valid(self, tmp_db, capsys, monkeypatch):
        db_path, conn = tmp_db
        conn.close()

        conn = db.get_db(db_path)
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        conn.close()

        # Write LLM output to temp file
        llm_output = json.dumps({
            "journeys": [],
            "gaps": [
                {
                    "category": "incomplete-journey",
                    "severity": "high",
                    "title": "Missing onboarding flow",
                    "description": "New users land on empty dashboard",
                    "trigger": "registration journey",
                    "evidence": ["No onboarding task"],
                    "recommendation": "Add onboarding wizard task",
                }
            ],
        })
        tmp_file = db_path.parent / "llm_output.json"
        tmp_file.write_text(llm_output, encoding="utf-8")

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["audit-validate", "--file", str(tmp_file)])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "ok"
        assert output["llm_gaps_added"] == 1
        assert output["total_gaps"] == 1

    def test_audit_accept_creates_task(self, tmp_db, capsys, monkeypatch):
        db_path, conn = tmp_db
        conn.close()

        # Setup: store milestone + task + gap
        conn = db.get_db(db_path)
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_tasks(conn, [_make_task("T01", "Login", goal="Build login")])
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Missing logout",
            description="Auth without logout",
        )
        db.store_audit_gap(conn, gap)
        conn.close()

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["audit-accept", "GAP-01"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "ok"
        assert len(output["accepted"]) == 1
        assert output["accepted"][0]["gap_id"] == "GAP-01"
        new_task_id = output["accepted"][0]["task_id"]
        assert new_task_id == "T02"

        # Verify task was stored
        conn = db.get_db(db_path)
        task = db.get_task(conn, new_task_id)
        assert task is not None
        assert task.title == "Missing logout"
        conn.close()

    def test_audit_dismiss(self, tmp_db, capsys, monkeypatch):
        db_path, conn = tmp_db
        conn.close()

        conn = db.get_db(db_path)
        gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.LOW,
            layer="implication",
            title="Optional feature",
            description="Not needed",
        )
        db.store_audit_gap(conn, gap)
        conn.close()

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["audit-dismiss", "GAP-01"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "ok"
        assert "GAP-01" in output["dismissed"]

        # Verify status changed
        conn = db.get_db(db_path)
        gaps = db.get_audit_gaps(conn, status="dismissed")
        assert len(gaps) == 1
        conn.close()

    def test_audit_dismiss_nonexistent(self, tmp_db, capsys, monkeypatch):
        db_path, conn = tmp_db
        conn.close()

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["audit-dismiss", "GAP-99"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "partial"
        assert len(output["errors"]) == 1


# ---------------------------------------------------------------------------
# Integration / E2E
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_deterministic_audit_e2e(self, tmp_db):
        """Full deterministic audit: auth decisions but no logout task."""
        _, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_decisions(conn, [
            _make_decision("BACK-01", "BACK", 1, "JWT authentication", "Use JWT tokens"),
            _make_decision("FRONT-01", "FRONT", 1, "React SPA", "Single page application"),
        ])
        db.store_tasks(conn, [
            _make_task("T01", "Login page", goal="Build login form with JWT auth",
                       decision_refs=["BACK-01", "FRONT-01"]),
            _make_task("T02", "Dashboard", goal="Main dashboard after login"),
        ])

        result = run_deterministic_audit(conn)
        assert result["gap_count"] > 0
        gap_titles = [g.title.lower() for g in result["deterministic_gaps"]]
        assert any("logout" in t for t in gap_titles)
        assert "llm_prompt" in result
        assert len(result["llm_prompt"]) > 100

    def test_full_audit_e2e(self, tmp_db):
        """Full audit with both deterministic and LLM gaps."""
        _, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_decisions(conn, [_make_decision("BACK-01", "BACK", 1, "JWT authentication")])
        db.store_tasks(conn, [_make_task("T01", "Login", goal="JWT login page")])

        # Store some deterministic gaps first
        det_gap = AuditGap(
            id="GAP-01",
            category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH,
            layer="implication",
            title="Missing logout",
            description="Auth without logout",
        )
        db.store_audit_gap(conn, det_gap)

        # Simulate LLM output
        llm_json = json.dumps({
            "journeys": [{"name": "Registration", "steps": []}],
            "gaps": [
                {
                    "category": "incomplete-journey",
                    "severity": "critical",
                    "title": "No password reset",
                    "description": "Users cannot reset forgotten passwords",
                    "trigger": "T01",
                    "evidence": ["Login exists but no forgot password"],
                    "recommendation": "Add password reset flow",
                }
            ],
        })

        result = run_full_audit(conn, llm_json)
        assert result["total"] == 2  # 1 deterministic + 1 LLM
        assert len(result["llm_gaps"]) == 1
        assert result["llm_gaps"][0].id == "GAP-02"

    def test_rules_cover_expected_domains(self):
        """Verify the implication rules cover all planned domains."""
        rule_names = {r.name for r in IMPLICATION_RULES}
        expected = {
            "authentication", "user-profile", "crud-resources", "search",
            "rag-ai", "file-upload", "notifications", "navigation",
            "payment", "real-time", "email", "multi-tenant", "dashboard",
            "forms", "pagination",
        }
        assert rule_names == expected


# ---------------------------------------------------------------------------
# Decision-level checks (specialist exit)
# ---------------------------------------------------------------------------

class TestDecisionImplications:
    """Test implication rules applied to decisions only (no tasks)."""

    def test_auth_decision_detects_missing_logout(self):
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT authentication", "Use JWT for login")]
        warnings = check_decision_implications(decisions)
        titles = [w["title"].lower() for w in warnings]
        assert any("logout" in t for t in titles)

    def test_no_trigger_no_warnings(self):
        decisions = [_make_decision("ARCH-01", "ARCH", 1, "Monorepo structure", "Keep it simple")]
        warnings = check_decision_implications(decisions)
        assert len(warnings) == 0

    def test_rag_decision_detects_missing_chunking(self):
        decisions = [_make_decision("LLM-01", "LLM", 1, "RAG pipeline", "Use retrieval augmented generation")]
        warnings = check_decision_implications(decisions)
        titles = [w["title"].lower() for w in warnings]
        assert any("chunk" in t for t in titles)
        assert any("embed" in t for t in titles)

    def test_covered_requirement_no_warning(self):
        decisions = [
            _make_decision("BACK-01", "BACK", 1, "JWT authentication", "Use JWT"),
            _make_decision("BACK-02", "BACK", 2, "Logout endpoint", "Sign out users"),
            _make_decision("BACK-03", "BACK", 3, "Password reset flow", "Forgot password email"),
            _make_decision("SEC-01", "SEC", 1, "Session timeout", "Token expiry after 30min"),
        ]
        warnings = check_decision_implications(decisions)
        # Auth rule fired, but all three requirements are covered
        titles = [w["title"].lower() for w in warnings]
        assert not any("logout" in t for t in titles)
        assert not any("password reset" in t for t in titles)
        assert not any("session expir" in t for t in titles)

    def test_warning_structure(self):
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT auth", "Login system")]
        warnings = check_decision_implications(decisions)
        assert len(warnings) > 0
        w = warnings[0]
        assert "type" in w
        assert w["type"] == "implication"
        assert "rule" in w
        assert "severity" in w
        assert "title" in w
        assert "description" in w
        assert "evidence" in w


class TestDecisionCrossRefs:
    """Test cross-domain contract checks between decision prefixes."""

    def test_front_references_api_no_back_decisions(self):
        """FRONT mentions API but no BACK decisions exist → warning."""
        decisions = [
            _make_decision("FRONT-01", "FRONT", 1, "Login page", "Calls API endpoint for auth"),
        ]
        warnings = check_decision_cross_refs(decisions, "FRONT")
        assert len(warnings) > 0
        assert any("BACK" in w["target"] for w in warnings)

    def test_front_with_back_no_warning(self):
        """FRONT mentions API and BACK decisions exist covering it → no warning."""
        decisions = [
            _make_decision("FRONT-01", "FRONT", 1, "Login page", "Calls API endpoint for auth"),
            _make_decision("BACK-01", "BACK", 1, "Auth API", "REST endpoint for authentication"),
        ]
        warnings = check_decision_cross_refs(decisions, "FRONT")
        # BACK exists and mentions "api" — no cross-domain warning for that contract
        back_missing = [w for w in warnings if w["target"] == "BACK" and "api" in w.get("description", "").lower()]
        assert len(back_missing) == 0

    def test_back_references_auth_no_sec(self):
        """BACK mentions auth but no SEC decisions exist → warning."""
        decisions = [
            _make_decision("BACK-01", "BACK", 1, "JWT token system", "Authentication with encrypted JWT"),
        ]
        warnings = check_decision_cross_refs(decisions, "BACK")
        assert any("SEC" in w["target"] for w in warnings)

    def test_no_triggers_no_warnings(self):
        """Decisions without cross-domain triggers → no warnings."""
        decisions = [
            _make_decision("ARCH-01", "ARCH", 1, "Monorepo", "Single repo layout"),
        ]
        warnings = check_decision_cross_refs(decisions, "ARCH")
        assert len(warnings) == 0

    def test_only_checks_current_prefix(self):
        """Only checks contracts where source matches current_prefix."""
        decisions = [
            _make_decision("FRONT-01", "FRONT", 1, "Login API call", "Fetch from API"),
            _make_decision("BACK-01", "BACK", 1, "User dashboard page", "Shows UI view"),
        ]
        # Check from BACK perspective — should flag FRONT reference, not BACK's own
        back_warnings = check_decision_cross_refs(decisions, "BACK")
        for w in back_warnings:
            assert w["source"] == "BACK"

    def test_target_exists_but_missing_coverage(self):
        """Target domain exists but doesn't cover the triggering concept."""
        decisions = [
            _make_decision("FRONT-01", "FRONT", 1, "Login page", "Calls authentication API"),
            _make_decision("BACK-01", "BACK", 1, "Database schema", "PostgreSQL models"),
        ]
        # BACK exists but doesn't mention API/endpoint — medium warning
        warnings = check_decision_cross_refs(decisions, "FRONT")
        api_warnings = [w for w in warnings if w["target"] == "BACK"]
        assert any(w["severity"] == "medium" for w in api_warnings)

    def test_warning_structure(self):
        """Verify warning dict shape."""
        decisions = [_make_decision("FRONT-01", "FRONT", 1, "Login", "API endpoint call")]
        warnings = check_decision_cross_refs(decisions, "FRONT")
        assert len(warnings) > 0
        w = warnings[0]
        assert w["type"] == "cross-domain"
        assert "source" in w
        assert "target" in w
        assert "severity" in w
        assert "title" in w
        assert "evidence" in w


class TestSpecialistExitCheck:
    """Test the orchestrated specialist exit check."""

    def test_clean_check(self, tmp_db):
        """Specialist with no cross-domain issues."""
        _, conn = tmp_db
        db.store_decisions(conn, [
            _make_decision("ARCH-01", "ARCH", 1, "Monorepo structure", "Simple layout"),
        ])
        result = run_specialist_exit_check(conn, "ARCH")
        assert result["status"] == "clean"
        assert result["total_warnings"] == 0

    def test_warnings_found(self, tmp_db):
        """Backend specialist with auth but no SEC decisions."""
        _, conn = tmp_db
        db.store_decisions(conn, [
            _make_decision("BACK-01", "BACK", 1, "JWT authentication", "Login with JWT tokens"),
        ])
        result = run_specialist_exit_check(conn, "BACK")
        assert result["status"] == "warnings"
        assert result["total_warnings"] > 0
        # Should have both implication warnings (no logout) and cross-domain (no SEC)
        assert len(result["implication_warnings"]) > 0
        assert len(result["cross_domain_warnings"]) > 0

    def test_severity_summary(self, tmp_db):
        _, conn = tmp_db
        db.store_decisions(conn, [
            _make_decision("BACK-01", "BACK", 1, "JWT auth", "Authentication system"),
        ])
        result = run_specialist_exit_check(conn, "BACK")
        assert "by_severity" in result
        total = sum(result["by_severity"].values())
        assert total == result["total_warnings"]

    def test_orchestrator_command(self, tmp_db, capsys, monkeypatch):
        """Test specialist-check CLI command."""
        db_path, conn = tmp_db
        db.store_decisions(conn, [
            _make_decision("FRONT-01", "FRONT", 1, "Login page", "API call to backend"),
        ])
        conn.close()

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["specialist-check", "FRONT"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "warnings"
        assert output["prefix"] == "FRONT"
        assert output["total_warnings"] > 0

    def test_orchestrator_clean(self, tmp_db, capsys, monkeypatch):
        """Clean specialist returns clean status."""
        db_path, conn = tmp_db
        db.store_decisions(conn, [
            _make_decision("ARCH-01", "ARCH", 1, "Simple architecture", "Basic layout"),
        ])
        conn.close()

        monkeypatch.chdir(db_path.parent)
        ret = orch_main(["specialist-check", "ARCH"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["status"] == "clean"
        assert output["total_warnings"] == 0


# ---------------------------------------------------------------------------
# Robustness tests (audit findings)
# ---------------------------------------------------------------------------

class TestMarkdownFenceStripping:
    """Verify LLM output wrapped in markdown fences is handled."""

    def test_strip_json_fence(self):
        raw = '```json\n{"gaps": []}\n```'
        assert _strip_markdown_fences(raw) == '{"gaps": []}'

    def test_strip_plain_fence(self):
        raw = '```\n{"gaps": []}\n```'
        assert _strip_markdown_fences(raw) == '{"gaps": []}'

    def test_no_fence_passthrough(self):
        raw = '{"gaps": []}'
        assert _strip_markdown_fences(raw) == '{"gaps": []}'

    def test_parse_with_fences(self):
        """Full parse_audit_output with markdown fences."""
        data = '```json\n{"gaps": [{"category": "implied-feature", "severity": "high", "title": "Test gap", "description": "Test desc"}]}\n```'
        gaps, errors = parse_audit_output(data)
        assert len(gaps) == 1
        assert len(errors) == 0
        assert gaps[0].title == "Test gap"

    def test_fence_with_whitespace(self):
        raw = '  ```json  \n  {"gaps": []}  \n  ```  '
        result = _strip_markdown_fences(raw)
        parsed = json.loads(result)
        assert parsed == {"gaps": []}


class TestEvidenceValidation:
    """Verify evidence items are coerced to strings."""

    def test_dict_evidence_coerced(self):
        """LLM sends dict in evidence array — coerced to string."""
        data = {
            "gaps": [{
                "category": "implied-feature",
                "severity": "high",
                "title": "Test",
                "description": "Test",
                "evidence": [{"ref": "T01", "type": "task"}],
            }],
        }
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 1
        # Evidence should be a list of strings (dict stringified)
        assert all(isinstance(e, str) for e in gaps[0].evidence)

    def test_mixed_evidence(self):
        """Mix of strings and non-strings in evidence."""
        data = {
            "gaps": [{
                "category": "implied-feature",
                "severity": "high",
                "title": "Test",
                "description": "Test",
                "evidence": ["valid string", 42, None],
            }],
        }
        gaps, errors = parse_audit_output(json.dumps(data))
        assert len(gaps) == 1
        assert len(gaps[0].evidence) == 3
        assert all(isinstance(e, str) for e in gaps[0].evidence)


class TestGapIdRenumbering:
    """Verify GAP IDs don't collide between Layer 1 and Layer 2."""

    def test_renumber_avoids_duplicates(self):
        """Contract gaps must be renumbered to continue from implication gaps."""
        decisions = [_make_decision("BACK-01", "BACK", 1, "JWT authentication")]
        tasks = [
            _make_task("T01", "Login page", goal="Build login with JWT auth",
                       decision_refs=["BACK-01", "FRONT-01"]),
            _make_task("T02", "User form", goal="Frontend form POSTs to /api/users",
                       decision_refs=["FRONT-01"]),
        ]
        # Use the shared helper that both build_audit_prompt and run_deterministic_audit use
        gaps = _run_and_renumber_deterministic(decisions, tasks)
        # All IDs must be unique
        ids = [g.id for g in gaps]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"
        # IDs must be sequential
        for i, gid in enumerate(ids, 1):
            assert gid == f"GAP-{i:02d}"

    def test_prompt_has_unique_gap_ids(self, tmp_db):
        """The LLM prompt must not contain duplicate GAP IDs."""
        _, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_decisions(conn, [
            _make_decision("BACK-01", "BACK", 1, "JWT authentication"),
            _make_decision("FRONT-01", "FRONT", 1, "React SPA"),
        ])
        db.store_tasks(conn, [
            _make_task("T01", "Login page", goal="Build login with JWT auth",
                       decision_refs=["BACK-01", "FRONT-01"]),
            _make_task("T02", "Dashboard form", goal="Frontend form POSTs to /api/users",
                       decision_refs=["FRONT-01"]),
        ])
        from engine.completeness import build_audit_prompt
        prompt = build_audit_prompt(conn)
        # Count GAP-01 occurrences — should appear at most once
        import re as re_mod
        gap_ids_in_prompt = re_mod.findall(r"GAP-\d{2}", prompt)
        assert len(gap_ids_in_prompt) == len(set(gap_ids_in_prompt)), \
            f"Duplicate GAP IDs in prompt: {gap_ids_in_prompt}"


class TestAuditIdempotency:
    """Verify re-running audit doesn't leave stale gaps."""

    def test_second_audit_clears_old_gaps(self, tmp_db, capsys, monkeypatch):
        """Running audit twice shouldn't accumulate stale gaps."""
        db_path, conn = tmp_db
        conn.close()

        conn = db.get_db(db_path)
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_decisions(conn, [_make_decision("BACK-01", "BACK", 1, "JWT authentication")])
        db.store_tasks(conn, [_make_task("T01", "Login", goal="JWT auth login")])
        conn.close()

        monkeypatch.chdir(db_path.parent)

        # First audit
        orch_main(["audit"])
        captured1 = capsys.readouterr()
        output1 = json.loads(captured1.out)
        count1 = output1["gap_count"]

        # Second audit (same state)
        orch_main(["audit"])
        captured2 = capsys.readouterr()
        output2 = json.loads(captured2.out)
        count2 = output2["gap_count"]

        assert count1 == count2, f"Gap count changed: {count1} → {count2}"

        # Verify DB has exactly count2 gaps (not count1 + count2)
        conn = db.get_db(db_path)
        all_gaps = db.get_audit_gaps(conn)
        assert len(all_gaps) == count2
        conn.close()


class TestFalsePositiveReduction:
    """Verify tightened triggers reduce false positives."""

    def test_generic_project_no_crud_trigger(self):
        """A task with 'create' in goal should NOT trigger CRUD rules."""
        decisions = []
        tasks = [_make_task("T01", "Create project structure", goal="Create the initial folder structure")]
        gaps = check_feature_implications(decisions, tasks)
        crud_gaps = [g for g in gaps if "crud" in g.trigger.lower()]
        assert len(crud_gaps) == 0

    def test_generic_project_no_search_trigger(self):
        """A task with 'filter' or 'query' should NOT trigger search rules."""
        decisions = []
        tasks = [_make_task("T01", "Database query layer", goal="Filter records by date")]
        gaps = check_feature_implications(decisions, tasks)
        search_gaps = [g for g in gaps if "search" in g.trigger.lower()]
        assert len(search_gaps) == 0

    def test_generic_project_no_form_trigger(self):
        """A task with 'form' should NOT trigger form rules."""
        decisions = []
        tasks = [_make_task("T01", "Transform data", goal="Input validation for API")]
        gaps = check_feature_implications(decisions, tasks)
        form_gaps = [g for g in gaps if "forms" in g.trigger.lower()]
        assert len(form_gaps) == 0

    def test_explicit_crud_still_triggers(self):
        """Explicit 'CRUD operations' in goal should still trigger."""
        decisions = []
        tasks = [_make_task("T01", "Resource manager", goal="CRUD operations for items")]
        gaps = check_feature_implications(decisions, tasks)
        crud_gaps = [g for g in gaps if "crud" in g.trigger.lower()]
        assert len(crud_gaps) > 0

    def test_explicit_search_still_triggers(self):
        """Explicit 'search' as a feature should still trigger."""
        decisions = [_make_decision("FRONT-01", "FRONT", 1, "Search page", "Full-text search for products")]
        tasks = [_make_task("T01", "Search feature", goal="Build search page")]
        gaps = check_feature_implications(decisions, tasks)
        search_gaps = [g for g in gaps if "search" in g.trigger.lower()]
        assert len(search_gaps) > 0


class TestAuditAcceptEdgeCases:
    """Edge cases in audit-accept/dismiss commands."""

    def test_accept_already_accepted(self, tmp_db, capsys, monkeypatch):
        """Accepting an already-accepted gap returns error."""
        db_path, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_tasks(conn, [_make_task("T01", "Login", goal="Build login")])
        gap = AuditGap(
            id="GAP-01", category=AuditGapCategory.IMPLIED_FEATURE,
            severity=AuditGapSeverity.HIGH, layer="implication",
            title="Test", description="Test",
        )
        db.store_audit_gap(conn, gap)
        db.update_audit_gap_status(conn, "GAP-01", "accepted", resolved_by="T02")
        conn.close()

        monkeypatch.chdir(db_path.parent)
        orch_main(["audit-accept", "GAP-01"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "already accepted" in output["errors"][0]

    def test_accept_multiple_gaps(self, tmp_db, capsys, monkeypatch):
        """Accepting multiple gaps at once."""
        db_path, conn = tmp_db
        db.store_milestones(conn, [Milestone(id="M1", name="Foundation", order_index=0)])
        db.store_tasks(conn, [_make_task("T01", "Login", goal="Build login")])
        for i in range(3):
            gap = AuditGap(
                id=f"GAP-{i+1:02d}", category=AuditGapCategory.IMPLIED_FEATURE,
                severity=AuditGapSeverity.HIGH, layer="implication",
                title=f"Gap {i+1}", description=f"Desc {i+1}",
            )
            db.store_audit_gap(conn, gap)
        conn.close()

        monkeypatch.chdir(db_path.parent)
        orch_main(["audit-accept", "GAP-01,GAP-02,GAP-03"])
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "ok"
        assert len(output["accepted"]) == 3

    def test_specialist_exit_unknown_prefix(self, tmp_db):
        """Unknown prefix returns clean (no matching contracts)."""
        _, conn = tmp_db
        db.store_decisions(conn, [
            _make_decision("BACK-01", "BACK", 1, "JWT auth", "Login system"),
        ])
        result = run_specialist_exit_check(conn, "UNKNOWN")
        # Should still run without error — just no matching contracts
        assert result["prefix"] == "UNKNOWN"
        # Implication warnings may still fire (they check all decisions)
        # But cross-domain should be empty (no contracts for UNKNOWN source)
        assert len(result["cross_domain_warnings"]) == 0

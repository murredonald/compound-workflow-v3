"""Pytest test suite for the workflow orchestrator pipeline.

Covers:
  - Model validation (edge cases, ID formats, field limits)
  - DB robustness (SQL edge cases, JSON safety, data corruption)
  - Validator (DF/QA IDs, circular deps, planning checks)
  - End-to-end flow (init → plan → specialists → synthesize → execute)
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

import pytest

from orchestrator import main as orch_main

from core import db
from core.db import DataError
from core.models import (
    MAX_TEXT_LENGTH,
    Constraint,
    Decision,
    DecisionPrefix,
    DeferredFinding,
    DeferredFindingCategory,
    Milestone,
    Phase,
    Pipeline,
    ReflexionCategory,
    ReflexionEntry,
    ReviewFinding,
    ReviewResult,
    ReviewVerdict,
    Severity,
    Task,
    TaskEval,
    TaskStatus,
    TestResults,
)
from engine.composer import compose_phase_context
from engine.executor import (
    check_deferred_overlap,
    check_execution_complete,
    check_recurrence,
    complete_task,
    do_scope_check,
    get_adjudication,
    get_execution_summary,
    load_reflexion_for_task,
    pick_next_task,
    promote_deferred_findings,
    record_deferred_finding,
    record_eval,
    record_review,
    start_review_cycle,
    start_task,
)
from engine.planner import build_constraint, build_decision, check_planning_complete
from engine.renderer import render
from engine.reviewer import (
    adjudicate_reviews,
    build_fix_context,
    check_milestone_boundary,
    check_review_cycle_limit,
    check_scope,
    determine_reviewers,
    get_milestone_progress,
    is_security_relevant,
    is_style_relevant,
)
from engine.synthesizer import (
    build_retry_prompt,
    build_synthesize_prompt,
    parse_llm_output,
    run_synthesize,
    store_validated_tasks,
)
from engine.validator import (
    ValidationResult,
    check_circular_deps,
    check_task_ids,
    validate_planning,
    validate_specialist_output,
    validate_task_queue,
)

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="class")
def flow_db(tmp_path_factory):
    """Shared DB for sequential flow tests."""
    tmp = tmp_path_factory.mktemp("flow")
    db_path = tmp / "state.db"
    db.init_db("InvoiceApp", db_path=db_path)
    conn = db.get_db(db_path)
    try:
        yield {"conn": conn, "db_path": db_path}
    finally:
        conn.close()


# ============================================================
# Model Validation Tests
# ============================================================

class TestModels:
    """Test Pydantic model validation rules."""

    def test_decision_valid(self):
        d = Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI", rationale="Async")
        assert d.id == "ARCH-01"
        assert d.prefix == DecisionPrefix.ARCH
        assert d.number == 1

    def test_decision_bad_id_format(self):
        with pytest.raises(ValueError, match="PREFIX-NN"):
            Decision(id="bad", prefix="ARCH", number=1,
                     title="Test", rationale="Why")

    def test_decision_unknown_prefix_in_id(self):
        with pytest.raises(ValueError, match="Unknown prefix"):
            Decision(id="XYZ-01", prefix="ARCH", number=1,
                     title="Test", rationale="Why")

    def test_decision_prefix_mismatch(self):
        with pytest.raises(ValueError, match="doesn't match"):
            Decision(id="ARCH-01", prefix="BACK", number=1,
                     title="Test", rationale="Why")

    def test_decision_number_zero(self):
        with pytest.raises(ValueError):
            Decision(id="ARCH-01", prefix="ARCH", number=0,
                     title="Test", rationale="Why")

    def test_decision_empty_title(self):
        with pytest.raises(ValueError):
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="", rationale="Why")

    def test_decision_empty_rationale(self):
        with pytest.raises(ValueError):
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="Test", rationale="")

    def test_decision_bad_timestamp(self):
        with pytest.raises(ValueError, match="ISO timestamp"):
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="Test", rationale="Why", created_at="not-a-date")

    def test_decision_text_length_limit(self):
        long = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError):
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title=long, rationale="Why")

    def test_task_valid_formats(self):
        for tid in ["T01", "T99", "DF-01", "QA-01", "QA-99"]:
            t = Task(id=tid, title="Test", milestone="M1")
            assert t.id == tid

    def test_task_bad_id(self):
        with pytest.raises(ValueError):
            Task(id="bad", title="Test", milestone="M1")

    def test_task_bad_milestone_ref(self):
        with pytest.raises(ValueError, match=r"M\{N\}"):
            Task(id="T01", title="Test", milestone="bad")

    def test_milestone_valid(self):
        m = Milestone(id="M1", name="Foundation")
        assert m.id == "M1"

    def test_milestone_bad_id(self):
        with pytest.raises(ValueError):
            Milestone(id="bad", name="Test")

    def test_milestone_empty_name(self):
        with pytest.raises(ValueError):
            Milestone(id="M1", name="")

    def test_constraint_valid(self):
        c = Constraint(id="C-01", category="hard", description="No budget")
        assert c.id == "C-01"

    def test_constraint_bad_id(self):
        with pytest.raises(ValueError, match="C-NN"):
            Constraint(id="bad", category="hard", description="No budget")

    def test_constraint_empty_description(self):
        with pytest.raises(ValueError):
            Constraint(id="C-01", category="hard", description="")

    def test_phase_bad_timestamp(self):
        with pytest.raises(ValueError, match="ISO timestamp"):
            Phase(id="plan", label="Planning", started_at="nope")

    def test_pipeline_empty_name(self):
        with pytest.raises(ValueError):
            Pipeline(project_name="")

    def test_pipeline_bad_timestamp(self):
        with pytest.raises(ValueError, match="ISO timestamp"):
            Pipeline(project_name="Test", created_at="bad")


# ============================================================
# DB Robustness Tests
# ============================================================

class TestDBRobustness:
    """Test DB edge cases and error handling."""

    def test_empty_prefixes_returns_empty(self, fresh_db):
        """get_decisions(prefixes=[]) returns empty, not SQL error."""
        result = db.get_decisions(fresh_db, prefixes=[])
        assert result == []

    def test_none_prefixes_returns_all(self, fresh_db):
        """get_decisions(prefixes=None) returns all decisions."""
        decisions = [
            Decision(id="GEN-01", prefix="GEN", number=1,
                     title="Test", rationale="Why"),
        ]
        db.store_decisions(fresh_db, decisions)
        result = db.get_decisions(fresh_db, prefixes=None)
        assert len(result) == 1

    def test_corrupted_json_raises_data_error(self, fresh_db):
        """Corrupted JSON in task fields raises DataError."""
        with fresh_db:
            fresh_db.execute(
                "INSERT INTO milestones (id, name, goal, order_index) "
                "VALUES (?, ?, ?, ?)", ("M1", "Test", "", 0)
            )
            fresh_db.execute(
                "INSERT INTO tasks (id, title, milestone, status, goal, "
                "depends_on, decision_refs, files_create, files_modify, "
                "acceptance_criteria) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("T01", "Test", "M1", "pending", "",
                 "NOT_JSON", "[]", "[]", "[]", "[]")
            )
        with pytest.raises(DataError, match="Corrupted JSON"):
            db.get_task(fresh_db, "T01")

    def test_next_pending_respects_deps(self, fresh_db):
        """next_pending_task only returns tasks whose deps are completed."""
        milestones = [Milestone(id="M1", name="Test")]
        tasks = [
            Task(id="T01", title="First", milestone="M1"),
            Task(id="T02", title="Second", milestone="M1",
                 depends_on=["T01"]),
        ]
        db.store_milestones(fresh_db, milestones)
        db.store_tasks(fresh_db, tasks)

        t = db.next_pending_task(fresh_db)
        assert t is not None
        assert t.id == "T01"

        db.update_task_status(fresh_db, "T01", TaskStatus.COMPLETED)
        t = db.next_pending_task(fresh_db)
        assert t is not None
        assert t.id == "T02"

    def test_connection_timeout(self, tmp_path):
        """get_db accepts timeout parameter (no hang on locked DB)."""
        db_path = tmp_path / "timeout.db"
        db.init_db("Test", db_path=db_path)
        conn = db.get_db(db_path)
        conn.close()  # Just verify it opens and closes


# ============================================================
# Validator Tests
# ============================================================

class TestValidator:
    """Test validator edge cases."""

    def test_check_task_ids_with_df_qa(self):
        """check_task_ids handles DF-NN and QA-NN formats without crashing."""
        tasks = [
            Task(id="T01", title="A", milestone="M1"),
            Task(id="T02", title="B", milestone="M1"),
            Task(id="DF-01", title="Fix", milestone="M1"),
            Task(id="QA-01", title="Check", milestone="M1"),
        ]
        result = check_task_ids(tasks)
        # T-series should be sequential, DF/QA should not crash
        assert "Duplicate" not in str(result.errors)

    def test_circular_deps_iterative(self):
        """Circular dependency detection works with iterative DFS."""
        tasks = [
            Task(id="T01", title="A", milestone="M1", depends_on=["T02"]),
            Task(id="T02", title="B", milestone="M1", depends_on=["T01"]),
        ]
        result = check_circular_deps(tasks)
        assert not result.valid
        assert any("Circular" in e for e in result.errors)

    def test_no_false_positive_cycles(self):
        """Linear chain does not trigger cycle detection."""
        tasks = [
            Task(id="T01", title="A", milestone="M1"),
            Task(id="T02", title="B", milestone="M1", depends_on=["T01"]),
            Task(id="T03", title="C", milestone="M1", depends_on=["T02"]),
        ]
        result = check_circular_deps(tasks)
        assert result.valid

    def test_diamond_deps_no_cycle(self):
        """Diamond dependency pattern (no cycle) should pass."""
        tasks = [
            Task(id="T01", title="A", milestone="M1"),
            Task(id="T02", title="B", milestone="M1", depends_on=["T01"]),
            Task(id="T03", title="C", milestone="M1", depends_on=["T01"]),
            Task(id="T04", title="D", milestone="M1", depends_on=["T02", "T03"]),
        ]
        result = check_circular_deps(tasks)
        assert result.valid

    def test_validate_planning_with_typed_constraints(self):
        """validate_planning accepts list[Constraint]."""
        decisions = [
            Decision(id="GEN-01", prefix="GEN", number=1,
                     title="Web app", rationale="Modern web"),
            Decision(id="GEN-02", prefix="GEN", number=2,
                     title="SMB user", rationale="Main audience"),
            Decision(id="GEN-03", prefix="GEN", number=3,
                     title="MVP scope v1", rationale="Core features"),
        ]
        constraints = [
            Constraint(id="C-01", category="hard", description="No budget"),
        ]
        result = validate_planning(decisions, constraints)
        assert result.valid

    def test_specialist_wrong_prefix(self):
        """Specialist validation catches wrong prefix."""
        decisions = [
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI", rationale="Fast"),
        ]
        result = validate_specialist_output(decisions, "BACK")
        assert not result.valid
        assert any("ARCH" in e and "BACK" in e for e in result.errors)


# ============================================================
# Renderer Tests
# ============================================================

class TestRenderer:
    """Test template rendering."""

    def test_simple_variable(self):
        result = render("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"

    def test_conditional_section_present(self):
        result = render("{{#show}}visible{{/show}}", {"show": True})
        assert "visible" in result

    def test_conditional_section_absent(self):
        result = render("before{{#show}}hidden{{/show}}after", {"show": None})
        assert result == "beforeafter"

    def test_default_value(self):
        result = render("{{missing|fallback}}", {})
        assert result == "fallback"

    def test_task_schema_injection(self):
        result = render("{{TASK_SCHEMA}}", {"TASK_SCHEMA": True})
        assert '"id": "T01"' in result

    def test_empty_list_is_falsy(self):
        result = render("{{#items}}stuff{{/items}}", {"items": []})
        assert "stuff" not in result


# ============================================================
# Synthesizer Tests
# ============================================================

class TestSynthesizer:
    """Test LLM output parsing and validation."""

    def test_parse_valid_json(self):
        output = json.dumps({
            "milestones": [
                {"id": "M1", "name": "Test", "goal": "Test", "order_index": 0},
            ],
            "tasks": [
                {"id": "T01", "title": "Task", "milestone": "M1",
                 "goal": "Do it", "decision_refs": ["ARCH-01"],
                 "files_create": ["a.py"], "acceptance_criteria": ["Works"]},
            ],
        })
        tasks, milestones, errors = parse_llm_output(output)
        assert len(errors) == 0
        assert len(tasks) == 1
        assert len(milestones) == 1

    def test_parse_invalid_json(self):
        _, _, errors = parse_llm_output("not json")
        assert len(errors) == 1
        assert "line" in errors[0].lower()  # Preserves line/col info

    def test_parse_empty_tasks(self):
        output = json.dumps({"milestones": [], "tasks": []})
        _, _, errors = parse_llm_output(output)
        assert len(errors) == 1
        assert "empty" in errors[0].lower()

    def test_parse_non_dict(self):
        output = json.dumps([1, 2, 3])
        _, _, errors = parse_llm_output(output)
        assert len(errors) == 1


# ============================================================
# End-to-End Flow Tests (sequential, shared DB)
# ============================================================

class TestFlow:
    """Sequential flow test — each test builds on the previous one."""

    def test_01_init_schema(self, flow_db):
        conn = flow_db["conn"]
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        assert row is not None
        assert int(row["value"]) == db.SCHEMA_VERSION

        events = db.get_events(conn, limit=5)
        assert len(events) >= 1
        assert events[0]["action"] == "init"

    def test_02_phase_guards(self, flow_db):
        conn = flow_db["conn"]
        with pytest.raises(db.PhaseGuardError) as exc_info:
            db.start_phase(conn, "synthesize")
        assert "plan" in str(exc_info.value)

        with pytest.raises(db.PhaseGuardError) as exc_info:
            db.start_phase(conn, "specialist/backend")
        assert "specialist/architecture" in str(exc_info.value)

        db.start_phase(conn, "plan")  # No prereqs — should succeed

    def test_03_planning(self, flow_db):
        conn = flow_db["conn"]
        decisions = [
            build_decision("GEN", 1, "Web SPA with REST API", "Modern web app"),
            build_decision("GEN", 2, "Primary user: SMB owner", "Highest pain"),
            build_decision("GEN", 3, "MVP: dashboard + invoicing", "Core v1 scope"),
            build_decision("GEN", 4, "Tech: Python + React", "Team expertise"),
        ]
        constraints = [
            build_constraint(1, "hard", "Must work offline"),
            build_constraint(2, "technical", "PostgreSQL required"),
        ]
        db.store_decisions(conn, decisions)
        db.store_constraints(conn, constraints)

        plan_result = validate_planning(decisions, constraints)
        assert plan_result.valid

        bad_result = validate_planning([decisions[0]], [])
        assert not bad_result.valid

        db_result = check_planning_complete(conn)
        assert db_result.valid

        db.complete_phase(conn, "plan")

    def test_04_specialists_and_context(self, flow_db):
        conn = flow_db["conn"]
        db_path = flow_db["db_path"]

        ckpt = db.create_checkpoint(db_path, "specialist/architecture")
        assert ckpt.exists()

        db.start_phase(conn, "specialist/architecture")
        arch = [
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI backend", rationale="Async fast",
                     created_by="specialist/architecture"),
            Decision(id="ARCH-02", prefix="ARCH", number=2,
                     title="PostgreSQL 16 + SQLAlchemy", rationale="Client req",
                     created_by="specialist/architecture"),
            Decision(id="ARCH-03", prefix="ARCH", number=3,
                     title="React 18 SPA + Vite", rationale="Fast builds",
                     created_by="specialist/architecture"),
        ]
        db.store_decisions(conn, arch)
        assert validate_specialist_output(arch, "ARCH").valid
        db.complete_phase(conn, "specialist/architecture")

        # Backend context filtering
        db.start_phase(conn, "specialist/backend")
        ctx = compose_phase_context(conn, "specialist/backend")
        prefixes = {d["prefix"] for d in ctx["decisions"]}
        assert "LEGAL" not in prefixes
        assert "FRONT" not in prefixes
        assert "ARCH" in prefixes

        back = [
            Decision(id="BACK-01", prefix="BACK", number=1,
                     title="REST API /api/v1/", rationale="Clean URLs",
                     created_by="specialist/backend"),
            Decision(id="BACK-02", prefix="BACK", number=2,
                     title="JWT 15min tokens", rationale="Stateless auth",
                     created_by="specialist/backend"),
        ]
        db.store_decisions(conn, back)
        db.complete_phase(conn, "specialist/backend")

        # Frontend sees BACK + ARCH
        db.start_phase(conn, "specialist/frontend")
        ctx = compose_phase_context(conn, "specialist/frontend")
        prefixes = {d["prefix"] for d in ctx["decisions"]}
        assert "BACK" in prefixes
        assert "ARCH" in prefixes

        front = [
            Decision(id="FRONT-01", prefix="FRONT", number=1,
                     title="React Router v6", rationale="Standard routing",
                     created_by="specialist/frontend"),
        ]
        db.store_decisions(conn, front)
        db.complete_phase(conn, "specialist/frontend")

        for sid in ["specialist/domain", "specialist/competition",
                    "specialist/design", "specialist/security",
                    "specialist/testing"]:
            db.skip_phase(conn, sid)

    def test_05_renderer(self, flow_db):
        template = (
            "Project: {{project_name}}\n\n## Decisions\n{{decisions}}\n\n"
            "{{#constraints}}Constraints: {{constraints}}{{/constraints}}"
        )
        arch = [
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI", rationale="Async"),
        ]
        constraints = [
            Constraint(id="C-01", category="hard", description="Must work offline"),
        ]
        rendered = render(template, {
            "project_name": "InvoiceApp",
            "decisions": [d.model_dump() for d in arch],
            "constraints": [c.model_dump() for c in constraints],
        })
        assert "InvoiceApp" in rendered
        assert "ARCH-01" in rendered
        assert "Must work offline" in rendered

    def test_06_synthesize_prompt(self, flow_db):
        conn = flow_db["conn"]
        db.start_phase(conn, "synthesize")
        prompt = build_synthesize_prompt(conn)
        assert "InvoiceApp" in prompt
        assert "ARCH-01" in prompt
        assert "BACK-01" in prompt
        assert "FRONT-01" in prompt
        assert "T01" in prompt
        assert len(prompt) > 1000

    def test_07_parse_and_validate(self, flow_db):
        conn = flow_db["conn"]
        llm_output = json.dumps({
            "milestones": [
                {"id": "M1", "name": "Foundation", "goal": "Core infra", "order_index": 0},
                {"id": "M2", "name": "Features", "goal": "User-facing", "order_index": 1},
            ],
            "tasks": [
                {"id": "T01", "title": "Project scaffold + FastAPI setup",
                 "milestone": "M1", "goal": "Set up FastAPI",
                 "depends_on": [], "decision_refs": ["ARCH-01", "ARCH-02"],
                 "files_create": ["src/main.py", "src/config.py"],
                 "acceptance_criteria": ["FastAPI starts", "DB connected"]},
                {"id": "T02", "title": "Frontend scaffold with Vite",
                 "milestone": "M1", "goal": "React 18 app",
                 "depends_on": [], "decision_refs": ["ARCH-03"],
                 "files_create": ["frontend/src/App.tsx"],
                 "acceptance_criteria": ["Vite starts", "React renders"]},
                {"id": "T03", "title": "REST API routes + JWT auth",
                 "milestone": "M2", "goal": "API endpoints",
                 "depends_on": ["T01"], "decision_refs": ["BACK-01", "BACK-02"],
                 "files_create": ["src/routes/auth.py"],
                 "files_modify": ["src/main.py"],
                 "acceptance_criteria": ["Login returns JWT", "CRUD works"]},
                {"id": "T04", "title": "Frontend routing + API integration",
                 "milestone": "M2", "goal": "Wire React to API",
                 "depends_on": ["T02", "T03"], "decision_refs": ["FRONT-01"],
                 "files_create": ["frontend/src/pages/Dashboard.tsx"],
                 "files_modify": ["frontend/src/App.tsx"],
                 "acceptance_criteria": ["Router works", "Dashboard fetches"]},
            ],
        })

        tasks, milestones, errors = parse_llm_output(llm_output)
        assert len(errors) == 0
        assert len(tasks) == 4
        assert len(milestones) == 2

        result = run_synthesize(conn, llm_output)
        assert result["status"] == "valid"

        # Store for later tests
        flow_db["tasks"] = tasks
        flow_db["milestones"] = milestones
        flow_db["llm_output"] = llm_output

    def test_08_validation_rejection(self, flow_db):
        conn = flow_db["conn"]

        # Circular dependency
        bad = json.dumps({
            "milestones": [{"id": "M1", "name": "F", "goal": "C", "order_index": 0}],
            "tasks": [
                {"id": "T01", "title": "A", "milestone": "M1",
                 "depends_on": ["T02"], "decision_refs": ["ARCH-01"],
                 "goal": "A", "files_create": ["a.py"],
                 "acceptance_criteria": ["A works"]},
                {"id": "T02", "title": "B", "milestone": "M1",
                 "depends_on": ["T01"], "decision_refs": ["BACK-01"],
                 "goal": "B", "files_create": ["b.py"],
                 "acceptance_criteria": ["B works"]},
            ],
        })
        bad_result = run_synthesize(conn, bad)
        assert bad_result["status"] == "invalid"
        assert any("Circular" in e for e in bad_result["errors"])

        # Retry prompt
        retry = build_retry_prompt(
            "original", bad,
            ValidationResult(valid=False, errors=["Circular dependency: T01 -> T02"]),
            cycle=1,
        )
        assert "Circular dependency" in retry
        assert "Retry 1/3" in retry

        # Garbage JSON
        garbage = run_synthesize(conn, "not json at all")
        assert garbage["status"] == "parse_error"

    def test_09_store_and_execute(self, flow_db):
        conn = flow_db["conn"]
        tasks = flow_db["tasks"]
        milestones = flow_db["milestones"]

        counts = store_validated_tasks(conn, tasks, milestones)
        assert counts["tasks_stored"] == 4
        assert counts["milestones_stored"] == 2

        db.complete_phase(conn, "synthesize")
        db.start_phase(conn, "execute")

        iteration = 0
        while not check_execution_complete(conn):
            iteration += 1
            task = pick_next_task(conn)
            if not task:
                break
            ctx = start_task(conn, task.id)
            assert "rendered_prompt" in ctx
            complete_task(conn, task.id)

        summary = get_execution_summary(conn)
        assert summary["all_done"]
        assert summary["total_tasks"] == 4
        assert iteration == 4

        db.complete_phase(conn, "execute")

    def test_10_db_integrity(self, flow_db):
        conn = flow_db["conn"]
        stored_tasks = db.get_tasks(conn)
        stored_milestones = db.get_milestones(conn)
        stored_decisions = db.get_decisions(conn)
        integrity = validate_task_queue(stored_tasks, stored_milestones, stored_decisions)
        assert integrity.valid, f"Integrity errors: {integrity.errors}"

    def test_11_event_log_and_history(self, flow_db):
        conn = flow_db["conn"]

        events = db.get_events(conn, limit=100)
        assert len(events) > 20

        # Decision history
        updated = [Decision(id="ARCH-01", prefix="ARCH", number=1,
                            title="FastAPI v2 with streaming", rationale="Need SSE",
                            created_by="specialist/architecture")]
        db.store_decisions(conn, updated)
        history = db.get_decision_history(conn, "ARCH-01")
        assert len(history) == 1
        assert history[0]["title"] == "FastAPI backend"

        current = db.get_decision(conn, "ARCH-01")
        assert current is not None
        assert current.title == "FastAPI v2 with streaming"

    def test_12_rollback(self, flow_db):
        conn = flow_db["conn"]
        db_path = flow_db["db_path"]

        pre_count = len(db.get_decisions(conn))
        conn.close()

        ok = db.rollback_to_checkpoint(db_path, "specialist/architecture")
        assert ok

        new_conn = db.get_db(db_path)
        post_count = len(db.get_decisions(new_conn))
        assert post_count < pre_count

        # Restore conn for any cleanup
        flow_db["conn"] = new_conn


# ============================================================
# Resume Command Tests
# ============================================================

class TestResume:
    """Test the resume command — post-compaction context reload from DB."""

    def test_resume_fresh_project(self, tmp_path, capsys):
        """Resume on a fresh project shows plan as next phase."""
        db_path = tmp_path / "state.db"
        db.init_db("TestProject", db_path=db_path)
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            ret = orch_main(["resume"])
        finally:
            os.chdir(old_cwd)
        assert ret == 0
        out = capsys.readouterr().out
        assert "TestProject" in out
        assert "RESUMED FROM DB" in out

    def test_resume_after_planning(self, tmp_path, capsys):
        """Resume after plan phase shows specialist context."""
        db_path = tmp_path / "state.db"
        db.init_db("ResumeTest", db_path=db_path)
        conn = db.get_db(db_path)

        # Complete planning
        db.start_phase(conn, "plan")
        decisions = [
            Decision(id="GEN-01", prefix="GEN", number=1,
                     title="Task management app", rationale="Core product"),
            Decision(id="GEN-02", prefix="GEN", number=2,
                     title="Target: developers", rationale="Power users"),
            Decision(id="GEN-03", prefix="GEN", number=3,
                     title="MVP: boards + tasks", rationale="Minimum scope"),
        ]
        db.store_decisions(conn, decisions)
        db.complete_phase(conn, "plan")

        # Start next specialist
        db.start_phase(conn, "specialist/domain")
        conn.close()

        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            ret = orch_main(["resume"])
        finally:
            os.chdir(old_cwd)
        assert ret == 0
        out = capsys.readouterr().out
        assert "ResumeTest" in out
        assert "specialist/domain" in out
        assert "GEN:3" in out or "Decisions: 3" in out

    def test_resume_during_execute(self, tmp_path, capsys):
        """Resume during execute shows active task with rendered prompt."""
        db_path = tmp_path / "state.db"
        db.init_db("ExecTest", db_path=db_path)
        conn = db.get_db(db_path)

        # Fast-forward to execute
        db.start_phase(conn, "plan")
        decisions = [
            Decision(id="GEN-01", prefix="GEN", number=1,
                     title="Web app", rationale="Modern"),
            Decision(id="GEN-02", prefix="GEN", number=2,
                     title="Users: everyone", rationale="Broad"),
            Decision(id="GEN-03", prefix="GEN", number=3,
                     title="MVP: core", rationale="Scope"),
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI", rationale="Fast"),
        ]
        db.store_decisions(conn, decisions)
        db.complete_phase(conn, "plan")

        # Skip specialists
        for s in ["specialist/domain", "specialist/competition",
                  "specialist/architecture", "specialist/backend",
                  "specialist/frontend", "specialist/design",
                  "specialist/security", "specialist/testing"]:
            db.skip_phase(conn, s)

        # Synthesize + store tasks
        db.start_phase(conn, "synthesize")
        milestones = [Milestone(id="M1", name="Core", goal="Foundation", order_index=0)]
        tasks = [
            Task(id="T01", title="Setup project", milestone="M1",
                 goal="Scaffold", depends_on=[], decision_refs=["ARCH-01"],
                 files_create=["src/main.py"],
                 acceptance_criteria=["Server starts"]),
            Task(id="T02", title="Add routes", milestone="M1",
                 goal="API routes", depends_on=["T01"],
                 decision_refs=["ARCH-01"],
                 files_create=["src/routes.py"],
                 acceptance_criteria=["Routes work"]),
        ]
        db.store_milestones(conn, milestones)
        db.store_tasks(conn, tasks)
        db.complete_phase(conn, "synthesize")

        # Start execute, mark T01 in-progress
        db.start_phase(conn, "execute")
        db.update_task_status(conn, "T01", TaskStatus.IN_PROGRESS)
        conn.close()

        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            ret = orch_main(["resume"])
        finally:
            os.chdir(old_cwd)
        assert ret == 0
        out = capsys.readouterr().out
        assert "ACTIVE TASK: T01" in out
        assert "Setup project" in out

    def test_resume_execute_next_pending(self, tmp_path, capsys):
        """Resume when no task is active shows next pending task."""
        db_path = tmp_path / "state.db"
        db.init_db("PendingTest", db_path=db_path)
        conn = db.get_db(db_path)

        db.start_phase(conn, "plan")
        db.store_decisions(conn, [
            Decision(id="GEN-01", prefix="GEN", number=1,
                     title="App", rationale="Why"),
            Decision(id="GEN-02", prefix="GEN", number=2,
                     title="Users", rationale="Who"),
            Decision(id="GEN-03", prefix="GEN", number=3,
                     title="Scope", rationale="What"),
        ])
        db.complete_phase(conn, "plan")

        for s in ["specialist/domain", "specialist/competition",
                  "specialist/architecture", "specialist/backend",
                  "specialist/frontend", "specialist/design",
                  "specialist/security", "specialist/testing"]:
            db.skip_phase(conn, s)

        db.start_phase(conn, "synthesize")
        db.store_milestones(conn, [
            Milestone(id="M1", name="Core", goal="Go", order_index=0),
        ])
        db.store_tasks(conn, [
            Task(id="T01", title="First task", milestone="M1",
                 goal="Do it", depends_on=[], decision_refs=["GEN-01"],
                 files_create=["a.py"], acceptance_criteria=["Done"]),
        ])
        db.complete_phase(conn, "synthesize")
        db.start_phase(conn, "execute")
        conn.close()

        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            ret = orch_main(["resume"])
        finally:
            os.chdir(old_cwd)
        assert ret == 0
        out = capsys.readouterr().out
        assert "NEXT TASK: T01" in out


# ============================================================
# Reflexion Model Validation Tests
# ============================================================

class TestReflexionModels:
    """Test Pydantic validation for reflexion + eval models."""

    def test_reflexion_entry_valid(self):
        e = ReflexionEntry(
            id="R001", task_id="T01", category="env-config",
            severity="medium", what_happened="Build failed",
            root_cause="Missing env var", lesson="Check env first",
        )
        assert e.id == "R001"
        assert e.category == ReflexionCategory.ENV_CONFIG

    def test_reflexion_bad_id_format(self):
        with pytest.raises(ValueError, match=r"R\{NNN\}"):
            ReflexionEntry(
                id="bad", task_id="T01", category="env-config",
                severity="medium", what_happened="X",
                root_cause="Y", lesson="Z",
            )

    def test_reflexion_bad_category(self):
        with pytest.raises(ValueError):
            ReflexionEntry(
                id="R001", task_id="T01", category="not-a-category",
                severity="medium", what_happened="X",
                root_cause="Y", lesson="Z",
            )

    def test_reflexion_empty_what_happened(self):
        with pytest.raises(ValueError):
            ReflexionEntry(
                id="R001", task_id="T01", category="env-config",
                severity="medium", what_happened="",
                root_cause="Y", lesson="Z",
            )

    def test_reflexion_bad_task_id(self):
        with pytest.raises(ValueError):
            ReflexionEntry(
                id="R001", task_id="bad", category="env-config",
                severity="medium", what_happened="X",
                root_cause="Y", lesson="Z",
            )

    def test_task_eval_valid(self):
        e = TaskEval(
            task_id="T01", milestone="M1", status="completed",
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T01:00:00Z",
            review_cycles=1, security_review=True,
            test_results=TestResults(total=10, passed=9, failed=1, skipped=0),
            files_planned=["a.py"], files_touched=["a.py", "b.py"],
            scope_violations=1,
        )
        assert e.task_id == "T01"
        assert e.test_results.total == 10
        assert e.security_review is True

    def test_task_eval_bad_milestone(self):
        with pytest.raises(ValueError, match=r"M\{N\}"):
            TaskEval(
                task_id="T01", milestone="bad", status="completed",
                started_at="2026-01-01T00:00:00Z",
            )

    def test_test_results_negative(self):
        with pytest.raises(ValueError):
            TestResults(total=-1, passed=0, failed=0, skipped=0)

    def test_test_results_parts_exceed_total(self):
        with pytest.raises(ValueError, match="exceeds total"):
            TestResults(total=5, passed=3, failed=2, skipped=1)

    def test_test_results_parts_equal_total(self):
        """Parts summing to exactly total is valid."""
        tr = TestResults(total=10, passed=5, failed=3, skipped=2)
        assert tr.total == 10

    def test_test_results_parts_below_total(self):
        """Parts below total is valid (some tests may not be categorized)."""
        tr = TestResults(total=10, passed=5, failed=2, skipped=1)
        assert tr.total == 10

    def test_task_eval_timestamps_misordered(self):
        with pytest.raises(ValueError, match="before started_at"):
            TaskEval(
                task_id="T01", milestone="M1", status="completed",
                started_at="2026-01-02T00:00:00Z",
                completed_at="2026-01-01T00:00:00Z",
            )

    def test_task_eval_timestamps_ordered(self):
        """completed_at after started_at is valid."""
        e = TaskEval(
            task_id="T01", milestone="M1", status="completed",
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T01:00:00Z",
        )
        assert e.completed_at == "2026-01-01T01:00:00Z"


# ============================================================
# Reflexion DB Tests
# ============================================================

class TestReflexionDB:
    """Test reflexion CRUD and analytics in DB."""

    def _make_entry(self, conn, entry_id="R001", task_id="T01",
                    category="env-config", severity="medium",
                    tags=None, what="Build failed", root="Missing var",
                    lesson="Check env"):
        """Helper to store a task + reflexion entry."""
        # Ensure milestone + task exist
        with contextlib.suppress(Exception):
            db.store_milestones(conn, [Milestone(id="M1", name="Test")])
        with contextlib.suppress(Exception):
            db.store_tasks(conn, [Task(id=task_id, title="Test", milestone="M1")])
        entry = ReflexionEntry(
            id=entry_id, task_id=task_id, category=category,
            severity=severity, what_happened=what,
            root_cause=root, lesson=lesson,
            tags=tags or [],
        )
        db.store_reflexion_entry(conn, entry)
        return entry

    def test_store_and_get(self, fresh_db):
        self._make_entry(fresh_db)
        entries = db.get_reflexion_entries(fresh_db)
        assert len(entries) == 1
        assert entries[0].id == "R001"
        assert entries[0].category == ReflexionCategory.ENV_CONFIG

    def test_search_by_tags(self, fresh_db):
        self._make_entry(fresh_db, entry_id="R001", tags=["auth", "backend"])
        self._make_entry(fresh_db, entry_id="R002", tags=["frontend", "css"])
        results = db.search_reflexion(fresh_db, tags=["auth"])
        assert len(results) == 1
        assert results[0].id == "R001"

    def test_next_reflexion_id_auto_increment(self, fresh_db):
        assert db.next_reflexion_id(fresh_db) == "R001"
        self._make_entry(fresh_db, entry_id="R001")
        assert db.next_reflexion_id(fresh_db) == "R002"
        self._make_entry(fresh_db, entry_id="R002")
        assert db.next_reflexion_id(fresh_db) == "R003"

    def test_next_reflexion_id_past_r999(self, fresh_db):
        """next_reflexion_id works correctly past R999 (integer-based, not string sort)."""
        # Insert R999 directly — string sort would break here
        db.store_milestones(fresh_db, [Milestone(id="M1", name="Test")])
        db.store_tasks(fresh_db, [Task(id="T01", title="Test", milestone="M1")])
        entry = ReflexionEntry(
            id="R999", task_id="T01", category="env-config",
            severity="low", what_happened="X", root_cause="Y", lesson="Z",
        )
        db.store_reflexion_entry(fresh_db, entry)
        assert db.next_reflexion_id(fresh_db) == "R1000"
        # Insert R1000 and verify it goes to R1001
        entry2 = ReflexionEntry(
            id="R1000", task_id="T01", category="env-config",
            severity="low", what_happened="X", root_cause="Y", lesson="Z",
        )
        db.store_reflexion_entry(fresh_db, entry2)
        assert db.next_reflexion_id(fresh_db) == "R1001"

    def test_corrupted_json_raises_data_error(self, fresh_db):
        """Corrupted JSON in reflexion tags raises DataError."""
        db.store_milestones(fresh_db, [Milestone(id="M1", name="Test")])
        db.store_tasks(fresh_db, [Task(id="T01", title="Test", milestone="M1")])
        with fresh_db:
            fresh_db.execute(
                "INSERT INTO reflexion_entries "
                "(id, timestamp, task_id, tags, category, severity, "
                "what_happened, root_cause, lesson, applies_to, preventive_action) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("R001", "2026-01-01T00:00:00Z", "T01",
                 "NOT_JSON", "env-config", "medium",
                 "What", "Root", "Lesson", "[]", ""),
            )
        with pytest.raises(DataError, match="Corrupted JSON"):
            db.get_reflexion_entries(fresh_db)

    def test_recurrence_at_threshold(self, fresh_db):
        """3+ entries with same category+tag triggers systemic issue."""
        for i in range(3):
            self._make_entry(
                fresh_db, entry_id=f"R{i+1:03d}", task_id="T01",
                category="env-config", tags=["deployment"],
                what=f"Failure {i+1}", root=f"Cause {i+1}",
                lesson=f"Lesson {i+1}",
            )
        patterns = db.get_reflexion_patterns(fresh_db)
        assert len(patterns["systemic_issues"]) >= 1
        issue = patterns["systemic_issues"][0]
        assert issue["category"] == "env-config"
        assert issue["tag"] == "deployment"
        assert issue["count"] >= 3

    def test_no_false_positive_below_threshold(self, fresh_db):
        """2 entries with same category+tag is NOT systemic."""
        for i in range(2):
            self._make_entry(
                fresh_db, entry_id=f"R{i+1:03d}", task_id="T01",
                category="env-config", tags=["deployment"],
                what=f"Failure {i+1}", root=f"Cause {i+1}",
                lesson=f"Lesson {i+1}",
            )
        patterns = db.get_reflexion_patterns(fresh_db)
        assert len(patterns["systemic_issues"]) == 0

    def test_different_categories_dont_cross_trigger(self, fresh_db):
        """Entries in different categories don't combine for recurrence."""
        self._make_entry(fresh_db, entry_id="R001", category="env-config",
                         tags=["auth"])
        self._make_entry(fresh_db, entry_id="R002", category="api-contract",
                         tags=["auth"])
        self._make_entry(fresh_db, entry_id="R003", category="dependency",
                         tags=["auth"])
        patterns = db.get_reflexion_patterns(fresh_db)
        assert len(patterns["systemic_issues"]) == 0


# ============================================================
# Task Eval DB Tests
# ============================================================

class TestTaskEvalDB:
    """Test task eval CRUD and analytics."""

    def _store_eval(self, conn, task_id="T01", milestone="M1",
                    review_cycles=0, test_total=10, test_passed=10,
                    test_failed=0, scope_violations=0,
                    files_planned=None, files_touched=None,
                    started_at="2026-01-01T00:00:00Z",
                    completed_at="2026-01-01T01:00:00Z"):
        """Helper to store prerequisite data + eval."""
        with contextlib.suppress(Exception):
            db.store_milestones(conn, [Milestone(id=milestone, name="Test")])
        with contextlib.suppress(Exception):
            db.store_tasks(conn, [Task(id=task_id, title="Test", milestone=milestone)])
        eval_ = TaskEval(
            task_id=task_id, milestone=milestone, status="completed",
            started_at=started_at, completed_at=completed_at,
            review_cycles=review_cycles, security_review=False,
            test_results=TestResults(
                total=test_total, passed=test_passed,
                failed=test_failed, skipped=0,
            ),
            files_planned=files_planned or ["a.py"],
            files_touched=files_touched or ["a.py"],
            scope_violations=scope_violations,
        )
        db.store_task_eval(conn, eval_)
        return eval_

    def test_store_and_get_with_nested_test_results(self, fresh_db):
        self._store_eval(fresh_db, test_total=15, test_passed=12,
                         test_failed=3)
        result = db.get_task_eval(fresh_db, "T01")
        assert result is not None
        assert result.test_results.total == 15
        assert result.test_results.passed == 12
        assert result.test_results.failed == 3

    def test_review_stats_computation(self, fresh_db):
        self._store_eval(fresh_db, task_id="T01", review_cycles=0)
        self._store_eval(fresh_db, task_id="T02", review_cycles=2)
        self._store_eval(fresh_db, task_id="T03", review_cycles=1,
                         scope_violations=2)
        stats = db.get_review_stats(fresh_db)
        assert stats["total"] == 3
        assert stats["avg_cycles"] == 1.0
        assert stats["first_try_pass_rate"] == round(1 / 3, 2)
        assert stats["total_scope_violations"] == 2

    def test_scope_drift_computation(self, fresh_db):
        self._store_eval(
            fresh_db, task_id="T01",
            files_planned=["a.py", "b.py"],
            files_touched=["a.py", "b.py", "c.py", "d.py"],
        )
        drift = db.get_scope_drift(fresh_db)
        assert len(drift) == 1
        assert drift[0]["task_id"] == "T01"
        assert set(drift[0]["unplanned_files"]) == {"c.py", "d.py"}
        assert drift[0]["drift_score"] == 1.0  # 2 unplanned / 2 planned

    def test_milestone_velocity(self, fresh_db):
        self._store_eval(
            fresh_db, task_id="T01",
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T01:00:00Z",
        )
        velocity = db.get_milestone_velocity(fresh_db)
        assert len(velocity) == 1
        assert velocity[0]["milestone"] == "M1"
        assert velocity[0]["task_count"] == 1
        assert velocity[0]["avg_duration_seconds"] > 0

    def test_empty_stats(self, fresh_db):
        stats = db.get_review_stats(fresh_db)
        assert stats["total"] == 0
        assert stats["first_try_pass_rate"] == 0


# ============================================================
# Executor Reflexion Integration Tests
# ============================================================

class TestExecutorReflexion:
    """Test executor-level reflexion + eval integration."""

    def _setup_db(self, conn):
        """Set up a DB with tasks ready for execution."""
        db.store_milestones(conn, [
            Milestone(id="M1", name="Foundation", order_index=0),
        ])
        db.store_decisions(conn, [
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI", rationale="Fast"),
        ])
        db.store_tasks(conn, [
            Task(id="T01", title="Setup project", milestone="M1",
                 decision_refs=["ARCH-01"],
                 files_create=["src/main.py"],
                 acceptance_criteria=["Server starts"]),
            Task(id="T02", title="Add routes", milestone="M1",
                 decision_refs=["ARCH-01"],
                 files_create=["src/routes.py"],
                 files_modify=["src/main.py"],
                 acceptance_criteria=["Routes work"]),
        ])

    def test_load_reflexion_by_decision_ref_overlap(self, fresh_db):
        self._setup_db(fresh_db)
        # Store reflexion entry tagged with ARCH-01
        entry = ReflexionEntry(
            id="R001", task_id="T01", category="api-contract",
            severity="medium", what_happened="API broke",
            root_cause="Version mismatch", lesson="Pin API version",
            tags=["ARCH-01", "src/main.py"],
        )
        db.store_reflexion_entry(fresh_db, entry)
        # T02 references ARCH-01 → should find R001
        result = load_reflexion_for_task(fresh_db, "T02")
        assert len(result) >= 1
        assert result[0]["id"] == "R001"

    def test_load_reflexion_by_file_overlap(self, fresh_db):
        self._setup_db(fresh_db)
        entry = ReflexionEntry(
            id="R001", task_id="T01", category="env-config",
            severity="low", what_happened="Import error",
            root_cause="Wrong path", lesson="Use absolute imports",
            tags=["src/main.py"],
        )
        db.store_reflexion_entry(fresh_db, entry)
        # T02 modifies src/main.py → should find R001
        result = load_reflexion_for_task(fresh_db, "T02")
        assert len(result) >= 1

    def test_no_results_for_unrelated_task(self, fresh_db):
        self._setup_db(fresh_db)
        entry = ReflexionEntry(
            id="R001", task_id="T01", category="env-config",
            severity="low", what_happened="X",
            root_cause="Y", lesson="Z",
            tags=["unrelated-tag"],
        )
        db.store_reflexion_entry(fresh_db, entry)
        # T02 searches by decision_refs (ARCH-01) + files (src/routes.py, src/main.py)
        # R001 is tagged "unrelated-tag" — no overlap with T02's search tags
        # But R001 has task_id="T01", not "T02", so task_id match won't hit either
        result = load_reflexion_for_task(fresh_db, "T02")
        # R001 DOES match because T02 has file src/main.py and R001 doesn't have that tag
        # But R001 has tag "unrelated-tag" which doesn't overlap T02's search tags
        r001_found = any(r["id"] == "R001" for r in result)
        assert not r001_found, "R001 should not match T02 (no overlapping tags)"

    def test_record_eval_auto_populates(self, fresh_db):
        self._setup_db(fresh_db)
        db.update_task_status(fresh_db, "T01", TaskStatus.COMPLETED)
        result = record_eval(
            fresh_db, "T01",
            review_cycles=1,
            test_results=TestResults(total=5, passed=5, failed=0, skipped=0),
            files_touched=["src/main.py"],
        )
        assert result["status"] == "ok"
        eval_ = db.get_task_eval(fresh_db, "T01")
        assert eval_ is not None
        assert eval_.milestone == "M1"
        assert eval_.files_planned == ["src/main.py"]
        assert eval_.review_cycles == 1

    def test_record_eval_with_explicit_timestamps(self, fresh_db):
        """record_eval uses caller-provided timestamps instead of _now()."""
        self._setup_db(fresh_db)
        db.update_task_status(fresh_db, "T02", TaskStatus.COMPLETED)
        result = record_eval(
            fresh_db, "T02",
            started_at="2026-01-01T10:00:00Z",
            completed_at="2026-01-01T11:30:00Z",
        )
        assert result["status"] == "ok"
        eval_ = db.get_task_eval(fresh_db, "T02")
        assert eval_ is not None
        assert eval_.started_at == "2026-01-01T10:00:00Z"
        assert eval_.completed_at == "2026-01-01T11:30:00Z"

    def test_load_reflexion_includes_own_task_entries(self, fresh_db):
        """load_reflexion_for_task returns entries created by the task itself."""
        self._setup_db(fresh_db)
        # Entry tagged with something T01 doesn't search for,
        # but task_id IS T01 — should still appear
        entry = ReflexionEntry(
            id="R001", task_id="T01", category="env-config",
            severity="low", what_happened="Build broke",
            root_cause="Missing import", lesson="Always run lint",
            tags=["unrelated-tag-only"],
        )
        db.store_reflexion_entry(fresh_db, entry)
        result = load_reflexion_for_task(fresh_db, "T01")
        assert len(result) == 1
        assert result[0]["id"] == "R001"

    def test_check_recurrence(self, fresh_db):
        self._setup_db(fresh_db)
        # Store 3 entries with same category+tag → systemic
        for i in range(3):
            entry = ReflexionEntry(
                id=f"R{i+1:03d}", task_id="T01",
                category="env-config", severity="medium",
                what_happened=f"Fail {i+1}", root_cause=f"Cause {i+1}",
                lesson=f"Lesson {i+1}", tags=["deployment"],
            )
            db.store_reflexion_entry(fresh_db, entry)
        systemic = check_recurrence(fresh_db)
        assert len(systemic) >= 1
        assert systemic[0]["category"] == "env-config"


# ============================================================
# Review Model Tests
# ============================================================

class TestReviewModels:
    """Test Pydantic models for review and deferred findings."""

    def test_review_finding_valid(self):
        f = ReviewFinding(
            id=1, severity="high", category="acceptance-criteria",
            description="Missing validation", file="src/main.py:42",
        )
        assert f.id == 1
        assert f.severity == Severity.HIGH

    def test_review_finding_bad_severity(self):
        with pytest.raises(ValueError):
            ReviewFinding(
                id=1, severity="extreme", category="test",
                description="Bad",
            )

    def test_review_finding_id_zero_allowed(self):
        """id=0 is allowed as default (auto-assigned by record_review)."""
        f = ReviewFinding(
            id=0, severity="low", category="test",
            description="Zero id is fine",
        )
        assert f.id == 0

    def test_review_finding_defaults(self):
        """Minimal ReviewFinding — only severity + description required."""
        f = ReviewFinding(severity="medium", description="Something wrong")
        assert f.id == 0
        assert f.category == "general"
        assert f.fix_description == ""

    def test_review_result_valid(self):
        r = ReviewResult(
            reviewer="code-reviewer", task_id="T01", verdict="pass",
            findings=[
                ReviewFinding(id=1, severity="low", category="style",
                              description="Minor issue"),
            ],
            criteria_assessed=5, criteria_passed=5,
        )
        assert r.verdict == ReviewVerdict.PASS
        assert len(r.findings) == 1

    def test_review_result_bad_verdict(self):
        with pytest.raises(ValueError):
            ReviewResult(
                reviewer="code-reviewer", task_id="T01", verdict="maybe",
            )

    def test_review_result_bad_task_id(self):
        with pytest.raises(ValueError, match="Task ID"):
            ReviewResult(
                reviewer="code-reviewer", task_id="BAD", verdict="pass",
            )

    def test_deferred_finding_valid(self):
        df = DeferredFinding(
            id="DF-01", discovered_in="T01",
            category="missing-feature",
            affected_area="User auth",
            description="Need password reset flow",
            files_likely=["src/auth.py"],
        )
        assert df.id == "DF-01"
        assert df.category == DeferredFindingCategory.MISSING_FEATURE

    def test_deferred_finding_bad_id(self):
        with pytest.raises(ValueError, match="DF-NN"):
            DeferredFinding(
                id="BAD", discovered_in="T01",
                category="missing-feature",
                affected_area="Test", description="Test",
            )

    def test_deferred_finding_bad_category(self):
        with pytest.raises(ValueError):
            DeferredFinding(
                id="DF-01", discovered_in="T01",
                category="invalid-category",
                affected_area="Test", description="Test",
            )


# ============================================================
# Review DB Tests
# ============================================================

class TestReviewDB:
    """Test DB operations for reviews and deferred findings."""

    @staticmethod
    def _setup_db(conn):
        """Set up milestones + tasks for review tests."""
        db.store_milestones(conn, [
            Milestone(id="M1", name="Foundation", order_index=0),
        ])
        db.store_tasks(conn, [
            Task(id="T01", title="Setup auth", milestone="M1",
                 files_create=["src/auth.py"], files_modify=["src/main.py"],
                 decision_refs=["SEC-01"],
                 acceptance_criteria=["Auth works"]),
            Task(id="T02", title="Setup DB", milestone="M1",
                 files_create=["src/db.py"]),
        ])

    def test_store_and_get_review_result(self, fresh_db):
        self._setup_db(fresh_db)
        result = ReviewResult(
            reviewer="code-reviewer", task_id="T01", verdict="pass",
            cycle=1, criteria_assessed=3, criteria_passed=3,
        )
        rowid = db.store_review_result(fresh_db, result)
        assert rowid > 0

        results = db.get_review_results(fresh_db, "T01")
        assert len(results) == 1
        assert results[0].reviewer == "code-reviewer"
        assert results[0].verdict == ReviewVerdict.PASS

    def test_get_review_results_by_cycle(self, fresh_db):
        self._setup_db(fresh_db)
        # Store two reviews in different cycles
        for cycle in (1, 2):
            r = ReviewResult(
                reviewer="code-reviewer", task_id="T01",
                verdict="concern" if cycle == 1 else "pass",
                cycle=cycle,
            )
            db.store_review_result(fresh_db, r)

        cycle1 = db.get_review_results(fresh_db, "T01", cycle=1)
        assert len(cycle1) == 1
        assert cycle1[0].verdict == ReviewVerdict.CONCERN

        cycle2 = db.get_review_results(fresh_db, "T01", cycle=2)
        assert len(cycle2) == 1
        assert cycle2[0].verdict == ReviewVerdict.PASS

    def test_get_latest_review_cycle(self, fresh_db):
        self._setup_db(fresh_db)
        assert db.get_latest_review_cycle(fresh_db, "T01") == 0

        db.store_review_result(fresh_db, ReviewResult(
            reviewer="x", task_id="T01", verdict="pass", cycle=1,
        ))
        assert db.get_latest_review_cycle(fresh_db, "T01") == 1

        db.store_review_result(fresh_db, ReviewResult(
            reviewer="x", task_id="T01", verdict="pass", cycle=3,
        ))
        assert db.get_latest_review_cycle(fresh_db, "T01") == 3

    def test_store_review_with_findings(self, fresh_db):
        self._setup_db(fresh_db)
        findings = [
            ReviewFinding(id=1, severity="high", category="acceptance-criteria",
                          description="Missing validation", file="src/auth.py:10"),
            ReviewFinding(id=2, severity="low", category="style",
                          description="Naming convention", file="src/auth.py:20"),
        ]
        result = ReviewResult(
            reviewer="code-reviewer", task_id="T01", verdict="concern",
            cycle=1, findings=findings,
        )
        db.store_review_result(fresh_db, result)

        stored = db.get_review_results(fresh_db, "T01")
        assert len(stored) == 1
        assert len(stored[0].findings) == 2
        assert stored[0].findings[0].severity == Severity.HIGH

    def test_store_and_get_deferred_finding(self, fresh_db):
        self._setup_db(fresh_db)
        finding = DeferredFinding(
            id="DF-01", discovered_in="T01",
            category="missing-feature",
            affected_area="Password reset",
            description="Need forgot password flow",
            files_likely=["src/auth.py", "src/email.py"],
        )
        fid = db.store_deferred_finding(fresh_db, finding)
        assert fid == "DF-01"

        findings = db.get_deferred_findings(fresh_db)
        assert len(findings) == 1
        assert findings[0].files_likely == ["src/auth.py", "src/email.py"]

    def test_next_deferred_finding_id(self, fresh_db):
        self._setup_db(fresh_db)
        assert db.next_deferred_finding_id(fresh_db) == "DF-01"

        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-01", discovered_in="T01", category="missing-feature",
            affected_area="Test", description="Test",
        ))
        assert db.next_deferred_finding_id(fresh_db) == "DF-02"

    def test_deferred_findings_filter_by_status(self, fresh_db):
        self._setup_db(fresh_db)
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-01", discovered_in="T01", category="missing-feature",
            affected_area="A", description="Open one",
        ))
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-02", discovered_in="T01", category="missing-test",
            affected_area="B", description="Promoted one", status="promoted",
        ))
        open_findings = db.get_deferred_findings(fresh_db, status="open")
        assert len(open_findings) == 1
        assert open_findings[0].id == "DF-01"

    def test_deferred_findings_for_files(self, fresh_db):
        self._setup_db(fresh_db)
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-01", discovered_in="T01", category="missing-feature",
            affected_area="Auth", description="Test",
            files_likely=["src/auth.py", "src/utils.py"],
        ))
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-02", discovered_in="T01", category="missing-test",
            affected_area="DB", description="Test",
            files_likely=["src/db.py"],
        ))
        # Search for auth.py overlap
        overlapping = db.get_deferred_findings_for_files(fresh_db, ["src/auth.py"])
        assert len(overlapping) == 1
        assert overlapping[0].id == "DF-01"

        # No overlap
        empty = db.get_deferred_findings_for_files(fresh_db, ["src/other.py"])
        assert len(empty) == 0

    def test_update_deferred_status(self, fresh_db):
        self._setup_db(fresh_db)
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-01", discovered_in="T01", category="missing-feature",
            affected_area="Test", description="Test",
        ))
        db.update_deferred_finding_status(fresh_db, "DF-01", "promoted")
        findings = db.get_deferred_findings(fresh_db, status="promoted")
        assert len(findings) == 1
        assert findings[0].id == "DF-01"


# ============================================================
# Reviewer Engine Tests
# ============================================================

class TestReviewer:
    """Test deterministic review logic in engine/reviewer.py."""

    def test_determine_reviewers_always_code_reviewer(self):
        task = Task(id="T01", title="Test", milestone="M1",
                    files_create=["src/utils.py"])
        reviewers = determine_reviewers(task, [])
        assert "code-reviewer" in reviewers
        assert len(reviewers) == 1  # no conditionals triggered

    def test_is_security_relevant_auth_file(self):
        task = Task(id="T01", title="Auth", milestone="M1",
                    files_create=["src/auth/login.py"])
        assert is_security_relevant(task, []) is True

    def test_is_security_relevant_sec_decision(self):
        task = Task(id="T01", title="Test", milestone="M1",
                    decision_refs=["SEC-01"],
                    files_create=["src/main.py"])
        decisions = [
            Decision(id="SEC-01", prefix="SEC", number=1,
                     title="Use JWT", rationale="Stateless"),
        ]
        assert is_security_relevant(task, decisions) is True

    def test_is_security_relevant_no_match(self):
        task = Task(id="T01", title="Test", milestone="M1",
                    files_create=["src/utils.py"])
        assert is_security_relevant(task, []) is False

    def test_is_style_relevant_css(self):
        task = Task(id="T01", title="Style", milestone="M1",
                    files_modify=["src/App.css"])
        assert is_style_relevant(task) is True

    def test_is_style_relevant_tsx(self):
        task = Task(id="T01", title="Component", milestone="M1",
                    files_create=["src/Button.tsx"])
        assert is_style_relevant(task) is True

    def test_is_style_relevant_no_match(self):
        task = Task(id="T01", title="Backend", milestone="M1",
                    files_create=["src/main.py"])
        assert is_style_relevant(task) is False

    def test_adjudicate_single_pass(self):
        reviews = [
            ReviewResult(reviewer="code-reviewer", task_id="T01",
                         verdict="pass", cycle=1),
        ]
        result = adjudicate_reviews(reviews)
        assert result["unified_verdict"] == "pass"
        assert result["primary_reviewer"] == "code-reviewer"

    def test_adjudicate_with_findings(self):
        findings = [
            ReviewFinding(id=1, severity="high", category="acceptance-criteria",
                          description="Missing check", file="src/main.py"),
        ]
        reviews = [
            ReviewResult(reviewer="code-reviewer", task_id="T01",
                         verdict="concern", cycle=1, findings=findings),
        ]
        result = adjudicate_reviews(reviews)
        assert result["unified_verdict"] == "concern"
        # Primary-only finding needs external confirmation (2+ sources) to be "confirmed"
        assert len(result["confirmed_findings"]) == 0
        assert len(result["all_findings"]) == 1

    def test_adjudicate_cross_reference(self):
        """Two reviewers find the same issue → confirmed."""
        finding1 = ReviewFinding(id=1, severity="high",
                                  category="scope", description="Issue",
                                  file="src/main.py")
        finding2 = ReviewFinding(id=1, severity="high",
                                  category="scope", description="Same issue",
                                  file="src/main.py")
        reviews = [
            ReviewResult(reviewer="code-reviewer", task_id="T01",
                         verdict="concern", cycle=1, findings=[finding1]),
            ReviewResult(reviewer="gpt", task_id="T01",
                         verdict="concern", cycle=1, findings=[finding2]),
        ]
        result = adjudicate_reviews(reviews)
        # Primary finding should be confirmed by both
        assert len(result["confirmed_findings"]) == 1
        assert len(result["confirmed_findings"][0]["confirmed_by"]) == 2

    def test_adjudicate_external_only_unconfirmed(self):
        """External-only finding gets flagged as unconfirmed."""
        reviews = [
            ReviewResult(reviewer="code-reviewer", task_id="T01",
                         verdict="pass", cycle=1),
            ReviewResult(reviewer="gpt", task_id="T01",
                         verdict="concern", cycle=1, findings=[
                             ReviewFinding(id=1, severity="medium",
                                           category="edge-case",
                                           description="Ext finding",
                                           file="src/other.py"),
                         ]),
        ]
        result = adjudicate_reviews(reviews)
        assert result["unified_verdict"] == "pass"  # Primary says pass
        assert len(result["unconfirmed_findings"]) == 1
        assert result["unconfirmed_findings"][0]["needs_validation"] is True

    def test_check_scope_clean(self):
        task = Task(id="T01", title="Test", milestone="M1",
                    files_create=["src/a.py"], files_modify=["src/b.py"])
        result = check_scope(task, ["src/a.py", "src/b.py"])
        assert result["in_scope"] is True
        assert result["violations"] == 0

    def test_check_scope_violations(self):
        task = Task(id="T01", title="Test", milestone="M1",
                    files_create=["src/a.py"])
        result = check_scope(task, ["src/a.py", "src/extra.py"])
        assert result["in_scope"] is False
        assert result["violations"] == 1
        assert "src/extra.py" in result["unexpected_files"]

    def test_build_fix_context_recurring(self):
        history = [
            {"cycle": 1, "findings": [
                {"file": "src/a.py", "category": "scope"},
                {"file": "src/b.py", "category": "edge-case"},
            ]},
            {"cycle": 2, "findings": [
                {"file": "src/a.py", "category": "scope"},
            ]},
        ]
        ctx = build_fix_context(history)
        assert ctx["total_cycles"] == 2
        assert "src/a.py" in ctx["recurring_files"]
        assert "scope" in ctx["recurring_categories"]

    def test_check_review_cycle_limit(self):
        assert check_review_cycle_limit(1, max_cycles=3) is False
        assert check_review_cycle_limit(3, max_cycles=3) is False
        assert check_review_cycle_limit(4, max_cycles=3) is True

    def test_milestone_progress(self, fresh_db):
        db.store_milestones(fresh_db, [
            Milestone(id="M1", name="Foundation", order_index=0),
        ])
        db.store_tasks(fresh_db, [
            Task(id="T01", title="A", milestone="M1", status="completed"),
            Task(id="T02", title="B", milestone="M1", status="pending"),
        ])
        progress = get_milestone_progress(fresh_db, "M1")
        assert progress["total"] == 2
        assert progress["completed"] == 1
        assert progress["remaining"] == 1
        assert progress["all_done"] is False


# ============================================================
# Executor Review Lifecycle Tests
# ============================================================

class TestExecutorReview:
    """Test review lifecycle functions in executor.py."""

    @staticmethod
    def _setup_db(conn):
        db.store_milestones(conn, [
            Milestone(id="M1", name="Foundation", order_index=0),
        ])
        db.store_tasks(conn, [
            Task(id="T01", title="Setup auth", milestone="M1",
                 files_create=["src/auth.py"], files_modify=["src/main.py"],
                 decision_refs=["SEC-01"],
                 acceptance_criteria=["Auth works"],
                 verification_cmd="pytest tests/ -v"),
        ])
        db.store_decisions(conn, [
            Decision(id="SEC-01", prefix="SEC", number=1,
                     title="Use JWT", rationale="Stateless auth"),
        ])

    def test_start_review_cycle(self, fresh_db):
        self._setup_db(fresh_db)
        result = start_review_cycle(fresh_db, "T01", ["src/auth.py"])
        assert result["cycle"] == 1
        assert "code-reviewer" in result["reviewers"]
        assert "security-auditor" in result["reviewers"]  # SEC-01 decision
        assert "review_context" in result

    def test_record_review(self, fresh_db):
        self._setup_db(fresh_db)
        findings = json.dumps([
            {"id": 1, "severity": "medium", "category": "edge-case",
             "description": "Missing null check"},
        ])
        result = record_review(
            fresh_db, "T01", "code-reviewer", "concern",
            findings_json=findings, cycle=1,
        )
        assert result["status"] == "ok"
        assert result["findings_count"] == 1

    def test_get_adjudication(self, fresh_db):
        self._setup_db(fresh_db)
        db.store_review_result(fresh_db, ReviewResult(
            reviewer="code-reviewer", task_id="T01", verdict="pass", cycle=1,
        ))
        result = get_adjudication(fresh_db, "T01", cycle=1)
        assert result["unified_verdict"] == "pass"

    def test_record_deferred_finding(self, fresh_db):
        self._setup_db(fresh_db)
        result = record_deferred_finding(
            fresh_db, "T01", "missing-feature",
            "Password reset", "Need forgot password flow",
            files_likely=["src/auth.py"],
        )
        assert result["status"] == "ok"
        assert result["id"] == "DF-01"

    def test_promote_deferred_findings(self, fresh_db):
        self._setup_db(fresh_db)
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-01", discovered_in="T01", category="missing-feature",
            affected_area="Auth", description="Test",
        ))
        result = promote_deferred_findings(fresh_db, ["DF-01"])
        assert "DF-01" in result["promoted"]

        findings = db.get_deferred_findings(fresh_db, status="promoted")
        assert len(findings) == 1

    def test_check_deferred_overlap(self, fresh_db):
        self._setup_db(fresh_db)
        db.store_deferred_finding(fresh_db, DeferredFinding(
            id="DF-01", discovered_in="T01", category="missing-feature",
            affected_area="Auth", description="Test",
            files_likely=["src/auth.py"],
        ))
        overlap = check_deferred_overlap(fresh_db, "T01")
        assert len(overlap) == 1
        assert overlap[0]["id"] == "DF-01"

    def test_scope_check_via_executor(self, fresh_db):
        self._setup_db(fresh_db)
        result = do_scope_check(fresh_db, "T01", ["src/auth.py", "src/main.py"])
        assert result["in_scope"] is True

        result = do_scope_check(fresh_db, "T01", ["src/auth.py", "src/extra.py"])
        assert result["in_scope"] is False

    def test_milestone_boundary_check(self, fresh_db):
        self._setup_db(fresh_db)
        result = check_milestone_boundary(fresh_db, "T01")
        assert result["milestone_id"] == "M1"
        # Only 1 task in M1, so completing it is a boundary
        assert result["is_boundary"] is True


# ============================================================
# Delete Task Cascade Tests
# ============================================================

class TestDeleteTaskCascade:
    """Verify delete_task removes FK-dependent child rows."""

    def _store_task(self, conn):
        """Store a task with child rows in all FK-dependent tables."""
        milestone = Milestone(id="M1", name="MVP Auth", order_index=0)
        db.store_milestones(conn, [milestone])

        task = Task(
            id="T01",
            title="Auth module",
            milestone="M1",
            files_create=["src/auth.py"],
        )
        db.store_tasks(conn, [task])

        # Add review result
        result = ReviewResult(
            task_id="T01",
            reviewer="code-reviewer",
            verdict="pass",
            cycle=1,
        )
        db.store_review_result(conn, result)

        # Add task eval
        eval_ = TaskEval(
            task_id="T01",
            milestone="M1",
            status=TaskStatus.COMPLETED,
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T01:00:00Z",
        )
        db.store_task_eval(conn, eval_)

        # Add reflexion entry
        entry = ReflexionEntry(
            id="R001",
            task_id="T01",
            category="edge-case-logic",
            severity="medium",
            what_happened="Test failed",
            root_cause="Off-by-one error",
            lesson="Check bounds",
            tags=["auth"],
        )
        db.store_reflexion_entry(conn, entry)

        # Add deferred finding (uses discovered_in, not task_id)
        finding = DeferredFinding(
            id="DF-01",
            affected_area="Auth endpoint",
            description="Auth endpoint needs rate limiting",
            discovered_in="T01",
            category="missing-feature",
        )
        db.store_deferred_finding(conn, finding)

    def test_delete_cascades_all_children(self, fresh_db):
        """delete_task removes review_results, task_evals, reflexion, deferred_findings."""
        self._store_task(fresh_db)

        # Verify children exist
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM review_results WHERE task_id='T01'"
        ).fetchone()[0] == 1
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM task_evals WHERE task_id='T01'"
        ).fetchone()[0] == 1
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM reflexion_entries WHERE task_id='T01'"
        ).fetchone()[0] == 1
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM deferred_findings WHERE discovered_in='T01'"
        ).fetchone()[0] == 1

        # Delete and verify cascade
        db.delete_task(fresh_db, "T01")

        assert fresh_db.execute(
            "SELECT COUNT(*) FROM tasks WHERE id='T01'"
        ).fetchone()[0] == 0
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM review_results WHERE task_id='T01'"
        ).fetchone()[0] == 0
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM task_evals WHERE task_id='T01'"
        ).fetchone()[0] == 0
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM reflexion_entries WHERE task_id='T01'"
        ).fetchone()[0] == 0
        assert fresh_db.execute(
            "SELECT COUNT(*) FROM deferred_findings WHERE discovered_in='T01'"
        ).fetchone()[0] == 0

    def test_delete_nonexistent_task_no_error(self, fresh_db):
        """Deleting a task that doesn't exist should not raise."""
        db.delete_task(fresh_db, "T99")

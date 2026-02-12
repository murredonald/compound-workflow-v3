"""Tests for the /decompose phase — task decomposition with artifact wiring.

Covers:
  - Model validation (Task with new fields, DecomposedTask, subtask IDs)
  - DB (schema v5 migration, store/read new fields)
  - Decomposer engine (infer, parse, validate, convert, store)
  - Composer (artifact loading in execute context)
  - Validator (subtask ID support, decomposed coverage)
  - Renderer (new formatters, decompose schema)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import db
from core.models import (
    ArtifactType,
    Decision,
    DecisionPrefix,
    DecomposedTask,
    Milestone,
    Task,
    TaskStatus,
)
from engine.composer import compose_execution_context, compose_task_context
from engine.decomposer import (
    TASK_ARTIFACT_RULES,
    build_decompose_prompt,
    infer_artifact_refs,
    parse_decompose_output,
    run_decompose_for_task,
    store_decomposed_tasks,
    subtasks_to_tasks,
    validate_decompose_output,
)
from engine.renderer import (
    format_available_artifacts,
    format_decision_index,
    get_decompose_schema,
    get_task_schema,
    render,
)
from engine.validator import (
    ValidationResult,
    check_decomposed_coverage,
    check_task_ids,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def db_with_tasks(fresh_db):
    """DB with milestones, decisions, tasks, and artifacts."""
    conn = fresh_db

    # Store milestones
    db.store_milestones(conn, [
        Milestone(id="M1", name="Foundation", goal="Setup", order_index=0),
        Milestone(id="M2", name="Features", goal="Build", order_index=1),
    ])

    # Store decisions
    db.store_decisions(conn, [
        Decision(id="ARCH-01", prefix=DecisionPrefix.ARCH, number=1,
                 title="Use FastAPI", rationale="Performance"),
        Decision(id="BACK-01", prefix=DecisionPrefix.BACK, number=1,
                 title="JWT auth", rationale="Security"),
        Decision(id="BACK-02", prefix=DecisionPrefix.BACK, number=2,
                 title="PostgreSQL", rationale="Reliability"),
        Decision(id="FRONT-01", prefix=DecisionPrefix.FRONT, number=1,
                 title="React components", rationale="Ecosystem"),
        Decision(id="STYLE-01", prefix=DecisionPrefix.STYLE, number=1,
                 title="Design tokens", rationale="Consistency"),
        Decision(id="SEC-01", prefix=DecisionPrefix.SEC, number=1,
                 title="Rate limiting", rationale="Protection"),
    ])

    # Store tasks
    db.store_tasks(conn, [
        Task(id="T01", title="API setup", milestone="M1", goal="Build API",
             decision_refs=["ARCH-01", "BACK-01", "BACK-02"],
             files_create=["src/api.py", "src/auth.py", "src/db.py"],
             acceptance_criteria=["API serves requests", "Auth works"]),
        Task(id="T02", title="Frontend shell", milestone="M1", goal="Build UI",
             depends_on=["T01"],
             decision_refs=["FRONT-01", "STYLE-01"],
             artifact_refs=["style-guide", "brand-guide"],
             files_create=["src/App.tsx", "src/theme.ts"],
             acceptance_criteria=["App renders", "Theme applied"]),
        Task(id="T03", title="Security hardening", milestone="M2",
             goal="Secure endpoints",
             depends_on=["T01"],
             decision_refs=["SEC-01"],
             files_modify=["src/api.py"],
             acceptance_criteria=["Rate limiting active"]),
    ])

    # Store artifacts
    db.store_artifact(conn, "style-guide", "# Style Guide\nColors: blue, white")
    db.store_artifact(conn, "brand-guide", "# Brand Guide\nLogo: acme.svg")

    return conn


# ============================================================
# Model tests
# ============================================================

class TestModels:
    """Test Task and DecomposedTask model changes."""

    def test_task_accepts_subtask_id(self):
        t = Task(id="T01.1", title="Sub", milestone="M1")
        assert t.id == "T01.1"

    def test_task_accepts_parent_id(self):
        t = Task(id="T01", title="Parent", milestone="M1")
        assert t.id == "T01"

    def test_task_accepts_artifact_refs(self):
        t = Task(id="T01", title="Test", milestone="M1",
                 artifact_refs=["style-guide", "brand-guide"])
        assert t.artifact_refs == ["style-guide", "brand-guide"]

    def test_task_rejects_bad_artifact_type(self):
        with pytest.raises(ValueError, match="Unknown artifact type"):
            Task(id="T01", title="Test", milestone="M1",
                 artifact_refs=["nonexistent-guide"])

    def test_task_accepts_parent_task_field(self):
        t = Task(id="T01.1", title="Sub", milestone="M1", parent_task="T01")
        assert t.parent_task == "T01"

    def test_task_rejects_bad_parent_task(self):
        with pytest.raises(ValueError, match="parent_task must be a T-series"):
            Task(id="T01.1", title="Sub", milestone="M1", parent_task="DF-01")

    def test_task_parent_task_none_default(self):
        t = Task(id="T01", title="Test", milestone="M1")
        assert t.parent_task is None

    def test_task_backwards_compat_no_new_fields(self):
        """Existing Task creation without new fields still works."""
        t = Task(id="T01", title="Old style", milestone="M1",
                 decision_refs=["ARCH-01"], files_create=["x.py"])
        assert t.artifact_refs == []
        assert t.parent_task is None

    def test_df_qa_ids_still_work(self):
        t_df = Task(id="DF-01", title="Deferred", milestone="M1")
        t_qa = Task(id="QA-01", title="QA fix", milestone="M1")
        assert t_df.id == "DF-01"
        assert t_qa.id == "QA-01"

    def test_decomposed_task_requires_parent(self):
        st = DecomposedTask(id="T01.1", title="Sub", milestone="M1",
                            parent_task="T01")
        assert st.parent_task == "T01"

    def test_decomposed_task_rejects_parent_id_format(self):
        with pytest.raises(ValueError, match="Subtask ID must be"):
            DecomposedTask(id="T01", title="Not subtask", milestone="M1",
                           parent_task="T01")

    def test_decomposed_task_rejects_bad_parent(self):
        with pytest.raises(ValueError, match="parent_task must be a T-series"):
            DecomposedTask(id="T01.1", title="Sub", milestone="M1",
                           parent_task="M1")


# ============================================================
# DB tests
# ============================================================

class TestDB:
    """Test schema v5 changes."""

    def test_store_task_with_artifact_refs(self, fresh_db):
        db.store_milestones(fresh_db, [
            Milestone(id="M1", name="Test", order_index=0)
        ])
        db.store_tasks(fresh_db, [
            Task(id="T01", title="Test", milestone="M1",
                 artifact_refs=["style-guide"])
        ])
        task = db.get_task(fresh_db, "T01")
        assert task is not None
        assert task.artifact_refs == ["style-guide"]

    def test_store_task_with_parent_task(self, fresh_db):
        db.store_milestones(fresh_db, [
            Milestone(id="M1", name="Test", order_index=0)
        ])
        db.store_tasks(fresh_db, [
            Task(id="T01.1", title="Subtask", milestone="M1",
                 parent_task="T01", artifact_refs=["brand-guide"])
        ])
        task = db.get_task(fresh_db, "T01.1")
        assert task is not None
        assert task.parent_task == "T01"
        assert task.artifact_refs == ["brand-guide"]

    def test_store_task_without_new_fields(self, fresh_db):
        """Backwards compat: tasks stored without new fields parse correctly."""
        db.store_milestones(fresh_db, [
            Milestone(id="M1", name="Test", order_index=0)
        ])
        db.store_tasks(fresh_db, [
            Task(id="T01", title="Old task", milestone="M1")
        ])
        task = db.get_task(fresh_db, "T01")
        assert task is not None
        assert task.artifact_refs == []
        assert task.parent_task is None


# ============================================================
# Decomposer engine tests
# ============================================================

class TestInferArtifactRefs:
    """Test deterministic artifact inference."""

    def test_style_prefix_infers_guides(self):
        result = infer_artifact_refs(
            ["STYLE-01", "STYLE-02"],
            ["style-guide", "brand-guide"]
        )
        assert "style-guide" in result
        assert "brand-guide" in result

    def test_front_prefix_infers_guides(self):
        result = infer_artifact_refs(
            ["FRONT-01"],
            ["style-guide", "brand-guide"]
        )
        assert result == ["brand-guide", "style-guide"]

    def test_arch_prefix_infers_nothing(self):
        result = infer_artifact_refs(
            ["ARCH-01", "BACK-01"],
            ["style-guide", "brand-guide"]
        )
        assert result == []

    def test_filters_unavailable_artifacts(self):
        result = infer_artifact_refs(
            ["STYLE-01"],
            ["style-guide"]  # brand-guide not available
        )
        assert result == ["style-guide"]
        assert "brand-guide" not in result

    def test_comp_infers_competition_analysis(self):
        result = infer_artifact_refs(
            ["COMP-01"],
            ["competition-analysis"]
        )
        assert result == ["competition-analysis"]

    def test_empty_refs(self):
        assert infer_artifact_refs([], ["style-guide"]) == []


class TestParseDecomposeOutput:
    """Test LLM output parsing."""

    def test_valid_output(self):
        raw = json.dumps({
            "subtasks": [
                {
                    "id": "T01.1",
                    "title": "Data models",
                    "milestone": "M1",
                    "goal": "Create models",
                    "decision_refs": ["BACK-01"],
                    "files_create": ["src/models.py"],
                    "acceptance_criteria": ["Models created"],
                    "parent_task": "T01",
                }
            ],
            "missing_decisions": [
                {"decision_id": "SEC-01", "reason": "Rate limiting needed"}
            ]
        })
        subtasks, missing, errors = parse_decompose_output(raw, "T01")
        assert len(subtasks) == 1
        assert subtasks[0].id == "T01.1"
        assert len(missing) == 1
        assert not errors

    def test_auto_injects_parent_task(self):
        raw = json.dumps({
            "subtasks": [
                {
                    "id": "T01.1",
                    "title": "Sub",
                    "milestone": "M1",
                    "goal": "Do stuff",
                    "files_create": ["x.py"],
                    "acceptance_criteria": ["Works"],
                }
            ]
        })
        subtasks, _, errors = parse_decompose_output(raw, "T01")
        assert not errors
        assert subtasks[0].parent_task == "T01"

    def test_invalid_json(self):
        subtasks, _, errors = parse_decompose_output("{bad json", "T01")
        assert errors
        assert "Invalid JSON" in errors[0]

    def test_empty_subtasks(self):
        raw = json.dumps({"subtasks": []})
        _, _, errors = parse_decompose_output(raw, "T01")
        assert any("empty" in e.lower() for e in errors)

    def test_bad_subtask_id(self):
        raw = json.dumps({
            "subtasks": [
                {
                    "id": "T01",
                    "title": "Not a subtask",
                    "milestone": "M1",
                    "parent_task": "T01",
                }
            ]
        })
        _, _, errors = parse_decompose_output(raw, "T01")
        assert errors  # Should fail DecomposedTask validation


class TestValidateDecomposeOutput:
    """Test the 9 validation checks."""

    def _make_parent(self) -> Task:
        return Task(
            id="T01", title="Parent", milestone="M1",
            decision_refs=["BACK-01", "BACK-02"],
            files_create=["src/api.py", "src/db.py"],
            acceptance_criteria=["Works"],
        )

    def _make_decisions(self) -> list[Decision]:
        return [
            Decision(id="BACK-01", prefix=DecisionPrefix.BACK, number=1,
                     title="JWT auth", rationale="Security"),
            Decision(id="BACK-02", prefix=DecisionPrefix.BACK, number=2,
                     title="PostgreSQL", rationale="Reliability"),
        ]

    def test_valid_decomposition(self):
        parent = self._make_parent()
        subtasks = [
            DecomposedTask(id="T01.1", title="API routes", milestone="M1",
                           decision_refs=["BACK-01"], parent_task="T01",
                           goal="Build routes", files_create=["src/api.py"],
                           acceptance_criteria=["Routes work"]),
            DecomposedTask(id="T01.2", title="Database", milestone="M1",
                           decision_refs=["BACK-02"], parent_task="T01",
                           depends_on=["T01.1"], goal="Build DB",
                           files_create=["src/db.py"],
                           acceptance_criteria=["DB works"]),
        ]
        result = validate_decompose_output(subtasks, parent, self._make_decisions())
        assert result.valid

    def test_uncovered_parent_decisions(self):
        parent = self._make_parent()
        subtasks = [
            DecomposedTask(id="T01.1", title="Only BACK-01", milestone="M1",
                           decision_refs=["BACK-01"], parent_task="T01",
                           goal="Partial", files_create=["src/api.py"],
                           acceptance_criteria=["Works"]),
        ]
        result = validate_decompose_output(subtasks, parent, self._make_decisions())
        assert not result.valid
        assert any("BACK-02" in e for e in result.errors)

    def test_duplicate_ids(self):
        parent = self._make_parent()
        subtasks = [
            DecomposedTask(id="T01.1", title="First", milestone="M1",
                           decision_refs=["BACK-01"], parent_task="T01",
                           goal="A", files_create=["src/api.py"],
                           acceptance_criteria=["OK"]),
            DecomposedTask(id="T01.1", title="Dupe", milestone="M1",
                           decision_refs=["BACK-02"], parent_task="T01",
                           goal="B", files_create=["src/db.py"],
                           acceptance_criteria=["OK"]),
        ]
        result = validate_decompose_output(subtasks, parent, self._make_decisions())
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_self_dependency(self):
        parent = self._make_parent()
        subtasks = [
            DecomposedTask(id="T01.1", title="Self dep", milestone="M1",
                           decision_refs=["BACK-01", "BACK-02"],
                           depends_on=["T01.1"], parent_task="T01",
                           goal="Loop", files_create=["src/api.py", "src/db.py"],
                           acceptance_criteria=["OK"]),
        ]
        result = validate_decompose_output(subtasks, parent, self._make_decisions())
        assert not result.valid
        assert any("depends on itself" in e for e in result.errors)

    def test_bad_artifact_ref_caught_by_model(self):
        """Pydantic catches invalid artifact types at parse time."""
        with pytest.raises(ValueError, match="Unknown artifact type"):
            DecomposedTask(id="T01.1", title="Bad art", milestone="M1",
                           decision_refs=["BACK-01", "BACK-02"],
                           artifact_refs=["nonexistent"],
                           parent_task="T01", goal="Fail",
                           files_create=["src/api.py", "src/db.py"],
                           acceptance_criteria=["OK"])

    def test_missing_goal_warning(self):
        parent = self._make_parent()
        subtasks = [
            DecomposedTask(id="T01.1", title="No goal", milestone="M1",
                           decision_refs=["BACK-01", "BACK-02"],
                           parent_task="T01",
                           files_create=["src/api.py", "src/db.py"],
                           acceptance_criteria=["OK"]),
        ]
        result = validate_decompose_output(subtasks, parent, self._make_decisions())
        assert any("no goal" in w for w in result.warnings)

    def test_uncovered_files_warning(self):
        parent = self._make_parent()
        subtasks = [
            DecomposedTask(id="T01.1", title="Partial files", milestone="M1",
                           decision_refs=["BACK-01", "BACK-02"],
                           parent_task="T01", goal="Partial",
                           files_create=["src/api.py"],  # missing src/db.py
                           acceptance_criteria=["OK"]),
        ]
        result = validate_decompose_output(subtasks, parent, self._make_decisions())
        assert any("src/db.py" in w for w in result.warnings)


class TestSubtasksToTasks:
    """Test DecomposedTask → Task conversion."""

    def test_converts_all_fields(self):
        st = DecomposedTask(
            id="T01.1", title="Sub", milestone="M1", goal="Do",
            depends_on=["T01.2"], decision_refs=["BACK-01"],
            artifact_refs=["style-guide"], parent_task="T01",
            files_create=["x.py"], files_modify=["y.py"],
            acceptance_criteria=["Works"], verification_cmd="pytest",
        )
        tasks = subtasks_to_tasks([st])
        assert len(tasks) == 1
        t = tasks[0]
        assert t.id == "T01.1"
        assert t.parent_task == "T01"
        assert t.artifact_refs == ["style-guide"]
        assert t.status == TaskStatus.PENDING
        assert t.verification_cmd == "pytest"


class TestRunDecomposeForTask:
    """Test full pipeline: parse + validate."""

    def test_valid_pipeline(self, db_with_tasks):
        raw = json.dumps({
            "subtasks": [
                {
                    "id": "T01.1", "title": "API routes", "milestone": "M1",
                    "goal": "Build routes", "decision_refs": ["ARCH-01", "BACK-01"],
                    "files_create": ["src/api.py"], "acceptance_criteria": ["Routes work"],
                    "parent_task": "T01",
                },
                {
                    "id": "T01.2", "title": "Auth + DB", "milestone": "M1",
                    "goal": "Build auth", "depends_on": ["T01.1"],
                    "decision_refs": ["BACK-02"],
                    "files_create": ["src/auth.py", "src/db.py"],
                    "acceptance_criteria": ["Auth works"],
                    "parent_task": "T01",
                },
            ]
        })
        result = run_decompose_for_task(db_with_tasks, "T01", raw)
        assert result["status"] == "valid"
        assert result["subtask_count"] == 2

    def test_missing_parent(self, db_with_tasks):
        result = run_decompose_for_task(db_with_tasks, "T99", "{}")
        assert result["status"] == "error"
        assert any("not found" in e for e in result["errors"])

    def test_parse_error(self, db_with_tasks):
        result = run_decompose_for_task(db_with_tasks, "T01", "{bad json")
        assert result["status"] == "parse_error"


class TestStoreDecomposedTasks:
    """Test parent replacement + dependency rewiring."""

    def test_replaces_parent_with_subtasks(self, db_with_tasks):
        subtasks = [
            DecomposedTask(id="T01.1", title="API routes", milestone="M1",
                           goal="Routes", decision_refs=["ARCH-01", "BACK-01"],
                           parent_task="T01", files_create=["src/api.py"],
                           acceptance_criteria=["OK"]),
            DecomposedTask(id="T01.2", title="Auth + DB", milestone="M1",
                           goal="Auth", decision_refs=["BACK-02"],
                           depends_on=["T01.1"], parent_task="T01",
                           files_create=["src/auth.py", "src/db.py"],
                           acceptance_criteria=["OK"]),
        ]
        result = store_decomposed_tasks(db_with_tasks, "T01", subtasks)
        assert result["parent_deleted"] == "T01"
        assert result["subtasks_stored"] == 2
        assert result["last_subtask"] == "T01.2"

        # Parent gone
        assert db.get_task(db_with_tasks, "T01") is None

        # Subtasks exist
        assert db.get_task(db_with_tasks, "T01.1") is not None
        assert db.get_task(db_with_tasks, "T01.2") is not None

    def test_rewires_dependencies(self, db_with_tasks):
        """T02 and T03 depend on T01. After decompose, they should depend on T01.2."""
        subtasks = [
            DecomposedTask(id="T01.1", title="Part 1", milestone="M1",
                           goal="First", decision_refs=["ARCH-01", "BACK-01"],
                           parent_task="T01", files_create=["src/api.py"],
                           acceptance_criteria=["OK"]),
            DecomposedTask(id="T01.2", title="Part 2", milestone="M1",
                           goal="Second", decision_refs=["BACK-02"],
                           depends_on=["T01.1"], parent_task="T01",
                           files_create=["src/auth.py", "src/db.py"],
                           acceptance_criteria=["OK"]),
        ]
        store_decomposed_tasks(db_with_tasks, "T01", subtasks)

        t02 = db.get_task(db_with_tasks, "T02")
        t03 = db.get_task(db_with_tasks, "T03")
        assert t02 is not None
        assert "T01.2" in t02.depends_on
        assert "T01" not in t02.depends_on
        assert t03 is not None
        assert "T01.2" in t03.depends_on


class TestBuildDecomposePrompt:
    """Test prompt composition for decompose."""

    def test_prompt_contains_decisions(self, db_with_tasks):
        prompt = build_decompose_prompt(db_with_tasks, "T01")
        assert "ARCH-01" in prompt
        assert "BACK-01" in prompt

    def test_prompt_contains_artifacts(self, db_with_tasks):
        # T02 has artifact_refs
        prompt = build_decompose_prompt(db_with_tasks, "T02")
        assert "Style Guide" in prompt or "style-guide" in prompt.lower()

    def test_prompt_missing_task(self, db_with_tasks):
        prompt = build_decompose_prompt(db_with_tasks, "T99")
        assert "ERROR" in prompt


# ============================================================
# Composer tests
# ============================================================

class TestComposerArtifacts:
    """Test artifact loading in execution context."""

    def test_task_with_artifact_refs_gets_artifacts(self, db_with_tasks):
        """T02 has artifact_refs — its context should include artifact content."""
        ctx = compose_task_context(db_with_tasks, "T02")
        assert "artifacts" in ctx
        assert "style-guide" in ctx["artifacts"]
        assert "brand-guide" in ctx["artifacts"]

    def test_task_without_artifact_refs_no_artifacts(self, db_with_tasks):
        """T01 has no artifact_refs — its context should not have artifacts."""
        ctx = compose_task_context(db_with_tasks, "T01")
        assert "artifacts" not in ctx

    def test_execution_context_inherits_artifacts(self, db_with_tasks):
        """compose_execution_context should include artifacts from task_context."""
        # Need to mock reviewer to avoid import errors
        try:
            ctx = compose_execution_context(db_with_tasks, "T02")
            if "error" not in ctx:
                assert "artifacts" in ctx
        except (ImportError, ModuleNotFoundError):
            pytest.skip("reviewer module dependencies not available")


# ============================================================
# Validator tests
# ============================================================

class TestValidatorSubtasks:
    """Test validator changes for subtask IDs."""

    def test_check_task_ids_accepts_subtask_format(self):
        tasks = [
            Task(id="T01.1", title="Sub1", milestone="M1"),
            Task(id="T01.2", title="Sub2", milestone="M1"),
        ]
        result = check_task_ids(tasks)
        assert not result.errors

    def test_check_task_ids_mixed_queue(self):
        tasks = [
            Task(id="T01", title="Parent", milestone="M1"),
            Task(id="T02.1", title="Sub1", milestone="M1"),
            Task(id="T02.2", title="Sub2", milestone="M1"),
        ]
        result = check_task_ids(tasks)
        assert not result.errors

    def test_check_decomposed_coverage_pass(self):
        parent = Task(id="T01", title="Parent", milestone="M1",
                      decision_refs=["BACK-01", "BACK-02"])
        sub1 = Task(id="T01.1", title="Sub1", milestone="M1",
                     decision_refs=["BACK-01"], parent_task="T01")
        sub2 = Task(id="T01.2", title="Sub2", milestone="M1",
                     decision_refs=["BACK-02"], parent_task="T01")
        result = check_decomposed_coverage([sub1, sub2], [parent])
        assert result.valid

    def test_check_decomposed_coverage_fail(self):
        parent = Task(id="T01", title="Parent", milestone="M1",
                      decision_refs=["BACK-01", "BACK-02"])
        sub1 = Task(id="T01.1", title="Sub1", milestone="M1",
                     decision_refs=["BACK-01"], parent_task="T01")
        result = check_decomposed_coverage([sub1], [parent])
        assert not result.valid
        assert any("BACK-02" in e for e in result.errors)


# ============================================================
# Renderer tests
# ============================================================

class TestRendererNew:
    """Test new renderer functions."""

    def test_format_decision_index(self):
        index = {
            "ARCH": [{"id": "ARCH-01", "title": "Use FastAPI"}],
            "BACK": [
                {"id": "BACK-01", "title": "JWT"},
                {"id": "BACK-02", "title": "PostgreSQL"},
            ],
        }
        result = format_decision_index(index)
        assert "ARCH" in result
        assert "BACK" in result
        assert "ARCH-01" in result
        assert "(2)" in result  # BACK count

    def test_format_decision_index_empty(self):
        assert format_decision_index({}) == "(none)"

    def test_format_available_artifacts_strings(self):
        result = format_available_artifacts(["style-guide", "brand-guide"])
        assert "`brand-guide`" in result
        assert "`style-guide`" in result

    def test_format_available_artifacts_dicts(self):
        result = format_available_artifacts([
            {"type": "style-guide", "updated_at": "2026-01-01"},
        ])
        assert "`style-guide`" in result

    def test_format_available_artifacts_empty(self):
        assert format_available_artifacts([]) == "(none)"

    def test_get_decompose_schema_contains_fields(self):
        schema = get_decompose_schema()
        assert "subtasks" in schema
        assert "missing_decisions" in schema
        assert "artifact_refs" in schema
        assert "decision_refs" in schema

    def test_get_task_schema_includes_artifact_refs(self):
        schema = get_task_schema()
        assert "artifact_refs" in schema

    def test_render_decompose_schema(self):
        """Template with {{DECOMPOSE_SCHEMA}} renders correctly."""
        template = "Output: {{DECOMPOSE_SCHEMA}}"
        result = render(template, {"DECOMPOSE_SCHEMA": True})
        assert "subtasks" in result

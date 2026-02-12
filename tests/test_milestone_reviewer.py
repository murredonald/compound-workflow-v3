"""Tests for engine/milestone_reviewer.py — milestone review prompt composition.

Covers:
  - compose_milestone_review (context composition, prompt rendering)
  - MilestoneReviewFinding / MilestoneReviewResult models
"""

from __future__ import annotations

import pytest

from core import db
from core.models import (
    DeferredFinding,
    Milestone,
    Task,
    TaskEval,
    TaskStatus,
    TestResults,
    _now,
)
from engine.milestone_reviewer import (
    MAX_FILES_PER_MILESTONE,
    MilestoneReviewFinding,
    MilestoneReviewResult,
    compose_milestone_review,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_milestone(conn, milestone_id="M1", name="Test Milestone", goal=""):
    """Helper to seed a milestone."""
    m = Milestone(id=milestone_id, name=name, goal=goal)
    db.store_milestones(conn, [m])
    return m


def _seed_task(
    conn,
    task_id="T01",
    milestone="M1",
    files_create=None,
    files_modify=None,
    acceptance_criteria=None,
    status=TaskStatus.COMPLETED,
):
    """Helper to seed a task."""
    task = Task(
        id=task_id,
        title=f"Task {task_id}",
        milestone=milestone,
        files_create=files_create or [],
        files_modify=files_modify or [],
        acceptance_criteria=acceptance_criteria or [],
        status=status,
    )
    db.store_tasks(conn, [task])
    return task


def _seed_eval(
    conn,
    task_id="T01",
    milestone="M1",
    review_cycles=1,
    scope_violations=0,
    test_total=5,
    test_passed=5,
):
    """Helper to seed a task eval."""
    now = _now()
    eval_ = TaskEval(
        task_id=task_id,
        milestone=milestone,
        status=TaskStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        review_cycles=review_cycles,
        scope_violations=scope_violations,
        test_results=TestResults(
            total=test_total,
            passed=test_passed,
            failed=test_total - test_passed,
            skipped=0,
        ),
    )
    db.store_task_eval(conn, eval_)
    return eval_


def _seed_deferred(conn, finding_id="DF-01", discovered_in="T01"):
    """Helper to seed a deferred finding."""
    d = DeferredFinding(
        id=finding_id,
        discovered_in=discovered_in,
        category="missing-feature",
        affected_area="API",
        description="Missing endpoint for user deletion",
    )
    db.store_deferred_finding(conn, d)
    return d


# ---------------------------------------------------------------------------
# TestComposeMilestoneReview
# ---------------------------------------------------------------------------

class TestComposeMilestoneReview:
    def test_milestone_not_found(self, fresh_db, tmp_path):
        """Non-existent milestone returns error dict with fix_hint."""
        result = compose_milestone_review(fresh_db, "M99", tmp_path)
        assert result["status"] == "error"
        assert "fix_hint" in result

    def test_basic_composition(self, fresh_db, tmp_path):
        """Milestone with 2 completed tasks returns review_prompt."""
        _seed_milestone(fresh_db, goal="Build the core")
        _seed_task(fresh_db, "T01", files_create=["src/app.py"])
        _seed_task(fresh_db, "T02", files_create=["src/db.py"])
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("def hello(): pass\n")
        (tmp_path / "src" / "db.py").write_text("import sqlite3\n")

        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        assert result["status"] == "ok"
        assert "review_prompt" in result
        assert result["task_count"] == 2
        assert result["file_count"] == 2

    def test_includes_task_evals(self, fresh_db, tmp_path):
        """Task eval data appears in the prompt."""
        _seed_milestone(fresh_db)
        _seed_task(fresh_db, "T01", files_create=["app.py"])
        _seed_eval(fresh_db, "T01", review_cycles=3, scope_violations=1)
        (tmp_path / "app.py").write_text("x = 1\n")

        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        prompt = result["review_prompt"]
        assert "3 review cycles" in prompt
        assert "1 scope violations" in prompt
        assert result["eval_summary"]["total_review_cycles"] == 3

    def test_includes_deferred_findings(self, fresh_db, tmp_path):
        """Deferred findings from milestone tasks appear in prompt."""
        _seed_milestone(fresh_db)
        _seed_task(fresh_db, "T01", files_create=["app.py"])
        _seed_deferred(fresh_db, "DF-01", "T01")
        (tmp_path / "app.py").write_text("x = 1\n")

        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        prompt = result["review_prompt"]
        assert "DF-01" in prompt
        assert "Missing endpoint" in prompt
        assert result["deferred_count"] == 1

    def test_includes_file_contents(self, fresh_db, tmp_path):
        """Actual file content appears in the prompt."""
        _seed_milestone(fresh_db)
        _seed_task(fresh_db, "T01", files_create=["app.py"])
        (tmp_path / "app.py").write_text("def magic_number():\n    return 42\n")

        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        prompt = result["review_prompt"]
        assert "magic_number" in prompt
        assert "return 42" in prompt

    def test_blocked_task_flagged(self, fresh_db, tmp_path):
        """Blocked tasks are noted in the prompt."""
        _seed_milestone(fresh_db)
        _seed_task(fresh_db, "T01", status=TaskStatus.COMPLETED)
        _seed_task(fresh_db, "T02", status=TaskStatus.BLOCKED)

        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        prompt = result["review_prompt"]
        assert "BLOCKED" in prompt

    def test_file_limit(self, fresh_db, tmp_path):
        """More than MAX_FILES_PER_MILESTONE files → capped."""
        _seed_milestone(fresh_db)
        # Create a task with 25 files
        files = [f"src/file{i:02d}.py" for i in range(25)]
        _seed_task(fresh_db, "T01", files_create=files)
        (tmp_path / "src").mkdir()
        for f in files:
            (tmp_path / f).write_text(f"# {f}\n")

        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        assert result["file_count"] == MAX_FILES_PER_MILESTONE
        assert "total files" in result["review_prompt"]

    def test_empty_milestone(self, fresh_db, tmp_path):
        """Milestone with no tasks returns ok with task_count=0."""
        _seed_milestone(fresh_db)
        result = compose_milestone_review(fresh_db, "M1", tmp_path)
        assert result["status"] == "ok"
        assert result["task_count"] == 0
        assert result["file_count"] == 0


# ---------------------------------------------------------------------------
# TestModels
# ---------------------------------------------------------------------------

class TestModels:
    def test_milestone_review_finding_defaults(self):
        """Default field values work correctly."""
        f = MilestoneReviewFinding(
            severity="medium",
            category="completeness",
            description="Task T02 is blocked",
        )
        assert f.task_ref == ""
        assert f.fix_description == ""

    def test_milestone_review_result_structure(self):
        """model_dump() produces expected structure."""
        r = MilestoneReviewResult(
            verdict="milestone_complete",
            findings=[],
            task_assessment={"T01": "complete"},
            summary="All good",
        )
        d = r.model_dump()
        assert d["verdict"] == "milestone_complete"
        assert d["task_assessment"]["T01"] == "complete"
        assert d["findings"] == []

    def test_extra_fields_rejected(self):
        """WorkflowModel base rejects unknown fields (extra='forbid')."""
        with pytest.raises(Exception):
            MilestoneReviewFinding(
                severity="medium",
                category="completeness",
                description="test",
                bonus_field="nope",
            )

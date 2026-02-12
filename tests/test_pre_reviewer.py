"""Tests for engine/pre_reviewer.py — LLM pre-review prompt composition.

Covers:
  - _read_file_contents (file reading, truncation, binary skip)
  - compose_pre_review (context composition, prompt rendering)
  - PreReviewFinding / PreReviewResult models
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core import db
from core.models import (
    Decision,
    Milestone,
    Task,
)
from engine.pre_reviewer import (
    BINARY_EXTENSIONS,
    PreReviewFinding,
    PreReviewResult,
    _read_file_contents,
    compose_pre_review,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_task(
    conn,
    task_id="T01",
    files_create=None,
    files_modify=None,
    acceptance_criteria=None,
    decision_refs=None,
    goal="",
):
    """Helper to seed a task + required milestone."""
    milestone = Milestone(id="M1", name="Test Milestone")
    db.store_milestones(conn, [milestone])
    task = Task(
        id=task_id,
        title="Test task",
        milestone="M1",
        files_create=files_create or [],
        files_modify=files_modify or [],
        acceptance_criteria=acceptance_criteria or [],
        decision_refs=decision_refs or [],
        goal=goal,
    )
    db.store_tasks(conn, [task])
    return task


def _seed_decision(
    conn,
    decision_id="ARCH-01",
    prefix="ARCH",
    number=1,
    title="Test decision",
    rationale="Because reasons",
):
    """Helper to seed a decision."""
    d = Decision(
        id=decision_id,
        prefix=prefix,
        number=number,
        title=title,
        rationale=rationale,
    )
    db.store_decisions(conn, [d])
    return d


# ---------------------------------------------------------------------------
# TestReadFileContents
# ---------------------------------------------------------------------------

class TestReadFileContents:
    def test_read_existing_files(self, tmp_path):
        """Reads real files and returns their content."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        result = _read_file_contents(["app.py"], tmp_path)
        assert "app.py" in result
        assert "def hello():" in result["app.py"]

    def test_read_missing_file(self, tmp_path):
        """Missing files return a marker string."""
        result = _read_file_contents(["ghost.py"], tmp_path)
        assert "file not found" in result["ghost.py"]

    def test_read_large_file_truncation(self, tmp_path):
        """Files exceeding max_lines are truncated with a marker."""
        content = "\n".join(f"line {i}" for i in range(1000))
        (tmp_path / "big.py").write_text(content)
        result = _read_file_contents(["big.py"], tmp_path, max_lines=100)
        assert "truncated" in result["big.py"]
        assert "line 0" in result["big.py"]
        assert "line 99" in result["big.py"]
        assert "line 500" not in result["big.py"]

    def test_read_binary_file(self, tmp_path):
        """Binary files are skipped with a marker."""
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
        result = _read_file_contents(["image.png"], tmp_path)
        assert "binary" in result["image.png"].lower()

    def test_empty_file_list(self, tmp_path):
        """Empty input returns empty dict."""
        result = _read_file_contents([], tmp_path)
        assert result == {}

    def test_path_normalization(self, tmp_path):
        """Paths are normalized to forward slashes."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n")
        result = _read_file_contents(["src\\app.py"], tmp_path)
        # Key should use forward slashes
        assert "src/app.py" in result
        assert "src\\app.py" not in result


# ---------------------------------------------------------------------------
# TestComposePreReview
# ---------------------------------------------------------------------------

class TestComposePreReview:
    def test_task_not_found(self, fresh_db, tmp_path):
        """Non-existent task returns error dict with fix_hint."""
        result = compose_pre_review(fresh_db, "T99", tmp_path)
        assert result["status"] == "error"
        assert "fix_hint" in result

    def test_basic_composition(self, fresh_db, tmp_path):
        """Task with files, criteria, decisions returns review_prompt."""
        _seed_decision(fresh_db)
        _seed_task(
            fresh_db,
            files_create=["src/app.py"],
            acceptance_criteria=["Must have a hello function"],
            decision_refs=["ARCH-01"],
            goal="Create the app module",
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text(
            "def hello():\n    return 'world'\n"
        )

        result = compose_pre_review(fresh_db, "T01", tmp_path)
        assert result["status"] == "ok"
        assert "review_prompt" in result
        assert result["file_count"] == 1
        assert len(result["acceptance_criteria"]) == 1

    def test_with_verify_result(self, fresh_db, tmp_path):
        """Verify result is incorporated into context."""
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("x = 1\n")
        verify = {
            "status": "fail",
            "all_passed": False,
            "summary": "12/13 checks passed. 1 auto-fixable.",
            "checks": [
                {"name": "lint", "passed": False, "output": "E501 line too long"},
            ],
        }
        result = compose_pre_review(fresh_db, "T01", tmp_path, verify_result=verify)
        assert result["status"] == "ok"
        assert result["verify_all_passed"] is False
        assert "12/13" in result["verify_summary"]

    def test_without_verify_result(self, fresh_db, tmp_path):
        """Works cleanly without verify data."""
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("x = 1\n")
        result = compose_pre_review(fresh_db, "T01", tmp_path)
        assert result["status"] == "ok"
        assert result["verify_all_passed"] is True
        assert result["verify_summary"] == ""

    def test_prompt_contains_criteria(self, fresh_db, tmp_path):
        """Review prompt includes all acceptance criteria."""
        criteria = ["Must return JSON", "Must handle errors", "Must log requests"]
        _seed_task(
            fresh_db,
            files_create=["app.py"],
            acceptance_criteria=criteria,
        )
        (tmp_path / "app.py").write_text("pass\n")
        result = compose_pre_review(fresh_db, "T01", tmp_path)
        prompt = result["review_prompt"]
        for c in criteria:
            assert c in prompt

    def test_prompt_contains_decisions(self, fresh_db, tmp_path):
        """Review prompt includes referenced decisions."""
        _seed_decision(
            fresh_db,
            "ARCH-01",
            "ARCH",
            1,
            "Use SQLite",
            "Lightweight and embedded",
        )
        _seed_task(
            fresh_db,
            files_create=["app.py"],
            decision_refs=["ARCH-01"],
        )
        (tmp_path / "app.py").write_text("import sqlite3\n")
        result = compose_pre_review(fresh_db, "T01", tmp_path)
        prompt = result["review_prompt"]
        assert "ARCH-01" in prompt
        assert "Use SQLite" in prompt

    def test_prompt_contains_file_contents(self, fresh_db, tmp_path):
        """Review prompt includes actual file contents."""
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("def magic_number():\n    return 42\n")
        result = compose_pre_review(fresh_db, "T01", tmp_path)
        prompt = result["review_prompt"]
        assert "magic_number" in prompt
        assert "return 42" in prompt

    def test_prompt_contains_verify_failures(self, fresh_db, tmp_path):
        """Failing verify checks are shown in the prompt."""
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("x = 1\n")
        verify = {
            "status": "fail",
            "all_passed": False,
            "checks": [
                {"name": "lint", "passed": False, "output": "E501 line too long"},
                {"name": "tests", "passed": True, "output": ""},
            ],
        }
        result = compose_pre_review(fresh_db, "T01", tmp_path, verify_result=verify)
        prompt = result["review_prompt"]
        assert "FAIL" in prompt
        assert "E501" in prompt

    def test_empty_task_files(self, fresh_db, tmp_path):
        """Task with no files returns ok with file_count=0."""
        _seed_task(fresh_db, files_create=[], files_modify=[])
        result = compose_pre_review(fresh_db, "T01", tmp_path)
        assert result["status"] == "ok"
        assert result["file_count"] == 0


# ---------------------------------------------------------------------------
# TestModels
# ---------------------------------------------------------------------------

class TestModels:
    def test_pre_review_finding_defaults(self):
        """Default field values work correctly."""
        f = PreReviewFinding(
            severity="medium",
            category="criteria",
            description="AC 1 not met",
        )
        assert f.file == ""
        assert f.fix_description == ""

    def test_pre_review_result_structure(self):
        """model_dump() produces expected structure."""
        r = PreReviewResult(
            verdict="pass",
            findings=[],
            criteria_status={"AC 1": "met"},
            summary="All good",
        )
        d = r.model_dump()
        assert d["verdict"] == "pass"
        assert d["criteria_status"]["AC 1"] == "met"
        assert d["findings"] == []

    def test_extra_fields_rejected(self):
        """WorkflowModel base rejects unknown fields (extra='forbid')."""
        with pytest.raises(Exception):
            PreReviewFinding(
                severity="medium",
                category="criteria",
                description="test",
                bonus_field="nope",
            )

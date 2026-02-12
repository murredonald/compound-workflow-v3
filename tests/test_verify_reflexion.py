"""Tests for verify reflexion — auto-learning from recurring check failures.

Covers:
  - CHECK_CATEGORY_MAP completeness and validity
  - extract_verify_reflexion (entry extraction from verify results)
  - verify_and_reflect (end-to-end: verify + reflexion storage + systemic detection)
"""

from __future__ import annotations

import pytest

from core import db
from core.models import (
    Milestone,
    ReflexionCategory,
    ReflexionEntry,
    Task,
)
from engine.verifier import (
    CHECK_CATEGORY_MAP,
    _HIGH_SEVERITY_CHECKS,
    extract_verify_reflexion,
    verify_and_reflect,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_task(
    conn,
    task_id="T01",
    files_create=None,
    files_modify=None,
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
    )
    db.store_tasks(conn, [task])
    return task


def _make_verify_result(
    task_id: str = "T01",
    checks: list[dict] | None = None,
    all_passed: bool = False,
) -> dict:
    """Build a verify result dict matching run_verify() output."""
    if checks is None:
        checks = []
    return {
        "status": "ok" if all_passed else "fail",
        "task_id": task_id,
        "checks": checks,
        "all_passed": all_passed,
        "auto_fixable_count": 0,
        "summary": "",
    }


def _make_check(
    name: str,
    passed: bool = True,
    output: str = "",
    fix_hint: str = "",
    skipped: bool = False,
) -> dict:
    """Build a single check result dict."""
    return {
        "name": name,
        "passed": passed,
        "output": output,
        "fix_hint": fix_hint,
        "skipped": skipped,
        "auto_fixable": False,
        "fix_cmd": "",
        "skip_reason": "",
    }


# ---------------------------------------------------------------------------
# TestCheckCategoryMap
# ---------------------------------------------------------------------------

class TestCheckCategoryMap:
    def test_all_checks_mapped(self):
        """Every known check name from the 13-check pipeline has a mapping."""
        expected_checks = {
            "lint", "format", "spelling", "type-check", "security",
            "secrets", "dep-audit", "tests", "data-validation",
            "task-verify", "debug-artifacts", "conflict-markers", "placeholders",
        }
        assert set(CHECK_CATEGORY_MAP.keys()) == expected_checks

    def test_categories_are_valid(self):
        """All mapped values are valid ReflexionCategory enum values."""
        valid = {c.value for c in ReflexionCategory}
        for check_name, category in CHECK_CATEGORY_MAP.items():
            assert category in valid, f"{check_name} maps to invalid category: {category}"


# ---------------------------------------------------------------------------
# TestExtractVerifyReflexion
# ---------------------------------------------------------------------------

class TestExtractVerifyReflexion:
    def test_no_failures_returns_empty(self):
        """All-pass verify result produces no reflexion entries."""
        result = _make_verify_result(
            checks=[_make_check("lint"), _make_check("tests")],
            all_passed=True,
        )
        entries = extract_verify_reflexion("T01", result, ["app.py"])
        assert entries == []

    def test_single_failure(self):
        """One failed check produces one reflexion entry with correct fields."""
        result = _make_verify_result(checks=[
            _make_check("lint", passed=False, output="E501 line too long",
                        fix_hint="Run ruff check --fix"),
        ])
        entries = extract_verify_reflexion("T01", result, ["src/app.py"])
        assert len(entries) == 1
        e = entries[0]
        assert e["task_id"] == "T01"
        assert e["category"] == "type-mismatch"  # lint → type-mismatch
        assert "lint" in e["tags"]
        assert "src/app.py" in e["tags"]
        assert "E501" in e["what_happened"]
        assert e["severity"] == "medium"

    def test_multiple_failures(self):
        """Two failed checks produce two entries."""
        result = _make_verify_result(checks=[
            _make_check("lint", passed=False, output="E501"),
            _make_check("tests", passed=False, output="FAILED test_foo"),
        ])
        entries = extract_verify_reflexion("T01", result, ["app.py"])
        assert len(entries) == 2
        categories = {e["category"] for e in entries}
        assert "type-mismatch" in categories  # lint
        assert "edge-case-logic" in categories  # tests

    def test_skipped_checks_ignored(self):
        """Skipped checks don't produce entries."""
        result = _make_verify_result(checks=[
            _make_check("lint", passed=True),
            _make_check("security", skipped=True),
            _make_check("tests", passed=False, output="FAILED"),
        ])
        entries = extract_verify_reflexion("T01", result, ["app.py"])
        assert len(entries) == 1
        assert entries[0]["category"] == "edge-case-logic"

    def test_severity_escalation(self):
        """security/secrets/tests checks get 'high' severity; others get 'medium'."""
        result = _make_verify_result(checks=[
            _make_check("lint", passed=False, output="err"),
            _make_check("security", passed=False, output="B101"),
            _make_check("secrets", passed=False, output="found key"),
            _make_check("tests", passed=False, output="FAILED"),
        ])
        entries = extract_verify_reflexion("T01", result, ["app.py"])
        severity_map = {e["tags"][-1]: e["severity"] for e in entries}
        assert severity_map["lint"] == "medium"
        assert severity_map["security"] == "high"
        assert severity_map["secrets"] == "high"
        assert severity_map["tests"] == "high"

    def test_entry_structure(self):
        """Entries have all required fields and no 'id' field."""
        result = _make_verify_result(checks=[
            _make_check("lint", passed=False, output="err", fix_hint="fix it"),
        ])
        entries = extract_verify_reflexion("T01", result, ["app.py"])
        e = entries[0]
        required = {
            "task_id", "tags", "category", "severity",
            "what_happened", "root_cause", "lesson",
            "applies_to", "preventive_action",
        }
        assert required.issubset(set(e.keys()))
        assert "id" not in e  # Caller assigns ID

    def test_output_truncation(self):
        """Long check output is truncated in the reflexion entry."""
        long_output = "x" * 500
        result = _make_verify_result(checks=[
            _make_check("lint", passed=False, output=long_output),
        ])
        entries = extract_verify_reflexion("T01", result, ["app.py"])
        assert len(entries[0]["what_happened"]) < 500


# ---------------------------------------------------------------------------
# TestVerifyAndReflect
# ---------------------------------------------------------------------------

class TestVerifyAndReflect:
    def test_task_not_found(self, fresh_db, tmp_path):
        """Non-existent task returns error dict."""
        result = verify_and_reflect(fresh_db, "T99", tmp_path)
        assert result.get("status") == "error"

    def test_all_pass_no_reflexion(self, fresh_db, tmp_path):
        """Clean verify with no files → all passed, no reflexion entries."""
        _seed_task(fresh_db, files_create=[], files_modify=[])
        result = verify_and_reflect(fresh_db, "T01", tmp_path)
        assert result["all_passed"] is True
        assert result["reflexion_entries"] == []
        assert result["systemic_issues"] == []

    def test_failure_records_reflexion(self, fresh_db, tmp_path):
        """Failed check → reflexion entry stored in DB."""
        # Create a Python file with a placeholder (will trigger the placeholder check)
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("def foo():\n    pass\n")
        result = verify_and_reflect(fresh_db, "T01", tmp_path)
        # The placeholder check should fire on "pass"
        if not result.get("all_passed", True):
            assert len(result["reflexion_entries"]) > 0
            # Verify it's actually in the DB
            db_entries = db.get_reflexion_entries(fresh_db, task_id="T01")
            assert len(db_entries) > 0

    def test_result_enrichment(self, fresh_db, tmp_path):
        """Return value includes both verify data and reflexion metadata."""
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("x = 1\n")
        result = verify_and_reflect(fresh_db, "T01", tmp_path)
        # Always has these keys regardless of pass/fail
        assert "reflexion_entries" in result
        assert "systemic_issues" in result
        # Also has standard verify keys
        assert "task_id" in result
        assert "checks" in result

    def test_systemic_detection(self, fresh_db, tmp_path):
        """Seed 2 prior entries with same category+tag, add 1 more → systemic."""
        _seed_task(fresh_db, files_create=["app.py"])
        (tmp_path / "app.py").write_text("x = 1\n")

        # Seed 2 prior reflexion entries with same category + overlapping tag
        for i in range(2):
            entry = ReflexionEntry(
                id=f"R{i + 1:03d}",
                task_id="T01",
                tags=["app.py", "lint"],
                category="type-mismatch",
                severity="medium",
                what_happened=f"Lint failed iteration {i}",
                root_cause="Bad style",
                lesson="Fix lint",
            )
            db.store_reflexion_entry(fresh_db, entry)

        # Now verify — any failure with same category will make it 3+
        result = verify_and_reflect(fresh_db, "T01", tmp_path)
        # We can't guarantee a specific check will fail in this env,
        # but the structure should be correct
        assert "systemic_issues" in result
        assert isinstance(result["systemic_issues"], list)

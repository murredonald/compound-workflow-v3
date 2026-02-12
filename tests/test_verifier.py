"""Tests for engine/verifier.py — task-scoped verification pipeline.

Covers:
  - detect_project_type (config file detection + tool availability)
  - _find_test_files (source-to-test mapping)
  - _run_check (subprocess runner)
  - _scan_files_for_patterns (regex scanning for LLM artifacts)
  - _validate_data_files (JSON/YAML validation)
  - run_verify (full pipeline integration)
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from core import db
from core.models import (
    Decision,
    Milestone,
    Task,
)
from engine.verifier import (
    CheckResult,
    VerifyResult,
    _filter_by_ext,
    _find_test_files,
    _run_check,
    _scan_files_for_patterns,
    _validate_data_files,
    CONFLICT_PATTERNS,
    DEBUG_PATTERNS,
    PLACEHOLDER_PATTERNS,
    detect_project_type,
    run_verify,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _seed_task(conn, task_id="T01", files_create=None, files_modify=None,
               verification_cmd=None):
    """Helper to seed a task + required milestone."""
    milestone = Milestone(id="M1", name="Test Milestone")
    db.store_milestones(conn, [milestone])

    task = Task(
        id=task_id,
        title="Test task",
        milestone="M1",
        files_create=files_create or [],
        files_modify=files_modify or [],
        verification_cmd=verification_cmd,
        decision_refs=[],
    )
    db.store_tasks(conn, [task])
    return task


# ---------------------------------------------------------------------------
# detect_project_type
# ---------------------------------------------------------------------------

class TestDetectProjectType:
    def test_python_project(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
        caps = detect_project_type(tmp_path)
        assert caps["has_python"] is True
        assert caps["has_node"] is False

    def test_node_project(self, tmp_path):
        (tmp_path / "package.json").write_text("{}\n")
        caps = detect_project_type(tmp_path)
        assert caps["has_node"] is True
        assert caps["has_python"] is False

    def test_empty_dir(self, tmp_path):
        caps = detect_project_type(tmp_path)
        assert caps["has_python"] is False
        assert caps["has_node"] is False

    def test_tool_detection(self, tmp_path):
        """Tool detection uses shutil.which — just verify keys exist."""
        caps = detect_project_type(tmp_path)
        expected_keys = {
            "has_python", "has_node", "has_ruff", "has_mypy",
            "has_bandit", "has_eslint", "has_tsc", "has_prettier",
            "has_gitleaks", "has_codespell", "has_pip_audit",
            "has_npm", "has_pytest",
        }
        assert set(caps.keys()) == expected_keys


# ---------------------------------------------------------------------------
# _find_test_files
# ---------------------------------------------------------------------------

class TestFindTestFiles:
    def test_flat_convention(self, tmp_path):
        """src/foo.py → tests/test_foo.py"""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.py").write_text("# test")
        result = _find_test_files(["src/foo.py"], tmp_path)
        assert "tests/test_foo.py" in result

    def test_nested_convention(self, tmp_path):
        """src/core/bar.py → tests/core/test_bar.py"""
        (tmp_path / "tests" / "core").mkdir(parents=True)
        (tmp_path / "tests" / "core" / "test_bar.py").write_text("# test")
        result = _find_test_files(["src/core/bar.py"], tmp_path)
        assert "tests/core/test_bar.py" in result

    def test_no_match(self, tmp_path):
        result = _find_test_files(["src/mystery.py"], tmp_path)
        assert result == []

    def test_non_python_skipped(self, tmp_path):
        result = _find_test_files(["src/style.css", "README.md"], tmp_path)
        assert result == []

    def test_test_file_included_directly(self, tmp_path):
        """If a test file is in the task's file list, include it."""
        (tmp_path / "tests").mkdir(exist_ok=True)
        (tmp_path / "tests" / "test_widget.py").write_text("# test")
        result = _find_test_files(["tests/test_widget.py"], tmp_path)
        assert "tests/test_widget.py" in result

    def test_dedup(self, tmp_path):
        """Same source appears twice → test file only listed once."""
        (tmp_path / "tests").mkdir(exist_ok=True)
        (tmp_path / "tests" / "test_foo.py").write_text("# test")
        result = _find_test_files(["src/foo.py", "src/foo.py"], tmp_path)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _filter_by_ext
# ---------------------------------------------------------------------------

class TestFilterByExt:
    def test_python_filter(self):
        files = ["a.py", "b.js", "c.py", "d.md"]
        assert _filter_by_ext(files, {".py"}) == ["a.py", "c.py"]

    def test_multi_ext(self):
        files = ["a.js", "b.ts", "c.tsx", "d.py"]
        assert _filter_by_ext(files, {".js", ".ts", ".tsx"}) == ["a.js", "b.ts", "c.tsx"]


# ---------------------------------------------------------------------------
# _run_check
# ---------------------------------------------------------------------------

class TestRunCheck:
    def test_passing(self, tmp_path):
        with patch("engine.verifier.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["echo", "ok"], returncode=0, stdout="ok", stderr="",
            )
            result = _run_check("test-check", ["echo", "ok"], tmp_path)
            assert result.passed is True
            assert result.output == ""
            assert result.auto_fixable is False

    def test_failing(self, tmp_path):
        with patch("engine.verifier.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["ruff", "check"], returncode=1,
                stdout="error: E501 line too long", stderr="",
            )
            result = _run_check(
                "lint", ["ruff", "check"], tmp_path,
                auto_fixable=True, fix_cmd="ruff check --fix",
            )
            assert result.passed is False
            assert "E501" in result.output
            assert result.auto_fixable is True
            assert result.fix_cmd == "ruff check --fix"

    def test_timeout(self, tmp_path):
        with patch("engine.verifier.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="mypy", timeout=60)
            result = _run_check("type-check", ["mypy", "foo.py"], tmp_path, timeout=60)
            assert result.passed is False
            assert "timed out" in result.output

    def test_tool_not_found(self, tmp_path):
        with patch("engine.verifier.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("No such file")
            result = _run_check("lint", ["nonexistent"], tmp_path)
            assert result.passed is True
            assert result.skipped is True

    def test_output_truncation(self, tmp_path):
        with patch("engine.verifier.subprocess.run") as mock_run:
            long_output = "x" * 10000
            mock_run.return_value = subprocess.CompletedProcess(
                args=["cmd"], returncode=1, stdout=long_output, stderr="",
            )
            result = _run_check("big-check", ["cmd"], tmp_path)
            assert len(result.output) < 6000
            assert "truncated" in result.output


# ---------------------------------------------------------------------------
# _scan_files_for_patterns
# ---------------------------------------------------------------------------

class TestScanPatterns:
    def test_debug_artifacts(self, tmp_path):
        (tmp_path / "app.py").write_text(
            "x = 1\nbreakpoint()\nprint('hello')\nimport pdb\n"
        )
        matches = _scan_files_for_patterns(
            ["app.py"], DEBUG_PATTERNS, tmp_path,
        )
        assert any("breakpoint()" in m for m in matches)
        assert any("import pdb" in m for m in matches)

    def test_todo_fixme(self, tmp_path):
        (tmp_path / "code.py").write_text(
            "# TODO fix this\n# FIXME broken\n# HACK workaround\n"
        )
        matches = _scan_files_for_patterns(
            ["code.py"], DEBUG_PATTERNS, tmp_path,
        )
        assert len(matches) == 3

    def test_conflict_markers(self, tmp_path):
        (tmp_path / "merge.py").write_text(
            "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n"
        )
        matches = _scan_files_for_patterns(
            ["merge.py"], CONFLICT_PATTERNS, tmp_path,
        )
        assert len(matches) == 3

    def test_placeholders(self, tmp_path):
        (tmp_path / "stub.py").write_text(
            "def foo():\n    pass\n\ndef bar():\n    ...\n\ndef baz():\n    raise NotImplementedError\n"
        )
        matches = _scan_files_for_patterns(
            ["stub.py"], PLACEHOLDER_PATTERNS, tmp_path,
        )
        assert len(matches) == 3

    def test_clean_file(self, tmp_path):
        (tmp_path / "clean.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n"
        )
        for patterns in [DEBUG_PATTERNS, CONFLICT_PATTERNS, PLACEHOLDER_PATTERNS]:
            matches = _scan_files_for_patterns(
                ["clean.py"], patterns, tmp_path,
            )
            assert matches == []

    def test_nonexistent_file_skipped(self, tmp_path):
        matches = _scan_files_for_patterns(
            ["ghost.py"], DEBUG_PATTERNS, tmp_path,
        )
        assert matches == []


# ---------------------------------------------------------------------------
# _validate_data_files
# ---------------------------------------------------------------------------

class TestValidateDataFiles:
    def test_valid_json(self, tmp_path):
        (tmp_path / "config.json").write_text('{"key": "value"}')
        errors = _validate_data_files(["config.json"], tmp_path)
        assert errors == []

    def test_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text('{key: value}')
        errors = _validate_data_files(["bad.json"], tmp_path)
        assert len(errors) == 1
        assert "invalid JSON" in errors[0]

    def test_nonexistent_skipped(self, tmp_path):
        errors = _validate_data_files(["ghost.json"], tmp_path)
        assert errors == []


# ---------------------------------------------------------------------------
# run_verify
# ---------------------------------------------------------------------------

class TestRunVerify:
    def test_task_not_found(self, fresh_db):
        result = run_verify(fresh_db, "T99", Path("."))
        assert result["status"] == "error"
        assert "fix_hint" in result

    def test_empty_file_list(self, fresh_db):
        _seed_task(fresh_db, files_create=[], files_modify=[])
        result = run_verify(fresh_db, "T01", Path("."))
        assert result["status"] == "ok"
        assert result["all_passed"] is True
        assert "No files" in result["summary"]

    @patch("engine.verifier.detect_project_type")
    @patch("engine.verifier._run_check")
    def test_python_project_runs_checks(self, mock_run, mock_detect, fresh_db, tmp_path):
        """With all tools available, verify runs lint/format/type/security checks."""
        _seed_task(fresh_db, files_create=["src/app.py"])

        mock_detect.return_value = {
            "has_python": True, "has_node": False,
            "has_ruff": True, "has_mypy": True, "has_bandit": True,
            "has_eslint": False, "has_tsc": False, "has_prettier": False,
            "has_gitleaks": True, "has_codespell": True,
            "has_pip_audit": True, "has_npm": False, "has_pytest": False,
        }
        mock_run.return_value = CheckResult(name="mock", passed=True)

        result = run_verify(fresh_db, "T01", tmp_path)

        # Verify _run_check was called for lint, format, spelling, type-check,
        # security, secrets, dep-audit
        check_names = [call.args[0] for call in mock_run.call_args_list]
        assert "lint" in check_names
        assert "format" in check_names
        assert "spelling" in check_names
        assert "type-check" in check_names
        assert "security" in check_names
        assert "secrets" in check_names
        assert "dep-audit" in check_names

    @patch("engine.verifier.detect_project_type")
    def test_skips_missing_tools(self, mock_detect, fresh_db, tmp_path):
        """When no tools are available, only built-in checks run."""
        _seed_task(fresh_db, files_create=["src/app.py"])

        mock_detect.return_value = {
            "has_python": True, "has_node": False,
            "has_ruff": False, "has_mypy": False, "has_bandit": False,
            "has_eslint": False, "has_tsc": False, "has_prettier": False,
            "has_gitleaks": False, "has_codespell": False,
            "has_pip_audit": False, "has_npm": False, "has_pytest": False,
        }

        result = run_verify(fresh_db, "T01", tmp_path)

        # Should still have the built-in checks (debug, conflict, placeholder)
        check_names = [c["name"] for c in result["checks"]]
        assert "debug-artifacts" in check_names
        assert "conflict-markers" in check_names
        assert "placeholders" in check_names
        # No subprocess checks should have run
        assert "lint" not in check_names
        assert "type-check" not in check_names

    @patch("engine.verifier.detect_project_type")
    @patch("engine.verifier._run_check")
    def test_verification_cmd_included(self, mock_run, mock_detect, fresh_db, tmp_path):
        """Task with verification_cmd gets an extra task-verify check."""
        _seed_task(fresh_db, files_create=["src/app.py"],
                   verification_cmd="pytest tests/ -v")

        mock_detect.return_value = {
            "has_python": True, "has_node": False,
            "has_ruff": False, "has_mypy": False, "has_bandit": False,
            "has_eslint": False, "has_tsc": False, "has_prettier": False,
            "has_gitleaks": False, "has_codespell": False,
            "has_pip_audit": False, "has_npm": False, "has_pytest": False,
        }
        mock_run.return_value = CheckResult(name="task-verify", passed=True)

        result = run_verify(fresh_db, "T01", tmp_path)
        check_names = [c["name"] for c in result["checks"]]
        assert "task-verify" in check_names

    @patch("engine.verifier.detect_project_type")
    @patch("engine.verifier._run_check")
    def test_file_scoping(self, mock_run, mock_detect, fresh_db, tmp_path):
        """Ruff only receives .py files from the task, not all files."""
        _seed_task(fresh_db, files_create=["src/app.py", "src/style.css", "README.md"])

        mock_detect.return_value = {
            "has_python": True, "has_node": False,
            "has_ruff": True, "has_mypy": False, "has_bandit": False,
            "has_eslint": False, "has_tsc": False, "has_prettier": False,
            "has_gitleaks": False, "has_codespell": False,
            "has_pip_audit": False, "has_npm": False, "has_pytest": False,
        }
        mock_run.return_value = CheckResult(name="lint", passed=True)

        run_verify(fresh_db, "T01", tmp_path)

        # Check the lint call only got .py files
        lint_call = mock_run.call_args_list[0]
        cmd_arg = lint_call.args[1]  # the command list
        assert "src/app.py" in cmd_arg
        assert "src/style.css" not in cmd_arg
        assert "README.md" not in cmd_arg

    def test_json_validation(self, fresh_db, tmp_path):
        """Task with .json file gets data-validation check."""
        _seed_task(fresh_db, files_create=["config.json"])
        (tmp_path / "config.json").write_text('{"valid": true}')

        with patch("engine.verifier.detect_project_type") as mock_detect:
            mock_detect.return_value = {
                "has_python": False, "has_node": False,
                "has_ruff": False, "has_mypy": False, "has_bandit": False,
                "has_eslint": False, "has_tsc": False, "has_prettier": False,
                "has_gitleaks": False, "has_codespell": False,
                "has_pip_audit": False, "has_npm": False, "has_pytest": False,
            }
            result = run_verify(fresh_db, "T01", tmp_path)

        check_names = [c["name"] for c in result["checks"]]
        assert "data-validation" in check_names
        data_check = next(c for c in result["checks"] if c["name"] == "data-validation")
        assert data_check["passed"] is True

    def test_invalid_json_fails(self, fresh_db, tmp_path):
        """Invalid JSON file triggers data-validation failure."""
        _seed_task(fresh_db, files_create=["bad.json"])
        (tmp_path / "bad.json").write_text('{broken}')

        with patch("engine.verifier.detect_project_type") as mock_detect:
            mock_detect.return_value = {
                "has_python": False, "has_node": False,
                "has_ruff": False, "has_mypy": False, "has_bandit": False,
                "has_eslint": False, "has_tsc": False, "has_prettier": False,
                "has_gitleaks": False, "has_codespell": False,
                "has_pip_audit": False, "has_npm": False, "has_pytest": False,
            }
            result = run_verify(fresh_db, "T01", tmp_path)

        assert result["status"] == "fail"
        data_check = next(c for c in result["checks"] if c["name"] == "data-validation")
        assert data_check["passed"] is False

    @patch("engine.verifier.detect_project_type")
    @patch("engine.verifier._run_check")
    def test_auto_fixable_flags(self, mock_run, mock_detect, fresh_db, tmp_path):
        """Lint and format are auto_fixable when they fail; type-check is not."""
        _seed_task(fresh_db, files_create=["src/app.py"])

        mock_detect.return_value = {
            "has_python": True, "has_node": False,
            "has_ruff": True, "has_mypy": True, "has_bandit": False,
            "has_eslint": False, "has_tsc": False, "has_prettier": False,
            "has_gitleaks": False, "has_codespell": False,
            "has_pip_audit": False, "has_npm": False, "has_pytest": False,
        }

        def mock_check(name, cmd, cwd, **kwargs):
            # All checks fail
            return CheckResult(
                name=name,
                passed=False,
                output="error",
                auto_fixable=kwargs.get("auto_fixable", False),
                fix_cmd=kwargs.get("fix_cmd", ""),
            )

        mock_run.side_effect = mock_check

        result = run_verify(fresh_db, "T01", tmp_path)

        checks_by_name = {c["name"]: c for c in result["checks"]}
        assert checks_by_name["lint"]["auto_fixable"] is True
        assert checks_by_name["format"]["auto_fixable"] is True
        assert checks_by_name["type-check"]["auto_fixable"] is False

    def test_debug_artifact_detection(self, fresh_db, tmp_path):
        """Files with breakpoint() trigger debug-artifacts failure."""
        _seed_task(fresh_db, files_create=["src/app.py"])
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "app.py").write_text("x = 1\nbreakpoint()\n")

        with patch("engine.verifier.detect_project_type") as mock_detect:
            mock_detect.return_value = {
                "has_python": False, "has_node": False,
                "has_ruff": False, "has_mypy": False, "has_bandit": False,
                "has_eslint": False, "has_tsc": False, "has_prettier": False,
                "has_gitleaks": False, "has_codespell": False,
                "has_pip_audit": False, "has_npm": False, "has_pytest": False,
            }
            result = run_verify(fresh_db, "T01", tmp_path)

        debug_check = next(c for c in result["checks"] if c["name"] == "debug-artifacts")
        assert debug_check["passed"] is False
        assert "breakpoint()" in debug_check["output"]

    def test_conflict_marker_detection(self, fresh_db, tmp_path):
        """Files with merge conflict markers trigger failure."""
        _seed_task(fresh_db, files_create=["src/app.py"])
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "app.py").write_text("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> main\n")

        with patch("engine.verifier.detect_project_type") as mock_detect:
            mock_detect.return_value = {
                "has_python": False, "has_node": False,
                "has_ruff": False, "has_mypy": False, "has_bandit": False,
                "has_eslint": False, "has_tsc": False, "has_prettier": False,
                "has_gitleaks": False, "has_codespell": False,
                "has_pip_audit": False, "has_npm": False, "has_pytest": False,
            }
            result = run_verify(fresh_db, "T01", tmp_path)

        conflict_check = next(c for c in result["checks"] if c["name"] == "conflict-markers")
        assert conflict_check["passed"] is False

    def test_all_passed_when_clean(self, fresh_db, tmp_path):
        """Clean files with no tools → all built-in checks pass."""
        _seed_task(fresh_db, files_create=["src/app.py"])
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "app.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n")

        with patch("engine.verifier.detect_project_type") as mock_detect:
            mock_detect.return_value = {
                "has_python": False, "has_node": False,
                "has_ruff": False, "has_mypy": False, "has_bandit": False,
                "has_eslint": False, "has_tsc": False, "has_prettier": False,
                "has_gitleaks": False, "has_codespell": False,
                "has_pip_audit": False, "has_npm": False, "has_pytest": False,
            }
            result = run_verify(fresh_db, "T01", tmp_path)

        assert result["status"] == "ok"
        assert result["all_passed"] is True

    def test_summary_format(self, fresh_db, tmp_path):
        """Summary string includes check counts."""
        _seed_task(fresh_db, files_create=["src/app.py"])
        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "app.py").write_text("x = 1\n")

        with patch("engine.verifier.detect_project_type") as mock_detect:
            mock_detect.return_value = {
                "has_python": False, "has_node": False,
                "has_ruff": False, "has_mypy": False, "has_bandit": False,
                "has_eslint": False, "has_tsc": False, "has_prettier": False,
                "has_gitleaks": False, "has_codespell": False,
                "has_pip_audit": False, "has_npm": False, "has_pytest": False,
            }
            result = run_verify(fresh_db, "T01", tmp_path)

        assert "checks passed" in result["summary"]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TestModels:
    def test_check_result_defaults(self):
        r = CheckResult(name="test", passed=True)
        assert r.auto_fixable is False
        assert r.fix_cmd == ""
        assert r.skipped is False

    def test_verify_result_structure(self):
        r = VerifyResult(
            task_id="T01",
            checks=[CheckResult(name="lint", passed=True)],
            all_passed=True,
            summary="1/1 checks passed.",
        )
        d = r.model_dump()
        assert d["task_id"] == "T01"
        assert len(d["checks"]) == 1

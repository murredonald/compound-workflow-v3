"""Task-scoped verification pipeline.

Runs 13 quality checks scoped to a task's files, returning structured JSON
with auto_fixable flags and fix_cmd per check. Enables Claude to self-fix
issues in Step 4 (SELF-VERIFY) before review.

Complements pre-commit-gate.sh — the hook remains as a commit-time safety net.
"""

from __future__ import annotations

import json
import logging
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core import db
from core.models import ReflexionCategory, ReflexionEntry, WorkflowModel

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CheckResult(WorkflowModel):
    """Result of a single verification check."""

    name: str
    passed: bool
    output: str = ""
    auto_fixable: bool = False
    fix_cmd: str = ""
    fix_hint: str = ""
    skipped: bool = False
    skip_reason: str = ""


class VerifyResult(WorkflowModel):
    """Aggregated result of all checks for a task."""

    task_id: str
    checks: list[CheckResult]
    all_passed: bool = False
    auto_fixable_count: int = 0
    summary: str = ""


# ---------------------------------------------------------------------------
# Project detection
# ---------------------------------------------------------------------------

def detect_project_type(project_root: Path) -> dict[str, bool]:
    """Scan project root for config files and tool availability.

    Returns a dict of capabilities: has_python, has_node, has_ruff, etc.
    """
    return {
        "has_python": (project_root / "pyproject.toml").exists()
        or (project_root / "setup.py").exists()
        or (project_root / "requirements.txt").exists(),
        "has_node": (project_root / "package.json").exists(),
        "has_ruff": shutil.which("ruff") is not None,
        "has_mypy": shutil.which("mypy") is not None,
        "has_bandit": shutil.which("bandit") is not None,
        "has_eslint": shutil.which("eslint") is not None,
        "has_tsc": shutil.which("tsc") is not None,
        "has_prettier": shutil.which("prettier") is not None,
        "has_gitleaks": shutil.which("gitleaks") is not None,
        "has_codespell": shutil.which("codespell") is not None,
        "has_pip_audit": shutil.which("pip-audit") is not None,
        "has_npm": shutil.which("npm") is not None,
        "has_pytest": shutil.which("pytest") is not None,
    }


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _find_test_files(task_files: list[str], project_root: Path) -> list[str]:
    """Map source files to test files by convention.

    Tries multiple conventions:
      src/foo/bar.py → tests/foo/test_bar.py
      src/foo/bar.py → tests/test_bar.py
      foo/bar.py → tests/foo/test_bar.py
      foo/bar.py → tests/test_bar.py
    """
    test_files: list[str] = []
    seen: set[str] = set()

    for f in task_files:
        if not f.endswith(".py"):
            continue
        p = Path(f)
        stem = p.stem  # bar
        # Skip if this IS a test file
        if stem.startswith("test_"):
            candidate = project_root / f
            if candidate.exists() and f not in seen:
                test_files.append(f)
                seen.add(f)
            continue

        # Build candidate paths
        parts = list(p.parts)
        # Strip leading src/ if present
        if parts and parts[0] == "src":
            parts = parts[1:]

        candidates = []
        # tests/{subpath}/test_{stem}.py
        if len(parts) > 1:
            candidates.append(
                Path("tests", *parts[:-1], f"test_{stem}.py")
            )
        # tests/test_{stem}.py (flat)
        candidates.append(Path("tests", f"test_{stem}.py"))

        for c in candidates:
            full = project_root / c
            # Normalize to forward slashes for cross-platform consistency
            s = str(c).replace("\\", "/")
            if full.exists() and s not in seen:
                test_files.append(s)
                seen.add(s)

    return test_files


def _filter_by_ext(files: list[str], extensions: set[str]) -> list[str]:
    """Filter file list to only those matching given extensions."""
    return [f for f in files if Path(f).suffix in extensions]


# ---------------------------------------------------------------------------
# Pattern scanning (zero-dep checks)
# ---------------------------------------------------------------------------

# (regex_pattern, human_label)
DEBUG_PATTERNS: list[tuple[str, str]] = [
    (r'\bbreakpoint\s*\(', "breakpoint()"),
    (r'\bimport\s+pdb\b', "import pdb"),
    (r'\bpdb\.set_trace\s*\(', "pdb.set_trace()"),
    (r'\bconsole\.log\s*\(', "console.log()"),
    (r'\bdebugger\s*;', "debugger;"),
    (r'#\s*TODO\b', "# TODO"),
    (r'#\s*FIXME\b', "# FIXME"),
    (r'#\s*HACK\b', "# HACK"),
    (r'#\s*XXX\b', "# XXX"),
    (r'//\s*TODO\b', "// TODO"),
    (r'//\s*FIXME\b', "// FIXME"),
]

CONFLICT_PATTERNS: list[tuple[str, str]] = [
    (r'^<{7}\s', "conflict marker <<<<<<<"),
    (r'^={7}\s*$', "conflict marker ======="),
    (r'^>{7}\s', "conflict marker >>>>>>>"),
]

PLACEHOLDER_PATTERNS: list[tuple[str, str]] = [
    (r'^\s+pass\s*$', "bare pass"),
    (r'^\s+\.\.\.\s*$', "ellipsis placeholder"),
    (r'\braise\s+NotImplementedError\b', "NotImplementedError"),
]


# ---------------------------------------------------------------------------
# Check → ReflexionCategory mapping
# ---------------------------------------------------------------------------

# Maps each of the 13 check names to a ReflexionCategory value.
# Used by extract_verify_reflexion() to auto-categorise failures.
CHECK_CATEGORY_MAP: dict[str, str] = {
    "lint": ReflexionCategory.TYPE_MISMATCH.value,
    "format": ReflexionCategory.TYPE_MISMATCH.value,
    "spelling": ReflexionCategory.OTHER.value,
    "type-check": ReflexionCategory.TYPE_MISMATCH.value,
    "security": ReflexionCategory.ENV_CONFIG.value,
    "secrets": ReflexionCategory.ENV_CONFIG.value,
    "dep-audit": ReflexionCategory.DEPENDENCY.value,
    "tests": ReflexionCategory.EDGE_CASE_LOGIC.value,
    "data-validation": ReflexionCategory.OTHER.value,
    "task-verify": ReflexionCategory.API_CONTRACT.value,
    "debug-artifacts": ReflexionCategory.SCOPE_CREEP.value,
    "conflict-markers": ReflexionCategory.STATE_MANAGEMENT.value,
    "placeholders": ReflexionCategory.SCOPE_CREEP.value,
}

# Checks that warrant "high" severity (the rest default to "medium").
_HIGH_SEVERITY_CHECKS = frozenset({"security", "secrets", "tests"})


def _scan_files_for_patterns(
    files: list[str],
    patterns: list[tuple[str, str]],
    project_root: Path,
) -> list[str]:
    """Regex scan over file contents. Returns matches as '{file}:{line}: {label}'."""
    matches: list[str] = []
    compiled = [(re.compile(p), label) for p, label in patterns]

    for f in files:
        full = project_root / f
        if not full.exists() or not full.is_file():
            continue
        try:
            lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, 1):
            for regex, label in compiled:
                if regex.search(line):
                    matches.append(f"{f}:{line_no}: {label}")
                    break  # one match per line is enough

    return matches


def _validate_data_files(
    files: list[str],
    project_root: Path,
) -> list[str]:
    """Validate JSON/YAML files parse correctly."""
    errors: list[str] = []
    for f in files:
        full = project_root / f
        if not full.exists():
            continue

        suffix = Path(f).suffix.lower()
        if suffix == ".json":
            try:
                json.loads(full.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                errors.append(f"{f}: invalid JSON — {e}")
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml  # noqa: PLC0415

                yaml.safe_load(full.read_text(encoding="utf-8"))
            except ImportError:
                pass  # yaml not installed, skip
            except Exception as e:  # noqa: BLE001
                errors.append(f"{f}: invalid YAML — {e}")

    return errors


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------

def _run_check(
    name: str,
    cmd: list[str],
    cwd: Path,
    *,
    auto_fixable: bool = False,
    fix_cmd: str = "",
    fix_hint: str = "",
    timeout: int = 60,
) -> CheckResult:
    """Run a subprocess check and return structured result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        passed = result.returncode == 0
        output = (result.stdout + result.stderr).strip()
        # Truncate very long output
        if len(output) > 5000:
            output = output[:5000] + "\n... (truncated)"
        return CheckResult(
            name=name,
            passed=passed,
            output=output if not passed else "",
            auto_fixable=auto_fixable and not passed,
            fix_cmd=fix_cmd if not passed else "",
            fix_hint=fix_hint if not passed else "",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            passed=False,
            output=f"{name} timed out after {timeout}s",
            fix_hint=f"Check why {name} is slow. Consider increasing timeout or scoping to fewer files.",
        )
    except FileNotFoundError:
        return CheckResult(
            name=name,
            passed=True,
            skipped=True,
            skip_reason=f"Tool not found: {cmd[0]}",
        )


# ---------------------------------------------------------------------------
# Main verify entry point
# ---------------------------------------------------------------------------

def run_verify(
    conn: sqlite3.Connection,
    task_id: str,
    project_root: Path,
) -> dict[str, Any]:
    """Run all applicable checks for a task's files.

    Returns structured JSON matching the orchestrator's _out() contract.
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {
            "status": "error",
            "error": f"Task {task_id} not found",
            "fix_hint": "Check task ID format (T01, DF-01, QA-01). "
            "Use 'status' or 'next' to see available tasks.",
        }

    all_files = task.files_create + task.files_modify
    if not all_files:
        return {
            "status": "ok",
            "task_id": task_id,
            "all_passed": True,
            "checks": [],
            "summary": "No files in task — nothing to verify.",
        }

    py_files = _filter_by_ext(all_files, {".py"})
    js_ts_files = _filter_by_ext(all_files, {".js", ".ts", ".tsx", ".jsx"})
    data_files = _filter_by_ext(all_files, {".json", ".yaml", ".yml"})

    caps = detect_project_type(project_root)
    checks: list[CheckResult] = []

    # --- 1. Lint ---
    if py_files and caps["has_ruff"]:
        files_str = " ".join(py_files)
        checks.append(_run_check(
            "lint",
            ["ruff", "check", *py_files],
            project_root,
            auto_fixable=True,
            fix_cmd=f"ruff check --fix {files_str}",
            fix_hint="Run the fix_cmd to auto-fix lint issues, then re-verify.",
        ))
    elif js_ts_files and caps["has_eslint"]:
        files_str = " ".join(js_ts_files)
        checks.append(_run_check(
            "lint",
            ["eslint", *js_ts_files],
            project_root,
            auto_fixable=True,
            fix_cmd=f"eslint --fix {files_str}",
            fix_hint="Run the fix_cmd to auto-fix lint issues, then re-verify.",
        ))

    # --- 2. Format ---
    if py_files and caps["has_ruff"]:
        files_str = " ".join(py_files)
        checks.append(_run_check(
            "format",
            ["ruff", "format", "--check", *py_files],
            project_root,
            auto_fixable=True,
            fix_cmd=f"ruff format {files_str}",
            fix_hint="Run the fix_cmd to auto-format, then re-verify.",
        ))
    elif js_ts_files and caps.get("has_prettier"):
        files_str = " ".join(js_ts_files)
        checks.append(_run_check(
            "format",
            ["prettier", "--check", *js_ts_files],
            project_root,
            auto_fixable=True,
            fix_cmd=f"prettier --write {files_str}",
            fix_hint="Run the fix_cmd to auto-format, then re-verify.",
        ))

    # --- 3. Spelling ---
    if caps["has_codespell"] and all_files:
        files_str = " ".join(all_files)
        checks.append(_run_check(
            "spelling",
            ["codespell", *all_files],
            project_root,
            auto_fixable=True,
            fix_cmd=f"codespell --write-changes {files_str}",
            fix_hint="Run the fix_cmd to auto-fix typos, then re-verify.",
        ))

    # --- 4. Type check ---
    if py_files and caps["has_mypy"]:
        checks.append(_run_check(
            "type-check",
            ["mypy", *py_files],
            project_root,
            fix_hint="Fix type errors shown in the output. Common fixes: add type annotations, fix argument types, handle Optional values.",
        ))
    elif js_ts_files and caps["has_tsc"]:
        checks.append(_run_check(
            "type-check",
            ["tsc", "--noEmit"],
            project_root,
            fix_hint="Fix TypeScript type errors shown in the output.",
        ))

    # --- 5. Security scan ---
    if py_files and caps["has_bandit"]:
        checks.append(_run_check(
            "security",
            ["bandit", "-r", *py_files],
            project_root,
            fix_hint="Fix security issues flagged by bandit. See https://bandit.readthedocs.io for explanations.",
        ))

    # --- 6. Secret scan ---
    if caps["has_gitleaks"]:
        checks.append(_run_check(
            "secrets",
            ["gitleaks", "detect", "--no-git", "--source", str(project_root)],
            project_root,
            fix_hint="Remove hardcoded secrets/credentials. Use environment variables or .env files instead.",
        ))

    # --- 7. Dependency audit ---
    if caps["has_python"] and caps["has_pip_audit"]:
        checks.append(_run_check(
            "dep-audit",
            ["pip-audit"],
            project_root,
            fix_hint="Update vulnerable dependencies. Run 'pip install --upgrade <package>'.",
            timeout=120,
        ))
    elif caps["has_node"] and caps["has_npm"]:
        checks.append(_run_check(
            "dep-audit",
            ["npm", "audit", "--audit-level=moderate"],
            project_root,
            fix_hint="Run 'npm audit fix' to resolve dependency vulnerabilities.",
            timeout=120,
        ))

    # --- 8. Tests (scoped) ---
    test_files = _find_test_files(all_files, project_root)
    if test_files and caps.get("has_pytest"):
        checks.append(_run_check(
            "tests",
            ["pytest", *test_files, "-v", "--tb=short"],
            project_root,
            fix_hint="Fix failing tests. Read the assertion errors and tracebacks in the output.",
            timeout=120,
        ))

    # --- 9. JSON/YAML validation ---
    if data_files:
        errors = _validate_data_files(data_files, project_root)
        checks.append(CheckResult(
            name="data-validation",
            passed=len(errors) == 0,
            output="\n".join(errors) if errors else "",
            fix_hint="Fix JSON/YAML syntax errors. Check for missing commas, unquoted keys, trailing commas." if errors else "",
        ))

    # --- 10. Task verification_cmd ---
    if task.verification_cmd:
        # Split command for subprocess (shell=False is safer)
        cmd_parts = shlex.split(task.verification_cmd)
        checks.append(_run_check(
            "task-verify",
            cmd_parts,
            project_root,
            fix_hint=f"Task verification command failed: {task.verification_cmd}. Fix the code to satisfy the verification.",
            timeout=120,
        ))

    # --- 11. Debug artifacts ---
    debug_matches = _scan_files_for_patterns(all_files, DEBUG_PATTERNS, project_root)
    checks.append(CheckResult(
        name="debug-artifacts",
        passed=len(debug_matches) == 0,
        output="\n".join(debug_matches) if debug_matches else "",
        fix_hint="Remove debug statements, breakpoints, and TODO/FIXME comments before review." if debug_matches else "",
    ))

    # --- 12. Conflict markers ---
    conflict_matches = _scan_files_for_patterns(all_files, CONFLICT_PATTERNS, project_root)
    checks.append(CheckResult(
        name="conflict-markers",
        passed=len(conflict_matches) == 0,
        output="\n".join(conflict_matches) if conflict_matches else "",
        fix_hint="Resolve merge conflict markers in the listed files." if conflict_matches else "",
    ))

    # --- 13. Placeholder detector ---
    placeholder_matches = _scan_files_for_patterns(
        py_files + js_ts_files, PLACEHOLDER_PATTERNS, project_root,
    )
    checks.append(CheckResult(
        name="placeholders",
        passed=len(placeholder_matches) == 0,
        output="\n".join(placeholder_matches) if placeholder_matches else "",
        fix_hint="Replace placeholder stubs (pass, ..., NotImplementedError) with real implementation." if placeholder_matches else "",
    ))

    # --- Build result ---
    all_passed = all(c.passed or c.skipped for c in checks)
    auto_fixable_count = sum(1 for c in checks if c.auto_fixable)
    passed_count = sum(1 for c in checks if c.passed)
    skipped_count = sum(1 for c in checks if c.skipped)
    total = len(checks)

    parts = [f"{passed_count}/{total} checks passed"]
    if skipped_count:
        parts.append(f"{skipped_count} skipped")
    if auto_fixable_count:
        parts.append(f"{auto_fixable_count} auto-fixable")

    result = VerifyResult(
        task_id=task_id,
        checks=checks,
        all_passed=all_passed,
        auto_fixable_count=auto_fixable_count,
        summary=". ".join(parts) + ".",
    )

    return {
        "status": "ok" if all_passed else "fail",
        **result.model_dump(),
    }


# ---------------------------------------------------------------------------
# Verify reflexion — learn from recurring failures
# ---------------------------------------------------------------------------

def extract_verify_reflexion(
    task_id: str,
    verify_result: dict[str, Any],
    task_files: list[str],
) -> list[dict[str, Any]]:
    """Extract reflexion entries from verify failures.

    Returns a list of reflexion entry dicts (without ``id`` — caller assigns).
    Only creates entries for deterministic failures (not skipped checks).
    """
    entries: list[dict[str, Any]] = []

    for check in verify_result.get("checks", []):
        # Skip passed, skipped
        if check.get("passed", False) or check.get("skipped", False):
            continue

        name = check.get("name", "unknown")
        output = check.get("output", "")
        fix_hint = check.get("fix_hint", "")

        category = CHECK_CATEGORY_MAP.get(name, ReflexionCategory.OTHER.value)
        severity = "high" if name in _HIGH_SEVERITY_CHECKS else "medium"

        # Truncate output for the reflexion entry (keep it compact)
        truncated_output = output[:300] + "..." if len(output) > 300 else output

        entries.append({
            "task_id": task_id,
            "tags": [*task_files, name],
            "category": category,
            "severity": severity,
            "what_happened": f"Verify check '{name}' failed: {truncated_output}",
            "root_cause": fix_hint or f"Check '{name}' detected issues in task files.",
            "lesson": f"Run '{name}' checks before review. {fix_hint}".strip(),
            "applies_to": task_files,
            "preventive_action": fix_hint or f"Ensure '{name}' passes before proceeding.",
        })

    return entries


def verify_and_reflect(
    conn: sqlite3.Connection,
    task_id: str,
    project_root: Path,
) -> dict[str, Any]:
    """Run verify + auto-record reflexion entries for failures.

    Combines ``run_verify()`` + ``extract_verify_reflexion()`` + DB storage.
    Returns the verify result enriched with reflexion metadata.
    """
    result = run_verify(conn, task_id, project_root)

    # Error cases pass through unchanged
    if result.get("status") == "error":
        return result

    # All passed — nothing to reflect on
    if result.get("all_passed", False):
        result["reflexion_entries"] = []
        result["systemic_issues"] = []
        return result

    # Get task files for tagging
    task = db.get_task(conn, task_id)
    task_files = (task.files_create + task.files_modify) if task else []

    # Extract and store reflexion entries
    raw_entries = extract_verify_reflexion(task_id, result, task_files)
    stored_entries: list[dict[str, Any]] = []

    for entry_dict in raw_entries:
        entry_id = db.next_reflexion_id(conn)
        entry = ReflexionEntry(id=entry_id, **entry_dict)
        db.store_reflexion_entry(conn, entry)
        stored_entries.append(entry.model_dump())

    # Check for systemic patterns
    patterns = db.get_reflexion_patterns(conn)
    systemic = patterns.get("systemic_issues", [])

    result["reflexion_entries"] = stored_entries
    result["systemic_issues"] = systemic
    return result

"""Decomposer — per-task decomposition into granular subtasks.

Pipeline (mirrors synthesizer.py):

  1. DETERMINISTIC: Build focused context for one parent task (decisions, artifacts)
  2. DETERMINISTIC: Render decompose prompt template with context injected
  3. LLM: Opus generates subtasks as structured JSON
  4. DETERMINISTIC: Parse + Pydantic-validate LLM output
  5. DETERMINISTIC: Run integrity checks (coverage, artifacts, deps)
  6. DETERMINISTIC: If invalid, build retry prompt with specific errors → goto 3
  7. DETERMINISTIC: Convert DecomposedTask → Task, replace parent, rewire deps
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

from core import db
from core.models import ArtifactType, DecomposedTask, Task, TaskStatus
from engine import MAX_RETRY_CYCLES
from engine.composer import load_prompt
from engine.renderer import render
from engine.validator import ValidationResult

# ---------------------------------------------------------------------------
# Deterministic artifact inference from decision prefixes
# ---------------------------------------------------------------------------

TASK_ARTIFACT_RULES: dict[str, list[str]] = {
    "STYLE": ["style-guide", "brand-guide"],
    "BRAND": ["brand-guide"],
    "FRONT": ["style-guide", "brand-guide"],
    "UIX": ["style-guide"],
    "COMP": ["competition-analysis"],
    "DOM": ["domain-knowledge"],
}


def infer_artifact_refs(
    decision_refs: list[str],
    available_artifacts: list[str],
) -> list[str]:
    """Infer artifact references from decision prefixes.

    Uses TASK_ARTIFACT_RULES to map decision prefixes to artifacts,
    then filters to only those actually available in the DB.
    """
    inferred: set[str] = set()
    for ref in decision_refs:
        prefix = ref.split("-")[0]
        for art in TASK_ARTIFACT_RULES.get(prefix, []):
            if art in available_artifacts:
                inferred.add(art)
    return sorted(inferred)


# ---------------------------------------------------------------------------
# Step 1+2: Build the decompose prompt for one parent task
# ---------------------------------------------------------------------------

def build_decompose_prompt(conn: sqlite3.Connection, task_id: str) -> str:
    """Compose focused context for one parent task and render the prompt.

    Context includes:
    - Parent task definition
    - Full text of referenced decisions
    - Full text of inferred artifacts
    - Project summary
    - Compact decision index (ID+title, for gap detection)
    - Constraints
    - Available artifacts list
    """
    task = db.get_task(conn, task_id)
    if not task:
        return f"ERROR: Task {task_id} not found"

    pipeline = db.get_pipeline(conn)

    # Fetch full decision text for referenced decisions
    prefixes = list({ref.split("-")[0] for ref in task.decision_refs})
    if prefixes:
        all_relevant = db.get_decisions(conn, prefixes=prefixes)
        decision_map = {d.id: d for d in all_relevant}
        referenced_decisions = [
            decision_map[ref]
            for ref in task.decision_refs
            if ref in decision_map
        ]
    else:
        referenced_decisions = []

    # Infer artifacts from decision refs
    available = [a["type"] for a in db.list_artifacts(conn)]
    inferred_arts = infer_artifact_refs(task.decision_refs, available)

    # Also include any existing artifact_refs on the task
    all_art_refs = sorted(set(inferred_arts) | set(task.artifact_refs))

    # Load artifact content
    artifacts: dict[str, str] = {}
    for art_type in all_art_refs:
        content = db.get_artifact(conn, art_type)
        if content:
            artifacts[art_type] = content

    # Build compact decision index (ALL decisions, ID+title only)
    all_decisions = db.get_decisions(conn)
    decision_index: dict[str, list[dict[str, str]]] = {}
    for d in all_decisions:
        decision_index.setdefault(d.prefix.value, []).append(
            {"id": d.id, "title": d.title}
        )

    constraints = db.get_constraints(conn)

    # Load template
    template = load_prompt("decompose")

    render_ctx: dict[str, Any] = {
        "project_name": pipeline.project_name,
        "project_summary": pipeline.project_summary,
        "task": task.model_dump(),
        "decisions": [d.model_dump() for d in referenced_decisions],
        "constraints": [c.model_dump() for c in constraints],
        "artifacts": artifacts,
        "decision_index": decision_index,
        "available_artifacts": available,
        "DECOMPOSE_SCHEMA": True,
    }

    return render(template, render_ctx)


# ---------------------------------------------------------------------------
# Step 4: Parse LLM output into DecomposedTask objects
# ---------------------------------------------------------------------------

def parse_decompose_output(
    raw_json: str,
    parent_task_id: str,
    parent_milestone: str = "",
) -> tuple[list[DecomposedTask], list[dict[str, Any]], list[str]]:
    """Parse LLM-generated JSON into validated DecomposedTask objects.

    Args:
        raw_json: Raw LLM JSON output.
        parent_task_id: ID of the parent task being decomposed.
        parent_milestone: Milestone of the parent task (auto-injected into
            subtasks that omit it).

    Returns:
        (subtasks, missing_decisions, parse_errors)
    """
    errors: list[str] = []

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [], [], [f"Invalid JSON at line {e.lineno} col {e.colno}: {e.msg}"]

    if not isinstance(data, dict):
        return [], [], ["Expected a JSON object with 'subtasks' key"]

    # Parse subtasks
    subtasks: list[DecomposedTask] = []
    raw_subtasks = data.get("subtasks", [])
    if not isinstance(raw_subtasks, list):
        errors.append("'subtasks' must be an array")
        raw_subtasks = []

    for i, item in enumerate(raw_subtasks):
        # Auto-inject parent_task and milestone if missing
        if isinstance(item, dict):
            item.setdefault("parent_task", parent_task_id)
            if parent_milestone:
                item.setdefault("milestone", parent_milestone)
        try:
            subtasks.append(DecomposedTask(**item))
        except (ValueError, TypeError) as e:
            errors.append(f"Subtask {i}: {e}")

    if not subtasks and not errors:
        errors.append("No subtasks generated — subtasks array is empty")

    # Parse missing_decisions (informational, not validated as models)
    missing_decisions: list[dict[str, Any]] = []
    raw_missing = data.get("missing_decisions", [])
    if isinstance(raw_missing, list):
        for item in raw_missing:
            if isinstance(item, dict):
                missing_decisions.append(item)

    return subtasks, missing_decisions, errors


# ---------------------------------------------------------------------------
# Step 5: Validate the decompose output
# ---------------------------------------------------------------------------

def validate_decompose_output(
    subtasks: list[DecomposedTask],
    parent_task: Task,
    all_decisions: list[Any],
) -> ValidationResult:
    """Run integrity checks on decomposed subtasks.

    Checks (9 total):
    1. Subtask IDs match T{parent}.{N} pattern
    2. No duplicate IDs
    3. Sequential numbering within parent (1..N)
    4. Every parent decision_ref covered by at least one subtask
    5. All subtask decision_refs exist in DB
    6. depends_on references valid subtask IDs or known task IDs
    7. artifact_refs values are valid ArtifactType strings
    8. Every subtask has goal, acceptance_criteria, file lists
    9. Union of subtask files covers parent file lists
    """
    result = ValidationResult()
    parent_num = parent_task.id.removeprefix("T")

    # 1. ID format check
    for st in subtasks:
        if not st.id.startswith(f"T{parent_num}."):
            result.add_error(
                f"Subtask {st.id} doesn't match parent {parent_task.id} "
                f"(expected T{parent_num}.N)"
            )

    # 2. No duplicate IDs
    seen_ids: set[str] = set()
    for st in subtasks:
        if st.id in seen_ids:
            result.add_error(f"Duplicate subtask ID: {st.id}")
        seen_ids.add(st.id)

    # 3. Sequential numbering
    numbers: list[int] = []
    for st in subtasks:
        parts = st.id.split(".")
        if len(parts) == 2 and parts[1].isdigit():
            numbers.append(int(parts[1]))
    if numbers:
        expected = list(range(1, len(numbers) + 1))
        if sorted(numbers) != expected:
            result.add_warning(
                f"Subtask numbering not sequential: got {sorted(numbers)}, "
                f"expected {expected}"
            )

    # 4. Parent decision coverage
    parent_refs = set(parent_task.decision_refs)
    covered_refs: set[str] = set()
    for st in subtasks:
        covered_refs.update(st.decision_refs)
    uncovered = parent_refs - covered_refs
    if uncovered:
        result.add_error(
            f"Parent decisions not covered by any subtask: {sorted(uncovered)}"
        )

    # 5. Decision refs exist
    decision_ids = {d.id for d in all_decisions}
    for st in subtasks:
        for ref in st.decision_refs:
            if ref not in decision_ids:
                result.add_warning(
                    f"Subtask {st.id} references unknown decision '{ref}'"
                )

    # 6. Dependency references valid
    valid_ids = seen_ids  # subtask IDs are valid dep targets
    for st in subtasks:
        for dep in st.depends_on:
            if dep not in valid_ids:
                result.add_warning(
                    f"Subtask {st.id} depends on '{dep}' which is not a "
                    f"subtask of {parent_task.id}"
                )
            if dep == st.id:
                result.add_error(f"Subtask {st.id} depends on itself")

    # 7. Artifact refs valid
    valid_arts = {t.value for t in ArtifactType}
    for st in subtasks:
        for ref in st.artifact_refs:
            if ref not in valid_arts:
                result.add_error(
                    f"Subtask {st.id} has unknown artifact_ref '{ref}'"
                )

    # 8. Completeness
    for st in subtasks:
        if not st.goal:
            result.add_warning(f"Subtask {st.id} has no goal")
        if not st.acceptance_criteria:
            result.add_warning(f"Subtask {st.id} has no acceptance criteria")
        if not st.files_create and not st.files_modify:
            result.add_warning(f"Subtask {st.id} has no file lists")

    # 9. File coverage
    parent_files = set(parent_task.files_create + parent_task.files_modify)
    subtask_files: set[str] = set()
    for st in subtasks:
        subtask_files.update(st.files_create)
        subtask_files.update(st.files_modify)
    uncovered_files = parent_files - subtask_files
    if uncovered_files:
        result.add_warning(
            f"Parent files not covered by subtasks: {sorted(uncovered_files)}"
        )

    return result


# ---------------------------------------------------------------------------
# Step 6: Build retry prompt
# ---------------------------------------------------------------------------

def build_decompose_retry_prompt(
    original_prompt: str,
    llm_output: str,
    result: ValidationResult,
    cycle: int,
) -> str:
    """Build a retry prompt with specific validation errors."""
    error_section = "\n".join(f"  - ERROR: {e}" for e in result.errors)
    warning_section = "\n".join(f"  - WARNING: {w}" for w in result.warnings)

    return f"""## Retry {cycle}/{MAX_RETRY_CYCLES} — Fix validation errors

Your previous subtask decomposition had validation failures. Fix the issues
below and regenerate the complete JSON output.

### Errors (must fix):
{error_section or '  (none)'}

### Warnings (should fix):
{warning_section or '  (none)'}

### Your previous output:
```json
{llm_output}
```

### Rules reminder:
- Subtask IDs must be T{{parent}}.1, T{{parent}}.2, etc. (sequential)
- Every parent decision_ref must be covered by at least one subtask
- All decision_refs must reference existing decisions
- Dependencies must reference valid subtask IDs
- Every subtask needs: goal, acceptance_criteria, file lists
- artifact_refs must be valid artifact types

Output the corrected complete JSON:
"""


# ---------------------------------------------------------------------------
# Step 7: Convert DecomposedTask → Task
# ---------------------------------------------------------------------------

def subtasks_to_tasks(subtasks: list[DecomposedTask]) -> list[Task]:
    """Convert DecomposedTask instances to Task instances for DB storage."""
    tasks: list[Task] = []
    for st in subtasks:
        tasks.append(Task(
            id=st.id,
            title=st.title,
            milestone=st.milestone,
            status=TaskStatus.PENDING,
            goal=st.goal,
            depends_on=st.depends_on,
            decision_refs=st.decision_refs,
            artifact_refs=st.artifact_refs,
            parent_task=st.parent_task,
            files_create=st.files_create,
            files_modify=st.files_modify,
            acceptance_criteria=st.acceptance_criteria,
            verification_cmd=st.verification_cmd,
        ))
    return tasks


# ---------------------------------------------------------------------------
# Full pipeline: parse + validate + return result
# ---------------------------------------------------------------------------

def run_decompose_for_task(
    conn: sqlite3.Connection,
    task_id: str,
    llm_output_json: str,
) -> dict[str, Any]:
    """Run the full post-LLM decompose pipeline for one task.

    Takes raw LLM JSON output and:
    1. Parses into DecomposedTask objects
    2. Validates against parent task and DB state
    3. Returns result with subtasks or errors
    """
    parent = db.get_task(conn, task_id)
    if not parent:
        return {
            "status": "error",
            "errors": [f"Parent task {task_id} not found"],
            "subtasks": [],
        }

    # Parse
    subtasks, missing_decisions, parse_errors = parse_decompose_output(
        llm_output_json, task_id, parent_milestone=parent.milestone
    )
    if parse_errors:
        return {
            "status": "parse_error",
            "errors": parse_errors,
            "subtasks": [],
            "missing_decisions": [],
        }

    # Validate
    all_decisions = db.get_decisions(conn)
    result = validate_decompose_output(subtasks, parent, all_decisions)

    return {
        "status": "valid" if result.valid else "invalid",
        "errors": result.errors,
        "warnings": result.warnings,
        "subtasks": [st.model_dump() for st in subtasks],
        "missing_decisions": missing_decisions,
        "subtask_count": len(subtasks),
    }


# ---------------------------------------------------------------------------
# Step 8: Store decomposed tasks (replace parent, rewire deps)
# ---------------------------------------------------------------------------

def store_decomposed_tasks(
    conn: sqlite3.Connection,
    parent_id: str,
    subtasks: list[DecomposedTask],
) -> dict[str, Any]:
    """Replace parent task with its subtasks and rewire dependencies.

    1. Delete the parent task from DB
    2. Store all subtasks as Task objects
    3. Rewire any task that depends on parent_id to depend on the last subtask

    All three operations run in a single transaction (the outer `with conn:`
    ensures atomicity — inner `with conn:` calls in db.* are no-ops).

    Returns a summary of what was done.
    """
    if not subtasks:
        return {"error": "No subtasks provided", "parent_id": parent_id}

    # Convert to Task objects
    tasks = subtasks_to_tasks(subtasks)

    # Find the last subtask (highest number) for dependency rewiring
    last_subtask_id = tasks[-1].id

    # Atomic: delete + rewire + store in one transaction
    with conn:
        db.delete_task(conn, parent_id)
        db.rewire_task_deps(conn, old_dep=parent_id, new_dep=last_subtask_id)
        stored = db.store_tasks(conn, tasks)

    return {
        "parent_deleted": parent_id,
        "subtasks_stored": stored,
        "last_subtask": last_subtask_id,
        "deps_rewired_to": last_subtask_id,
    }

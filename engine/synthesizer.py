"""Synthesizer — hybrid deterministic + LLM task generation.

Replaces the toy taskmaker.py with a proper pipeline:

  1. DETERMINISTIC: Compose structured context from DB (all decisions, constraints)
  2. DETERMINISTIC: Render synthesize prompt template with context injected
  3. LLM: Claude generates tasks as structured JSON (this module provides the prompt)
  4. DETERMINISTIC: Parse + Pydantic-validate LLM output
  5. DETERMINISTIC: Run integrity checks (coverage, cycles, deps, milestones)
  6. DETERMINISTIC: If invalid, build retry prompt with specific errors → goto 3

The LLM call itself happens outside this module (Claude Code does it).
This module handles everything around it: context composition, prompt rendering,
output parsing, validation, and retry feedback.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

from core import db
from core.models import Decision, Milestone, Task
from engine import MAX_RETRY_CYCLES
from engine.composer import compose_synthesize_context, load_prompt
from engine.renderer import render
from engine.validator import ValidationResult, validate_task_queue


# ---------------------------------------------------------------------------
# Step 1+2: Build the synthesize prompt (context + template)
# ---------------------------------------------------------------------------

def build_synthesize_prompt(conn: sqlite3.Connection) -> str:
    """Compose full context from DB and render into synthesize prompt template.

    Returns a ready-to-use prompt string with all decisions, constraints,
    milestones, and output schema injected.
    """
    # Get structured context from DB
    ctx = compose_synthesize_context(conn)

    # Load the synthesize prompt template
    template = load_prompt("synthesize")
    if not template:
        raise FileNotFoundError("Prompt template 'synthesize.md' not found")

    # Build the render context
    render_ctx = {
        "project_name": ctx["project_name"],
        "decisions_by_prefix": ctx.get("decisions_by_prefix", {}),
        "decisions": ctx.get("decisions", []),
        "constraints": ctx.get("constraints", []),
        "decision_count": ctx.get("decision_count", 0),
        "completed_phases": ctx.get("completed_phases", []),
        "milestones": ctx.get("milestones", []),
        "TASK_SCHEMA": True,  # triggers schema insertion
    }

    return render(template, render_ctx)


# ---------------------------------------------------------------------------
# Step 4: Parse LLM output into validated objects
# ---------------------------------------------------------------------------

def parse_llm_output(raw_json: str) -> tuple[list[Task], list[Milestone], list[str]]:
    """Parse LLM-generated JSON into validated Task and Milestone objects.

    The LLM is expected to output:
    {
      "milestones": [...],
      "tasks": [...]
    }

    Returns:
        (tasks, milestones, parse_errors)
    """
    errors: list[str] = []

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [], [], [f"Invalid JSON at line {e.lineno} col {e.colno}: {e.msg}"]

    if not isinstance(data, dict):
        return [], [], ["Expected a JSON object with 'milestones' and 'tasks' keys"]

    # Parse milestones
    milestones: list[Milestone] = []
    raw_milestones = data.get("milestones", [])
    if not isinstance(raw_milestones, list):
        errors.append("'milestones' must be an array")
        raw_milestones = []

    for i, item in enumerate(raw_milestones):
        try:
            milestones.append(Milestone(**item))
        except (ValueError, TypeError) as e:
            errors.append(f"Milestone {i}: {e}")

    # Parse tasks
    tasks: list[Task] = []
    raw_tasks = data.get("tasks", [])
    if not isinstance(raw_tasks, list):
        errors.append("'tasks' must be an array")
        raw_tasks = []

    for i, item in enumerate(raw_tasks):
        try:
            tasks.append(Task(**item))
        except (ValueError, TypeError) as e:
            errors.append(f"Task {i}: {e}")

    if not tasks and not errors:
        errors.append("No tasks generated — task array is empty")

    return tasks, milestones, errors


# ---------------------------------------------------------------------------
# Step 5: Validate the generated task queue
# ---------------------------------------------------------------------------

def validate_output(
    tasks: list[Task],
    milestones: list[Milestone],
    decisions: list[Decision],
) -> ValidationResult:
    """Run full integrity checks on the generated task queue.

    This is the deterministic guardrail that catches LLM mistakes:
    - Missing decision coverage
    - Circular dependencies
    - Invalid milestone references
    - Missing acceptance criteria
    - etc.
    """
    return validate_task_queue(tasks, milestones, decisions)


# ---------------------------------------------------------------------------
# Step 6: Build retry prompt if validation failed
# ---------------------------------------------------------------------------

def build_retry_prompt(
    original_prompt: str,
    llm_output: str,
    result: ValidationResult,
    cycle: int,
) -> str:
    """Build a retry prompt with specific validation errors.

    The LLM gets:
    1. The original synthesize prompt (for context)
    2. Its previous output
    3. The specific errors/warnings it needs to fix
    4. Which retry cycle this is

    Returns the complete retry prompt.
    """
    error_section = "\n".join(f"  - ERROR: {e}" for e in result.errors)
    warning_section = "\n".join(f"  - WARNING: {w}" for w in result.warnings)

    return f"""## Retry {cycle}/{MAX_RETRY_CYCLES} — Fix validation errors

Your previous task queue output had validation failures. Fix the issues below
and regenerate the complete JSON output.

### Errors (must fix):
{error_section or '  (none)'}

### Warnings (should fix):
{warning_section or '  (none)'}

### Your previous output:
```json
{llm_output}
```

### Rules reminder:
- Every non-GEN decision must be covered by at least one task
- No circular dependencies
- All dependency targets must be valid task IDs
- All milestone references must be valid
- Every task needs: goal, acceptance_criteria, decision_refs, file lists
- Task IDs must be sequential: T01, T02, T03, ...

Output the corrected complete JSON (milestones + tasks):
"""


# ---------------------------------------------------------------------------
# Full synthesize pipeline (for programmatic use / testing)
# ---------------------------------------------------------------------------

def run_synthesize(
    conn: sqlite3.Connection,
    llm_output_json: str,
) -> dict[str, Any]:
    """Run the full post-LLM synthesize pipeline.

    Takes the raw LLM JSON output and:
    1. Parses it into Pydantic objects
    2. Validates integrity
    3. Returns result with tasks or errors

    This is what the orchestrator's validate-tasks command calls.
    """
    # Parse
    tasks, milestones, parse_errors = parse_llm_output(llm_output_json)
    if parse_errors:
        return {
            "status": "parse_error",
            "errors": parse_errors,
            "tasks": [],
            "milestones": [],
        }

    # Validate against DB state
    decisions = db.get_decisions(conn)
    result = validate_output(tasks, milestones, decisions)

    return {
        "status": "valid" if result.valid else "invalid",
        "errors": result.errors,
        "warnings": result.warnings,
        "tasks": [t.model_dump() for t in tasks],
        "milestones": [m.model_dump() for m in milestones],
        "task_count": len(tasks),
        "milestone_count": len(milestones),
    }


def store_validated_tasks(
    conn: sqlite3.Connection,
    tasks: list[Task],
    milestones: list[Milestone],
) -> dict[str, int]:
    """Store validated tasks and milestones to DB.

    Only call this after validation passes.
    """
    m_count = db.store_milestones(conn, milestones)
    t_count = db.store_tasks(conn, tasks)
    return {"milestones_stored": m_count, "tasks_stored": t_count}

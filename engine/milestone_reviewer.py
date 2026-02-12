"""Milestone review — prompt composition for milestone boundary review.

Compiles task evals, scope drift, deferred findings, review highlights,
and file contents into a comprehensive review prompt for a milestone
reviewer subagent.

This catches integration issues, incomplete tasks, and accumulated debt
before the next milestone begins.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field

from core import db
from core.models import (
    MAX_TEXT_LENGTH,
    Severity,
    TaskStatus,
    WorkflowModel,
)
from engine.pre_reviewer import _read_file_contents
from engine.reviewer import get_milestone_progress

if TYPE_CHECKING:
    import sqlite3


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILES_PER_MILESTONE = 20


# ---------------------------------------------------------------------------
# Models (schema-only — for LLM output reference, not stored in DB)
# ---------------------------------------------------------------------------

class MilestoneReviewFinding(WorkflowModel):
    """A single finding from the milestone reviewer LLM."""

    severity: Severity
    category: str = Field(
        min_length=1,
        description="One of: completeness, quality, scope, integration, debt",
    )
    description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    task_ref: str = ""
    fix_description: str = ""


class MilestoneReviewResult(WorkflowModel):
    """Structured output expected from the milestone reviewer LLM.

    Included in the prompt as a JSON schema reference so the LLM knows
    exactly what structure to return.
    """

    verdict: str = Field(
        description="One of: milestone_complete, fixable, blocked",
    )
    findings: list[MilestoneReviewFinding] = Field(default_factory=list)
    task_assessment: dict[str, str] = Field(default_factory=dict)
    summary: str = ""


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_MILESTONE_REVIEW_PROMPT = """\
You are a milestone reviewer. Assess whether this milestone is complete, \
high-quality, and ready for the next phase. Be concise — only flag real issues.

## Milestone: {milestone_id} — {milestone_name}

### Goal

{milestone_goal}

### Progress

{progress_block}

### Task Summary

{tasks_block}

### Task Evals

{evals_block}

### Deferred Findings

{deferred_block}

### Review History

{reviews_block}

### File Contents

{files_block}

## Instructions

Assess this milestone across 6 dimensions:

1. **Completeness**: Are all tasks done? Any blocked? Any criteria unmet?
2. **Criteria compliance**: Check acceptance criteria across tasks.
3. **Scope discipline**: Note any scope violations from task evals.
4. **Deferred debt**: Are deferred findings acceptable or risky?
5. **Code quality**: Review cycle counts, recurring findings across tasks.
6. **Integration risk**: Cross-task dependencies, shared files, potential conflicts.

## Output Format

Return a JSON object:

```json
{{
  "verdict": "milestone_complete|fixable|blocked",
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "completeness|quality|scope|integration|debt",
      "description": "what is wrong",
      "task_ref": "T01 (if applicable)",
      "fix_description": "what to do"
    }}
  ],
  "task_assessment": {{
    "T01": "complete — all criteria met",
    "T02": "complete — 2 review cycles, lint issues"
  }},
  "summary": "1-2 sentence overview"
}}
```

If everything looks good, return verdict "milestone_complete" with empty findings.\
"""


# ---------------------------------------------------------------------------
# Main composition
# ---------------------------------------------------------------------------

def compose_milestone_review(
    conn: sqlite3.Connection,
    milestone_id: str,
    project_root: Path,
) -> dict[str, Any]:
    """Build comprehensive milestone review context with file contents.

    Returns structured context + rendered prompt for an LLM to review.
    The ``review_prompt`` field is the full prompt string to delegate to
    a Sonnet subagent via the Task tool.
    """
    # Find the milestone
    milestones = db.get_milestones(conn)
    milestone = None
    for m in milestones:
        if m.id == milestone_id:
            milestone = m
            break

    if not milestone:
        return {
            "status": "error",
            "error": f"Milestone {milestone_id} not found",
            "fix_hint": "Check milestone ID format (M1, M2). "
            "Use 'status' to see available milestones.",
        }

    # Get all tasks in this milestone
    tasks = db.get_tasks(conn, milestone=milestone_id)

    # Get progress
    progress = get_milestone_progress(conn, milestone_id)

    # Get task evals
    evals = db.get_task_evals(conn, milestone=milestone_id)
    eval_map = {e.task_id: e for e in evals}

    # Get deferred findings from this milestone's tasks
    task_ids = {t.id for t in tasks}
    all_deferred = db.get_deferred_findings(conn)
    milestone_deferred = [
        d for d in all_deferred if d.discovered_in in task_ids
    ]

    # Get review results for all tasks (latest cycle summary)
    review_summaries: list[str] = []
    for t in tasks:
        reviews = db.get_review_results(conn, t.id)
        if reviews:
            latest = max(reviews, key=lambda r: r.cycle)
            finding_count = len(latest.findings)
            review_summaries.append(
                f"- {t.id}: cycle {latest.cycle}, "
                f"verdict={latest.verdict.value}, "
                f"{finding_count} findings"
            )

    # Collect all files from all tasks (deduplicated), limit to MAX_FILES
    all_files: list[str] = []
    seen_files: set[str] = set()
    for t in tasks:
        for f in t.files_create + t.files_modify:
            if f not in seen_files:
                all_files.append(f)
                seen_files.add(f)
    # Truncate if too many files
    truncated = len(all_files) > MAX_FILES_PER_MILESTONE
    if truncated:
        all_files = all_files[:MAX_FILES_PER_MILESTONE]

    # Read file contents
    file_contents = _read_file_contents(all_files, project_root)

    # --- Format blocks ---

    # Progress
    progress_block = (
        f"Total tasks: {progress['total']}\n"
        f"Completed: {progress['completed']}\n"
        f"Blocked: {progress['blocked']}\n"
        f"In progress: {progress['in_progress']}\n"
        f"Remaining: {progress['remaining']}"
    )

    # Tasks
    if tasks:
        task_lines = []
        for t in tasks:
            status_icon = {
                TaskStatus.COMPLETED: "done",
                TaskStatus.BLOCKED: "BLOCKED",
                TaskStatus.IN_PROGRESS: "in progress",
                TaskStatus.PENDING: "pending",
            }.get(t.status, t.status.value)
            criteria_count = len(t.acceptance_criteria)
            task_lines.append(
                f"- **{t.id}**: {t.title} [{status_icon}] "
                f"({criteria_count} criteria, "
                f"files: {len(t.files_create)} create + {len(t.files_modify)} modify)"
            )
        tasks_block = "\n".join(task_lines)
    else:
        tasks_block = "(no tasks in this milestone)"

    # Evals
    if evals:
        eval_lines = []
        for e in evals:
            tr = e.test_results
            eval_lines.append(
                f"- **{e.task_id}**: {e.review_cycles} review cycles, "
                f"tests {tr.passed}/{tr.total} passed, "
                f"{e.scope_violations} scope violations"
            )
        evals_block = "\n".join(eval_lines)
    else:
        evals_block = "(no task evals recorded)"

    # Deferred findings
    if milestone_deferred:
        deferred_lines = []
        for d in milestone_deferred:
            deferred_lines.append(
                f"- **{d.id}** (from {d.discovered_in}): "
                f"[{d.category.value}] {d.description}"
            )
        deferred_block = "\n".join(deferred_lines)
    else:
        deferred_block = "(none)"

    # Reviews
    reviews_block = "\n".join(review_summaries) if review_summaries else "(no reviews recorded)"

    # Files
    files_parts: list[str] = []
    for path, content in file_contents.items():
        ext = Path(path).suffix.lstrip(".")
        files_parts.append(f"#### {path}\n```{ext}\n{content}\n```")
    files_block = "\n\n".join(files_parts) if files_parts else "(no files)"
    if truncated:
        files_block += (
            f"\n\n(showing {MAX_FILES_PER_MILESTONE} of "
            f"{len(seen_files)} total files)"
        )

    # Render prompt
    review_prompt = _MILESTONE_REVIEW_PROMPT.format(
        milestone_id=milestone_id,
        milestone_name=milestone.name,
        milestone_goal=milestone.goal or "(no goal specified)",
        progress_block=progress_block,
        tasks_block=tasks_block,
        evals_block=evals_block,
        deferred_block=deferred_block,
        reviews_block=reviews_block,
        files_block=files_block,
    )

    # Eval summary for the return dict
    total_review_cycles = sum(e.review_cycles for e in evals)
    total_scope_violations = sum(e.scope_violations for e in evals)

    return {
        "status": "ok",
        "milestone_id": milestone_id,
        "review_prompt": review_prompt,
        "task_count": len(tasks),
        "file_count": len(file_contents),
        "deferred_count": len(milestone_deferred),
        "eval_summary": {
            "tasks_with_evals": len(evals),
            "total_review_cycles": total_review_cycles,
            "total_scope_violations": total_scope_violations,
        },
    }

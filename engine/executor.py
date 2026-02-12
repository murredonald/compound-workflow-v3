"""Execution loop — picks tasks, provides context, records results.

The executor doesn't implement tasks (Claude does that).
It manages the loop: pick → context → execute → record → next.

All operations go through the orchestrator/db layer. This module provides
the high-level loop logic that the orchestrator CLI commands call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core import db
from core.models import (
    DeferredFinding,
    DeferredFindingCategory,
    ReviewFinding,
    ReviewResult,
    ReviewVerdict,
    Task,
    TaskEval,
    TaskStatus,
    TestResults,
    _now,
)
from engine.composer import compose_task_context
from engine.renderer import render
from engine.reviewer import (
    adjudicate_reviews,
    build_fix_context,
    check_scope,
    compose_review_context,
    determine_reviewers,
)

if TYPE_CHECKING:
    import sqlite3

# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------

def pick_next_task(conn: sqlite3.Connection) -> Task | None:
    """Pick the next executable task (respects dependency order)."""
    return db.next_pending_task(conn)


def start_task(conn: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    """Mark task as in-progress and return rendered execution context.

    Returns a dict with:
      - task details
      - filtered decisions (only those the task references)
      - rendered execution prompt
      - sibling tasks for milestone awareness
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {
            "error": f"Task {task_id} not found",
            "fix_hint": "Check task ID format (T01, DF-01, QA-01). "
                        "Use 'next' to see the next available task.",
        }

    db.update_task_status(conn, task_id, TaskStatus.IN_PROGRESS)

    ctx = compose_task_context(conn, task_id)
    template = ctx.pop("prompt", "")
    ctx["task_id"] = task_id

    # Render the execution prompt with context injected
    rendered_prompt = render(template, ctx) if template else ""
    ctx["rendered_prompt"] = rendered_prompt

    return ctx


def complete_task(conn: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    """Mark task as completed and report milestone progress."""
    db.update_task_status(conn, task_id, TaskStatus.COMPLETED)

    task = db.get_task(conn, task_id)
    if not task:
        return {"task": task_id, "status": "completed"}

    milestone_tasks = db.get_tasks(conn, milestone=task.milestone)
    completed_count = sum(1 for t in milestone_tasks if t.status == TaskStatus.COMPLETED)
    all_done = all(
        t.status in (TaskStatus.COMPLETED, TaskStatus.BLOCKED)
        for t in milestone_tasks
    )

    return {
        "task": task_id,
        "status": "completed",
        "milestone": task.milestone,
        "milestone_complete": all_done,
        "milestone_progress": f"{completed_count}/{len(milestone_tasks)}",
    }


def block_task(conn: sqlite3.Connection, task_id: str, reason: str = "") -> dict[str, Any]:
    """Mark task as blocked."""
    db.update_task_status(conn, task_id, TaskStatus.BLOCKED)
    return {"task": task_id, "status": "blocked", "reason": reason}


# ---------------------------------------------------------------------------
# Execution summary
# ---------------------------------------------------------------------------

def get_execution_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Get progress by status and milestone."""
    tasks = db.get_tasks(conn)
    milestones = db.get_milestones(conn)

    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

    by_milestone: dict[str, dict[str, Any]] = {}
    for m in milestones:
        m_tasks = [t for t in tasks if t.milestone == m.id]
        done = sum(1 for t in m_tasks if t.status == TaskStatus.COMPLETED)
        by_milestone[m.id] = {
            "name": m.name,
            "total": len(m_tasks),
            "completed": done,
            "progress_pct": round(done / len(m_tasks) * 100) if m_tasks else 0,
        }

    return {
        "total_tasks": len(tasks),
        "by_status": by_status,
        "by_milestone": by_milestone,
        "all_done": len(tasks) > 0 and all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.BLOCKED)
            for t in tasks
        ),
    }


def check_execution_complete(conn: sqlite3.Connection) -> bool:
    """Check if all tasks are done."""
    tasks = db.get_tasks(conn)
    return len(tasks) > 0 and all(
        t.status in (TaskStatus.COMPLETED, TaskStatus.BLOCKED)
        for t in tasks
    )


# ---------------------------------------------------------------------------
# Reflexion + eval integration
# ---------------------------------------------------------------------------

def record_eval(
    conn: sqlite3.Connection,
    task_id: str,
    started_at: str | None = None,
    completed_at: str | None = None,
    review_cycles: int = 0,
    security_review: bool = False,
    test_results: TestResults | None = None,
    files_touched: list[str] | None = None,
    scope_violations: int = 0,
    notes: str = "",
) -> dict[str, Any]:
    """Record task eval — auto-pulls milestone + files_planned from task metadata.

    Caller supplies runtime metrics (review cycles, test results, etc).
    Timestamps should be the actual task start/complete times, not recording time.
    Falls back to _now() only if not provided.
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {
            "error": f"Task {task_id} not found",
            "fix_hint": "Check task ID. Use 'status' to see available tasks.",
        }

    if test_results is None:
        test_results = TestResults(total=0, passed=0, failed=0, skipped=0)

    eval_ = TaskEval(
        task_id=task_id,
        milestone=task.milestone,
        status=task.status,
        started_at=started_at or _now(),
        completed_at=completed_at if completed_at is not None else (
            _now() if task.status == TaskStatus.COMPLETED else None
        ),
        review_cycles=review_cycles,
        security_review=security_review,
        test_results=test_results,
        files_planned=task.files_create + task.files_modify,
        files_touched=files_touched or [],
        scope_violations=scope_violations,
        notes=notes,
    )
    db.store_task_eval(conn, eval_)
    return {"status": "ok", "task_id": task_id, "eval": eval_.model_dump()}


def load_reflexion_for_task(
    conn: sqlite3.Connection, task_id: str
) -> list[dict[str, Any]]:
    """Load relevant reflexion entries for a task.

    Searches by overlapping tags: decision_refs and files.
    Also includes entries created by this task (task_id column match).
    Called before starting each task to surface past lessons.
    """
    task = db.get_task(conn, task_id)
    if not task:
        return []

    # Build search tags from task's metadata (decision_refs + files only)
    # Milestone excluded: it over-matches (all tasks in M1 see all M1 reflexion)
    search_tags: list[str] = []
    search_tags.extend(task.decision_refs)
    search_tags.extend(task.files_create)
    search_tags.extend(task.files_modify)

    # Tag-based search
    tag_entries = (
        db.search_reflexion(conn, tags=search_tags) if search_tags else []
    )
    # Also include entries created by this specific task
    task_entries = db.get_reflexion_entries(conn, task_id=task_id)

    # Merge, dedup by id
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for e in tag_entries + task_entries:
        if e.id not in seen:
            result.append(e.model_dump())
            seen.add(e.id)

    return result


def check_recurrence(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Check for systemic issues (3+ reflexion entries with same category+tag).

    Delegates to the deterministic SQL query in db.get_reflexion_patterns().
    """
    patterns = db.get_reflexion_patterns(conn)
    systemic: list[dict[str, Any]] = patterns.get("systemic_issues", [])
    return systemic


# ---------------------------------------------------------------------------
# Review lifecycle
# ---------------------------------------------------------------------------

def start_review_cycle(
    conn: sqlite3.Connection,
    task_id: str,
    changed_files: list[str],
    verification_output: str = "",
) -> dict[str, Any]:
    """Begin a review cycle — compose context and determine reviewers.

    Returns the context dict for reviewers + the list of reviewer names.
    Called by the orchestrator's review-start command.
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {
            "error": f"Task {task_id} not found",
            "fix_hint": "Check task ID. Use 'status' to see available tasks.",
        }

    # Determine cycle number
    current_cycle = db.get_latest_review_cycle(conn, task_id) + 1

    # Compose review context
    review_ctx = compose_review_context(conn, task_id, changed_files, verification_output)

    # Determine reviewers
    prefixes = list({ref.split("-")[0] for ref in task.decision_refs})
    decisions = db.get_decisions(conn, prefixes=prefixes) if prefixes else []
    reviewers = determine_reviewers(task, decisions)

    # Build fix context if this is a re-review
    fix_ctx: dict[str, Any] = {}
    if current_cycle > 1:
        prev_reviews = db.get_review_results(conn, task_id)
        cycle_history = [
            {
                "cycle": r.cycle,
                "reviewer": r.reviewer,
                "verdict": r.verdict.value,
                "findings": [f.model_dump() for f in r.findings],
            }
            for r in prev_reviews
        ]
        fix_ctx = build_fix_context(cycle_history)

    return {
        "task_id": task_id,
        "cycle": current_cycle,
        "reviewers": reviewers,
        "review_context": review_ctx,
        "fix_context": fix_ctx,
    }


def record_review(
    conn: sqlite3.Connection,
    task_id: str,
    reviewer: str,
    verdict: str,
    findings_json: str = "[]",
    raw_output: str = "",
    cycle: int | None = None,
    criteria_assessed: int = 0,
    criteria_passed: int = 0,
    criteria_failed: int = 0,
    scope_issues_json: str = "[]",
    decision_compliance_json: str = "{}",
) -> dict[str, Any]:
    """Store a single reviewer's result with Pydantic validation.

    Accepts raw JSON strings for findings/scope/compliance — validates
    through the model before storage.
    """
    import json

    if cycle is None:
        cycle = db.get_latest_review_cycle(conn, task_id) + 1

    # Validate verdict enum before construction
    try:
        verdict_enum = ReviewVerdict(verdict)
    except ValueError:
        valid = [v.value for v in ReviewVerdict]
        return {
            "error": f"Invalid verdict: {verdict!r}",
            "fix_hint": f"Valid verdicts: {', '.join(valid)}",
        }

    # Parse JSON inputs
    try:
        raw_findings = json.loads(findings_json)
    except json.JSONDecodeError:
        return {
            "error": f"Invalid findings JSON: {findings_json[:100]}",
            "fix_hint": "Findings must be a JSON array of objects with: severity, description.",
        }
    try:
        scope_issues = json.loads(scope_issues_json)
    except json.JSONDecodeError:
        scope_issues = []
    try:
        decision_compliance = json.loads(decision_compliance_json)
    except json.JSONDecodeError:
        decision_compliance = {}

    # Build validated model — auto-assign finding IDs if missing or zero
    try:
        findings = [ReviewFinding(**f) for f in raw_findings]
    except (ValueError, TypeError) as e:
        return {
            "error": f"Invalid finding in list: {e}",
            "fix_hint": "Each finding needs: severity (critical|major|minor|info), description. "
                        "Optional: category, file, decision_ref, fix_description.",
            "input_echo": str(raw_findings[:2])[:300],
        }
    for i, finding in enumerate(findings, 1):
        if finding.id == 0:
            finding.id = i
    result = ReviewResult(
        reviewer=reviewer,
        task_id=task_id,
        verdict=verdict_enum,
        cycle=cycle,
        findings=findings,
        criteria_assessed=criteria_assessed,
        criteria_passed=criteria_passed,
        criteria_failed=criteria_failed,
        scope_issues=scope_issues,
        decision_compliance=decision_compliance,
        raw_output=raw_output,
    )

    rowid = db.store_review_result(conn, result)
    return {
        "status": "ok",
        "task_id": task_id,
        "reviewer": reviewer,
        "verdict": verdict,
        "cycle": cycle,
        "rowid": rowid,
        "findings_count": len(findings),
    }


def get_adjudication(
    conn: sqlite3.Connection,
    task_id: str,
    cycle: int | None = None,
) -> dict[str, Any]:
    """Load reviews for a task/cycle and run adjudication.

    Cross-references all reviewers' findings and produces a unified verdict.
    """
    reviews = db.get_review_results(conn, task_id, cycle=cycle)
    if not reviews:
        return {
            "task_id": task_id,
            "cycle": cycle,
            "error": "No reviews found for this task/cycle",
            "fix_hint": "Record reviews first with 'review-record' before adjudicating.",
        }

    result = adjudicate_reviews(reviews)
    result["task_id"] = task_id
    result["cycle"] = cycle or max(r.cycle for r in reviews)
    return result


# ---------------------------------------------------------------------------
# Deferred findings
# ---------------------------------------------------------------------------

def record_deferred_finding(
    conn: sqlite3.Connection,
    task_id: str,
    category: str,
    affected_area: str,
    description: str,
    files_likely: list[str] | None = None,
    spec_reference: str = "",
) -> dict[str, Any]:
    """Store a deferred finding — a scope gap discovered during execution."""
    # Validate category enum before construction
    try:
        cat = DeferredFindingCategory(category)
    except ValueError:
        valid = [c.value for c in DeferredFindingCategory]
        return {
            "error": f"Invalid category: {category!r}",
            "fix_hint": f"Valid categories: {', '.join(valid)}",
            "input_echo": {"category": category, "task_id": task_id},
        }

    finding_id = db.next_deferred_finding_id(conn)

    finding = DeferredFinding(
        id=finding_id,
        discovered_in=task_id,
        category=cat,
        affected_area=affected_area,
        files_likely=files_likely or [],
        spec_reference=spec_reference,
        description=description,
    )

    db.store_deferred_finding(conn, finding)
    return {
        "status": "ok",
        "id": finding_id,
        "discovered_in": task_id,
        "category": category,
    }


def promote_deferred_findings(
    conn: sqlite3.Connection,
    finding_ids: list[str],
) -> dict[str, Any]:
    """Change status to 'promoted' for multiple deferred findings."""
    promoted: list[str] = []
    for fid in finding_ids:
        db.update_deferred_finding_status(conn, fid, "promoted")
        promoted.append(fid)
    return {"status": "ok", "promoted": promoted}


def check_deferred_overlap(
    conn: sqlite3.Connection,
    task_id: str,
) -> list[dict[str, Any]]:
    """Query deferred findings whose files overlap with this task's files."""
    task = db.get_task(conn, task_id)
    if not task:
        return []

    all_files = task.files_create + task.files_modify
    if not all_files:
        return []

    findings = db.get_deferred_findings_for_files(conn, all_files)
    return [f.model_dump() for f in findings]


def do_scope_check(
    conn: sqlite3.Connection,
    task_id: str,
    actual_files: list[str],
) -> dict[str, Any]:
    """Run scope check for a task against actual files touched."""
    task = db.get_task(conn, task_id)
    if not task:
        return {
            "error": f"Task {task_id} not found",
            "fix_hint": "Check task ID. Use 'status' to see available tasks.",
        }
    return check_scope(task, actual_files)

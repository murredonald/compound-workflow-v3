"""Review orchestration — determines who reviews, composes context, adjudicates.

This module handles deterministic review logic. It does NOT invoke subagents
(that's the prompt's job). It composes what goes TO reviewers and validates
what comes BACK.

Responsibilities:
  - Reviewer selection (which reviewers for which task)
  - Context composition (what context each reviewer receives)
  - Adjudication (cross-referencing multiple reviewer outputs)
  - Scope checking (actual files vs planned files)
  - Milestone boundary detection
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core import db
from core.models import (
    Decision,
    ReviewResult,
    ReviewVerdict,
    Task,
)

if TYPE_CHECKING:
    import sqlite3


# ---------------------------------------------------------------------------
# Reviewer selection (deterministic)
# ---------------------------------------------------------------------------

# Files/patterns that trigger the security auditor
_SECURITY_FILE_PATTERNS = (
    "auth", "login", "session", "token", "password", "secret",
    "credential", "permission", "rbac", "acl", "crypto", "encrypt",
    "api/", "middleware/", "payment", "billing", "financial",
)

# Decision prefixes that trigger security review
_SECURITY_PREFIXES = {"SEC", "LEGAL"}

# File extensions that trigger the style reviewer
_STYLE_EXTENSIONS = (".css", ".scss", ".sass", ".less", ".tsx", ".jsx", ".vue", ".svelte")


def determine_reviewers(task: Task, decisions: list[Decision]) -> list[str]:
    """Determine which reviewers should examine this task.

    Always includes code-reviewer. Conditionally adds:
    - security-auditor: if task touches auth/data/API/secret files or SEC-* decisions
    - frontend-style-reviewer: if task touches CSS/SCSS/TSX/JSX files
    """
    reviewers = ["code-reviewer"]

    if is_security_relevant(task, decisions):
        reviewers.append("security-auditor")

    if is_style_relevant(task):
        reviewers.append("frontend-style-reviewer")

    return reviewers


def is_security_relevant(task: Task, decisions: list[Decision]) -> bool:
    """True if task touches auth/data/API/secrets/financial files or SEC-* decisions."""
    all_files = task.files_create + task.files_modify

    # Check file paths for security-related patterns
    for f in all_files:
        f_lower = f.lower()
        if any(pat in f_lower for pat in _SECURITY_FILE_PATTERNS):
            return True

    # Check referenced decisions for security prefixes
    for ref in task.decision_refs:
        prefix = ref.split("-")[0]
        if prefix in _SECURITY_PREFIXES:
            return True

    # Check decisions directly
    return any(d.prefix.value in _SECURITY_PREFIXES for d in decisions)


def is_style_relevant(task: Task) -> bool:
    """True if task touches style-related files (.css/.scss/.tsx/.jsx etc)."""
    all_files = task.files_create + task.files_modify
    return any(
        f.lower().endswith(_STYLE_EXTENSIONS)
        for f in all_files
    )


# ---------------------------------------------------------------------------
# Context composition (for reviewer inputs)
# ---------------------------------------------------------------------------

def compose_review_context(
    conn: sqlite3.Connection,
    task_id: str,
    changed_files: list[str],
    verification_output: str = "",
) -> dict[str, Any]:
    """Build the context dict that goes TO a code reviewer.

    Returns a dict containing everything a reviewer needs:
    - task definition (title, goal, acceptance criteria, files)
    - referenced decisions (for compliance checking)
    - constraints (hard limits to check against)
    - changed files list (what was actually modified)
    - verification output (test results)
    - decision checklist (for per-decision compliance matrix)
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    # Fetch referenced decisions
    prefixes = list({ref.split("-")[0] for ref in task.decision_refs})
    if prefixes:
        all_relevant = db.get_decisions(conn, prefixes=prefixes)
        decision_map = {d.id: d for d in all_relevant}
        decisions = [
            decision_map[ref]
            for ref in task.decision_refs
            if ref in decision_map
        ]
    else:
        decisions = []

    constraints = db.get_constraints(conn)

    return {
        "task_id": task_id,
        "task": task.model_dump(),
        "decisions": [d.model_dump() for d in decisions],
        "constraints": [c.model_dump() for c in constraints],
        "changed_files": changed_files,
        "verification_output": verification_output,
        "decision_checklist": [
            {"id": d.id, "title": d.title}
            for d in decisions
        ],
    }


# ---------------------------------------------------------------------------
# Adjudication (cross-reference multiple reviewers)
# ---------------------------------------------------------------------------

def adjudicate_reviews(
    reviews: list[ReviewResult],
    primary: str = "code-reviewer",
) -> dict[str, Any]:
    """Cross-reference reviews from multiple reviewers into a unified verdict.

    Rules:
    1. Primary reviewer (code-reviewer) verdict is authoritative
    2. Findings confirmed by 2+ reviewers = high confidence
    3. External-only findings (GPT/Gemini) are flagged for manual validation
    4. Unified verdict = worst confirmed verdict (BLOCK > CONCERN > PASS)
    """
    if not reviews:
        return {
            "unified_verdict": "pass",
            "confirmed_findings": [],
            "unconfirmed_findings": [],
            "all_findings": [],
            "reviewers_consulted": [],
            "detail": "No reviews submitted",
        }

    # Separate primary from external
    primary_review: ReviewResult | None = None
    external_reviews: list[ReviewResult] = []
    for r in reviews:
        if r.reviewer == primary:
            primary_review = r
        else:
            external_reviews.append(r)

    # If no primary review, use the first review as primary
    if primary_review is None:
        primary_review = reviews[0]
        external_reviews = reviews[1:]

    # Collect all findings with source attribution
    all_findings: list[dict[str, Any]] = []
    for finding in primary_review.findings:
        all_findings.append({
            **finding.model_dump(),
            "source": primary_review.reviewer,
            "confirmed_by": [primary_review.reviewer],
        })

    # Cross-reference external findings
    unconfirmed: list[dict[str, Any]] = []
    for ext_review in external_reviews:
        for ext_finding in ext_review.findings:
            # Check if this finding matches any primary finding (same file + similar category)
            matched = False
            for af in all_findings:
                if (af["file"] == ext_finding.file and
                        af["category"] == ext_finding.category):
                    af["confirmed_by"].append(ext_review.reviewer)
                    matched = True
                    break
            if not matched:
                unconfirmed.append({
                    **ext_finding.model_dump(),
                    "source": ext_review.reviewer,
                    "needs_validation": True,
                })

    # Determine unified verdict
    # "Confirmed" = found by 2+ reviewers (primary + at least one external)
    confirmed_findings = [f for f in all_findings if len(f["confirmed_by"]) >= 2]

    # Worst verdict: primary is authoritative, plus confirmed external verdicts
    verdicts = [primary_review.verdict]
    if confirmed_findings:
        for ext in external_reviews:
            verdicts.append(ext.verdict)
    unified = _worst_verdict(verdicts)

    # Build fix list: primary findings are always actionable (authoritative),
    # confirmed findings get priority ordering
    actionable = confirmed_findings + [
        f for f in all_findings if f not in confirmed_findings
    ]
    fix_list = [
        {
            "id": i + 1,
            "file": f.get("file", ""),
            "description": f.get("description", ""),
            "fix_description": f.get("fix_description", ""),
            "severity": f.get("severity", "medium"),
        }
        for i, f in enumerate(actionable)
        if f.get("severity", "medium") in ("critical", "high", "medium")
    ]

    return {
        "unified_verdict": unified.value,
        "primary_reviewer": primary_review.reviewer,
        "primary_verdict": primary_review.verdict.value,
        "confirmed_findings": confirmed_findings,
        "unconfirmed_findings": unconfirmed,
        "all_findings": all_findings + unconfirmed,
        "fix_list": fix_list,
        "reviewers_consulted": [r.reviewer for r in reviews],
        "scope_issues": primary_review.scope_issues,
        "decision_compliance": primary_review.decision_compliance,
    }


def _worst_verdict(verdicts: list[ReviewVerdict]) -> ReviewVerdict:
    """Return the most severe verdict from a list."""
    if not verdicts:
        return ReviewVerdict.PASS
    severity_order = {
        ReviewVerdict.BLOCK: 2,
        ReviewVerdict.CONCERN: 1,
        ReviewVerdict.PASS: 0,
    }
    return max(verdicts, key=lambda v: severity_order.get(v, 0))


# ---------------------------------------------------------------------------
# Fix cycle support
# ---------------------------------------------------------------------------

def build_fix_context(cycle_history: list[dict[str, Any]]) -> dict[str, Any]:
    """Build cross-cycle error history to prevent pendulum effect.

    When a reviewer finds issues, and the fix introduces new issues,
    this context helps Claude see the full history and avoid oscillating.
    """
    if not cycle_history:
        return {"cycles": [], "recurring_files": [], "recurring_categories": []}

    # Track which files and categories appear across cycles
    file_counts: dict[str, int] = {}
    cat_counts: dict[str, int] = {}

    for cycle in cycle_history:
        for finding in cycle.get("findings", []):
            f = finding.get("file", "")
            if f:
                file_counts[f] = file_counts.get(f, 0) + 1
            cat = finding.get("category", "")
            if cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # Files/categories appearing in 2+ cycles indicate pendulum risk
    recurring_files = [f for f, c in file_counts.items() if c >= 2]
    recurring_categories = [cat for cat, c in cat_counts.items() if c >= 2]

    return {
        "cycles": cycle_history,
        "total_cycles": len(cycle_history),
        "recurring_files": recurring_files,
        "recurring_categories": recurring_categories,
    }


def check_review_cycle_limit(current_cycle: int, max_cycles: int = 3) -> bool:
    """True if current cycle exceeds the max — should escalate."""
    return current_cycle > max_cycles


# ---------------------------------------------------------------------------
# Milestone boundary detection
# ---------------------------------------------------------------------------

def check_milestone_boundary(
    conn: sqlite3.Connection,
    task_id: str,
) -> dict[str, Any]:
    """Check if completing this task finishes a milestone.

    Returns:
      - is_boundary: True if this is the last task in its milestone
      - milestone_id: The milestone this task belongs to
      - progress: {total, completed, remaining}
      - open_deferred_count: Number of open deferred findings
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    progress = get_milestone_progress(conn, task.milestone)
    open_deferred = db.get_deferred_findings(conn, status="open")

    return {
        "is_boundary": progress["remaining"] <= 1,  # This task is the last one
        "milestone_id": task.milestone,
        "progress": progress,
        "open_deferred_count": len(open_deferred),
    }


def get_milestone_progress(
    conn: sqlite3.Connection,
    milestone_id: str,
) -> dict[str, Any]:
    """Get progress stats for a milestone."""
    tasks = db.get_tasks(conn, milestone=milestone_id)
    completed = sum(1 for t in tasks if t.status.value == "completed")
    blocked = sum(1 for t in tasks if t.status.value == "blocked")
    in_progress = sum(1 for t in tasks if t.status.value == "in_progress")

    return {
        "milestone_id": milestone_id,
        "total": len(tasks),
        "completed": completed,
        "blocked": blocked,
        "in_progress": in_progress,
        "remaining": len(tasks) - completed - blocked,
        "all_done": len(tasks) > 0 and (completed + blocked) == len(tasks),
    }


# ---------------------------------------------------------------------------
# Scope checking (deterministic)
# ---------------------------------------------------------------------------

def check_scope(task: Task, actual_files: list[str]) -> dict[str, Any]:
    """Compare actual files touched vs planned files.

    Returns:
      - in_scope: True if no violations
      - violations: count of out-of-scope files
      - unexpected: files touched but not in plan
      - missing: files in plan but not touched
    """
    planned = set(task.files_create + task.files_modify)
    actual = set(actual_files)

    unexpected = sorted(actual - planned)
    missing = sorted(planned - actual)

    return {
        "in_scope": len(unexpected) == 0,
        "violations": len(unexpected),
        "unexpected_files": unexpected,
        "missing_files": missing,
        "planned_count": len(planned),
        "actual_count": len(actual),
    }

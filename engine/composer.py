"""Prompt / context composer.

Builds filtered, validated context blobs from the DB for each pipeline phase.
This is what prevents context bloat — each specialist gets ONLY the decisions
it needs, not all 200+ decisions from every domain.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

logger = logging.getLogger(__name__)

from core.db import (
    get_artifact,
    get_constraints,
    get_decisions,
    get_deferred_findings_for_files,
    get_milestones,
    get_phases,
    get_pipeline,
    get_reflexion_entries,
    get_review_results,
    get_task,
    get_tasks,
    search_reflexion,
)
from core.models import PhaseStatus

# ---------------------------------------------------------------------------
# Relevance matrix
# ---------------------------------------------------------------------------
# Maps each phase to the decision prefixes it needs.
# "*" = all prefixes.
# Empty list = per-task filtering (only decisions referenced by the task).

RELEVANCE: dict[str, list[str]] = {
    # Planning sees everything it created
    "plan": ["GEN"],

    # Specialists — each sees GEN + its direct dependencies
    "specialist/domain":        ["GEN"],
    "specialist/competition":   ["GEN", "DOM"],
    "specialist/architecture":  ["GEN", "DOM", "COMP"],
    "specialist/backend":       ["GEN", "ARCH", "DOM", "SEC", "DATA"],
    "specialist/frontend":      ["GEN", "ARCH", "BACK", "STYLE", "BRAND", "UIX", "COMP"],
    "specialist/design":        ["GEN", "BRAND", "FRONT", "UIX", "COMP"],
    "specialist/branding":      ["GEN", "DOM", "COMP"],
    "specialist/security":      ["GEN", "ARCH", "BACK", "LEGAL"],
    "specialist/testing":       ["GEN", "ARCH", "BACK", "FRONT", "SEC"],
    "specialist/devops":        ["GEN", "ARCH", "BACK", "SEC", "TEST"],
    "specialist/uix":           ["GEN", "FRONT", "STYLE", "BRAND", "COMP"],
    "specialist/legal":         ["GEN", "DOM", "SEC"],
    "specialist/pricing":       ["GEN", "DOM", "COMP"],
    "specialist/llm":           ["GEN", "ARCH", "BACK", "DOM"],
    "specialist/scraping":      ["GEN", "ARCH", "BACK", "LEGAL", "SEC"],
    "specialist/data-ml":       ["GEN", "ARCH", "BACK", "DOM"],

    # Synthesize needs everything to build the task queue
    "synthesize": ["*"],

    # Execute uses per-task filtering (see compose_task_context)
    "execute": [],

    # Retro / release are summary phases
    "retro": [],
    "release": [],
}

# Maps each specialist to the artifact types it should see as context.
# Empty or missing = no artifacts needed.
ARTIFACT_RELEVANCE: dict[str, list[str]] = {
    "specialist/design":    ["brand-guide"],
    "specialist/frontend":  ["style-guide", "brand-guide"],
    "specialist/uix":       ["style-guide"],
    "specialist/testing":   ["style-guide"],
    "specialist/pricing":   ["competition-analysis"],
    "specialist/legal":     ["competition-analysis"],
}


# ---------------------------------------------------------------------------
# Prompt template loading
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a .md prompt template by name.

    Returns empty string if file doesn't exist, but logs a warning
    so silent failures are visible in debug output.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        logger.warning("Prompt template not found: %s (looked in %s)", name, path)
        return ""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Context composers
# ---------------------------------------------------------------------------

def compose_phase_context(conn: sqlite3.Connection, phase_id: str) -> dict[str, Any]:
    """Build filtered context for a pipeline phase.

    Returns a dict ready for JSON serialisation that contains:
    - project info
    - relevant decisions (filtered by RELEVANCE matrix)
    - constraints
    - pipeline progress
    - the prompt template for this phase
    """
    pipeline = get_pipeline(conn)
    phases = get_phases(conn)

    # Determine which prefixes this phase needs
    prefixes = RELEVANCE.get(phase_id, [])
    if prefixes == ["*"]:
        decisions = get_decisions(conn)
    elif prefixes:
        decisions = get_decisions(conn, prefixes=prefixes)
    else:
        decisions = []

    constraints = get_constraints(conn)

    # Completed phases for context
    completed = [p.id for p in phases if p.status == PhaseStatus.COMPLETED]
    pending = [p.id for p in phases if p.status == PhaseStatus.PENDING]

    # Load prompt template
    # specialist/frontend -> specialist, plan -> plan
    prompt_name = phase_id.split("/")[0]
    prompt_template = load_prompt(prompt_name)

    # For specialists, also load the specialist-specific prompt if it exists
    specialist_prompt = ""
    if "/" in phase_id:
        specialist_name = phase_id.split("/")[1]
        specialist_prompt = load_prompt(f"specialist_{specialist_name}")

    # Load relevant artifacts for this specialist (brand-guide, style-guide, etc.)
    artifacts: dict[str, str] = {}
    for art_type in ARTIFACT_RELEVANCE.get(phase_id, []):
        content = get_artifact(conn, art_type)
        if content:
            artifacts[art_type] = content

    return {
        "phase": phase_id,
        "project_name": pipeline.project_name,
        "project_summary": pipeline.project_summary,
        "decisions": [d.model_dump() for d in decisions],
        "decision_count": len(decisions),
        "constraints": [c.model_dump() for c in constraints],
        "completed_phases": completed,
        "pending_phases": pending,
        "prompt": prompt_template,
        "specialist_prompt": specialist_prompt,
        "artifacts": artifacts,
        # Schema references — triggers get_decision_schema()/get_task_schema()
        # in the renderer when templates use {{DECISION_SCHEMA}} or {{TASK_SCHEMA}}
        "DECISION_SCHEMA": True,
        "TASK_SCHEMA": True,
    }


def compose_task_context(conn: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    """Build context for executing a specific task.

    Only includes decisions that the task explicitly references.
    This is the tightest possible filtering.
    """
    task = get_task(conn, task_id)
    if not task:
        return {
            "error": f"Task {task_id} not found",
            "fix_hint": f"Check task ID format (T01, DF-01, QA-01). "
                        f"Use 'status' or 'next' to see available tasks.",
        }

    pipeline = get_pipeline(conn)

    # Fetch only referenced decisions (batch: one query instead of N)
    prefixes = list({ref_id.split("-")[0] for ref_id in task.decision_refs})
    if prefixes:
        all_relevant = get_decisions(conn, prefixes=prefixes)
        decision_map = {d.id: d for d in all_relevant}
        referenced_decisions = [
            decision_map[ref_id]
            for ref_id in task.decision_refs
            if ref_id in decision_map
        ]
    else:
        referenced_decisions = []

    # Get the milestone context
    milestones = get_milestones(conn)
    milestone_info = None
    for m in milestones:
        if m.id == task.milestone:
            milestone_info = m
            break

    # Get sibling tasks in the same milestone (for awareness)
    sibling_tasks = get_tasks(conn, milestone=task.milestone)

    # Load execution prompt
    prompt = load_prompt("execute")

    # Constraints (G4 fix — previously missing from task context)
    constraints = get_constraints(conn)

    # Load artifacts referenced by this task
    artifacts: dict[str, str] = {}
    if task.artifact_refs:
        for art_type in task.artifact_refs:
            content = get_artifact(conn, art_type)
            if content:
                artifacts[art_type] = content

    ctx: dict[str, Any] = {
        "phase": "execute",
        "project_name": pipeline.project_name,
        "project_summary": pipeline.project_summary,
        "task": task.model_dump(),
        "decisions": [d.model_dump() for d in referenced_decisions],
        "constraints": [c.model_dump() for c in constraints],
        "milestone": milestone_info.model_dump() if milestone_info else None,
        "sibling_tasks": [
            {"id": t.id, "title": t.title, "status": t.status.value}
            for t in sibling_tasks
        ],
        "prompt": prompt,
    }
    if artifacts:
        ctx["artifacts"] = artifacts
    return ctx


def compose_synthesize_context(conn: sqlite3.Connection) -> dict[str, Any]:
    """Build context for the synthesize/task-maker phase.

    This gets ALL decisions because it needs to generate tasks from everything.
    """
    base = compose_phase_context(conn, "synthesize")

    # Add milestone info
    milestones = get_milestones(conn)
    base["milestones"] = [m.model_dump() for m in milestones]

    # Group decisions by prefix for the task maker
    by_prefix: dict[str, list[dict[str, Any]]] = {}
    for d in base["decisions"]:
        prefix = d["prefix"]
        by_prefix.setdefault(prefix, []).append(d)
    base["decisions_by_prefix"] = by_prefix

    return base


def compose_execution_context(conn: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    """Build enriched execution context for the full Ralph loop.

    Extends compose_task_context with:
    - constraints (hard limits)
    - reflexion_entries (matching past lessons for this task)
    - deferred_overlap (deferred findings touching this task's files)
    - reviewers (determined by reviewer.determine_reviewers)
    - review_history (past review cycles if this is cycle 2+)
    - verification_cmd (from task)
    - max_review_cycles (default 3)
    """
    # Import here to avoid circular dependency (reviewer imports from db)
    from engine.reviewer import determine_reviewers

    base = compose_task_context(conn, task_id)
    if "error" in base:
        return base

    task = get_task(conn, task_id)
    if not task:
        return base

    # Reflexion entries matching this task's metadata
    # 1. Direct task match (task_id)
    # 2. Tag-based match (file paths, decision refs)
    all_files = task.files_create + task.files_modify
    reflexion = get_reflexion_entries(conn, task_id=task_id)
    seen_ids = {e.id for e in reflexion}

    # Tag-based search: match file paths and decision refs
    search_tags = all_files + task.decision_refs
    if search_tags:
        tag_matches = search_reflexion(conn, tags=search_tags)
        for entry in tag_matches:
            if entry.id not in seen_ids:
                reflexion.append(entry)
                seen_ids.add(entry.id)

    base["reflexion_entries"] = [e.model_dump() for e in reflexion]

    # Deferred findings overlapping with this task's files
    if all_files:
        deferred = get_deferred_findings_for_files(conn, all_files)
        base["deferred_overlap"] = [d.model_dump() for d in deferred]
    else:
        base["deferred_overlap"] = []

    # Determine reviewers
    prefixes = list({ref.split("-")[0] for ref in task.decision_refs})
    if prefixes:
        all_relevant = get_decisions(conn, prefixes=prefixes)
        decision_map = {d.id: d for d in all_relevant}
        decisions = [
            decision_map[ref]
            for ref in task.decision_refs
            if ref in decision_map
        ]
    else:
        decisions = []
    base["reviewers"] = determine_reviewers(task, decisions)

    # Review history (for cycle 2+ fix context)
    reviews = get_review_results(conn, task_id)
    if reviews:
        base["review_history"] = [r.model_dump() for r in reviews]

    # Execution metadata
    base["task_id"] = task_id
    base["verification_cmd"] = task.verification_cmd or ""
    base["max_review_cycles"] = 3

    return base


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def context_to_json(ctx: dict[str, Any]) -> str:
    """Serialise context to pretty JSON."""
    return json.dumps(ctx, indent=2, ensure_ascii=False)


def context_summary(ctx: dict[str, Any]) -> str:
    """One-line summary of a context blob."""
    phase = ctx.get("phase", "?")
    n_decisions = ctx.get("decision_count", len(ctx.get("decisions", [])))
    n_constraints = len(ctx.get("constraints", []))
    return f"Phase: {phase} | Decisions: {n_decisions} | Constraints: {n_constraints}"

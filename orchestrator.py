"""Pipeline orchestrator — the single entry point for all state operations.

Claude Code calls this CLI.  It never reads the DB directly.
The orchestrator validates everything through Pydantic before touching SQLite.

Usage:
    python orchestrator.py init "Project Name"
    python orchestrator.py status
    python orchestrator.py next
    python orchestrator.py resume
    python orchestrator.py context [--phase PHASE] [--task TASK_ID]
    python orchestrator.py render-prompt --phase PHASE [--task TASK_ID]
    python orchestrator.py synthesize-prompt
    python orchestrator.py validate-tasks < tasks.json
    python orchestrator.py validate-decisions --prefix BACK < decisions.json
    python orchestrator.py validate-plan
    python orchestrator.py store-decisions  < decisions.json
    python orchestrator.py store-constraints < constraints.json
    python orchestrator.py store-tasks < tasks.json
    python orchestrator.py store-milestones < milestones.json
    python orchestrator.py store-artifact --type brand-guide [--file FILE]
    python orchestrator.py start-phase PHASE_ID
    python orchestrator.py complete-phase PHASE_ID
    python orchestrator.py skip-phase PHASE_ID
    python orchestrator.py task-start TASK_ID
    python orchestrator.py task-done TASK_ID
    python orchestrator.py task-block TASK_ID
    python orchestrator.py record-reflexion < entry.json
    python orchestrator.py record-eval < eval.json
    python orchestrator.py query-reflexion --for-task T05
    python orchestrator.py query-reflexion --tags tag1,tag2 --category env-config
    python orchestrator.py query-eval --task-id T01
    python orchestrator.py query-eval --milestone M1
    python orchestrator.py stats [--type review|scope|velocity|reflexion]
    python orchestrator.py validate
    python orchestrator.py rollback LABEL
    python orchestrator.py log [--limit N] [--phase PHASE]
    python orchestrator.py history DECISION_ID
    python orchestrator.py review-start TASK_ID --files f1,f2
    python orchestrator.py review-record TASK_ID --reviewer X --verdict pass < findings.json
    python orchestrator.py review-adjudicate TASK_ID [--cycle 1]
    python orchestrator.py review-history TASK_ID
    python orchestrator.py deferred-record < finding.json
    python orchestrator.py deferred-list [--status open]
    python orchestrator.py deferred-promote DF-01,DF-02
    python orchestrator.py deferred-update DF-01 --status dismissed
    python orchestrator.py milestone-check --task-id T05
    python orchestrator.py milestone-check --milestone-id M1
    python orchestrator.py milestone-review M1 [--project-root PATH]
    python orchestrator.py scope-check TASK_ID --files f1,f2
    python orchestrator.py verify TASK_ID [--project-root PATH]
    python orchestrator.py verify-reflect TASK_ID [--project-root PATH]
    python orchestrator.py pre-review TASK_ID [--project-root PATH] [--file verify.json]
    python orchestrator.py decompose-list
    python orchestrator.py decompose-prompt TASK_ID
    python orchestrator.py validate-decompose TASK_ID [--file subtasks.json]
    python orchestrator.py store-decomposed TASK_ID [--file subtasks.json]
    python orchestrator.py specialist-check BACK
    python orchestrator.py audit
    python orchestrator.py audit-validate [--file opus_output.json]
    python orchestrator.py audit-accept GAP-01,GAP-03
    python orchestrator.py audit-dismiss GAP-02,GAP-04
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure this script can import siblings when run directly
sys.path.insert(0, str(Path(__file__).parent))

from core import db
from core.models import (
    Constraint,
    Decision,
    DecisionPrefix,
    Milestone,
    PhaseStatus,
    ReflexionEntry,
    Task,
    TaskEval,
    TaskStatus,
    TestResults,
)
from engine.composer import (
    compose_execution_context,
    compose_phase_context,
    compose_synthesize_context,
    compose_task_context,
)
from engine.executor import (
    do_scope_check,
    get_adjudication,
    load_reflexion_for_task,
    promote_deferred_findings,
    record_deferred_finding,
    record_review,
    start_review_cycle,
)
from engine.renderer import render
from engine.verifier import run_verify, verify_and_reflect
from engine.pre_reviewer import compose_pre_review
from engine.milestone_reviewer import compose_milestone_review
from engine.reviewer import check_milestone_boundary, get_milestone_progress
from engine.completeness import (
    run_deterministic_audit,
    run_full_audit,
    run_specialist_exit_check,
)
from engine.decomposer import (
    build_decompose_prompt,
    parse_decompose_output,
    run_decompose_for_task,
    store_decomposed_tasks,
)
from engine.synthesizer import (
    build_synthesize_prompt,
    parse_llm_output,
    run_synthesize,
    store_validated_tasks,
)
from engine.validator import (
    ValidationResult,
    validate_planning,
    validate_specialist_output,
    validate_task_queue,
)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class OrchestratorError(Exception):
    pass


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _out(data: Any) -> None:
    """Print JSON to stdout."""
    if isinstance(data, str):
        print(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def _err(
    msg: str,
    *,
    fix_hint: str = "",
    input_echo: Any = None,
    command: str = "",
) -> int:
    """Return a structured JSON error to stdout so the LLM can parse and self-fix.

    Every error is machine-readable JSON with:
    - error: what went wrong (human-readable)
    - fix_hint: what to do differently (actionable)
    - input_echo: truncated echo of what was received (for diagnosis)
    - command: which orchestrator command failed
    """
    payload: dict[str, Any] = {
        "status": "error",
        "error": msg,
    }
    if fix_hint:
        payload["fix_hint"] = fix_hint
    if command:
        payload["command"] = command
    if input_echo is not None:
        # Truncate large inputs for readability
        echo_str = str(input_echo)
        payload["input_echo"] = echo_str[:500] + "..." if len(echo_str) > 500 else echo_str
    _out(payload)
    return 1


def _validation_error(
    items: list[Any],
    errors: list[str],
    *,
    command: str = "",
    expected_schema: str = "",
) -> int:
    """Return structured validation errors with the failing items echoed back.

    Used for Pydantic batch validation (decisions, constraints, milestones, etc).
    Echoes each failing item so the LLM can see exactly what it sent wrong.
    """
    payload: dict[str, Any] = {
        "status": "validation_error",
        "errors": errors,
        "error_count": len(errors),
        "fix_hint": "Fix the listed errors and re-submit. Check field names, types, and formats.",
    }
    if command:
        payload["command"] = command
    if expected_schema:
        payload["expected_schema"] = expected_schema
    # Echo first 3 failing items (truncated)
    if items:
        echoed = []
        for item in items[:3]:
            s = json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else str(item)
            echoed.append(s[:300] + "..." if len(s) > 300 else s)
        payload["input_sample"] = echoed
    _out(payload)
    return 1


def _read_stdin_json() -> Any:
    """Read JSON from stdin."""
    raw = sys.stdin.read().strip()
    if not raw:
        raise OrchestratorError("No JSON data on stdin")
    return json.loads(raw)


def _read_json_input(args: argparse.Namespace) -> Any:
    """Read JSON from --file flag or stdin (Windows-friendly).

    Prefers --file when provided (avoids Windows stdin piping issues).
    Falls back to stdin for Unix-style piping.
    """
    file_path = getattr(args, "file", None)
    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise OrchestratorError(f"File not found: {file_path}")
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            raise OrchestratorError(f"File is empty: {file_path}")
        return json.loads(raw)
    return _read_stdin_json()


def _get_db_path() -> Path:
    """Resolve DB path — look in CWD first, then script dir."""
    cwd_db = Path.cwd() / db.DB_NAME
    if cwd_db.exists():
        return cwd_db
    script_db = Path(__file__).parent / db.DB_NAME
    if script_db.exists():
        return script_db
    return cwd_db  # default to CWD for creation


# ---------------------------------------------------------------------------
# Commands — init / status / next
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    """Initialise a new project DB."""
    path = db.init_db(args.project_name, db_path=_get_db_path())
    _out({"status": "ok", "db": str(path), "project": args.project_name})
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show pipeline status dashboard."""
    conn = db.get_db(_get_db_path())
    try:
        pipeline = db.get_pipeline(conn)
        phases = db.get_phases(conn)
        dec_counts = db.count_decisions(conn)
        tasks = db.get_tasks(conn)

        task_summary = {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "blocked": sum(1 for t in tasks if t.status == TaskStatus.BLOCKED),
        }

        _out({
            "project": pipeline.project_name,
            "current_phase": pipeline.current_phase,
            "phases": [
                {"id": p.id, "label": p.label, "status": p.status.value}
                for p in phases
            ],
            "decisions": dec_counts,
            "decisions_total": sum(dec_counts.values()),
            "tasks": task_summary,
        })
    finally:
        conn.close()
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    """Determine what to do next."""
    conn = db.get_db(_get_db_path())
    try:
        pipeline = db.get_pipeline(conn)
        phases = db.get_phases(conn)

        # If in execute phase, find next task
        if pipeline.current_phase == "execute":
            task = db.next_pending_task(conn)
            if task:
                _out({
                    "action": "execute_task",
                    "task_id": task.id,
                    "task_title": task.title,
                    "milestone": task.milestone,
                })
            else:
                _out({
                    "action": "advance",
                    "next_phase": "retro",
                    "reason": "All tasks completed",
                })
            return 0

        # Find the next pending phase
        for phase in phases:
            if phase.status == PhaseStatus.PENDING:
                _out({
                    "action": "start_phase",
                    "phase_id": phase.id,
                    "phase_label": phase.label,
                })
                return 0

        _out({"action": "done", "reason": "All phases completed"})
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — resume (post-compaction context reload)
# ---------------------------------------------------------------------------

def cmd_resume(args: argparse.Namespace) -> int:
    """Reload full context from DB after compaction.

    Outputs everything Claude needs to continue working:
    - Pipeline status (project name, phase, progress)
    - What to do next
    - Rendered prompt with only the relevant decisions injected

    This replaces 140 lines of bash that parsed markdown files.
    """
    conn = db.get_db(_get_db_path())
    try:
        pipeline = db.get_pipeline(conn)
        phases = db.get_phases(conn)
        current = pipeline.current_phase or ""

        # --- Status block ---
        completed_phases = [p.id for p in phases if p.status == PhaseStatus.COMPLETED]
        dec_counts = db.count_decisions(conn)

        print(f"=== {pipeline.project_name} — RESUMED FROM DB ===")
        print(f"Phase: {current or '(none)'}")
        print(f"Completed: {', '.join(completed_phases) or '(none)'}")
        print(f"Decisions: {sum(dec_counts.values())} ({', '.join(f'{k}:{v}' for k, v in sorted(dec_counts.items()))})")

        # --- Task progress (if in execute) ---
        tasks = db.get_tasks(conn)
        if tasks:
            by_status: dict[str, int] = {}
            for t in tasks:
                by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            print(f"Tasks: {' | '.join(f'{k}: {v}' for k, v in sorted(by_status.items()))}")

        # --- What to do next ---
        if current == "execute":
            # Find active task first (in-progress), then next pending
            active_task = None
            for t in tasks:
                if t.status == TaskStatus.IN_PROGRESS:
                    active_task = t
                    break

            if active_task:
                print(f"\nACTIVE TASK: {active_task.id} — {active_task.title}")
                # Show relevant reflexion entries
                reflexion = load_reflexion_for_task(conn, active_task.id)
                if reflexion:
                    print(f"\nRELEVANT LESSONS ({len(reflexion)}):")
                    for r in reflexion[:5]:
                        print(f"  - [{r['category']}] {r['lesson']}")
                ctx = compose_task_context(conn, active_task.id)
                template = ctx.pop("prompt", "")
                if template:
                    print(f"\n{render(template, {**ctx, 'task_id': active_task.id})}")
            else:
                next_task = db.next_pending_task(conn)
                if next_task:
                    print(f"\nNEXT TASK: {next_task.id} — {next_task.title}")
                    print("Run: task-start", next_task.id)
                else:
                    print("\nAll tasks done. Run: complete-phase execute")
        elif current:
            # Non-execute phase — render the phase prompt with context
            ctx = compose_phase_context(conn, current)
            template = ctx.pop("prompt", "")
            if template:
                print(f"\n{render(template, ctx)}")
            else:
                print(f"\nPhase '{current}' active. No prompt template found.")
        else:
            # No active phase — find next pending
            for phase in phases:
                if phase.status == PhaseStatus.PENDING:
                    print(f"\nNEXT: start-phase {phase.id}")
                    break
            else:
                print("\nAll phases completed.")

        print("===")
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — context + prompt rendering
# ---------------------------------------------------------------------------

def cmd_context(args: argparse.Namespace) -> int:
    """Build filtered context for a phase or task."""
    conn = db.get_db(_get_db_path())
    try:
        if args.task:
            ctx = compose_task_context(conn, args.task)
        elif args.phase:
            if args.phase == "synthesize":
                ctx = compose_synthesize_context(conn)
            else:
                ctx = compose_phase_context(conn, args.phase)
        else:
            pipeline = db.get_pipeline(conn)
            phase_id = pipeline.current_phase
            if not phase_id:
                return _err(
                    "No active phase.  Specify --phase or --task.",
                    fix_hint="Use 'context --phase specialist/backend' or 'context --task T01'.",
                    command="context",
                )
            ctx = compose_phase_context(conn, phase_id)

        _out(ctx)
    finally:
        conn.close()
    return 0


def cmd_render_prompt(args: argparse.Namespace) -> int:
    """Build filtered context and render it into a prompt template.

    This is the main integration point: DB → context → rendered prompt.
    Claude reads this output and acts on it.
    """
    conn = db.get_db(_get_db_path())
    try:
        if args.task:
            ctx = compose_task_context(conn, args.task)
            ctx["task_id"] = args.task
        elif args.phase:
            if args.phase == "synthesize":
                ctx = compose_synthesize_context(conn)
            else:
                ctx = compose_phase_context(conn, args.phase)
                # Add specialist-specific context
                if args.phase.startswith("specialist/"):
                    prefix_map = {
                        "domain": "DOM", "competition": "COMP", "architecture": "ARCH",
                        "backend": "BACK", "frontend": "FRONT", "design": "STYLE",
                        "branding": "BRAND", "security": "SEC", "testing": "TEST",
                        "devops": "OPS", "uix": "UIX", "legal": "LEGAL",
                        "pricing": "PRICE", "llm": "LLM", "scraping": "INGEST",
                        "data-ml": "DATA",
                    }
                    specialist_name = args.phase.split("/")[1]
                    ctx["PREFIX"] = prefix_map.get(specialist_name, specialist_name.upper())
                    ctx["specialist_name"] = specialist_name.replace("-", " ").title()
        else:
            return _err(
                "Specify --phase or --task.",
                fix_hint="Use 'render-prompt --phase specialist/backend' or '--task T01'.",
                command="render-prompt",
            )

        # Render the prompt template with context
        template = ctx.pop("prompt", "")
        if not template:
            return _err(
                f"No prompt template found for {args.phase or args.task}",
                fix_hint="Check that prompts/ directory has the matching .md file.",
                command="render-prompt",
            )

        rendered = render(template, ctx)
        # Output as plain text (not JSON) — this IS the prompt
        print(rendered)
    finally:
        conn.close()
    return 0


def cmd_synthesize_prompt(args: argparse.Namespace) -> int:
    """Build the full synthesize prompt with all decisions injected.

    This is the key hybrid entry point:
    1. Orchestrator composes context from DB
    2. Renders it into the synthesize prompt template
    3. Outputs the complete prompt for Claude to act on
    """
    conn = db.get_db(_get_db_path())
    try:
        prompt = build_synthesize_prompt(conn)
        print(prompt)
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — validation (pre-store checks)
# ---------------------------------------------------------------------------

def cmd_validate_tasks(args: argparse.Namespace) -> int:
    """Validate LLM-generated tasks without storing them.

    Reads JSON from stdin or --file, parses into Pydantic objects, runs full
    integrity checks against the current DB state. Returns structured errors/warnings.

    This is the post-LLM guardrail in the hybrid flow.
    """
    try:
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(f"File not found: {file_path}", command="validate-tasks")
            raw = path.read_text(encoding="utf-8").strip()
        else:
            raw = sys.stdin.read().strip()
    except (OSError, ValueError) as e:
        return _err(
            f"Failed to read stdin: {e}",
            fix_hint='Expected JSON: {"milestones": [...], "tasks": [...]}',
            command="validate-tasks",
        )

    conn = db.get_db(_get_db_path())
    try:
        result = run_synthesize(conn, raw)
        # Enrich error results with fix hints
        if result["status"] != "valid":
            result["fix_hint"] = "Fix the listed errors in your JSON and re-submit."
            result["command"] = "validate-tasks"
        _out(result)
        return 0 if result["status"] == "valid" else 1
    finally:
        conn.close()


def cmd_validate_decisions(args: argparse.Namespace) -> int:
    """Validate LLM-generated specialist decisions without storing them.

    Reads decision JSON from stdin or --file, validates format + prefix consistency.
    """
    try:
        raw = _read_json_input(args)
    except (json.JSONDecodeError, OrchestratorError) as e:
        return _err(
            f"Invalid JSON input: {e}",
            fix_hint='Expected JSON array or {"decisions": [...]}.',
            command="validate-decisions",
        )

    # Handle both {decisions: [...]} and [...] formats
    if isinstance(raw, dict) and "decisions" in raw:
        items = raw["decisions"]
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]

    # Parse through Pydantic
    decisions: list[Decision] = []
    parse_errors: list[str] = []
    failed_items: list[Any] = []
    for i, item in enumerate(items):
        try:
            decisions.append(Decision(**item))
        except (ValueError, TypeError) as e:
            parse_errors.append(f"Decision {i}: {e}")
            failed_items.append(item)

    if parse_errors:
        return _validation_error(
            failed_items, parse_errors,
            command="validate-decisions",
            expected_schema='{"id": "ARCH-01", "prefix": "ARCH", "number": 1, '
                            '"title": "...", "rationale": "..."}',
        )

    # Validate the prefix is a known DecisionPrefix
    try:
        DecisionPrefix(args.prefix)
    except ValueError:
        valid_prefixes = ", ".join(p.value for p in DecisionPrefix)
        return _err(
            f"Unknown prefix: {args.prefix!r}",
            fix_hint=f"Valid prefixes: {valid_prefixes}",
            command="validate-decisions",
        )

    # Run specialist-specific validation
    result = validate_specialist_output(decisions, args.prefix)
    _out({
        "status": "valid" if result.valid else "invalid",
        "errors": result.errors,
        "warnings": result.warnings,
        "decision_count": len(decisions),
    })
    return 0 if result.valid else 1


def cmd_validate_plan(args: argparse.Namespace) -> int:
    """Check if planning phase has sufficient output to proceed."""
    conn = db.get_db(_get_db_path())
    try:
        decisions = db.get_decisions(conn)
        constraints = db.get_constraints(conn)
        result = validate_planning(decisions, constraints)
        _out({
            "status": "complete" if result.valid else "incomplete",
            "errors": result.errors,
            "warnings": result.warnings,
        })
        return 0 if result.valid else 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Commands — store (validated writes)
# ---------------------------------------------------------------------------

def cmd_store_summary(args: argparse.Namespace) -> int:
    """Store the executive summary produced at the end of planning.

    Reads plain text from --file, --text, or stdin.
    Also accepts JSON: {"summary": "text"}.
    """
    # Read summary text
    file_path = getattr(args, "file", None)
    text = getattr(args, "text", None)
    if text:
        summary = text
    elif file_path:
        path = Path(file_path)
        if not path.exists():
            return _err(f"File not found: {file_path}")
        summary = path.read_text(encoding="utf-8").strip()
    else:
        summary = sys.stdin.read().strip()

    if not summary:
        return _err(
            "Empty summary — provide text via --text, --file, or stdin",
            fix_hint="Use: store-summary --text \"Your 3-5 sentence project summary here\"",
            command="store-summary",
        )

    # Handle JSON wrapper: {"summary": "text"}
    if summary.startswith("{"):
        try:
            data = json.loads(summary)
            if isinstance(data, dict) and "summary" in data:
                summary = data["summary"]
        except json.JSONDecodeError:
            pass  # treat as plain text

    conn = db.get_db(_get_db_path())
    try:
        db.set_project_summary(conn, summary)
        _out({"status": "ok", "summary_length": len(summary)})
    except (ValueError, TypeError) as e:
        return _err(
            f"Validation error: {e}",
            fix_hint=f"Summary must be non-empty and under 32000 characters (got {len(summary)}).",
            input_echo=summary[:200],
            command="store-summary",
        )
    finally:
        conn.close()
    return 0


def cmd_store_decisions(args: argparse.Namespace) -> int:
    """Read decisions JSON from stdin or --file, validate, store."""
    try:
        raw = _read_json_input(args)
    except (json.JSONDecodeError, OrchestratorError) as e:
        return _err(
            f"Invalid JSON input: {e}",
            fix_hint='Expected JSON array or {"decisions": [...]}. '
                     'Each decision needs: id, prefix, number, title, rationale.',
            command="store-decisions",
        )

    # Handle both {decisions: [...]} and [...] formats
    if isinstance(raw, dict) and "decisions" in raw:
        items = raw["decisions"]
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]

    decisions: list[Decision] = []
    errors: list[str] = []
    failed_items: list[Any] = []
    for i, item in enumerate(items):
        try:
            decisions.append(Decision(**item))
        except (ValueError, TypeError) as e:
            errors.append(f"Item {i}: {e}")
            failed_items.append(item)

    if errors:
        return _validation_error(
            failed_items, errors,
            command="store-decisions",
            expected_schema='{"id": "ARCH-01", "prefix": "ARCH", "number": 1, '
                            '"title": "...", "rationale": "...", "details": "..."}',
        )

    conn = db.get_db(_get_db_path())
    try:
        count = db.store_decisions(conn, decisions)
        _out({"status": "ok", "stored": count})
    finally:
        conn.close()
    return 0


def cmd_store_artifact(args: argparse.Namespace) -> int:
    """Store a specialist artifact (brand-guide, style-guide, etc.).

    Reads plain text from --file or stdin.
    """
    from core.models import ArtifactType

    # Validate artifact type
    valid_types = {t.value for t in ArtifactType}
    if args.type not in valid_types:
        return _err(
            f"Unknown artifact type: {args.type}",
            fix_hint=f"Valid types: {', '.join(sorted(valid_types))}",
            command="store-artifact",
        )

    # Read content
    file_path = getattr(args, "file", None)
    if file_path:
        path = Path(file_path)
        if not path.exists():
            return _err(f"File not found: {file_path}", command="store-artifact")
        content = path.read_text(encoding="utf-8").strip()
    else:
        content = sys.stdin.read().strip()

    if not content:
        return _err(
            "Empty content — provide text via --file or stdin",
            fix_hint="Use: store-artifact --type brand-guide --file brand-guide.md",
            command="store-artifact",
        )

    conn = db.get_db(_get_db_path())
    try:
        db.store_artifact(conn, args.type, content)
        _out({"status": "ok", "type": args.type, "chars": len(content)})
    finally:
        conn.close()
    return 0


def cmd_store_constraints(args: argparse.Namespace) -> int:
    """Read constraints JSON from stdin, validate, store."""
    try:
        raw = _read_json_input(args)
    except (json.JSONDecodeError, OrchestratorError) as e:
        return _err(
            f"Invalid JSON input: {e}",
            fix_hint='Expected JSON array or {"constraints": [...]}. '
                     'Each constraint needs: id (C-NN), category (hard|soft|preference), description.',
            command="store-constraints",
        )

    # Handle both {constraints: [...]} and [...] formats
    if isinstance(raw, dict) and "constraints" in raw:
        items = raw["constraints"]
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]

    constraints: list[Constraint] = []
    errors: list[str] = []
    failed_items: list[Any] = []
    for i, item in enumerate(items):
        try:
            constraints.append(Constraint(**item))
        except (ValueError, TypeError) as e:
            errors.append(f"Item {i}: {e}")
            failed_items.append(item)

    if errors:
        return _validation_error(
            failed_items, errors,
            command="store-constraints",
            expected_schema='{"id": "C-01", "category": "hard", "description": "..."}',
        )

    conn = db.get_db(_get_db_path())
    try:
        count = db.store_constraints(conn, constraints)
        _out({"status": "ok", "stored": count})
    finally:
        conn.close()
    return 0


def cmd_store_milestones(args: argparse.Namespace) -> int:
    """Read milestones JSON from stdin or --file, validate, store."""
    try:
        raw = _read_json_input(args)
    except (json.JSONDecodeError, OrchestratorError) as e:
        return _err(
            f"Invalid JSON input: {e}",
            fix_hint='Expected JSON array or {"milestones": [...]}. '
                     'Each milestone needs: id (M1, M2), name.',
            command="store-milestones",
        )

    # Handle {milestones: [...]} wrapper
    if isinstance(raw, dict) and "milestones" in raw:
        items = raw["milestones"]
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]

    milestones: list[Milestone] = []
    errors: list[str] = []
    failed_items: list[Any] = []
    for i, item in enumerate(items):
        try:
            milestones.append(Milestone(**item))
        except (ValueError, TypeError) as e:
            errors.append(f"Item {i}: {e}")
            failed_items.append(item)

    if errors:
        return _validation_error(
            failed_items, errors,
            command="store-milestones",
            expected_schema='{"id": "M1", "name": "Core Infrastructure"}',
        )

    conn = db.get_db(_get_db_path())
    try:
        count = db.store_milestones(conn, milestones)
        _out({"status": "ok", "stored": count})
    finally:
        conn.close()
    return 0


def cmd_store_tasks(args: argparse.Namespace) -> int:
    """Read tasks JSON from stdin or --file, validate against DB, then store.

    Unlike the raw store, this runs the full validation pipeline
    (integrity checks, coverage, cycles) before storing.
    """
    try:
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(f"File not found: {file_path}", command="store-tasks")
            raw = path.read_text(encoding="utf-8").strip()
        else:
            raw = sys.stdin.read().strip()
    except (OSError, ValueError) as e:
        return _err(
            f"Failed to read input: {e}",
            fix_hint='Expected JSON: {"milestones": [...], "tasks": [...]}',
            command="store-tasks",
        )

    conn = db.get_db(_get_db_path())
    try:
        # Use the synthesizer pipeline: parse → validate → store
        result = run_synthesize(conn, raw)

        if result["status"] == "parse_error":
            _out({
                "status": "error",
                "errors": result["errors"],
                "fix_hint": "JSON parse failed. Check syntax (missing commas, unquoted keys, etc).",
                "command": "store-tasks",
            })
            return 1

        if result["status"] == "invalid":
            # Return errors but also warnings — let caller decide
            _out({
                "status": "invalid",
                "errors": result["errors"],
                "warnings": result["warnings"],
                "fix_hint": "Fix errors and re-submit. Use validate-tasks to check first.",
                "command": "store-tasks",
            })
            return 1

        # Valid — store
        tasks, milestones, _ = parse_llm_output(raw)
        counts = store_validated_tasks(conn, tasks, milestones)
        _out({
            "status": "ok",
            **counts,
            "warnings": result["warnings"],
        })
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — phase lifecycle
# ---------------------------------------------------------------------------

def cmd_start_phase(args: argparse.Namespace) -> int:
    db_path = _get_db_path()
    conn = db.get_db(db_path)
    try:
        db.create_checkpoint(db_path, args.phase_id)
        phase = db.start_phase(conn, args.phase_id)
        _out({"status": "ok", "phase": phase.id, "started_at": phase.started_at,
              "checkpoint": f"Created checkpoint '{args.phase_id}'"})
    except db.PhaseGuardError as e:
        _out({
            "status": "error",
            "phase": e.phase_id,
            "reason": "Prerequisites not met",
            "unmet": e.unmet,
            "fix_hint": f"Complete these phases first: {', '.join(e.unmet)}. "
                        f"Use 'start-phase <phase>' then 'complete-phase <phase>'.",
            "command": "start-phase",
        })
        return 1
    finally:
        conn.close()
    return 0


def cmd_complete_phase(args: argparse.Namespace) -> int:
    conn = db.get_db(_get_db_path())
    try:
        phase = db.complete_phase(conn, args.phase_id)
        _out({"status": "ok", "phase": phase.id, "completed_at": phase.completed_at})
    finally:
        conn.close()
    return 0


def cmd_skip_phase(args: argparse.Namespace) -> int:
    conn = db.get_db(_get_db_path())
    try:
        db.skip_phase(conn, args.phase_id)
        _out({"status": "ok", "phase": args.phase_id, "skipped": True})
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — task lifecycle
# ---------------------------------------------------------------------------

def cmd_task_start(args: argparse.Namespace) -> int:
    conn = db.get_db(_get_db_path())
    try:
        task = db.get_task(conn, args.task_id)
        if not task:
            return _err(
                f"Task '{args.task_id}' not found",
                fix_hint="Check the task ID. Use 'next' to find the next pending task.",
                command="task-start",
            )
        db.update_task_status(conn, args.task_id, TaskStatus.IN_PROGRESS)
        # Use enriched execution context (includes verification_cmd,
        # max_review_cycles, reflexion_entries, reviewers, deferred_overlap)
        ctx = compose_execution_context(conn, args.task_id)
        template = ctx.pop("prompt", "")
        rendered = render(template, ctx) if template else ""
        reflexion = ctx.get("reflexion_entries", [])
        _out({
            "status": "ok",
            "task": args.task_id,
            "new_status": "in_progress",
            "prompt": rendered,
            "reflexion": reflexion,
            "reflexion_count": len(reflexion),
        })
    finally:
        conn.close()
    return 0


def cmd_task_done(args: argparse.Namespace) -> int:
    conn = db.get_db(_get_db_path())
    try:
        task = db.get_task(conn, args.task_id)
        if not task:
            return _err(
                f"Task '{args.task_id}' not found",
                fix_hint="Check the task ID. Use 'status' to see current tasks.",
                command="task-done",
            )
        db.update_task_status(conn, args.task_id, TaskStatus.COMPLETED)

        # Check milestone completion
        milestone_info = {}
        m_tasks = db.get_tasks(conn, milestone=task.milestone)
        completed = sum(1 for t in m_tasks if t.status == TaskStatus.COMPLETED)
        all_done = all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.BLOCKED)
            for t in m_tasks
        )
        milestone_info = {
            "milestone": task.milestone,
            "milestone_complete": all_done,
            "milestone_progress": f"{completed}/{len(m_tasks)}",
        }

        _out({"status": "ok", "task": args.task_id, "new_status": "completed",
              **milestone_info})
    finally:
        conn.close()
    return 0


def cmd_task_block(args: argparse.Namespace) -> int:
    conn = db.get_db(_get_db_path())
    try:
        task = db.get_task(conn, args.task_id)
        if not task:
            return _err(
                f"Task '{args.task_id}' not found",
                fix_hint="Check the task ID. Use 'status' to see current tasks.",
                command="task-block",
            )
        db.update_task_status(conn, args.task_id, TaskStatus.BLOCKED)
        _out({"status": "ok", "task": args.task_id, "new_status": "blocked"})
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — reflexion + evals
# ---------------------------------------------------------------------------

def cmd_record_reflexion(args: argparse.Namespace) -> int:
    """Record a reflexion entry from stdin or --file JSON."""
    try:
        raw = _read_json_input(args)
    except (json.JSONDecodeError, OrchestratorError) as e:
        return _err(
            f"Invalid JSON input: {e}",
            fix_hint="Expected JSON with: task_id, category, what_happened, lesson, tags.",
            command="record-reflexion",
        )

    conn = db.get_db(_get_db_path())
    try:
        # Auto-assign ID if not provided
        if "id" not in raw:
            raw["id"] = db.next_reflexion_id(conn)

        entry = ReflexionEntry(**raw)
        entry_id = db.store_reflexion_entry(conn, entry)

        # Check for systemic issues after recording
        patterns = db.get_reflexion_patterns(conn)
        systemic = patterns.get("systemic_issues", [])

        result: dict[str, Any] = {"status": "ok", "id": entry_id}
        if systemic:
            result["systemic_issues"] = systemic
        _out(result)
    except (ValueError, TypeError) as e:
        return _validation_error(
            [raw], [str(e)],
            command="record-reflexion",
            expected_schema='{"task_id": "T01", "category": "env-config", '
                            '"what_happened": "...", "lesson": "...", "tags": ["..."]}',
        )
    finally:
        conn.close()
    return 0


def cmd_record_eval(args: argparse.Namespace) -> int:
    """Record a task eval from stdin or --file JSON."""
    try:
        raw = _read_json_input(args)
    except (json.JSONDecodeError, OrchestratorError) as e:
        return _err(
            f"Invalid JSON input: {e}",
            fix_hint="Expected JSON with: task_id, milestone, status, started_at, "
                     "test_results, files_touched.",
            command="record-eval",
        )

    conn = db.get_db(_get_db_path())
    try:
        # Handle nested test_results
        if "test_results" in raw and isinstance(raw["test_results"], dict):
            raw["test_results"] = TestResults(**raw["test_results"])

        eval_ = TaskEval(**raw)
        task_id = db.store_task_eval(conn, eval_)
        _out({"status": "ok", "task_id": task_id, "eval": eval_.model_dump()})
    except (ValueError, TypeError) as e:
        return _validation_error(
            [raw], [str(e)],
            command="record-eval",
            expected_schema='{"task_id": "T01", "milestone": "M1", "status": "completed", '
                            '"started_at": "...", "test_results": {"total": 5, "passed": 5, '
                            '"failed": 0, "skipped": 0}, "files_touched": ["..."]}',
        )
    finally:
        conn.close()
    return 0


def cmd_query_reflexion(args: argparse.Namespace) -> int:
    """Query reflexion entries by task, tags, or category."""
    conn = db.get_db(_get_db_path())
    try:
        if args.for_task:
            # Delegate to the same logic executor uses — searches by
            # decision_refs, files, and task_id (not just literal tag match)
            entries = load_reflexion_for_task(conn, args.for_task)
            _out({"entries": entries, "count": len(entries)})
        else:
            tags = args.tags.split(",") if args.tags else None
            entries_list = db.search_reflexion(conn, tags=tags, category=args.category)
            _out({
                "entries": [e.model_dump() for e in entries_list],
                "count": len(entries_list),
            })
    finally:
        conn.close()
    return 0


def cmd_query_eval(args: argparse.Namespace) -> int:
    """Query task evals by task_id or milestone."""
    conn = db.get_db(_get_db_path())
    try:
        if args.task_id:
            eval_ = db.get_task_eval(conn, args.task_id)
            if eval_:
                _out(eval_.model_dump())
            else:
                _out({"error": f"No eval for task {args.task_id}"})
                return 1
        elif args.milestone:
            evals = db.get_task_evals(conn, milestone=args.milestone)
            _out({
                "evals": [e.model_dump() for e in evals],
                "count": len(evals),
            })
        else:
            evals = db.get_task_evals(conn)
            _out({
                "evals": [e.model_dump() for e in evals],
                "count": len(evals),
            })
    finally:
        conn.close()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show deterministic analytics from task evals + reflexion."""
    conn = db.get_db(_get_db_path())
    try:
        stat_type = args.type if hasattr(args, "type") and args.type else None

        result: dict[str, Any] = {}

        if not stat_type or stat_type == "review":
            result["review"] = db.get_review_stats(conn)

        if not stat_type or stat_type == "scope":
            result["scope_drift"] = db.get_scope_drift(conn)

        if not stat_type or stat_type == "velocity":
            result["velocity"] = db.get_milestone_velocity(conn)

        if not stat_type or stat_type == "reflexion":
            result["reflexion_patterns"] = db.get_reflexion_patterns(conn)

        _out(result)
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — audit + history
# ---------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> int:
    """Run full integrity checks on the DB using the validator module."""
    conn = db.get_db(_get_db_path())
    try:
        tasks = db.get_tasks(conn)
        milestones = db.get_milestones(conn)
        decisions = db.get_decisions(conn)

        result = ValidationResult()

        # Task queue validation (if tasks exist)
        if tasks:
            result.merge(validate_task_queue(tasks, milestones, decisions))

        # Phase ordering check
        phases = db.get_phases(conn)
        active_count = sum(1 for p in phases if p.status == PhaseStatus.ACTIVE)
        if active_count > 1:
            result.add_warning(
                f"Multiple phases active ({active_count}), expected 0 or 1"
            )

        _out(result.to_dict())
        return 0 if result.valid else 1
    finally:
        conn.close()


def cmd_rollback(args: argparse.Namespace) -> int:
    """Rollback to a checkpoint."""
    db_path = _get_db_path()
    if args.label == "list":
        checkpoints = db.list_checkpoints(db_path)
        _out({"checkpoints": checkpoints})
        return 0

    ok = db.rollback_to_checkpoint(db_path, args.label)
    if ok:
        _out({"status": "ok", "restored_from": args.label})
    else:
        _out({"status": "error", "reason": f"No checkpoint '{args.label}' found",
              "available": db.list_checkpoints(db_path)})
        return 1
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    """Show recent events."""
    conn = db.get_db(_get_db_path())
    try:
        events = db.get_events(conn, limit=args.limit, phase=args.phase)
        _out({"events": events, "count": len(events)})
    finally:
        conn.close()
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Show past versions of a decision."""
    conn = db.get_db(_get_db_path())
    try:
        versions = db.get_decision_history(conn, args.decision_id)
        current = db.get_decision(conn, args.decision_id)
        _out({
            "decision_id": args.decision_id,
            "current": current.model_dump() if current else None,
            "previous_versions": versions,
            "total_versions": len(versions) + (1 if current else 0),
        })
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — review lifecycle
# ---------------------------------------------------------------------------

def cmd_review_start(args: argparse.Namespace) -> int:
    """Start a review cycle — compose context and determine reviewers."""
    conn = db.get_db(_get_db_path())
    try:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        verification = args.verification or ""
        result = start_review_cycle(conn, args.task_id, files, verification)
        _out(result)
        return 1 if "error" in result else 0
    finally:
        conn.close()


def cmd_review_record(args: argparse.Namespace) -> int:
    """Store a single reviewer's result."""
    conn = db.get_db(_get_db_path())
    try:
        # Read findings from --file or stdin
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(f"File not found: {file_path}", command="review-record")
            try:
                findings_json = path.read_text(encoding="utf-8").strip() or "[]"
            except (OSError, ValueError) as e:
                return _err(
                    f"Failed to read {file_path}: {e}",
                    command="review-record",
                )
        elif not sys.stdin.isatty():
            findings_json = sys.stdin.read().strip() or "[]"
        else:
            findings_json = "[]"

        result = record_review(
            conn,
            task_id=args.task_id,
            reviewer=args.reviewer,
            verdict=args.verdict,
            findings_json=findings_json,
            cycle=args.cycle,
            criteria_assessed=args.criteria_assessed,
            criteria_passed=args.criteria_passed,
            criteria_failed=args.criteria_failed,
        )
        _out(result)
        return 1 if "error" in result else 0
    finally:
        conn.close()


def cmd_review_adjudicate(args: argparse.Namespace) -> int:
    """Cross-reference reviews and produce a unified verdict."""
    conn = db.get_db(_get_db_path())
    try:
        result = get_adjudication(conn, args.task_id, cycle=args.cycle)
        _out(result)
        return 1 if "error" in result else 0
    finally:
        conn.close()


def cmd_review_history(args: argparse.Namespace) -> int:
    """Show all reviews for a task across all cycles."""
    conn = db.get_db(_get_db_path())
    try:
        reviews = db.get_review_results(conn, args.task_id)
        _out({
            "task_id": args.task_id,
            "total_reviews": len(reviews),
            "reviews": [r.model_dump() for r in reviews],
        })
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — deferred findings
# ---------------------------------------------------------------------------

def cmd_deferred_record(args: argparse.Namespace) -> int:
    """Store a deferred finding from stdin or --file JSON."""
    conn = db.get_db(_get_db_path())
    try:
        try:
            data = _read_json_input(args)
        except (json.JSONDecodeError, OrchestratorError) as e:
            return _err(
                f"Invalid JSON input: {e}",
                fix_hint="Expected JSON with: discovered_in, category, affected_area, description.",
                command="deferred-record",
            )
        # Validate required keys before calling executor
        missing = [k for k in ("discovered_in", "category", "affected_area", "description")
                   if k not in data]
        if missing:
            return _err(
                f"Missing required fields: {', '.join(missing)}",
                fix_hint="Required: discovered_in (task ID), category (missing-feature|"
                         "missing-validation|missing-integration|missing-test), "
                         "affected_area, description.",
                input_echo=data,
                command="deferred-record",
            )
        result = record_deferred_finding(
            conn,
            task_id=data["discovered_in"],
            category=data["category"],
            affected_area=data["affected_area"],
            description=data["description"],
            files_likely=data.get("files_likely", []),
            spec_reference=data.get("spec_reference", ""),
        )
        _out(result)
        return 1 if "error" in result else 0
    except (ValueError, TypeError) as e:
        return _err(
            f"Validation error: {e}",
            fix_hint="Check category is valid: missing-feature, missing-validation, "
                     "missing-integration, missing-test.",
            command="deferred-record",
        )
    finally:
        conn.close()


def cmd_deferred_list(args: argparse.Namespace) -> int:
    """List deferred findings."""
    conn = db.get_db(_get_db_path())
    try:
        findings = db.get_deferred_findings(conn, status=args.status)
        _out({
            "count": len(findings),
            "findings": [f.model_dump() for f in findings],
        })
    finally:
        conn.close()
    return 0


def cmd_deferred_promote(args: argparse.Namespace) -> int:
    """Promote deferred findings to task status."""
    conn = db.get_db(_get_db_path())
    try:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        result = promote_deferred_findings(conn, ids)
        _out(result)
    finally:
        conn.close()
    return 0


def cmd_deferred_update(args: argparse.Namespace) -> int:
    """Update a deferred finding's status."""
    conn = db.get_db(_get_db_path())
    try:
        db.update_deferred_finding_status(conn, args.finding_id, args.status)
        _out({"status": "ok", "id": args.finding_id, "new_status": args.status})
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — milestone + scope
# ---------------------------------------------------------------------------

def cmd_milestone_check(args: argparse.Namespace) -> int:
    """Check milestone progress and boundary status."""
    if not args.task_id and not args.milestone_id:
        return _err(
            "Either --task-id or --milestone-id is required",
            fix_hint="Provide --task-id T05 to check if T05's milestone is complete, "
                     "or --milestone-id M1 to see M1 progress.",
            command="milestone-check",
        )
    conn = db.get_db(_get_db_path())
    try:
        if args.task_id:
            result = check_milestone_boundary(conn, args.task_id)
        else:
            result = get_milestone_progress(conn, args.milestone_id)
        _out(result)
        return 1 if "error" in result else 0
    finally:
        conn.close()


def cmd_scope_check(args: argparse.Namespace) -> int:
    """Compare actual files vs planned files for a task."""
    conn = db.get_db(_get_db_path())
    try:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        result = do_scope_check(conn, args.task_id, files)
        _out(result)
        return 1 if "error" in result else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Commands — milestone review
# ---------------------------------------------------------------------------

def cmd_milestone_review(args: argparse.Namespace) -> int:
    """Compose a milestone review prompt for the milestone-reviewer subagent."""
    conn = db.get_db(_get_db_path())
    try:
        project_root = Path(args.project_root) if args.project_root else Path.cwd()
        result = compose_milestone_review(conn, args.milestone_id, project_root)
        _out(result)
        return 0 if result.get("status") == "ok" else 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Commands — verify (task-scoped quality checks)
# ---------------------------------------------------------------------------

def cmd_verify(args: argparse.Namespace) -> int:
    """Run 13 quality checks scoped to a task's files."""
    conn = db.get_db(_get_db_path())
    try:
        project_root = Path(args.project_root) if args.project_root else Path.cwd()
        result = run_verify(conn, args.task_id, project_root)
        _out(result)
        return 0 if result.get("all_passed", False) else 1
    finally:
        conn.close()


def cmd_verify_reflect(args: argparse.Namespace) -> int:
    """Run verify + auto-record reflexion entries for failures."""
    conn = db.get_db(_get_db_path())
    try:
        project_root = Path(args.project_root) if args.project_root else Path.cwd()
        result = verify_and_reflect(conn, args.task_id, project_root)
        _out(result)
        return 0 if result.get("all_passed", False) else 1
    finally:
        conn.close()


def cmd_pre_review(args: argparse.Namespace) -> int:
    """Compose a pre-review prompt for fast LLM screening."""
    conn = db.get_db(_get_db_path())
    try:
        project_root = Path(args.project_root) if args.project_root else Path.cwd()

        # Read optional verify result from --file or stdin
        verify_result = None
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(
                    f"File not found: {file_path}",
                    command="pre-review",
                )
            try:
                verify_result = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                return _err(
                    f"Invalid verify JSON: {e}",
                    fix_hint="Expected JSON output from 'orchestrator.py verify'.",
                    command="pre-review",
                )
        elif not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if raw:
                try:
                    verify_result = json.loads(raw)
                except json.JSONDecodeError as e:
                    sys.stderr.write(
                        f"Warning: ignoring malformed verify JSON from stdin: {e}\n"
                    )

        result = compose_pre_review(conn, args.task_id, project_root, verify_result)
        _out(result)
        return 0 if result.get("status") == "ok" else 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Commands — decompose (per-task subtask generation)
# ---------------------------------------------------------------------------

def cmd_decompose_list(args: argparse.Namespace) -> int:
    """List parent tasks available for decomposition."""
    conn = db.get_db(_get_db_path())
    try:
        tasks = db.get_tasks(conn)
        # Parent tasks are T-series without a dot (not subtasks)
        parents = [
            t for t in tasks
            if t.id.startswith("T") and "." not in t.id
        ]
        _out({
            "status": "ok",
            "parent_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "milestone": t.milestone,
                    "decision_refs": t.decision_refs,
                    "decision_count": len(t.decision_refs),
                }
                for t in parents
            ],
            "count": len(parents),
        })
    finally:
        conn.close()
    return 0


def cmd_decompose_prompt(args: argparse.Namespace) -> int:
    """Build a focused decompose prompt for one parent task."""
    conn = db.get_db(_get_db_path())
    try:
        prompt = build_decompose_prompt(conn, args.task_id)
        if prompt.startswith("ERROR:"):
            return _err(prompt, command="decompose-prompt")
        print(prompt)
    finally:
        conn.close()
    return 0


def cmd_validate_decompose(args: argparse.Namespace) -> int:
    """Parse and validate subtask JSON for a parent task."""
    try:
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(f"File not found: {file_path}", command="validate-decompose")
            raw = path.read_text(encoding="utf-8").strip()
        else:
            raw = sys.stdin.read().strip()
    except (OSError, ValueError) as e:
        return _err(
            f"Failed to read input: {e}",
            fix_hint='Expected JSON: {"subtasks": [...], "missing_decisions": [...]}',
            command="validate-decompose",
        )

    conn = db.get_db(_get_db_path())
    try:
        result = run_decompose_for_task(conn, args.task_id, raw)
        if result["status"] != "valid":
            result["fix_hint"] = "Fix the listed errors in your JSON and re-submit."
            result["command"] = "validate-decompose"
        _out(result)
        return 0 if result["status"] == "valid" else 1
    finally:
        conn.close()


def cmd_store_decomposed(args: argparse.Namespace) -> int:
    """Validate and store decomposed subtasks, replacing the parent task."""
    try:
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(f"File not found: {file_path}", command="store-decomposed")
            raw = path.read_text(encoding="utf-8").strip()
        else:
            raw = sys.stdin.read().strip()
    except (OSError, ValueError) as e:
        return _err(
            f"Failed to read input: {e}",
            fix_hint='Expected JSON: {"subtasks": [...]}',
            command="store-decomposed",
        )

    conn = db.get_db(_get_db_path())
    try:
        # First validate
        result = run_decompose_for_task(conn, args.task_id, raw)

        if result["status"] == "parse_error":
            _out({
                "status": "error",
                "errors": result["errors"],
                "fix_hint": "JSON parse failed. Check syntax.",
                "command": "store-decomposed",
            })
            return 1

        if result["status"] == "invalid":
            _out({
                "status": "invalid",
                "errors": result["errors"],
                "warnings": result.get("warnings", []),
                "fix_hint": "Fix errors and re-submit. Use validate-decompose to check first.",
                "command": "store-decomposed",
            })
            return 1

        if result["status"] == "error":
            _out(result)
            return 1

        # Valid — parse again and store
        subtasks_parsed, _, _ = parse_decompose_output(raw, args.task_id)
        store_result = store_decomposed_tasks(conn, args.task_id, subtasks_parsed)
        _out({
            "status": "ok",
            **store_result,
            "missing_decisions": result.get("missing_decisions", []),
            "warnings": result.get("warnings", []),
        })
    finally:
        conn.close()
    return 0


# ---------------------------------------------------------------------------
# Commands — specialist exit check
# ---------------------------------------------------------------------------

def cmd_specialist_check(args: argparse.Namespace) -> int:
    """Run cross-domain completeness checks for a specialist session.

    Called at the end of each specialist session to catch gaps early.
    Reports implication warnings (global) and cross-domain contract warnings
    (specific to this specialist's decisions).
    """
    conn = db.get_db(_get_db_path())
    try:
        result = run_specialist_exit_check(conn, args.prefix)
        _out(result)
        return 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Commands — completeness audit
# ---------------------------------------------------------------------------

def cmd_audit(args: argparse.Namespace) -> int:
    """Run deterministic audit (Layer 1+2), return gaps + LLM prompt."""
    conn = db.get_db(_get_db_path())
    try:
        # Clear stale gaps from any previous audit run
        db.clear_audit_gaps(conn)

        result = run_deterministic_audit(conn)

        # Store deterministic gaps
        for gap in result["deterministic_gaps"]:
            db.store_audit_gap(conn, gap)

        _out({
            "status": "ok",
            "gap_count": result["gap_count"],
            "by_severity": result["by_severity"],
            "by_layer": result["by_layer"],
            "gaps": [g.model_dump() for g in result["deterministic_gaps"]],
        })

        # Print LLM prompt to stderr so it can be captured separately
        print(result["llm_prompt"], file=sys.stderr)
    finally:
        conn.close()
    return 0


def cmd_audit_validate(args: argparse.Namespace) -> int:
    """Parse + validate LLM audit output, merge with deterministic gaps."""
    try:
        file_path = getattr(args, "file", None)
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return _err(f"File not found: {file_path}", command="audit-validate")
            raw = path.read_text(encoding="utf-8").strip()
        else:
            raw = sys.stdin.read().strip()
    except (OSError, ValueError) as e:
        return _err(
            f"Failed to read input: {e}",
            fix_hint='Expected JSON: {"journeys": [...], "gaps": [...]}',
            command="audit-validate",
        )

    conn = db.get_db(_get_db_path())
    try:
        result = run_full_audit(conn, raw)
        _out({
            "status": "ok" if not result["llm_errors"] else "partial",
            "total_gaps": result["total"],
            "llm_gaps_added": len(result["llm_gaps"]),
            "by_severity": result["by_severity"],
            "errors": result["llm_errors"],
            "gaps": [g.model_dump() for g in result["all_gaps"]],
        })
        return 0 if not result["llm_errors"] else 1
    finally:
        conn.close()


def cmd_audit_accept(args: argparse.Namespace) -> int:
    """Accept gaps — creates placeholder tasks."""
    gap_ids = [g.strip() for g in args.ids.split(",") if g.strip()]
    if not gap_ids:
        return _err("No gap IDs provided", command="audit-accept")

    conn = db.get_db(_get_db_path())
    try:
        accepted: list[dict[str, str]] = []
        errors: list[str] = []

        # Get milestones for task placement
        milestones = db.get_milestones(conn)
        if not milestones:
            return _err("No milestones found — run synthesize first", command="audit-accept")
        last_milestone = milestones[-1]

        # Get existing tasks for ID generation
        existing_tasks = db.get_tasks(conn)
        # Find highest T-series ID
        max_t = 0
        for t in existing_tasks:
            if t.id.startswith("T") and "." not in t.id:
                try:
                    num = int(t.id[1:])
                    max_t = max(max_t, num)
                except ValueError:
                    pass

        # Query all gaps once (not per-iteration)
        all_gaps = db.get_audit_gaps(conn)
        gap_lookup = {g.id: g for g in all_gaps}

        for gap_id in gap_ids:
            gap = gap_lookup.get(gap_id)
            if not gap:
                errors.append(f"{gap_id}: not found")
                continue
            if gap.status != "open":
                errors.append(f"{gap_id}: already {gap.status}")
                continue

            # Create a new task from the gap
            max_t += 1
            task_id = f"T{max_t:02d}"

            # Infer dependencies from trigger (if it's a task ID)
            depends_on: list[str] = []
            if gap.trigger and gap.trigger.startswith("T") and not gap.trigger.startswith("rule:"):
                depends_on = [gap.trigger]

            new_task = Task(
                id=task_id,
                title=gap.title,
                milestone=last_milestone.id,
                goal=gap.description,
                depends_on=depends_on,
                acceptance_criteria=[gap.recommendation] if gap.recommendation else [],
            )
            db.store_tasks(conn, [new_task])

            # Update gap status
            db.update_audit_gap_status(conn, gap_id, "accepted", resolved_by=task_id)
            accepted.append({"gap_id": gap_id, "task_id": task_id, "title": gap.title})

        _out({
            "status": "ok" if not errors else "partial",
            "accepted": accepted,
            "errors": errors,
        })
    finally:
        conn.close()
    return 0 if not errors else 1


def cmd_audit_dismiss(args: argparse.Namespace) -> int:
    """Dismiss gaps as not relevant."""
    gap_ids = [g.strip() for g in args.ids.split(",") if g.strip()]
    if not gap_ids:
        return _err("No gap IDs provided", command="audit-dismiss")

    conn = db.get_db(_get_db_path())
    try:
        dismissed: list[str] = []
        errors: list[str] = []

        # Query all gaps once (not per-iteration)
        all_gaps = db.get_audit_gaps(conn)
        gap_lookup = {g.id: g for g in all_gaps}

        for gap_id in gap_ids:
            gap = gap_lookup.get(gap_id)
            if not gap:
                errors.append(f"{gap_id}: not found")
                continue
            if gap.status != "open":
                errors.append(f"{gap_id}: already {gap.status}")
                continue

            db.update_audit_gap_status(conn, gap_id, "dismissed")
            dismissed.append(gap_id)

        _out({
            "status": "ok" if not errors else "partial",
            "dismissed": dismissed,
            "errors": errors,
        })
    finally:
        conn.close()
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Workflow orchestrator — validated pipeline state management",
    )
    subs = p.add_subparsers(dest="command", required=True)

    # init
    s = subs.add_parser("init", help="Initialise a new project")
    s.add_argument("project_name", help="Project name")
    s.set_defaults(func=cmd_init)

    # status
    s = subs.add_parser("status", help="Pipeline status dashboard")
    s.set_defaults(func=cmd_status)

    # next
    s = subs.add_parser("next", help="Determine what to do next")
    s.set_defaults(func=cmd_next)

    # resume (post-compaction context reload)
    s = subs.add_parser("resume",
                        help="Reload full context from DB (for on-compact hook)")
    s.set_defaults(func=cmd_resume)

    # context (raw JSON)
    s = subs.add_parser("context", help="Build filtered context (raw JSON)")
    s.add_argument("--phase", help="Phase ID (e.g. specialist/frontend)")
    s.add_argument("--task", help="Task ID (e.g. T01)")
    s.set_defaults(func=cmd_context)

    # render-prompt (rendered natural language)
    s = subs.add_parser("render-prompt",
                        help="Render a prompt template with DB context injected")
    s.add_argument("--phase", help="Phase ID (e.g. specialist/frontend)")
    s.add_argument("--task", help="Task ID (e.g. T01)")
    s.set_defaults(func=cmd_render_prompt)

    # synthesize-prompt
    s = subs.add_parser("synthesize-prompt",
                        help="Build the full synthesize prompt with all decisions")
    s.set_defaults(func=cmd_synthesize_prompt)

    # validate-tasks (pre-store check for LLM output)
    s = subs.add_parser("validate-tasks",
                        help="Validate LLM-generated tasks from stdin (no store)")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_validate_tasks)

    # validate-decisions (pre-store check for specialist output)
    s = subs.add_parser("validate-decisions",
                        help="Validate specialist decisions from stdin (no store)")
    s.add_argument("--prefix", required=True,
                   help="Expected prefix (e.g. BACK, FRONT)")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_validate_decisions)

    # validate-plan
    s = subs.add_parser("validate-plan",
                        help="Check if planning is complete enough to proceed")
    s.set_defaults(func=cmd_validate_plan)

    # store-summary
    s = subs.add_parser("store-summary",
                        help="Store executive summary (text via --text, --file, or stdin)")
    s.add_argument("--text", help="Summary text directly on the command line")
    s.add_argument("--file", help="Read summary from a file")
    s.set_defaults(func=cmd_store_summary)

    # store-artifact
    s = subs.add_parser("store-artifact",
                        help="Store a specialist artifact (brand-guide, style-guide, etc.)")
    s.add_argument("--type", required=True,
                   help="Artifact type (brand-guide, competition-analysis, style-guide, domain-knowledge)")
    s.add_argument("--file", help="Read content from file instead of stdin")
    s.set_defaults(func=cmd_store_artifact)

    # store-decisions
    s = subs.add_parser("store-decisions",
                        help="Store decisions from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_store_decisions)

    # store-constraints
    s = subs.add_parser("store-constraints",
                        help="Store constraints from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_store_constraints)

    # store-milestones
    s = subs.add_parser("store-milestones",
                        help="Store milestones from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_store_milestones)

    # store-tasks (validated + stored)
    s = subs.add_parser("store-tasks",
                        help="Validate and store tasks from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_store_tasks)

    # start-phase
    s = subs.add_parser("start-phase", help="Mark a phase as active")
    s.add_argument("phase_id")
    s.set_defaults(func=cmd_start_phase)

    # complete-phase
    s = subs.add_parser("complete-phase", help="Mark a phase as completed")
    s.add_argument("phase_id")
    s.set_defaults(func=cmd_complete_phase)

    # skip-phase
    s = subs.add_parser("skip-phase", help="Skip a phase")
    s.add_argument("phase_id")
    s.set_defaults(func=cmd_skip_phase)

    # task-start
    s = subs.add_parser("task-start",
                        help="Start a task (marks in-progress + returns prompt)")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_task_start)

    # task-done
    s = subs.add_parser("task-done",
                        help="Complete a task (marks done + milestone progress)")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_task_done)

    # task-block
    s = subs.add_parser("task-block", help="Mark a task as blocked")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_task_block)

    # record-reflexion
    s = subs.add_parser("record-reflexion",
                        help="Record a reflexion entry from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_record_reflexion)

    # record-eval
    s = subs.add_parser("record-eval",
                        help="Record a task eval from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_record_eval)

    # query-reflexion
    s = subs.add_parser("query-reflexion",
                        help="Query reflexion entries")
    s.add_argument("--for-task", help="Find entries relevant to a task ID")
    s.add_argument("--tags", help="Comma-separated tags to search")
    s.add_argument("--category", help="Filter by category")
    s.set_defaults(func=cmd_query_reflexion)

    # query-eval
    s = subs.add_parser("query-eval",
                        help="Query task evals")
    s.add_argument("--task-id", help="Specific task ID")
    s.add_argument("--milestone", help="Filter by milestone")
    s.set_defaults(func=cmd_query_eval)

    # stats
    s = subs.add_parser("stats",
                        help="Show analytics from evals + reflexion")
    s.add_argument("--type", choices=["review", "scope", "velocity", "reflexion"],
                   help="Show only one stat type")
    s.set_defaults(func=cmd_stats)

    # validate (full DB check)
    s = subs.add_parser("validate", help="Run full DB integrity checks")
    s.set_defaults(func=cmd_validate)

    # rollback
    s = subs.add_parser("rollback",
                        help="Rollback to a checkpoint (use 'list' to see available)")
    s.add_argument("label", help="Checkpoint label (phase ID) or 'list'")
    s.set_defaults(func=cmd_rollback)

    # log
    s = subs.add_parser("log", help="Show recent events")
    s.add_argument("--limit", type=int, default=20, help="Number of events")
    s.add_argument("--phase", help="Filter by phase")
    s.set_defaults(func=cmd_log)

    # history
    s = subs.add_parser("history", help="Show past versions of a decision")
    s.add_argument("decision_id", help="Decision ID (e.g. ARCH-01)")
    s.set_defaults(func=cmd_history)

    # --- Review lifecycle ---

    # review-start
    s = subs.add_parser("review-start",
                        help="Start a review cycle for a task")
    s.add_argument("task_id", help="Task ID")
    s.add_argument("--files", required=True,
                   help="Comma-separated list of changed files")
    s.add_argument("--verification", default="",
                   help="Verification output (test results)")
    s.set_defaults(func=cmd_review_start)

    # review-record
    s = subs.add_parser("review-record",
                        help="Store a reviewer's result (findings via stdin or --file)")
    s.add_argument("task_id", help="Task ID")
    s.add_argument("--reviewer", required=True, help="Reviewer name")
    s.add_argument("--verdict", required=True,
                   choices=["pass", "concern", "block"], help="Review verdict")
    s.add_argument("--cycle", type=int, default=None, help="Cycle number")
    s.add_argument("--criteria-assessed", type=int, default=0)
    s.add_argument("--criteria-passed", type=int, default=0)
    s.add_argument("--criteria-failed", type=int, default=0)
    s.add_argument("--file", help="Read findings JSON from file instead of stdin")
    s.set_defaults(func=cmd_review_record)

    # review-adjudicate
    s = subs.add_parser("review-adjudicate",
                        help="Cross-reference reviews for unified verdict")
    s.add_argument("task_id", help="Task ID")
    s.add_argument("--cycle", type=int, default=None, help="Specific cycle")
    s.set_defaults(func=cmd_review_adjudicate)

    # review-history
    s = subs.add_parser("review-history",
                        help="Show all reviews for a task")
    s.add_argument("task_id", help="Task ID")
    s.set_defaults(func=cmd_review_history)

    # --- Deferred findings ---

    # deferred-record
    s = subs.add_parser("deferred-record",
                        help="Store a deferred finding from stdin or --file JSON")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_deferred_record)

    # deferred-list
    s = subs.add_parser("deferred-list",
                        help="List deferred findings")
    s.add_argument("--status", default=None,
                   help="Filter by status (open, promoted, etc)")
    s.set_defaults(func=cmd_deferred_list)

    # deferred-promote
    s = subs.add_parser("deferred-promote",
                        help="Promote deferred findings")
    s.add_argument("ids", help="Comma-separated finding IDs (e.g. DF-01,DF-02)")
    s.set_defaults(func=cmd_deferred_promote)

    # deferred-update
    s = subs.add_parser("deferred-update",
                        help="Update a deferred finding status")
    s.add_argument("finding_id", help="Finding ID (e.g. DF-01)")
    s.add_argument("--status", required=True,
                   choices=["open", "promoted", "deferred-post-v1", "dismissed"],
                   help="New status")
    s.set_defaults(func=cmd_deferred_update)

    # --- Milestone + scope ---

    # milestone-check
    s = subs.add_parser("milestone-check",
                        help="Check milestone progress or boundary")
    s.add_argument("--task-id", default=None,
                   help="Task ID (checks if this task completes the milestone)")
    s.add_argument("--milestone-id", default=None,
                   help="Milestone ID (e.g. M1)")
    s.set_defaults(func=cmd_milestone_check)

    # milestone-review
    s = subs.add_parser("milestone-review",
                        help="Compose a milestone review prompt for the reviewer subagent")
    s.add_argument("milestone_id", help="Milestone ID (e.g. M1)")
    s.add_argument("--project-root", default=None,
                   help="Project root directory (default: CWD)")
    s.set_defaults(func=cmd_milestone_review)

    # scope-check
    s = subs.add_parser("scope-check",
                        help="Compare actual vs planned files for a task")
    s.add_argument("task_id", help="Task ID")
    s.add_argument("--files", required=True,
                   help="Comma-separated list of actual files touched")
    s.set_defaults(func=cmd_scope_check)

    # --- Verify ---

    # verify (task-scoped quality checks)
    s = subs.add_parser("verify",
                        help="Run quality checks scoped to a task's files")
    s.add_argument("task_id", help="Task ID (e.g. T01)")
    s.add_argument("--project-root", default=None,
                   help="Project root directory (default: CWD)")
    s.set_defaults(func=cmd_verify)

    # verify-reflect (verify + auto-record reflexion)
    s = subs.add_parser("verify-reflect",
                        help="Run verify + auto-record reflexion for failures")
    s.add_argument("task_id", help="Task ID (e.g. T01)")
    s.add_argument("--project-root", default=None,
                   help="Project root directory (default: CWD)")
    s.set_defaults(func=cmd_verify_reflect)

    # --- Pre-review ---

    # pre-review (LLM pre-screening prompt composition)
    s = subs.add_parser("pre-review",
                        help="Compose a pre-review prompt for fast LLM screening")
    s.add_argument("task_id", help="Task ID (e.g. T01)")
    s.add_argument("--project-root", default=None,
                   help="Project root directory (default: CWD)")
    s.add_argument("--file", help="Read verify JSON from file instead of stdin")
    s.set_defaults(func=cmd_pre_review)

    # --- Decompose ---

    # decompose-list
    s = subs.add_parser("decompose-list",
                        help="List parent tasks available for decomposition")
    s.set_defaults(func=cmd_decompose_list)

    # decompose-prompt
    s = subs.add_parser("decompose-prompt",
                        help="Build a focused decompose prompt for one parent task")
    s.add_argument("task_id", help="Parent task ID (e.g. T01)")
    s.set_defaults(func=cmd_decompose_prompt)

    # validate-decompose
    s = subs.add_parser("validate-decompose",
                        help="Parse and validate subtask JSON for a parent task")
    s.add_argument("task_id", help="Parent task ID (e.g. T01)")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_validate_decompose)

    # store-decomposed
    s = subs.add_parser("store-decomposed",
                        help="Validate and store decomposed subtasks, replacing parent")
    s.add_argument("task_id", help="Parent task ID (e.g. T01)")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_store_decomposed)

    # --- Specialist exit check ---

    # specialist-check
    s = subs.add_parser("specialist-check",
                        help="Run cross-domain completeness checks for a specialist")
    s.add_argument("prefix", help="Decision prefix (e.g. BACK, FRONT, SEC)")
    s.set_defaults(func=cmd_specialist_check)

    # --- Completeness audit ---

    # audit
    s = subs.add_parser("audit",
                        help="Run deterministic completeness audit (Layer 1+2)")
    s.set_defaults(func=cmd_audit)

    # audit-validate
    s = subs.add_parser("audit-validate",
                        help="Parse + validate LLM audit output, merge with deterministic gaps")
    s.add_argument("--file", help="Read JSON from file instead of stdin")
    s.set_defaults(func=cmd_audit_validate)

    # audit-accept
    s = subs.add_parser("audit-accept",
                        help="Accept gaps and create tasks for them")
    s.add_argument("ids", help="Comma-separated gap IDs (e.g. GAP-01,GAP-03)")
    s.set_defaults(func=cmd_audit_accept)

    # audit-dismiss
    s = subs.add_parser("audit-dismiss",
                        help="Dismiss gaps as not relevant")
    s.add_argument("ids", help="Comma-separated gap IDs (e.g. GAP-02,GAP-04)")
    s.set_defaults(func=cmd_audit_dismiss)

    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except OrchestratorError as e:
        return _err(str(e), command=getattr(args, "command", "unknown"))
    except db.PhaseGuardError as e:
        return _err(
            f"Phase prerequisites not met for '{e.phase_id}'",
            fix_hint=f"Complete these phases first: {', '.join(e.unmet)}",
            command=getattr(args, "command", "unknown"),
        )
    except db.DataError as e:
        return _err(
            f"Database data corruption: {e}",
            fix_hint="The DB may have corrupted JSON. Try 'rollback' to a checkpoint.",
            command=getattr(args, "command", "unknown"),
        )
    except Exception as e:
        return _err(
            f"Unexpected error: {e}",
            fix_hint=f"Exception type: {type(e).__name__}. "
                     "Check input format and DB state. Use 'validate' to check DB integrity.",
            command=getattr(args, "command", "unknown"),
        )


if __name__ == "__main__":
    sys.exit(main())

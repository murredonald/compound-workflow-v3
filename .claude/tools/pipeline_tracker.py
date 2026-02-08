"""Pipeline progress tracker for Compound Workflow v3.

Manages `.workflow/pipeline-status.json` — a single file that records which
pipeline phases are pending, in progress, completed, or skipped. Each command
calls `start` on entry and `complete` on exit, giving a live dashboard view.

Usage:
    python .claude/tools/pipeline_tracker.py init --type greenfield --project "My App"
    python .claude/tools/pipeline_tracker.py start --phase plan
    python .claude/tools/pipeline_tracker.py complete --phase plan --summary "9 decisions"
    python .claude/tools/pipeline_tracker.py skip --phase specialists/design --reason "no web UI"
    python .claude/tools/pipeline_tracker.py task-update --milestone M2 --task T09 \
        --total-milestones 4 --completed-milestones 1 \
        --total-tasks 25 --completed-tasks 8
    python .claude/tools/pipeline_tracker.py add-phase --phase specialists/backend \
        --label "Backend Deep Dive" --after plan-define
    python .claude/tools/pipeline_tracker.py status
    python .claude/tools/pipeline_tracker.py current
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_FILE = Path(".workflow/pipeline-status.json")

VALID_STATUSES = {"pending", "in_progress", "completed", "skipped"}

GREENFIELD_PHASES: list[dict[str, str]] = [
    {"id": "plan", "label": "Strategic Planning (Discovery)", "command": "/plan"},
    {"id": "specialists/competition", "label": "Competition & Feature Analysis", "command": "/specialists/competition"},
    {"id": "plan-define", "label": "Strategic Planning (Definition)", "command": "/plan-define"},
    # Specialists added dynamically by /plan-define via add-phase
    {"id": "synthesize", "label": "Plan Synthesis + Validation", "command": "/synthesize"},
    {"id": "execute", "label": "Execution (Ralph Loop)", "command": "/execute"},
    {"id": "runtime-qa", "label": "Runtime QA Testing", "command": "/execute"},
    {"id": "qa-fix-pass", "label": "QA Fix Pass", "command": "/execute"},
    {"id": "release", "label": "Release Closure", "command": "/release"},
    {"id": "retro", "label": "Evidence-Based Retrospective", "command": "/retro"},
]

EVOLUTION_PHASES: list[dict[str, str]] = [
    {"id": "intake", "label": "Observation Capture + Triage", "command": "/intake"},
    {"id": "plan-delta", "label": "Lightweight Planning", "command": "/plan-delta"},
    # Optional specialists added dynamically via add-phase
    {"id": "synthesize", "label": "Plan Synthesis + Validation", "command": "/synthesize"},
    {"id": "execute", "label": "Execution (Ralph Loop)", "command": "/execute"},
    {"id": "runtime-qa", "label": "Runtime QA Testing", "command": "/execute"},
    {"id": "qa-fix-pass", "label": "QA Fix Pass", "command": "/execute"},
    {"id": "release", "label": "Release Closure", "command": "/release"},
    {"id": "retro", "label": "Evidence-Based Retrospective", "command": "/retro"},
]


def _now() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_phase(template: dict[str, str]) -> dict[str, Any]:
    """Create a phase entry from a template."""
    return {
        "id": template["id"],
        "label": template["label"],
        "command": template["command"],
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "summary": None,
    }


def load_pipeline(path: Path | None = None) -> dict[str, Any]:
    """Load pipeline status from JSON file."""
    p = path or STATUS_FILE
    if not p.exists():
        print(f"Error: pipeline not initialized — run `init` first ({p})", file=sys.stderr)
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pipeline(data: dict[str, Any], path: Path | None = None) -> None:
    """Save pipeline status to JSON file."""
    p = path or STATUS_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _find_phase(data: dict[str, Any], phase_id: str) -> dict[str, Any] | None:
    """Find a phase by ID."""
    for phase in data["phases"]:
        if phase["id"] == phase_id:
            return phase
    return None


def init_pipeline(
    pipeline_type: str,
    project_name: str,
    path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Create a new pipeline status file."""
    p = path or STATUS_FILE
    if p.exists() and not force:
        print(f"Error: pipeline already exists at {p} — use --force to overwrite", file=sys.stderr)
        sys.exit(1)

    templates = GREENFIELD_PHASES if pipeline_type == "greenfield" else EVOLUTION_PHASES
    data: dict[str, Any] = {
        "pipeline_type": pipeline_type,
        "project_name": project_name,
        "started_at": _now(),
        "updated_at": _now(),
        "current_phase": None,
        "phases": [_make_phase(t) for t in templates],
    }
    save_pipeline(data, p)
    return data


def start_phase(phase_id: str, path: Path | None = None) -> dict[str, Any]:
    """Mark a phase as in_progress."""
    data = load_pipeline(path)
    phase = _find_phase(data, phase_id)
    if phase is None:
        print(f"Error: phase '{phase_id}' not found in pipeline", file=sys.stderr)
        sys.exit(1)
    if phase["status"] in ("completed", "skipped"):
        print(f"Error: phase '{phase_id}' is already {phase['status']}", file=sys.stderr)
        sys.exit(1)

    # Check for another in_progress phase
    for p in data["phases"]:
        if p["id"] != phase_id and p["status"] == "in_progress":
            print(
                f"Error: phase '{p['id']}' is already in_progress — "
                f"complete or skip it before starting '{phase_id}'",
                file=sys.stderr,
            )
            sys.exit(1)

    phase["status"] = "in_progress"
    phase["started_at"] = _now()
    data["current_phase"] = phase_id
    save_pipeline(data, path)
    return data


def complete_phase(
    phase_id: str,
    summary: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Mark a phase as completed."""
    data = load_pipeline(path)
    phase = _find_phase(data, phase_id)
    if phase is None:
        print(f"Error: phase '{phase_id}' not found in pipeline", file=sys.stderr)
        sys.exit(1)
    if phase["status"] != "in_progress":
        print(
            f"Error: phase '{phase_id}' is '{phase['status']}', not in_progress",
            file=sys.stderr,
        )
        sys.exit(1)

    phase["status"] = "completed"
    phase["completed_at"] = _now()
    if summary:
        phase["summary"] = summary
    data["current_phase"] = None
    save_pipeline(data, path)
    return data


def skip_phase(
    phase_id: str,
    reason: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Mark a phase as skipped."""
    data = load_pipeline(path)
    phase = _find_phase(data, phase_id)
    if phase is None:
        print(f"Error: phase '{phase_id}' not found in pipeline", file=sys.stderr)
        sys.exit(1)
    if phase["status"] == "completed":
        print(
            f"Error: phase '{phase_id}' is 'completed', cannot skip",
            file=sys.stderr,
        )
        sys.exit(1)

    # Allow skipping in_progress phases (e.g., qa-fix-pass started then
    # determined no must-fix findings exist). Treat as "started but skipped."
    phase["status"] = "skipped"
    if reason:
        phase["summary"] = f"Skipped: {reason}"
    save_pipeline(data, path)
    return data


def task_update(
    milestone: str,
    task: str,
    total_milestones: int,
    completed_milestones: int,
    total_tasks: int,
    completed_tasks: int,
    milestone_label: str | None = None,
    task_label: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Update execute phase progress counters."""
    data = load_pipeline(path)
    phase = _find_phase(data, "execute")
    if phase is None:
        print("Error: 'execute' phase not found in pipeline", file=sys.stderr)
        sys.exit(1)

    phase["execute_progress"] = {
        "total_milestones": total_milestones,
        "completed_milestones": completed_milestones,
        "current_milestone": milestone,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "current_task": task,
    }
    if milestone_label:
        phase["execute_progress"]["milestone_label"] = milestone_label
    if task_label:
        phase["execute_progress"]["task_label"] = task_label
    save_pipeline(data, path)
    return data


def add_phase(
    phase_id: str,
    label: str,
    after_phase_id: str,
    command: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Insert a new phase after an existing phase."""
    data = load_pipeline(path)

    # Check duplicate
    if _find_phase(data, phase_id) is not None:
        print(f"Error: phase '{phase_id}' already exists", file=sys.stderr)
        sys.exit(1)

    # Find insertion point
    insert_idx = None
    for i, p in enumerate(data["phases"]):
        if p["id"] == after_phase_id:
            insert_idx = i + 1
            break
    if insert_idx is None:
        print(f"Error: after-phase '{after_phase_id}' not found", file=sys.stderr)
        sys.exit(1)

    cmd = command or f"/{phase_id}"
    new_phase: dict[str, Any] = {
        "id": phase_id,
        "label": label,
        "command": cmd,
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "summary": None,
    }
    data["phases"].insert(insert_idx, new_phase)
    save_pipeline(data, path)
    return data


def get_current(path: Path | None = None) -> str | None:
    """Return the current phase ID or None."""
    data = load_pipeline(path)
    return data.get("current_phase")


def render_dashboard(path: Path | None = None) -> str:
    """Render a text dashboard of pipeline status."""
    data = load_pipeline(path)

    project = data.get("project_name", "Unknown")
    ptype = data.get("pipeline_type", "unknown")
    started = data.get("started_at", "")[:16].replace("T", " ")

    lines: list[str] = []
    sep = "=" * 63
    thin_sep = "-" * 63

    lines.append(sep)
    lines.append(f"PIPELINE STATUS -- {project}")
    lines.append(f"Pipeline: {ptype} | Started: {started} UTC")
    lines.append(sep)
    lines.append("")

    markers = {
        "completed": "[x]",
        "in_progress": "[>]",
        "pending": "[ ]",
        "skipped": "[-]",
    }

    completed_count = 0
    non_skipped_count = 0

    for phase in data["phases"]:
        status = phase["status"]
        marker = markers.get(status, "[ ]")
        cmd = phase.get("command", f"/{phase['id']}")

        # Build info column
        info = ""
        if status == "in_progress":
            if phase["id"] == "execute" and "execute_progress" in phase:
                ep = phase["execute_progress"]
                info = (
                    f"M{ep['completed_milestones']}/{ep['total_milestones']} milestones, "
                    f"{ep['completed_tasks']}/{ep['total_tasks']} tasks"
                )
            else:
                info = "In progress..."
        elif phase.get("summary"):
            info = phase["summary"]
        elif status == "pending" and phase["id"] == "execute":
            info = "0/0 milestones, 0/0 tasks"

        # Format line
        cmd_col = f"{cmd:<34}"
        line = f"  {marker} {cmd_col}{info}"
        lines.append(line)

        # Execute in_progress detail line
        if status == "in_progress" and phase["id"] == "execute" and "execute_progress" in phase:
            ep = phase["execute_progress"]
            detail_parts = []
            ml = ep.get("milestone_label", "")
            tl = ep.get("task_label", "")
            if ml:
                detail_parts.append(f"{ep['current_milestone']} -- {ml}")
            else:
                detail_parts.append(ep["current_milestone"])
            if tl:
                detail_parts.append(f"{ep['current_task']} -- {tl}")
            else:
                detail_parts.append(ep["current_task"])
            lines.append(f"      Current: {' | '.join(detail_parts)}")

        if status == "completed":
            completed_count += 1
        if status != "skipped":
            non_skipped_count += 1

    lines.append("")
    lines.append(thin_sep)

    current = data.get("current_phase")
    current_str = f"Current: /{current}" if current else "Idle"
    lines.append(
        f"Progress: {completed_count}/{non_skipped_count} phases complete | {current_str}"
    )
    lines.append(sep)

    return "\n".join(lines)


BACKLOG_FILE = Path(".workflow/backlog.md")

OPEN_STATUSES = {"new", "triaged", "planned", "in-progress"}
CLOSED_STATUSES = {"resolved", "closed", "wontfix", "duplicate", "superseded"}


def render_backlog_summary(backlog_path: Path | None = None) -> str:
    """Parse backlog.md and render a summary table."""
    p = backlog_path or BACKLOG_FILE
    if not p.exists():
        return "No backlog found (.workflow/backlog.md does not exist)."

    content = p.read_text(encoding="utf-8")

    # Parse CRs — each starts with ## CR-NNN: Title
    cr_blocks = re.split(r"(?=^## CR-\d{3}:)", content, flags=re.MULTILINE)

    by_status: dict[str, int] = {}
    by_lane: dict[str, dict[str, int]] = {}  # lane -> {open, closed}
    aging: dict[str, int] = {"< 7 days": 0, "7-30 days": 0, "> 30 days": 0}

    now = datetime.now(timezone.utc)

    for block in cr_blocks:
        if not block.strip().startswith("## CR-"):
            continue

        # Extract status
        status_match = re.search(
            r"\*\*Status:\*\*\s*(.+?)(?:\n|$)", block
        )
        status = status_match.group(1).strip().lower() if status_match else "unknown"
        # Normalize statuses like "promoted → CR-005"
        if status.startswith("promoted"):
            status = "promoted"
        by_status[status] = by_status.get(status, 0) + 1

        # Extract version lane
        lane_match = re.search(
            r"\*\*Version Lane:\*\*\s*(.+?)(?:\n|$)", block
        )
        lane = lane_match.group(1).strip() if lane_match else "unassigned"
        if lane not in by_lane:
            by_lane[lane] = {"open": 0, "closed": 0}
        if status in OPEN_STATUSES:
            by_lane[lane]["open"] += 1
        else:
            by_lane[lane]["closed"] += 1

        # Aging for open CRs
        if status in OPEN_STATUSES:
            created_match = re.search(
                r"\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})", block
            )
            if created_match:
                try:
                    created = datetime.strptime(
                        created_match.group(1), "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    days = (now - created).days
                    if days < 7:
                        aging["< 7 days"] += 1
                    elif days <= 30:
                        aging["7-30 days"] += 1
                    else:
                        aging["> 30 days"] += 1
                except ValueError:
                    aging["< 7 days"] += 1  # Default if date parse fails
            else:
                aging["< 7 days"] += 1  # No date = assume recent

    total = sum(by_status.values())
    if total == 0:
        return "Backlog is empty (no CRs found)."

    lines: list[str] = []
    sep = "=" * 63
    thin_sep = "-" * 63

    lines.append("")
    lines.append(sep)
    lines.append("BACKLOG SUMMARY")
    lines.append(thin_sep)

    # By status
    lines.append("By status:")
    status_order = [
        "new", "triaged", "planned", "in-progress",
        "resolved", "closed", "wontfix", "duplicate", "superseded",
    ]
    for s in status_order:
        if s in by_status:
            lines.append(f"  {s:<14}{by_status[s]}")
    # Show any statuses not in the expected order
    for s, count in sorted(by_status.items()):
        if s not in status_order:
            lines.append(f"  {s:<14}{count}")

    # By version lane
    lines.append("")
    lines.append("By version lane:")
    for lane in sorted(by_lane.keys()):
        counts = by_lane[lane]
        total_lane = counts["open"] + counts["closed"]
        lines.append(
            f"  {lane:<14}{total_lane} ({counts['open']} open, {counts['closed']} closed)"
        )

    # Aging
    open_total = sum(aging.values())
    if open_total > 0:
        lines.append("")
        lines.append("Aging (open CRs):")
        lines.append(f"  {'< 7 days:':<14}{aging['< 7 days']}")
        lines.append(f"  {'7-30 days:':<14}{aging['7-30 days']}")
        warn = " !!!" if aging["> 30 days"] > 0 else ""
        lines.append(f"  {'> 30 days:':<14}{aging['> 30 days']}{warn}")

    lines.append(sep)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Pipeline progress tracker for Compound Workflow v3",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="Path to pipeline-status.json (default: .workflow/pipeline-status.json)",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Create pipeline with typed phase list")
    p_init.set_defaults(command="init")
    p_init.add_argument("--type", dest="pipeline_type", choices=["greenfield", "evolution"], required=True)
    p_init.add_argument("--project", required=True, help="Project name")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing file")

    # start
    p_start = sub.add_parser("start", help="Mark phase as in_progress")
    p_start.set_defaults(command="start")
    p_start.add_argument("--phase", required=True, help="Phase ID")

    # complete
    p_complete = sub.add_parser("complete", help="Mark phase as completed")
    p_complete.set_defaults(command="complete")
    p_complete.add_argument("--phase", required=True, help="Phase ID")
    p_complete.add_argument("--summary", default=None, help="Completion summary")

    # skip
    p_skip = sub.add_parser("skip", help="Mark phase as skipped")
    p_skip.set_defaults(command="skip")
    p_skip.add_argument("--phase", required=True, help="Phase ID")
    p_skip.add_argument("--reason", default=None, help="Reason for skipping")

    # task-update
    p_task = sub.add_parser("task-update", help="Update execute progress counters")
    p_task.set_defaults(command="task-update")
    p_task.add_argument("--milestone", required=True, help="Current milestone (e.g. M2)")
    p_task.add_argument("--task", required=True, help="Current task (e.g. T09)")
    p_task.add_argument("--total-milestones", type=int, required=True)
    p_task.add_argument("--completed-milestones", type=int, required=True)
    p_task.add_argument("--total-tasks", type=int, required=True)
    p_task.add_argument("--completed-tasks", type=int, required=True)
    p_task.add_argument("--milestone-label", default=None, help="Milestone description")
    p_task.add_argument("--task-label", default=None, help="Task description")

    # add-phase
    p_add = sub.add_parser("add-phase", help="Insert specialist mid-pipeline")
    p_add.set_defaults(command="add-phase")
    p_add.add_argument("--phase", required=True, help="New phase ID")
    p_add.add_argument("--label", required=True, help="Phase label")
    p_add.add_argument("--after", required=True, dest="after_phase", help="Insert after this phase ID")
    p_add.add_argument("--command", default=None, dest="phase_command", help="Command name (default: /{phase})")

    # status
    p_status = sub.add_parser("status", help="Print dashboard")
    p_status.set_defaults(command="status")

    # current
    p_current = sub.add_parser("current", help="Print current phase ID")
    p_current.set_defaults(command="current")

    # backlog-summary
    p_backlog = sub.add_parser("backlog-summary", help="Print backlog summary")
    p_backlog.set_defaults(command="backlog-summary")
    p_backlog.add_argument(
        "--backlog-file", type=Path, default=None,
        help="Path to backlog.md (default: .workflow/backlog.md)",
    )

    return parser


def main() -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    path = args.status_file

    if args.command == "init":
        init_pipeline(args.pipeline_type, args.project, path=path, force=args.force)
        print(f"Pipeline initialized: {args.pipeline_type} — {args.project}")

    elif args.command == "start":
        start_phase(args.phase, path=path)
        print(f"Started: {args.phase}")

    elif args.command == "complete":
        complete_phase(args.phase, summary=args.summary, path=path)
        print(f"Completed: {args.phase}")

    elif args.command == "skip":
        skip_phase(args.phase, reason=args.reason, path=path)
        print(f"Skipped: {args.phase}")

    elif args.command == "task-update":
        task_update(
            milestone=args.milestone,
            task=args.task,
            total_milestones=args.total_milestones,
            completed_milestones=args.completed_milestones,
            total_tasks=args.total_tasks,
            completed_tasks=args.completed_tasks,
            milestone_label=args.milestone_label,
            task_label=args.task_label,
            path=path,
        )
        print(f"Updated: {args.milestone}/{args.task}")

    elif args.command == "add-phase":
        add_phase(
            phase_id=args.phase,
            label=args.label,
            after_phase_id=args.after_phase,
            command=args.phase_command,
            path=path,
        )
        print(f"Added: {args.phase} after {args.after_phase}")

    elif args.command == "status":
        print(render_dashboard(path))

    elif args.command == "current":
        current = get_current(path)
        if current:
            print(current)
        else:
            print("none")

    elif args.command == "backlog-summary":
        backlog_path = getattr(args, "backlog_file", None)
        print(render_backlog_summary(backlog_path))


if __name__ == "__main__":
    main()

"""State chain cryptographic audit trail management.

Records agent actions across the Compound Workflow v3 pipeline with
SHA-256 hashes linked in a tamper-evident chain. Each entry's prev_hash
references the previous entry's output_hash.

Usage:
    python .claude/tools/chain_manager.py record --task T05 --stage review \\
        --agent code-reviewer --input-file in.txt --output-file out.txt \\
        --description "Code review" --verdict PASS
    python .claude/tools/chain_manager.py verify
    python .claude/tools/chain_manager.py summary [--task T05]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHAIN_FILE = Path(".workflow/state-chain/chain.json")

EMPTY_CHAIN: dict[str, Any] = {
    "_schema": {
        "version": "1.0",
        "description": (
            "Cryptographic audit trail of agent state transitions. "
            "Each entry's prev_hash links to the previous entry's output_hash."
        ),
    },
    "entries": [],
    "integrity": {
        "last_verified": None,
        "chain_valid": True,
        "broken_links": [],
    },
}


def hash_content(content: str) -> str:
    """Compute SHA-256 hex digest of a string.

    Args:
        content: String to hash (UTF-8 encoded).

    Returns:
        64-character lowercase hex digest prefixed with ``sha256:``.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _load_chain(chain_path: Path) -> dict[str, Any]:
    """Load chain data from disk, creating an empty chain if missing."""
    if chain_path.exists():
        with open(chain_path, "r", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    return json.loads(json.dumps(EMPTY_CHAIN))


def _save_chain(chain_path: Path, data: dict[str, Any]) -> None:
    """Write chain data to disk, creating parent directories if needed."""
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chain_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def record_entry(
    task_id: str,
    stage: str,
    agent: str,
    input_data: str,
    output_data: str,
    description: str,
    pipeline: str = "",
    verdict: str | None = None,
    warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    chain_path: Path = CHAIN_FILE,
) -> dict[str, Any]:
    """Append a new entry to the state chain.

    Args:
        task_id: Task or milestone identifier (e.g. ``T05``, ``M2``, ``PLAN``).
        stage: Pipeline stage (``verify``, ``review``, ``milestone_review``,
            ``artifact_gen``, ``completion``, ``generation``, ``validation``,
            ``analysis``).
        agent: Agent name (``self``, ``code-reviewer``, ``planner``, etc.).
        input_data: Raw input text sent to the agent.
        output_data: Raw output text received from the agent.
        description: Human-readable summary of this action.
        pipeline: Pipeline phase (``plan``, ``specialist``, ``synthesize``,
            ``execute``, ``retro``).  Defaults to empty string.
        verdict: Agent verdict if applicable (``PASS``, ``CONCERN``, ``BLOCK``,
            ``MILESTONE_COMPLETE``, ``FIXABLE``, ``BLOCKED``).
        warnings: Warning messages.
        metadata: Stage-specific extra data.
        chain_path: Path to the chain JSON file.

    Returns:
        The newly created entry dict.
    """
    chain_data = _load_chain(chain_path)
    entries: list[dict[str, Any]] = chain_data["entries"]

    seq = len(entries) + 1
    prev_hash: str | None = entries[-1]["output_hash"] if entries else None

    entry: dict[str, Any] = {
        "seq": seq,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "task_id": task_id,
        "pipeline": pipeline,
        "stage": stage,
        "agent": agent,
        "input_hash": hash_content(input_data),
        "output_hash": hash_content(output_data),
        "prev_hash": prev_hash,
        "description": description,
        "verdict": verdict,
        "warnings": warnings or [],
        "metadata": metadata or {},
    }

    entries.append(entry)
    _save_chain(chain_path, chain_data)
    return entry


def verify_integrity(chain_path: Path = CHAIN_FILE) -> tuple[bool, list[str]]:
    """Verify chain integrity by checking all prev_hash links.

    Args:
        chain_path: Path to the chain JSON file.

    Returns:
        Tuple of ``(chain_valid, broken_link_descriptions)``.
    """
    chain_data = _load_chain(chain_path)
    entries: list[dict[str, Any]] = chain_data["entries"]
    broken: list[str] = []

    for i, entry in enumerate(entries):
        if i == 0:
            if entry.get("prev_hash") is not None:
                broken.append(
                    f"Entry 1: prev_hash should be null, got {entry['prev_hash']}"
                )
        else:
            expected = entries[i - 1]["output_hash"]
            actual = entry.get("prev_hash")
            if actual != expected:
                broken.append(
                    f"Entry {i + 1}: prev_hash mismatch "
                    f"(expected {expected}, got {actual})"
                )

    valid = len(broken) == 0
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    chain_data["integrity"] = {
        "last_verified": now,
        "chain_valid": valid,
        "broken_links": broken,
    }
    _save_chain(chain_path, chain_data)
    return valid, broken


def get_summary(
    task_id: str | None = None,
    chain_path: Path = CHAIN_FILE,
) -> str:
    """Return a human-readable chain summary.

    Args:
        task_id: Filter to entries matching this task ID.  ``None`` for all.
        chain_path: Path to the chain JSON file.

    Returns:
        Formatted multi-line summary string.
    """
    chain_data = _load_chain(chain_path)
    entries: list[dict[str, Any]] = chain_data["entries"]

    if task_id:
        entries = [e for e in entries if e["task_id"] == task_id]

    if not entries:
        if task_id:
            return f"No chain entries for task {task_id}."
        return "Chain is empty."

    lines: list[str] = [f"Chain entries: {len(entries)}", ""]
    for entry in entries:
        verdict_str = f"  Verdict: {entry['verdict']}" if entry.get("verdict") else ""
        warnings_str = (
            f"  Warnings: {', '.join(entry['warnings'])}" if entry.get("warnings") else ""
        )
        lines.append(f"[{entry['seq']}] {entry['timestamp']}")
        lines.append(
            f"  Task: {entry['task_id']} | "
            f"Pipeline: {entry.get('pipeline', '')} | "
            f"Stage: {entry['stage']} | "
            f"Agent: {entry['agent']}"
        )
        lines.append(f"  Input:  {entry['input_hash']}")
        lines.append(f"  Output: {entry['output_hash']}")
        lines.append(f"  Prev:   {entry['prev_hash'] or '(genesis)'}")
        lines.append(f"  {entry['description']}")
        if verdict_str:
            lines.append(verdict_str)
        if warnings_str:
            lines.append(warnings_str)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_record(args: argparse.Namespace) -> int:
    """Handle the ``record`` subcommand."""
    input_data = Path(args.input_file).read_text(encoding="utf-8")
    output_data = Path(args.output_file).read_text(encoding="utf-8")

    meta: dict[str, Any] = {}
    if args.metadata:
        meta = json.loads(args.metadata)

    entry = record_entry(
        task_id=args.task,
        stage=args.stage,
        agent=args.agent,
        input_data=input_data,
        output_data=output_data,
        description=args.description,
        pipeline=args.pipeline or "",
        verdict=args.verdict,
        metadata=meta,
        chain_path=Path(args.chain_file),
    )
    print(f"Recorded chain entry #{entry['seq']}: {entry['description']}")
    print(f"  Output hash: {entry['output_hash']}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Handle the ``verify`` subcommand."""
    valid, broken = verify_integrity(chain_path=Path(args.chain_file))
    if valid:
        print("Chain integrity verified — no broken links.")
        return 0
    print("Chain integrity FAILED — broken links detected:", file=sys.stderr)
    for link in broken:
        print(f"  - {link}", file=sys.stderr)
    return 1


def _cmd_summary(args: argparse.Namespace) -> int:
    """Handle the ``summary`` subcommand."""
    print(get_summary(task_id=args.task, chain_path=Path(args.chain_file)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="State chain audit trail management.",
    )
    parser.add_argument(
        "--chain-file",
        default=str(CHAIN_FILE),
        help="Path to chain JSON file (default: %(default)s)",
    )

    subs = parser.add_subparsers(dest="command", required=True)

    # -- record --
    rec = subs.add_parser("record", help="Record a new chain entry")
    rec.add_argument("--task", required=True, help="Task/milestone ID (e.g. T05, M2, PLAN)")
    rec.add_argument("--stage", required=True, help="Stage name (e.g. review, verify)")
    rec.add_argument("--agent", required=True, help="Agent name (e.g. code-reviewer, self)")
    rec.add_argument("--input-file", required=True, help="Path to file containing input data")
    rec.add_argument("--output-file", required=True, help="Path to file containing output data")
    rec.add_argument("--description", required=True, help="Human-readable description")
    rec.add_argument("--pipeline", default="", help="Pipeline phase (plan, execute, etc.)")
    rec.add_argument("--verdict", default=None, help="Agent verdict (PASS, CONCERN, BLOCK, ...)")
    rec.add_argument("--metadata", default=None, help="JSON string of extra metadata")

    # -- verify --
    subs.add_parser("verify", help="Verify chain integrity")

    # -- summary --
    summ = subs.add_parser("summary", help="Show chain summary")
    summ.add_argument("--task", default=None, help="Filter to a specific task ID")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "record": _cmd_record,
        "verify": _cmd_verify,
        "summary": _cmd_summary,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

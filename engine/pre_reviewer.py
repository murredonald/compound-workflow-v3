"""Pre-review — fast LLM sanity check before formal code review.

Composes a comprehensive context from task implementation (file contents,
verify results, acceptance criteria, decisions) and generates a structured
review prompt for a fast model (Sonnet) to pre-screen before the expensive
Opus code-reviewer runs.

This catches obvious issues (unmet criteria, verify failures, scope drift)
early, reducing wasted Opus review cycles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field

from core import db
from core.models import (
    MAX_TEXT_LENGTH,
    ReviewVerdict,
    Severity,
    WorkflowModel,
)

if TYPE_CHECKING:
    import sqlite3


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_LINES = 500

BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".o",
    ".db", ".sqlite", ".sqlite3",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
})


# ---------------------------------------------------------------------------
# Models (schema-only — for LLM output reference, not stored in DB)
# ---------------------------------------------------------------------------

class PreReviewFinding(WorkflowModel):
    """A single finding from the pre-reviewer LLM."""

    severity: Severity
    category: str = Field(
        min_length=1,
        description="One of: criteria, decision, verify, gap, scope",
    )
    description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    file: str = ""
    fix_description: str = ""


class PreReviewResult(WorkflowModel):
    """Structured output expected from the pre-reviewer LLM.

    Included in the prompt as a JSON schema reference so the LLM knows
    exactly what structure to return.
    """

    verdict: ReviewVerdict
    findings: list[PreReviewFinding] = Field(default_factory=list)
    criteria_status: dict[str, str] = Field(default_factory=dict)
    summary: str = ""


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def _read_file_contents(
    files: list[str],
    project_root: Path,
    max_lines: int = DEFAULT_MAX_LINES,
) -> dict[str, str]:
    """Read actual file contents from disk for review.

    Truncates large files. Skips binary files. Returns {path: content}
    with forward-slash-normalised keys for cross-platform consistency.
    """
    contents: dict[str, str] = {}

    for f in files:
        # Normalise key to forward slashes
        key = f.replace("\\", "/")

        # Skip binary extensions
        if Path(f).suffix.lower() in BINARY_EXTENSIONS:
            contents[key] = "(binary file, skipped)"
            continue

        full = (project_root / f).resolve()
        if not full.is_relative_to(project_root.resolve()):
            contents[key] = "(path outside project root, skipped)"
            continue
        if not full.exists() or not full.is_file():
            contents[key] = "(file not found)"
            continue

        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            contents[key] = "(read error)"
            continue

        lines = text.splitlines()
        if len(lines) > max_lines:
            text = "\n".join(lines[:max_lines]) + (
                f"\n... (truncated at {max_lines}/{len(lines)} lines)"
            )

        contents[key] = text

    return contents


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_PRE_REVIEW_PROMPT = """\
You are a fast code pre-reviewer. Review the implementation below against \
the task requirements. Be concise — only flag real issues.

## Task: {task_id} — {task_title}

### Goal

{task_goal}

### Acceptance Criteria

{criteria_block}

### Referenced Decisions

{decisions_block}

### Verification Results

{verify_block}

### File Contents

{files_block}

## Instructions

For each acceptance criterion, determine:
- **MET**: criterion is clearly satisfied by the code
- **UNMET**: criterion is not met (cite specific file + reason)
- **UNCLEAR**: cannot determine from the code alone

For each referenced decision, check compliance.

Flag any obvious implementation gaps:
- Empty functions / stub implementations (pass, ..., NotImplementedError)
- Missing error handling for obvious failure modes
- Hardcoded values that should be configurable
- Files in the task plan that are missing or empty

Check scope: are only the planned files present? Any extras?

## Output Format

Return a JSON object:

```json
{{
  "verdict": "pass|concern|block",
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "criteria|decision|verify|gap|scope",
      "description": "what is wrong",
      "file": "path:line (if applicable)",
      "fix_description": "what to do"
    }}
  ],
  "criteria_status": {{
    "criterion text": "met|unmet|unclear"
  }},
  "summary": "1-2 sentence overview"
}}
```

If everything looks good, return verdict "pass" with empty findings.\
"""


# ---------------------------------------------------------------------------
# Main composition
# ---------------------------------------------------------------------------

def compose_pre_review(
    conn: sqlite3.Connection,
    task_id: str,
    project_root: Path,
    verify_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build comprehensive pre-review context with file contents.

    Returns structured context + rendered prompt for an LLM to review.
    The ``review_prompt`` field is the full prompt string to delegate to
    a Sonnet subagent via the Task tool.
    """
    task = db.get_task(conn, task_id)
    if not task:
        return {
            "status": "error",
            "error": f"Task {task_id} not found",
            "fix_hint": "Check task ID format (T01, DF-01, QA-01). "
            "Use 'status' or 'next' to see available tasks.",
        }

    # Fetch referenced decisions (same pattern as compose_review_context)
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

    # Read actual file contents
    all_files = task.files_create + task.files_modify
    file_contents = _read_file_contents(all_files, project_root)

    # Format acceptance criteria
    if task.acceptance_criteria:
        criteria_block = "\n".join(
            f"{i}. {c}" for i, c in enumerate(task.acceptance_criteria, 1)
        )
    else:
        criteria_block = "(none specified)"

    # Format decisions
    if decisions:
        decisions_block = "\n".join(
            f"- **{d.id}**: {d.title}\n  Rationale: {d.rationale}"
            for d in decisions
        )
    else:
        decisions_block = "(none referenced)"

    # Format verify results
    verify_summary = ""
    verify_all_passed = True
    if verify_result:
        verify_summary = verify_result.get("summary", "")
        verify_all_passed = verify_result.get("all_passed", True)
        checks = verify_result.get("checks", [])
        verify_lines: list[str] = []
        for check in checks:
            name = check.get("name", "?")
            passed = check.get("passed", False)
            skipped = check.get("skipped", False)
            status = "SKIP" if skipped else ("PASS" if passed else "FAIL")
            line = f"- {name}: {status}"
            if not passed and not skipped:
                output = check.get("output", "")
                if output:
                    # Truncate per-check output for the prompt
                    out_lines = output.splitlines()[:5]
                    line += "\n  " + "\n  ".join(out_lines)
            verify_lines.append(line)
        verify_block = "\n".join(verify_lines)
    else:
        verify_block = "(no verification results provided)"

    # Format file contents
    files_parts: list[str] = []
    for path, content in file_contents.items():
        ext = Path(path).suffix.lstrip(".")
        files_parts.append(f"#### {path}\n```{ext}\n{content}\n```")
    files_block = "\n\n".join(files_parts) if files_parts else "(no files)"

    # Render prompt
    review_prompt = _PRE_REVIEW_PROMPT.format(
        task_id=task_id,
        task_title=task.title,
        task_goal=task.goal or "(no goal specified)",
        criteria_block=criteria_block,
        decisions_block=decisions_block,
        verify_block=verify_block,
        files_block=files_block,
    )

    return {
        "status": "ok",
        "task_id": task_id,
        "review_prompt": review_prompt,
        "acceptance_criteria": task.acceptance_criteria,
        "decisions": [{"id": d.id, "title": d.title} for d in decisions],
        "file_count": len(file_contents),
        "verify_summary": verify_summary,
        "verify_all_passed": verify_all_passed,
    }

"""Prompt renderer — injects structured DB context into prompt templates.

Takes a prompt template with {{PLACEHOLDER}} markers and replaces them
with formatted data from the orchestrator's context blobs.

This is the bridge between the DB (structured) and Claude (natural language).
The renderer knows how to format decisions, constraints, tasks, etc. into
readable prompt sections.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Core renderer
# ---------------------------------------------------------------------------

def render(template: str, context: dict[str, Any]) -> str:
    """Render a prompt template with context values.

    Supports:
      - {{VARIABLE}}           — simple replacement
      - {{#SECTION}}...{{/SECTION}}  — conditional block (included if key is truthy)
      - {{VARIABLE|default}}   — fallback if key missing/empty

    Structured keys get special formatting:
      - decisions      → format_decisions()
      - constraints    → format_constraints()
      - task           → format_task()
      - sibling_tasks  → format_sibling_tasks()
      - milestones     → format_milestones()
      - decisions_by_prefix → format_decisions_grouped()
    """
    result = template

    # 1. Conditional sections: {{#KEY}}...{{/KEY}}
    result = _render_sections(result, context)

    # 2. Variable replacements: {{KEY}} or {{KEY|default}}
    result = _render_variables(result, context)

    return result


# ---------------------------------------------------------------------------
# Section rendering (conditional blocks)
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(
    r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", re.DOTALL
)


def _render_sections(template: str, context: dict[str, Any]) -> str:
    """Process conditional sections."""
    def _replace_section(match: re.Match[str]) -> str:
        key = match.group(1)
        body = match.group(2)
        value = context.get(key)
        if value:
            # Recursively render the section body
            return render(body.strip(), context)
        return ""

    return _SECTION_RE.sub(_replace_section, template)


# ---------------------------------------------------------------------------
# Variable rendering
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\{\{(\w+)(?:\|([^}]*))?\}\}")


def _render_variables(template: str, context: dict[str, Any]) -> str:
    """Replace {{KEY}} and {{KEY|default}} placeholders."""
    def _replace_var(match: re.Match[str]) -> str:
        key = match.group(1)
        default = match.group(2) or ""
        value = context.get(key)

        if value is None or value == "":
            return default

        # Route structured data to specialised formatters
        return _format_value(key, value)

    return _VAR_RE.sub(_replace_var, template)


def _format_value(key: str, value: Any) -> str:
    """Format a value based on its key name."""
    formatters: dict[str, Callable[[Any], str]] = {
        "decisions": format_decisions,
        "constraints": format_constraints,
        "task": format_task,
        "sibling_tasks": format_sibling_tasks,
        "milestones": format_milestones,
        "decisions_by_prefix": format_decisions_grouped,
        "completed_phases": format_phase_list,
        "pending_phases": format_phase_list,
        "reflexion_entries": format_reflexion_entries,
        "deferred_overlap": format_deferred_findings,
        "review_history": format_review_results,
        "fix_list": format_fix_list,
        "reviewers": format_reviewers,
        "artifacts": format_artifacts,
        "decision_index": format_decision_index,
        "available_artifacts": format_available_artifacts,
        "TASK_SCHEMA": lambda _: get_task_schema(),
        "DECISION_SCHEMA": lambda _: get_decision_schema(),
        "DECOMPOSE_SCHEMA": lambda _: get_decompose_schema(),
        "AUDIT_SCHEMA": lambda _: get_audit_schema(),
    }

    formatter = formatters.get(key)
    if formatter:
        return formatter(value)

    # Fallback: stringify
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value)


# ---------------------------------------------------------------------------
# Structured data formatters
# ---------------------------------------------------------------------------

def format_decisions(decisions: list[dict[str, Any]]) -> str:
    """Format a flat list of decisions into readable blocks."""
    if not decisions:
        return "(none)"

    lines: list[str] = []
    for d in decisions:
        lines.append(f"- **{d['id']}**: {d['title']}")
        lines.append(f"  Rationale: {d['rationale']}")
    return "\n".join(lines)


def format_decisions_grouped(by_prefix: dict[str, list[dict[str, Any]]]) -> str:
    """Format decisions grouped by prefix with headers."""
    if not by_prefix:
        return "(none)"

    sections: list[str] = []
    for prefix, decisions in sorted(by_prefix.items()):
        section_lines = [f"### {prefix} ({len(decisions)} decisions)"]
        for d in decisions:
            section_lines.append(f"- **{d['id']}**: {d['title']}")
            section_lines.append(f"  Rationale: {d['rationale']}")
        sections.append("\n".join(section_lines))
    return "\n\n".join(sections)


def format_constraints(constraints: list[dict[str, Any]]) -> str:
    """Format constraints as a numbered list."""
    if not constraints:
        return "(none)"

    lines: list[str] = []
    for c in constraints:
        lines.append(f"- [{c.get('category', '?')}] {c['description']}")
    return "\n".join(lines)


def format_task(task: dict[str, Any]) -> str:
    """Format a single task for the execution prompt."""
    lines = [
        f"**{task['id']}: {task['title']}**",
        f"Milestone: {task.get('milestone', '?')}",
        f"Goal: {task.get('goal', 'N/A')}",
    ]

    if task.get("depends_on"):
        lines.append(f"Dependencies: {', '.join(task['depends_on'])}")

    if task.get("decision_refs"):
        lines.append(f"Decisions: {', '.join(task['decision_refs'])}")

    if task.get("files_create"):
        lines.append("Files to create:")
        for f in task["files_create"]:
            lines.append(f"  - {f}")

    if task.get("files_modify"):
        lines.append("Files to modify:")
        for f in task["files_modify"]:
            lines.append(f"  - {f}")

    if task.get("acceptance_criteria"):
        lines.append("Acceptance criteria:")
        for i, ac in enumerate(task["acceptance_criteria"], 1):
            lines.append(f"  {i}. {ac}")

    if task.get("verification_cmd"):
        lines.append(f"Verify: `{task['verification_cmd']}`")

    return "\n".join(lines)


def format_sibling_tasks(tasks: list[dict[str, Any]]) -> str:
    """Format sibling tasks as a compact status list."""
    if not tasks:
        return "(none)"

    lines: list[str] = []
    status_icons = {
        "pending": "[ ]",
        "in_progress": "[~]",
        "completed": "[x]",
        "blocked": "[!]",
    }
    for t in tasks:
        icon = status_icons.get(t.get("status", ""), "[ ]")
        lines.append(f"{icon} {t['id']}: {t['title']}")
    return "\n".join(lines)


def format_milestones(milestones: list[dict[str, Any]]) -> str:
    """Format milestones as a summary."""
    if not milestones:
        return "(none)"

    lines: list[str] = []
    for m in milestones:
        lines.append(f"- **{m['id']}**: {m['name']} — {m.get('goal', '')}")
    return "\n".join(lines)


def format_phase_list(phases: list[str]) -> str:
    """Format a list of phase IDs."""
    if not phases:
        return "(none)"
    return ", ".join(phases)


def format_reflexion_entries(entries: list[dict[str, Any]]) -> str:
    """Format reflexion entries for the execution prompt."""
    if not entries:
        return "(none)"

    lines: list[str] = []
    for e in entries:
        cat = e.get("category", "?")
        lesson = e.get("lesson", "")
        task = e.get("task_id", "?")
        lines.append(f"- [{cat}] {lesson} (from {task})")
    return "\n".join(lines)


def format_deferred_findings(findings: list[dict[str, Any]]) -> str:
    """Format deferred findings for prompt display."""
    if not findings:
        return "(none)"

    lines: list[str] = []
    for f in findings:
        fid = f.get("id", "?")
        area = f.get("affected_area", "")
        desc = f.get("description", "")
        lines.append(f"- **{fid}**: {area} — {desc}")
    return "\n".join(lines)


def format_review_results(results: list[dict[str, Any]]) -> str:
    """Format review results (past cycles) for fix context."""
    if not results:
        return "(none)"

    lines: list[str] = []
    for r in results:
        reviewer = r.get("reviewer", "?")
        verdict = r.get("verdict", "?")
        cycle = r.get("cycle", "?")
        n_findings = len(r.get("findings", []))
        lines.append(f"- Cycle {cycle} | {reviewer}: {verdict} ({n_findings} findings)")
        for f in r.get("findings", []):
            sev = f.get("severity", "?")
            desc = f.get("description", "")
            lines.append(f"  - [{sev}] {desc}")
    return "\n".join(lines)


def format_fix_list(findings: list[dict[str, Any]]) -> str:
    """Format a numbered fix list for addressing review findings."""
    if not findings:
        return "(none)"

    lines: list[str] = []
    for i, f in enumerate(findings, 1):
        file_ref = f.get("file", "")
        desc = f.get("description", "")
        fix = f.get("fix_description", "")
        prefix = f"{i}. {file_ref} — {desc}" if file_ref else f"{i}. {desc}"
        if fix:
            prefix += f" → {fix}"
        lines.append(prefix)
    return "\n".join(lines)


def format_reviewers(reviewers: list[str]) -> str:
    """Format reviewer list for display."""
    if not reviewers:
        return "(none)"
    return ", ".join(reviewers)


def format_artifacts(artifacts: dict[str, str]) -> str:
    """Format artifact content for specialist context injection."""
    if not artifacts:
        return "(none)"

    sections: list[str] = []
    for art_type, content in sorted(artifacts.items()):
        label = art_type.replace("-", " ").title()
        sections.append(f"### {label}\n\n{content}")
    return "\n\n".join(sections)


def format_decision_index(index: dict[str, list[dict[str, str]]]) -> str:
    """Format a compact decision index (ID + title only, grouped by prefix)."""
    if not index:
        return "(none)"

    sections: list[str] = []
    for prefix in sorted(index.keys()):
        entries = index[prefix]
        section_lines = [f"**{prefix}** ({len(entries)}):"]
        for entry in entries:
            section_lines.append(f"  - {entry['id']}: {entry['title']}")
        sections.append("\n".join(section_lines))
    return "\n".join(sections)


def format_available_artifacts(artifacts: list[str] | list[dict[str, str]]) -> str:
    """Format available artifact types as a backtick-wrapped list."""
    if not artifacts:
        return "(none)"

    # Handle both list[str] and list[dict] (from list_artifacts)
    names: list[str] = []
    for item in artifacts:
        if isinstance(item, dict):
            names.append(item.get("type", str(item)))
        else:
            names.append(str(item))

    return ", ".join(f"`{name}`" for name in sorted(names))


# ---------------------------------------------------------------------------
# JSON schema references (included in prompts so LLM knows the output format)
# ---------------------------------------------------------------------------

def get_task_schema() -> str:
    """Return the JSON schema for task output that the LLM must produce."""
    return """{
  "milestones": [
    {
      "id": "M1",
      "name": "Foundation",
      "goal": "Core infrastructure",
      "order_index": 0
    }
  ],
  "tasks": [
    {
      "id": "T01",
      "title": "Short imperative title",
      "milestone": "M1",
      "goal": "What this task accomplishes and why",
      "depends_on": [],
      "decision_refs": ["ARCH-01", "ARCH-02"],
      "artifact_refs": ["style-guide", "brand-guide"],
      "files_create": ["src/models/user.py", "src/models/__init__.py"],
      "files_modify": [],
      "acceptance_criteria": [
        "User model created with fields: id, email, name",
        "Database migration runs successfully",
        "Unit tests pass for model validation"
      ],
      "verification_cmd": "pytest tests/models/ -v"
    }
  ]
}"""


def get_decompose_schema() -> str:
    """Return the JSON schema for decompose output that the LLM must produce."""
    return """{
  "subtasks": [
    {
      "id": "T01.1",
      "title": "Short imperative title for subtask",
      "milestone": "M1",
      "goal": "What this subtask accomplishes",
      "depends_on": [],
      "decision_refs": ["BACK-01", "SEC-02"],
      "artifact_refs": ["style-guide", "brand-guide"],
      "files_create": ["src/auth/jwt.py"],
      "files_modify": ["src/config.py"],
      "acceptance_criteria": [
        "JWT token generation works",
        "Token validation middleware passes tests"
      ],
      "verification_cmd": "pytest tests/auth/ -v"
    }
  ],
  "missing_decisions": [
    {
      "decision_id": "SEC-04",
      "reason": "Rate limiting should apply to this endpoint",
      "recommended_subtask": "T01.2"
    }
  ]
}"""


def get_audit_schema() -> str:
    """Return the JSON schema for completeness audit output."""
    return """{
  "journeys": [
    {
      "name": "Journey name (e.g. 'New user registration')",
      "steps": [
        {
          "action": "What the user does",
          "task": "T01.1 or null if no task covers this",
          "status": "covered or missing"
        }
      ]
    }
  ],
  "gaps": [
    {
      "category": "implied-feature | dead-reference | missing-api-contract | incomplete-journey | missing-state | orphaned-component",
      "severity": "critical | high | medium | low",
      "title": "Short gap title",
      "description": "Detailed explanation with task references",
      "trigger": "What triggered this gap (task ID, decision ID, or journey name)",
      "evidence": ["Specific reference 1", "Specific reference 2"],
      "recommendation": "Suggested fix"
    }
  ]
}"""


def get_decision_schema() -> str:
    """Return the JSON schema for decision output."""
    return """{
  "decisions": [
    {
      "id": "BACK-01",
      "prefix": "BACK",
      "number": 1,
      "title": "Short descriptive title",
      "rationale": "Why this decision was made"
    }
  ]
}"""

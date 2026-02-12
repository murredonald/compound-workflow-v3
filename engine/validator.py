"""Validation engine — reusable integrity checks for all pipeline data.

Used by:
  - synthesizer.py (validate LLM-generated tasks before storage)
  - orchestrator.py validate command (on-demand full DB check)
  - planner.py (validate planning completeness)

Every check returns a ValidationResult so callers get structured feedback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.models import Constraint, Decision, DecisionPrefix, Milestone, Task

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Structured validation output."""
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def merge(self, other: ValidationResult) -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Task ID number extraction
# ---------------------------------------------------------------------------

def _extract_task_number(task_id: str) -> int | None:
    """Extract the numeric part from T01, T01.1, DF-01, QA-01 formats.

    For subtask IDs like T01.1, returns the parent number (1).
    """
    m = re.match(r"^T(\d+)(?:\.\d+)?$", task_id)
    if m:
        return int(m.group(1))
    m = re.match(r"^(?:DF|QA)-(\d+)$", task_id)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Task queue validation
# ---------------------------------------------------------------------------

def validate_task_queue(
    tasks: list[Task],
    milestones: list[Milestone],
    decisions: list[Decision],
) -> ValidationResult:
    """Full integrity check on a generated task queue.

    Runs all checks and returns a merged result.
    """
    result = ValidationResult()
    result.merge(check_task_ids(tasks))
    result.merge(check_milestone_refs(tasks, milestones))
    result.merge(check_dependency_refs(tasks))
    result.merge(check_circular_deps(tasks))
    result.merge(check_decision_coverage(tasks, decisions))
    result.merge(check_decision_refs(tasks, decisions))
    result.merge(check_task_completeness(tasks))
    return result


def check_task_ids(tasks: list[Task]) -> ValidationResult:
    """Verify task IDs have no duplicates; T-series are sequential."""
    result = ValidationResult()
    seen: set[str] = set()

    for task in tasks:
        if task.id in seen:
            result.add_error(f"Duplicate task ID: {task.id}")
        seen.add(task.id)

    # Check sequential numbering for T-series only (DF/QA are runtime-generated)
    # Separate parent tasks (T01, T02) from subtasks (T01.1, T01.2)
    t_parents = [t for t in tasks if t.id.startswith("T") and "." not in t.id]
    t_subtasks = [t for t in tasks if t.id.startswith("T") and "." in t.id]

    if t_parents and not t_subtasks:
        # Pure parent queue — check sequential numbering
        numbers = sorted(
            n for t in t_parents if (n := _extract_task_number(t.id)) is not None
        )
        expected = list(range(1, len(t_parents) + 1))
        if numbers != expected:
            result.add_warning(
                f"T-series IDs not sequential: got {numbers}, expected {expected}"
            )
    elif t_parents or t_subtasks:
        # Mixed or pure subtask queue — check parent numbers exist and
        # subtask numbering is sequential within each parent
        parent_nums = {
            _extract_task_number(t.id) for t in t_parents
        } if t_parents else set()
        # Group subtasks by parent
        sub_by_parent: dict[str, list[str]] = {}
        for t in t_subtasks:
            parent_part = t.id.split(".")[0]
            sub_by_parent.setdefault(parent_part, []).append(t.id)
        for parent_id, sub_ids in sub_by_parent.items():
            sub_nums = sorted(int(s.split(".")[1]) for s in sub_ids)
            expected_sub = list(range(1, len(sub_nums) + 1))
            if sub_nums != expected_sub:
                result.add_warning(
                    f"Subtasks of {parent_id} not sequential: "
                    f"got {sub_nums}, expected {expected_sub}"
                )

    return result


def check_milestone_refs(
    tasks: list[Task],
    milestones: list[Milestone],
) -> ValidationResult:
    """Every task must reference an existing milestone."""
    result = ValidationResult()
    milestone_ids = {m.id for m in milestones}

    for task in tasks:
        if task.milestone not in milestone_ids:
            result.add_error(
                f"Task {task.id} references missing milestone '{task.milestone}' "
                f"(available: {sorted(milestone_ids)})"
            )

    # Check every milestone has at least one task
    task_milestones = {t.milestone for t in tasks}
    for m in milestones:
        if m.id not in task_milestones:
            result.add_warning(f"Milestone {m.id} ({m.name}) has no tasks")

    return result


def check_dependency_refs(tasks: list[Task]) -> ValidationResult:
    """Every dependency target must be an existing task ID."""
    result = ValidationResult()
    task_ids = {t.id for t in tasks}

    for task in tasks:
        for dep in task.depends_on:
            if dep not in task_ids:
                result.add_error(
                    f"Task {task.id} depends on missing task '{dep}'"
                )
            if dep == task.id:
                result.add_error(f"Task {task.id} depends on itself")

    return result


def check_circular_deps(tasks: list[Task]) -> ValidationResult:
    """Detect circular dependencies using iterative DFS (3-color)."""
    result = ValidationResult()

    # Build adjacency list
    deps_map: dict[str, list[str]] = {t.id: list(t.depends_on) for t in tasks}

    white, gray, black = 0, 1, 2
    color: dict[str, int] = {t.id: white for t in tasks}

    for start in deps_map:
        if color[start] != white:
            continue
        # Iterative DFS with explicit stack: (node, dep_index)
        stack: list[tuple[str, int]] = [(start, 0)]
        color[start] = gray
        while stack:
            tid, idx = stack[-1]
            deps = deps_map.get(tid, [])
            if idx < len(deps):
                stack[-1] = (tid, idx + 1)
                dep = deps[idx]
                if dep not in color:
                    continue  # Unknown task ID — caught by check_dependency_refs
                if color[dep] == gray:
                    result.add_error(f"Circular dependency: {tid} -> {dep}")
                elif color[dep] == white:
                    color[dep] = gray
                    stack.append((dep, 0))
            else:
                color[tid] = black
                stack.pop()

    return result


def check_decision_coverage(
    tasks: list[Task],
    decisions: list[Decision],
) -> ValidationResult:
    """Every non-GEN decision should be referenced by at least one task."""
    result = ValidationResult()

    # Collect all decision refs across tasks
    covered: set[str] = set()
    for task in tasks:
        covered.update(task.decision_refs)

    # Check coverage
    for d in decisions:
        if d.prefix == DecisionPrefix.GEN:
            continue  # GEN decisions are planning artifacts, not implementation
        if d.id not in covered:
            result.add_warning(f"Decision {d.id} ({d.title}) not covered by any task")

    return result


def check_decision_refs(
    tasks: list[Task],
    decisions: list[Decision],
) -> ValidationResult:
    """Every decision_ref in a task must exist."""
    result = ValidationResult()
    decision_ids = {d.id for d in decisions}

    for task in tasks:
        for ref in task.decision_refs:
            if ref not in decision_ids:
                result.add_warning(
                    f"Task {task.id} references unknown decision '{ref}'"
                )

    return result


def check_task_completeness(tasks: list[Task]) -> ValidationResult:
    """Check that tasks have sufficient detail for execution."""
    result = ValidationResult()

    for task in tasks:
        if not task.goal:
            result.add_warning(f"Task {task.id} has no goal")
        if not task.acceptance_criteria:
            result.add_warning(f"Task {task.id} has no acceptance criteria")
        if not task.decision_refs:
            result.add_warning(f"Task {task.id} references no decisions")
        if not task.files_create and not task.files_modify:
            result.add_warning(f"Task {task.id} has no file lists")

    return result


# ---------------------------------------------------------------------------
# Planning validation
# ---------------------------------------------------------------------------

def validate_planning(
    decisions: list[Decision],
    constraints: list[Constraint] | None = None,
) -> ValidationResult:
    """Check if planning phase produced sufficient output."""
    result = ValidationResult()

    gen_decisions = [d for d in decisions if d.prefix == DecisionPrefix.GEN]

    if len(gen_decisions) < 3:
        result.add_error(
            f"Only {len(gen_decisions)} GEN decisions — minimum 3 required "
            "(app type, target users, MVP scope)"
        )

    # Check key topics by looking at decision content
    all_text = " ".join(d.title.lower() + " " + d.rationale.lower() for d in gen_decisions)

    topic_checks = {
        "app_type": ["app", "web", "mobile", "desktop", "api", "platform", "system", "tool", "service"],
        "users": ["user", "persona", "customer", "audience", "owner", "admin"],
        "scope": ["mvp", "scope", "v1", "core", "feature", "workflow"],
    }

    for topic, keywords in topic_checks.items():
        if not any(kw in all_text for kw in keywords):
            result.add_warning(f"No decision appears to cover '{topic}' — consider adding one")

    if constraints is not None and len(constraints) == 0:
        result.add_warning("No constraints defined — most projects have at least 1")

    return result


# ---------------------------------------------------------------------------
# Specialist validation
# ---------------------------------------------------------------------------

def validate_specialist_output(
    decisions: list[Decision],
    expected_prefix: str,
) -> ValidationResult:
    """Validate decisions produced by a specialist phase."""
    result = ValidationResult()

    if not decisions:
        result.add_error(f"Specialist produced no {expected_prefix} decisions")
        return result

    # All decisions should have the expected prefix
    for d in decisions:
        if d.prefix.value != expected_prefix:
            result.add_error(
                f"Decision {d.id} has prefix {d.prefix.value}, "
                f"expected {expected_prefix}"
            )

    # Check for ID numbering sanity
    numbers = [d.number for d in decisions if d.prefix.value == expected_prefix]
    if numbers and numbers != sorted(numbers):
        result.add_warning(
            f"{expected_prefix} decision numbers not in order: {numbers}"
        )
    if len(numbers) != len(set(numbers)):
        result.add_error(f"Duplicate decision numbers in {expected_prefix}")

    return result


# ---------------------------------------------------------------------------
# Decomposed task validation
# ---------------------------------------------------------------------------

def check_decomposed_coverage(
    subtasks: list[Task],
    parent_tasks: list[Task],
) -> ValidationResult:
    """Verify that decomposed subtasks cover all parent decision_refs.

    For each parent task, checks that the union of its subtasks'
    decision_refs covers all the parent's decision_refs.
    """
    result = ValidationResult()

    # Build parent → subtasks mapping
    parent_to_subs: dict[str, list[Task]] = {}
    for st in subtasks:
        if st.parent_task:
            parent_to_subs.setdefault(st.parent_task, []).append(st)

    for parent in parent_tasks:
        subs = parent_to_subs.get(parent.id, [])
        if not subs:
            continue  # Parent not decomposed — that's fine

        parent_refs = set(parent.decision_refs)
        covered: set[str] = set()
        for sub in subs:
            covered.update(sub.decision_refs)

        uncovered = parent_refs - covered
        if uncovered:
            result.add_error(
                f"Parent {parent.id} decisions not covered by subtasks: "
                f"{sorted(uncovered)}"
            )

    return result

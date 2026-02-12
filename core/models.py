"""Pydantic models for all workflow data types.

Every piece of data that enters or leaves the DB goes through these models.
Validation happens automatically — bad data never reaches SQLite.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TEXT_LENGTH = 2000  # Upper bound for free-text fields


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DecisionPrefix(StrEnum):
    GEN = "GEN"
    DOM = "DOM"
    COMP = "COMP"
    BRAND = "BRAND"
    ARCH = "ARCH"
    BACK = "BACK"
    FRONT = "FRONT"
    STYLE = "STYLE"
    UIX = "UIX"
    SEC = "SEC"
    OPS = "OPS"
    LEGAL = "LEGAL"
    PRICE = "PRICE"
    LLM = "LLM"
    INGEST = "INGEST"
    DATA = "DATA"
    TEST = "TEST"


class PhaseStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReflexionCategory(StrEnum):
    TYPE_MISMATCH = "type-mismatch"
    EDGE_CASE_LOGIC = "edge-case-logic"
    ENV_CONFIG = "env-config"
    API_CONTRACT = "api-contract"
    STATE_MANAGEMENT = "state-management"
    DEPENDENCY = "dependency"
    DECISION_GAP = "decision-gap"
    SCOPE_CREEP = "scope-creep"
    PERFORMANCE = "performance"
    OTHER = "other"


class ArtifactType(StrEnum):
    BRAND_GUIDE = "brand-guide"
    COMPETITION_ANALYSIS = "competition-analysis"
    STYLE_GUIDE = "style-guide"
    DOMAIN_KNOWLEDGE = "domain-knowledge"


class ReviewVerdict(StrEnum):
    PASS = "pass"
    CONCERN = "concern"
    BLOCK = "block"


class DeferredFindingCategory(StrEnum):
    MISSING_FEATURE = "missing-feature"
    MISSING_VALIDATION = "missing-validation"
    MISSING_INTEGRATION = "missing-integration"
    MISSING_TEST = "missing-test"


class AuditGapSeverity(StrEnum):
    CRITICAL = "critical"    # Feature literally broken without this
    HIGH = "high"            # Major user flow incomplete
    MEDIUM = "medium"        # Degraded experience
    LOW = "low"              # Nice-to-have missing


class AuditGapCategory(StrEnum):
    IMPLIED_FEATURE = "implied-feature"
    DEAD_REFERENCE = "dead-reference"
    MISSING_API_CONTRACT = "missing-api-contract"
    INCOMPLETE_JOURNEY = "incomplete-journey"
    MISSING_STATE = "missing-state"
    ORPHANED_COMPONENT = "orphaned-component"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class WorkflowModel(BaseModel):
    """Strict base — no extra fields allowed."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------

_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(\.\d+)?"              # optional fractional seconds
    r"([+-]\d{2}:\d{2}|Z)?$"  # optional timezone offset
)


def _validate_iso_timestamp(v: str | None) -> str | None:
    """Validate an optional ISO timestamp string."""
    if v is None:
        return v
    if not _ISO_RE.match(v):
        raise ValueError(f"Not a valid ISO timestamp: {v!r}")
    return v


# ---------------------------------------------------------------------------
# Pipeline / Phases
# ---------------------------------------------------------------------------

class Phase(WorkflowModel):
    """A single pipeline phase."""

    id: str
    label: str = Field(max_length=MAX_TEXT_LENGTH)
    status: PhaseStatus = PhaseStatus.PENDING
    order_index: int = Field(default=0, ge=0)
    started_at: str | None = None
    completed_at: str | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def validate_timestamps(cls, v: str | None) -> str | None:
        return _validate_iso_timestamp(v)


class Pipeline(WorkflowModel):
    """Top-level pipeline state."""

    project_name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    project_summary: str = Field(
        default="",
        max_length=MAX_TEXT_LENGTH,
        description="Executive summary produced at the end of planning. "
        "Frames decisions and constraints into a coherent project narrative.",
    )
    current_phase: str | None = None
    created_at: str = Field(default_factory=lambda: _now())
    updated_at: str = Field(default_factory=lambda: _now())

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timestamps(cls, v: str) -> str:
        if not _ISO_RE.match(v):
            raise ValueError(f"Not a valid ISO timestamp: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

class Decision(WorkflowModel):
    """A single specialist decision."""

    id: str  # e.g. "ARCH-01"
    prefix: DecisionPrefix
    number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    rationale: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    created_by: str = ""  # which phase produced it
    created_at: str = Field(default_factory=lambda: _now())

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) != 2 or not parts[1].isdigit():
            raise ValueError(f"Decision ID must be PREFIX-NN, got: {v!r}")
        try:
            DecisionPrefix(parts[0])
        except ValueError:
            raise ValueError(
                f"Unknown prefix in decision ID: {parts[0]!r} "
                f"(valid: {', '.join(p.value for p in DecisionPrefix)})"
            ) from None
        return v

    @field_validator("prefix")
    @classmethod
    def validate_prefix_matches_id(cls, v: DecisionPrefix, info: Any) -> DecisionPrefix:
        if "id" in info.data and info.data["id"].split("-")[0] != v.value:
            raise ValueError(
                f"Prefix {v!r} doesn't match ID {info.data['id']!r}"
            )
        return v

    @field_validator("number")
    @classmethod
    def validate_number_matches_id(cls, v: int, info: Any) -> int:
        if "id" in info.data:
            parts = info.data["id"].split("-")
            if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) != v:
                raise ValueError(
                    f"Number {v} doesn't match ID {info.data['id']!r} "
                    f"(expected {int(parts[1])})"
                )
        return v

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: str) -> str:
        if not _ISO_RE.match(v):
            raise ValueError(f"Not a valid ISO timestamp: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

_CONSTRAINT_ID_RE = re.compile(r"^C-\d{2,}$")


class Constraint(WorkflowModel):
    """A hard boundary or technical limit."""

    id: str
    category: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    source: str = ""  # which phase/specialist

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _CONSTRAINT_ID_RE.match(v):
            raise ValueError(f"Constraint ID must be C-NN, got: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

_TASK_ID_RE = re.compile(r"^(T\d{2,}(\.\d+)?|DF-\d{2,}|QA-\d{2,})$")
_MILESTONE_ID_RE = re.compile(r"^M\d+$")


class Task(WorkflowModel):
    """A single executable task."""

    id: str  # T01, T02, ...
    title: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    milestone: str  # M1, M2, ...
    status: TaskStatus = TaskStatus.PENDING
    goal: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    depends_on: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)  # decision IDs
    artifact_refs: list[str] = Field(default_factory=list)  # ArtifactType values
    parent_task: str | None = None  # back-ref e.g. "T01" for subtask "T01.1"
    files_create: list[str] = Field(default_factory=list)
    files_modify: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    verification_cmd: str | None = None

    @field_validator("id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(
                f"Task ID must be T{{NN}}, T{{NN}}.{{N}}, DF-{{NN}}, or QA-{{NN}}, got: {v!r}"
            )
        return v

    @field_validator("milestone")
    @classmethod
    def validate_milestone_ref(cls, v: str) -> str:
        if not _MILESTONE_ID_RE.match(v):
            raise ValueError(f"Milestone ref must be M{{N}}, got: {v!r}")
        return v

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[str]) -> list[str]:
        for dep in v:
            if not _TASK_ID_RE.match(dep):
                raise ValueError(
                    f"depends_on item must be a valid task ID "
                    f"(T{{NN}}, T{{NN}}.{{N}}, DF-{{NN}}, QA-{{NN}}), got: {dep!r}"
                )
        return v

    @field_validator("decision_refs")
    @classmethod
    def validate_decision_refs(cls, v: list[str]) -> list[str]:
        prefixes = {p.value for p in DecisionPrefix}
        for ref in v:
            parts = ref.split("-", 1)
            if len(parts) != 2 or parts[0] not in prefixes or not parts[1].isdigit():
                raise ValueError(
                    f"decision_refs item must be PREFIX-NN (e.g. ARCH-03), got: {ref!r}"
                )
        return v

    @field_validator("artifact_refs")
    @classmethod
    def validate_artifact_refs(cls, v: list[str]) -> list[str]:
        valid = {t.value for t in ArtifactType}
        for ref in v:
            if ref not in valid:
                raise ValueError(
                    f"Unknown artifact type: {ref!r} (valid: {sorted(valid)})"
                )
        return v

    @field_validator("parent_task")
    @classmethod
    def validate_parent_task(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^T\d{2,}$", v):
            raise ValueError(f"parent_task must be a T-series ID, got: {v!r}")
        return v


class DecomposedTask(WorkflowModel):
    """Subtask generated by /decompose. Parsed here, stored as Task."""

    id: str  # T01.1, T01.2
    title: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    milestone: str
    goal: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    depends_on: list[str] = Field(default_factory=list)
    decision_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    files_create: list[str] = Field(default_factory=list)
    files_modify: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    verification_cmd: str | None = None
    parent_task: str  # REQUIRED for decomposed tasks

    @field_validator("id")
    @classmethod
    def validate_subtask_id(cls, v: str) -> str:
        if not re.match(r"^T\d{2,}\.\d+$", v):
            raise ValueError(f"Subtask ID must be T{{NN}}.{{N}}, got: {v!r}")
        return v

    @field_validator("milestone")
    @classmethod
    def validate_milestone_ref(cls, v: str) -> str:
        if not _MILESTONE_ID_RE.match(v):
            raise ValueError(f"Milestone ref must be M{{N}}, got: {v!r}")
        return v

    @field_validator("depends_on")
    @classmethod
    def validate_depends_on(cls, v: list[str]) -> list[str]:
        for dep in v:
            if not _TASK_ID_RE.match(dep):
                raise ValueError(
                    f"depends_on item must be a valid task ID "
                    f"(T{{NN}}, T{{NN}}.{{N}}, DF-{{NN}}, QA-{{NN}}), got: {dep!r}"
                )
        return v

    @field_validator("decision_refs")
    @classmethod
    def validate_decision_refs(cls, v: list[str]) -> list[str]:
        prefixes = {p.value for p in DecisionPrefix}
        for ref in v:
            parts = ref.split("-", 1)
            if len(parts) != 2 or parts[0] not in prefixes or not parts[1].isdigit():
                raise ValueError(
                    f"decision_refs item must be PREFIX-NN (e.g. ARCH-03), got: {ref!r}"
                )
        return v

    @field_validator("artifact_refs")
    @classmethod
    def validate_artifact_refs(cls, v: list[str]) -> list[str]:
        valid = {t.value for t in ArtifactType}
        for ref in v:
            if ref not in valid:
                raise ValueError(
                    f"Unknown artifact type: {ref!r} (valid: {sorted(valid)})"
                )
        return v

    @field_validator("parent_task")
    @classmethod
    def validate_parent_task(cls, v: str) -> str:
        if not re.match(r"^T\d{2,}$", v):
            raise ValueError(f"parent_task must be a T-series ID, got: {v!r}")
        return v


class Milestone(WorkflowModel):
    """A milestone grouping tasks."""

    id: str  # M1, M2, ...
    name: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    goal: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    order_index: int = Field(default=0, ge=0)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _MILESTONE_ID_RE.match(v):
            raise ValueError(f"Milestone ID must be M{{N}}, got: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Test Results (nested in TaskEval)
# ---------------------------------------------------------------------------

class TestResults(WorkflowModel):
    """Test execution results — nested inside TaskEval."""

    __test__ = False  # Not a pytest test class

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)

    @model_validator(mode="after")
    def check_counts_consistent(self) -> TestResults:
        parts = self.passed + self.failed + self.skipped
        if parts > self.total:
            raise ValueError(
                f"passed + failed + skipped ({parts}) exceeds total ({self.total})"
            )
        return self


# ---------------------------------------------------------------------------
# Reflexion
# ---------------------------------------------------------------------------

_REFLEXION_ID_RE = re.compile(r"^R\d{3,}$")


class ReflexionEntry(WorkflowModel):
    """A single reflexion entry — a lesson learned from a task."""

    id: str  # R001, R002, ...
    timestamp: str = Field(default_factory=lambda: _now())
    task_id: str  # T01, DF-01, QA-01
    tags: list[str] = Field(default_factory=list)
    category: ReflexionCategory
    severity: Severity
    what_happened: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    root_cause: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    lesson: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    applies_to: list[str] = Field(default_factory=list)
    preventive_action: str = Field(default="", max_length=MAX_TEXT_LENGTH)

    @field_validator("id")
    @classmethod
    def validate_reflexion_id(cls, v: str) -> str:
        if not _REFLEXION_ID_RE.match(v):
            raise ValueError(f"Reflexion ID must be R{{NNN}}, got: {v!r}")
        return v

    @field_validator("task_id")
    @classmethod
    def validate_task_ref(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(
                f"Task ID must be T{{NN}}, DF-{{NN}}, or QA-{{NN}}, got: {v!r}"
            )
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        if not _ISO_RE.match(v):
            raise ValueError(f"Not a valid ISO timestamp: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Task Evals
# ---------------------------------------------------------------------------

class TaskEval(WorkflowModel):
    """Per-task execution metrics — review cycles, test results, scope drift."""

    task_id: str  # T01, DF-01, QA-01
    milestone: str  # M1, M2
    status: TaskStatus
    started_at: str
    completed_at: str | None = None
    review_cycles: int = Field(default=0, ge=0)
    security_review: bool = False
    test_results: TestResults = Field(
        default_factory=lambda: TestResults(total=0, passed=0, failed=0, skipped=0)
    )
    files_planned: list[str] = Field(default_factory=list)
    files_touched: list[str] = Field(default_factory=list)
    scope_violations: int = Field(default=0, ge=0)
    reflexion_entries_created: int = Field(default=0, ge=0)
    notes: str = Field(default="", max_length=MAX_TEXT_LENGTH)

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(
                f"Task ID must be T{{NN}}, DF-{{NN}}, or QA-{{NN}}, got: {v!r}"
            )
        return v

    @field_validator("milestone")
    @classmethod
    def validate_milestone_ref(cls, v: str) -> str:
        if not _MILESTONE_ID_RE.match(v):
            raise ValueError(f"Milestone ref must be M{{N}}, got: {v!r}")
        return v

    @field_validator("started_at")
    @classmethod
    def validate_started_at(cls, v: str) -> str:
        if not _ISO_RE.match(v):
            raise ValueError(f"Not a valid ISO timestamp: {v!r}")
        return v

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: str | None) -> str | None:
        return _validate_iso_timestamp(v)

    @model_validator(mode="after")
    def check_timestamps_ordered(self) -> TaskEval:
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError(
                f"completed_at ({self.completed_at}) is before "
                f"started_at ({self.started_at})"
            )
        return self


# ---------------------------------------------------------------------------
# Review Results
# ---------------------------------------------------------------------------


class ReviewFinding(WorkflowModel):
    """A single finding from a reviewer.

    The `id` and `category` fields have defaults so reviewers can omit them:
    - `id` defaults to 0 and is auto-assigned by record_review if missing
    - `category` defaults to "general" for uncategorised findings
    """

    id: int = Field(default=0, ge=0)
    severity: Severity
    category: str = Field(default="general", min_length=1)
    description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    file: str = ""  # file:line reference
    decision_ref: str = ""  # ARCH-01 etc if related
    fix_description: str = ""  # what "done" looks like


class ReviewResult(WorkflowModel):
    """Structured output from a single reviewer."""

    reviewer: str = Field(min_length=1)  # code-reviewer, security-auditor, gpt, gemini
    task_id: str
    verdict: ReviewVerdict
    cycle: int = Field(default=1, ge=1)
    findings: list[ReviewFinding] = Field(default_factory=list)
    criteria_assessed: int = Field(default=0, ge=0)
    criteria_passed: int = Field(default=0, ge=0)
    criteria_failed: int = Field(default=0, ge=0)
    scope_issues: list[str] = Field(default_factory=list)
    decision_compliance: dict[str, str] = Field(default_factory=dict)
    raw_output: str = Field(default="", max_length=50000)
    created_at: str = Field(default_factory=lambda: _now())

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(
                f"Task ID must be T{{NN}}, DF-{{NN}}, or QA-{{NN}}, got: {v!r}"
            )
        return v

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: str) -> str:
        if not _ISO_RE.match(v):
            raise ValueError(f"Not a valid ISO timestamp: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Deferred Findings
# ---------------------------------------------------------------------------

_DF_ID_RE = re.compile(r"^DF-\d{2,}$")


class DeferredFindingStatus(StrEnum):
    OPEN = "open"
    PROMOTED = "promoted"
    DEFERRED_POST_V1 = "deferred-post-v1"
    DISMISSED = "dismissed"


class DeferredFinding(WorkflowModel):
    """A scope gap discovered during execution."""

    id: str  # DF-01, DF-02
    discovered_in: str  # T{NN} where found
    category: DeferredFindingCategory
    affected_area: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    files_likely: list[str] = Field(default_factory=list)
    spec_reference: str = ""
    description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    status: DeferredFindingStatus = DeferredFindingStatus.OPEN

    @field_validator("id")
    @classmethod
    def validate_df_id(cls, v: str) -> str:
        if not _DF_ID_RE.match(v):
            raise ValueError(f"Deferred finding ID must be DF-NN, got: {v!r}")
        return v

    @field_validator("discovered_in")
    @classmethod
    def validate_task_ref(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(
                f"Task ID must be T{{NN}}, DF-{{NN}}, or QA-{{NN}}, got: {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Audit Gaps (completeness audit)
# ---------------------------------------------------------------------------

_GAP_ID_RE = re.compile(r"^GAP-\d{2,}$")

_VALID_GAP_LAYERS = {"implication", "contract", "journey"}
_VALID_GAP_STATUSES = {"open", "accepted", "dismissed", "deferred"}


class AuditGap(WorkflowModel):
    """A completeness gap found by the audit."""

    id: str                           # GAP-01, GAP-02
    category: AuditGapCategory
    severity: AuditGapSeverity
    layer: str                        # "implication", "contract", "journey"
    title: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    description: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    trigger: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    evidence: list[str] = Field(default_factory=list)
    recommendation: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    status: str = "open"              # open, accepted, dismissed, deferred
    resolved_by: str = Field(default="", max_length=MAX_TEXT_LENGTH)  # Task ID that addresses this gap

    @field_validator("id")
    @classmethod
    def validate_gap_id(cls, v: str) -> str:
        if not _GAP_ID_RE.match(v):
            raise ValueError(f"Gap ID must be GAP-NN, got: {v!r}")
        return v

    @field_validator("layer")
    @classmethod
    def validate_layer(cls, v: str) -> str:
        if v not in _VALID_GAP_LAYERS:
            raise ValueError(
                f"Layer must be one of {sorted(_VALID_GAP_LAYERS)}, got: {v!r}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_GAP_STATUSES:
            raise ValueError(
                f"Status must be one of {sorted(_VALID_GAP_STATUSES)}, got: {v!r}"
            )
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

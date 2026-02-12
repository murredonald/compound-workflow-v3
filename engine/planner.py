"""Planning phase — structures the discovery conversation.

This module doesn't replace Claude's creative planning work.
It provides:
  1. A question framework to guide the conversation
  2. Decision/constraint builders with Pydantic validation
  3. Phase completion checks via the validator module
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core import db

if TYPE_CHECKING:
    import sqlite3
from core.models import Constraint, Decision, DecisionPrefix
from engine.validator import ValidationResult, validate_planning

# ---------------------------------------------------------------------------
# Planning question framework
# ---------------------------------------------------------------------------

PLANNING_STAGES: list[dict[str, str]] = [
    {
        "stage": "vision",
        "question": "What is the core problem this project solves?",
        "produces": "GEN-01 style decisions about app type and purpose",
    },
    {
        "stage": "users",
        "question": "Who are the primary users? What are their goals?",
        "produces": "GEN decisions about user personas and priorities",
    },
    {
        "stage": "workflows",
        "question": "What are the 3-5 core workflows users will perform?",
        "produces": "GEN decisions about feature scope",
    },
    {
        "stage": "scope",
        "question": "What is IN scope for v1 and what is OUT?",
        "produces": "GEN decisions about MVP boundaries",
    },
    {
        "stage": "constraints",
        "question": "What are the hard constraints? (tech, budget, timeline, regs)",
        "produces": "Constraints + GEN decisions about technical choices",
    },
    {
        "stage": "risks",
        "question": "What are the top 3 risks and how will we mitigate them?",
        "produces": "GEN decisions about risk mitigation strategies",
    },
]


def get_planning_stages() -> list[dict[str, str]]:
    """Return the structured question framework."""
    return PLANNING_STAGES


# ---------------------------------------------------------------------------
# Decision / constraint builders
# ---------------------------------------------------------------------------

def build_decision(
    prefix: str,
    number: int,
    title: str,
    rationale: str,
    created_by: str = "plan",
) -> Decision:
    """Build and validate a single decision."""
    return Decision(
        id=f"{prefix}-{number:02d}",
        prefix=DecisionPrefix(prefix),
        number=number,
        title=title,
        rationale=rationale,
        created_by=created_by,
    )


def build_constraint(
    number: int,
    category: str,
    description: str,
    source: str = "plan",
) -> Constraint:
    """Build and validate a single constraint."""
    return Constraint(
        id=f"C-{number:02d}",
        category=category,
        description=description,
        source=source,
    )


# ---------------------------------------------------------------------------
# Completion check (delegates to validator)
# ---------------------------------------------------------------------------

def check_planning_complete(conn: sqlite3.Connection) -> ValidationResult:
    """Check if planning produced sufficient decisions to proceed.

    Uses the validator module for real content analysis instead of
    simple string matching.
    """
    decisions = db.get_decisions(conn)
    constraints = db.get_constraints(conn)
    return validate_planning(decisions, constraints)

"""Completeness audit engine — catch implied features before /execute.

Three layers (post-synthesize, pre-execute):
  1. Feature Implication Rules (deterministic) — auth without logout, RAG without chunking
  2. Cross-Task Contract Checks (deterministic) — frontend API calls without backend endpoints
  3. User Journey Tracing (LLM) — dead-end pages, incomplete flows

Early detection (post-specialist, pre-synthesize):
  check_decision_implications()   → Implication rules on decisions only
  check_decision_cross_refs()     → Cross-domain contract checks between decision prefixes
  run_specialist_exit_check()     → Orchestrates both for a specialist session

Pipeline:
  run_deterministic_audit()  → Layer 1+2 gaps + LLM prompt for Layer 3
  parse_audit_output()       → Parse LLM JSON into AuditGap objects
  run_full_audit()           → Merge deterministic + LLM gaps
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

from core import db
from core.models import (
    AuditGap,
    AuditGapCategory,
    AuditGapSeverity,
    Decision,
    Task,
)
from engine.composer import load_prompt
from engine.renderer import get_audit_schema, render

# ---------------------------------------------------------------------------
# Data structures for implication rules
# ---------------------------------------------------------------------------


@dataclass
class Requirement:
    """A feature that must/should exist when a rule triggers."""

    name: str
    search_terms: list[str]
    severity: str  # "critical" or "high" or "medium"
    category: str = "implied-feature"


@dataclass
class ImplicationRule:
    """Maps feature triggers to required companion features."""

    name: str
    triggers: list[str]
    requires: list[Requirement] = field(default_factory=list)
    suggests: list[Requirement] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Feature implication rules (~15 domains)
# ---------------------------------------------------------------------------

IMPLICATION_RULES: list[ImplicationRule] = [
    ImplicationRule(
        name="authentication",
        triggers=["login", "register", "sign up", "signup", "auth", "jwt", "session"],
        requires=[
            Requirement("logout", ["logout", "sign out", "signout", "log out"], "critical"),
            Requirement("password reset", ["password reset", "forgot password", "recover password"], "high"),
            Requirement("session expiry", ["session expir", "token expir", "token refresh", "session timeout"], "medium"),
        ],
    ),
    ImplicationRule(
        name="user-profile",
        triggers=["profile", "avatar", "account settings", "user settings"],
        requires=[
            Requirement("profile page", ["profile page", "profile view", "user profile", "account page"], "high"),
            Requirement("profile edit", ["edit profile", "update profile", "profile form", "profile edit"], "high"),
        ],
    ),
    ImplicationRule(
        name="crud-resources",
        triggers=["crud", "crud operations", "create and delete", "create, read, update"],
        requires=[
            Requirement("list view", ["list view", "list page", "index page", "browse", "all items"], "high"),
            Requirement("empty state", ["empty state", "no results", "no items", "empty list", "zero state"], "medium"),
            Requirement("error state", ["error state", "error handling", "error page", "error message"], "medium"),
            Requirement("delete confirmation", ["delete confirm", "confirm delete", "delete dialog", "confirm removal"], "medium"),
        ],
    ),
    ImplicationRule(
        name="search",
        triggers=["search", "search bar", "search feature", "full-text search", "search page"],
        requires=[
            Requirement("search results", ["search results", "results page", "search output"], "high"),
            Requirement("empty results", ["no results", "empty search", "no matches", "zero results"], "medium"),
        ],
    ),
    ImplicationRule(
        name="rag-ai",
        triggers=["rag", "retrieval augmented", "knowledge base", "embeddings", "vector"],
        requires=[
            Requirement("chunking", ["chunk", "split", "segment", "tokeniz"], "critical"),
            Requirement("embedding pipeline", ["embed", "vectoriz", "encoding pipeline"], "critical"),
            Requirement("vector store", ["vector store", "vector db", "pinecone", "chromadb", "qdrant", "weaviate", "pgvector"], "critical"),
            Requirement("retrieval endpoint", ["retrieval", "search endpoint", "query endpoint", "retrieve"], "high"),
        ],
    ),
    ImplicationRule(
        name="file-upload",
        triggers=["upload", "attachment", "file upload"],
        requires=[
            Requirement("storage backend", ["storage", "s3", "blob", "file storage", "upload storage"], "critical"),
            Requirement("file validation", ["file validat", "file type", "file size", "mime type", "allowed types"], "high"),
            Requirement("upload progress", ["upload progress", "progress bar", "upload status"], "medium"),
        ],
    ),
    ImplicationRule(
        name="notifications",
        triggers=["notification", "alert", "push notification"],
        requires=[
            Requirement("delivery mechanism", ["email delivery", "push delivery", "notification service", "notification send"], "high"),
            Requirement("notification preferences", ["notification preference", "notification setting", "unsubscribe", "opt out"], "medium"),
            Requirement("mark as read", ["mark as read", "read status", "notification dismiss", "clear notification"], "medium"),
        ],
    ),
    ImplicationRule(
        name="navigation",
        triggers=["navbar", "sidebar", "navigation bar", "navigation menu", "site navigation"],
        requires=[
            Requirement("404 page", ["404", "not found", "page not found", "missing page"], "high"),
        ],
    ),
    ImplicationRule(
        name="payment",
        triggers=["payment", "billing", "subscription", "checkout", "stripe", "paypal"],
        requires=[
            Requirement("payment confirmation", ["payment confirm", "order confirm", "receipt", "success page"], "critical"),
            Requirement("cancellation", ["cancel", "refund", "unsubscribe", "downgrade"], "high"),
        ],
    ),
    ImplicationRule(
        name="real-time",
        triggers=["websocket", "real-time", "realtime", "live update", "socket.io"],
        requires=[
            Requirement("reconnection", ["reconnect", "connection lost", "retry connection"], "high"),
            Requirement("offline fallback", ["offline", "fallback", "degraded mode", "connection error"], "medium"),
        ],
    ),
    ImplicationRule(
        name="email",
        triggers=["email verification", "email confirm", "invite email", "send email"],
        requires=[
            Requirement("email templates", ["email template", "html email", "email layout"], "high"),
            Requirement("delivery service", ["smtp", "sendgrid", "ses", "mailgun", "email service", "email provider"], "high"),
        ],
    ),
    ImplicationRule(
        name="multi-tenant",
        triggers=["workspace", "team", "organization", "tenant", "multi-tenant"],
        requires=[
            Requirement("workspace switching", ["switch workspace", "workspace select", "change organization"], "high"),
            Requirement("member invite", ["invite member", "add member", "team invite", "invite user"], "high"),
            Requirement("role management", ["role", "permission", "access control", "rbac"], "high"),
        ],
    ),
    ImplicationRule(
        name="dashboard",
        triggers=["dashboard", "analytics", "metrics", "statistics"],
        requires=[
            Requirement("data aggregation", ["aggregat", "summariz", "roll up", "compute metrics"], "high"),
            Requirement("date range", ["date range", "date picker", "time period", "date filter"], "medium"),
        ],
    ),
    ImplicationRule(
        name="forms",
        triggers=["form submission", "form validation", "input form", "contact form", "registration form"],
        requires=[
            Requirement("error messages", ["error message", "validation error", "field error", "form error", "invalid input"], "high"),
            Requirement("success state", ["success message", "form success", "submit success", "confirmation"], "medium"),
        ],
    ),
    ImplicationRule(
        name="pagination",
        triggers=["paginate", "pagination", "infinite scroll", "load more"],
        requires=[
            Requirement("loading state", ["loading state", "loading indicator", "spinner", "skeleton"], "medium"),
        ],
    ),
]

# ---------------------------------------------------------------------------
# API contract patterns for cross-task checking
# ---------------------------------------------------------------------------

# Regex patterns that suggest frontend → backend API calls
_API_CALL_PATTERNS = [
    re.compile(r"\b(?:fetch|post|put|patch|delete|get)\s*\(\s*['\"/]", re.IGNORECASE),
    re.compile(r"/api/\w+", re.IGNORECASE),
    re.compile(r"\bapi\s+(?:call|request|endpoint)", re.IGNORECASE),
    re.compile(r"\bREST\s+(?:api|endpoint|call)", re.IGNORECASE),
    re.compile(r"\bPOST(?:s)?\s+(?:to|data)", re.IGNORECASE),
]

# Patterns that suggest a task creates API endpoints
_API_ENDPOINT_PATTERNS = [
    re.compile(r"\b(?:api|endpoint|route)\b.*\b(?:creat|implement|build|add)\b", re.IGNORECASE),
    re.compile(r"\b(?:creat|implement|build|add)\b.*\b(?:api|endpoint|route)\b", re.IGNORECASE),
    re.compile(r"\bREST\s+(?:api|endpoint)", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Layer 1: Feature Implication Checking
# ---------------------------------------------------------------------------

def _build_corpus(decisions: list[Decision], tasks: list[Task]) -> str:
    """Build a searchable text corpus from decisions and tasks."""
    parts: list[str] = []
    for d in decisions:
        parts.append(d.title.lower())
        parts.append(d.rationale.lower())
    for t in tasks:
        parts.append(t.title.lower())
        parts.append(t.goal.lower())
        for ac in t.acceptance_criteria:
            parts.append(ac.lower())
    return " ".join(parts)


def _terms_in_corpus(terms: list[str], corpus: str) -> bool:
    """Check if ANY of the search terms appear in the corpus."""
    return any(term.lower() in corpus for term in terms)


def check_feature_implications(
    decisions: list[Decision],
    tasks: list[Task],
) -> list[AuditGap]:
    """Layer 1: Scan decisions and tasks for trigger patterns, check required features exist."""
    corpus = _build_corpus(decisions, tasks)
    gaps: list[AuditGap] = []
    gap_num = 0

    for rule in IMPLICATION_RULES:
        # Check if ANY trigger word appears in the corpus
        triggered = _terms_in_corpus(rule.triggers, corpus)
        if not triggered:
            continue

        # Find which trigger matched (for evidence)
        matched_triggers = [t for t in rule.triggers if t.lower() in corpus]

        # Check each required feature
        for req in rule.requires:
            if not _terms_in_corpus(req.search_terms, corpus):
                gap_num += 1
                evidence = [
                    f"Trigger '{matched_triggers[0]}' found in task queue",
                    f"No task mentions any of: {', '.join(req.search_terms[:3])}",
                ]
                gaps.append(AuditGap(
                    id=f"GAP-{gap_num:02d}",
                    category=AuditGapCategory(req.category),
                    severity=AuditGapSeverity(req.severity),
                    layer="implication",
                    title=f"Missing {req.name} (implied by {rule.name})",
                    description=(
                        f"The task queue includes {rule.name} features "
                        f"(trigger: '{matched_triggers[0]}') but no task "
                        f"covers {req.name}."
                    ),
                    trigger=f"rule:{rule.name}",
                    evidence=evidence,
                    recommendation=f"Add a task for: {req.name}",
                ))

        # Suggested features generate lower-severity gaps
        for req in rule.suggests:
            if not _terms_in_corpus(req.search_terms, corpus):
                gap_num += 1
                gaps.append(AuditGap(
                    id=f"GAP-{gap_num:02d}",
                    category=AuditGapCategory(req.category),
                    severity=AuditGapSeverity.LOW,
                    layer="implication",
                    title=f"Consider adding {req.name} (suggested by {rule.name})",
                    description=(
                        f"The task queue includes {rule.name} features "
                        f"but {req.name} is not covered. This is recommended "
                        f"but not critical."
                    ),
                    trigger=f"rule:{rule.name}",
                    evidence=[f"Trigger found for {rule.name}, no match for {req.name}"],
                    recommendation=f"Consider adding: {req.name}",
                ))

    return gaps


# ---------------------------------------------------------------------------
# Layer 2: Cross-Task Contract Checking
# ---------------------------------------------------------------------------

def _task_text(task: Task) -> str:
    """Combine task fields into searchable text."""
    parts = [task.title, task.goal]
    parts.extend(task.acceptance_criteria)
    return " ".join(parts)


def _is_frontend_task(task: Task) -> bool:
    """Check if a task is primarily frontend."""
    refs = task.decision_refs
    text = _task_text(task).lower()
    has_front_ref = any(r.startswith("FRONT-") or r.startswith("STYLE-") or r.startswith("UIX-") for r in refs)
    has_front_keywords = any(kw in text for kw in ["frontend", "ui ", "component", "page", "view", "react", "vue", "angular", "css", "html"])
    return has_front_ref or has_front_keywords


def _is_backend_task(task: Task) -> bool:
    """Check if a task is primarily backend."""
    refs = task.decision_refs
    text = _task_text(task).lower()
    has_back_ref = any(r.startswith("BACK-") or r.startswith("ARCH-") for r in refs)
    has_back_keywords = any(kw in text for kw in ["backend", "endpoint", "server", "database", "model", "migration"])
    return has_back_ref or has_back_keywords


def _mentions_api_call(text: str) -> bool:
    """Check if text suggests an API call is being made."""
    return any(p.search(text) for p in _API_CALL_PATTERNS)


def _mentions_api_endpoint(text: str) -> bool:
    """Check if text suggests an API endpoint is being created."""
    return any(p.search(text) for p in _API_ENDPOINT_PATTERNS)


def check_cross_task_contracts(
    tasks: list[Task],
    decisions: list[Decision],
) -> list[AuditGap]:
    """Layer 2: Check that frontend and backend tasks have matching contracts."""
    gaps: list[AuditGap] = []
    gap_num = 0

    frontend_tasks = [t for t in tasks if _is_frontend_task(t)]
    backend_tasks = [t for t in tasks if _is_backend_task(t)]

    # Build searchable backend corpus
    backend_corpus = " ".join(_task_text(t) for t in backend_tasks).lower()

    # Check 1: Frontend tasks that reference API calls → verify backend task exists
    for ft in frontend_tasks:
        ft_text = _task_text(ft)
        if _mentions_api_call(ft_text):
            # Check if any backend task covers this
            if not backend_tasks:
                gap_num += 1
                gaps.append(AuditGap(
                    id=f"GAP-{gap_num:02d}",
                    category=AuditGapCategory.MISSING_API_CONTRACT,
                    severity=AuditGapSeverity.CRITICAL,
                    layer="contract",
                    title=f"Frontend task {ft.id} calls API but no backend tasks exist",
                    description=(
                        f"Task {ft.id} ({ft.title}) appears to make API calls "
                        f"but there are no backend tasks in the queue."
                    ),
                    trigger=ft.id,
                    evidence=[f"Task {ft.id} text suggests API call", "No backend tasks found"],
                    recommendation="Add backend API endpoint tasks",
                ))

    # Check 2: Frontend tasks referencing specific API paths
    api_path_re = re.compile(r"/api/[\w/\-]+", re.IGNORECASE)
    for ft in frontend_tasks:
        ft_text = _task_text(ft)
        api_paths = api_path_re.findall(ft_text)
        for path in api_paths:
            path_lower = path.lower()
            if path_lower not in backend_corpus:
                gap_num += 1
                gaps.append(AuditGap(
                    id=f"GAP-{gap_num:02d}",
                    category=AuditGapCategory.MISSING_API_CONTRACT,
                    severity=AuditGapSeverity.HIGH,
                    layer="contract",
                    title=f"No backend task for {path} (referenced by {ft.id})",
                    description=(
                        f"Task {ft.id} ({ft.title}) references API path '{path}' "
                        f"but no backend task mentions this path."
                    ),
                    trigger=ft.id,
                    evidence=[f"Task {ft.id} references '{path}'", "Path not found in any backend task"],
                    recommendation=f"Add a backend task implementing {path}",
                ))

    return gaps


# ---------------------------------------------------------------------------
# Early Detection: Decision-Level Checks (specialist exit)
# ---------------------------------------------------------------------------

# Cross-domain contracts between decision prefixes.
# If a decision in source_prefix mentions any trigger word,
# we check that at least one decision exists in target_prefix.
@dataclass
class CrossDomainContract:
    """A contract between two decision domains."""

    source_prefix: str
    triggers: list[str]     # keywords in source decision title/rationale
    target_prefix: str
    message: str            # what's missing

_CROSS_DOMAIN_CONTRACTS: list[CrossDomainContract] = [
    # Frontend → Backend
    CrossDomainContract("FRONT", ["api", "endpoint", "fetch", "backend", "server", "REST"],
                        "BACK", "Frontend references backend functionality"),
    # Backend → Frontend
    CrossDomainContract("BACK", ["page", "form", "ui", "frontend", "component", "screen", "view", "dashboard"],
                        "FRONT", "Backend references frontend functionality"),
    # Any → Security
    CrossDomainContract("FRONT", ["auth", "login", "permission", "role", "protect", "password"],
                        "SEC", "Frontend references security functionality"),
    CrossDomainContract("BACK", ["auth", "login", "permission", "role", "protect", "encrypt", "token", "jwt"],
                        "SEC", "Backend references security functionality"),
    # Frontend → Design
    CrossDomainContract("FRONT", ["theme", "dark mode", "responsive", "mobile", "layout", "style"],
                        "STYLE", "Frontend references design decisions"),
    # Backend → DevOps
    CrossDomainContract("BACK", ["deploy", "ci/cd", "docker", "kubernetes", "scaling", "monitoring", "logging"],
                        "OPS", "Backend references infrastructure"),
    # Any → Testing
    CrossDomainContract("BACK", ["test", "e2e", "integration test", "unit test"],
                        "TEST", "Backend references testing strategy"),
    CrossDomainContract("FRONT", ["test", "e2e", "integration test", "visual test", "snapshot"],
                        "TEST", "Frontend references testing strategy"),
    # LLM → Backend
    CrossDomainContract("LLM", ["api", "endpoint", "backend", "server", "queue", "webhook"],
                        "BACK", "LLM decisions reference backend infrastructure"),
    # Scraping → Backend
    CrossDomainContract("INGEST", ["store", "database", "pipeline", "queue", "backend"],
                        "BACK", "Scraping decisions reference backend infrastructure"),
    # Payment → Security + Legal
    CrossDomainContract("PRICE", ["payment", "billing", "stripe", "paypal", "pci"],
                        "SEC", "Pricing references security (PCI compliance)"),
    CrossDomainContract("PRICE", ["terms", "refund", "subscription", "gdpr", "tax"],
                        "LEGAL", "Pricing references legal obligations"),
]


def _build_decision_corpus(decisions: list[Decision]) -> str:
    """Build a searchable text corpus from decisions only."""
    parts: list[str] = []
    for d in decisions:
        parts.append(d.title.lower())
        parts.append(d.rationale.lower())
    return " ".join(parts)


def check_decision_implications(
    decisions: list[Decision],
) -> list[dict[str, Any]]:
    """Run implication rules against decisions only (pre-task, specialist time).

    Returns lightweight warning dicts (not AuditGap — we're pre-audit).
    Each dict has: rule, severity, title, description, evidence.
    """
    corpus = _build_decision_corpus(decisions)
    warnings: list[dict[str, Any]] = []

    for rule in IMPLICATION_RULES:
        triggered = _terms_in_corpus(rule.triggers, corpus)
        if not triggered:
            continue

        matched_triggers = [t for t in rule.triggers if t.lower() in corpus]

        for req in rule.requires:
            if not _terms_in_corpus(req.search_terms, corpus):
                warnings.append({
                    "type": "implication",
                    "rule": rule.name,
                    "severity": req.severity,
                    "title": f"Missing {req.name} (implied by {rule.name})",
                    "description": (
                        f"Decisions mention {rule.name} features "
                        f"(trigger: '{matched_triggers[0]}') but no decision "
                        f"covers {req.name}. This will likely become a gap."
                    ),
                    "evidence": [
                        f"Trigger '{matched_triggers[0]}' found in decisions",
                        f"No decision mentions: {', '.join(req.search_terms[:3])}",
                    ],
                })

    return warnings


def check_decision_cross_refs(
    decisions: list[Decision],
    current_prefix: str,
) -> list[dict[str, Any]]:
    """Check if current specialist's decisions imply work in other domains.

    Only checks contracts where source_prefix matches current_prefix.
    Checks if target_prefix has ANY decisions at all (not specific keywords —
    just "does the target domain exist in the DB yet?").

    Returns lightweight warning dicts.
    """
    warnings: list[dict[str, Any]] = []

    # Group decisions by prefix
    by_prefix: dict[str, list[Decision]] = {}
    for d in decisions:
        by_prefix.setdefault(d.prefix.value, []).append(d)

    current_decisions = by_prefix.get(current_prefix, [])
    if not current_decisions:
        return warnings

    # Build corpus for just the current specialist's decisions
    current_corpus = _build_decision_corpus(current_decisions)

    for contract in _CROSS_DOMAIN_CONTRACTS:
        if contract.source_prefix != current_prefix:
            continue

        # Check if any trigger word appears in current specialist's decisions
        triggered = _terms_in_corpus(contract.triggers, current_corpus)
        if not triggered:
            continue

        matched_triggers = [t for t in contract.triggers if t.lower() in current_corpus]

        # Check if target domain has ANY decisions
        target_decisions = by_prefix.get(contract.target_prefix, [])
        if not target_decisions:
            warnings.append({
                "type": "cross-domain",
                "source": current_prefix,
                "target": contract.target_prefix,
                "severity": "high",
                "title": f"No {contract.target_prefix} decisions yet — {contract.message}",
                "description": (
                    f"{current_prefix} decision mentions '{matched_triggers[0]}' "
                    f"which implies {contract.target_prefix} decisions are needed, "
                    f"but no {contract.target_prefix} specialist has run yet."
                ),
                "evidence": [
                    f"Trigger '{matched_triggers[0]}' in {current_prefix} decisions",
                    f"No {contract.target_prefix}-* decisions in DB",
                ],
                "recommendation": f"Run /specialists/{_prefix_to_specialist(contract.target_prefix)} before /synthesize",
            })
            continue

        # Target domain exists — check if it covers the triggering concept
        target_corpus = _build_decision_corpus(target_decisions)
        # Check if any of the trigger words appear in the target domain too
        covered = _terms_in_corpus(contract.triggers, target_corpus)
        if not covered:
            warnings.append({
                "type": "cross-domain",
                "source": current_prefix,
                "target": contract.target_prefix,
                "severity": "medium",
                "title": f"{contract.target_prefix} may not cover: {matched_triggers[0]}",
                "description": (
                    f"{current_prefix} decisions mention '{matched_triggers[0]}' "
                    f"but {contract.target_prefix} decisions don't reference "
                    f"this concept. Consider updating {contract.target_prefix} decisions."
                ),
                "evidence": [
                    f"Trigger '{matched_triggers[0]}' in {current_prefix} decisions",
                    f"Not found in {contract.target_prefix} decisions",
                ],
                "recommendation": f"Review {contract.target_prefix} decisions for coverage",
            })

    return warnings


def _prefix_to_specialist(prefix: str) -> str:
    """Map a decision prefix to its specialist command name."""
    mapping = {
        "GEN": "plan", "DOM": "domain", "COMP": "competition",
        "BRAND": "branding", "ARCH": "architecture", "BACK": "backend",
        "FRONT": "frontend", "STYLE": "design", "UIX": "uix",
        "SEC": "security", "OPS": "devops", "LEGAL": "legal",
        "PRICE": "pricing", "LLM": "llm", "INGEST": "scraping",
        "DATA": "data-ml", "TEST": "testing",
    }
    return mapping.get(prefix, prefix.lower())


def run_specialist_exit_check(
    conn: sqlite3.Connection,
    prefix: str,
) -> dict[str, Any]:
    """Run all pre-audit checks for a specialist session.

    Called at the end of each specialist session to catch cross-domain
    gaps early, before /synthesize.

    Returns:
        {
            "status": "clean" | "warnings",
            "prefix": str,
            "implication_warnings": [...],
            "cross_domain_warnings": [...],
            "total_warnings": int,
            "by_severity": {"critical": N, "high": N, ...},
        }
    """
    decisions = db.get_decisions(conn)

    # 1. Implication rules on ALL decisions (catches global gaps)
    impl_warnings = check_decision_implications(decisions)

    # 2. Cross-domain checks for current specialist
    cross_warnings = check_decision_cross_refs(decisions, prefix)

    # Severity summary
    all_warnings = impl_warnings + cross_warnings
    by_severity: dict[str, int] = {}
    for w in all_warnings:
        sev = w.get("severity", "medium")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "status": "clean" if not all_warnings else "warnings",
        "prefix": prefix,
        "implication_warnings": impl_warnings,
        "cross_domain_warnings": cross_warnings,
        "total_warnings": len(all_warnings),
        "by_severity": by_severity,
    }


# ---------------------------------------------------------------------------
# Layer 3: Build Audit Prompt (for LLM user journey tracing)
# ---------------------------------------------------------------------------

def _format_task_queue_by_milestone(
    tasks: list[Task],
    milestones: list[dict[str, Any]],
) -> str:
    """Group tasks under milestone headers with goal + criteria."""
    if not tasks:
        return "(no tasks)"

    # Build milestone lookup
    ms_lookup: dict[str, str] = {}
    for m in milestones:
        ms_lookup[m["id"]] = m.get("name", m["id"])

    # Group tasks by milestone
    by_milestone: dict[str, list[Task]] = {}
    for t in tasks:
        by_milestone.setdefault(t.milestone, []).append(t)

    sections: list[str] = []
    for ms_id in sorted(by_milestone.keys()):
        ms_name = ms_lookup.get(ms_id, ms_id)
        lines = [f"### {ms_id}: {ms_name}"]
        for t in by_milestone[ms_id]:
            lines.append(f"\n**{t.id}: {t.title}**")
            if t.goal:
                lines.append(f"Goal: {t.goal}")
            if t.decision_refs:
                lines.append(f"Decisions: {', '.join(t.decision_refs)}")
            if t.depends_on:
                lines.append(f"Depends on: {', '.join(t.depends_on)}")
            if t.acceptance_criteria:
                lines.append("Acceptance criteria:")
                for i, ac in enumerate(t.acceptance_criteria, 1):
                    lines.append(f"  {i}. {ac}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _format_decision_index_compact(decisions: list[Decision]) -> str:
    """Compact one-line-per-decision index."""
    if not decisions:
        return "(no decisions)"

    lines: list[str] = []
    current_prefix = ""
    for d in sorted(decisions, key=lambda x: (x.prefix.value, x.number)):
        if d.prefix.value != current_prefix:
            current_prefix = d.prefix.value
            lines.append(f"\n**{current_prefix}:**")
        lines.append(f"  - {d.id}: {d.title}")
    return "\n".join(lines)


def _format_deterministic_gaps(gaps: list[AuditGap]) -> str:
    """Format deterministic gaps for inclusion in the LLM prompt."""
    if not gaps:
        return "(none found — rules passed clean)"

    lines: list[str] = []
    for g in gaps:
        lines.append(f"- **{g.id}** [{g.severity.value}] {g.title}")
        lines.append(f"  Layer: {g.layer} | Category: {g.category.value}")
        lines.append(f"  {g.description}")
    return "\n".join(lines)


def build_audit_prompt(
    conn: sqlite3.Connection,
    precomputed_gaps: list[AuditGap] | None = None,
) -> str:
    """Compose the full completeness audit prompt for Opus.

    Includes project summary, full task queue, decision index,
    deterministic gaps, and instructions for multi-lens analysis.

    Args:
        conn: Database connection.
        precomputed_gaps: If provided, use these instead of re-running
            deterministic checks. Avoids double computation when called
            from run_deterministic_audit().
    """
    pipeline = db.get_pipeline(conn)
    decisions = db.get_decisions(conn)
    tasks = db.get_tasks(conn)
    milestones = db.get_milestones(conn)

    # Use precomputed gaps or run deterministic checks
    if precomputed_gaps is not None:
        det_gaps = precomputed_gaps
    else:
        det_gaps = _run_and_renumber_deterministic(decisions, tasks)

    # Format milestone data for template
    ms_dicts = [{"id": m.id, "name": m.name, "goal": m.goal} for m in milestones]

    # Load and render prompt template
    template = load_prompt("completeness")

    context = {
        "project_name": pipeline.project_name,
        "project_summary": pipeline.project_summary or "(no summary available)",
        "task_queue_by_milestone": _format_task_queue_by_milestone(tasks, ms_dicts),
        "decision_index_compact": _format_decision_index_compact(decisions),
        "deterministic_gaps": _format_deterministic_gaps(det_gaps),
        "AUDIT_SCHEMA": get_audit_schema(),
    }

    return render(template, context)


def _run_and_renumber_deterministic(
    decisions: list[Decision],
    tasks: list[Task],
) -> list[AuditGap]:
    """Run Layer 1+2 and renumber contract gaps to avoid ID collisions."""
    gaps = check_feature_implications(decisions, tasks)
    contract_gaps = check_cross_task_contracts(tasks, decisions)

    # Renumber contract gaps to continue from implication gaps
    offset = len(gaps)
    for i, g in enumerate(contract_gaps):
        contract_gaps[i] = g.model_copy(update={"id": f"GAP-{offset + i + 1:02d}"})
    gaps.extend(contract_gaps)
    return gaps


# ---------------------------------------------------------------------------
# Parse + Validate LLM audit output
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _strip_markdown_fences(text: str) -> str:
    """Strip ```json ... ``` fences that LLMs commonly wrap output in."""
    m = _FENCE_RE.match(text.strip())
    return m.group(1).strip() if m else text.strip()


def parse_audit_output(
    raw_json: str,
    existing_gap_count: int = 0,
) -> tuple[list[AuditGap], list[str]]:
    """Parse LLM-generated audit JSON into AuditGap objects.

    Returns (gaps, errors). If errors is non-empty, some gaps may still be valid.
    Gap IDs are auto-numbered starting from existing_gap_count + 1.
    Handles markdown code fences (```json ... ```) that LLMs commonly add.
    """
    errors: list[str] = []

    # Strip markdown fences before parsing
    cleaned = _strip_markdown_fences(raw_json)

    # Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return [], [f"Invalid JSON: {e}"]

    if not isinstance(data, dict):
        return [], ["Output must be a JSON object"]

    raw_gaps = data.get("gaps", [])
    if not isinstance(raw_gaps, list):
        return [], ["'gaps' must be a list"]

    gaps: list[AuditGap] = []
    gap_num = existing_gap_count

    valid_categories = {c.value for c in AuditGapCategory}
    valid_severities = {s.value for s in AuditGapSeverity}

    for i, raw in enumerate(raw_gaps):
        if not isinstance(raw, dict):
            errors.append(f"Gap {i}: not an object")
            continue

        # Validate category
        cat = raw.get("category", "")
        if cat not in valid_categories:
            errors.append(f"Gap {i}: invalid category '{cat}'")
            continue

        # Validate severity
        sev = raw.get("severity", "")
        if sev not in valid_severities:
            errors.append(f"Gap {i}: invalid severity '{sev}'")
            continue

        # Validate required string fields
        title = raw.get("title", "")
        desc = raw.get("description", "")
        if not title or not desc:
            errors.append(f"Gap {i}: missing title or description")
            continue

        # Validate and coerce evidence items to strings
        raw_evidence = raw.get("evidence", [])
        if isinstance(raw_evidence, list):
            evidence = [str(item)[:2000] for item in raw_evidence]
        else:
            evidence = []

        gap_num += 1
        try:
            gap = AuditGap(
                id=f"GAP-{gap_num:02d}",
                category=AuditGapCategory(cat),
                severity=AuditGapSeverity(sev),
                layer="journey",
                title=title[:2000],
                description=desc[:2000],
                trigger=str(raw.get("trigger", ""))[:2000],
                evidence=evidence,
                recommendation=str(raw.get("recommendation", ""))[:2000],
            )
            gaps.append(gap)
        except (ValueError, TypeError) as e:
            errors.append(f"Gap {i}: validation error: {e}")
            gap_num -= 1  # Don't waste the ID

    return gaps, errors


# ---------------------------------------------------------------------------
# Orchestration functions
# ---------------------------------------------------------------------------

def run_deterministic_audit(
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Run Layer 1 + Layer 2 checks, return gaps + LLM prompt.

    Returns:
        {
            "deterministic_gaps": list[AuditGap],
            "gap_count": int,
            "llm_prompt": str,
            "by_severity": dict[str, int],
            "by_layer": dict[str, int],
        }
    """
    decisions = db.get_decisions(conn)
    tasks = db.get_tasks(conn)

    # Run Layer 1+2 with proper renumbering
    gaps = _run_and_renumber_deterministic(decisions, tasks)

    # Build LLM prompt — pass precomputed gaps to avoid re-running checks
    llm_prompt = build_audit_prompt(conn, precomputed_gaps=gaps)

    # Severity/layer summary
    by_severity: dict[str, int] = {}
    by_layer: dict[str, int] = {}
    for g in gaps:
        by_severity[g.severity.value] = by_severity.get(g.severity.value, 0) + 1
        by_layer[g.layer] = by_layer.get(g.layer, 0) + 1

    return {
        "deterministic_gaps": gaps,
        "gap_count": len(gaps),
        "llm_prompt": llm_prompt,
        "by_severity": by_severity,
        "by_layer": by_layer,
    }


def run_full_audit(
    conn: sqlite3.Connection,
    llm_json: str,
) -> dict[str, Any]:
    """Process LLM audit output, merge with deterministic gaps already stored.

    Returns:
        {
            "all_gaps": list[AuditGap],
            "llm_gaps": list[AuditGap],
            "llm_errors": list[str],
            "by_severity": dict[str, int],
            "total": int,
        }
    """
    # Get already-stored deterministic gaps
    existing_gaps = db.get_audit_gaps(conn)
    existing_count = len(existing_gaps)

    # Parse LLM output
    llm_gaps, llm_errors = parse_audit_output(llm_json, existing_count)

    # Store LLM gaps
    for gap in llm_gaps:
        db.store_audit_gap(conn, gap)

    # Combine
    all_gaps = existing_gaps + llm_gaps

    # Severity summary
    by_severity: dict[str, int] = {}
    for g in all_gaps:
        by_severity[g.severity.value] = by_severity.get(g.severity.value, 0) + 1

    return {
        "all_gaps": all_gaps,
        "llm_gaps": llm_gaps,
        "llm_errors": llm_errors,
        "by_severity": by_severity,
        "total": len(all_gaps),
    }

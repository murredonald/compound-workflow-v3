"""Tests for the specialist prompt migration: base template, per-specialist
body files, artifact storage, context filtering, and end-to-end rendering.

Covers:
  - Base template rendering with context injection
  - All 16 specialist body files exist and have required sections
  - Artifact storage (DB CRUD)
  - Artifact injection into specialist context
  - End-to-end rendering through composer → renderer pipeline
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core import db
from core.models import Constraint, Decision
from engine.composer import (
    ARTIFACT_RELEVANCE,
    RELEVANCE,
    compose_phase_context,
    load_prompt,
)
from engine.renderer import format_artifacts, format_decisions, render

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

ALL_SPECIALISTS = [
    "architecture",
    "backend",
    "branding",
    "competition",
    "data-ml",
    "design",
    "devops",
    "domain",
    "frontend",
    "legal",
    "llm",
    "pricing",
    "scraping",
    "security",
    "testing",
    "uix",
]

# Expected focus area counts per specialist (minimum — some have conditional FAs)
EXPECTED_FA_COUNTS: dict[str, int] = {
    "architecture": 6,
    "backend": 9,
    "branding": 5,
    "competition": 6,
    "data-ml": 7,
    "design": 7,
    "devops": 7,
    "domain": 7,
    "frontend": 10,
    "legal": 6,
    "llm": 9,
    "pricing": 7,
    "scraping": 8,
    "security": 6,
    "testing": 9,
    "uix": 8,
}

# Prefix each specialist should reference in its body
SPECIALIST_PREFIX: dict[str, str] = {
    "architecture": "ARCH",
    "backend": "BACK",
    "branding": "BRAND",
    "competition": "COMP",
    "data-ml": "DATA",
    "design": "STYLE",
    "devops": "OPS",
    "domain": "DOM",
    "frontend": "FRONT",
    "legal": "LEGAL",
    "llm": "LLM",
    "pricing": "PRICE",
    "scraping": "INGEST",
    "security": "SEC",
    "testing": "TEST",
    "uix": "UIX",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_db(tmp_path):
    """DB with pipeline, a GEN decision, and a constraint."""
    db_path = tmp_path / "test.db"
    db.init_db("InvoiceApp", db_path=db_path)
    conn = db.get_db(db_path)
    # Add a GEN decision
    db.store_decisions(conn, [
        Decision(id="GEN-01", prefix="GEN", number=1,
                 title="SaaS invoice management tool",
                 rationale="Target market: freelancers and small agencies"),
    ])
    # Add a constraint
    db.store_constraints(conn, [
        Constraint(id="C-01", category="budget",
                   description="Solo developer, no paid infrastructure at launch"),
    ])
    yield conn
    conn.close()


# ============================================================
# TestBaseTemplate — base specialist.md rendering
# ============================================================

class TestBaseTemplate:
    """Test the base specialist.md template renders correctly."""

    def test_base_renders_with_context(self):
        """Base template renders all required variables."""
        template = load_prompt("specialist")
        assert template, "specialist.md should exist and be non-empty"

        context = {
            "PREFIX": "BACK",
            "specialist_name": "backend",
            "project_name": "TestApp",
            "project_summary": "A test application",
            "decisions": [
                {"id": "GEN-01", "prefix": "GEN", "number": 1,
                 "title": "Use Python", "rationale": "Team expertise"},
            ],
            "constraints": [
                {"category": "budget", "description": "No paid infra"},
            ],
            "completed_phases": ["plan", "specialist/domain"],
            "pending_phases": ["specialist/backend"],
            "specialist_prompt": "You are a backend specialist.",
            "artifacts": {},
            "DECISION_SCHEMA": True,
        }

        result = render(template, context)
        assert "BACK" in result
        assert "backend" in result
        assert "TestApp" in result
        assert "A test application" in result
        assert "GEN-01" in result
        assert "You are a backend specialist." in result
        assert "GATE: Orientation" in result

    def test_base_includes_specialist_body(self):
        """{{specialist_prompt}} is replaced with body content."""
        template = load_prompt("specialist")
        body = "## Role\n\nYou are the **best** specialist."
        context = {
            "PREFIX": "TEST",
            "specialist_name": "testing",
            "project_name": "App",
            "decisions": [],
            "constraints": [],
            "completed_phases": [],
            "pending_phases": [],
            "specialist_prompt": body,
            "artifacts": {},
            "DECISION_SCHEMA": True,
        }
        result = render(template, context)
        assert "You are the **best** specialist." in result
        # Template variable should be replaced
        assert "{{specialist_prompt}}" not in result

    def test_base_renders_decisions(self):
        """Decisions are formatted with ID and rationale."""
        template = load_prompt("specialist")
        context = {
            "PREFIX": "ARCH",
            "specialist_name": "architecture",
            "project_name": "App",
            "decisions": [
                {"id": "GEN-01", "prefix": "GEN", "number": 1,
                 "title": "FastAPI", "rationale": "Async support"},
                {"id": "GEN-02", "prefix": "GEN", "number": 2,
                 "title": "PostgreSQL", "rationale": "Relational data"},
            ],
            "constraints": [],
            "completed_phases": [],
            "pending_phases": [],
            "specialist_prompt": "Body here.",
            "artifacts": {},
            "DECISION_SCHEMA": True,
        }
        result = render(template, context)
        assert "GEN-01" in result
        assert "FastAPI" in result
        assert "GEN-02" in result
        assert "PostgreSQL" in result

    def test_base_renders_empty_specialist(self):
        """Missing specialist file → empty body, no crash."""
        template = load_prompt("specialist")
        context = {
            "PREFIX": "FAKE",
            "specialist_name": "nonexistent",
            "project_name": "App",
            "decisions": [],
            "constraints": [],
            "completed_phases": [],
            "pending_phases": [],
            "specialist_prompt": "",  # Empty — file didn't exist
            "artifacts": {},
            "DECISION_SCHEMA": True,
        }
        result = render(template, context)
        # Should render without error
        assert "FAKE" in result
        assert "GATE: Orientation" in result

    def test_base_conditional_sections(self):
        """{{#project_summary}} block included only when truthy."""
        template = load_prompt("specialist")

        # With summary
        ctx_with = {
            "PREFIX": "DOM",
            "specialist_name": "domain",
            "project_name": "App",
            "project_summary": "An invoice app for freelancers",
            "decisions": [],
            "constraints": [],
            "completed_phases": [],
            "pending_phases": [],
            "specialist_prompt": "Body.",
            "artifacts": {},
            "DECISION_SCHEMA": True,
        }
        result_with = render(template, ctx_with)
        assert "An invoice app for freelancers" in result_with

        # Without summary
        ctx_without = {**ctx_with, "project_summary": ""}
        result_without = render(template, ctx_without)
        assert "An invoice app for freelancers" not in result_without

    def test_base_artifacts_conditional(self):
        """{{#artifacts}} block only rendered when artifacts are present."""
        template = load_prompt("specialist")
        base_ctx = {
            "PREFIX": "STYLE",
            "specialist_name": "design",
            "project_name": "App",
            "decisions": [],
            "constraints": [],
            "completed_phases": [],
            "pending_phases": [],
            "specialist_prompt": "Body.",
            "DECISION_SCHEMA": True,
        }

        # No artifacts — block should not appear
        ctx_no_art = {**base_ctx, "artifacts": {}}
        result_no = render(template, ctx_no_art)
        assert "Reference Artifacts" not in result_no

        # With artifacts — block should appear
        ctx_with_art = {**base_ctx, "artifacts": {"brand-guide": "# Brand\nBlue is primary."}}
        result_with = render(template, ctx_with_art)
        assert "Reference Artifacts" in result_with
        assert "Blue is primary." in result_with


# ============================================================
# TestSpecialistFiles — validate all 16 body files
# ============================================================

class TestSpecialistFiles:
    """Validate structure and content of all 16 specialist body files."""

    def test_all_16_files_exist(self):
        """Every specialist has a corresponding prompt file."""
        for name in ALL_SPECIALISTS:
            path = PROMPTS_DIR / f"specialist_{name}.md"
            assert path.exists(), f"Missing: specialist_{name}.md"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_files_have_role_section(self, name: str):
        """Each specialist file includes a Role section."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        assert "## Role" in content, f"specialist_{name}.md missing ## Role"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_files_have_decision_prefix(self, name: str):
        """Each specialist file includes a Decision Prefix section."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        expected_prefix = SPECIALIST_PREFIX[name]
        assert "Decision Prefix" in content, \
            f"specialist_{name}.md missing Decision Prefix"
        assert f"{expected_prefix}-" in content, \
            f"specialist_{name}.md should reference {expected_prefix}-"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_files_have_focus_areas(self, name: str):
        """Each file has the expected number of ### Focus Area headers."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        # Count ### headers that look like focus areas (### N. Title or ### FA N: Title)
        fa_headers = re.findall(r"^### \d+\.", content, re.MULTILINE)
        expected = EXPECTED_FA_COUNTS[name]
        assert len(fa_headers) >= expected, (
            f"specialist_{name}.md: expected >= {expected} focus areas, "
            f"found {len(fa_headers)}"
        )

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_no_template_variables_in_body(self, name: str):
        """Body files must NOT use {{VARIABLE}} syntax — that's for the base template."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        matches = re.findall(r"\{\{[A-Z_]+\}\}", content)
        assert not matches, (
            f"specialist_{name}.md contains template variables: {matches}. "
            f"Body files should be pure static markdown."
        )

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_no_old_workflow_file_reads(self, name: str):
        """Body files should not reference old .workflow/ file reads."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        # Old pattern: "Read .workflow/decisions/GEN.md"
        old_reads = re.findall(
            r"[Rr]ead.*\.workflow/decisions/\w+\.md", content
        )
        assert not old_reads, (
            f"specialist_{name}.md still references old file reads: {old_reads}"
        )

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_files_have_scope_boundaries(self, name: str):
        """Every specialist body should have a Scope & Boundaries section."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        assert "## Scope & Boundaries" in content, \
            f"specialist_{name}.md missing ## Scope & Boundaries"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_has_anti_patterns(self, name: str):
        """Each specialist has domain-specific anti-patterns."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        assert "Anti-Pattern" in content, \
            f"specialist_{name}.md missing Anti-Patterns section"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_has_anti_pattern_reference_file(self, name: str):
        """Each specialist has a corresponding antipatterns/ reference file."""
        ap_path = PROMPTS_DIR / "antipatterns" / f"{name}.md"
        assert ap_path.exists(), f"Missing: antipatterns/{name}.md"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_anti_pattern_file_has_structured_entries(self, name: str):
        """Anti-pattern files use PREFIX-AP-NN format with required fields."""
        content = (PROMPTS_DIR / "antipatterns" / f"{name}.md").read_text(encoding="utf-8")
        prefix = SPECIALIST_PREFIX[name]
        # Must contain at least one PREFIX-AP-NN entry
        ap_entries = re.findall(rf"^### {prefix}-AP-\d+:", content, re.MULTILINE)
        assert len(ap_entries) >= 10, (
            f"antipatterns/{name}.md: expected >= 10 anti-patterns, "
            f"found {len(ap_entries)}"
        )
        # Must contain required fields
        assert "**Mistake:**" in content, \
            f"antipatterns/{name}.md missing **Mistake:** field"
        assert "**Why:**" in content, \
            f"antipatterns/{name}.md missing **Why:** field"
        assert "**Instead:**" in content, \
            f"antipatterns/{name}.md missing **Instead:** field"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_specialist_references_antipattern_file(self, name: str):
        """Each specialist body references its antipatterns file."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        assert f"antipatterns/{name}.md" in content, \
            f"specialist_{name}.md should reference antipatterns/{name}.md"

    @pytest.mark.parametrize("name", ALL_SPECIALISTS)
    def test_has_decision_format_examples(self, name: str):
        """Each specialist has decision format examples."""
        content = (PROMPTS_DIR / f"specialist_{name}.md").read_text(encoding="utf-8")
        assert "Decision Format Example" in content, \
            f"specialist_{name}.md missing Decision Format Examples"

    def test_prefix_in_relevance_matrix(self):
        """Every specialist in the prompt set has an entry in the RELEVANCE matrix."""
        for name in ALL_SPECIALISTS:
            phase_id = f"specialist/{name}"
            assert phase_id in RELEVANCE, (
                f"specialist/{name} not in composer.RELEVANCE matrix"
            )


# ============================================================
# TestArtifactStorage — DB CRUD for artifacts
# ============================================================

class TestArtifactStorage:
    """Test artifact storage in the DB."""

    def test_store_and_retrieve(self, fresh_db):
        """Store an artifact and retrieve it."""
        db.store_artifact(fresh_db, "brand-guide", "# Brand Guide\nBlue.")
        result = db.get_artifact(fresh_db, "brand-guide")
        assert result == "# Brand Guide\nBlue."

    def test_overwrite_artifact(self, fresh_db):
        """Second write replaces first."""
        db.store_artifact(fresh_db, "brand-guide", "Version 1")
        db.store_artifact(fresh_db, "brand-guide", "Version 2")
        result = db.get_artifact(fresh_db, "brand-guide")
        assert result == "Version 2"

    def test_get_missing_artifact(self, fresh_db):
        """Returns None for non-existent artifact."""
        result = db.get_artifact(fresh_db, "nonexistent")
        assert result is None

    def test_list_artifacts(self, fresh_db):
        """List all stored artifacts."""
        db.store_artifact(fresh_db, "brand-guide", "Brand content")
        db.store_artifact(fresh_db, "style-guide", "Style content")
        artifacts = db.list_artifacts(fresh_db)
        types = [a["type"] for a in artifacts]
        assert "brand-guide" in types
        assert "style-guide" in types
        assert len(artifacts) == 2

    def test_artifact_in_phase_context(self, seeded_db):
        """Relevant artifacts are injected into specialist context."""
        # Store a brand guide
        db.store_artifact(seeded_db, "brand-guide", "# Brand\nPrimary: Blue")

        # Design specialist should see brand-guide
        ctx = compose_phase_context(seeded_db, "specialist/design")
        assert "brand-guide" in ctx["artifacts"]
        assert "Primary: Blue" in ctx["artifacts"]["brand-guide"]

    def test_artifact_not_injected_for_irrelevant_specialist(self, seeded_db):
        """Specialists not in ARTIFACT_RELEVANCE don't get artifacts."""
        db.store_artifact(seeded_db, "brand-guide", "# Brand\nPrimary: Blue")

        # Backend specialist should NOT see brand-guide
        ctx = compose_phase_context(seeded_db, "specialist/backend")
        assert not ctx["artifacts"]

    def test_artifact_relevance_completeness(self):
        """All artifact types in ARTIFACT_RELEVANCE are valid ArtifactType values."""
        from core.models import ArtifactType
        valid_types = {t.value for t in ArtifactType}
        for phase_id, art_types in ARTIFACT_RELEVANCE.items():
            for art_type in art_types:
                assert art_type in valid_types, (
                    f"{phase_id} references unknown artifact type: {art_type}"
                )


# ============================================================
# TestEndToEnd — full rendering pipeline
# ============================================================

class TestEndToEnd:
    """Test the full compose → render pipeline for specialists."""

    def test_render_backend_specialist(self, seeded_db):
        """Full render of backend specialist with seeded DB."""
        ctx = compose_phase_context(seeded_db, "specialist/backend")
        template = ctx["prompt"]
        result = render(template, ctx)

        # Base template content
        assert "InvoiceApp" in result
        assert "GEN-01" in result
        assert "GATE: Orientation" in result

        # Backend-specific body content
        assert "API Contract Design" in result
        assert "BACK-" in result
        assert "Database Schema" in result

    def test_render_domain_specialist(self, seeded_db):
        """Full render of domain specialist."""
        ctx = compose_phase_context(seeded_db, "specialist/domain")
        template = ctx["prompt"]
        result = render(template, ctx)

        assert "InvoiceApp" in result
        assert "DOM-" in result

    def test_render_design_with_artifact(self, seeded_db):
        """Design specialist renders with brand-guide artifact injected."""
        db.store_artifact(seeded_db, "brand-guide", "# Brand\nPrimary color: #0066CC")

        ctx = compose_phase_context(seeded_db, "specialist/design")
        template = ctx["prompt"]
        result = render(template, ctx)

        # Should contain brand guide content
        assert "#0066CC" in result
        assert "Reference Artifacts" in result
        # Should contain design-specific body
        assert "STYLE-" in result

    def test_context_filtering(self, seeded_db):
        """Backend sees GEN+ARCH decisions, not FRONT decisions."""
        # Add an ARCH and FRONT decision
        db.store_decisions(seeded_db, [
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI framework", rationale="Async"),
            Decision(id="FRONT-01", prefix="FRONT", number=1,
                     title="React SPA", rationale="Component model"),
        ])

        # Backend sees ARCH (in its RELEVANCE list) but not FRONT
        ctx = compose_phase_context(seeded_db, "specialist/backend")
        decision_ids = {d["id"] for d in ctx["decisions"]}
        assert "GEN-01" in decision_ids
        assert "ARCH-01" in decision_ids
        assert "FRONT-01" not in decision_ids

    def test_context_filtering_frontend_sees_back(self, seeded_db):
        """Frontend sees BACK decisions but not SEC."""
        db.store_decisions(seeded_db, [
            Decision(id="ARCH-01", prefix="ARCH", number=1,
                     title="FastAPI", rationale="Async"),
            Decision(id="BACK-01", prefix="BACK", number=1,
                     title="REST API", rationale="Standard"),
            Decision(id="SEC-01", prefix="SEC", number=1,
                     title="JWT auth", rationale="Stateless"),
        ])

        ctx = compose_phase_context(seeded_db, "specialist/frontend")
        decision_ids = {d["id"] for d in ctx["decisions"]}
        assert "GEN-01" in decision_ids
        assert "ARCH-01" in decision_ids
        assert "BACK-01" in decision_ids
        # SEC is NOT in frontend's RELEVANCE list
        assert "SEC-01" not in decision_ids

    def test_no_unrendered_placeholders(self, seeded_db):
        """Rendered output should not contain raw {{VARIABLE}} placeholders."""
        ctx = compose_phase_context(seeded_db, "specialist/backend")
        template = ctx["prompt"]
        result = render(template, ctx)

        # Find any remaining {{WORD}} patterns (excluding code blocks)
        # Strip fenced code blocks first to avoid false positives
        stripped = re.sub(r"```.*?```", "", result, flags=re.DOTALL)
        remaining = re.findall(r"\{\{[A-Z_]+\}\}", stripped)
        assert not remaining, (
            f"Unrendered placeholders in output: {remaining}"
        )


# ============================================================
# TestFormatters — renderer helper functions
# ============================================================

class TestFormatters:
    """Test individual renderer formatters."""

    def test_format_decisions_empty(self):
        assert format_decisions([]) == "(none)"

    def test_format_decisions_with_data(self):
        result = format_decisions([
            {"id": "GEN-01", "title": "Use Python", "rationale": "Team knows it"},
        ])
        assert "**GEN-01**" in result
        assert "Use Python" in result
        assert "Team knows it" in result

    def test_format_artifacts_empty(self):
        assert format_artifacts({}) == "(none)"

    def test_format_artifacts_with_data(self):
        result = format_artifacts({
            "brand-guide": "# Brand\nBlue primary.",
            "style-guide": "# Styles\n16px base.",
        })
        assert "### Brand Guide" in result
        assert "Blue primary." in result
        assert "### Style Guide" in result
        assert "16px base." in result

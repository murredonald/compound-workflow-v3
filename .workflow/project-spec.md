# Workflow Engine — Project Specification

**Version:** 1.0 (Strategic Planning)
**Date:** 2026-02-09
**Phase:** complete
**Depth:** Light

---

## 1. Overview

- **App type:** Workflow orchestration platform (API + UI + LLM integration)
- **One-liner:** A typed, database-backed workflow engine that replaces brittle prompt-chained markdown with Pydantic-validated JSON artifacts, configurable pipeline templates, and a React control plane.
- **Problem statement:** The current compound workflow system (v3) chains LLM interactions through prompt-engineered markdown files. State is unvalidated, progress is invisible without reading raw files, the workflow is hardcoded in prompt templates, and second-opinion LLM integration is bolted on via shell scripts. One malformed artifact cascades silently. The new system makes every state transition typed, validated, visible, and recoverable.

| ID | Success Criterion | Measurement |
|----|-------------------|-------------|
| SC-01 | All artifacts are validated JSON with Pydantic schemas | Zero untyped state files in pipeline |
| SC-02 | Visual UI shows full pipeline flow and live progress | React dashboard with React Flow DAG |
| SC-03 | Workflow templates are configurable | Can create/clone/edit templates as JSON configs |
| SC-04 | Second-opinion LLMs are pluggable via UI | Settings page with provider management |
| SC-05 | Claude retains full file access for building projects | Tool definitions cover read/write/edit/bash/git |
| SC-06 | Pipeline state is validated at every transition boundary | Invalid output fails loudly with typed error |

## 2. Users & Personas

### Persona: Solo Developer (You)

- **Role:** Developer using AI-assisted structured workflows to build software
- **Context:** Running compound dev workflows from local machine, personal projects
- **Goals:** Reliable pipeline execution, visibility into progress, customizable flows, easy LLM provider management
- **Frustrations:** Silent state corruption, no progress visibility, can't tweak flow without editing markdown prompts, brittle cross-phase handoffs
- **Tech proficiency:** High

### Jobs-to-be-done

| ID | Job | Frequency | Priority |
|----|-----|-----------|----------|
| J1 | Run a full dev workflow with confidence state won't corrupt | Every project | Must-have |
| J2 | See at a glance where a project is in the pipeline | Multiple times/day | Must-have |
| J3 | Configure which phases run, in what order, with which LLM | Per project | Must-have |
| J4 | Connect/disconnect second-opinion LLMs from UI | Occasional | Should-have |
| J5 | Review artifacts (decisions, tasks, evals) in structured UI | After each phase | Must-have |
| J6 | Replay/retry a failed phase without restarting the pipeline | On failure | Must-have |
| J7 | Compare artifacts across runs | Occasional | Nice-to-have |
| J8 | Pause a running pipeline and resume later | Occasional | Must-have |

## 3. Core Workflows

### Primary Workflow: Run a project through a pipeline

1. Open UI → Create new project (name, pick template)
2. Pipeline view shows phases as nodes in a flow diagram (React Flow)
3. Click "Start" → first phase activates
4. Orchestrator sends task to Claude via Anthropic API with phase-specific prompt + tools
5. Claude works (tool calls stream in real-time to UI via WebSocket)
6. Phase completes → orchestrator validates output against Pydantic schema
7. Artifact saved to DB → UI updates, next phase unlocks
8. Repeat until pipeline complete
   - Auto-mode ON: phases advance automatically
   - Auto-mode OFF: user clicks "Continue" to advance

### Secondary Workflows

**Configure LLM providers:**
Settings page → Add provider (Anthropic/OpenAI/Gemini) → Enter API key → Test connection → Save. Per-template: assign which provider handles which phase/role.

**Create/edit workflow template:**
Templates page → Clone existing or create blank → Edit phases (add/remove/reorder) → Configure per-phase: model, tools allowed, output schema, auto/manual → Save.

**Review artifacts:**
Project view → Click any completed phase → See structured artifacts. Filter/search across artifacts. Drill into details.

**Error/retry:**
Phase fails validation → UI shows error with details → Options: Retry (same config), Retry with different model, Roll back to checkpoint, Skip phase.

### Edge Cases

| Case | Behavior | Priority |
|------|----------|----------|
| Claude stuck in tool loop | Timeout per phase (configurable), kill and surface partial results | Must-handle |
| API rate limit / outage | Exponential backoff, pause pipeline, notify in UI | Must-handle |
| Schema validation fails | Show raw output alongside expected schema, user decides: retry/force-accept/edit | Must-handle |
| Mid-phase context window fills | Orchestrator manages context (summarize earlier tool results) | Must-handle |
| Concurrent phase conflict | Template marks which phases are parallelizable | Should-handle |

## 4. Data Model

### Core Entities

**Project** — Top-level container for a development effort.
- id, name, created_at, updated_at
- template_id (FK → WorkflowTemplate)
- status: idle | running | paused | completed | failed
- current_phase_id
- config overrides (auto-mode, timeouts)

**WorkflowTemplate** — Defines a reusable pipeline structure.
- id, name, description, is_default
- phases: list of PhaseDefinition (ordered, with dependencies)
- created_at, cloned_from

**PhaseDefinition** — A single step in a workflow template.
- id, name, type: interactive | automated | loop
- order, depends_on: list of phase ids
- parallelizable: bool
- model: opus | sonnet | haiku
- system_prompt_template: str
- tools_allowed: list of tool names
- output_schema: str (Pydantic model name reference)
- timeout_seconds
- auto_proceed: bool

**PipelineRun** — A single execution of a project's pipeline.
- id, project_id, template_snapshot (frozen copy at start)
- status, started_at, completed_at
- current_phase

**PhaseExecution** — A single phase's execution within a run.
- id, pipeline_run_id, phase_definition_id
- status: pending | running | completed | failed | skipped | rolled_back
- started_at, completed_at
- model_used, tokens_in, tokens_out
- checkpoint_id (FK → Checkpoint)

**Artifact** — A validated output from a phase.
- id, phase_execution_id, artifact_type (decision, task, spec, eval, etc.)
- schema_version
- data: JSON (validated content)
- created_at

**LLMProvider** — A configured AI provider.
- id, name: anthropic | openai | gemini
- api_key (encrypted at rest)
- role: primary | reviewer | second_opinion
- enabled: bool
- config: JSON (model name, temperature, etc.)

**ToolCall** — Audit log of every tool invocation.
- id, phase_execution_id
- tool_name, input, output
- timestamp, duration_ms

**Checkpoint** — Rollback point for error recovery.
- id, pipeline_run_id, phase_execution_id
- snapshot: JSON (full pipeline state)
- created_at

### Data Sensitivity

| Data | Sensitivity | Handling |
|------|-------------|----------|
| API keys | High | Fernet encryption at rest, local key file |
| Project files (via Claude tools) | Medium | Stay on local filesystem, not in DB |
| Artifacts | Low | Structured JSON in SQLite |
| Tool call logs | Low | Audit trail in SQLite |

## 5. Technical Foundation

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend framework | FastAPI | Async, Pydantic-native, WebSocket built-in |
| ORM/Models | SQLModel | Pydantic + SQLAlchemy in one model class |
| Database | SQLite | Zero-config, single file, solo dev |
| Migrations | Alembic | Schema versioning |
| LLM SDK (primary) | anthropic Python SDK | Direct API with tool use + streaming |
| LLM SDK (secondary) | openai, google-genai | Pluggable providers |
| Frontend framework | React 18 + Vite | Fast dev, user preference |
| State management | Zustand | Lightweight, no boilerplate |
| UI components | shadcn/ui + Tailwind | Clean, composable, no lock-in |
| Flow visualization | React Flow | Pipeline DAG rendering |
| Real-time | FastAPI WebSocket | Stream tool calls + progress to UI |
| API client | TanStack Query | Caching, refetch, WS integration |

### Auth
None. Solo dev, localhost only.

### Deployment
Local development server. `uvicorn` for backend, `vite dev` for frontend.

## 7. MVP Scope

### In-Scope (v1)

| # | Feature | Priority |
|---|---------|----------|
| F1 | Pydantic models for all artifact types (decisions, tasks, specs, evals, tool calls) | Must |
| F2 | Workflow engine — template-driven state machine, phase transitions, validation gates | Must |
| F3 | Anthropic API integration with tool use (file ops, bash, git) | Must |
| F4 | SQLite persistence via SQLModel — all entities from data model | Must |
| F5 | FastAPI REST API — CRUD for projects, templates, providers; pipeline control | Must |
| F6 | WebSocket streaming — tool calls + phase progress in real-time | Must |
| F7 | React dashboard — project list, pipeline flow view (React Flow), artifact viewer | Must |
| F8 | Template management — create, clone, edit workflow templates as JSON | Must |
| F9 | LLM provider settings — add/remove providers, API key management, test connection | Must |
| F10 | Checkpoint & rollback — auto-checkpoint after each phase, rollback on failure | Must |
| F11 | Auto-mode toggle — switchable mid-run | Should |
| F12 | One default template — current compound workflow encoded as first template | Must |
| F13 | Second-opinion LLM routing — send review/planning tasks to OpenAI or Gemini | Should |

### Non-Goals (v1)

| Non-Goal | Reason | Revisit |
|----------|--------|---------|
| Visual drag-and-drop template editor | JSON editing is fine for solo dev | v2 |
| Multi-user auth / sharing | Solo dev tool | If ever shared |
| Cloud deployment / Docker | Runs locally | v2 if needed |
| Artifact diffing / cross-project comparison | Nice-to-have, not core | v2 |
| Mobile responsive UI | Desktop-only tool | Never |
| Plugin system for custom tools | Tool defs are in code, config is enough | v2 |
| Natural language template creation | Cool but scope creep | v2+ |

### Scope Boundaries

- Max 1 concurrent pipeline run
- Tool execution is local only (no remote/container sandboxing)
- Frontend is desktop-width only
- No file size limits on artifacts (local SQLite)

## 8. Modules & Milestones

### Modules

| Module | Responsibility | Complexity | Dependencies |
|--------|---------------|------------|--------------|
| M1: Data Layer | SQLModel models, DB setup, Alembic migrations, Pydantic artifact schemas | Medium | None |
| M2: Workflow Engine | Template parser, state machine, phase transitions, validation gates, checkpoint/rollback | High | M1 |
| M3: LLM Integration | Anthropic adapter (tool use + streaming), OpenAI/Gemini adapters, provider manager | High | M1 |
| M4: Tool Registry | Tool definitions (file ops, bash, git, glob, grep), execution layer, safety checks | Medium | M1 |
| M5: API Layer | FastAPI routes, WebSocket endpoint, request/response schemas | Medium | M1, M2, M3 |
| M6: Frontend Shell | React scaffold, routing, Zustand stores, TanStack Query, shadcn/ui setup | Medium | M5 |
| M7: Pipeline UI | React Flow pipeline view, custom phase nodes, real-time status, auto-mode toggle | High | M5, M6 |
| M8: Management UI | Project CRUD, template editor (JSON), LLM provider settings, artifact viewer | Medium | M5, M6 |
| M9: Default Template | Encode current compound workflow as first template JSON, phase prompts, tool configs | Low | M1, M2 |

### Dependency Graph

```
M1 (Data Layer)
├── M2 (Engine) ──┐
├── M3 (LLM) ─────┼── M5 (API) ── M6 (Frontend Shell)
├── M4 (Tools) ───┘       │              ├── M7 (Pipeline UI)
└── M9 (Template)          │              └── M8 (Management UI)
                           └──────────────────────┘
```

### Milestones

#### Milestone 1: "State Machine Walks"
**Goal:** Backend foundation — workflow engine runs phases with validated state transitions.
**Modules:** M1 (Data Layer), M2 (Workflow Engine), M4 (Tool Registry), M9 (Default Template)
**Demo:** Python script runs a 3-phase workflow template, Claude builds a small project, artifacts validated and saved to DB.

#### Milestone 2: "API Talks"
**Goal:** Backend API + LLM integration — pipeline controllable via HTTP.
**Modules:** M3 (LLM Integration), M5 (API Layer)
**Demo:** Hit API endpoints to create project, start pipeline, watch tool calls stream via WebSocket.

#### Milestone 3: "Eyes On"
**Goal:** Frontend — full visual experience.
**Modules:** M6 (Frontend Shell), M7 (Pipeline UI), M8 (Management UI)
**Demo:** Create project in UI, watch Claude work in real-time, review artifacts, manage templates and providers.

## 10. Specialist Routing

| Specialist | Status | Reason |
|------------|--------|--------|
| /specialists/competition | ⏭️ SKIPPED | Internal personal tool, no competitors |
| /specialists/domain | ⏭️ SKIP | Domain is well-understood (dev tooling) |
| /specialists/branding | ⏭️ SKIP | Personal tool, no brand needed |
| /specialists/architecture | ✅ RUN | Core system design: engine internals, LLM adapter pattern, state machine |
| /specialists/backend | ✅ RUN | FastAPI routes, WebSocket design, DB layer |
| /specialists/frontend | ✅ RUN | React pages, React Flow integration, component hierarchy |
| /specialists/design | ⏭️ SKIP | Personal tool, shadcn/ui defaults are fine |
| /specialists/uix | ⏭️ SKIP | Solo dev, known workflows |
| /specialists/security | ⏭️ SKIP | Local-only, no auth, minimal attack surface |
| /specialists/devops | ⏭️ SKIP | Local dev server only |
| /specialists/legal | ⏭️ SKIP | Personal tool, no compliance needs |
| /specialists/pricing | ⏭️ SKIP | Not a product |
| /specialists/llm | ✅ RUN | LLM integration is core — prompt design, tool schemas, model routing, context management |
| /specialists/scraping | ⏭️ SKIP | No external data ingestion |
| /specialists/data-ml | ⏭️ SKIP | No ML/analytics |
| /specialists/testing | ✅ RUN | Test strategy for engine, API, and integration tests |

**Execution order:**
1. /specialists/architecture (system design — informs everything)
2. /specialists/backend (API + DB — depends on architecture)
3. /specialists/llm (LLM integration — depends on architecture)
4. /specialists/frontend (UI — depends on backend API shape)
5. /specialists/testing (test strategy — needs all other decisions)

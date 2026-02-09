# Workflow Engine — Project Specification

**Version:** 0.5 (Discovery Phase)
**Date:** 2026-02-09
**Phase:** discovery
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
| J8 | Pause a running pipeline and resume later | Occasional | Must-have (free with DB state) |

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
<!-- PENDING: Populated by /plan-define after competition analysis -->

## 8. Modules & Milestones
<!-- PENDING: Populated by /plan-define -->

## Assumptions (Unconfirmed)

- A01: The existing .claude/ framework is reference material only — no runtime dependency
- A02: React Flow can handle the complexity of parallel phase rendering with custom nodes
- A03: SQLModel handles JSON column types well enough for artifact storage
- A04: Anthropic SDK streaming + tool use can be wrapped cleanly in an async generator for WebSocket forwarding

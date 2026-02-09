# Decisions Log — Workflow Engine

**Source:** /plan + /plan-define (Strategic Planning)
**Phase:** complete
**Total:** 28 decisions

---

### GEN-01: App type = Workflow orchestration platform
**Category:** Project
**Stage:** 0
**Decision:** Internal dev tool with FastAPI backend, React frontend, and LLM integration. Not a simple dashboard — a full control plane for driving dev workflows.
**Alternatives:** Dashboard-only viewer, CLI wrapper, VS Code extension
**Rationale:** Need to both visualize and control pipeline execution, manage LLM providers, and configure workflow templates.
**Trade-offs:** Higher scope than a read-only dashboard, but delivers full control.

---

### GEN-02: Core problem = Brittle prompt-chained workflow
**Category:** Project
**Stage:** 0
**Decision:** The current compound workflow v3 relies on LLMs correctly parsing/generating freeform markdown for state transitions. One malformed file cascades failures silently. Fix: typed Pydantic schemas as contracts between pipeline phases.
**Alternatives:** Patch the existing markdown system with better prompts, add validation hooks
**Rationale:** Prompt engineering for state management is fundamentally brittle. Typed contracts make transitions deterministic.
**Trade-offs:** Full redesign vs incremental improvement. Chose clean break for long-term reliability.

---

### GEN-03: Target user = Solo dev (personal use)
**Category:** Project
**Stage:** 0
**Decision:** No auth, no multi-tenancy, no public access. Built for one person.
**Alternatives:** Multi-user SaaS, team tool
**Rationale:** Personal workflow tool. Simplifies every architectural decision.
**Trade-offs:** Can't share with others without adding auth later.

---

### GEN-04: Planning depth = Light
**Category:** Process
**Stage:** 0
**Decision:** Light planning (4 merged stages). Solo dev personal tool doesn't need deep UX/risk analysis.
**Alternatives:** Deep (9 stages)
**Rationale:** Scope and user are well-understood. Speed matters.
**Trade-offs:** Less formal risk analysis — acceptable for personal tool.

---

### GEN-05: Success criteria defined
**Category:** Project
**Stage:** 0
**Decision:** Six measurable success criteria: validated JSON artifacts, visual progress UI, configurable templates, pluggable LLMs, full Claude file access, validated state transitions.
**Alternatives:** N/A
**Rationale:** Concrete criteria prevent scope drift and define "done."
**Trade-offs:** None.

---

### GEN-06: Clean redesign in new directory
**Category:** Project
**Stage:** 0
**Decision:** Build new system from scratch in a separate directory. Existing .claude/ framework is reference material, not a dependency.
**Alternatives:** Retrofit existing system, incremental migration
**Rationale:** Retrofitting typed schemas onto a markdown-based system creates two sources of truth. Clean break is simpler.
**Trade-offs:** No incremental value — it works or it doesn't. Existing prompt engineering investment is reference only.

---

### GEN-07: Artifact format = JSON persisted to database
**Category:** Technical
**Stage:** 0
**Decision:** All workflow state (decisions, task queues, specs, evals, audit chain) stored as validated JSON in SQLite. No markdown state files.
**Alternatives:** Keep markdown with validation layer, hybrid markdown+JSON
**Rationale:** JSON is natively parseable, validatable by Pydantic, and storable in DB. Markdown parsing is its own source of brittleness.
**Trade-offs:** Human readability moves to the React UI instead of raw files.

---

### GEN-08: Workflow templates are first-class
**Category:** Technical
**Stage:** 0
**Decision:** The current plan→specialize→synthesize→execute→retro flow is ONE template. Users can create others, modify phases, skip steps, reorder.
**Alternatives:** Hardcoded pipeline with feature flags, plugin system
**Rationale:** Configurable templates are the right abstraction — they're data, not code. New workflows without code changes.
**Trade-offs:** Template engine adds complexity. Mitigated by starting with JSON config (not visual editor).

---

### GEN-09: Separation of concerns — Python orchestrates, Claude builds, React observes+controls
**Category:** Technical
**Stage:** 0
**Decision:** Python/FastAPI owns state management, validation, and phase transitions. Claude (via API) does the thinking and code generation. React provides visibility and user controls.
**Alternatives:** Claude Code as orchestrator (current), all-in-one monolith
**Rationale:** Clean separation makes each layer testable and replaceable independently. The orchestrator is deterministic code, not prompt engineering.
**Trade-offs:** More moving parts than a monolith.

---

### GEN-10: LLM integration = Anthropic API direct with tool use
**Category:** Technical
**Stage:** 0
**Decision:** Use Anthropic Python SDK directly with tool definitions. Claude gets full file/shell access via typed tool schemas. Orchestrator controls which tools each phase gets.
**Alternatives:** Claude Code CLI as subprocess, Claude Code with FastAPI sidecar
**Rationale:** Direct API gives structured output, per-phase tool control, model routing, and an intercept layer for validation. Claude Code is a black box that can't enforce output schemas.
**Trade-offs:** Must implement tool execution layer (file ops, bash, git). Worth it for the control gained.

---

### GEN-11: Database = SQLite via SQLModel
**Category:** Technical
**Stage:** 3+4
**Decision:** SQLite for persistence, SQLModel for ORM (Pydantic + SQLAlchemy in one model class). Alembic for migrations.
**Alternatives:** PostgreSQL, filesystem JSON files
**Rationale:** Zero-config, single file, trivial backups. SQLModel means one model definition for validation AND persistence. Solo dev doesn't need Postgres.
**Trade-offs:** No concurrent write support — fine for single user.

---

### GEN-12: Templates = JSON config validated by Pydantic
**Category:** Technical
**Stage:** 3+4
**Decision:** Workflow templates are JSON files validated by Pydantic models. Config-driven for v1, visual editor is a future feature.
**Alternatives:** YAML, database-only, visual editor from day 1
**Rationale:** JSON is natively compatible with Pydantic. Config files are version-controllable. Visual editor is scope creep for v1.
**Trade-offs:** Editing JSON is less friendly than a UI — acceptable for solo dev.

---

### GEN-13: Error recovery = checkpoint-based rollback
**Category:** Technical
**Stage:** 1
**Decision:** Every phase completion creates a checkpoint in the DB (full pipeline state snapshot). Failed phases can roll back to previous checkpoint and retry. No manual file surgery.
**Alternatives:** Manual recovery, restart-from-scratch, log-and-continue
**Rationale:** DB-backed state makes checkpointing nearly free. Eliminates the #1 pain point: manually fixing corrupted markdown files.
**Trade-offs:** Checkpoint storage grows with pipeline length — mitigated by pruning old checkpoints.

---

### GEN-14: Multi-project support
**Category:** Technical
**Stage:** 1
**Decision:** DB-backed state naturally supports multiple projects. Each project is a row with its own pipeline state, artifacts, and template. UI shows a project list.
**Alternatives:** Single-project only
**Rationale:** Falls out naturally from the data model. No extra work to support.
**Trade-offs:** None meaningful.

---

### GEN-15: Auto-mode = per-pipeline toggle
**Category:** Technical
**Stage:** 2
**Decision:** When on, phases advance without user confirmation. When off, user explicitly triggers each phase. Switchable mid-run.
**Alternatives:** Always manual, always auto, per-phase setting only
**Rationale:** Some workflows need supervision (planning), others can run unsupervised (execution). Toggle lets user decide in real-time.
**Trade-offs:** Auto-mode with expensive LLM calls could burn tokens if a phase goes sideways. Mitigated by timeout (GEN-17).

---

### GEN-16: Real-time streaming via WebSocket
**Category:** Technical
**Stage:** 2
**Decision:** Claude's tool calls and reasoning stream to the React UI as they happen via FastAPI WebSocket. Live visibility into what Claude is doing, not just phase-complete notifications.
**Alternatives:** Polling, SSE, phase-complete-only updates
**Rationale:** Watching Claude work in real-time is the primary UX differentiator over the current blind CLI. WebSocket is bidirectional (needed for user controls like pause/cancel).
**Trade-offs:** WebSocket adds frontend complexity. Worth it for real-time UX.

---

### GEN-17: Phase timeout with graceful handling
**Category:** Technical
**Stage:** 2
**Decision:** Configurable timeout per phase in template. On timeout: save partial state, surface to user, allow retry.
**Alternatives:** No timeout (let it run), hard kill
**Rationale:** Claude can get stuck in tool loops. Timeout prevents runaway API costs and provides a recovery path.
**Trade-offs:** Timeout too short = false failures. Default should be generous (10-15 min for execution phases).

---

### GEN-18: Parallel phase support
**Category:** Technical
**Stage:** 2
**Decision:** Templates can mark independent phases as parallelizable. Orchestrator runs them concurrently (e.g., multiple specialists at once).
**Alternatives:** Strictly sequential, user-triggered parallel
**Rationale:** Specialists are naturally independent. Running them in parallel saves time.
**Trade-offs:** Parallel LLM calls multiply token spend. Context isolation between parallel phases must be enforced.

---

### GEN-19: Data model = 9 core entities
**Category:** Technical
**Stage:** 3+4
**Decision:** Project, WorkflowTemplate, PhaseDefinition, PipelineRun, PhaseExecution, Artifact, LLMProvider, ToolCall, Checkpoint.
**Alternatives:** Fewer entities with embedded JSON, more entities with junction tables
**Rationale:** Each entity has a clear lifecycle and purpose. Normalized enough for queries, denormalized enough for simplicity.
**Trade-offs:** 9 models is moderate complexity — manageable for solo dev.

---

### GEN-20: API key storage = Fernet-encrypted in DB
**Category:** Technical
**Stage:** 3+4
**Decision:** API keys stored in SQLite with Fernet symmetric encryption. Local key file for decryption.
**Alternatives:** Environment variables only, system keychain, HashiCorp Vault
**Rationale:** Solo dev, local only. Env vars are less convenient for multi-provider management via UI. Fernet is simple and sufficient.
**Trade-offs:** Key file on disk is a single point of compromise — acceptable for personal tool on own machine.

---

### GEN-21: Frontend stack = React + Vite + shadcn/ui + Tailwind + React Flow
**Category:** Technical
**Stage:** 3+4
**Decision:** React 18 with Vite for build. shadcn/ui + Tailwind for components/styling. React Flow for pipeline DAG visualization.
**Alternatives:** Next.js, Vue, plain CSS, D3 for visualization
**Rationale:** Vite is fastest dev experience. shadcn/ui is composable without lock-in. React Flow is purpose-built for flow diagrams. Tailwind pairs with shadcn.
**Trade-offs:** Tailwind has a learning curve if unfamiliar. shadcn requires manual component installation.

---

### GEN-22: State management = Zustand
**Category:** Technical
**Stage:** 3+4
**Decision:** Zustand for React state management.
**Alternatives:** Redux Toolkit, Jotai, React Context, MobX
**Rationale:** Minimal boilerplate, TypeScript-friendly, works well with TanStack Query for server state. Solo dev doesn't need Redux ceremony.
**Trade-offs:** Less ecosystem/middleware than Redux — fine for this scale.

---

### GEN-23: API client = TanStack Query
**Category:** Technical
**Stage:** 3+4
**Decision:** TanStack Query (React Query) for API data fetching with caching, background refetch, and optimistic updates.
**Alternatives:** SWR, raw fetch, Axios
**Rationale:** Handles cache invalidation, loading/error states, and pairs well with WebSocket for real-time updates.
**Trade-offs:** Another dependency — but solves real problems vs raw fetch.

---

### GEN-24: Project directory structure defined
**Category:** Technical
**Stage:** 3+4
**Decision:** Monorepo with backend/ (FastAPI + SQLModel + engine + LLM adapters + tools) and frontend/ (React + Vite + shadcn) plus templates/ directory for workflow configs.
**Alternatives:** Separate repos, single flat directory
**Rationale:** Monorepo keeps related code together. Clear separation between backend/frontend/templates.
**Trade-offs:** None for solo dev.

---

### GEN-25: MVP = 13 features, 7 non-goals
**Category:** Scope
**Stage:** 6+7
**Decision:** v1 includes: Pydantic models, workflow engine, Anthropic API integration, SQLite persistence, FastAPI REST API, WebSocket streaming, React dashboard, template management, LLM provider settings, checkpoint/rollback, auto-mode toggle, default template, second-opinion LLM routing. Non-goals: visual template editor, auth, cloud deploy, artifact diffing, mobile, plugins, NL template creation.
**Alternatives:** Smaller MVP (engine + CLI only), larger MVP (visual editor included)
**Rationale:** 13 features covers the full loop: define workflow → run it → see it → recover from errors. Non-goals prevent scope creep without losing core value.
**Trade-offs:** Ambitious for solo dev — mitigated by milestone structure.

---

### GEN-26: 9 modules with clean dependency DAG
**Category:** Scope
**Stage:** 6+7
**Decision:** M1 (Data Layer), M2 (Workflow Engine), M3 (LLM Integration), M4 (Tool Registry), M5 (API Layer), M6 (Frontend Shell), M7 (Pipeline UI), M8 (Management UI), M9 (Default Template). No circular dependencies.
**Alternatives:** Fewer coarser modules, more fine-grained modules
**Rationale:** Each module has clear responsibility and testable boundaries. Dependencies flow one direction.
**Trade-offs:** 9 modules is moderate — manageable with milestone grouping.

---

### GEN-27: 3 milestones — backend-first, API-second, frontend-last
**Category:** Scope
**Stage:** 6+7
**Decision:** MS1 "State Machine Walks" (M1+M2+M4+M9), MS2 "API Talks" (M3+M5), MS3 "Eyes On" (M6+M7+M8). Each is independently demo-able.
**Alternatives:** Vertical slices (thin feature end-to-end), frontend-first prototyping
**Rationale:** Backend-first ensures the hard problems (engine, validation, tool execution) are solved before building UI on top. Each milestone produces a working system at increasing capability.
**Trade-offs:** No visual feedback until MS3 — acceptable because CLI/API testing covers MS1-MS2.

---

### GEN-28: Highest-risk module = M2 (Workflow Engine)
**Category:** Scope
**Stage:** 6+7
**Decision:** The workflow engine (state machine, parallel phases, checkpoint/rollback, validation gates) is the most complex and highest-risk module. Built first in MS1 to de-risk early.
**Alternatives:** Start with simpler modules to build momentum
**Rationale:** If the engine doesn't work, nothing else matters. Early de-risking.
**Trade-offs:** Slower start — harder module first means more time before first visible result.

---

## Pending for Specialists

| Decision | Assigned To | Context |
|----------|-------------|---------|
| Engine internals: state machine, phase transitions, checkpoint strategy | /specialists/architecture | Core system design |
| LLM adapter pattern, provider abstraction, context management | /specialists/architecture | Multi-LLM integration pattern |
| FastAPI routes, WebSocket design, request/response schemas | /specialists/backend | API layer design |
| DB schema finalization, migration strategy | /specialists/backend | SQLModel details |
| Prompt design per phase, tool schemas, model routing strategy | /specialists/llm | LLM integration details |
| Context window management, structured output patterns | /specialists/llm | Anthropic API specifics |
| React pages, React Flow integration, component hierarchy | /specialists/frontend | UI architecture |
| Real-time streaming UX, state synchronization | /specialists/frontend | WebSocket + Zustand |
| Test strategy: engine unit tests, API integration tests, E2E | /specialists/testing | Quality assurance |

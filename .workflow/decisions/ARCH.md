# Decisions Log — Architecture

**Source:** /specialists/architecture
**Total:** 16 decisions

---

### ARCH-01: Modular monolith — single FastAPI process with package-level boundaries
**Category:** System Pattern
**Decision:** All 9 modules live in one FastAPI process, separated by Python packages with explicit public interfaces. Modules communicate via direct function calls and shared Pydantic types.
**Alternatives:** Microservices, service mesh, separate processes
**Rationale:** Solo dev, local-only. Monolith is correct. No deploy complexity.
**Trade-offs:** Can't scale modules independently — irrelevant for single user.

---

### ARCH-02: Async-first with sync fallback
**Category:** System Pattern
**Decision:** FastAPI is async-native. LLM API calls, WebSocket streaming, and DB queries use async/await. Tool execution (bash, file ops) uses asyncio.to_thread() to avoid blocking. SQLite via aiosqlite + SQLAlchemy async engine.
**Alternatives:** Fully sync with threading, fully async
**Rationale:** Streaming LLM responses while handling WebSocket clients requires async. Sync tool execution wraps cleanly.
**Trade-offs:** Async SQLite has single writer lock — fine for single user.

---

### ARCH-03: Strict dependency direction — no circular imports
**Category:** Module Boundaries
**Decision:** Dependency flows one way: M5(API) → M2(Engine) → M3(LLM) → M4(Tools) → M1(Data). No module may import from a module above it. Enforced by import linting.
**Alternatives:** Allow bidirectional with interfaces, event bus
**Rationale:** Clean dependency graph makes testing and reasoning easy.
**Trade-offs:** May need event callbacks for upward communication — acceptable.

---

### ARCH-04: Shared types via Pydantic schemas in app/schemas/
**Category:** Module Boundaries
**Decision:** All inter-module communication uses Pydantic models defined in app/schemas/. No raw dicts, no SQLModel instances crossing module boundaries.
**Alternatives:** Pass ORM objects directly, use TypedDicts
**Rationale:** Decouples DB representation from API/engine contracts.
**Trade-offs:** Some mapping boilerplate (SQLModel ↔ Pydantic). Worth it for clean boundaries.

---

### ARCH-05: SQLite with aiosqlite, WAL mode, auto-migrations on startup
**Category:** Infrastructure
**Decision:** Single SQLite file at data/workflow.db. WAL mode for better read concurrency. Alembic migrations auto-run on app startup.
**Alternatives:** PostgreSQL, manual migration running
**Rationale:** Zero config. WAL mode is strictly better than default journal mode. Auto-migration safe for solo dev.
**Trade-offs:** None meaningful at this scale.

---

### ARCH-06: No caching layer for v1
**Category:** Infrastructure
**Decision:** SQLite is fast enough for single-user local queries. No Redis, no in-memory cache.
**Alternatives:** Redis, in-memory LRU cache
**Rationale:** Premature optimization. SQLite < 50ms per query is easily met.
**Trade-offs:** Add caching later if performance targets missed.

---

### ARCH-07: No background job system — engine IS the job runner
**Category:** Infrastructure
**Decision:** LLM conversations run as async tasks within the FastAPI process. Phase execution is managed by the engine, streamed via WebSocket. No Celery, no task queue.
**Alternatives:** Celery, ARQ, dramatiq
**Rationale:** The engine IS the job runner. Separate job system adds complexity for zero benefit.
**Trade-offs:** If FastAPI process dies mid-phase, phase is lost. Checkpoints mitigate (resume from last checkpoint on restart).

---

### ARCH-08: Env config via .env + Pydantic BaseSettings
**Category:** Infrastructure
**Decision:** Single .env file for local config (DB path, log level, default model). Pydantic BaseSettings validates at startup. API keys live in DB (GEN-20).
**Alternatives:** YAML config, env vars only, secrets manager
**Rationale:** Pydantic Settings validates config at startup. One file, one source of truth.
**Trade-offs:** None.

---

### ARCH-09: Local dev = uvicorn + vite dev, no Docker
**Category:** Infrastructure
**Decision:** No Docker compose, no devcontainer. uvicorn --reload for backend, npm run dev for frontend.
**Alternatives:** Docker compose, devcontainer
**Rationale:** Solo dev, local only. Docker adds overhead for zero benefit.
**Trade-offs:** None at this scale.

---

### ARCH-10: Error hierarchy — WorkflowError base with typed subclasses
**Category:** Cross-Cutting
**Decision:** Base WorkflowError with subclasses: PhaseValidationError, PhaseTimeoutError, ProviderError, ToolExecutionError, CheckpointError, TemplateError. API layer catches and maps to HTTP status codes.
**Alternatives:** Generic exceptions, error codes without hierarchy
**Rationale:** Typed exceptions enable precise catch blocks and clear error handling paths.
**Trade-offs:** None.

---

### ARCH-11: Structured JSON logging via stdlib
**Category:** Cross-Cutting
**Decision:** JSON-formatted structured logs via Python stdlib logging. Context fields: timestamp, level, module, message, project_id, phase_id, run_id. Levels: DEBUG (tool calls), INFO (transitions), WARNING (retries), ERROR (failures).
**Alternatives:** Loguru, structlog
**Rationale:** Stdlib is sufficient. No external dependency needed.
**Trade-offs:** Less ergonomic than structlog — acceptable.

---

### ARCH-12: DI via FastAPI Depends(), singletons at startup
**Category:** Cross-Cutting
**Decision:** FastAPI's built-in DI for request-scoped deps (DB session). Engine and LLM adapters are singletons initialized at app startup via lifespan.
**Alternatives:** dependency-injector library, manual wiring
**Rationale:** FastAPI's DI is powerful enough. External DI is overkill.
**Trade-offs:** None.

---

### ARCH-13: Consistent API error envelope
**Category:** Cross-Cutting
**Decision:** All error responses use format: {"error": {"code": "UPPER_SNAKE", "message": "human readable", "details": {}, "phase_id": "uuid", "run_id": "uuid"}}. Error codes are uppercase snake_case strings.
**Alternatives:** Plain text errors, problem+json RFC 7807
**Rationale:** Consistent envelope makes frontend error handling predictable.
**Trade-offs:** Slightly verbose — worth it for consistency.

---

### ARCH-14: LLM adapter protocol with per-provider implementations
**Category:** Integration
**Decision:** Abstract LLMAdapter protocol with run_conversation() and test_connection(). Three implementations: AnthropicAdapter, OpenAIAdapter, GeminiAdapter. Engine doesn't know which provider it's using.
**Alternatives:** Direct SDK usage, single adapter with switch
**Rationale:** Provider abstraction lets you swap LLMs per phase without engine changes.
**Trade-offs:** Lowest-common-denominator API. Provider-specific features need escape hatches.

---

### ARCH-15: StreamEvent union type for real-time WebSocket updates
**Category:** Integration
**Decision:** Union type: TextDelta | ToolCallStart | ToolCallResult | PhaseProgress | PhaseComplete | PhaseError. Engine produces events, API forwards to WebSocket, frontend renders per type.
**Alternatives:** Raw JSON, string messages, SSE
**Rationale:** Typed events make frontend rendering deterministic. WebSocket is bidirectional (pause/cancel).
**Trade-offs:** More event types may be needed — extensible by adding union members.

---

### ARCH-16: Log-based monitoring only, no observability stack
**Category:** Performance
**Decision:** No Prometheus, Grafana, or APM. Structured logs + DB-recorded phase timings (started_at/completed_at) are sufficient.
**Alternatives:** Full observability stack
**Rationale:** Solo dev, local tool. Observability stack is overkill.
**Trade-offs:** Less visibility into performance — acceptable, add later if needed.

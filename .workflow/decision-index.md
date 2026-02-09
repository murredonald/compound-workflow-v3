# Decision Index

| ID | Decision | Source | Stage |
|----|----------|--------|-------|
| GEN-01 | App type = Workflow orchestration platform | /plan | 0 |
| GEN-02 | Core problem = Brittle prompt-chained workflow | /plan | 0 |
| GEN-03 | Target user = Solo dev (personal use) | /plan | 0 |
| GEN-04 | Planning depth = Light | /plan | 0 |
| GEN-05 | Success criteria defined (6 criteria) | /plan | 0 |
| GEN-06 | Clean redesign in new directory | /plan | 0 |
| GEN-07 | Artifact format = JSON persisted to database | /plan | 0 |
| GEN-08 | Workflow templates are first-class | /plan | 0 |
| GEN-09 | Python orchestrates, Claude builds, React observes+controls | /plan | 0 |
| GEN-10 | LLM integration = Anthropic API direct with tool use | /plan | 0 |
| GEN-11 | Database = SQLite via SQLModel | /plan | 3+4 |
| GEN-12 | Templates = JSON config validated by Pydantic | /plan | 3+4 |
| GEN-13 | Error recovery = checkpoint-based rollback | /plan | 1 |
| GEN-14 | Multi-project support | /plan | 1 |
| GEN-15 | Auto-mode = per-pipeline toggle | /plan | 2 |
| GEN-16 | Real-time streaming via WebSocket | /plan | 2 |
| GEN-17 | Phase timeout with graceful handling | /plan | 2 |
| GEN-18 | Parallel phase support | /plan | 2 |
| GEN-19 | Data model = 9 core entities | /plan | 3+4 |
| GEN-20 | API key storage = Fernet-encrypted in DB | /plan | 3+4 |
| GEN-21 | Frontend = React + Vite + shadcn/ui + Tailwind + React Flow | /plan | 3+4 |
| GEN-22 | State management = Zustand | /plan | 3+4 |
| GEN-23 | API client = TanStack Query | /plan | 3+4 |
| GEN-24 | Project directory structure = monorepo (backend/frontend/templates) | /plan | 3+4 |
| GEN-25 | MVP = 13 features, 7 non-goals | /plan-define | 6+7 |
| GEN-26 | 9 modules with clean dependency DAG | /plan-define | 6+7 |
| GEN-27 | 3 milestones — backend-first, API-second, frontend-last | /plan-define | 6+7 |
| GEN-28 | Highest-risk module = M2 (Workflow Engine) | /plan-define | 6+7 |
| ARCH-01 | Modular monolith — single FastAPI process, package-level boundaries | /specialists/architecture | FA1 |
| ARCH-02 | Async-first with sync fallback via asyncio.to_thread() | /specialists/architecture | FA1 |
| ARCH-03 | Strict dependency direction — no circular imports | /specialists/architecture | FA2 |
| ARCH-04 | Shared types via Pydantic schemas, no ORM objects crossing boundaries | /specialists/architecture | FA2 |
| ARCH-05 | SQLite with aiosqlite, WAL mode, auto-migrations on startup | /specialists/architecture | FA3 |
| ARCH-06 | No caching layer for v1 | /specialists/architecture | FA3 |
| ARCH-07 | No background job system — engine IS the job runner | /specialists/architecture | FA3 |
| ARCH-08 | Env config via .env + Pydantic BaseSettings | /specialists/architecture | FA3 |
| ARCH-09 | Local dev = uvicorn + vite dev, no Docker | /specialists/architecture | FA3 |
| ARCH-10 | Error hierarchy — WorkflowError base with typed subclasses | /specialists/architecture | FA4 |
| ARCH-11 | Structured JSON logging via stdlib | /specialists/architecture | FA4 |
| ARCH-12 | DI via FastAPI Depends(), singletons at startup | /specialists/architecture | FA4 |
| ARCH-13 | Consistent API error envelope with typed error codes | /specialists/architecture | FA4 |
| ARCH-14 | LLM adapter protocol with per-provider implementations | /specialists/architecture | FA5 |
| ARCH-15 | StreamEvent union type for real-time WebSocket updates | /specialists/architecture | FA5 |
| ARCH-16 | Log-based monitoring only, no observability stack | /specialists/architecture | FA6 |
| BACK-01 | REST API at /api/ prefix, auto-generated OpenAPI docs | /specialists/backend | FA1 |
| BACK-02 | 7 endpoint groups, ~25 endpoints total | /specialists/backend | FA1 |
| BACK-03 | Pagination via limit/offset query params | /specialists/backend | FA1 |
| BACK-04 | Pydantic v2 strict mode for all request/response schemas | /specialists/backend | FA2 |
| BACK-05 | Pipeline + phase state machine with defined transitions | /specialists/backend | FA2 |
| BACK-06 | Three validation layers — request, service, DB | /specialists/backend | FA2 |
| BACK-07 | Template validation on create/update (no circular deps, valid schemas) | /specialists/backend | FA2 |
| BACK-08 | UUID primary keys, snake_case naming | /specialists/backend | FA3 |
| BACK-09 | 8 core tables with typed columns, indexes, FK constraints | /specialists/backend | FA3 |
| BACK-10 | Cascade deletes for children, RESTRICT for references, no soft delete | /specialists/backend | FA3 |
| BACK-11 | Alembic migrations with descriptive names, auto-run on startup | /specialists/backend | FA3 |
| BACK-12 | Transactional operations with post-commit side effects | /specialists/backend | FA4 |
| BACK-13 | No concurrency control needed (single user) | /specialists/backend | FA4 |
| BACK-14 | Three LLM provider integrations via SDK with retry/backoff | /specialists/backend | FA5 |
| BACK-15 | Secondary LLM failure is non-blocking | /specialists/backend | FA5 |

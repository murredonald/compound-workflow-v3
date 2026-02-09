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

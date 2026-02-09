# Constraints — Workflow Engine

**Source:** /plan + /plan-define (Strategic Planning)
**Phase:** complete

---

## Hard Constraints (Non-Negotiable)

### Team
- **Constraint:** Solo developer, personal use only
- **Impact:** No auth, no multi-tenancy, no team features. Simplifies every design decision. No need for role-based access, audit for compliance, or user management.

### Budget
- **Constraint:** LLM API costs are the only variable cost (Anthropic, OpenAI, Gemini)
- **Impact:** Token-efficient design matters. Phase timeouts prevent runaway costs. Model routing (Haiku for simple, Opus for complex) optimizes spend.

### Technical
- **Constraint:** Must use Anthropic API with tool use for Claude integration
- **Impact:** Orchestrator must implement tool execution layer (file ops, bash, git). Structured output via tool schemas, not prompt engineering.

### Stack
- **Constraint:** FastAPI + Pydantic + SQLModel backend, React + Vite frontend
- **Impact:** Python 3.11+ required. Node.js for frontend build. Both run locally.

---

## Scope Boundaries

### In Scope (v1)
- Pydantic models for all artifact types
- Workflow engine with template-driven state machine
- Anthropic API integration with tool use
- SQLite persistence via SQLModel
- FastAPI REST API + WebSocket streaming
- React dashboard with React Flow pipeline visualization
- Template management (JSON config)
- LLM provider settings with encrypted API keys
- Checkpoint-based rollback
- Auto-mode toggle
- Default template (compound workflow)
- Second-opinion LLM routing

### Out of Scope (v1)
- Visual drag-and-drop template editor (v2)
- Multi-user auth / sharing (if ever shared)
- Cloud deployment / Docker (v2 if needed)
- Artifact diffing / cross-project comparison (v2)
- Mobile responsive UI (never)
- Plugin system for custom tools (v2)
- Natural language template creation (v2+)

### Boundaries
- Max 1 concurrent pipeline run
- Tool execution is local only (no remote/container sandboxing)
- Frontend is desktop-width only
- No file size limits on artifacts (local SQLite)

---

## Performance Targets

| Metric | Target | Priority |
|--------|--------|----------|
| Phase transition validation | < 100ms | Must-meet |
| UI responsiveness | < 200ms for interactions | Must-meet |
| WebSocket latency (tool call → UI) | < 500ms | Should-meet |
| SQLite query time | < 50ms for any single query | Must-meet |
| Cold start (backend) | < 3s | Should-meet |

---

## Data Constraints

| Constraint | Limit | Rationale |
|------------|-------|-----------|
| Max concurrent pipeline runs | 1 (solo dev) | SQLite write concurrency, single user |
| Checkpoint retention | Last 10 per pipeline run | Prevent unbounded DB growth |
| Tool call log retention | Full run history | Audit trail, manageable at solo scale |
| Artifact size | No hard limit (JSON in SQLite) | Single user, local storage |

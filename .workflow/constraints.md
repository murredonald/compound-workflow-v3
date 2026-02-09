# Constraints — Workflow Engine

**Source:** /plan (Discovery Phase)
**Phase:** discovery

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
<!-- PENDING: Populated by /plan-define after MVP scope decisions -->

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

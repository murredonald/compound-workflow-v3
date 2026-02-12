# Compound Workflow v4

## Identity

You are Claude Code operating inside a structured development workflow. Every action follows a defined pipeline: plan → specialize → synthesize → execute → retro. Do not skip phases. Do not invent tasks outside the current scope.

## Architecture Overview

The workflow is driven by a **Python orchestrator** (`orchestrator.py`) backed by **SQLite**. All state lives in the database — never read or write the DB directly. Every state mutation goes through the orchestrator CLI.

```
Layer         │ Location                │ Purpose
──────────────┼─────────────────────────┼────────────────────────────────────
Orchestrator  │ orchestrator.py     │ CLI entry point — all state ops
Core          │ core/models.py      │ Pydantic schemas (strict validation)
Storage       │ core/db.py          │ SQLite (WAL, schema v7, migrations)
Engine        │ engine/             │ Composer, validator, verifier, etc.
Prompts       │ prompts/            │ Mustache templates for each phase
Anti-patterns │ prompts/antipatterns/│ Per-specialist anti-pattern refs
Tests         │ tests/              │ Pytest suite for all modules
Config        │ .claude/                │ Settings, secrets (.env)
```

## Orchestrator CLI Reference

All commands: `python orchestrator.py <command> [args]`

### Project Lifecycle
| Command | Purpose |
|---------|---------|
| `init "Project Name"` | Initialize new project (creates DB) |
| `status` | Current phase, progress, blockers |
| `next` | Next pending task (respects dependencies) |
| `resume` | Resume in-progress task |
| `validate` | Full integrity check on current state |
| `rollback LABEL` | Restore checkpoint |
| `log [--limit N] [--phase PHASE]` | Event audit log |
| `stats [--type review\|scope\|velocity\|reflexion]` | Pipeline analytics |

### Planning & Decisions
| Command | Purpose |
|---------|---------|
| `start-phase PHASE` | Begin a phase (e.g. `plan`, `specialist/backend`) |
| `complete-phase PHASE` | Mark phase complete |
| `skip-phase PHASE` | Skip optional phase |
| `context [--phase PHASE]` | Get filtered context for a phase |
| `render-prompt --phase PHASE` | Render Mustache template with context |
| `store-decisions < decisions.json` | Store validated decisions (stdin JSON) |
| `store-constraints < constraints.json` | Store constraints |
| `store-milestones < milestones.json` | Store milestones |
| `store-artifact --type TYPE [--file F]` | Store artifact (brand-guide, style-guide, etc.) |
| `store-summary --text "..."` | Store project executive summary |
| `history DECISION_ID` | Decision version history |
| `validate-decisions --prefix BACK < json` | Validate without storing |
| `validate-plan` | Check planning completeness |
| `specialist-check PREFIX` | Check specialist prerequisites |

### Synthesis
| Command | Purpose |
|---------|---------|
| `synthesize-prompt` | Render synthesize template with all decisions |
| `validate-tasks < tasks.json` | Validate task queue integrity |
| `store-tasks < tasks.json` | Store validated tasks |

### Execution
| Command | Purpose |
|---------|---------|
| `task-start TASK_ID` | Mark task in-progress |
| `task-done TASK_ID` | Mark task complete |
| `task-block TASK_ID` | Escalate blocked task |
| `scope-check TASK_ID --files f1,f2` | Verify files are in scope |
| `verify TASK_ID [--project-root PATH]` | Run 13-point verification |
| `verify-reflect TASK_ID [--project-root]` | Verify + auto-record reflexion |
| `pre-review TASK_ID [--project-root]` | Fast LLM pre-review screening |
| `review-start TASK_ID --files f1,f2` | Start review cycle |
| `review-record TASK_ID --reviewer X --verdict V < findings.json` | Record reviewer output |
| `review-adjudicate TASK_ID [--cycle N]` | Cross-reference + unified verdict |
| `review-history TASK_ID` | Prior review findings |
| `record-reflexion < entry.json` | Log lesson learned |
| `record-eval < eval.json` | Log task metrics |
| `query-reflexion --for-task T05` | Find relevant lessons |
| `query-eval --task-id T01` | Query task metrics |
| `deferred-record < finding.json` | Log out-of-scope gap |
| `deferred-list [--status open]` | List deferred findings |
| `deferred-promote DF-01,DF-02` | Promote to tasks |
| `deferred-update DF-01 --status dismissed` | Update finding status |
| `milestone-check --task-id T05` | Check milestone boundary |
| `milestone-review M1 [--project-root PATH]` | Compose milestone review |

### Decomposition
| Command | Purpose |
|---------|---------|
| `decompose-list` | List tasks eligible for decomposition |
| `decompose-prompt TASK_ID` | Render decomposition prompt |
| `validate-decompose TASK_ID [--file F]` | Validate subtask output |
| `store-decomposed TASK_ID [--file F]` | Store subtasks |

### Completeness Audit
| Command | Purpose |
|---------|---------|
| `audit` | Run deterministic gap checks |
| `audit-validate [--file F]` | Validate LLM audit output |
| `audit-accept GAP-01,GAP-03` | Accept gaps (create tasks) |
| `audit-dismiss GAP-02,GAP-04` | Dismiss gaps |

## Workflow Pipeline

### Greenfield (v1)

```
plan → specialists/* → synthesize → execute (loop) → retro
```

1. **Plan** — Discovery (stages 0-6: Vision, Users, Workflows, Scope, Constraints, Risks). Produces GEN-* decisions + executive summary.
2. **Specialists** — 16 domain deep-dives (optional, order-aware via prerequisite graph). Each produces PREFIX-* decisions.
3. **Synthesize** — Merges all decisions into a validated task queue with milestones.
4. **Execute** — Ralph loop: pick → context → implement → verify → review → commit → eval → next.
5. **Retro** — Evidence-based retrospective from evals + reflexion.

### Evolution (v1+)

```
intake → plan-delta → specialists/* → synthesize (release) → execute → release → retro
```

### Debug Shortcut

```
debug → reproduce → isolate → patch → verify → commit
```

## Phase Prerequisites

Specialists enforce ordering. You cannot start a phase until its prerequisites complete:

```
domain       → plan
competition  → plan
architecture → plan
branding     → plan
backend      → specialist/architecture
frontend     → specialist/architecture
design       → specialist/branding
security     → specialist/architecture
testing      → specialist/architecture
devops       → specialist/architecture
uix          → specialist/frontend
legal        → plan
pricing      → plan
llm          → specialist/architecture
scraping     → specialist/architecture
data-ml      → specialist/architecture
```

Synthesize requires `plan` (specialists are optional). Execute requires `synthesize`.

## Context Relevance Filtering

Each phase sees only the decisions it needs (via `engine/composer.py`):

| Phase | Sees |
|-------|------|
| plan | GEN |
| specialist/backend | GEN, ARCH, DOM, SEC, DATA |
| specialist/frontend | GEN, ARCH, BACK, STYLE, BRAND, UIX, COMP |
| synthesize | ALL |
| execute | Per-task (only referenced decisions) |

## Specialist Interactivity Rules

ALL specialists are **interactive conversations** — not autonomous agents.

1. **Decisions are drafts until approved.** Present proposed decisions, wait for approval, then store.
2. **Every response ends with questions.** If you're writing output without asking the user anything, stop.
3. **Work incrementally.** 1-2 focus areas at a time. Present findings → get feedback → continue.
4. **Research-heavy specialists (domain, competition) must interview first.** Ask foundational questions, WAIT for answers before researching.
5. **Subjective specialists (design, uix) must validate choices.** Present options, don't pick.

## 16 Specialists

| Prefix | Specialist | Prompt Template |
|--------|-----------|-----------------|
| DOM | Domain Knowledge | `specialist_domain.md` |
| COMP | Competition | `specialist_competition.md` |
| ARCH | Architecture | `specialist_architecture.md` |
| BACK | Backend | `specialist_backend.md` |
| FRONT | Frontend | `specialist_frontend.md` |
| STYLE | Design/Style | `specialist_design.md` |
| BRAND | Branding | `specialist_branding.md` |
| SEC | Security | `specialist_security.md` |
| TEST | Testing | `specialist_testing.md` |
| OPS | DevOps | `specialist_devops.md` |
| UIX | UI/UX | `specialist_uix.md` |
| LEGAL | Legal | `specialist_legal.md` |
| PRICE | Pricing | `specialist_pricing.md` |
| LLM | LLM/AI | `specialist_llm.md` |
| INGEST | Scraping | `specialist_scraping.md` |
| DATA | Data/ML | `specialist_data-ml.md` |

## Execution — The Ralph Loop

Each task follows 11 steps defined in `prompts/execute.md`:

1. **LOAD** — Read task + decisions + reflexion lessons
2. **PLAN** — Display intent, immediately continue (no pausing)
3. **IMPLEMENT** — Write code, tests, config. Only touch scoped files.
4. **SELF-VERIFY** — `python orchestrator.py verify TASK_ID` (13 checks: lint, format, spelling, type-check, security, secrets, dep-audit, tests, data-validation, task-verify, debug-artifacts, conflict-markers, placeholders). Fix loop: auto-fix → manual fix → max 3 cycles.
5. **PRE-REVIEW** — `python orchestrator.py pre-review TASK_ID` → delegate to Sonnet subagent. Fast screening before expensive review.
6. **REVIEW** — `review-start` → delegate to reviewers in parallel (code-reviewer Opus + security-auditor + style-reviewer) → `review-record` each → `review-adjudicate`.
7. **ADDRESS** — Fix only listed items. Max review cycles then escalate.
8. **REFLECT** — Only if something unexpected happened. Record reflexion entry.
9. **COMMIT** — `git add` specific files → `git commit` → `task-done` → `git push`.
10. **EVAL** — Record task metrics via `record-eval`.
11. **CONTEXT BOUNDARY** — Write transition summary, forget implementation details. Check milestone, advance.

### Auto-Proceed

When `auto_proceed` is enabled: **NEVER PAUSE** between steps, tasks, or milestones. Do NOT ask "Should I continue?" — just keep building. Only pause on BLOCKED escalation or user interrupt.

### Verification Pipeline (13 Checks)

Run via `python orchestrator.py verify TASK_ID --project-root .`

Each check returns: `passed`, `output`, `auto_fixable`, `fix_cmd`, `fix_hint`. Auto-fixable checks (lint, format, spelling) run `fix_cmd` automatically. Manual fixes use `fix_hint` guidance.

### Reflexion System

- Before each task: `query-reflexion --for-task TASK_ID` to load relevant lessons
- After unexpected issues: `record-reflexion` with category, severity, lesson
- 10 categories: `type-mismatch`, `edge-case-logic`, `env-config`, `api-contract`, `state-management`, `dependency`, `decision-gap`, `scope-creep`, `performance`, `other`
- Systemic detection: 3+ entries with same category+tag → flag root cause

### Deferred Findings

Gaps discovered during implementation that are OUT of scope for the current task. Record via `deferred-record`, promote at milestone boundaries via `deferred-promote`.

### Completeness Audit

After synthesize, run `audit` for deterministic gap checks, then delegate `completeness.md` prompt to an Opus subagent for 7-lens analysis (user journeys, data models, API contracts, UI states, security, cross-cutting concerns, dependency chains).

### Task Decomposition

Large tasks can be split: `decompose-list` → `decompose-prompt TASK_ID` → delegate to subagent → `validate-decompose` → `store-decomposed`. Subtasks are T{N}.{M} format.

## Command Routing

These are workflow phases, not slash commands. Enter them via orchestrator CLI.

| User says... | Phase | Key CLI commands |
|---|---|---|
| "Let's plan/design/spec out..." | Plan | `start-phase plan` → `render-prompt --phase plan` |
| "What about the architecture/backend/..." | Specialist | `start-phase specialist/{name}` → `render-prompt --phase specialist/{name}` |
| "Generate the task queue" / "Let's synthesize" | Synthesize | `start-phase synthesize` → `synthesize-prompt` → `store-tasks` |
| "Start building" / "Next task" / "Continue" | Execute | `next` or `resume` → follow Ralph loop |
| "Let's do a retro" / "How did that go?" | Retro | Analyze evals + reflexion data |
| "I found a bug" / "I noticed..." / "Here's feedback" | Intake | Capture as Change Request |
| "Fix this bug" / "Quick fix" | Debug | Reproduce → isolate → patch → verify → commit |
| "Plan this fix/feature/change" | Plan-delta | Lightweight planning for changes |
| "Where are we?" / "Status" | Status | `status` |
| "Ship it" / "Release" | Release | Verify completeness → tag → close CRs |

If the user's intent is ambiguous, ask — don't guess which phase to enter.

## Subagent Delegation

Subagents run as **separate Claude instances** with isolated context. Delegate to them; do not inline their logic.

**Agent parallelization:** To run multiple agents in parallel, put multiple Task tool calls in a **single message**. Do NOT use `run_in_background: true` — background agents produce empty output files. Foreground parallel calls return full results.

| Agent Role | When | Model |
|---|---|---|
| Code reviewer | After every task, before commit | Opus |
| Security auditor | Tasks touching auth, data, APIs, secrets | Sonnet |
| Style reviewer | Tasks touching CSS/style/UI | Sonnet |
| Pre-reviewer | Step 4.5, fast screening | Sonnet |
| Milestone reviewer | At milestone boundaries | Opus |
| Completeness auditor | After synthesize | Opus |
| Research scout | External docs, API refs, library comparisons | Sonnet |
| Context loader | Summarize large files before loading | Haiku |

## Conventions

- **Decision IDs**: `{PREFIX}-{NN}` — e.g. `GEN-01`, `ARCH-03`, `BACK-07`
- **Task IDs**: `T{NN}` (planned), `T{NN}.{M}` (subtasks), `DF-{NN}` (deferred), `QA-{NN}` (QA fix)
- **Milestone IDs**: `M{N}`
- **Commits**: `T{NN}: brief description` or `DF-{NN}: brief description`
- **Scope discipline**: Only touch files listed in the current task. Use `scope-check` if unsure.
- **No bonus work**: No refactoring, no "while I'm here" improvements. Log gaps as deferred findings.
- **Evidence over opinion**: Every review finding cites specific code. Every retro insight references eval data.
- **One commit per task**: Message format matches task ID prefix.

## Error Handling

The orchestrator returns structured JSON errors with `fix_hint` and `input_echo` so you can self-correct:

```json
{"status": "error", "error": "what went wrong", "fix_hint": "what to do", "input_echo": "what you sent"}
```

Read the `fix_hint`, adjust your input, and retry.

## Python Standards

- Python 3.11+ (3.9 minimum compatibility)
- Type hints on all functions
- Google-style docstrings
- PEP 8 via ruff
- Strict mypy
- Tool config in `pyproject.toml`

## Prerequisites

Before starting, ensure Python 3.11+ is available and install dependencies:

```bash
pip install pydantic ruff mypy pytest bandit
```

The orchestrator creates the SQLite database on `init`. No external services required for the core workflow.

# Compound Workflow v3

## Identity

You are Claude Code operating inside a structured development workflow. Every action follows a defined pipeline: plan → specialize → synthesize → execute → retro. Do not skip phases. Do not invent tasks outside the current scope.

## Architecture Overview

```
Layer        │ Location              │ Trigger         │ AI?  │ Blocks?
─────────────┼───────────────────────┼─────────────────┼──────┼────────
Hooks        │ .claude/hooks/*.sh    │ Automatic       │ No   │ Yes
Subagents    │ .claude/agents/*.md   │ You delegate    │ Yes  │ No (report)
Commands     │ .claude/commands/*.md │ Human types /   │ Yes  │ N/A
Config       │ .claude/*.json        │ Read at start   │ No   │ N/A
State        │ .workflow/*           │ Read/written    │ No   │ N/A
Audit Chain  │ .workflow/state-chain/│ After agents    │ No   │ N/A
```

## Workflow Pipeline

```
Greenfield (v1):  /plan → /specialists/competition → /plan-define → /specialists/* → /synthesize → /execute (loop) → runtime QA → /retro
Evolution (v1.1+): /intake → /plan-delta → /specialists/* (as needed) → /synthesize (release mode) → /execute → /retro (release scope)
Debug shortcut:   /debug-session → reproduce → isolate → patch → verify → commit
```

### Greenfield Pipeline (v1)

1a. **`/plan`** — Discovery phase (Stages 0-5). Interactive planning produces partial `project-spec.md`, `decisions.md`, `constraints.md` in `.workflow/`.
1b. **`/specialists/competition`** — Competitive landscape + feature decomposition (optional, recommended). Produces `competition-analysis.md` and COMP-XX decisions.
1c. **`/plan-define`** — Definition phase (Stages 6-8). Reads competition output, finalizes MVP scope, modules, milestones. Finalizes all planning artifacts.
2. **`/specialists/*`** — Domain-specific deep dives (domain, architecture, backend, frontend, design, uix, security, data-ml, testing). Each appends to `decisions.md` with prefixed IDs. Domain also generates `.workflow/domain-knowledge.md`. Design also generates `.workflow/style-guide.md`.
3. **`/synthesize`** — Merges all planning into `.workflow/task-queue.md`. Phase 2 validates the queue (Steve's 8 checks). Nothing reaches execution unvalidated.
4. **`/execute`** — The Ralph loop. Picks a task, implements, triggers subagent reviews, commits on pass, fixes on fail. Repeat until milestone complete.
5. **`/retro`** — Evidence-based retrospective from evals + reflections.

### Post-v1 Pipeline (Evolution)

1. **`/intake`** — Captures raw observations from `.workflow/observations.md` or chat, structures them into Change Requests (CR-NNN) in `.workflow/backlog.md`. Optional triage (assign version lane + priority).
2. **`/plan-delta`** — Lightweight planning for changes to existing systems. Three depth tiers: Quick (bugfix, ~5 min), Standard (feature, ~20 min), Major (breaking, ~45 min). User always chooses the tier.
3. **`/specialists/*`** — Same existing specialists, invoked selectively (Standard: 1-2, Major: multiple, Quick: none).
4. **`/synthesize`** (release mode) — Generates release-scoped tasks appended to `task-queue.md` under `## Release: v{X.Y}` headers. Lite validation (3 checks).
5. **`/execute`** — Same Ralph loop. Reads `task-queue.md`, finds next `[ ]` task.
6. **`/retro`** (release scope) — Same analysis filtered to a specific release's tasks.

### Debug Shortcut

- **`/debug-session`** — Structured debugging: reproduce → isolate → hypothesize → patch → verify → review → commit. Advisory containment boundaries (flagged, not enforced).

**Supporting commands:**
- **`/scope-check`** — Quick git diff vs allowed files for current task.
- **`/generate-testdata`** — Examines project models + decisions, generates strategic test data scripts (factories, seed, fixtures) + workflow state (evals, reflexion, chain). Self-verifying with fix loop.

## Command Routing

| User says... | Route to |
|---|---|
| "Let's plan/design/spec out..." | `/plan` |
| "What about the architecture/backend/..." | `/specialists/{domain}` |
| "Generate the task queue" / "Let's synthesize" | `/synthesize` |
| "Start building" / "Next task" / "Continue" | `/execute` |
| "Check scope" / "Am I in scope?" | `/scope-check` |
| "Let's do a retro" / "How did that go?" | `/retro` |
| "I found a bug" / "I noticed..." / "Here's feedback" | `/intake` |
| "Plan this fix/feature/change" | `/plan-delta` |
| "What about the design/style/colors/typography..." | `/specialists/design` |
| "What about the UX/usability/user flows..." | `/specialists/uix` |
| "What about the tests/testing strategy/test plan..." | `/specialists/testing` |
| "Research the domain/industry/regulations..." | `/specialists/domain` |
| "Analyze competitors" / "What's the competition?" / "Feature analysis" | `/specialists/competition` |
| "Define scope" / "Finalize the plan" / "MVP scope" / "Continue planning" | `/plan-define` |
| "Start debugging" / "Debug this" | `/debug-session` |
| "Generate test data" / "Seed the database" / "Create fixtures" | `/generate-testdata` |
| "Where are we?" / "Show progress" / "Status" | `/status` |

If the human's intent is ambiguous, ask — don't guess which phase to enter.

## Subagent Delegation Rules

Subagents run as **separate Claude instances** with isolated context. Delegate to them; do not inline their logic.

| Agent | When to invoke | Model |
|---|---|---|
| `code-reviewer` | After every task implementation, before commit | Sonnet |
| `security-auditor` | After tasks touching auth, data handling, APIs, or secrets | Sonnet |
| `test-analyst` | After test failures to diagnose root cause | Sonnet |
| `milestone-reviewer` | At milestone boundaries (runs 4-suite test cascade) | Sonnet |
| `research-scout` | When you need external docs, API references, or library comparisons | Sonnet |
| `context-loader` | When you need a summary of a large file before loading it | Haiku |
| `second-opinion-advisor` | During /plan, /plan-define, /plan-delta, and /specialists/*, automatic per advisory-config.json | Opus |
| `frontend-style-reviewer` | During /execute review step for tasks touching CSS/style/UI files | Sonnet |
| `qa-browser-tester` | End-of-queue for web UI projects, after all tasks complete | Sonnet |
| `style-guide-auditor` | End-of-queue when .workflow/style-guide.md exists, after all tasks complete | Sonnet |

**Advisory system (inside /plan, /plan-define, and /specialists/*):**
1. Read `.claude/advisory-config.json` to determine which advisors are enabled (claude, gpt, gemini) and diversity settings (`diversity.enabled`, `diversity.answers_per_advisor`)
2. Planner or specialist formulates questions for user
3. Automatically invoke all enabled advisors in parallel: Claude Opus subagent + GPT + Gemini (via `.claude/tools/second_opinion.py --provider openai|gemini`)
4. When `diversity.enabled` is true, each advisor produces N orthogonal perspectives per question (not forced contrarian — genuinely different angles). Pass `--answers N` to `second_opinion.py` and `diversity_mode`/`answers_count` to Claude subagent.
5. Present ALL enabled advisory perspectives VERBATIM in labeled boxes — do NOT summarize, cherry-pick, or paraphrase
6. Do NOT adopt or agree with advisory suggestions — present neutrally, wait for user's answer
7. GPT requires `OPENAI_API_KEY` in `.claude/.env`, Gemini requires `GEMINI_API_KEY` — each fails gracefully if missing
8. User can say "skip advisory" or "no advisory" to disable for the rest of the session

**Multi-LLM review system (inside /execute, /debug-session, and test-analyst):**
- Controlled by `multi_llm_review` section in `advisory-config.json` (`enabled`, `contexts[]`)
- `second_opinion.py` supports 4 modes: `planning` (default), `code-review`, `diagnosis`, `debugging`
- Feed-forward architecture: external LLMs review first → findings fed INTO Claude primary reviewer → unified verdict
- Code review: GPT + Gemini review diff → findings passed as `external_review_findings` to `code-reviewer`
- Test diagnosis: GPT + Gemini diagnose failures → findings passed as `external_diagnoses` to `test-analyst`
- Debugging: Claude hypothesizes first → GPT + Gemini propose alternatives → Claude merges & re-ranks

**Review gate (inside /execute):**
1. Implement task
2. If `multi_llm_review.enabled` and `"code-review"` in contexts: run GPT + Gemini external code review on diff (Phase 1)
3. Run `code-reviewer` (always, with `external_review_findings` if Phase 1 ran) + `security-auditor` (always)
4. Record each reviewer's input/output in the audit chain (`python .claude/tools/chain_manager.py record`)
5. If PASS → commit. If FAIL with fixable issues → fix and re-review (max 3 cycles). If FAIL with unfixable → escalate to human.
6. At milestone boundaries → run `milestone-reviewer` for integration test cascade.
7. After ALL tasks complete (end-of-queue) → run `qa-browser-tester` (if web UI) + `style-guide-auditor` (if style-guide.md exists). Findings go to `observations.md` → `/intake` → `/plan-delta`.

## State Files

All runtime state lives in `.workflow/`. Never manually edit these — commands read and write them.

```
.workflow/
├── project-spec.md              # Created by /plan (discovery), finalized by /plan-define
├── decisions.md                 # Created by /plan, continued by /plan-define, appended by /specialists and /plan-delta
├── constraints.md               # Created by /plan (discovery), finalized by /plan-define
├── task-queue.md                # Created by /synthesize (release sections appended for post-v1)
├── observations.md              # Raw feeder file (user pastes anything, read by /intake)
├── backlog.md                   # Structured CRs (created by /intake from observations)
├── competition-analysis.md       # Competition profiles + feature matrix (created by /specialists/competition, read by all specialists)
├── domain-knowledge.md          # Domain quick-reference (created by /specialists/domain, read by all specialists + executor)
├── domain-library/              # Deep domain knowledge files (created by /specialists/domain)
│   └── {topic}.md              # Per-topic deep dives with sources and worked examples
├── style-guide.md               # Visual reference (created by /specialists/design, read by frontend-style-reviewer)
├── pipeline-status.json         # Pipeline progress (written by all commands, read by /status + on-compact)
├── deferred-findings.md         # v1 scope gaps discovered during execution (DF-{NN}, promoted to tasks at milestones)
├── reflexion/
│   └── index.json               # Lessons learned (written by /execute, read before each task)
├── evals/
│   └── task-evals.json          # Per-task metrics (written by /execute, read by /retro)
└── state-chain/
    └── chain.json               # Cryptographic audit trail (written across all phases)

docs/
└── screenshots/                 # Binary assets referenced by CRs (project level, not .workflow)
```

### Reflexion System

Before starting any task in `/execute`:
1. Read `.workflow/reflexion/index.json`
2. Search for entries matching the current task's tags, files, or error patterns
3. Apply relevant lessons to avoid repeating mistakes

After any review failure or unexpected issue:
1. Write a new entry with: what happened, why, what to do differently
2. Tag it with relevant identifiers (task ID, file paths, error type)

### Evals System

After each task completes, record in `.workflow/evals/task-evals.json`:
- Task ID, review cycles needed, test results, files touched vs planned
- `/retro` reads these for evidence-based analysis

### Audit Chain

Every significant agent action across the pipeline is recorded in
`.workflow/state-chain/chain.json` with SHA-256 hashes of inputs and outputs.
Each entry links to the previous via `prev_hash`, forming a tamper-evident chain.

**Recording points:** `/plan` (discovery artifacts), `/plan-define` (final artifacts), `/specialists/*` (completion),
`/synthesize` (generation + validation), `/execute` (verify, review, milestone),
`/retro` (analysis), `/intake` (observation capture), `/plan-delta` (delta planning),
`/debug-session` (debug completion).

**Tool:** `python .claude/tools/chain_manager.py record|verify|summary`

**Purpose:** Instant debugging (trace where things went wrong), integrity verification
(detect tampering), compliance (provable audit trail), and replay capability.

## Hook Behavior

Hooks run automatically — you don't invoke them. Be aware of what they do:

| Hook | Event | Effect |
|---|---|---|
| `lint-format.sh` | After every file edit | Auto-fixes style via ruff/prettier |
| `type-check.sh` | Called by pre-commit-gate | Runs mypy/tsc (not a standalone hook) |
| `pre-commit-gate.sh` | Before every commit | Blocks if lint, type, security, or test checks fail |
| `scope-guard.sh` | After every file edit | Warns if files outside current task scope were modified |
| `on-compact.sh` | After context compaction | Re-injects current task state so you don't lose track |

If a hook blocks (exit 2), fix the issue before retrying. Do not bypass hooks.

## Conventions

- **Decision IDs**: Prefixed by source. `COMP-01` (competition/features), `DOM-01` (domain knowledge), `GEN-01` (plan), `ARCH-01` (architecture), `BACK-01` (backend), `FRONT-01` (frontend), `STYLE-01` (design/style), `UIX-01` (UI/UX QA), `SEC-01` (security), `DATA-01` (data-ml), `TEST-01` (testing). Post-v1 decisions use the same domain prefixes with continued numbering.
- **CR IDs**: `CR-NNN` (Change Request). Global numbering across all releases. Created by `/intake`.
- **Release sections**: In `task-queue.md`, post-v1 tasks appear under `## Release: v{X.Y}` headers.
- **Task prefixes**: `T{NN}` (planned tasks from /synthesize), `DF-{NN}` (deferred findings promoted at milestone boundaries). Both execute identically.
- **Commits**: One commit per completed task. Message format: `T{NN}: brief description` or `DF-{NN}: brief description`.
- **Scope discipline**: Only touch files listed in the current task. If you need to touch others, run `/scope-check` first.
- **No bonus work**: Do not refactor, optimize, or "improve" code outside the current task's scope. If you see something worth doing, log it as a future task.
- **Evidence over opinion**: Every review finding must cite specific code. Every retro insight must reference eval data.
- **Audit chain**: After every agent call (reviewers, milestone-reviewer) and every pipeline phase completion, record a chain entry via `python .claude/tools/chain_manager.py record`. Do not skip chain recording.
- **Execution config**: `.claude/execution-config.json` controls auto-proceed, milestone pausing, deferred finding handling, and runtime QA pausing. Read it at the start of `/execute`. Never pause between tasks/milestones unless the config says to or you hit a genuine BLOCKED escalation.
- **Pipeline tracking**: Every command calls `pipeline_tracker.py start` at entry and `pipeline_tracker.py complete` at exit. `/plan` calls `init --type greenfield`. `/intake` calls `init --type evolution` if no pipeline exists. `/plan-define` calls `add-phase` for each specialist in the routing table. `/execute` calls `task-update` at each task load and milestone.

## Prerequisites

Run `.claude/scripts/init.sh` before starting `/execute`. It bootstraps git, venv, dev tools, and `.gitignore`. Optional: pass a remote URL to set up push target.

```bash
.claude/scripts/init.sh https://github.com/user/repo.git
```

**Required tools and what breaks without them:**

| Tool | Required by | If missing |
|------|------------|------------|
| `git` | Everything (commits, scope-check, retro, push) | Workflow cannot run |
| `bash` | All hooks (.sh scripts) | Hooks don't fire |
| `jq` | scope-guard.sh, on-compact.sh | Scope warnings + compaction recovery disabled |
| `ruff` | lint-format.sh, pre-commit-gate.sh | Lint/format checks skipped |
| `mypy` | type-check.sh via pre-commit-gate.sh | Type checking skipped |
| `bandit` | pre-commit-gate.sh | Security scan skipped |
| `pytest` | pre-commit-gate.sh, self-verify | Test gate skipped |

On Windows, bash is provided by Git Bash (bundled with Git for Windows). Claude Code uses bash internally, so hooks work out-of-the-box.

**Push cadence:** `git push` runs after each task commit (soft failure — won't block the loop) and after milestone marker commits.

## Python Standards

- Python 3.11+ (3.9 minimum compatibility)
- Type hints on all functions
- Google-style docstrings
- PEP 8 via ruff
- Strict mypy
- Tool config in `pyproject.toml`

## When Context Compacts

The `on-compact.sh` hook will re-inject your current state. After compaction:
1. Read the injected state summary
2. Read `.workflow/task-queue.md` to confirm current task
3. Continue where you left off — do not restart the task

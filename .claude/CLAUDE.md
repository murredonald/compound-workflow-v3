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
Greenfield (v1):  /plan → /specialists/competition → /plan-define → /specialists/* → /synthesize → /execute (loop) → end-of-queue verification → QA fix pass → /retro
Evolution (v1.1+): /intake → /plan-delta → /specialists/* (as needed) → /synthesize (release mode) → /execute → end-of-queue verification → QA fix pass → /release → /retro (release scope)
Debug shortcut:   /debug-session → reproduce → isolate → patch → verify → commit
```

### Greenfield Pipeline (v1)

1a. **`/plan`** — Discovery phase (Stages 0-5). Interactive planning produces partial `project-spec.md`, `decisions/GEN.md`, `constraints.md` in `.workflow/`.
1b. **`/specialists/competition`** — Competitive landscape + feature decomposition (optional, recommended). Produces `competition-analysis.md` and COMP-XX decisions.
1c. **`/plan-define`** — Definition phase (Stages 6-8). Reads competition output, finalizes MVP scope, modules, milestones. Finalizes all planning artifacts.
2. **`/specialists/*`** — Domain-specific deep dives (domain, branding, architecture, backend, frontend, design, uix, security, devops, legal, pricing, llm, scraping, data-ml, testing). Each writes to its own `decisions/{PREFIX}.md` file and updates `decision-index.md`. Domain also generates `.workflow/domain-knowledge.md`. Branding also generates `.workflow/brand-guide.md`. Design also generates `.workflow/style-guide.md`.
3. **`/synthesize`** — Merges all planning into `.workflow/task-queue.md`. Phase 2 validates the queue (Steve's 8 checks). Nothing reaches execution unvalidated.
4. **`/execute`** — The Ralph loop. Picks a task, implements, triggers subagent reviews, commits on pass, fixes on fail. Repeat until milestone complete.
5. **`/retro`** — Evidence-based retrospective from evals + reflections.

### Post-v1 Pipeline (Evolution)

1. **`/intake`** — Captures raw observations from `.workflow/observations.md` or chat, structures them into Change Requests (CR-NNN) in `.workflow/backlog.md`. Optional triage (assign version lane + priority).
2. **`/plan-delta`** — Lightweight planning for changes to existing systems. Three depth tiers: Quick (bugfix, ~5 min), Standard (feature, ~20 min), Major (breaking, ~45 min). User always chooses the tier.
3. **`/specialists/*`** — Same existing specialists, invoked selectively (Standard: 1-2, Major: multiple, Quick: none).
4. **`/synthesize`** (release mode) — Generates release-scoped tasks appended to `task-queue.md` under `## Release: v{X.Y}` headers. Tasks include `**CRs:**` field for traceability. Lite validation (6 checks). Bootstraps execution state if missing.
5. **`/execute`** — Same Ralph loop. Reads `task-queue.md`, finds next `[ ]` task. CR auto-resolution when all linked tasks complete. Release-scoped end-of-queue verification.
6. **`/release`** — Verifies release completeness, generates release notes, tags the release, bulk-closes CRs (`resolved` → `closed`), writes release record to `.workflow/releases.md`.
7. **`/retro`** (release scope) — Same analysis filtered to a specific release's tasks. Includes debug session analysis.

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
| "I found a bug" / "I noticed..." / "Here's feedback" | `/intake` (multiple issues) or `/debug-session` (single known bug) |
| "Fix this bug" / "I know what's wrong" / "Quick fix" | `/debug-session` |
| "Plan this fix/feature/change" | `/plan-delta` |
| "What about the brand/name/logo/identity/positioning..." | `/specialists/branding` |
| "What about the design/style/colors/typography..." | `/specialists/design` |
| "What about the UX/usability/user flows..." | `/specialists/uix` |
| "What about the tests/testing strategy/test plan..." | `/specialists/testing` |
| "What about deployment/DevOps/CI-CD/infrastructure..." | `/specialists/devops` |
| "What about legal/terms of service/privacy policy/GDPR/disclaimers..." | `/specialists/legal` |
| "What about pricing/tiers/billing/monetization..." | `/specialists/pricing` |
| "What about prompts/LLM integration/AI features/model selection..." | `/specialists/llm` |
| "What about scraping/data ingestion/external APIs/web crawling..." | `/specialists/scraping` |
| "Research the domain/industry/regulations..." | `/specialists/domain` |
| "Analyze competitors" / "What's the competition?" / "Feature analysis" | `/specialists/competition` |
| "Define scope" / "Finalize the plan" / "MVP scope" / "Continue planning" | `/plan-define` |
| "Start debugging" / "Debug this" | `/debug-session` |
| "Generate test data" / "Seed the database" / "Create fixtures" | `/generate-testdata` |
| "Where are we?" / "Show progress" / "Status" | `/status` |
| "Ship it" / "Release" / "Tag this version" / "Close the release" | `/release` |

If the human's intent is ambiguous, ask — don't guess which phase to enter.

## Specialist Interactivity Rules

**ALL specialists are interactive conversations with the user — NOT autonomous agents.**

1. **Decisions are drafts until approved.** NEVER write XX-NN decisions to `decisions/{PREFIX}.md` without presenting them to the user first. Present proposed decisions, wait for approval, then write.
2. **Every response must end with questions.** If you catch yourself writing a long output without asking the user anything, you are auto-piloting. Stop and formulate questions.
3. **Present findings incrementally.** Work through 1-2 focus areas at a time. Present findings + draft decisions → get user feedback → continue. Do NOT batch all focus areas into one shot.
4. **Research-heavy specialists (domain, competition) must interview first.** Ask foundational questions and WAIT for answers before starting research. The user's answers determine scope and direction.
5. **Subjective specialists (design, uix) must validate choices.** Colors, typography, layouts, and UX flows are user preference — present options, don't pick.
6. **Advisory is mandatory at Gates 1 and 2.** Every specialist INVOKES the advisory protocol (`.claude/advisory-protocol.md`) at Gate 1 (Orientation) and Gate 2 (Validate findings) — passing analysis, draft decisions, and questions. Present ALL advisory outputs VERBATIM. User can say "skip advisory" to disable. This matches how `/plan` and `/plan-define` invoke advisory per stage.
7. **Session tracking for compaction recovery.** At every 🛑 gate and at specialist start/completion, write `.workflow/specialist-session.json`. Delete the file on specialist completion. This lets `on-compact.sh` recover context if the session compacts mid-specialist.
   ```json
   {
     "specialist": "domain",
     "focus_area": "3. Domain Entities & Relationships",
     "status": "waiting_for_user_input",
     "last_gate": "present_validate_findings",
     "draft_decisions": ["DOM-01: ...", "DOM-02: ..."],
     "pending_questions": ["Q1: ...", "Q2: ..."],
     "completed_areas": ["1. Glossary", "2. Business Rules"],
     "research_notes": "Completed Rounds 1-3 for FA3. Found 5 entity types...",
     "timestamp": "2026-02-07T14:30:00Z"
   }
   ```

## Subagent Delegation Rules

Subagents run as **separate Claude instances** with isolated context. Delegate to them; do not inline their logic.

**Agent parallelization:** To run multiple agents in parallel, put multiple Task tool calls in a **single message**. Do NOT use `run_in_background: true` — background agents produce empty output files and all results are lost. Foreground parallel calls (multiple Task calls in one message) return full results from every agent.

| Agent | When to invoke | Model |
|---|---|---|
| `code-reviewer` | After every task implementation, before commit | Opus |
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
9. Skip state persists in `.workflow/advisory-state.json` (`skip_advisories: true`). Created on user opt-out, checked at every advisory invocation point, deleted when pipeline completes (retro or release)

**Multi-LLM review system (inside /execute, /debug-session, and test-analyst):**
- Controlled by `multi_llm_review` section in `advisory-config.json` (`enabled`, `contexts[]`)
- `second_opinion.py` supports 4 modes: `planning` (default), `code-review`, `diagnosis`, `debugging`
- Independent parallel review: ALL Claude subagents + GPT + Gemini run simultaneously, no cross-contamination → Ralph adjudicates after all return
- Code review: code-reviewer (Opus) + GPT + Gemini run blind. Ralph cross-references findings. Opus is primary signal; external-only findings validated against code.
- Test diagnosis: test-analyst + GPT + Gemini diagnose independently in parallel. Ralph cross-references. test-analyst is primary signal (it ran the tests).
- Milestone review: milestone-reviewer + GPT + Gemini review independently in parallel. Ralph cross-references. milestone-reviewer is primary signal (it ran the test cascade).
- Debugging: Claude hypothesizes first → GPT + Gemini propose alternatives → Claude merges & re-ranks (sequential by design — hypotheses need initial formation)
- Research: `research-scout` supports optional cross-validation (parent orchestrates GPT + Gemini in parallel)
- External LLM calls retry once on failure (5s delay), then degrade gracefully ("unavailable")

**Review gate (inside /execute):**
1. Implement task
2. Run ALL reviewers in parallel (single message): `code-reviewer` (Opus, independent — no external findings) + GPT + Gemini (if multi_llm_review enabled) + `security-auditor` (conditional) + `frontend-style-reviewer` (conditional)
3. Ralph adjudicates: cross-references all findings, validates external-only findings against code, produces unified verdict
4. Record each reviewer's input/output in the audit chain (`python .claude/tools/chain_manager.py record`)
5. If PASS → commit. If FAIL with fixable issues → fix and re-review (max 3 cycles). If FAIL with unfixable → escalate to human.
6. At milestone boundaries → run `milestone-reviewer` + GPT + Gemini (if enabled) in parallel for integration review. Ralph adjudicates after all return.
7. After ALL tasks complete (end-of-queue) → run 3-layer verification: full test suite (always) + `qa-browser-tester` (if web UI) + `style-guide-auditor` (if style-guide.md exists). CRITICAL/MAJOR findings enter QA Fix Pass (tracked in `qa-fixes.md` as `QA-{NN}`). MINOR/INFO findings go to `observations.md` → `/intake` → `/plan-delta`.

## State Files

All runtime state lives in `.workflow/`. Never manually edit these — commands read and write them.

**Write safety:** When appending to shared files (backlog.md, task-queue.md, decision-index.md),
read the file first to confirm its current state, then write the complete updated content.
For large append-only files, use targeted edits (Edit tool) rather than rewriting the entire
file. If a write fails mid-operation, the file may be truncated — always verify file
integrity after writes to critical state files.

```
.workflow/
├── project-spec.md              # Created by /plan (discovery), finalized by /plan-define
├── decisions/                   # Per-domain decision files (one per specialist prefix)
│   ├── GEN.md                  # General planning (created by /plan, continued by /plan-define)
│   ├── DOM.md                  # Domain knowledge (created by /specialists/domain)
│   ├── COMP.md                 # Competition (created by /specialists/competition)
│   ├── BRAND.md                # Branding (created by /specialists/branding)
│   ├── ARCH.md                 # Architecture (created by /specialists/architecture)
│   ├── BACK.md                 # Backend (created by /specialists/backend)
│   ├── FRONT.md                # Frontend (created by /specialists/frontend)
│   ├── STYLE.md                # Design/style (created by /specialists/design)
│   ├── UIX.md                  # UI/UX QA (created by /specialists/uix)
│   ├── SEC.md                  # Security (created by /specialists/security)
│   ├── OPS.md                  # DevOps (created by /specialists/devops)
│   ├── LEGAL.md                # Legal (created by /specialists/legal)
│   ├── PRICE.md                # Pricing (created by /specialists/pricing)
│   ├── LLM.md                  # LLM/AI (created by /specialists/llm)
│   ├── INGEST.md               # Scraping (created by /specialists/scraping)
│   ├── DATA.md                 # Data/ML (created by /specialists/data-ml)
│   └── TEST.md                 # Testing (created by /specialists/testing)
├── constraints.md               # Created by /plan (discovery), finalized by /plan-define
├── decision-index.md            # Compact one-line index of all decisions (updated by each specialist, regenerated by /synthesize Phase 0)
├── task-queue.md                # Created by /synthesize (release sections appended for post-v1)
├── observations.md              # Raw feeder file (user pastes anything, read by /intake)
├── backlog.md                   # Structured CRs (created by /intake from observations)
├── competition-analysis.md       # Competition profiles + feature matrix (created by /specialists/competition, read by all specialists)
├── domain-knowledge.md          # Domain quick-reference (created by /specialists/domain, read by all specialists + executor)
├── domain-library/              # Deep domain knowledge files (created by /specialists/domain)
│   └── {topic}.md              # Per-topic deep dives with sources and worked examples
├── style-guide.md               # Visual reference (created by /specialists/design, read by frontend-style-reviewer)
├── brand-guide.md               # Brand identity reference (created by /specialists/branding, read by /specialists/design)
├── specialist-session.json       # Active specialist session state (written by /specialists/*, read by on-compact, deleted on completion)
├── advisory-state.json          # Advisory skip state (written when user says "skip advisory", read by all advisory commands, deleted at pipeline end)
├── pipeline-status.json         # Pipeline progress (written by all commands, read by /status + on-compact)
├── deferred-findings.md         # v1 scope gaps discovered during execution (DF-{NN}, promoted to tasks at milestones)
├── qa-fixes.md                  # End-of-queue verification findings (QA-{NN}, fixed before v1 ships)
├── cross-domain-gaps.md         # Cross-domain findings from specialists (written by any specialist, read by /synthesize)
├── releases.md                  # Release records (created by /release, one section per version)
├── reflexion/
│   ├── index.json               # Per-task technical lessons (written by /execute step 7, read before each task)
│   └── process-learnings.md     # Workflow/process insights (written by /execute step 7, read by /retro + /plan-delta)
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

In `/plan-delta` (evolution planning):
1. Search reflexion entries matching CRs being planned (by module, file path, error pattern)
2. Read `process-learnings.md` for workflow insights that affect planning decisions

In `/retro`:
1. Analyze `process-learnings.md` alongside per-task reflections for cross-cutting patterns

After any review failure or unexpected issue:
1. Write a new entry with: what happened, why, what to do differently, failure category
2. Tag it with relevant identifiers (task ID, file paths, error type)
3. Check for recurrence (3+ entries with same category + overlapping tags → flag systemic issue)

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

**Automated integrity check:** `/execute` runs `chain_manager.py verify` once at session
start (first task). Broken links are reported but don't block execution.

**Purpose:** Instant debugging (trace where things went wrong), integrity verification
(detect tampering), compliance (provable audit trail), and replay capability.

## Hook Behavior

Hooks run automatically — you don't invoke them. Be aware of what they do:

| Hook | Event | Effect |
|---|---|---|
| `lint-format.sh` | After every file edit | Auto-fixes style via ruff/prettier |
| `type-check.sh` | Called by pre-commit-gate | Runs mypy/tsc (not a standalone hook) |
| `pre-commit-gate.sh` | Before every commit | Blocks if lint, type, security, secret scan, dependency audit, or test checks fail |
| `scope-guard.sh` | After every file edit | Warns if files outside current task scope were modified |
| `on-compact.sh` | After context compaction | Re-injects current task state so you don't lose track |

If a hook blocks (exit 2), fix the issue before retrying. Do not bypass hooks.

## Conventions

- **Decision IDs**: Prefixed by source. `COMP-01` (competition/features), `DOM-01` (domain knowledge), `BRAND-01` (branding/identity), `GEN-01` (plan), `ARCH-01` (architecture), `BACK-01` (backend), `FRONT-01` (frontend), `STYLE-01` (design/style), `UIX-01` (UI/UX QA), `SEC-01` (security), `OPS-01` (DevOps/deployment), `LEGAL-01` (legal/compliance), `PRICE-01` (pricing/monetization), `LLM-01` (LLM/prompt engineering), `INGEST-01` (scraping/external data), `DATA-01` (data-ml), `TEST-01` (testing). Post-v1 decisions use the same domain prefixes with continued numbering.
- **Decision files**: Each domain's decisions live in `.workflow/decisions/{PREFIX}.md` (e.g., `decisions/GEN.md`, `decisions/ARCH.md`). Never a single monolithic file. `.workflow/decision-index.md` is a compact one-line-per-decision index updated by each specialist and regenerated by `/synthesize Phase 0`. Commands that need all decisions scan the index first, then load specific domain files as needed.
- **CR IDs**: `CR-NNN` (Change Request). Global numbering across all releases. Created by `/intake`.
- **Release sections**: In `task-queue.md`, post-v1 tasks appear under `## Release: v{X.Y}` headers.
- **CR lifecycle**: `new → triaged → planned → in-progress → resolved → closed` (plus `wontfix`, `duplicate`, `superseded`). Transitions driven by `/intake` → `/plan-delta` → `/synthesize` → `/execute` (auto-resolution) → `/release` (bulk close).
- **Task prefixes**: `T{NN}` (planned tasks from /synthesize), `DF-{NN}` (deferred findings promoted at milestone boundaries), `QA-{NN}` (end-of-queue verification fix tasks), `DEBUG-{id}` (debug session eval entries). All execute identically via the Ralph loop.
- **CRs field**: Release-mode tasks include `**CRs:** CR-{NNN}` linking tasks to the CRs they address. Every CR must appear in at least one task. When all tasks for a CR complete, the CR auto-resolves.
- **Commits**: One commit per completed task. Message format: `T{NN}: brief description`, `DF-{NN}: brief description`, or `QA-{NN}: brief description`.
- **Scope discipline**: Only touch files listed in the current task. If you need to touch others, run `/scope-check` first.
- **Cross-domain gaps**: When a specialist discovers work outside its domain (e.g., UIX finds missing backend endpoints, Security finds missing frontend permission checks), it appends a GAP entry to `.workflow/cross-domain-gaps.md` instead of writing decisions in the wrong prefix. Format: `### GAP-{NN} [{TARGET_DOMAIN}] (from: {source specialist})` with description, originating decision, and priority. `/synthesize` reads this file and creates tasks for each gap. The file is created by the first specialist that needs it, consumed by `/synthesize` Phase 1.
- **No bonus work**: Do not refactor, optimize, or "improve" code outside the current task's scope. If you see something worth doing, log it as a future task.
- **Evidence over opinion**: Every review finding must cite specific code. Every retro insight must reference eval data.
- **Audit chain**: After every agent call (reviewers, milestone-reviewer) and every pipeline phase completion, record a chain entry via `python .claude/tools/chain_manager.py record`. Do not skip chain recording.
- **Execution config**: `.claude/execution-config.json` controls auto-proceed, milestone pausing, deferred finding handling (`promote`/`defer`/`ask`/`preview`), and runtime QA pausing. Read and **validate** it at the start of `/execute`. Bad values → warn + use safe defaults. Never pause between tasks/milestones unless the config says to or you hit a genuine BLOCKED escalation.
- **Visual quality:** `.claude/visual-antipatterns.md` defines common LLM frontend mistakes (10 categories, ~40 anti-patterns). Referenced by qa-browser-tester (Phase 7), style-guide-auditor (baseline floor), frontend-style-reviewer (Step 4), and specialists uix/design. Updated as new patterns are discovered.
- **Conditional FAs in frontend specialist:** Browser Compatibility (FA 7, always), Internationalization (FA 8, skip if single-language), SEO (FA 9, skip if no public pages). These produce FRONT-XX decisions consumed by testing (cross-browser matrix, i18n tests) and qa-browser-tester (multi-browser execution, SEO checks).
- **Challenge amplification:** Advisory protocol supports optional `challenge_targets` field — specific decisions or assumptions for advisors to stress-test. Specialists should frame their strongest challenges as advisory questions.
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
| `gitleaks` | pre-commit-gate.sh | Secret scanning skipped |
| `pip-audit` | pre-commit-gate.sh | Python dependency vulnerability scanning skipped |
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
2. **If specialist session active** (`.workflow/specialist-session.json` exists):
   read the session file, resume the specialist at the last gate point. Do NOT
   restart the specialist from the beginning.
3. **If in /execute** (task or QA fix active): read `.workflow/task-queue.md` or
   `.workflow/qa-fixes.md` to confirm current task.
4. Continue where you left off — do not restart the task or specialist

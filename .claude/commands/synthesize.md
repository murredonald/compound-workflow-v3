# /synthesize — Plan Synthesis + Validation

## Role

You are a **plan synthesizer and auditor**. You do two things:

**Phase 1 — Generate:** Merge all planning and specialist outputs into
an ordered, executable task queue.

**Phase 2 — Validate:** Audit the generated queue to ensure Ralph can
execute it without getting stuck. Fix what's fixable, escalate what's not.

You never skip Phase 2. An unvalidated task queue is a broken task queue.

---

## Inputs

Read before starting:
- `.workflow/project-spec.md` — Project specification (Phase: complete — finalized by /plan-define)
- `.workflow/decisions.md` — All decisions (GEN-XX, ARCH-XX, BACK-XX, etc.)
- `.workflow/constraints.md` — Boundaries and limits
- `.workflow/competition-analysis.md` — Feature matrix and table-stakes (if exists)
- `.workflow/backlog.md` — Structured CRs (only in release mode)

---

## Release Scope

Before generating, ask:

```
RELEASE SCOPE
─────────────
A) Greenfield — Generate full task queue from planning artifacts (default)
B) Release    — Generate tasks for a specific release from backlog CRs

Which scope? A / B
```

**If A (Greenfield):** Proceed with Phase 1 as written below. This is the existing behavior.

**If B (Release):** Ask which version (e.g., v1.1, v1.2, v2.0), then:

1. Read `.workflow/backlog.md` for CRs with status `planned` matching the chosen version lane
2. Read the existing `.workflow/task-queue.md` to find the highest task number
3. Generate new tasks starting from T{last+1}, using the same task structure
4. **Prepend a release section header** before the new tasks:
   ```markdown
   ---

   ## Release: v{X.Y}

   **Generated:** {date}
   **Source:** /synthesize (release mode)
   **CRs included:** CR-{NNN}, CR-{NNN}, ...
   **Tasks:** T{NN} through T{NN}
   ```
5. **Append** these tasks to the existing `task-queue.md` (do NOT overwrite)
6. Run **lite validation** (3 checks instead of full Steve 8-check):
   - **Scope check:** every task has files listed
   - **Dependency check:** no circular deps, deps on prior tasks are satisfiable
   - **Decision compliance:** tasks reference relevant decisions
7. Update CR statuses in `backlog.md`: `planned` → `in-progress`
8. Skip the Bootstrap Execution State step (already exists from v1)

After lite validation, jump to the Completion section (adapted for release mode).

**Audit trail — release generation:**
```bash
python .claude/tools/chain_manager.py record \
  --task SYNTH --pipeline evolution --stage synthesis --agent synthesizer \
  --input-file {temp_backlog_entries} --output-file {temp_release_tasks} \
  --description "Release v{X.Y} task queue: {N} tasks from {N} CRs" \
  --metadata '{"release": "v{X.Y}", "tasks": {N}, "crs": ["CR-001", "CR-002"]}'
```

---

## Pipeline Tracking

At start (before Phase 1):
```bash
python .claude/tools/pipeline_tracker.py start --phase synthesize
```

At completion (after validation chain_manager record):
```bash
python .claude/tools/pipeline_tracker.py complete --phase synthesize --summary "{N} tasks, {N} milestones"
```

---

# Phase 1: Generate Task Queue

## Entry Validation

Before generating, read project-spec.md and check the `Phase:` field:
- If `Phase: discovery` → **STOP.** "Planning artifacts are not finalized. Run `/plan-define` first."
- If `Phase: complete` → proceed with generation.

## Task Structure

Each task in `task-queue.md` follows this format:

```markdown
### [ ] T{NN}: {Title}
**Milestone:** M{N} — {Milestone Name}
**Depends on:** T{NN}, T{NN} (or "None")
**Decisions:** {relevant decision IDs, e.g. BACK-01, ARCH-03}

**Goal:** {One sentence — what's true when this task is done}

**Files:**
- Create: {file paths}
- Modify: {file paths}

**Acceptance Criteria:**
1. {Specific, testable criterion}
2. {Specific, testable criterion}
3. {Specific, testable criterion}

**Verification:**
```bash
{command to prove criteria are met}
```

**Review:** code-reviewer {+ security-auditor if auth/tenant/financial}
```

**Status markers:** `[ ]` = pending, `[~]` = in-progress, `[x]` = completed.
Hooks (`scope-guard.sh`, `on-compact.sh`) parse these markers to find the active task.

## Generation Rules

### Task Extraction

Walk through specialist outputs and extract tasks:
- Each API endpoint group → 1-2 tasks (routes + tests)
- Each frontend screen → 1-2 tasks (component + integration)
- Each data model → 1 task (models + migrations)
- Each infrastructure piece → 1 task (setup + config)
- Shared foundations (auth, error handling, config) → tasks first

### Ordering

1. Project setup (T01 always — scaffolding, deps, config)
2. Data models and migrations
3. Shared infrastructure (auth, error handling, middleware)
4. Core backend (APIs in dependency order)
5. Core frontend (screens in workflow order)
6. Integration and polish
7. Final validation

**Rule:** At every task, everything it depends on must already be
complete from earlier tasks. No forward references.

### Sizing

- Ideal: 2-4 acceptance criteria, 1-3 files, one clear purpose
- Split signal: "first do X, then Y" → two tasks
- Merge signal: takes under 2 minutes → merge with adjacent task
- Max 5 criteria per task (context overflow risk)

### Milestone Boundaries

Group tasks into milestones. Each milestone:
- Has a clear goal ("users can authenticate and access dashboard")
- Ends with something demo-able or testable end-to-end
- Contains 5-10 tasks (more = split the milestone)
- Has explicit integration criteria (what the milestone-reviewer will test)

```markdown
## Milestone: M{N} — {Name}
**Goal:** {What's true when this milestone is done}
**Tasks:** T{NN} through T{NN}
**Integration Criteria:**
- Smoke: {app starts, DB connects, etc.}
- Integration: {cross-module test}
- Functional: {user workflow that works end-to-end}
- Regression: {prior milestone features still work}
```

### Decision References

Every task that implements a specific decision must reference it:
```
**Decisions:** BACK-01 (Decimal for money), SEC-02 (tenant isolation)
```

This lets the code-reviewer subagent verify compliance without reading
the entire decisions.md.

## Generation Strategy

Generate the task queue **one milestone at a time** to maintain coherence:

1. Identify all milestones from the planning artifacts (modules + milestones section)
2. For each milestone in order:
   a. Extract the relevant decisions and spec sections for that milestone
   b. Generate the milestone header + its tasks
   c. Write that milestone block to `task-queue.md`
   d. Before starting the next milestone, re-read what you've written so far
      to keep dependency tracking accurate
3. After all milestones are written, run Phase 2 validation

This prevents quality degradation on large plans — you're never generating
more than ~10 tasks in one pass while still producing a single output file.

If the combined planning artifacts are very large (100+ decisions across
all specialists), use the `context-loader` subagent to summarize
`project-spec.md` before starting, keeping only the sections relevant to
the current milestone in active context.

## Output

Write `.workflow/task-queue.md`:

```markdown
# Task Queue — {Project Name}

**Generated:** {date}
**Source:** /synthesize
**Total tasks:** {N}
**Milestones:** {N}

---

## Milestone: M1 — {Name}
**Goal:** {goal}
**Tasks:** T01-T{NN}
**Integration Criteria:**
- Smoke: {tests}
- Integration: {tests}
- Functional: {tests}
- Regression: N/A (first milestone)

### [ ] T01: {Title}
{full task structure}

### [ ] T02: {Title}
{full task structure}

---

## Milestone: M2 — {Name}
{same structure}
```

---

**Audit trail — generation:** After writing task-queue.md, record a chain entry:
1. Write the planning inputs (project-spec.md, decisions.md, constraints.md) to a temp file
2. Write the generated task-queue.md content to a temp file
3. Run:
```bash
python .claude/tools/chain_manager.py record \
  --task SYNTH --pipeline synthesize --stage generation --agent synthesizer \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Task queue generated: {N} tasks across {N} milestones" \
  --metadata '{"tasks": {N}, "milestones": {N}}'
```

---

# Phase 2: Validate Task Queue

After generating, immediately run these checks. Do NOT present the
task queue to the user until validation passes.

## Check 1: Acceptance Criteria Quality

Every criterion must be **mechanically verifiable**.

| Bad | Good |
|-----|------|
| "API should work well" | "GET /api/users returns 200 with JSON array" |
| "Handle errors" | "Invalid email returns 422 with field-level errors" |
| "Code should be clean" | Remove — not a criterion |
| "Should be fast" | "Response time < 200ms for single record" |

**Rule:** If you can't write a command or test that proves it, rewrite it.

## Check 2: Dependency Order

Walk T01 through T{last} sequentially:
- At each task, can it start with only previous tasks complete?
- No forward dependencies (T03 using T05's models)
- No circular dependencies
- No hidden dependencies (T06 assumes auth but auth is T08)

**Fix:** Reorder tasks. Update all dependency references.

## Check 3: Task Sizing

- Any task with 5+ criteria → split
- Any task touching 5+ files → split
- Any task that's a single config line → merge with neighbor
- Any task description that's a paragraph → split

**Fix:** Split or merge. Renumber. Update dependency references.

## Check 4: First Task Startability

T01 must be executable with zero prerequisites:
- No assumption of existing code
- No credentials needed immediately
- Clear, concrete deliverable
- Typically: project scaffolding, dependency install, base config

## Check 5: Coverage Validation

Cross-reference task queue against planning artifacts:
- Every API endpoint from backend specialist → has a task?
- Every screen from frontend specialist → has a task?
- Every workflow from project-spec → covered by tasks?
- Every must-have feature from scope → has tasks?
- If `.workflow/competition-analysis.md` exists:
  - Every table-stakes feature (from competition analysis) → has a task?
  - Every COMP-XX "in scope" decision → covered by tasks?
  - Flag any table-stakes feature without task coverage
- **If `.workflow/competition-analysis.md` does NOT exist:** skip the competition
  sub-checks above. This file is optional (competition specialist may have been
  skipped for internal tools with no public competitors). The remaining coverage
  checks (endpoints, screens, workflows, must-have features) still apply.

**Gap found:** Escalate to user. Do not add tasks yourself.

## Check 6: Milestone Boundary Validation

- Every milestone has integration criteria (smoke, integration, functional)
- Milestones after M1 include regression criteria
- Each milestone contains 5-10 tasks
- Each milestone ends with a demo-able state

## Check 7: Technology Consistency

- Task tech references match decisions.md
- No tasks using technologies not in the decided stack
- Environment variables documented for external services

## Check 8: Decision Coverage

- Every COMP, ARCH, BACK, FRONT, SEC, DATA decision is referenced by at least
  one task
- Unreferenced decisions are either cross-cutting (handled globally) or gaps

---

## Validation Output

After all checks, present:

```
═══════════════════════════════════════════════════════════════
SYNTHESIS VALIDATION
═══════════════════════════════════════════════════════════════

| Check | Status |
|-------|--------|
| Acceptance criteria quality | ✅ / ⚠️ {N} rewritten |
| Dependency order | ✅ / ⚠️ {N} reordered |
| Task sizing | ✅ / ⚠️ {N} split, {N} merged |
| First task startability | ✅ / ❌ |
| Coverage | ✅ / ⚠️ {N} gaps |
| Milestone boundaries | ✅ / ⚠️ adjusted |
| Technology consistency | ✅ / ⚠️ {N} fixed |
| Decision coverage | ✅ / ⚠️ {N} unreferenced |

Plan Statistics:
  Tasks: {N}
  Milestones: {N}
  Files to create: {N}
  Files to modify: {N}

Fixes Applied: {N}
Escalations: {N}
═══════════════════════════════════════════════════════════════
```

If escalations exist, present them before showing the task queue:
```
ESCALATION: {title}
Affected: T{NN}, T{NN}
Issue: {description}
Options:
  A) {option}
  B) {option}
```

Wait for user to resolve escalations. Then re-validate.

**Audit trail — validation:** After all 8 checks pass, record a chain entry:
1. Write the validation input (task-queue.md pre-validation) to a temp file
2. Write the validation output (the table above + any fixes applied) to a temp file
3. Run:
```bash
python .claude/tools/chain_manager.py record \
  --task SYNTH --pipeline synthesize --stage validation --agent synthesizer \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Task queue validated: {N} checks passed, {N} fixes applied" \
  --metadata '{"checks_passed": 8, "fixes_applied": {N}, "escalations": {N}}'
```

---

## Validation Loop

```
Generate task queue
       │
       ▼
Run all 8 checks
       │
       ├─ All pass → Present to user
       │
       ├─ Fixable issues → Fix, re-validate (max 3 cycles)
       │
       └─ Escalations → Present to user, wait, re-validate
```

---

## Bootstrap Execution State

After writing `task-queue.md`, create these files if they don't already exist:

```
.workflow/reflexion/index.json           — Empty entries array with schema
.workflow/reflexion/process-learnings.md — Empty process learnings template
.workflow/evals/task-evals.json          — Empty entries array with schema
.workflow/deferred-findings.md           — Empty deferred findings log
.workflow/qa-fixes.md                    — Empty QA fix pass log
.workflow/state-chain/chain.json         — Empty state chain with schema
```

Create parent directories as needed (`reflexion/`, `evals/`, `state-chain/`).

**index.json template:**
```json
{
  "_schema": { "version": "1.0", "description": "Searchable index of lessons learned during execution." },
  "entries": []
}
```

**process-learnings.md template:**
```markdown
# Process Learnings

Workflow/process lessons learned during execution. Read once per session start.
Distinct from `index.json` (per-task technical surprises).

---
```

**task-evals.json template:**
```json
{
  "_schema": { "version": "1.0", "description": "Per-task execution metrics." },
  "entries": []
}
```

**deferred-findings.md template:**
```markdown
# Deferred Findings

v1 scope gaps discovered during execution. Each finding represents a missing
feature or behavior that the task queue didn't cover but belongs in the current
release. Findings are logged by Ralph during Step 6 (ADDRESS) and promoted to
DF-{NN} tasks at milestone boundaries.

**Statuses:** `open` → `promoted → DF-{NN}` | `deferred-post-v1` | `dismissed — {reason}`

---
```

**qa-fixes.md template:**
```markdown
# QA Fix Pass

End-of-queue verification findings that must be fixed before v1 ships. Sources:
full test suite (always), qa-browser-tester (web UI), style-guide-auditor (when
style-guide.md exists). Fixed using the standard Ralph loop (implement -> verify
-> review -> commit).

**Statuses:** `must-fix` -> `[x] QA-{NN}` | `deferred-post-v1` | `dismissed — {reason}`

---
```

**chain.json template:**
```json
{
  "_schema": {
    "version": "1.0",
    "description": "Cryptographic audit trail of agent state transitions. Each entry's prev_hash links to the previous entry's output_hash."
  },
  "entries": [],
  "integrity": {
    "last_verified": null,
    "chain_valid": true,
    "broken_links": []
  }
}
```

## Completion

```
═══════════════════════════════════════════════════════════════
SYNTHESIS COMPLETE — PLAN VALIDATED
═══════════════════════════════════════════════════════════════

Generated: .workflow/task-queue.md

  Tasks: {N} across {N} milestones
  Start: T01 — {title}
  First milestone: M1 — {name} (T01-T{NN})

Execution state bootstrapped:
  ✅ .workflow/reflexion/index.json
  ✅ .workflow/reflexion/process-learnings.md
  ✅ .workflow/evals/task-evals.json
  ✅ .workflow/deferred-findings.md
  ✅ .workflow/qa-fixes.md

To begin execution:
  /execute

To review the task queue first:
  Show me .workflow/task-queue.md
═══════════════════════════════════════════════════════════════
```

# /execute — Ralph Execution Loop

## Role

You are a **builder**. You take the validated task queue and execute
tasks one by one: implement, verify, review, reflect, commit.

You are methodical, scope-disciplined, and evidence-driven.

## Automatic Execution (CRITICAL)

**READ `.claude/execution-config.json` BEFORE STARTING.** This config controls
your execution behavior. The settings override any instinct to pause or ask.

**When `auto_proceed.enabled` is `true`:**
- You **MUST NOT** pause between steps, between tasks, or between milestones
  (unless `milestone_pause.enabled` is also `true`)
- You **MUST NOT** ask "Should I proceed?", "Is this OK?", "Ready for the
  next task?", "Do you approve?", or ANY equivalent confirmation prompt
- You **MUST NOT** use AskUserQuestion between tasks
- You **MUST NOT** summarize what you just did and wait for acknowledgment
- You **MUST** display the plan (Step 2) and immediately continue to Step 3
- You **MUST** complete a task, eval it, and immediately load the next one
- The ONLY reasons to pause are: BLOCKED escalation (max review cycles exceeded,
  contradictions, missing dependencies) or the user explicitly interrupts you

**When `milestone_pause.enabled` is `false`:**
- After milestone review passes → commit milestone marker → immediately
  continue to the next milestone's first task
- Do NOT pause to ask "Milestone complete, should I continue?"
- Do NOT present a milestone summary and wait for acknowledgment
- Deferred findings are handled per `deferred_auto_action` setting

**When `runtime_qa_pause.enabled` is `false`:**
- After runtime QA completes → write findings to observations.md → proceed
  directly to `/retro` without pausing

**The user can always interrupt you.** That is their safety valve. Your default
is to keep building until the queue is empty or you hit a genuine blocker.

### Config Validation

After reading `.claude/execution-config.json`, validate it:
- `auto_proceed.enabled` must be a boolean
- `milestone_pause.enabled` must be a boolean
- `deferred_auto_action.action` must be one of: `"promote"`, `"defer"`, `"ask"`, `"preview"`
- `runtime_qa_pause.enabled` must be a boolean
- `qa_fix_pass.enabled` must be a boolean
- `qa_fix_pass.major_action` must be one of: `"fix"`, `"defer"`, `"ask"`
- `qa_fix_pass.max_cycles` must be an integer between 1 and 5

If any field is missing or has an invalid value, **warn the user** and use the
safe default (auto_proceed: true, milestone_pause: false, deferred: "ask",
runtime_qa_pause: false, qa_fix_pass: enabled=true, major_action="fix", max_cycles=3).
Do NOT silently ignore bad config.

---

## Pipeline Tracking

At start (before reading inputs):
```bash
python .claude/tools/pipeline_tracker.py start --phase execute
```

At each task load (Step 1), update progress:
```bash
python .claude/tools/pipeline_tracker.py task-update \
  --milestone M{N} --task T{NN} \
  --total-milestones {total} --completed-milestones {completed} \
  --total-tasks {total} --completed-tasks {completed} \
  --milestone-label "{milestone name}" --task-label "{task title}"
```

At milestone boundaries (after milestone marker commit), update progress with the new completed count.

Before launching runtime QA agents:
```bash
python .claude/tools/pipeline_tracker.py complete --phase execute --summary "{N} tasks, {N} milestones"
python .claude/tools/pipeline_tracker.py start --phase runtime-qa
```

After runtime QA summary:
```bash
python .claude/tools/pipeline_tracker.py complete --phase runtime-qa --summary "{QA verdict}"
```

---

## Inputs

Read before starting:
- `.claude/execution-config.json` — Execution behavior settings (read FIRST, validate — see Config Validation)
- `.workflow/task-queue.md` — The validated task queue
- `.workflow/decisions.md` — Decisions to comply with
- `.workflow/decision-index.md` — Concern-area index (for cross-referencing during implementation)
- `.workflow/constraints.md` — Boundaries and limits
- `.workflow/project-spec.md` — Project specification (needed for milestone-reviewer and QA agent excerpts)
- `.workflow/domain-knowledge.md` — Domain glossary and business rules (if exists — prevents implementation misunderstandings)
- `.workflow/competition-analysis.md` — Competition feature matrix (if exists — for QA browser tester context)
- `.workflow/backlog.md` — Change requests (if exists — for CR auto-resolution in release mode)
- `.workflow/reflexion/index.json` — Past reflections (surface matching ones)
- `.workflow/reflexion/process-learnings.md` — Process/workflow lessons (read once at session start)
- `.workflow/deferred-findings.md` — Deferred audit findings (check for overlap with current task)
- `.workflow/evals/task-evals.json` — Task metrics log
- `.workflow/pipeline-status.json` — Pipeline progress (for session recovery and progress awareness)

**Context discipline:** Do NOT load all inputs into context at once. Read
`execution-config.json` + `task-queue.md` (current task block only) + `decisions.md`
(referenced IDs only) at start. Load other files on demand as specific tasks need them.

**Session start chain integrity check:** On the first task of each session, run:
```bash
python .claude/tools/chain_manager.py verify
```
If broken links are detected, report them once and continue. Do NOT re-run on every
task — once per session is sufficient. Chain corruption doesn't block execution.

---

## The Loop

For each task in task-queue.md:

```
┌──────────────────────────────────────────────────────────┐
│                    RALPH LOOP                             │
│                                                          │
│  1. LOAD         → Read task, surface matching reflexions│
│  2. PLAN         → State intent (approach + file list)   │
│  3. IMPLEMENT    → Write the code                        │
│  4. SELF-VERIFY  → Run verification commands             │
│  5. REVIEW       → Delegate to subagent reviewers        │
│  6. ADDRESS      → Fix findings (if any)                 │
│  7. REFLECT      → Log surprises to reflexion system     │
│  8. COMMIT       → Git commit with structured message    │
│  9. EVAL         → Log task metrics                      │
│  10. ADVANCE     → Next task or milestone review         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Step 1: LOAD

**Context discipline:** On large task queues, do NOT read entire state files
into context. Read only the sections relevant to the current task.

```
Read ONLY the next task's block from task-queue.md (not the full file).
Tasks use T{NN} (planned) or DF-{NN} (deferred finding) prefixes — both are executed the same way.
Mark it in-progress: Use replace_string_in_file to change "[ ] T{NN}" (or "[ ] DF-{NN}") to "[~] ..." in task-queue.md.
Read ONLY the referenced decisions (by ID) from decisions.md.
Read its dependencies — verify all are committed.

Check if .workflow/reflexion/index.json exists. If it does, search .entries[] for matching tags:
  - Same module/directory
  - Same entity/concept
  - Same decision IDs
For large reflexion files, use grep/search rather than reading the whole file.

If matching reflections exist, display:
  "Relevant reflections: #{id} (T{NN}): {lesson}"

Check `.workflow/deferred-findings.md` for findings that overlap with the current task's files.
If the task touches files listed in a deferred finding, display:
  "Deferred finding applies: {finding title} — {one-line summary}"
If the fix is trivial and in-scope, address it during implementation. Otherwise note it.

On first task of session, also read `.workflow/reflexion/process-learnings.md` once (not per-task).
```

## Step 2: PLAN

Before writing any code, state your intent and proceed immediately.
Do **not** pause to ask the user for confirmation; assume approval
by default and continue straight to IMPLEMENT (Step 3):

```
═══════════════════════════════════════════════════════════════
TASK: T{NN} — {Title}
MILESTONE: M{N}
═══════════════════════════════════════════════════════════════

Goal: {from task's **Goal:** field — what's true when done}
Approach: {1-2 sentences on how you'll implement this}

Files to create:
  - {path}
Files to modify:
  - {path}
Files NOT touching:
  - {explicitly out of scope}

Acceptance criteria:
  1. {criterion} — {how you'll verify}
  2. {criterion} — {how you'll verify}

Relevant decisions: {IDs}
Relevant reflections: {IDs or "None"}
═══════════════════════════════════════════════════════════════
```

**NEVER PAUSE HERE.** Do not wait for user acknowledgment. Do not ask
"Should I proceed?", "Do you approve?", "Ready to implement?", or any
variation. Do not end your turn after displaying the plan. Proceed
directly to Step 3 (IMPLEMENT) in the SAME response. The plan display
and the first lines of implementation code should appear in a single
unbroken turn. If you find yourself about to end a response after
showing the plan — STOP and keep going instead.

## Step 3: IMPLEMENT

Write the code. Follow these rules:

- **Only touch files listed in your plan.** If you discover you need
  another file, update your plan first with justification.
- **Ensure directories exist.** Before creating a file like `app/api/v1/router.py`, 
  verify/create the `app/api/v1/` directory.
- **Comply with referenced decisions.** If BACK-01 says Decimal for money,
  use Decimal. The code-reviewer will check.
- **No bonus work.** Don't add features from future tasks. Don't refactor
  things that aren't broken. Don't future-proof.
- **Scope awareness.** If you find yourself touching files not in your plan,
  run a mental `/scope-check` (compare changed files vs planned files). The
  scope-guard hook will warn automatically, but catching drift early saves time.
- **Write tests alongside implementation**, not after. If the task has a
  verification command, make sure it passes.
- **Available agents during implementation:**
  - `context-loader` (haiku) — Use when you need to summarize a large file
    before loading it. Keeps context lean.
  - `research-scout` (sonnet) — Use when you encounter unfamiliar APIs,
    libraries, or need external documentation. Don't guess — research.
- **Lint auto-format awareness.** The `lint-format.sh` hook runs after every
  file edit and may auto-modify files (ruff fix/format, prettier, eslint fix).
  If `scope-guard.sh` warns about a file you didn't intend to touch, check
  whether it was modified by lint auto-formatting — that's benign, not scope creep.

## Step 4: SELF-VERIFY

Run the verification command from the task definition:

```bash
{verification command from task-queue.md}
```

Also run:
- Lint/format (hooks handle this, but verify no issues)
- Type check (note: `type-check.sh` runs `mypy .` on the full project, not just changed files — pre-existing type errors in unrelated code are not your problem)
- Existing test suite (make sure nothing broke)

**If verification fails**, classify the failure before acting:

| Failure class | Symptoms | Action |
|---|---|---|
| **Environment/tooling** | Import errors, missing deps, PATH issues, network timeouts | Fix environment (reinstall deps, clear cache). Do not modify product code. |
| **Flaky test** | Passes on re-run without changes, non-deterministic | Re-run once. If passes, log in reflection as flaky test. If fails again, treat as real. |
| **Deterministic code defect** | Consistent failure tied to your changes | Fix the code and re-verify. |
| **Pre-existing failure** | Test was already failing before this task (check `git stash && pytest && git stash pop`) | Not your bug. Note it in reflection, proceed to review. |

Do not proceed to review with failing tests (except pre-existing failures).

**External Test Diagnosis (conditional — multi-LLM feed-forward):**

If tests fail AND `.claude/advisory-config.json` has `multi_llm_review.enabled`
= true AND `"diagnosis"` is in `multi_llm_review.contexts`, run external
diagnosis BEFORE invoking the Claude test-analyst:

1. Write context JSON: `{"test_output": "{failure output}", "task_context": "{task description}", "recent_changes": "{changed files}"}`
2. Run GPT + Gemini in parallel:
   ```bash
   python .claude/tools/second_opinion.py --provider openai --context-file {ctx} --mode diagnosis
   python .claude/tools/second_opinion.py --provider gemini --context-file {ctx} --mode diagnosis
   ```
3. Collect outputs. If a provider fails (exit 1), **retry once** after 5 seconds.
   If the retry also fails, note as unavailable and continue — failures are non-blocking.
4. When invoking the test-analyst subagent, pass `external_diagnoses` with the raw GPT + Gemini outputs. The test-analyst validates external categorizations against its own analysis.

**Audit trail:** After verification completes (pass or fail), record a chain entry:
1. Write the task definition block to a temp file (input)
2. Write the verification command output to a temp file (output)
3. Run:
```bash
python .claude/tools/chain_manager.py record \
  --task T{NN} --pipeline execute --stage verify --agent self \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Self-verify T{NN}" \
  --verdict PASS \
  --metadata '{"command": "{verification_cmd}", "exit_code": 0, "files_touched": ["{paths}"]}'
```
Use `--verdict FAIL` if verification failed. Omit `--verdict` if unclear.

## Step 5: REVIEW

Delegate to subagent reviewers by loading their personas from `.claude/agents/`.
Always run `code-reviewer`. Run `security-auditor` when the task touches
auth, data, APIs, secrets, or financial logic (see conditional rules below).

### Agent delegation procedure

For every subagent call in this step:

1. **Read** the persona file with the Read tool: `.claude/agents/{agent-name}.md`
2. **Include the full persona content** verbatim at the top of the Task tool prompt
3. Append the structured inputs listed below for that agent
4. Use `subagent_type: "general-purpose"` with `model: "sonnet"`

Do NOT paraphrase the persona. Do NOT write your own review prompt.
The persona defines review criteria, output format, and bias rules.

### External Code Review (conditional — multi-LLM feed-forward)

Read `.claude/advisory-config.json`. If `multi_llm_review.enabled` is true
AND `"code-review"` is in `multi_llm_review.contexts`, run external reviews
BEFORE the Claude code-reviewer. Their findings will be fed INTO the
code-reviewer as additional input.

**Phase 1 — External reviews (run GPT + Gemini in parallel):**

1. Generate git diff of changed files:
   ```bash
   git diff HEAD -- {changed_files} > {temp_diff_file}
   ```
2. Write context JSON to a temp file:
   ```json
   {
     "task_id": "T{NN}",
     "task_definition": "{acceptance criteria}",
     "git_diff": "{diff content}",
     "decisions": "{relevant decisions}",
     "constraints": "{relevant constraints}"
   }
   ```
3. Run both providers in parallel (if enabled in `advisors`):
   ```bash
   python .claude/tools/second_opinion.py --provider openai --context-file {ctx} --mode code-review
   python .claude/tools/second_opinion.py --provider gemini --context-file {ctx} --mode code-review
   ```
4. Collect outputs. If a provider fails (exit 1), **retry once** after 5 seconds.
   If the retry also fails, note "{Provider} review unavailable — 2 attempts failed" and continue.
   Do NOT retry more than once — external LLM failures should not block execution.
5. Record each external review in the audit chain:
   ```bash
   python .claude/tools/chain_manager.py record \
     --task T{NN} --pipeline execute --stage external-review --agent {provider}-code-review \
     --input-file {ctx} --output-file {temp_output} \
     --description "{Provider} external code review of T{NN}"
   ```

**Phase 2 — Claude code-reviewer (runs after externals complete):**

### code-reviewer (always)
Load persona: `.claude/agents/code-reviewer.md`

Provide:
- `task_id`: T{NN}
- `task_definition`: acceptance criteria, allowed files
- `decisions`: relevant decision entries
- `constraints`: relevant constraint entries
- `changed_files`: list of files modified
- `verification_output`: The console output from Step 4 (proof it runs)
- `external_review_findings`: (if Phase 1 ran) The raw, unedited GPT and Gemini code review outputs from Phase 1. Format: `"GPT: {output}\n\nGemini: {output}"`. If Phase 1 didn't run or both failed, omit this field.

### security-auditor (conditional — auth, data, APIs, secrets, financial)
Load persona: `.claude/agents/security-auditor.md`

**Run when** the task touches: authentication/authorization, user data or PII,
API endpoints, secrets/config, file system operations, or financial logic.
**Skip** for pure CSS/style tasks, documentation-only tasks, test data fixtures,
and scaffolding with no business logic.

Provide:
- `task_id`: T{NN} (or DF-{NN} / QA-{NN})
- `changed_files`: files to review
- `task_context`: what the task does
- `constraints`: security-relevant constraints

### frontend-style-reviewer (conditional)

If the current task touches CSS, style, or UI files (`.css`, `.scss`, `.tsx`/`.jsx`
with style changes, classes, design tokens), also run:

Load persona: `.claude/agents/frontend-style-reviewer.md`

Provide:
- `changed_files`: CSS/style files modified
- `task_context`: what the task does (UI-relevant parts)
- `design_tokens`: content of `.workflow/style-guide.md` if it exists; if no
  style guide exists, pass `"No style guide — use internal consistency checks"`
  (the agent has a fallback mode for this case)

Run **in parallel** with code-reviewer and security-auditor (when applicable).

### Audit trail for reviews

After **each** reviewer returns, record a chain entry:
1. Write the structured input you sent to the reviewer to a temp file
2. Write the reviewer's full response to a temp file
3. Run:
```bash
python .claude/tools/chain_manager.py record \
  --task T{NN} --pipeline execute --stage review --agent {reviewer-name} \
  --input-file {temp_input} --output-file {temp_output} \
  --description "{Reviewer-name} review of T{NN} (cycle {N})" \
  --verdict {PASS|CONCERN|BLOCK} \
  --metadata '{"review_cycle": {N}}'
```

Do this for each reviewer (code-reviewer, security-auditor, and
frontend-style-reviewer if applicable). The chain links each reviewer's
output to the previous entry, creating a traceable sequence of all
review actions for the task.

### Handling Review Results

| Verdict | Action |
|---------|--------|
| **PASS** | Proceed to step 7 |
| **CONCERN** | Review findings. Fix if quick, note if cosmetic. Proceed. |
| **BLOCK** | Must fix. Return to step 3. Re-verify. Re-review. Max 3 cycles. |

After 3 review cycles with BLOCK: escalate to user.

## Step 6: ADDRESS

If reviewers returned CONCERN or BLOCK findings:

1. Fix only what the reviewers listed. Nothing more.
2. Re-run verification (step 4)
3. Re-run the reviewer that flagged the issue (step 5)
4. Repeat until PASS or CONCERN-only

**Do not create new tasks for code-level findings.** The original task wasn't done.
Fix it within the same task scope.

### Deferred Findings (Scope Gaps)

If a reviewer or self-verify reveals a **missing feature or behavior** that:
- Is NOT a code fix for the current task (it's something the task queue never covered)
- Belongs in v1 scope (ties to a spec section, decision, or user workflow)
- Cannot be addressed within the current task's file list

Then log it as a deferred finding. Append to `.workflow/deferred-findings.md`:

```markdown
### DF-{NN}: {Title}
**Discovered:** T{NN} — {task title}
**Category:** missing-feature | missing-validation | missing-integration | missing-test
**Affected area:** {module/entity/workflow}
**Files likely needed:** {best guess at file paths}
**Spec reference:** {which project-spec section or decision ID this relates to}
**Description:** {2-3 sentences: what's missing, why it matters, why it's v1 scope}
**Status:** open
```

Number sequentially: DF-01, DF-02, etc. Check existing entries for the next number.

**When NOT to defer:**
- Code bugs in the current task → fix them (Step 6 normal path)
- Nice-to-haves or v2 ideas → note in reflection, not deferred findings
- Things already covered by a later task → check task-queue.md first

## Step 7: REFLECT

If anything unexpected happened during this task, log a reflection:

Append to the `"entries"` array in `.workflow/reflexion/index.json`:

```json
{
  "id": {N},
  "timestamp": "{ISO 8601}",
  "task_id": "T{NN}",
  "tags": ["{module}", "{concept}", "{decision_id}", "{file_path}", "{error_type}"],
  "severity": "low | medium | high",
  "what_happened": "{factual description of the issue}",
  "root_cause": "{why it happened — evidence-based}",
  "lesson": "{what to do differently — 1-2 sentences}",
  "applies_to": ["{task types or file patterns where relevant}"]
}
```

**When to reflect:**
- An assumption was wrong
- A decision created an unexpected edge case
- A library/tool behaved differently than expected
- A pattern that worked elsewhere failed here
- Something took much longer than expected

**When NOT to reflect:**
- Everything went as planned
- The fix was a typo

Append to `.workflow/reflexion/index.json`.

**Process learnings (optional):** If a *workflow/process* surprise occurred (not a code
bug but a process insight — e.g., "splitting large tasks into sub-tasks reduced review
cycles", "running security auditor early caught auth issues sooner"), append to
`.workflow/reflexion/process-learnings.md`:

```markdown
### {ISO date} — {one-line title}
**Task:** T{NN}
**Insight:** {what you learned about the workflow/process itself}
**Recommendation:** {what to do differently in future projects}
```

This is separate from per-task reflections (index.json = technical surprises,
process-learnings.md = workflow/meta insights). Most tasks won't have process learnings —
only log when genuinely useful.

## Step 8: COMMIT

```bash
git add {changed files only — not unrelated files}
git commit -m "T{NN}: {task title}"       # or "DF-{NN}: {title}" for deferred findings
```

After successful commit, mark the task complete:
Use replace_string_in_file to change `[~] T{NN}` (or `[~] DF-{NN}`) to `[x] ...` in `task-queue.md`.

Then push to remote (soft failure — don't block the loop):
```bash
git push 2>&1 || echo "⚠️ Push failed — will retry on next commit."
```

### Rollback (when milestone review requires reverting a task)

If a milestone review identifies that a previously committed task caused
integration failures and the fix requires reverting that task's changes:

1. `git revert {commit_sha}` — creates a new revert commit (preserves history)
2. Mark the reverted task as `[ ] T{NN}` again in task-queue.md (re-pending)
3. Log a reflection explaining why the task was reverted
4. The task re-enters the queue and will be picked up again with the new context

**Never use `git reset --hard` or force-push** to undo committed work. Revert
commits preserve history and are safe for shared branches. Escalate to user
before any destructive git operation.

Show stderr so failures are diagnosable. On first push, use `git push -u origin {branch}` to set upstream tracking.

The pre-commit-gate hook will run automatically:
- Type check
- Security scan
- Tests with coverage

**If hook blocks:** Read the error output carefully. Common causes and fixes:
- **Lint failure** → run `ruff check --fix` on the failing file, then retry
- **Type check failure** → fix the type error in the reported file:line, then retry
- **Security scan failure** → check if it's a real issue or false positive; fix or add inline ignore
- **Test failure** → diagnose the failing test (may need test-analyst), fix, then retry

If the same hook blocks **3 times in a row** on the same error, escalate to user —
the issue may require a structural change beyond the current task's scope.

### CR Auto-Resolution (release tasks only)

If the completed task has a `**CRs:**` field (release-mode tasks), check each referenced CR:

1. Read the release section header to find all tasks in this release
2. For each CR referenced by the just-completed task:
   - Find ALL tasks in the release that reference this CR
   - If ALL of them are `[x]` (complete):
     - Update the CR's status in `.workflow/backlog.md`: `in-progress` → `resolved`
     - Display: `CR-{NNN} resolved — all linked tasks complete`
   - If some are still `[ ]` or `[~]`: do nothing (CR stays `in-progress`)

This runs automatically — no user interaction needed. The CR→task link via
the `**CRs:**` field makes this deterministic.

## Step 9: EVAL

Append an entry to the `"entries"` array in `.workflow/evals/task-evals.json`:

```json
{
  "task_id": "T{NN}",
  "milestone": "M{N}",
  "status": "completed",
  "started_at": "{ISO 8601 timestamp}",
  "completed_at": "{ISO 8601 timestamp}",
  "review_cycles": {N},
  "security_review": true | false | null,
  "test_results": {
    "total": {N},
    "passed": {N},
    "failed": {N},
    "skipped": {N}
  },
  "files_planned": ["{paths from task spec}"],
  "files_touched": ["{paths from git diff}"],
  "scope_violations": {N},
  "reflexion_entries_created": {N},
  "notes": "{optional — edge cases or escalation reasons}"
}
```

## Step 10: ADVANCE

Check what comes next:

```
IF next item is a task:
  → Return to step 1 with next task

IF current task is the last in a milestone:
  → Run milestone review (see below)

IF all tasks complete:
  → Run End-of-Queue Verification & Fix Pass (see below)
  → For evolution releases: /release (tag, close CRs, release notes)
  → Then /retro
```

---

## Milestone Review

At the end of each milestone, invoke the **milestone-reviewer** subagent.
Load persona: `.claude/agents/milestone-reviewer.md`

Provide:
- `milestone_id`: M{N}
- `milestone_definition`: from task-queue.md (including integration criteria)
- `task_list`: tasks in this milestone
- `prior_milestones`: previously completed milestones
- `project_spec_excerpt`: relevant workflows
- `external_review_findings`: (optional) if `multi_llm_review.enabled` and `"code-review"` in contexts, run GPT + Gemini with a milestone-level integration review before invoking the milestone-reviewer. Use `--mode code-review` with a context summarizing cross-module integration points. Pass their outputs as `external_review_findings`.

### Audit trail for milestone review

After the milestone-reviewer returns, record a chain entry:
1. Write the milestone inputs (milestone definition, task list) to a temp file
2. Write the milestone-reviewer's full response to a temp file
3. Run:
```bash
python .claude/tools/chain_manager.py record \
  --task M{N} --pipeline execute --stage milestone_review --agent milestone-reviewer \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Milestone M{N} integration review" \
  --verdict {MILESTONE_COMPLETE|FIXABLE|BLOCKED} \
  --metadata '{"test_suites": ["smoke", "integration", "functional", "regression"]}'
```

### Handling Milestone Review Results

| Verdict | Action |
|---------|--------|
| **MILESTONE_COMPLETE** | Commit milestone marker, then check `milestone_pause` setting |
| **FIXABLE** | Fix issues, re-run code-reviewer on affected tasks, re-run milestone-reviewer. Max 2 cycles. Pass previous cycle's failure list as context so the reviewer can verify fixes and avoid regressions. |
| **BLOCKED** | Escalate to user with findings and options (ALWAYS pauses, regardless of config) |

After milestone passes:
```bash
git commit --allow-empty -m "M{N}: {milestone name} — milestone complete"
git push
```

**Config-driven behavior after milestone marker commit:**

If `milestone_pause.enabled` is `false` (default):
- Display a brief milestone completion line:
  `✅ M{N}: {milestone name} — complete. Continuing to M{N+1}.`
- Handle deferred findings per `deferred_auto_action` (see below)
- Immediately continue to the next milestone's first task (Step 1)
- Do NOT pause, summarize, or ask the user anything

If `milestone_pause.enabled` is `true`:
- Display the full milestone summary
- Present deferred findings for user decision
- Wait for user to acknowledge before continuing

### Deferred Finding Promotion

After the milestone marker commit, check `.workflow/deferred-findings.md` for
entries with `**Status:** open`. If any exist:

**If `milestone_pause.enabled` is `true` OR `deferred_auto_action.action` is `"ask"`:**

1. **Present** each open finding to the user:
   ```
   DEFERRED FINDINGS — {N} open after M{N}
   ─────────────────────────────────────────
   DF-01: {title} (from T{XX}) — {one-line description}
   DF-02: {title} (from T{XX}) — {one-line description}

   For each: PROMOTE to task / DEFER to post-v1 / DISMISS?
   ```

**If `milestone_pause.enabled` is `false` AND `deferred_auto_action.action` is `"promote"`:**
- Auto-promote ALL open findings to tasks (append to task-queue.md)
- Display: `Auto-promoted {N} deferred findings to tasks: DF-01, DF-02, ...`
- Continue without pausing

**If `milestone_pause.enabled` is `false` AND `deferred_auto_action.action` is `"defer"`:**
- Auto-defer ALL open findings to post-v1
- Update each status to `deferred-post-v1`
- Display: `Auto-deferred {N} findings to post-v1: DF-01, DF-02, ...`
- Continue without pausing

**If `milestone_pause.enabled` is `false` AND `deferred_auto_action.action` is `"preview"`:**
- Display each finding with a one-line summary (same as "ask" display format)
- But do NOT pause — auto-promote all after displaying
- This gives the user visibility into what's being promoted without blocking execution
- Display: `Preview: promoting {N} deferred findings: DF-01 ({title}), DF-02 ({title}), ...`
- Continue without pausing

2. **For each promoted finding** (whether user-chosen or auto-promoted), append a task to `task-queue.md`:
   ```markdown
   ### [ ] DF-{NN}: {Title}
   **Milestone:** Deferred (discovered during M{N})
   **Depends on:** {last completed task or "None"}
   **Source:** Deferred finding from T{XX} review
   **Decisions:** {relevant decision IDs from the finding's spec reference}

   **Goal:** {from the finding's description}

   **Files:**
   - Create: {from finding's "files likely needed"}
   - Modify: {from finding's "files likely needed"}

   **Acceptance Criteria:**
   1. {derived from finding description}

   **Verification:**
   ```bash
   {appropriate test command}
   ```

   **Review:** code-reviewer {+ security-auditor if relevant}
   ```

3. **Update** the finding's status in `deferred-findings.md`:
   - Promoted → `**Status:** promoted → DF-{NN}`
   - Deferred to post-v1 → `**Status:** deferred-post-v1`
   - Dismissed → `**Status:** dismissed — {reason}`

4. DF tasks are executed in the normal Ralph loop — they appear as the
   next `[ ]` entries and get picked up by Step 1 (LOAD).

---

## End-of-Queue Verification & Fix Pass

When the current scope's tasks are complete, run end-of-queue verification.

**Trigger — greenfield:** All tasks in task-queue.md are `[x]` (complete).

**Trigger — evolution (release mode):** All tasks under the current
`## Release: v{X.Y}` section in task-queue.md are `[x]` (complete).
Earlier release sections and original v1 tasks are not checked — they
were verified when their own scope completed. Look for the release header
that matches the current pipeline's release scope (from pipeline-status.json
or the most recent `## Release:` header with incomplete tasks).

**Verification scope:** Regardless of trigger mode:
- **Layer 0 (Full test suite):** Always runs the COMPLETE project test suite.
  Evolution changes can break v1 features — full suite is mandatory.
- **Layer 1 (Browser QA):** Conditional. For evolution releases, only run if
  the release's tasks touch FRONT-XX related files (`.tsx`, `.jsx`, `.css`,
  `.scss`, UI components). If no frontend changes, skip with note.
- **Layer 2 (Style compliance):** Same conditional as Layer 1.

### Layer 0: Full Test Suite (always runs)

Before any browser/style QA, run the complete project test suite one final time.
Individual task verifications pass in isolation, but the assembled whole can reveal
cross-milestone integration gaps.

```bash
# Run the project's complete test command (from TEST-XX decisions or project-spec)
{test_command}  # e.g., pytest --tb=short -q, npm test, etc.
```

Classify failures by severity:
- **CRITICAL:** Tests for core user workflows or primary jobs-to-be-done fail
- **MAJOR:** Tests for secondary features, edge cases, or non-critical integrations fail
- **MINOR:** Flaky tests, warnings, deprecation notices (not actual failures)

Record chain entry:
```bash
python .claude/tools/chain_manager.py record \
  --task FINAL-VERIFY --pipeline execute --stage final_test_suite --agent self \
  --input-file {temp_input} --output-file {temp_test_output} \
  --description "End-of-queue full test suite: {N} tests, {N} failures" \
  --verdict {PASS|CONCERN|BLOCK} \
  --metadata '{"total": {N}, "passed": {N}, "failed": {N}, "skipped": {N}}'
```

### Layer 1: Browser QA (conditional — web UI projects)

**Conditions:** FRONT-XX decisions exist in decisions.md.
**Skip if:** No FRONT-XX decisions (API-only, CLI, library projects).

1. **Start the application** (if not already running):
   ```bash
   {dev_server_command} &
   APP_PID=$!
   # Wait for ready (poll health endpoint or sleep)
   ```

2. **Run qa-browser-tester:**

   Load persona: `.claude/agents/qa-browser-tester.md`

   Provide:
   - `milestone_id`: "FINAL" (end-of-queue)
   - `milestone_definition`: full project deliverable summary
   - `completed_tasks`: all tasks
   - `app_url`: http://localhost:{port}
   - `uix_decisions`: all UIX-XX entries from decisions.md
   - `test_decisions`: relevant TEST-XX entries
   - `project_spec_excerpt`: all screens, workflows, jobs-to-be-done
   - `competition_analysis_excerpt`: table-stakes features (if `.workflow/competition-analysis.md` exists)
   - `route_map`: all known routes from FRONT-XX decisions or project spec

3. Record chain entry with `--stage runtime_qa --agent qa-browser-tester`.

### Layer 2: Style Compliance (conditional — when style-guide.md exists)

**Conditions:** `.workflow/style-guide.md` exists.
**Run in parallel with Layer 1** when both apply.

1. **Run style-guide-auditor:**

   Load persona: `.claude/agents/style-guide-auditor.md`

   Provide:
   - `milestone_id`: "FINAL"
   - `app_url`: http://localhost:{port}
   - `style_guide`: content of `.workflow/style-guide.md`
   - `style_decisions`: all STYLE-XX entries from decisions.md
   - `front_decisions`: FRONT-XX entries
   - `route_map`: all pages

2. Record chain entry with `--stage runtime_qa --agent style-guide-auditor`.

### Pipeline tracking for verification layers

After all verification layers complete:
```bash
python .claude/tools/pipeline_tracker.py complete --phase runtime-qa --summary "{verdicts per layer}"
```

---

### QA Fix Pass

**Read `qa_fix_pass` from `.claude/execution-config.json`.** If `qa_fix_pass.enabled`
is `false`, skip this entire section — write ALL findings to `observations.md` and
proceed to `/retro` (preserves pre-v3.5 behavior).

If `qa_fix_pass.enabled` is `true`, proceed with triage and fix loop:

```bash
python .claude/tools/pipeline_tracker.py start --phase qa-fix-pass
```

#### Step A: TRIAGE

Collect findings from ALL verification layers into a unified list. Each finding
already has severity (from the test suite classification or QA agent output) and
source.

**Routing rules:**
- **CRITICAL** → must-fix (always — these are v1 blockers)
- **MAJOR** → read `qa_fix_pass.major_action`:
  - `"fix"` → must-fix
  - `"defer"` → auto-defer to post-v1 (write to observations.md)
  - `"ask"` → present to user per finding for decision
- **MINOR / INFO** → auto-defer (write directly to observations.md)

Display the triage summary:
```
═══════════════════════════════════════════════════════════════
END-OF-QUEUE VERIFICATION — TRIAGE
═══════════════════════════════════════════════════════════════

Layer              │ CRITICAL │ MAJOR │ MINOR │ INFO │ Verdict
───────────────────┼──────────┼───────┼───────┼──────┼────────
Full test suite    │ {N}      │ {N}   │ {N}   │ —    │ {verdict}
Browser QA         │ {N}      │ {N}   │ {N}   │ {N}  │ {verdict}
Style compliance   │ {N}      │ {N}   │ {N}   │ {N}  │ {verdict}
───────────────────┼──────────┼───────┼───────┼──────┼────────
Total              │ {N}      │ {N}   │ {N}   │ {N}  │

Must-fix: {N}    Deferred: {N}
═══════════════════════════════════════════════════════════════
```

If zero must-fix findings:
```bash
python .claude/tools/pipeline_tracker.py skip --phase qa-fix-pass --reason "No CRITICAL/MAJOR findings"
```
Write all findings to observations.md, stop the app, proceed to `/retro`.

Record triage chain entry:
```bash
python .claude/tools/chain_manager.py record \
  --task QA-FIX-PASS --pipeline execute --stage qa_fix_triage --agent qa-fix-triage \
  --input-file {temp_qa_findings} --output-file {temp_triage_result} \
  --description "QA Fix Pass triage: {N} must-fix, {N} deferred" \
  --metadata '{"critical": {N}, "major_fix": {N}, "major_defer": {N}, "minor": {N}, "info": {N}}'
```

#### Step B: GENERATE QA-{NN} tasks

For each must-fix finding, create an entry in `.workflow/qa-fixes.md`:

```markdown
### [ ] QA-{NN}: {Title}
**Source:** test-suite | qa-browser-tester | style-guide-auditor
**Severity:** CRITICAL | MAJOR
**Page:** {route/URL or "N/A" for test failures}
**Original finding:** {description / test failure message}
**Expected:** {what should happen per spec/test}
**Evidence:** {test output / console errors / computed values}
**Ref:** {TEST-XX / UIX-XX / STYLE-XX / decision ID}

**Fix approach:** {1-2 sentences — how to fix this}
**Files:**
- Modify: {file paths}

**Verification:**
```bash
{specific test command or browser check}
```

**Review:** code-reviewer {+ security-auditor if relevant}
```

**Status markers:** `[ ]` = pending, `[~]` = in-progress, `[x]` = completed.

#### Step C: QA FIX LOOP

Execute each QA-{NN} task using the same Ralph loop mechanics:

```
FOR EACH QA-{NN} in qa-fixes.md (in order):

  1. LOAD — Read QA-{NN} block, mark [~], surface matching reflexions
  2. PLAN — Display fix plan, proceed immediately
  3. IMPLEMENT — Fix the issue (same scope discipline rules)
  4. SELF-VERIFY — Run the verification command from QA-{NN}
  5. REVIEW — code-reviewer (always) + security-auditor (always)
     Same review gate: PASS → commit, CONCERN → fix, BLOCK → fix + re-review
     Max 3 review cycles per QA fix
  6. REFLECT — Only if something unexpected happened
  7. COMMIT — git commit -m "QA-{NN}: {title}", mark [x] in qa-fixes.md, git push
  8. EVAL — Append to task-evals.json with task_id "QA-{NN}" and "qa_fix_pass": true
```

Record chain entries for each QA fix:
- `--task QA-{NN} --stage qa_fix_verify` (after verification)
- `--task QA-{NN} --stage qa_fix_review --agent code-reviewer` (after review)

#### Step D: RE-VERIFICATION (full test suite + targeted QA)

After all QA-{NN} fixes are committed, re-verify. Fixes can introduce regressions,
so the full test suite MUST re-run — not just previously-failing tests.

1. **Full test suite (always):** re-run the ENTIRE project test suite
   ```bash
   {test_command}  # same command as Layer 0 — full suite, not filtered
   ```
   This catches regressions introduced by QA fixes. Classify any NEW failures
   by severity (same rules as Layer 0).

2. **Browser QA fixes (if Layer 1 ran):** re-run qa-browser-tester with targeted scope:
   ```
   reverify_mode: true
   targeted_routes: ["/affected-page-1", "/affected-page-2"]
   ```
   (Runs Phases 1-4 only on affected routes)

3. **Style fixes (if Layer 2 ran):** re-run style-guide-auditor with targeted scope:
   ```
   reverify_mode: true
   targeted_routes: ["/affected-page-1", "/affected-page-2"]
   ```
   (Runs Phases 2-6 only on affected pages)

Run the full test suite first (blocking). Then run browser QA and style
re-verification in parallel if both apply.

Record chain entries per layer:
```bash
python .claude/tools/chain_manager.py record \
  --task QA-REVERIFY --pipeline execute --stage qa_reverify --agent {agent} \
  --input-file {temp_input} --output-file {temp_output} \
  --description "QA re-verification cycle {N}: {result}" \
  --verdict {verdict} \
  --metadata '{"cycle": {N}, "full_suite_passed": {true|false}, "targeted_routes": [...]}'
```

**If re-verification finds NEW issues:**
- NEW CRITICAL → create new QA-{NN} entries, execute fix loop again (next cycle)
- NEW MAJOR/MINOR/INFO → auto-defer to observations.md
- **Max cycles:** controlled by `qa_fix_pass.max_cycles` (default 3)
- If the final cycle STILL has test failures or new CRITICAL issues → **escalate to user**
  (something is structurally wrong — fixes are introducing regressions)

**The loop continues until the full test suite passes clean AND no new CRITICAL
findings exist from browser QA / style layers, OR max_cycles is reached.**

#### Step E: COMPLETE

1. Write all deferred findings to `.workflow/observations.md` (MINOR, INFO, deferred MAJOR,
   and any new findings from re-verification that were auto-deferred)

2. Stop the application (if started for browser QA):
   ```bash
   kill $APP_PID 2>/dev/null
   ```

3. Display completion summary:
   ```
   ═══════════════════════════════════════════════════════════════
   END-OF-QUEUE VERIFICATION COMPLETE
   ═══════════════════════════════════════════════════════════════

   Verification layers:
     Full test suite:  {verdict} ({N} tests, {N} failures)
     Browser QA:       {verdict} ({N} findings) [or: skipped — no FRONT-XX]
     Style compliance: {verdict} ({N} findings) [or: skipped — no style-guide.md]

   QA Fix Pass:
     Must-fix executed: {N}  (QA-01 through QA-{NN})
     Deferred to post-v1: {N}
     Re-verification cycles: {N}

   {N} deferred findings written to observations.md

   Next: /retro
   ═══════════════════════════════════════════════════════════════
   ```

4. Record completion chain entry:
   ```bash
   python .claude/tools/chain_manager.py record \
     --task QA-FIX-PASS --pipeline execute --stage qa_fix_complete --agent qa-fix-pass \
     --input-file {temp_qa_fixes_md} --output-file {temp_summary} \
     --description "QA Fix Pass complete: {N} fixed, {N} deferred, {N} cycles" \
     --verdict PASS \
     --metadata '{"fixed": {N}, "deferred": {N}, "reverify_cycles": {N}}'
   ```

5. Pipeline tracking:
   ```bash
   python .claude/tools/pipeline_tracker.py complete --phase qa-fix-pass --summary "{N} fixed, {N} deferred"
   ```

6. **Config-driven behavior after verification:**

   If `runtime_qa_pause.enabled` is `false` (default):
   - Display the summary and proceed directly to `/retro`
   - Do NOT pause for acknowledgment

   If `runtime_qa_pause.enabled` is `true`:
   - Display the summary and wait for user acknowledgment before `/retro`

---

## Task Failure Escalation

Escalate to the user when:
- 3 review cycles and still BLOCK
- 2 milestone review cycles and still failing
- Task requires a file/module not in any task's scope
- Task contradicts a locked decision
- External service is unavailable and no mock exists

When escalating:
```
═══════════════════════════════════════════════════════════════
⚠️ ESCALATION — T{NN}: {title}
═══════════════════════════════════════════════════════════════

Issue: {what's wrong}
Attempts: {what you tried}
Root cause: {your analysis}

Options:
  A) {option — with trade-off}
  B) {option — with trade-off}
  C) Skip task (document why in reflection)
═══════════════════════════════════════════════════════════════
```

---

## Session Recovery

If context compacts mid-task, the `on-compact.sh` hook re-injects these signals:

1. **Active task or QA fix** — `[~]` marker from task-queue.md or qa-fixes.md (with 8 lines of context)
2. **Next pending task** — first `[ ]` in task-queue.md (if no active task)
3. **Pipeline progress** — current phase, completed/total phases from pipeline-status.json
4. **Last 3 reflections** — recent lessons from reflexion/index.json
5. **Last chain entry** — sequence number, task, stage, agent, verdict
6. **Multi-LLM review status** — whether external reviews are enabled and which contexts
7. **Advisory skip state** — whether user disabled advisories (not relevant during execute, but injected)
8. **Specialist session** — if specialist-session.json exists, specialist takes priority (not relevant during execute)

After compaction or session restart:
1. Read the injected state from on-compact — it provides the immediate context
2. Read `.workflow/pipeline-status.json` if it exists — check `current_phase` and
   the execute phase's nested progress (last completed milestone/task) to confirm
   where you left off. This is more reliable than scanning task-queue.md alone.
3. Check `.workflow/qa-fixes.md` for `[~]` markers — if found, you compacted
   mid-QA-fix-pass. Resume that QA-{NN} fix (not the main task queue).
4. Find the `[~]` task in task-queue.md — read only that block
5. If no `[~]` found in either file, find the first `[ ]` task (next pending)
6. If unclear, check the last few entries in task-evals.json to find
   the last completed task and resume from the next one
7. Cross-reference steps 2-6: pipeline-status, task-queue markers, and evals
   should agree. If they disagree, trust task-queue.md markers as source of truth.
8. Check multi-LLM review status (signal 6) — ensure external reviews continue
   to run if they were enabled before compaction.
9. Do NOT re-read the full task queue, decisions, or reflexion files —
   load only what's needed for the current task
10. Run chain integrity check: `python .claude/tools/chain_manager.py verify`
    If broken links detected, report them but continue — chain corruption
    doesn't block execution

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad |
|---|---|
| "Tests pass so it's done" | Tests may be incomplete. Reviewers check criteria. |
| Fixing beyond the review list | Scope creep inside a fix cycle |
| Skipping review for "simple" tasks | Simple tasks have simple bugs that compound |
| Creating T05.1 or T05bis | The task isn't done. Finish it. |
| Committing with failing hooks | Never force-commit to bypass gates |
| Reflecting on everything | Only surprises. If it went as planned, move on. |
| Skipping milestone review | Integration bugs compound silently |
| Pausing to ask "Should I continue?" | Config says auto_proceed. The user interrupts if needed. |
| Ending a turn after showing the plan | Plan display + implementation must be in ONE turn. |
| Loading full state files into context | Read only the current task block + referenced decisions. Context overflow kills quality. |
| Retrying external LLMs more than once | One retry on failure, then degrade gracefully. Don't block execution for advisory. |
| Running chain integrity check every task | Once per session is enough. Repeated checks waste context and time. |
| Skipping config validation at start | Bad config → wrong pause behavior, wrong deferred action. Validate early. |
| Amending the previous commit after hook failure | Creates a NEW commit instead. Amending after hook failure destroys the previous task's work. |
| Retrying the same failing approach 3+ times | Classify the failure type first (env/flake/code/pre-existing). Different root causes need different fixes. |

---

## Quick Reference

```
Loop:     Load → Plan → Implement → Verify → Review → Address → Reflect → Commit → Eval → Advance
Review:   code-reviewer (always) + security-auditor (conditional: auth/data/APIs/secrets) + external LLM review (if multi_llm_review enabled)
Agents:   context-loader (large files) + research-scout (external docs) available during IMPLEMENT on demand
Cycles:   Max 3 review cycles per task, max 2 milestone review cycles (with failure memory)
Failures: Classify first (environment / flaky / deterministic / pre-existing) before fixing
Reflect:  Only surprises. Tags for searchability.
Commit:   Hooks enforce quality. Never bypass. If hook blocks 3x on same error → escalate.
Rollback: git revert (never reset --hard). Re-pending task in queue. Escalate before destructive git ops.
Push:     After each task commit (soft failure) + after milestone marker.
Escalate: After max cycles, contradictions, or missing dependencies.
Resume:   on-compact injects 8 signals. Cross-ref pipeline-status + task-queue markers + evals.
Deferred: Missing v1 scope → DF-{NN} in deferred-findings.md → promoted at milestone boundary.
Prefixes: T{NN} (planned tasks), DF-{NN} (deferred findings), QA-{NN} (QA fix pass) — all execute the same way.
Verify:   End-of-queue: full test suite (always) + browser QA (FRONT-XX) + style audit (style-guide.md).
QA Fix:   CRITICAL=must-fix, MAJOR=config-driven (fix/defer/ask), MINOR/INFO=auto-defer. QA-{NN} in qa-fixes.md. Max {max_cycles} cycles.
Config:   .claude/execution-config.json — auto_proceed, milestone_pause, deferred_auto_action, runtime_qa_pause, qa_fix_pass.
Validate: Config validated at start. Bad values → warn user + use safe defaults.
Chain:    Integrity check once per session (first task). Retry external LLMs once on failure.
Cleanup:  Temp files from chain entries accumulate. Clean scratchpad between milestones if context is tight.
No pause: NEVER ask "Should I continue?" — read config, follow it. User interrupts if needed.
```

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
- `.claude/execution-config.json` — Execution behavior settings (read FIRST)
- `.workflow/task-queue.md` — The validated task queue
- `.workflow/decisions.md` — Decisions to comply with
- `.workflow/constraints.md` — Boundaries and limits
- `.workflow/reflexion/index.json` — Past reflections (surface matching ones)
- `.workflow/reflexion/process-learnings.md` — Process/workflow lessons (read once at session start)
- `.workflow/deferred-findings.md` — Deferred audit findings (check for overlap with current task)
- `.workflow/evals/task-evals.json` — Task metrics log

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
- **Write tests alongside implementation**, not after. If the task has a
  verification command, make sure it passes.

## Step 4: SELF-VERIFY

Run the verification command from the task definition:

```bash
{verification command from task-queue.md}
```

Also run:
- Lint/format (hooks handle this, but verify no issues)
- Type check on changed files
- Existing test suite (make sure nothing broke)

**If verification fails:** Fix and re-run. Do not proceed to review
with failing tests.

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
Always run both `code-reviewer` and `security-auditor`.

### Agent delegation procedure

For every subagent call in this step:

1. **Read** the persona file with the Read tool: `.claude/agents/{agent-name}.md`
2. **Include the full persona content** verbatim at the top of the Task tool prompt
3. Append the structured inputs listed below for that agent
4. Use `subagent_type: "general-purpose"` with `model: "sonnet"`

Do NOT paraphrase the persona. Do NOT write your own review prompt.
The persona defines review criteria, output format, and bias rules.

### code-reviewer (always)
Load persona: `.claude/agents/code-reviewer.md`

Provide:
- `task_id`: T{NN}
- `task_definition`: acceptance criteria, allowed files
- `decisions`: relevant decision entries
- `constraints`: relevant constraint entries
- `changed_files`: list of files modified
- `verification_output`: The console output from Step 4 (proof it runs)

### security-auditor (always)
Load persona: `.claude/agents/security-auditor.md`

Provide:
- `changed_files`: files to review
- `task_context`: what the task does
- `constraints`: security-relevant constraints

### frontend-style-reviewer (conditional)

If the current task touches CSS, style, or UI files (`.css`, `.scss`, `.tsx`/`.jsx`
with style changes, Tailwind classes, design tokens), also run:

Load persona: `.claude/agents/frontend-style-reviewer.md`

Provide:
- `changed_files`: CSS/style files modified
- `task_context`: what the task does (UI-relevant parts)
- `design_tokens`: reference to design system if any

Run **in parallel** with code-reviewer and security-auditor.

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

Show stderr so failures are diagnosable. On first push, use `git push -u origin {branch}` to set upstream tracking.

The pre-commit-gate hook will run automatically:
- Type check
- Security scan
- Tests with coverage

**If hook blocks:** Read the error, fix the issue, retry commit.
This is normal — the hook catches things reviews might miss.

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
  → Run End-of-Queue Runtime QA (if web UI project — see below)
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
| **FIXABLE** | Fix issues, re-run code-reviewer on affected tasks, re-run milestone-reviewer. Max 2 cycles. |
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

## End-of-Queue Runtime QA (Conditional)

When ALL tasks are complete (no `[ ]` or `[~]` entries remain in task-queue.md)
and the project has a web UI, run a comprehensive runtime QA pass before
handing off to `/retro`.

**Conditions (ALL must be true):**
- All tasks in task-queue.md are `[x]` (complete)
- FRONT-XX decisions exist in decisions.md (project has web UI)

**Skip if:** No FRONT-XX decisions exist (API-only, CLI, library projects).

**Procedure:**

1. **Start the application** (if not already running):
   ```bash
   # Use the project's dev server command from TEST-XX or project-spec
   {dev_server_command} &
   APP_PID=$!
   # Wait for ready (poll health endpoint or sleep)
   ```

2. **Run qa-browser-tester** (always, when conditions met):

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

3. **Run style-guide-auditor** (if `.workflow/style-guide.md` exists):

   Load persona: `.claude/agents/style-guide-auditor.md`

   Provide:
   - `milestone_id`: "FINAL"
   - `app_url`: http://localhost:{port}
   - `style_guide`: content of `.workflow/style-guide.md`
   - `style_decisions`: all STYLE-XX entries from decisions.md
   - `front_decisions`: FRONT-XX entries
   - `route_map`: all pages

   Run in **parallel** with qa-browser-tester if both apply.

4. **Record audit chain entries** for each agent:
   ```bash
   python .claude/tools/chain_manager.py record \
     --task FINAL-QA --pipeline execute --stage runtime_qa --agent qa-browser-tester \
     --input-file {temp_input} --output-file {temp_output} \
     --description "End-of-queue runtime QA" \
     --verdict {QA_PASS|QA_CONCERN|QA_BLOCK} \
     --metadata '{"phases_run": 7, "findings": {"critical": N, "major": N, "minor": N}}'
   ```
   (Same for style-guide-auditor with `--agent style-guide-auditor` and `--verdict {STYLE_PASS|STYLE_CONCERN|STYLE_BLOCK}`)

5. **Write findings to observations.md:**

   For each finding (CRITICAL, MAJOR, MINOR) from both agents, append to
   `.workflow/observations.md`:

   ```markdown
   ## QA Finding: {title}
   **Source:** qa-browser-tester | style-guide-auditor
   **Severity:** {CRITICAL|MAJOR|MINOR}
   **Page:** {route/URL}
   **Description:** {what's wrong}
   **Expected:** {what should happen per UIX-XX / STYLE-XX / spec}
   **Evidence:** {console errors, computed values, screenshots}
   ```

6. **Present summary to user:**
   ```
   ═══════════════════════════════════════════════════════════════
   RUNTIME QA COMPLETE
   ═══════════════════════════════════════════════════════════════

   QA Browser Tester: {QA_PASS|QA_CONCERN|QA_BLOCK}
     {N} critical, {N} major, {N} minor findings

   Style Guide Auditor: {STYLE_PASS|STYLE_CONCERN|STYLE_BLOCK} (or: skipped — no style-guide.md)
     {N} critical, {N} major, {N} minor findings

   All findings written to .workflow/observations.md

   Next steps:
     → /retro (retrospective on v1 execution)
     → /intake (process QA findings into CRs)
     → /plan-delta (plan patches/fixes)
   ═══════════════════════════════════════════════════════════════
   ```

7. **Stop the application:**
   ```bash
   kill $APP_PID 2>/dev/null
   ```

8. **Config-driven behavior after Runtime QA:**

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

If context compacts mid-task, the on-compact hook re-injects:
- Current task ID and state
- Recent reflections

After compaction or session restart:
1. Read the injected state from on-compact
2. Find the `[~]` task in task-queue.md — read only that block
3. If no `[~]` found, find the first `[ ]` task (next pending)
4. If unclear, check the last few entries in task-evals.json to find
   the last completed task and resume from the next one
5. Do NOT re-read the full task queue, decisions, or reflexion files —
   load only what's needed for the current task
6. Run chain integrity check: `python .claude/tools/chain_manager.py verify`
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

---

## Quick Reference

```
Loop:     Load → Plan → Implement → Verify → Review → Address → Reflect → Commit → Eval → Advance
Review:   code-reviewer (always) + security-auditor (always)
Cycles:   Max 3 review cycles per task, max 2 milestone review cycles
Reflect:  Only surprises. Tags for searchability.
Commit:   Hooks enforce quality. Never bypass.
Push:     After each task commit (soft failure) + after milestone marker.
Escalate: After max cycles, contradictions, or missing dependencies.
Resume:   Check evals/task-evals.json for last completed task.
Deferred: Missing v1 scope → DF-{NN} in deferred-findings.md → promoted at milestone boundary.
Prefixes: T{NN} (planned tasks), DF-{NN} (deferred findings) — both execute the same way.
Runtime QA: qa-browser-tester + style-guide-auditor after all tasks complete → findings to observations.md → /intake → /plan-delta.
Config:   .claude/execution-config.json — auto_proceed, milestone_pause, deferred_auto_action, runtime_qa_pause.
No pause: NEVER ask "Should I continue?" — read config, follow it. User interrupts if needed.
```

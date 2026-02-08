# /retro — Evidence-Based Retrospective

## Purpose

Analyze what happened during execution using real data — not feelings.
Uses reflections, eval metrics, and git history to find patterns and
improve the next cycle.

---

## When to Run

- After completing a milestone
- After completing all tasks
- After completing a release (post-v1)
- When execution feels stuck and you want to understand why

---

## Scope Selection

At the start, ask:

```
RETRO SCOPE
───────────
A) Full      — Analyze all tasks and metrics (default)
B) Release   — Analyze tasks from a specific release only
C) Milestone — Analyze a specific milestone

Which scope? A / B / C
```

**If A (Full):** Proceed with all analysis sections below using all data.

**If B (Release):** Ask which release (reads `## Release: v{X.Y}` headers from
`task-queue.md`). Filter all analysis to only tasks under that release header.
Additionally:
- Compare planned CRs (from `.workflow/backlog.md` with matching version lane)
  vs actually resolved (status = `resolved` or `closed`)
- Note CRs that were `planned` but not completed in this release
- Add a "Release Planning Quality" subsection under Planning Quality

**If C (Milestone):** Ask which milestone. Filter to tasks in that milestone block.

---

## Pipeline Tracking

At start (before analysis):
```bash
python .claude/tools/pipeline_tracker.py start --phase retro
```

At completion (after chain_manager record):
```bash
python .claude/tools/pipeline_tracker.py complete --phase retro --summary "{N} tasks analyzed, {X}% first-try pass"
```

---

## Inputs

- `.workflow/reflexion/index.json` — All reflections (per-task technical surprises)
- `.workflow/reflexion/process-learnings.md` — Process/workflow lessons (cross-cutting)
- `.workflow/evals/task-evals.json` — Per-task metrics
- `.workflow/decisions.md` — Decisions that were made
- `.workflow/state-chain/chain.json` — Audit trail of all agent actions
- `.workflow/backlog.md` — CRs and their statuses (release scope only)
- `.workflow/qa-fixes.md` — QA Fix Pass results (if exists)
- `git log --oneline` — Commit history

---

## Analysis

### 1. Execution Metrics

From `task-evals.json` `.entries[]`, compute:

```
Tasks completed: {N} (status = "completed")
Tasks escalated: {N} (status = "escalated")
Average review cycles: {X} (from review_cycles field)
Tasks needing multiple reviews: {N} ({%}) (review_cycles > 1)
Scope violations: {N} total (from scope_violations field)
Total reflections logged: {N} (from reflexion_entries_created field)
```

### 2. Reflection Patterns

From `reflexion/index.json` `.entries[]`, group by tag and severity:

```
Top reflection tags:
  {tag}: {N} reflections ({N} medium, {N} high)
  {tag}: {N} reflections

Recurring issues (entries with matching tags or applies_to):
  - {pattern across multiple reflections}
```

### 2b. Process Learnings

From `.workflow/reflexion/process-learnings.md`, review cross-cutting workflow lessons:
- Which process patterns worked well? (e.g., "running tests before review saved cycles")
- Which process patterns caused friction? (e.g., "milestone reviews were too strict early on")
- Are any process learnings now outdated or superseded by newer entries?
- Recommendations: what should change in the workflow itself (not just code)?

### 3. Review Effectiveness

From eval data:
- What percentage of tasks passed review on first try?
- What did code-reviewer catch most often? (scope, criteria, decisions, edge cases)
- Did security-auditor findings lead to real fixes?
- Did hooks catch things reviewers missed? (or vice versa)

### 4. Planning Quality

- Tasks that needed rework → was the task definition unclear?
- Decisions that caused friction → should the decision be revisited?
- Missing tasks discovered during execution → planning gap
- Tasks that were trivially easy → could have been merged

### 5. Time Distribution

From git timestamps:
- Which tasks took longest?
- Were long tasks predictable from complexity estimates?
- Where did the most rework happen?

### 6. Audit Chain Analysis

First verify chain integrity:
```bash
python .claude/tools/chain_manager.py verify
```

From `.workflow/state-chain/chain.json`, analyze:

```
Chain integrity: ✅ VALID / ❌ BROKEN ({N} broken links)
Total chain entries: {N}

Entries by pipeline stage:
  plan:        {N}
  specialist:  {N}
  synthesize:  {N}
  execute:     {N}
  retro:       {N}

Execute-stage breakdown:
  verify:           {N} entries
  review:           {N} entries ({N} PASS, {N} CONCERN, {N} BLOCK)
  milestone_review:  {N} entries

Review retry patterns:
  Tasks with multiple review cycles: {list from chain entries with review_cycle > 1}

Warnings logged in chain: {N} total
  {warning patterns if any}
```

This data supplements eval metrics — the chain shows the exact sequence
of events, not just summaries.

### 7. End-of-Queue Verification Analysis

If `.workflow/qa-fixes.md` exists, analyze the end-of-queue verification pass:

```
Findings by verification layer:
  Full test suite:  {N} findings ({N} critical, {N} major, {N} minor)
  Browser QA:       {N} findings ({N} critical, {N} major, {N} minor)
  Style compliance: {N} findings ({N} critical, {N} major, {N} minor)

Must-fix executed: {N}
Deferred to post-v1: {N}
Re-verification cycles: {N}
New issues found in re-verification: {N}
```

Per-layer analysis:
- Test suite: which test categories failed most? (unit, integration, e2e)
- Browser QA: which phases found the most issues? (missing functionality vs broken interactions vs edge cases)
- Style: systematic violations vs isolated deviations?

Root cause analysis:
- Which spec areas produced the most findings across all layers?
- Were QA fixes in files that tasks should have covered better?
- Did milestone reviews miss integration issues that the full suite caught?
- Is runtime QA catching real v1 gaps, or mostly polish items?

---

## Output

Present findings in chat. No file output needed unless the user
wants a permanent record.

```
═══════════════════════════════════════════════════════════════
RETROSPECTIVE — {Milestone or Project Name}
═══════════════════════════════════════════════════════════════

Execution Summary:
  Tasks: {N} completed
  Review pass rate (first try): {X}%
  Hook block rate: {X}%
  Reflections: {N}

What Worked:
  - {evidence-based observation}
  - {evidence-based observation}

What Didn't:
  - {pattern} — seen in T{NN}, T{NN}, T{NN}
  - {pattern} — {N} reflections about this

Improvements for Next Cycle:
  1. {specific, actionable change}
  2. {specific, actionable change}
  3. {specific, actionable change}

Planning Gaps:
  - {feature/task that was missing}
  - {decision that caused friction}
═══════════════════════════════════════════════════════════════
```

---

## Key Questions to Answer

1. **Is planning helping?** Compare rework rate against what you'd
   expect without planning. If most tasks pass first try, planning
   is paying off.

2. **Are reviews catching real issues?** If code-reviewer always
   says PASS, either the code is perfect or the reviewer is too lenient.
   Check if hooks catch things after review.

3. **Are reflections useful?** Did any surfaced reflection actually
   prevent a repeated mistake? If not, the tagging might need work.

4. **Where does quality come from?** Rank: planning, hooks, reviews,
   reflections. Double down on what works, simplify what doesn't.

---

## Audit Trail

After presenting the retrospective, record a chain entry:

1. Write the inputs used (eval data summary, reflexion summary) to a temp file
2. Write the retrospective output to a temp file
3. Run:
```bash
python .claude/tools/chain_manager.py record \
  --task RETRO --pipeline retro --stage analysis --agent retro-analyst \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Retrospective: {N} tasks analyzed, {X}% first-try pass rate" \
  --metadata '{"tasks_analyzed": {N}, "first_try_pass_rate": {X}}'
```

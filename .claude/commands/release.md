# /release — Release Closure

## Role

You are a **release manager**. You verify a release is complete, generate
release artifacts, and formally close the release cycle.

You do not plan, implement, or debug. You verify and ship.

---

## Inputs

Read before starting:
- `.workflow/task-queue.md` — Tasks for the release
- `.workflow/backlog.md` — CRs for the release
- `.workflow/evals/task-evals.json` — Task metrics
- `.workflow/qa-fixes.md` — QA fix results (if exists)
- `git log` — Commit history for the release

---

## Preconditions

**Required** (stop and notify user if not met):
- A `## Release: v{X.Y}` section exists in task-queue.md
- ALL tasks under that release section are `[x]` (complete)
- End-of-queue verification has passed (check chain entries for FINAL-VERIFY)

If preconditions are not met:
```
Release v{X.Y} is not ready:
  - {N} tasks still incomplete: T{NN}, T{NN}
  - End-of-queue verification: {not run / failed}

Complete these before running /release.
```

---

## Pipeline Tracking

At start:
```bash
python .claude/tools/pipeline_tracker.py start --phase release
```

At completion:
```bash
python .claude/tools/pipeline_tracker.py complete --phase release --summary "v{X.Y} released"
```

---

## Procedure

### Step 1: Verify Completeness

1. Read the `## Release: v{X.Y}` section — confirm all tasks `[x]`
2. Read `.workflow/backlog.md` — confirm all CRs for this version lane
   are `resolved` (or `wontfix`/`duplicate`/`superseded`)
3. Check chain entries for end-of-queue verification verdict
4. If any check fails, STOP and report what's missing

### Step 2: Generate Release Notes

From the release's CRs and tasks, generate a release summary:

```markdown
# Release Notes — v{X.Y}

**Date:** {date}
**CRs resolved:** {N}
**Tasks completed:** {N}

## Changes

### Bug Fixes
- {CR-NNN}: {title} — {one-line description of fix}

### Enhancements
- {CR-NNN}: {title} — {one-line description}

### Breaking Changes
- {CR-NNN}: {title} — {what changed, migration needed}

## QA Summary
- Full test suite: {pass/fail} ({N} tests)
- Browser QA: {pass/skipped} ({N} findings fixed)
- Style compliance: {pass/skipped}
```

Present to user for review before proceeding.

### Step 3: Tag Release

```bash
git tag -a v{X.Y} -m "Release v{X.Y}: {summary}"
```

### Step 4: Close CRs

Bulk-update all `resolved` CRs for this version lane:
`resolved` → `closed`

### Step 5: Write Release Record

Append to `.workflow/releases.md` (create if doesn't exist):

```markdown
## v{X.Y} — {date}

**CRs:** CR-{NNN}, CR-{NNN}, ...
**Tasks:** T{NN} through T{NN}
**Tag:** v{X.Y}
**Commit:** {SHA}
**QA verdict:** {pass}
```

### Step 6: Audit Trail

```bash
python .claude/tools/chain_manager.py record \
  --task RELEASE --pipeline evolution --stage release --agent release-manager \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Release v{X.Y}: {N} CRs closed, {N} tasks" \
  --metadata '{"release": "v{X.Y}", "crs_closed": ["CR-001"], "tag": "v{X.Y}"}'
```

## Completion

```
═══════════════════════════════════════════════════════════════
RELEASE COMPLETE — v{X.Y}
═══════════════════════════════════════════════════════════════
CRs closed: {N} (CR-{first} through CR-{last})
Tasks completed: {N}
Git tag: v{X.Y}
Release notes: presented above

Next: /retro (release scope) for retrospective analysis
═══════════════════════════════════════════════════════════════
```

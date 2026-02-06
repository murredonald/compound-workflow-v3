# /intake — Observation Capture + Optional Triage

## Role

You are an **observation parser**. You read raw, unstructured input — from
`.workflow/observations.md` or directly from the user's chat — and structure
it into Change Requests (CRs) in `.workflow/backlog.md`.

You capture first, triage optionally. You do not plan fixes, investigate
root causes, or implement anything.

---

## Inputs

- `.workflow/observations.md` — Raw feeder file (any format, user pastes anything)
- `.workflow/backlog.md` — Existing CRs (to determine next CR number)
- User's chat message (may contain additional observations)

---

## Outputs

- `.workflow/backlog.md` — Append new CR entries
- `.workflow/observations.md` — Mark processed entries

---

## Pipeline Tracking

At start (before Step 1), initialize evolution pipeline if it doesn't exist:
```bash
# Only if .workflow/pipeline-status.json does not exist:
python .claude/tools/pipeline_tracker.py init --type evolution --project "{project name}"
```
Then start the phase:
```bash
python .claude/tools/pipeline_tracker.py start --phase intake
```

At completion (after chain_manager record):
```bash
python .claude/tools/pipeline_tracker.py complete --phase intake --summary "{N} CRs captured"
```

---

## Procedure

### 1. Gather Raw Observations

Read `.workflow/observations.md` for any content between the `<!-- Paste observations below this line -->`
marker and the `## Processed` section. Also consider the user's chat message
as additional input.

If there's nothing new in either source:
```
No new observations found. Write to .workflow/observations.md or tell me
what you've noticed, then run /intake again.
```

### 2. Extract Observations

Parse the raw input. Identify distinct observations — each bug, friction point,
idea, or piece of feedback becomes a separate CR.

For each observation, infer:
- **Type**: `bug` | `enhancement` | `debt` | `breaking`
- **Severity**: `critical` | `high` | `medium` | `low`
- **Source**: `testing` | `usage` | `review` | `automated`
- **Description**: Clean summary of the observation
- **Steps to Reproduce**: Extract if present (bugs only), otherwise "TBD"
- **Affected Area**: Infer module/screen/API from context

### 3. Assign CR Numbers

Read `.workflow/backlog.md` to find the highest existing CR number.
New CRs continue from there: CR-001, CR-002, etc. (zero-padded to 3 digits).

### 4. Present for Confirmation

```
I found {N} observations:

  CR-{NNN}: {title} [{type}/{severity}]
  CR-{NNN}: {title} [{type}/{severity}]
  CR-{NNN}: {title} [{type}/{severity}]

Correct? Adjust any fields, or confirm to proceed.
```

Wait for user to confirm or adjust.

### 5. Optional Triage

After confirmation:
```
Prioritize these now or skip?
  A) Prioritize — assign version lanes and priority for each CR
  B) Skip — save as "new", triage later
```

**If prioritize:** For each CR, ask:
```
CR-{NNN}: {title} [{type}/{severity}]
  Version lane: v1.1 (stability) / v1.2 (features) / v2.0 (breaking)
  Priority within lane: 1 (highest) / 2 / 3 / 4 (lowest)
```

Set status to `triaged`.

**If skip:** Set status to `new`.

### 6. Write to Backlog

Append each CR to `.workflow/backlog.md` using this format:

```markdown
## CR-{NNN}: {Title}
**Type:** {bug | enhancement | debt | breaking}
**Severity:** {critical | high | medium | low}
**Version Lane:** {v1.1 | v1.2 | v2.0 | unassigned}
**Priority:** {1-4 | unassigned}
**Source:** {testing | usage | review | automated}
**Description:** {Clean description}
**Steps to Reproduce:** {Steps or "N/A"}
**Affected Area:** {module/screen/API}
**Screenshots:** {docs/screenshots/CR-NNN-*.png or "None"}
**Status:** {new | triaged}

---
```

### 7. Mark Processed

Move the raw text from the active section of `observations.md` to the
`## Processed` section at the bottom, prefixed with the CR numbers:
```
- [CR-001, CR-002, CR-003] {original raw text, summarized}
```

## Audit Trail

Record a chain entry:
```bash
python .claude/tools/chain_manager.py record \
  --task INTAKE --pipeline evolution --stage capture --agent intake \
  --input-file {temp_observations} --output-file {temp_backlog_entries} \
  --description "Intake: {N} CRs captured (CR-{first} through CR-{last})" \
  --metadata '{"crs_created": ["CR-001", "CR-002"], "triaged": true}'
```

## Completion

```
═══════════════════════════════════════════════════════════════
INTAKE COMPLETE
═══════════════════════════════════════════════════════════════
CRs captured: CR-{first} through CR-{last} ({N} total)
Triaged: {yes/no}
Version lanes: {v1.1: N, v1.2: N, v2.0: N | "not triaged"}

Next: /plan-delta to plan fixes/features, or add more observations to
.workflow/observations.md and run /intake again.
═══════════════════════════════════════════════════════════════
```

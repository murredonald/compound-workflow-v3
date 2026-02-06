# /plan-delta — Lightweight Planning for Existing Systems

## Role

You are a **delta planner**. You plan changes to an existing codebase —
bugfixes, features, refactors, or breaking changes. You are lighter than
`/plan` because the system already exists; you build on existing decisions
rather than starting from scratch.

You read existing planning artifacts, assess impact, and produce
domain-appropriate decisions. You do not implement anything.

---

## Inputs

Read before starting:
- `.workflow/backlog.md` — CRs to plan for
- `.workflow/project-spec.md` — Existing project specification
- `.workflow/decisions.md` — All existing decisions
- `.workflow/constraints.md` — Boundaries and limits

---

## Outputs

- `.workflow/decisions.md` — Append new decisions (using existing domain prefixes)
- `.workflow/backlog.md` — Update CR statuses to `planned`

---

## Depth Tiers

At the start, present the tier menu. **The user always chooses.**

```
PLAN-DELTA DEPTH
────────────────
A) Quick    — Single bugfix or small patch. ~5 min.
               No specialists, no advisory.
B) Standard — Feature addition or multi-file change. ~20 min.
               1-2 relevant specialists, advisory (config-driven).
C) Major    — Breaking change or architecture impact. ~45 min.
               Multiple specialists, full advisory, migration path.

Which tier? A / B / C
```

---

## Pipeline Tracking

At start (before Step 1):
```bash
python .claude/tools/pipeline_tracker.py start --phase plan-delta
```

At completion (after chain_manager record):
```bash
python .claude/tools/pipeline_tracker.py complete --phase plan-delta --summary "{tier}: {N} CRs planned"
```

---

## Procedure

### Step 1: Select CRs

Ask the user which CR(s) from backlog.md to plan for.
Read those CRs. If they're not `triaged`, note it: "These CRs haven't been
triaged yet. Proceeding with planning — you can triage during /intake later."

### Step 2: Read Context

Read `.workflow/project-spec.md`, `.workflow/decisions.md`, and
`.workflow/constraints.md` to understand the existing system.

For Quick tier: skim the relevant sections only.
For Standard/Major: read thoroughly.

### Step 3: Analyze (varies by tier)

**Quick:**
1. Read source files relevant to the CR
2. Confirm the bug exists (if bug) or understand the change area
3. Identify root cause (if bug) or impact area (if enhancement)
4. If any design choice is needed, produce a decision using the appropriate
   domain prefix (e.g., `BACK-15: Use parameterized queries for login input`)
5. Skip to Step 6

**Standard:**
1. Read source files relevant to the CR(s)
2. Impact analysis: what existing code does this touch? Which modules?
3. Decision compatibility: does this conflict with any existing decisions?
4. Invoke 1-2 relevant existing specialists:
   - Backend change → `/specialists/backend`
   - Frontend change → `/specialists/frontend`
   - Architecture impact → `/specialists/architecture`
   - Security concern → `/specialists/security`
   - Data/ML work → `/specialists/data-ml`
5. Formulate 2-4 targeted questions for the user

### Advisory Perspectives (Standard and Major only)

Follow the shared advisory protocol in `.claude/advisory-protocol.md`.
Use `specialist_domain` = domain of the change (e.g., "backend", "frontend") for this command.

**Major (additions to Standard):**
- Invoke multiple specialists as needed
- Document migration path if breaking changes are involved
- May amend existing decisions (flag clearly: "Amending ARCH-03: ...")
- Full advisory cycle

### Step 4: Produce Decisions

For each design choice, append a decision to `.workflow/decisions.md` using
the **existing domain prefix** with continued numbering:

```
BACK-15: Use parameterized queries for login input sanitization
FRONT-08: Add loading skeleton for dashboard initial render
ARCH-07: Extract auth module to support OAuth2 flow (amends ARCH-03)
```

**No separate DELTA-XX prefix.** A backend decision is BACK-XX whether it's
v1 or v1.2. This keeps decisions.md scannable by domain.

### Step 5: Update CR Status

In `.workflow/backlog.md`, update each planned CR's status:
`triaged` → `planned` (or `new` → `planned` if triage was skipped).

### Step 6: Audit Trail

Record a chain entry:
```bash
python .claude/tools/chain_manager.py record \
  --task PLAN-DELTA --pipeline evolution --stage planning --agent plan-delta \
  --input-file {temp_input} --output-file {temp_output} \
  --description "Plan-delta ({tier}): {N} CRs planned, {N} decisions added" \
  --metadata '{"tier": "standard", "crs_planned": ["CR-001"], "decisions_added": ["BACK-15"]}'
```

### Step 7: Completion

```
═══════════════════════════════════════════════════════════════
PLAN-DELTA COMPLETE ({TIER})
═══════════════════════════════════════════════════════════════
CRs planned: {list}
Decisions added: {list with prefixes}
Decisions amended: {list or "none"}
Specialists consulted: {list or "none"}
Conflicts with existing decisions: {none / list}

Next: /synthesize (release mode) to generate the task queue
═══════════════════════════════════════════════════════════════
```

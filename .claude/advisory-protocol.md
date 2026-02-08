# Advisory Protocol (Shared Reference)

This protocol is referenced by all planning commands and specialist deep dives.
Each calling file specifies `specialist_domain` and its own context.

## Prerequisites

Read `.claude/advisory-config.json` to determine which advisors are enabled.
Also read the `diversity` section — if `diversity.enabled` is true, set
`answers_count` = `diversity.answers_per_advisor` (used in steps below).

## Invoke Advisors (in parallel)

**Claude advisor** (if `advisors.claude.enabled`) — Spawn using the Task tool:
- **Read** the persona: `.claude/agents/second-opinion-advisor.md`
- **Include the full persona** verbatim at the top of the prompt
- Use `subagent_type: "general-purpose"` with `model: "opus"`
- Provide:
  - `project_spec`: Content of `.workflow/project-spec.md` (or current state if not yet generated)
  - `decisions`: Content of `.workflow/decisions.md` (or confirmed decisions so far)
  - `constraints`: Content of `.workflow/constraints.md` (or known constraints so far)
  - `specialist_domain`: As specified by the calling command
  - `focus_area`: The focus area or planning stage you just explored
  - `specialist_analysis`: Your full analysis (options, trade-offs, reasoning)
  - `questions`: The questions you formulated
  - `diversity_mode`: diversity.enabled from advisory-config.json (true/false)
  - `answers_count`: diversity.answers_per_advisor (e.g. 3) — only if diversity_mode is true

**GPT advisor** (if `advisors.gpt.enabled`) — Run in parallel:
- Write context JSON to a temp file with: project_spec, decisions,
  constraints, specialist_domain, focus_area, specialist_analysis, questions
- Run: `python .claude/tools/second_opinion.py --provider openai --context-file {temp_json}` (append `--answers {answers_count}` if diversity enabled)
- If exit 1: note GPT advisory unavailable, continue without it

**Gemini advisor** (if `advisors.gemini.enabled`) — Run in parallel:
- Use the same context JSON temp file
- Run: `python .claude/tools/second_opinion.py --provider gemini --context-file {temp_json}` (append `--answers {answers_count}` if diversity enabled)
- If exit 1: note Gemini advisory unavailable, continue without it

## Challenge Amplification (optional but recommended)

When formulating questions for advisors, include 1-2 **challenge questions** —
specific decisions or assumptions you want the advisors to stress-test.

Frame challenges as: "The specialist/planner proposes X. What could go wrong?
What's the strongest argument against X? What alternative would you recommend?"

This works best when:
- A decision has been made quickly without much debate
- The user seems certain but the specialist has doubts
- A trade-off exists that hasn't been explicitly discussed
- A common beginner mistake pattern applies

**Include challenge context in the temp JSON:**
```json
{
  "specialist_domain": "frontend",
  "specialist_analysis": "...",
  "questions": ["..."],
  "challenge_targets": [
    "User chose CSR for all pages including marketing. SEO impact?",
    "Browser support matrix says 'modern only' but 15% of traffic is Firefox ESR"
  ]
}
```

The `challenge_targets` field is optional. When present, advisors will specifically
stress-test these decisions in addition to providing their regular perspectives.

## Present Results

Display ALL enabled perspectives **VERBATIM and UNEDITED** in labeled boxes:

```
+-- Claude Opus Perspective ------------------------------------+
|  {claude advisor output — COMPLETE, UNEDITED}                 |
+---------------------------------------------------------------+

+-- GPT Perspective --------------------------------------------+
|  {gpt output — COMPLETE, UNEDITED}                            |
+---------------------------------------------------------------+

+-- Gemini Perspective -----------------------------------------+
|  {gemini output — COMPLETE, UNEDITED}                         |
+---------------------------------------------------------------+
```

### Anti-Patterns — DO NOT DO THESE

- **Do NOT summarize** — show every word the advisor returned
- **Do NOT synthesize** — do not merge or combine multiple advisor outputs
- **Do NOT cherry-pick** — do not select only the parts you agree with
- **Do NOT paraphrase** — use the advisor's exact words, not your rephrasing
- **Do NOT editorialize** — do not add commentary between or within advisor outputs
- **Do NOT omit** — if an advisor returned output, the user must see ALL of it

The user needs the raw, unfiltered perspectives to make an informed decision.
Presenting only selected fragments defeats the purpose of multi-LLM diversity.

**IMPORTANT: Do NOT adopt or agree with advisory suggestions. Present them
neutrally and wait for the user's answer. You are the specialist/planner —
the advisors provide input, not decisions.**

## Opt-out

If the user says "skip advisory" or "no advisory" at any point, skip the
advisory protocol for all remaining focus areas/stages in this session.
Acknowledge once: "Advisory disabled for this session."

**Persist the skip state** by writing `.workflow/advisory-state.json`:
```json
{
  "skip_advisories": true,
  "disabled_since": "{ISO 8601 timestamp}",
  "disabled_by": "user"
}
```

**At the start of any command that invokes advisory** (plan, plan-define,
plan-delta, specialists), check if `.workflow/advisory-state.json` exists
and `skip_advisories` is `true`. If so, skip advisory without asking again.
Delete the file when the pipeline completes (retro or release) to reset
for the next session.

After presenting advisories, **stop and wait for user input.**

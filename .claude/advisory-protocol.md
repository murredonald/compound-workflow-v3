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

## Present Results

Display all enabled perspectives in labeled boxes:

```
+-- Claude Opus Perspective ------------------------------------+
|  {claude advisor output}                                      |
+---------------------------------------------------------------+

+-- GPT Perspective --------------------------------------------+
|  {gpt output}                                                 |
+---------------------------------------------------------------+

+-- Gemini Perspective -----------------------------------------+
|  {gemini output}                                              |
+---------------------------------------------------------------+
```

**IMPORTANT: Do NOT adopt or agree with advisory suggestions. Present them
neutrally and wait for the user's answer. You are the specialist/planner —
the advisors provide input, not decisions.**

## Opt-out

If the user says "skip advisory" or "no advisory" at any point, skip the
advisory protocol for all remaining focus areas/stages in this session.
Acknowledge once: "Advisory disabled for this session."

After presenting advisories, **stop and wait for user input.**

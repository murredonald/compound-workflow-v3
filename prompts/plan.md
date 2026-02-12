# Planning: Discovery Phase

You are planning project **{{project_name}}**.

Work through these stages **interactively** (ask, wait for user, then continue):

## Stages

1. **Vision** — What problem does this solve? What type of app?
2. **Users** — Who are the primary users? What are their goals and pain points?
3. **Workflows** — What are the 3-5 core user workflows?
4. **Scope** — What is IN for v1 (MVP) and what is OUT?
5. **Constraints** — Hard limits: tech stack, budget, timeline, regulations
6. **Risks** — Top 3 risks and mitigation strategies

## Output

After each stage, store decisions as JSON via the orchestrator:

{{DECISION_SCHEMA}}

Constraints use a separate format:
```json
{"constraints": [{"id": "C-01", "category": "hard", "description": "Must work offline"}]}
```

## Executive Summary

After all 6 stages are complete, produce a **project summary** — a concise paragraph (3-5 sentences) that frames the project coherently:

- What the project is and what problem it solves
- Who it's for and the core value proposition
- Key technical approach and constraints
- MVP scope in one sentence

Store it via: `python orchestrator.py store-summary --text "Your summary here"`

This summary is passed to every specialist as context so they understand the project's big picture before diving into their domain.

## Rules

- Every response must end with a question — don't assume
- Decisions are drafts until the user confirms
- Don't move to the next stage until the current one is resolved
- Each decision needs a clear rationale
- Minimum 3 GEN decisions before planning is complete
- Required topics: app type, target users, and MVP scope
- Planning is not complete until the executive summary is stored

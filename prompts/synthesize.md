# Synthesize: Generate Task Queue

You are generating an **executable task queue** from all specialist decisions for **{{project_name}}**.

## All Decisions

{{decisions_by_prefix}}

## Constraints

{{constraints}}

## Completed Phases

{{completed_phases}}

{{#milestones}}
## Existing Milestones

{{milestones}}
{{/milestones}}

## Your Job

Turn every non-GEN decision into granular, implementable tasks. One decision may become multiple tasks. Related decisions across domains may combine into one task.

### Task sizing rules
- Each task should be completable in one coding session (~1-2 hours)
- A task should touch no more than 5-8 files
- If a decision is too large for one task, split it (e.g., BACK-01 → T03 "API routes" + T04 "Database models")
- Cross-domain tasks are fine (e.g., BACK-02 + SEC-01 → "JWT auth with rate limiting")
- Do NOT bundle 10+ decisions into a single task — maximum 5 decision_refs per task
- One decision that spans multiple concerns should become MULTIPLE tasks
  (e.g., "JWT auth" → data model, API routes, middleware, tests)
- Count: expect roughly 1 task per 3-5 decisions
  (500 decisions should produce 100-170 tasks, not 45)

### Artifact wiring
- If a task references STYLE-*, FRONT-*, or BRAND-* decisions involving visual
  output, add `artifact_refs: ["style-guide", "brand-guide"]`
- Tasks touching CSS/colors/fonts/typography MUST reference style-guide and brand-guide
- Valid artifact_refs values: `"brand-guide"`, `"style-guide"`,
  `"competition-analysis"`, `"domain-knowledge"`

### Dependency rules
- Infrastructure before features (ARCH → BACK → FRONT)
- Backend APIs before frontend that consumes them
- Security can parallel backend but must complete before deploy
- Testing infrastructure early, test execution after implementation
- No circular dependencies

### Milestone rules
- Create 2-4 milestones ordered by implementation phase
- M1: Foundation (project setup, core models, base infrastructure)
- M2: Core Features (API endpoints, main UI, business logic)
- M3+: Polish / Integration (auth, testing, deployment, UX refinement)

## Output Format

Output a single JSON object. No markdown fences, no explanation — just the JSON.

{{TASK_SCHEMA}}

# Completeness Audit — Find What's Missing Before We Build

You are auditing the task queue for **{{project_name}}** to find
gaps, missing features, dead references, and incomplete coverage.

Your job: apply **7 analytical lenses** to the task queue below
and report every gap you find. Be thorough — anything you miss
will become a bug or a blocked task during implementation.

## Project Summary

{{project_summary}}

## Task Queue (grouped by milestone)

{{task_queue_by_milestone}}

## Decision Index

{{decision_index_compact}}

## Gaps Already Found (deterministic checks)

Automated rules already found these gaps. Do NOT duplicate them.
Focus on gaps the rules missed.

{{deterministic_gaps}}

---

## Analysis Lenses

Work through ALL 7 lenses below. Each lens catches different gap types.

### Lens 1: User Journey Tracing

Identify 5-10 critical user flows from the project summary, then
walk each step-by-step through the task queue.

Example flows to consider:
- First-time user: discovery → signup → verification → onboarding → first value
- Returning user: login → navigate → core action → result → logout
- Admin/operator: authenticate → admin panel → manage resources → verify changes
- Error recovery: bad input → error message → correction → retry → success
- Edge user: forgot password → reset flow → re-login

For each step ask:
1. What does the user see or do?
2. Which task creates this screen/action?
3. What happens if they click every button/link — does a task exist for each destination?
4. What happens on failure at this step?
5. Can they go back? Is the back-path covered?

**Gap types**: `incomplete-journey`, `dead-reference`

### Lens 2: Data Model Completeness

For every data entity implied by the decisions and tasks:
- Is it created? (model definition, migration, seed/fixture data)
- Is it read? (list view, detail view, search/filter)
- Is it updated? (edit form, inline edit, bulk update)
- Is it deleted? (soft delete vs hard delete, cascade effects, confirmation)
- Are relationships handled? (foreign keys, orphan prevention, many-to-many join tables)
- Is there validation? (required fields, uniqueness, format constraints)

**Gap types**: `implied-feature`, `missing-state`

### Lens 3: API Surface & Contracts

For every frontend interaction that needs data:
- Does a backend endpoint exist to serve it?
- Does the endpoint have a task that implements it?

For every backend endpoint:
- Is it consumed by at least one frontend task (or documented as API-only)?
- Does it handle authentication/authorization?
- Does it validate input and return proper error responses?
- Is there pagination for list endpoints?

For every external integration (third-party APIs, webhooks, OAuth providers):
- Is there a task for the integration itself?
- Is there error handling for when the external service is unavailable?
- Are credentials/config managed somewhere?

**Gap types**: `missing-api-contract`, `implied-feature`

### Lens 4: UI States & Feedback

For every page, component, or interactive element implied by the tasks:
- **Empty state**: What shows when there's no data yet? (first-time user, empty search, no items)
- **Loading state**: What shows while data is being fetched?
- **Error state**: What shows when the request fails? Can the user retry?
- **Success state**: Is there confirmation for destructive or important actions?
- **Partial state**: What if data is incomplete? (profile half-filled, upload interrupted)
- **Overflow state**: What happens with too many items? (pagination, virtualization, truncation)
- **Permission state**: What shows when user lacks access? (403 page, disabled buttons, hidden elements)

**Gap types**: `missing-state`, `implied-feature`

### Lens 5: Security & Access Control

- Every protected resource → Is there an auth check task?
- Every role mentioned in decisions → Are permissions enforced in both frontend (hide/disable) and backend (reject)?
- Every form → Is there input validation on both client and server?
- Every file upload → Is there size/type validation?
- Every sensitive action → Is there confirmation, rate limiting, or audit logging?
- Session management → Is there timeout, revocation, concurrent session handling?

**Gap types**: `implied-feature`, `missing-api-contract`

### Lens 6: Cross-Cutting Concerns

Things that apply broadly but might not have explicit tasks:
- **Error handling**: Global error boundary, 404 page, 500 page, network error fallback
- **Navigation**: Are all pages reachable? Does every link have a destination? Breadcrumbs?
- **Search**: If any list has more than ~20 items, is there search or filtering?
- **Notifications**: If actions trigger async processes, how does the user know the result?
- **Email/messaging**: Are transactional emails covered? (welcome, reset, confirmation, receipt)
- **Settings/preferences**: Can users configure their experience? (timezone, language, notifications)
- **Help/onboarding**: Is there any guidance for new users? Tooltips? Docs?
- **Responsive/mobile**: If the project targets mobile, are mobile-specific tasks present?
- **Logging/monitoring**: Are there tasks for observability? (error tracking, analytics, health checks)

**Gap types**: `implied-feature`, `orphaned-component`

### Lens 7: Dependency Chain Integrity

Look at task dependencies and milestone ordering:
- Are there tasks that logically depend on something but have no `depends_on`?
- Are there circular implicit dependencies? (A needs B's output, B needs A's output)
- Are there tasks in early milestones that reference features from later milestones?
- Is there a task that seems too large to be a single unit of work? (should be decomposed)
- Are there orphaned tasks that nothing depends on and don't seem to produce user-facing value?

**Gap types**: `orphaned-component`, `implied-feature`

---

## Severity Guide

- **critical**: Feature is literally broken without this. Dead link, missing API endpoint, no auth on protected route.
- **high**: Major user flow is incomplete. No password reset, no error handling on payment, no logout.
- **medium**: Degraded experience. No loading spinners, no empty states, no search on long lists.
- **low**: Polish gap. No breadcrumbs, no keyboard shortcuts, no animations.

## Output Format

Output a single JSON object. No markdown fences, no explanation.

{{AUDIT_SCHEMA}}

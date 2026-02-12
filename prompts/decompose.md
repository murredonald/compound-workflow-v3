# Decompose: Break Parent Task into Granular Subtasks

You are decomposing **one parent task** into focused, implementable subtasks
for **{{project_name}}**.

## Project Summary

{{project_summary}}

## Parent Task

{{task}}

## Referenced Decisions (full text)

{{decisions}}

## Constraints

{{constraints}}

{{#artifacts}}
## Relevant Artifacts

These artifacts are directly relevant to this task. Use them as reference
for colors, fonts, spacing, naming, domain terminology, and positioning.

{{artifacts}}
{{/artifacts}}

## Decision Index (all domains — for gap detection)

Scan this index for decisions that SHOULD be referenced by this task's
subtasks but are NOT listed in the parent task's decision_refs. Report
any gaps in the `missing_decisions` output field.

{{decision_index}}

## Available Artifacts

{{available_artifacts}}

---

## Your Job

Break the parent task above into **2-6 subtasks** that are individually
implementable. Each subtask should:

1. **Be completable in one focused coding session** (30-90 min)
2. **Touch 1-4 files** (not 8+)
3. **Reference specific decisions** — every parent decision_ref must appear
   in at least one subtask
4. **Reference relevant artifacts** — if a subtask involves visual output
   (CSS, colors, fonts, layout, UI components), include `artifact_refs`
   pointing to `style-guide` and/or `brand-guide`
5. **Have clear acceptance criteria** — testable, not vague

### Decision Audit

For each subtask, explicitly verify:
- Which parent decisions does this subtask implement?
- Are there decisions in the index above that SHOULD apply to this subtask
  but are missing from the parent task? Report these as `missing_decisions`.

### Artifact Wiring Rules

- Subtasks touching CSS, colors, fonts, typography → `["style-guide", "brand-guide"]`
- Subtasks building UI components or layouts → `["style-guide", "brand-guide"]`
- Subtasks dealing with domain terminology → `["domain-knowledge"]`
- Subtasks involving competitive positioning → `["competition-analysis"]`
- Only reference artifacts that are available (listed above)

### Subtask Sizing Rules

- **Too big**: If a subtask has 5+ acceptance criteria or 5+ files, split further
- **Too small**: If a subtask is just "create one file with one function", merge up
- **Right size**: 2-3 acceptance criteria, 1-4 files, 1-3 decision refs

### Dependency Rules

- Earlier subtasks should handle data models / infrastructure
- Later subtasks should handle integration / UI / tests
- Keep the dependency chain short (max depth 3)

## Output Format

Output a single JSON object. No markdown fences, no explanation — just the JSON.

{{DECOMPOSE_SCHEMA}}

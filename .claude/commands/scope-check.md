# /scope-check — Quick Scope Validation

## Purpose

Fast sanity check: compare actual file changes against the current
task's allowed file list. Run anytime you suspect scope drift.

---

## Procedure

1. Read only the `[~]` in-progress task block from `.workflow/task-queue.md` (not the full file)
2. Get changed files: `git status --porcelain` (shows modified AND untracked files)
3. Compare against task's "Files to create" and "Files to modify"
4. Report

## Output

### Clean
```
SCOPE CHECK — {T{NN}|QA-{NN}}: {title}
All changes within scope. ✅
```

### Drift Detected
```
SCOPE CHECK — {T{NN}|QA-{NN}}: {title}

In scope:
  ✅ {file} (expected)
  ✅ {file} (expected)

Out of scope:
  ⚠️ {file} — NOT in task file list

Missing:
  ❌ {file} — listed but not changed

Options:
  A) Remove out-of-scope changes (git checkout {file})
  B) Update task intent with justification
  C) Defer out-of-scope work to a later task
```

## When to Use

- Mid-task gut check
- Before committing (scope-guard hook does this automatically,
  but this gives a more detailed view)
- After a long implementation session
- When you've touched "just one more file"

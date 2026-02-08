#!/bin/bash
# PostToolUse hook: warns when editing files outside the current task's scope.
# Reads the active task from .workflow/task-queue.md. If no workflow state
# exists, silently exits — this hook only activates during /execute.

cd "$CLAUDE_PROJECT_DIR" || exit 0

TASK_QUEUE=".workflow/task-queue.md"
[ ! -f "$TASK_QUEUE" ] && exit 0

if ! command -v jq &>/dev/null; then
  echo "⚠️ jq not installed — scope-guard disabled. Run .claude/scripts/init.sh" >&2
  exit 0
fi

EDITED=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // .path // empty' 2>/dev/null)
[ -z "$EDITED" ] && exit 0

# Find the active task block (marked [~] in-progress)
# Block ends at the next task heading (### [) or end of file
# Handles all task prefixes: T{NN} (planned), DF-{NN} (deferred), QA-{NN} (QA fix)
ACTIVE_BLOCK=$(awk '/\[~\]/{found=1} found && /^### \[/ && !/\[~\]/{exit} found{print}' "$TASK_QUEUE" 2>/dev/null)

# Also check qa-fixes.md for active QA fixes (QA-{NN} tasks live there, not in task-queue)
QA_FIXES=".workflow/qa-fixes.md"
if [ -z "$ACTIVE_BLOCK" ] && [ -f "$QA_FIXES" ]; then
  ACTIVE_BLOCK=$(awk '/\[~\]/{found=1} found && /^### \[/ && !/\[~\]/{exit} found{print}' "$QA_FIXES" 2>/dev/null)
fi
[ -z "$ACTIVE_BLOCK" ] && exit 0

# Extract file paths from the multi-line Files block:
#   **Files:**
#   - Create: path/to/file.py, path/to/other.py
#   - Modify: path/to/existing.py
ALLOWED_FILES=$(echo "$ACTIVE_BLOCK" | awk '/^\*\*Files:\*\*/{found=1; next} found && /^- (Create|Modify):/{gsub(/^- (Create|Modify): */, ""); gsub(/,/, "\n"); print} found && !/^- /{found=0}' | xargs)
[ -z "$ALLOWED_FILES" ] && exit 0

# Check if the edited file matches any allowed file pattern
BASENAME=$(basename "$EDITED")
for pattern in $ALLOWED_FILES; do
  # Match against full path or basename
  if [[ "$EDITED" == *"$pattern"* ]] || [[ "$BASENAME" == *"$pattern"* ]]; then
    exit 0  # Match found, all good
  fi
done

# No match — warn
echo "⚠️  SCOPE: '$EDITED' is not in the current task's file list." >&2
echo "   Allowed: $ALLOWED_FILES" >&2
echo "   If intentional, continue. Otherwise run /scope-check." >&2
exit 0  # Warn only, never block

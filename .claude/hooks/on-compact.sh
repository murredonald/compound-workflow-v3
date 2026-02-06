#!/bin/bash
# SessionStart hook (compact matcher): re-injects workflow state after
# Claude Code compacts the context window. Keeps Claude oriented on
# the current task and recent learnings.

cd "$CLAUDE_PROJECT_DIR" || exit 0

TASK_QUEUE=".workflow/task-queue.md"
REFLEXION=".workflow/reflexion/index.json"

echo "=== WORKFLOW STATE (post-compaction) ==="

if ! command -v jq &>/dev/null; then
  echo "⚠️ jq not installed — reflexion recall disabled. Run .claude/scripts/init.sh"
fi

# Show active task
if [ -f "$TASK_QUEUE" ]; then
  ACTIVE=$(grep -m1 '\[~\]' "$TASK_QUEUE" 2>/dev/null)
  if [ -n "$ACTIVE" ]; then
    echo "ACTIVE TASK: $ACTIVE"
    # Show the task's details (next few lines after the match)
    grep -A8 '\[~\]' "$TASK_QUEUE" 2>/dev/null | head -10
  else
    NEXT=$(grep -m1 '\[ \]' "$TASK_QUEUE" 2>/dev/null)
    [ -n "$NEXT" ] && echo "NEXT TASK: $NEXT" || echo "All tasks complete."
  fi
else
  echo "No task queue found."
fi

# Pipeline progress
PIPELINE_STATUS=".workflow/pipeline-status.json"
if [ -f "$PIPELINE_STATUS" ] && command -v jq &>/dev/null; then
  CURRENT=$(jq -r '.current_phase // "none"' "$PIPELINE_STATUS")
  COMPLETED=$(jq '[.phases[] | select(.status == "completed")] | length' "$PIPELINE_STATUS")
  TOTAL=$(jq '[.phases[] | select(.status != "skipped")] | length' "$PIPELINE_STATUS")
  echo ""
  echo "PIPELINE: $(jq -r '.pipeline_type' "$PIPELINE_STATUS") | Phase: $CURRENT | Progress: $COMPLETED/$TOTAL"
fi

# Show recent reflections
if [ -f "$REFLEXION" ] && command -v jq &>/dev/null; then
  LESSONS=$(jq -r '.entries[-3:][] | "- " + .lesson' "$REFLEXION" 2>/dev/null)
  if [ -n "$LESSONS" ]; then
    echo ""
    echo "RECENT REFLECTIONS:"
    echo "$LESSONS"
  fi
fi

# Show last chain entry
CHAIN_FILE=".workflow/state-chain/chain.json"
if [ -f "$CHAIN_FILE" ] && command -v jq &>/dev/null; then
  LAST_CHAIN=$(jq -r '.entries[-1] // empty | "LAST CHAIN: seq=" + (.seq|tostring) + " task=" + .task_id + " stage=" + .stage + " agent=" + .agent + " verdict=" + (.verdict // "n/a")' "$CHAIN_FILE" 2>/dev/null)
  if [ -n "$LAST_CHAIN" ]; then
    echo ""
    echo "$LAST_CHAIN"
  fi
fi

echo "======================================="

#!/bin/bash
# SessionStart hook (compact matcher): re-injects workflow state after
# Claude Code compacts the context window. Keeps Claude oriented on
# the current task and recent learnings.

cd "$CLAUDE_PROJECT_DIR" || exit 0

TASK_QUEUE=".workflow/task-queue.md"
REFLEXION=".workflow/reflexion/index.json"
SPECIALIST_SESSION=".workflow/specialist-session.json"

echo "=== WORKFLOW STATE (post-compaction) ==="

if ! command -v jq &>/dev/null; then
  echo "⚠️ jq not installed — reflexion recall disabled. Run .claude/scripts/init.sh"
fi

# Check for active specialist session FIRST (takes priority over task queue)
if [ -f "$SPECIALIST_SESSION" ] && command -v jq &>/dev/null; then
  SPEC_NAME=$(jq -r '.specialist // "unknown"' "$SPECIALIST_SESSION" 2>/dev/null)
  SPEC_FOCUS=$(jq -r '.focus_area // "unknown"' "$SPECIALIST_SESSION" 2>/dev/null)
  SPEC_STATUS=$(jq -r '.status // "unknown"' "$SPECIALIST_SESSION" 2>/dev/null)
  SPEC_DECISIONS=$(jq -r '.draft_decisions // [] | length' "$SPECIALIST_SESSION" 2>/dev/null)
  SPEC_GATE=$(jq -r '.last_gate // "none"' "$SPECIALIST_SESSION" 2>/dev/null)
  echo "╔═══════════════════════════════════════════════════════╗"
  echo "║ SPECIALIST SESSION ACTIVE: /specialists/$SPEC_NAME"
  echo "║ Focus area: $SPEC_FOCUS"
  echo "║ Status: $SPEC_STATUS"
  echo "║ Last gate: $SPEC_GATE"
  echo "║ Draft decisions: $SPEC_DECISIONS"
  echo "╚═══════════════════════════════════════════════════════╝"
  echo ""
  echo "ACTION: Read .workflow/specialist-session.json for full state,"
  echo "then continue the specialist session where it left off."
  echo "Do NOT restart the specialist from the beginning."
  # Show pending questions if any
  PENDING=$(jq -r '.pending_questions // [] | .[]' "$SPECIALIST_SESSION" 2>/dev/null)
  if [ -n "$PENDING" ]; then
    echo ""
    echo "PENDING QUESTIONS (waiting for user):"
    echo "$PENDING"
  fi
fi

# Show active task (if not in specialist session)
if [ ! -f "$SPECIALIST_SESSION" ] && [ -f "$TASK_QUEUE" ]; then
  ACTIVE=$(grep -m1 '\[~\]' "$TASK_QUEUE" 2>/dev/null)
  if [ -n "$ACTIVE" ]; then
    echo "ACTIVE TASK: $ACTIVE"
    # Show the task's details (next few lines after the match)
    grep -A8 '\[~\]' "$TASK_QUEUE" 2>/dev/null | head -10
  else
    # Check if we're in QA Fix Pass
    QA_FIXES=".workflow/qa-fixes.md"
    if [ -f "$QA_FIXES" ]; then
      QA_ACTIVE=$(grep -m1 '\[~\]' "$QA_FIXES" 2>/dev/null)
      if [ -n "$QA_ACTIVE" ]; then
        echo "QA FIX PASS ACTIVE: $QA_ACTIVE"
        grep -A8 '\[~\]' "$QA_FIXES" 2>/dev/null | head -10
      fi
    fi
    if [ -z "$QA_ACTIVE" ]; then
      NEXT=$(grep -m1 '\[ \]' "$TASK_QUEUE" 2>/dev/null)
      [ -n "$NEXT" ] && echo "NEXT TASK: $NEXT" || echo "All tasks complete."
    fi
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

# Multi-LLM review status
ADVISORY_CONFIG=".claude/advisory-config.json"
if [ -f "$ADVISORY_CONFIG" ] && command -v jq &>/dev/null; then
  MLR_ENABLED=$(jq -r '.multi_llm_review.enabled // false' "$ADVISORY_CONFIG" 2>/dev/null)
  if [ "$MLR_ENABLED" = "true" ]; then
    MLR_CONTEXTS=$(jq -r '.multi_llm_review.contexts // [] | join(", ")' "$ADVISORY_CONFIG" 2>/dev/null)
    echo ""
    echo "MULTI-LLM REVIEW: enabled | Contexts: $MLR_CONTEXTS"
  fi
fi

# Advisory skip state
ADVISORY_STATE=".workflow/advisory-state.json"
if [ -f "$ADVISORY_STATE" ] && command -v jq &>/dev/null; then
  SKIP=$(jq -r '.skip_advisories // false' "$ADVISORY_STATE" 2>/dev/null)
  if [ "$SKIP" = "true" ]; then
    echo ""
    echo "ADVISORY: DISABLED by user (skip state persisted)"
  fi
fi

echo "======================================="

#!/bin/bash
# PostToolUse hook: auto-fix style and formatting on file edits.
# Detects which tools are available and applies them. Never blocks.

cd "$CLAUDE_PROJECT_DIR" || exit 0

CHANGED=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // .path // empty' 2>/dev/null)
[ -z "$CHANGED" ] && exit 0
[ ! -f "$CHANGED" ] && exit 0

# ── Python ─────────────────────────────────────────────────────
if [[ "$CHANGED" == *.py ]]; then
  command -v ruff &>/dev/null && ruff check --fix --quiet "$CHANGED" 2>/dev/null
  command -v ruff &>/dev/null && ruff format --quiet "$CHANGED" 2>/dev/null
fi

# ── JavaScript / TypeScript ────────────────────────────────────
if [[ "$CHANGED" =~ \.(js|ts|jsx|tsx)$ ]]; then
  command -v prettier &>/dev/null && prettier --write --log-level silent "$CHANGED" 2>/dev/null
  command -v eslint &>/dev/null && eslint --fix --quiet "$CHANGED" 2>/dev/null
fi

exit 0

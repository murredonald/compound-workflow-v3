#!/bin/bash
# Standalone type-check script. Called by pre-commit-gate.sh.
# Detects Python (mypy) or TypeScript (tsc) based on what's available.

cd "$CLAUDE_PROJECT_DIR" || exit 0

ERRORS=0

# ── Python: mypy ───────────────────────────────────────────────
if command -v mypy &>/dev/null; then
  if [ -f "pyproject.toml" ] || [ -f "mypy.ini" ] || [ -f "setup.cfg" ]; then
    mypy . --no-error-summary 2>&1
    [ $? -ne 0 ] && ERRORS=1
  fi
fi

# ── TypeScript: tsc ────────────────────────────────────────────
if command -v tsc &>/dev/null && [ -f "tsconfig.json" ]; then
  tsc --noEmit 2>&1
  [ $? -ne 0 ] && ERRORS=1
fi

exit $ERRORS

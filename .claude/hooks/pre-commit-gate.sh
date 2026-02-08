#!/bin/bash
# PreToolUse hook: blocks git commit if quality checks fail.
# Exit 2 = block (stderr goes to Claude as feedback). Exit 0 = allow.
# Only runs tools that are actually installed — safe for any project.

cd "$CLAUDE_PROJECT_DIR" || exit 0

ERRORS=""
SKIPPED=""

# ── Lint checking ─────────────────────────────────────────────
if [ -f "pyproject.toml" ] && ! command -v ruff &>/dev/null; then
  SKIPPED+="⚠️ ruff not installed — lint/format check skipped\n"
fi
if command -v ruff &>/dev/null && [ -f "pyproject.toml" ]; then
  if ! ruff check --quiet . 2>/dev/null; then
    ERRORS+="• ruff: Lint issues found (not auto-fixable).\n"
  fi
fi
if command -v eslint &>/dev/null && [ -f "package.json" ]; then
  if ! eslint --quiet . 2>/dev/null; then
    ERRORS+="• eslint: Lint issues found.\n"
  fi
fi

# ── Type checking ──────────────────────────────────────────────
if ! "$CLAUDE_PROJECT_DIR/.claude/hooks/type-check.sh" >/dev/null 2>&1; then
  ERRORS+="• Type errors found. Run type-check manually for details.\n"
fi

# ── Python: security scan ─────────────────────────────────────
if [ -d "src" ] && ! command -v bandit &>/dev/null; then
  SKIPPED+="⚠️ bandit not installed — security scan skipped\n"
fi
if command -v bandit &>/dev/null && [ -d "src" ]; then
  if ! bandit -r src/ -q -ll 2>/dev/null; then
    ERRORS+="• bandit: Security issues found (medium+ severity).\n"
  fi
fi

# ── Secret scanning ──────────────────────────────────────────
if command -v gitleaks &>/dev/null; then
  if ! gitleaks protect --staged --no-banner -q 2>/dev/null; then
    ERRORS+="• gitleaks: Secrets detected in staged files.\n"
  fi
else
  SKIPPED+="⚠️ gitleaks not installed — secret scanning skipped\n"
fi

# ── Dependency vulnerability scanning ────────────────────────
if command -v pip-audit &>/dev/null && [ -f "requirements.txt" -o -f "pyproject.toml" ]; then
  if ! pip-audit --strict --progress-spinner off -q 2>/dev/null; then
    ERRORS+="• pip-audit: Known vulnerabilities in Python dependencies.\n"
  fi
fi
if command -v npm &>/dev/null && [ -f "package-lock.json" ]; then
  AUDIT_OUTPUT=$(npm audit --audit-level=high 2>/dev/null || true)
  if echo "$AUDIT_OUTPUT" | grep -qE "high|critical"; then
    ERRORS+="• npm audit: High/critical vulnerabilities in Node dependencies.\n"
  fi
fi

# ── Python: tests ─────────────────────────────────────────────
if [ -d "tests" ] && ! command -v pytest &>/dev/null; then
  SKIPPED+="⚠️ pytest not installed — test gate skipped\n"
fi
if command -v pytest &>/dev/null && [ -d "tests" ]; then
  if ! pytest tests/ -q --tb=line 2>/dev/null; then
    ERRORS+="• pytest: Tests are failing.\n"
  fi
fi

# ── JS/TS: tests ──────────────────────────────────────────────
if [ -f "package.json" ]; then
  if command -v npx &>/dev/null; then
    if grep -q '"test"' package.json 2>/dev/null; then
      if ! npm test --silent 2>/dev/null; then
        ERRORS+="• npm test: Tests are failing.\n"
      fi
    fi
  fi
fi

# ── Verdict ────────────────────────────────────────────────────
if [ -n "$SKIPPED" ]; then
  echo -e "$SKIPPED" >&2
  echo "Run .claude/scripts/init.sh to install missing tools." >&2
  echo "" >&2
fi

if [ -n "$ERRORS" ]; then
  echo "╔══════════════════════════════════════╗" >&2
  echo "║     PRE-COMMIT GATE: BLOCKED         ║" >&2
  echo "╚══════════════════════════════════════╝" >&2
  echo -e "$ERRORS" >&2
  echo "" >&2
  echo "Recovery hints:" >&2
  echo "  • Lint issues → run: ruff check --fix . && ruff format ." >&2
  echo "  • Type errors → fix type annotations, then re-run commit" >&2
  echo "  • Test failures → run: pytest tests/ -v --tb=short" >&2
  echo "  • Security issues → run: bandit -r src/ -ll for details" >&2
  echo "  • Secrets detected → remove secrets, use .env files (gitignored)" >&2
  echo "  • Dependency vulns → run: pip-audit --fix or npm audit fix" >&2
  exit 2
fi

exit 0

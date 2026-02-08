#!/bin/bash
# Compound Workflow v3 — Project Initialization
# Usage: ./init.sh [remote-url]
# Example: ./init.sh https://github.com/user/repo.git

set -euo pipefail

REMOTE_URL="${1:-}"
PASS=0
WARN=0
FAIL=0

pass() { echo "  [OK] $1"; ((PASS++)) || true; }
warn() { echo "  [!!] $1"; ((WARN++)) || true; }
fail() { echo "  [XX] $1"; ((FAIL++)) || true; }

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Compound Workflow v3 — Project Init"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── 1. Git ────────────────────────────────────────────────────
echo "Git:"
if command -v git &>/dev/null; then
  pass "git installed ($(git --version | head -1))"
else
  fail "git not found — install Git for Windows: https://git-scm.com"
fi

if [ -d .git ]; then
  pass "already a git repository"
else
  if command -v git &>/dev/null; then
    git init -q
    pass "git init — repository created"
  else
    fail "cannot init repo — git not installed"
  fi
fi

if [ -n "$REMOTE_URL" ]; then
  if git remote get-url origin &>/dev/null; then
    EXISTING=$(git remote get-url origin)
    if [ "$EXISTING" = "$REMOTE_URL" ]; then
      pass "remote origin already set to $REMOTE_URL"
    else
      warn "remote origin exists ($EXISTING) — not overwriting. Remove with: git remote remove origin"
    fi
  else
    git remote add origin "$REMOTE_URL"
    pass "remote origin set to $REMOTE_URL"
  fi
else
  if git remote get-url origin &>/dev/null; then
    pass "remote origin: $(git remote get-url origin)"
  else
    warn "no remote configured — push will fail. Re-run with: ./init.sh <remote-url>"
  fi
fi

# Set upstream tracking if remote exists and branch has commits
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$BRANCH" ] && git remote get-url origin &>/dev/null; then
  if ! git config "branch.${BRANCH}.remote" &>/dev/null; then
    if git rev-parse HEAD &>/dev/null 2>&1; then
      git push -u origin "$BRANCH" 2>&1 && pass "upstream set: origin/$BRANCH" || warn "initial push failed — check remote auth"
    else
      warn "no commits yet — upstream will be set on first push"
    fi
  else
    pass "upstream tracking: origin/$BRANCH"
  fi
fi

echo ""

# ── 2. .gitignore ─────────────────────────────────────────────
echo ".gitignore:"
if [ -f .gitignore ]; then
  pass "already exists"
else
  cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage

# Node
node_modules/
.next/

# Environment / Secrets
.env
.env.local
.env.*.local
.claude/.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Workflow runtime state (created by /plan — not part of template)
# Uncomment the line below if you want to EXCLUDE workflow state from git.
# By default, .workflow/ IS tracked so your decisions and specs are versioned.
# .workflow/
GITIGNORE
  pass "created with Python + Node defaults"
fi

echo ""

# ── 3. Python environment ─────────────────────────────────────
echo "Python:"
PYTHON=""
# On Windows, python3 may be a broken Store alias — try python first
if command -v python &>/dev/null; then
  PY_VER=$(python --version 2>&1)
  if echo "$PY_VER" | grep -q "Python 3\."; then
    pass "python found ($PY_VER)"
    PYTHON=python
  fi
fi
if [ -z "$PYTHON" ] && command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version 2>&1)
  if echo "$PY_VER" | grep -q "Python 3\."; then
    pass "python3 found ($PY_VER)"
    PYTHON=python3
  fi
fi
if [ -z "$PYTHON" ]; then
  fail "python not found — install Python 3.11+"
fi

if [ -n "${PYTHON:-}" ] && [ -f pyproject.toml ]; then
  VENV_OK=false
  if [ -d .venv ]; then
    # Verify venv Python is functional (catches broken symlinks from removed interpreters)
    VENV_PY=""
    if [ -f .venv/Scripts/python.exe ]; then
      VENV_PY=".venv/Scripts/python.exe"
    elif [ -f .venv/bin/python ]; then
      VENV_PY=".venv/bin/python"
    fi
    if [ -n "$VENV_PY" ] && "$VENV_PY" --version &>/dev/null; then
      pass "venv OK at .venv/ ($("$VENV_PY" --version 2>&1))"
      VENV_OK=true
    else
      warn "venv at .venv/ is broken (Python interpreter missing) — recreating"
      rm -rf .venv
    fi
  fi
  if [ "$VENV_OK" = "false" ]; then
    $PYTHON -m venv .venv
    pass "venv created at .venv/"
  fi

  # Activate and install dev tools
  if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
  elif [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
  fi

  echo ""
  echo "Dev tools:"
  $PYTHON -m pip install --quiet --upgrade pip 2>/dev/null || true

  # App dev tools (linting, typing, security, testing)
  for tool in ruff mypy bandit pytest; do
    if command -v $tool &>/dev/null; then
      pass "$tool already installed"
    else
      if $PYTHON -m pip install --quiet "$tool" 2>/dev/null; then
        pass "$tool installed"
      else
        fail "$tool install failed"
      fi
    fi
  done

  # AI layer dependencies (advisory system + Playwright)
  if [ -f .claude/requirements.txt ]; then
    if $PYTHON -m pip install --quiet -r .claude/requirements.txt 2>/dev/null; then
      pass "AI layer deps installed (.claude/requirements.txt)"
    else
      warn "AI layer deps install failed — advisory system may be unavailable"
    fi
  else
    warn "no .claude/requirements.txt — AI advisory deps not installed"
  fi

  # Playwright browser (Chromium) for JS-rendered site scraping
  if $PYTHON -m playwright install chromium 2>/dev/null; then
    pass "Playwright Chromium browser installed"
  else
    warn "Playwright Chromium install failed — JS-rendered site scraping unavailable"
  fi
elif [ -n "${PYTHON:-}" ]; then
  warn "no pyproject.toml — skipping venv and dev tools"
fi

echo ""

# ── 4. jq (required by hooks) ─────────────────────────────────
echo "System tools:"
if command -v jq &>/dev/null; then
  pass "jq installed ($(jq --version 2>&1))"
else
  fail "jq not found — on-compact.sh and scope-guard.sh will be disabled"
  echo "       Install: https://jqlang.github.io/jq/download/"
  echo "       Windows: winget install jqlang.jq"
  echo "       macOS:   brew install jq"
  echo "       Linux:   apt install jq"
fi

if command -v bash &>/dev/null; then
  pass "bash available"
else
  fail "bash not found — hooks will not run"
fi

echo ""

# ── 5. Advisory system (.claude/.env) ─────────────────────────
echo "Advisory (cross-model):"
if [ -f .claude/.env ]; then
  if grep -q "OPENAI_API_KEY=." .claude/.env 2>/dev/null; then
    pass ".claude/.env found with OPENAI_API_KEY"
  else
    warn ".claude/.env exists but OPENAI_API_KEY not set — GPT advisory will be unavailable"
  fi
  if grep -q "GEMINI_API_KEY=." .claude/.env 2>/dev/null; then
    pass ".claude/.env found with GEMINI_API_KEY"
  else
    warn ".claude/.env exists but GEMINI_API_KEY not set — Gemini advisory will be unavailable"
  fi
else
  warn "no .claude/.env file — GPT and Gemini advisory will be unavailable (Claude advisory still works)"
fi

if [ -f .claude/advisory-config.json ]; then
  pass "advisory-config.json found"
else
  warn "no .claude/advisory-config.json — all advisors will be treated as enabled"
fi

echo ""

# ── 6. Workflow state ──────────────────────────────────────────
echo "Workflow state:"
for f in .workflow/project-spec.md .workflow/decisions.md .workflow/constraints.md; do
  if [ -f "$f" ]; then
    pass "$f exists"
  else
    warn "$f missing — run /plan first"
  fi
done

for f in .workflow/reflexion/index.json .workflow/reflexion/process-learnings.md .workflow/evals/task-evals.json .workflow/deferred-findings.md; do
  if [ -f "$f" ]; then
    pass "$f exists"
  else
    warn "$f missing — will be created by /synthesize"
  fi
done

if [ -f ".workflow/state-chain/chain.json" ]; then
  pass ".workflow/state-chain/chain.json exists"
else
  warn ".workflow/state-chain/chain.json missing — will be created on first chain recording"
fi

# Post-v1 evolution files
for f in .workflow/observations.md .workflow/backlog.md; do
  if [ -f "$f" ]; then
    pass "$f exists"
  else
    warn "$f missing — will be created when post-v1 workflow starts"
  fi
done

# Screenshots directory
if [ -d "docs/screenshots" ]; then
  pass "docs/screenshots/ exists"
else
  mkdir -p docs/screenshots
  pass "docs/screenshots/ created"
fi

echo ""

# ── Summary ───────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
echo "  Results: $PASS passed, $WARN warnings, $FAIL failures"
echo "═══════════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "  Fix failures above before running /execute."
  echo "  Warnings are non-blocking but may reduce quality gate coverage."
  exit 1
fi

if [ "$WARN" -gt 0 ]; then
  echo ""
  echo "  Ready with warnings. Some quality gates may be reduced."
  exit 0
fi

echo ""
echo "  Ready to go. Run /plan or /execute."
exit 0

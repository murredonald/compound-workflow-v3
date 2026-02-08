"""Cross-model advisory perspective for Compound Workflow v3.

Calls external LLM APIs (OpenAI, Google Gemini) to provide an independent
second opinion on specialist/planning questions. Designed to complement the
Claude-based second-opinion-advisor subagent with genuine model diversity.

Supports orthogonal multi-answer mode: each model produces N genuinely
different perspectives per question set (not forced contrarian).

Usage:
    # Planning mode (default)
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json
    python .claude/tools/second_opinion.py --provider gemini --context-file ctx.json
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json --answers 3

    # Code review mode
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json --mode code-review

    # Test diagnosis mode
    python .claude/tools/second_opinion.py --provider gemini --context-file ctx.json --mode diagnosis

    # Debugging mode
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json --mode debugging

    # Custom model override
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json --model gpt-4o
    python .claude/tools/second_opinion.py --provider gemini --context-file ctx.json --model gemini-2.0-flash

Context JSON format (planning mode):
    {
        "project_spec": "...",
        "decisions": "...",
        "constraints": "...",
        "specialist_domain": "architecture",
        "focus_area": "Infrastructure Decisions",
        "specialist_analysis": "...",
        "questions": ["Q1...", "Q2...", "Q3..."]
    }

Context JSON format (code-review mode):
    {
        "task_id": "T05",
        "task_definition": "...",
        "git_diff": "...",
        "decisions": "...",
        "constraints": "..."
    }

Context JSON format (diagnosis mode):
    {
        "test_output": "...",
        "task_context": "...",
        "recent_changes": "...",
        "failure_categories": "..."
    }

Context JSON format (debugging mode):
    {
        "bug_description": "...",
        "reproduction_steps": "...",
        "current_hypotheses": "..."
    }
"""

from __future__ import annotations

import argparse
import json
import sys
import time

# Fix Windows console encoding (cp1252 can't handle Unicode from LLM responses)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from typing import Any

SYSTEM_PROMPT_SINGLE = """\
You are a senior technical advisor providing an independent perspective on
software architecture and planning questions. You bring deep expertise and
give SPECIFIC, ACTIONABLE advice grounded in real technologies, patterns,
and domain knowledge.

You are NOT a contrarian. You simply answer questions from a fresh viewpoint,
based only on the project context provided.

## Quality Standards — CRITICAL

Your advice must be CONCRETE and TECHNICAL. Avoid generic platitudes.

BAD (too generic): "Consider using a database that fits your needs."
GOOD (specific): "Use PostgreSQL with JSONB columns for flexible metadata —
it avoids a separate document store while keeping ACID transactions for
financial data, which simplifies deployment for a solo developer."

BAD: "Ensure proper error handling for edge cases."
GOOD: "When the external API returns a 429, implement exponential backoff
with jitter starting at 1s, capped at 60s — store retry state in a Redis
key with TTL matching the Retry-After header."

## Rules
- For each question, provide your perspective in 4-6 sentences with SPECIFIC
  technical recommendations.
- Name specific technologies, libraries, patterns, data structures, or approaches.
- Ground your responses in the project's specific context and domain.
- Reference decision IDs (GEN-XX, ARCH-XX, etc.) when relevant.
- Do NOT repeat the specialist's analysis — add to it with NEW insights.
- If you have domain knowledge relevant to the project (e.g., fintech
  regulations, healthcare compliance, domain-specific algorithms), bring it.
- Flag risks or considerations the specialist's framing might underweight.
- Keep total output under 500 words.

Output format:
### Advisory Perspective: {focus_area}

**Q1: {question text}**
{Your perspective — specific, technical, actionable}

**Q2: {question text}**
{Your perspective — specific, technical, actionable}

(Continue for all questions)
"""

SYSTEM_PROMPT_ORTHOGONAL = """\
You are a senior technical advisor providing independent perspectives on
software architecture and planning questions. You bring deep expertise and
give SPECIFIC, ACTIONABLE advice grounded in real technologies, patterns,
and domain knowledge.

You will produce {N} genuinely different perspectives for each question.
Think of each perspective as viewing the problem through a different lens.
All perspectives must be independently useful and defensible.

## Quality Standards — CRITICAL

Every perspective must be CONCRETE and TECHNICAL. Avoid generic platitudes.
Each perspective should name specific technologies, patterns, data structures,
or architectural approaches. If you have domain knowledge relevant to the
project (e.g., fintech regulations, healthcare compliance, domain-specific
algorithms, industry standards), bring it.

BAD (too generic): "Consider the user's needs when designing the output."
GOOD (specific): "Use a write-ahead pattern where mutations go through a
command queue — this gives you exactly-once semantics via idempotency keys
and lets you replay failed operations, which matters when your workflow
involves external payment providers."

## Perspective Approach
- Perspective A: Your primary recommendation — the approach you'd champion if
  you were the architect. Be specific about WHY, citing concrete trade-offs.
- Perspective B: A genuinely different valid approach — what a smart colleague
  with different experience might propose. Not a weaker version of A.
- Perspective C: The angle most likely being overlooked — the hidden assumption,
  the scaling trap, the domain-specific gotcha, the user behavior that breaks
  the design. This should make the reader think "I hadn't considered that."

## Rules
- For each question, provide {N} distinct perspectives, each 3-5 sentences.
- Every perspective must contain at least one SPECIFIC technical recommendation
  (a named technology, pattern, data structure, or concrete approach).
- Ground every perspective in the project's specific context and domain.
- Reference decision IDs (GEN-XX, ARCH-XX, etc.) when relevant.
- Do NOT repeat the specialist's analysis — add genuinely NEW insights.
- Each perspective must offer a substantially different insight, not a rephrase.
- If two perspectives converge, find a third angle instead.
- Keep total output under {word_limit} words.

Output format:
### Advisory Perspectives: {{focus_area}}

**Q1: {{question text}}**

*Perspective A:* {{specific, technical, actionable — name technologies/patterns}}

*Perspective B:* {{genuinely different approach — specific, not a weaker version of A}}

*Perspective C:* {{the overlooked angle — domain gotcha, hidden assumption, scaling trap}}

**Q2: {{question text}}**

*Perspective A:* {{...}}

*Perspective B:* {{...}}

*Perspective C:* {{...}}

(Continue for all questions, {N} perspectives each)
"""


SYSTEM_PROMPT_CODE_REVIEW = """\
You are a senior code reviewer providing an independent review of a code diff.
You find real issues — bugs, security vulnerabilities, logic errors, performance
problems, and style violations. You cite specific file:line locations for every
finding.

## Quality Standards — CRITICAL

Every finding must be SPECIFIC and cite a file:line location. Avoid vague
observations.

BAD (too vague): "Error handling could be improved."
GOOD (specific): "BUG at api/routes.py:42 — `user_id` is cast to int without
try/except, so a non-numeric path parameter returns a 500 instead of 422."

BAD: "Consider adding input validation."
GOOD: "SECURITY at auth/login.py:28 — password field is logged at DEBUG level
via `logger.debug(f'Login attempt: {request.body}')`, leaking credentials
to log aggregation."

## Rules
- Classify each finding: BUG | SECURITY | PERFORMANCE | LOGIC | STYLE
- Assign severity: CRITICAL | MAJOR | MINOR
- Cite file:line for every finding — no exceptions
- Focus on the diff provided — don't speculate about code you can't see
- If the diff looks clean, say so — don't invent issues for completeness
- Keep total output under 800 words

Output format:
### Code Review: {task_id}

**Finding 1: [{severity}] [{category}] {brief title}**
Location: {file}:{line}
Issue: {what's wrong — specific, technical}
Suggestion: {how to fix — specific}

**Finding 2: ...**

### Summary
- Total findings: {N} (Critical: {N}, Major: {N}, Minor: {N})
- Verdict: CLEAN | CONCERNS | ISSUES
"""

SYSTEM_PROMPT_DIAGNOSIS = """\
You are a senior test diagnostician analyzing test failures. You categorize
failures by root cause, identify patterns, and provide specific diagnosis
with file:line citations.

## Quality Standards — CRITICAL

Every diagnosis must identify the specific root cause location and category.
Avoid generic "something went wrong" analyses.

BAD (too vague): "The test is failing because of a data issue."
GOOD (specific): "CODE_BUG — `calculate_tax()` in tax/engine.py:87 returns
float instead of Decimal, causing assertion mismatch in test_tax_calc:23
where expected=Decimal('19.99') but got=19.990000000000002."

BAD: "Test environment might need updating."
GOOD: "ENV_ISSUE — test_integration:45 expects Redis on localhost:6379 but
the CI fixture uses port 6380 (see conftest.py:12). The test passes locally
because the developer's Redis runs on the default port."

## Failure Categories
- **CODE_BUG** — Implementation has a real bug
- **TEST_BUG** — Test itself is wrong (bad assertion, wrong fixture, stale mock)
- **MISSING_IMPL** — Test expects something not yet implemented
- **ENV_ISSUE** — Missing dependency, config, or service
- **FLAKY** — Non-deterministic failure (timing, ordering, randomness)

## Rules
- Categorize every failure with one of the categories above
- Cite test name, test file:line, and likely source file:line
- Identify patterns across failures (e.g., "3 failures all trace to same missing import")
- If you see test output, analyze the actual error messages — don't guess
- Keep total output under 800 words

Output format:
### Test Diagnosis: {task_context}

**Failure 1: [{category}] {test_name}**
Test: {test_file}:{line}
Error: {one-line error summary}
Root cause: {source_file}:{line} — {what's wrong}
Suggested fix: {specific action}

**Failure 2: ...**

### Pattern Analysis
{Any cross-cutting patterns across failures}

### Priority Order
1. {most impactful fix first — with reason}
2. {next}
"""

SYSTEM_PROMPT_DEBUGGING = """\
You are a senior debugging advisor generating alternative hypotheses for
a bug. You think laterally — considering root causes that the primary
debugger might overlook.

## Quality Standards — CRITICAL

Every hypothesis must include a specific location to check and a concrete
test method. Avoid hand-wavy suggestions.

BAD (too vague): "Maybe it's a race condition somewhere."
GOOD (specific): "H2: The WebSocket handler in ws/handler.py:34 reads
`session.user_id` without acquiring the session lock. If two messages arrive
within the same event loop tick, the second overwrites the first's context.
Test: Add `asyncio.sleep(0)` between two concurrent `send()` calls in the
test and check if the response contains the wrong user's data."

BAD: "Check the database queries."
GOOD: "H3: The N+1 query in reports/generator.py:78 (`for item in items:
    item.category.name`) triggers a lazy load per row. With 500+ items, the
DB connection pool (max 10, see config.py:23) exhausts, causing the timeout
observed in the bug report. Test: Run with `SQLALCHEMY_ECHO=1` and count
queries — should be 2 (items + categories), not 502."

## Rules
- Generate 2-4 hypotheses, ranked by likelihood
- Each hypothesis: specific location (file:line), mechanism, and test method
- Think orthogonally — don't just rephrase the primary debugger's hypotheses
- Consider: timing issues, state corruption, config drift, dependency version
  skew, encoding issues, platform differences, caching staleness
- If existing hypotheses are provided, propose DIFFERENT angles
- Keep total output under 600 words

Output format:
### Debugging Hypotheses: {bug_description}

**H1 (likely): {title}**
Location: {file}:{line}
Mechanism: {how the bug manifests}
Test method: {specific way to confirm or eliminate}

**H2 (possible): {title}**
Location: {file}:{line}
Mechanism: {how the bug manifests}
Test method: {specific way to confirm or eliminate}

**H3 (unlikely but check): {title}**
...
"""

MODE_PROMPTS: dict[str, str] = {
    "planning": "",  # sentinel — uses get_system_prompt() instead
    "code-review": SYSTEM_PROMPT_CODE_REVIEW,
    "diagnosis": SYSTEM_PROMPT_DIAGNOSIS,
    "debugging": SYSTEM_PROMPT_DEBUGGING,
}


def get_system_prompt(answers: int = 1) -> str:
    """Return the appropriate system prompt based on answer count."""
    if answers <= 1:
        return SYSTEM_PROMPT_SINGLE
    word_limit = answers * 350
    return SYSTEM_PROMPT_ORTHOGONAL.replace("{N}", str(answers)).replace(
        "{word_limit}", str(word_limit)
    )

PROVIDER_DEFAULTS: dict[str, str] = {
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
}


def load_advisory_config() -> dict[str, Any]:
    """Load advisory-config.json to get configured models."""
    config_path = Path(".claude/advisory-config.json")
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_configured_model(provider: str) -> str | None:
    """Get the model configured in advisory-config.json for a provider."""
    config = load_advisory_config()
    advisors = config.get("advisors", {})
    provider_key = "gpt" if provider == "openai" else provider
    provider_config = advisors.get(provider_key, {})
    return provider_config.get("model")


API_KEY_NAMES: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def load_env(env_path: Path | None = None) -> dict[str, str]:
    """Load environment variables from .env file using stdlib only."""
    if env_path is None:
        env_path = Path(".claude/.env")
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
    return env_vars


def build_user_message(context: dict[str, Any]) -> str:
    """Build the user message from the context JSON."""
    parts: list[str] = []

    parts.append(f"## Project Specification\n{context.get('project_spec', 'N/A')}")
    parts.append(f"## Current Decisions\n{context.get('decisions', 'N/A')}")
    parts.append(f"## Constraints\n{context.get('constraints', 'N/A')}")
    parts.append(f"## Specialist Domain: {context.get('specialist_domain', 'N/A')}")
    parts.append(f"## Focus Area: {context.get('focus_area', 'N/A')}")
    parts.append(
        f"## Specialist Analysis\n{context.get('specialist_analysis', 'N/A')}"
    )

    questions = context.get("questions", [])
    if isinstance(questions, list):
        q_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    else:
        q_text = str(questions)
    parts.append(f"## Questions\n{q_text}")

    return "\n\n".join(parts)


def build_code_review_message(context: dict[str, Any]) -> str:
    """Build the user message for code-review mode."""
    parts: list[str] = []

    parts.append(f"## Task: {context.get('task_id', 'N/A')}")
    parts.append(f"## Task Definition\n{context.get('task_definition', 'N/A')}")
    parts.append(f"## Git Diff\n```\n{context.get('git_diff', 'N/A')}\n```")

    if context.get("decisions"):
        parts.append(f"## Relevant Decisions\n{context['decisions']}")
    if context.get("constraints"):
        parts.append(f"## Constraints\n{context['constraints']}")

    return "\n\n".join(parts)


def build_diagnosis_message(context: dict[str, Any]) -> str:
    """Build the user message for diagnosis mode."""
    parts: list[str] = []

    parts.append(f"## Test Output\n```\n{context.get('test_output', 'N/A')}\n```")
    parts.append(f"## Task Context\n{context.get('task_context', 'N/A')}")

    if context.get("recent_changes"):
        parts.append(f"## Recent Changes\n{context['recent_changes']}")
    if context.get("failure_categories"):
        parts.append(f"## Initial Categorization\n{context['failure_categories']}")

    return "\n\n".join(parts)


def build_debugging_message(context: dict[str, Any]) -> str:
    """Build the user message for debugging mode."""
    parts: list[str] = []

    parts.append(f"## Bug Description\n{context.get('bug_description', 'N/A')}")

    if context.get("reproduction_steps"):
        parts.append(f"## Reproduction Steps\n{context['reproduction_steps']}")
    if context.get("current_hypotheses"):
        parts.append(f"## Current Hypotheses\n{context['current_hypotheses']}")

    return "\n\n".join(parts)


MESSAGE_BUILDERS: dict[str, Any] = {
    "planning": build_user_message,
    "code-review": build_code_review_message,
    "diagnosis": build_diagnosis_message,
    "debugging": build_debugging_message,
}


def resolve_api_key(
    provider: str,
    env_vars: dict[str, str],
) -> str:
    """Resolve the API key for a provider from env vars or os.environ."""
    key_name = API_KEY_NAMES[provider]
    api_key = env_vars.get(key_name, "")
    if not api_key:
        import os

        api_key = os.environ.get(key_name, "")
    if not api_key:
        print(
            f"Error: {key_name} not found in .claude/.env or environment variables",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key


def call_openai(
    api_key: str,
    user_message: str,
    model: str = "gpt-4o",
    timeout: int = 90,
    system_prompt: str | None = None,
) -> str:
    """Call OpenAI chat completions API."""
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError:
        print(
            "Error: openai package not installed. Run: pip install openai",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT_SINGLE
    client = OpenAI(api_key=api_key, timeout=timeout)
    # Newer models (gpt-4.1+, gpt-5+, o-series) use max_completion_tokens
    # Older models (gpt-4o, gpt-4-turbo) use max_tokens
    newer_model = any(
        model.startswith(p) for p in ("gpt-4.1", "gpt-5", "o1", "o3", "o4")
    )
    token_param = (
        {"max_completion_tokens": 4000}
        if newer_model
        else {"max_tokens": 4000}
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        **token_param,
    )
    content = response.choices[0].message.content
    if content is None:
        return ""
    return content.strip()


def call_gemini(
    api_key: str,
    user_message: str,
    model: str = "gemini-2.0-flash",
    system_prompt: str | None = None,
) -> str:
    """Call Google Gemini API via the google-genai SDK."""
    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]
    except ImportError:
        print(
            "Error: google-genai package not installed. "
            "Run: pip install google-genai",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT_SINGLE
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=prompt,
            temperature=0.7,
            max_output_tokens=4000,
        ),
    )
    if response.text is None:
        return ""
    return response.text.strip()


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Cross-model advisory perspective for workflow specialists",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default="openai",
        help="LLM provider to use (default: openai)",
    )
    parser.add_argument(
        "--context-file",
        required=True,
        type=Path,
        help="Path to JSON file with specialist context",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use (default: provider-specific — gpt-4o / gemini-2.0-flash)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Path to .env file (default: .claude/.env in current directory)",
    )
    parser.add_argument(
        "--answers",
        type=int,
        default=1,
        help="Number of orthogonal perspectives per question (default: 1). "
        "When >1, uses orthogonal thinking prompt for diverse answers. "
        "Only applies to planning mode.",
    )
    parser.add_argument(
        "--mode",
        choices=["planning", "code-review", "diagnosis", "debugging"],
        default="planning",
        help="Review mode (default: planning). "
        "code-review: reviews git diff for issues. "
        "diagnosis: diagnoses test failures. "
        "debugging: generates alternative hypotheses.",
    )
    return parser


def main() -> None:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Load context
    if not args.context_file.exists():
        print(f"Error: context file not found: {args.context_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.context_file, "r", encoding="utf-8") as f:
        context = json.load(f)

    # Resolve model: CLI flag > advisory-config.json > hardcoded default
    model = args.model or get_configured_model(args.provider) or PROVIDER_DEFAULTS[args.provider]

    # Load API key
    env_vars = load_env(args.env_file)
    api_key = resolve_api_key(args.provider, env_vars)

    # Build message using mode-appropriate builder
    builder = MESSAGE_BUILDERS[args.mode]
    user_message = builder(context)

    # Select system prompt: planning mode uses get_system_prompt (answers-aware),
    # other modes use their fixed prompt from MODE_PROMPTS
    if args.mode == "planning":
        system_prompt = get_system_prompt(args.answers)
    else:
        system_prompt = MODE_PROMPTS[args.mode]

    # Retry once after 5s on transient failures (as documented in CLAUDE.md)
    max_attempts = 2
    result = ""
    for attempt in range(1, max_attempts + 1):
        try:
            if args.provider == "openai":
                result = call_openai(
                    api_key=api_key,
                    user_message=user_message,
                    model=model,
                    system_prompt=system_prompt,
                )
            else:
                result = call_gemini(
                    api_key=api_key,
                    user_message=user_message,
                    model=model,
                    system_prompt=system_prompt,
                )
            break  # Success — exit retry loop
        except Exception as e:
            if attempt < max_attempts:
                print(
                    f"Warning: {args.provider} API call failed (attempt {attempt}/{max_attempts}): {e}",
                    file=sys.stderr,
                )
                print("Retrying in 5 seconds...", file=sys.stderr)
                time.sleep(5)
            else:
                print(
                    f"Error: {args.provider} API failed after {max_attempts} attempts: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()

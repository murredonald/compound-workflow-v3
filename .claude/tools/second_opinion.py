"""Cross-model advisory perspective for Compound Workflow v3.

Calls external LLM APIs (OpenAI, Google Gemini) to provide an independent
second opinion on specialist/planning questions. Designed to complement the
Claude-based second-opinion-advisor subagent with genuine model diversity.

Supports orthogonal multi-answer mode: each model produces N genuinely
different perspectives per question set (not forced contrarian).

Usage:
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json
    python .claude/tools/second_opinion.py --provider gemini --context-file ctx.json
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json --answers 3
    python .claude/tools/second_opinion.py --provider openai --context-file ctx.json --model gpt-4o
    python .claude/tools/second_opinion.py --provider gemini --context-file ctx.json --model gemini-2.0-flash

Context JSON format:
    {
        "project_spec": "...",
        "decisions": "...",
        "constraints": "...",
        "specialist_domain": "architecture",
        "focus_area": "Infrastructure Decisions",
        "specialist_analysis": "...",
        "questions": ["Q1...", "Q2...", "Q3..."]
    }
"""

from __future__ import annotations

import argparse
import json
import sys
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
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=4000,
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
        "When >1, uses orthogonal thinking prompt for diverse answers.",
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

    # Build message and call API
    user_message = build_user_message(context)
    system_prompt = get_system_prompt(args.answers)

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
    except Exception as e:
        print(f"Error calling {args.provider} API: {e}", file=sys.stderr)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()

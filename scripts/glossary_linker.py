#!/usr/bin/env python3
"""
Glossary Linker — insert contextual glossary links into blog posts and glossary items.

Rules:
- First mention only per term per file
- 3-7 links per 1000 words target
- Longest match first
- No links in: frontmatter, code blocks, headings, existing links, images, imports, HTML attrs
- No self-links in glossary items
- Locale-aware (link to same locale as source)
- Context-sensitive terms need AI/ML context nearby
- No links to draft terms (all published now, but check anyway)

Usage:
    python scripts/glossary_linker.py                          # Dry run all
    python scripts/glossary_linker.py --apply                  # Apply to all
    python scripts/glossary_linker.py --apply --blogs-only     # Only blog posts
    python scripts/glossary_linker.py --apply --glossary-only  # Only glossary cross-links
    python scripts/glossary_linker.py --file blog/wat-is-rag-en.mdx --apply
"""

import argparse
import io
import os
import re
import sys
from dataclasses import dataclass, field

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
BLOG_DIR = "website/src/content/blog"
LOCALES = ["en", "nl", "fr", "de"]


@dataclass
class GlossaryTerm:
    slug: str
    term: str  # display name per locale
    locale: str
    category: str
    synonyms: list[str] = field(default_factory=list)
    is_draft: bool = False


def load_terms() -> dict[str, list[GlossaryTerm]]:
    """Load all glossary terms grouped by locale."""
    terms: dict[str, list[GlossaryTerm]] = {loc: [] for loc in LOCALES}

    for f in sorted(os.listdir(GLOSSARY_DIR)):
        if not f.endswith(".mdx"):
            continue
        locale = None
        for loc in LOCALES:
            if f.endswith(f"-{loc}.mdx"):
                locale = loc
                break
        if not locale:
            continue

        slug = f[: -len(f"-{locale}.mdx")]
        fpath = os.path.join(GLOSSARY_DIR, f)
        with open(fpath, encoding="utf-8") as fh:
            content = fh.read()

        fm = content.split("---")[1] if "---" in content else ""
        term_match = re.search(r'term:\s*"([^"]+)"', fm)
        cat_match = re.search(r'category:\s*"([^"]+)"', fm)
        syn_match = re.search(r'synonyms:\s*\[([^\]]*)\]', fm)
        draft = "draft: true" in fm

        term_name = term_match.group(1) if term_match else slug
        category = cat_match.group(1) if cat_match else ""
        synonyms = []
        if syn_match:
            synonyms = [s.strip().strip('"').strip("'") for s in syn_match.group(1).split(",") if s.strip()]

        terms[locale].append(GlossaryTerm(
            slug=slug, term=term_name, locale=locale,
            category=category, synonyms=synonyms, is_draft=draft,
        ))

    return terms


# Context-sensitive terms that need AI/ML words nearby
CONTEXT_SENSITIVE = {
    "temperature": ["llm", "model", "sampling", "generation", "ai", "gpt", "token"],
    "prompt": ["llm", "ai", "model", "chatgpt", "gpt", "generation", "language"],
    "pruning": ["model", "neural", "network", "weights", "parameters", "layer"],
    "attention": ["transformer", "self-attention", "multi-head", "mechanism", "layer"],
    "inference": ["model", "ai", "neural", "llm", "prediction", "latency"],
    "distillation": ["knowledge", "model", "teacher", "student", "neural"],
}

# Terms where bare single-word matching is too aggressive
COMPOUND_ONLY = {"semantic", "vector", "dense", "sparse", "hybrid"}


def build_patterns(terms: list[GlossaryTerm]) -> list[tuple[re.Pattern, GlossaryTerm]]:
    """Build regex patterns for all terms, longest first."""
    patterns = []
    for t in terms:
        if t.is_draft:
            continue
        # Collect all matchable forms
        forms = [t.term]
        forms.extend(t.synonyms)
        # Add slug with spaces (e.g. "byte-pair-encoding" -> "byte pair encoding")
        slug_spaced = t.slug.replace("-", " ")
        if slug_spaced.lower() not in [f.lower() for f in forms]:
            forms.append(slug_spaced)

        for form in forms:
            form = form.strip()
            if not form or len(form) < 2:
                continue
            # Skip single words that are part of compound terms
            if form.lower() in COMPOUND_ONLY:
                continue
            # Build word-boundary regex, case-insensitive
            escaped = re.escape(form)
            # Allow optional trailing s for plurals
            pattern_str = r"\b" + escaped + r"s?\b"
            try:
                pat = re.compile(pattern_str, re.IGNORECASE)
                patterns.append((pat, t, form, len(form)))
            except re.error:
                pass

    # Sort by length descending (longest match first)
    patterns.sort(key=lambda x: -x[3])
    return [(p, t) for p, t, _f, _l in patterns]


def find_exclusion_zones(content: str) -> list[tuple[int, int]]:
    """Find zones where links should NOT be inserted."""
    zones = []

    # Frontmatter
    fm_match = re.match(r"^---\n.*?\n---", content, re.DOTALL)
    if fm_match:
        zones.append((0, fm_match.end()))

    # Code blocks (``` ... ```)
    for m in re.finditer(r"```[\s\S]*?```", content):
        zones.append((m.start(), m.end()))

    # Inline code (`...`)
    for m in re.finditer(r"`[^`]+`", content):
        zones.append((m.start(), m.end()))

    # Headings (lines starting with #)
    for m in re.finditer(r"^#+\s.*$", content, re.MULTILINE):
        zones.append((m.start(), m.end()))

    # Existing links [...](...)
    for m in re.finditer(r"\[([^\]]*)\]\([^)]+\)", content):
        zones.append((m.start(), m.end()))

    # Images ![...](...)
    for m in re.finditer(r"!\[([^\]]*)\]\([^)]+\)", content):
        zones.append((m.start(), m.end()))

    # Import statements
    for m in re.finditer(r"^import\s.*$", content, re.MULTILINE):
        zones.append((m.start(), m.end()))

    # HTML/JSX tags with attributes
    for m in re.finditer(r"<[^>]+>", content):
        zones.append((m.start(), m.end()))

    # Blockquote citation lines (> Author et al.) — don't link in References
    refs_idx = content.find("## References")
    if refs_idx >= 0:
        zones.append((refs_idx, len(content)))

    # Table header rows (line before |---|)
    for m in re.finditer(r"^(\|[^\n]+\|)\n\|[-| ]+\|", content, re.MULTILINE):
        zones.append((m.start(), m.start() + len(m.group(1))))

    return sorted(zones)


def is_in_zone(pos: int, end: int, zones: list[tuple[int, int]]) -> bool:
    """Check if position falls in any exclusion zone."""
    for zs, ze in zones:
        if zs <= pos < ze or zs < end <= ze:
            return True
        if pos < zs:
            break  # zones are sorted, no need to check further
    return False


def has_context(term_slug: str, content: str, match_start: int) -> bool:
    """For context-sensitive terms, check if AI/ML context exists nearby."""
    # Check if this term needs context
    base = term_slug.split("-")[0].lower()
    if base not in CONTEXT_SENSITIVE:
        return True  # not context-sensitive, always link

    context_words = CONTEXT_SENSITIVE[base]
    # Look at surrounding ~200 chars
    window_start = max(0, match_start - 200)
    window_end = min(len(content), match_start + 200)
    window = content[window_start:window_end].lower()

    return any(w in window for w in context_words)


def has_inline_definition(content: str, match_start: int, match_end: int) -> bool:
    """Check if the term is already explained in context (parenthetical, 'is a', etc.)."""
    # Get the sentence containing the match
    line_start = content.rfind("\n", 0, match_start) + 1
    line_end = content.find("\n", match_end)
    if line_end == -1:
        line_end = len(content)
    sentence = content[line_start:line_end]

    # Check for parenthetical definition right after: "RAG (Retrieval-Augmented...)"
    after = content[match_end:match_end + 50]
    if re.match(r"\s*\(", after):
        return True

    # Check for "is a", "refers to", "means", "defined as"
    definition_patterns = [r"\bis\s+a\b", r"\brefers\s+to\b", r"\bmeans\b", r"\bdefined\s+as\b"]
    for pat in definition_patterns:
        if re.search(pat, sentence[match_start - line_start:], re.IGNORECASE):
            return True

    return False


def link_file(filepath: str, terms: list[GlossaryTerm], dry_run: bool = True) -> dict:
    """Process a single file and insert glossary links."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Determine locale from filename
    locale = None
    for loc in LOCALES:
        if filepath.endswith(f"-{loc}.mdx"):
            locale = loc
            break
    if not locale:
        return {"file": filepath, "links": 0, "skipped": 0}

    # Determine if this is a glossary file (for self-link prevention)
    is_glossary = GLOSSARY_DIR in filepath.replace("\\", "/")
    self_slug = None
    if is_glossary:
        basename = os.path.basename(filepath)
        self_slug = basename[: -len(f"-{locale}.mdx")]

    # Build patterns for this locale's terms
    locale_terms = [t for t in terms if t.locale == locale]
    patterns = build_patterns(locale_terms)

    zones = find_exclusion_zones(content)

    linked_slugs = set()  # track which terms we've already linked
    insertions = []  # (start, end, replacement)
    skipped = []

    # Also track existing glossary links already in the file
    for m in re.finditer(r"\[([^\]]+)\]\(/" + re.escape(locale) + r"/glossary/([^/]+)/\)", content):
        linked_slugs.add(m.group(2))

    for pattern, term in patterns:
        if term.slug in linked_slugs:
            continue  # already linked this term
        if self_slug and term.slug == self_slug:
            continue  # don't self-link

        for match in pattern.finditer(content):
            ms, me = match.start(), match.end()

            # Check exclusion zones
            if is_in_zone(ms, me, zones):
                continue

            # Check if already inside a planned insertion zone
            if any(ins_s <= ms < ins_e for ins_s, ins_e, _ in insertions):
                continue

            # Check context for sensitive terms
            if not has_context(term.slug, content, ms):
                skipped.append((term.slug, "no AI context"))
                continue

            # Check inline definition
            if has_inline_definition(content, ms, me):
                skipped.append((term.slug, "defined inline"))
                continue

            # Build link
            anchor = match.group(0)
            link = f"[{anchor}](/{locale}/glossary/{term.slug}/)"
            insertions.append((ms, me, link))
            linked_slugs.add(term.slug)

            # Add the insertion zone to exclusion zones so we don't nest
            zones.append((ms, ms + len(link)))
            zones.sort()
            break  # first mention only

    if not insertions:
        return {"file": filepath, "links": 0, "skipped": len(skipped)}

    # Check density (3-7 per 1000 words target, cap at 10)
    word_count = len(content.split())
    max_links = max(3, min(10, int(word_count / 100)))  # ~10 per 1000 words max
    if len(insertions) > max_links:
        insertions = insertions[:max_links]

    # Apply insertions (reverse order to preserve positions)
    if not dry_run:
        new_content = content
        for ms, me, link in sorted(insertions, key=lambda x: -x[0]):
            new_content = new_content[:ms] + link + new_content[me:]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    return {
        "file": os.path.basename(filepath),
        "links": len(insertions),
        "skipped": len(skipped),
        "terms": [ins[2].split("/glossary/")[1].split("/")[0] for ins in insertions] if insertions else [],
    }


def main():
    parser = argparse.ArgumentParser(description="Glossary linker")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser.add_argument("--blogs-only", action="store_true")
    parser.add_argument("--glossary-only", action="store_true")
    parser.add_argument("--file", type=str, help="Process single file (relative to content/)")
    args = parser.parse_args()

    dry_run = not args.apply
    terms_by_locale = load_terms()
    all_terms = [t for terms in terms_by_locale.values() for t in terms]

    print(f"{'DRY RUN' if dry_run else 'APPLYING'} glossary linker")
    print(f"Terms loaded: {sum(len(v) for v in terms_by_locale.values())} across {len(LOCALES)} locales")
    print()

    files_to_process = []

    if args.file:
        for base in [BLOG_DIR, GLOSSARY_DIR]:
            fpath = os.path.join(base, args.file)
            if os.path.exists(fpath):
                files_to_process.append(fpath)

    if not args.file:
        if not args.glossary_only:
            for f in sorted(os.listdir(BLOG_DIR)):
                if f.endswith(".mdx"):
                    files_to_process.append(os.path.join(BLOG_DIR, f))

        if not args.blogs_only:
            for f in sorted(os.listdir(GLOSSARY_DIR)):
                if f.endswith(".mdx"):
                    files_to_process.append(os.path.join(GLOSSARY_DIR, f))

    total_links = 0
    total_files_linked = 0
    term_counts: dict[str, int] = {}

    for fpath in files_to_process:
        result = link_file(fpath, all_terms, dry_run=dry_run)
        if result["links"] > 0:
            total_links += result["links"]
            total_files_linked += 1
            terms_list = result.get("terms", [])
            for t in terms_list:
                term_counts[t] = term_counts.get(t, 0) + 1
            if result["links"] >= 3:
                print(f"  {result['file']}: {result['links']} links ({', '.join(terms_list[:5])})")

    print(f"\n{'='*60}")
    print(f"SUMMARY {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Files processed: {len(files_to_process)}")
    print(f"  Files with links: {total_files_linked}")
    print(f"  Total links: {total_links}")
    print(f"  Avg links/file: {total_links/max(1,total_files_linked):.1f}")

    if term_counts:
        print(f"\n  Top linked terms:")
        for term, count in sorted(term_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"    {term}: {count}")

    # Orphan check: terms never linked
    linked_set = set(term_counts.keys())
    all_slugs = {t.slug for t in terms_by_locale.get("en", []) if not t.is_draft}
    orphans = all_slugs - linked_set
    if orphans and len(orphans) < 50:
        print(f"\n  Orphan terms (never linked): {len(orphans)}")
        for o in sorted(orphans)[:20]:
            print(f"    - {o}")


if __name__ == "__main__":
    main()

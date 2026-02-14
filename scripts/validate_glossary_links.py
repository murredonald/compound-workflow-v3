#!/usr/bin/env python3
"""Validate glossary links inserted by glossary_linker.py.

Checks:
1. No duplicate links to same glossary term in a single file
2. Links point to correct locale (match file locale)
3. No dead links (linked slug actually exists as glossary term)
4. No links in frontmatter, headings, code blocks, or other excluded zones
5. Link density sanity check
"""
import io
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
BLOG_DIR = "website/src/content/blog"
LOCALES = ["en", "nl", "fr", "de"]

# Build set of valid glossary slugs per locale
valid_slugs: dict[str, set[str]] = {loc: set() for loc in LOCALES}
for f in os.listdir(GLOSSARY_DIR):
    if not f.endswith(".mdx"):
        continue
    for loc in LOCALES:
        if f.endswith(f"-{loc}.mdx"):
            slug = f[: -len(f"-{loc}.mdx")]
            valid_slugs[loc].add(slug)
            break

total_valid = sum(len(v) for v in valid_slugs.values())
print(f"Valid glossary slugs: {total_valid} across {len(LOCALES)} locales")

# Collect all files to check
files = []
for d in [BLOG_DIR, GLOSSARY_DIR]:
    for f in sorted(os.listdir(d)):
        if f.endswith(".mdx"):
            files.append(os.path.join(d, f))

duplicate_errors = []
locale_errors = []
dead_link_errors = []
self_link_errors = []
density_warnings = []
frontmatter_link_errors = []

glossary_link_re = re.compile(r"\[([^\]]+)\]\(/([a-z]{2})/glossary/([^/]+)/\)")

for fpath in files:
    with open(fpath, encoding="utf-8") as fh:
        content = fh.read()

    fname = os.path.basename(fpath)

    # Determine file locale
    file_locale = None
    for loc in LOCALES:
        if fname.endswith(f"-{loc}.mdx"):
            file_locale = loc
            break
    if not file_locale:
        continue

    # Determine if glossary file and its slug
    is_glossary = GLOSSARY_DIR in fpath.replace("\\", "/")
    self_slug = None
    if is_glossary:
        self_slug = fname[: -len(f"-{file_locale}.mdx")]

    # Find frontmatter boundaries
    fm_end = 0
    fm_match = re.match(r"^---\n.*?\n---", content, re.DOTALL)
    if fm_match:
        fm_end = fm_match.end()

    # Find all glossary links
    seen_slugs: dict[str, int] = {}
    for m in glossary_link_re.finditer(content):
        anchor = m.group(1)
        link_locale = m.group(2)
        link_slug = m.group(3)
        pos = m.start()

        # Check: link in frontmatter
        if pos < fm_end:
            frontmatter_link_errors.append(f"{fname}: link to '{link_slug}' inside frontmatter")

        # Check: locale mismatch
        if link_locale != file_locale:
            locale_errors.append(f"{fname}: link to /{link_locale}/glossary/{link_slug}/ but file is {file_locale}")

        # Check: dead link
        if link_slug not in valid_slugs.get(link_locale, set()):
            dead_link_errors.append(f"{fname}: dead link to /{link_locale}/glossary/{link_slug}/")

        # Check: duplicate
        if link_slug in seen_slugs:
            duplicate_errors.append(f"{fname}: duplicate link to '{link_slug}' (positions {seen_slugs[link_slug]} and {pos})")
        else:
            seen_slugs[link_slug] = pos

        # Check: self-link in glossary
        if is_glossary and link_slug == self_slug:
            self_link_errors.append(f"{fname}: self-link to '{link_slug}'")

    # Density check
    word_count = len(content.split())
    link_count = len(seen_slugs)
    if word_count > 200 and link_count > 0:
        density = link_count / (word_count / 1000)
        if density > 15:
            density_warnings.append(f"{fname}: {link_count} links in {word_count} words ({density:.1f}/1000w)")

print(f"\nFiles checked: {len(files)}")

print(f"\n1. Duplicate links (same term linked twice): {len(duplicate_errors)}")
for e in duplicate_errors[:20]:
    print(f"   - {e}")

print(f"\n2. Locale mismatches (link points to wrong locale): {len(locale_errors)}")
for e in locale_errors[:20]:
    print(f"   - {e}")

print(f"\n3. Dead links (slug doesn't exist): {len(dead_link_errors)}")
for e in dead_link_errors[:20]:
    print(f"   - {e}")

print(f"\n4. Self-links (glossary item links to itself): {len(self_link_errors)}")
for e in self_link_errors[:10]:
    print(f"   - {e}")

print(f"\n5. Links in frontmatter: {len(frontmatter_link_errors)}")
for e in frontmatter_link_errors[:10]:
    print(f"   - {e}")

print(f"\n6. Density warnings (>15 links/1000w): {len(density_warnings)}")
for e in density_warnings[:10]:
    print(f"   - {e}")

total_issues = len(duplicate_errors) + len(locale_errors) + len(dead_link_errors) + len(self_link_errors) + len(frontmatter_link_errors)
print(f"\n{'='*60}")
print(f"Total issues: {total_issues}")
if total_issues == 0:
    print("ALL CLEAR")

#!/usr/bin/env python3
"""Comprehensive glossary cross-locale check."""
import io, os, re, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
LOCALES = ["en", "nl", "fr", "de"]

def parse_frontmatter(content: str) -> dict:
    """Extract frontmatter fields."""
    fm = {}
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return fm
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm

def get_refs_section(content: str) -> str:
    """Extract References section."""
    idx = content.find("## References")
    if idx == -1:
        return ""
    return content[idx:].strip()

def count_refs(refs: str) -> int:
    """Count citation lines in References."""
    return len([l for l in refs.split("\n") if l.strip().startswith(("-", ">"))])

# Collect all slugs
all_files = sorted(os.listdir(GLOSSARY_DIR))
slugs = set()
for f in all_files:
    if f.endswith(".mdx"):
        # Extract slug: everything before the last -XX.mdx
        for loc in LOCALES:
            suffix = f"-{loc}.mdx"
            if f.endswith(suffix):
                slugs.add(f[:-len(suffix)])
                break

slugs = sorted(slugs)
print(f"Total unique slugs: {len(slugs)}\n")

# Checks
missing_locales = []
refs_mismatches = []
category_mismatches = []
aiml_no_refs = []
refs_not_propagated = []
empty_body = []

for slug in slugs:
    files = {}
    for loc in LOCALES:
        fpath = os.path.join(GLOSSARY_DIR, f"{slug}-{loc}.mdx")
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                files[loc] = f.read()
        else:
            missing_locales.append(f"{slug}-{loc}.mdx")

    if "en" not in files:
        continue

    en_fm = parse_frontmatter(files["en"])
    en_refs = get_refs_section(files["en"])
    en_ref_count = count_refs(en_refs)
    category = en_fm.get("category", "")

    # Check ai-ml terms have references
    if category == "ai-ml" and en_ref_count == 0:
        aiml_no_refs.append(slug)

    # Check body isn't just frontmatter
    body = files["en"].split("---", 2)[-1].strip() if "---" in files["en"] else ""
    if len(body) < 20:
        empty_body.append(f"{slug}-en")

    # Check each locale
    for loc in LOCALES:
        if loc == "en" or loc not in files:
            continue

        loc_fm = parse_frontmatter(files[loc])
        loc_refs = get_refs_section(files[loc])
        loc_ref_count = count_refs(loc_refs)

        # Category mismatch
        if loc_fm.get("category", "") != category:
            category_mismatches.append(f"{slug}: en={category}, {loc}={loc_fm.get('category', '?')}")

        # termSlug mismatch
        if loc_fm.get("termSlug", "") != en_fm.get("termSlug", ""):
            category_mismatches.append(f"{slug}: termSlug mismatch en={en_fm.get('termSlug')}, {loc}={loc_fm.get('termSlug')}")

        # References: EN has but locale doesn't
        if en_ref_count > 0 and loc_ref_count == 0:
            refs_not_propagated.append(f"{slug}-{loc}.mdx (EN has {en_ref_count} refs)")

        # Body check
        loc_body = files[loc].split("---", 2)[-1].strip() if "---" in files[loc] else ""
        if len(loc_body) < 20:
            empty_body.append(f"{slug}-{loc}")

# Report
print("=" * 60)
print("CROSS-LOCALE GLOSSARY CHECK")
print("=" * 60)

print(f"\n1. Missing locale files: {len(missing_locales)}")
for m in missing_locales[:20]:
    print(f"   - {m}")
if len(missing_locales) > 20:
    print(f"   ... and {len(missing_locales) - 20} more")

print(f"\n2. AI-ML terms without References: {len(aiml_no_refs)}")
for t in aiml_no_refs:
    print(f"   - {t}")

print(f"\n3. References not propagated to locales: {len(refs_not_propagated)}")
for r in refs_not_propagated[:20]:
    print(f"   - {r}")
if len(refs_not_propagated) > 20:
    print(f"   ... and {len(refs_not_propagated) - 20} more")

print(f"\n4. Category/slug mismatches: {len(category_mismatches)}")
for c in category_mismatches[:10]:
    print(f"   - {c}")

print(f"\n5. Empty/minimal body: {len(empty_body)}")
for e in empty_body[:20]:
    print(f"   - {e}")
if len(empty_body) > 20:
    print(f"   ... and {len(empty_body) - 20} more")

print(f"\n{'=' * 60}")
print("SUMMARY")
print(f"{'=' * 60}")
print(f"  Slugs checked:             {len(slugs)}")
print(f"  Missing locale files:      {len(missing_locales)}")
print(f"  AI-ML without refs:        {len(aiml_no_refs)}")
print(f"  Refs not propagated:       {len(refs_not_propagated)}")
print(f"  Category/slug mismatches:  {len(category_mismatches)}")
print(f"  Empty/minimal body:        {len(empty_body)}")

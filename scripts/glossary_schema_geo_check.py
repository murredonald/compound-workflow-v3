#!/usr/bin/env python3
"""Check glossary schema compliance and GEO (no brand mentions)."""
import io, os, re, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
LOCALES = ["en", "nl", "fr", "de"]
REQUIRED_FIELDS = ["term", "termSlug", "short", "category", "category_name", "locale"]
VALID_CATEGORIES = {"ai-ml", "tax-law", "legal", "technical", "business", "ai-regulation", "search"}
BRAND_PATTERNS = [
    r"\bauryth\b", r"\bauryth tx\b", r"\baurythm\b",
    r"\bauryth\.ai\b", r"\bauryth\.com\b",
]
brand_re = re.compile("|".join(BRAND_PATTERNS), re.IGNORECASE)

schema_errors = []
geo_violations = []
slug_errors = []
locale_errors = []
category_errors = []
short_missing = []

for f in sorted(os.listdir(GLOSSARY_DIR)):
    if not f.endswith(".mdx"):
        continue

    fpath = os.path.join(GLOSSARY_DIR, f)
    with open(fpath, encoding="utf-8") as fh:
        content = fh.read()

    # Parse frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        schema_errors.append(f"{f}: missing frontmatter")
        continue

    fm_text = fm_match.group(1)
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key = line.split(":")[0].strip()
            val = line.split(":", 1)[1].strip()
            fm[key] = val

    # 1. Check for forbidden `slug:` field (should be `termSlug:`)
    if "slug" in fm:
        slug_errors.append(f"{f}: uses 'slug:' instead of 'termSlug:'")

    # 2. Check required fields
    for field in REQUIRED_FIELDS:
        if field not in fm:
            schema_errors.append(f"{f}: missing '{field}'")

    # 3. Check locale matches filename
    expected_locale = None
    for loc in LOCALES:
        if f.endswith(f"-{loc}.mdx"):
            expected_locale = loc
            break
    if expected_locale and fm.get("locale", "").strip('"').strip("'") != expected_locale:
        locale_errors.append(f"{f}: locale={fm.get('locale')} but filename says {expected_locale}")

    # 4. Check category is valid
    cat = fm.get("category", "").strip('"').strip("'")
    if cat and cat not in VALID_CATEGORIES:
        category_errors.append(f"{f}: unknown category '{cat}'")

    # 5. Check short field isn't empty
    short = fm.get("short", "").strip('"').strip("'")
    if not short or len(short) < 10:
        short_missing.append(f"{f}: short field empty or too short")

    # 6. GEO check: no brand mentions in body (after frontmatter)
    body = content[fm_match.end():]
    brand_matches = brand_re.findall(body)
    if brand_matches:
        geo_violations.append(f"{f}: brand mentions in body: {brand_matches}")

print("=" * 60)
print("SCHEMA & GEO CHECK")
print("=" * 60)

print(f"\n1. Schema errors (missing fields): {len(schema_errors)}")
for e in schema_errors[:10]:
    print(f"   - {e}")

print(f"\n2. Slug field errors (slug: vs termSlug:): {len(slug_errors)}")
for e in slug_errors:
    print(f"   - {e}")

print(f"\n3. Locale mismatches: {len(locale_errors)}")
for e in locale_errors[:10]:
    print(f"   - {e}")

print(f"\n4. Invalid categories: {len(category_errors)}")
for e in category_errors:
    print(f"   - {e}")

print(f"\n5. Missing/empty short field: {len(short_missing)}")
for e in short_missing[:10]:
    print(f"   - {e}")

print(f"\n6. GEO violations (brand in body): {len(geo_violations)}")
for e in geo_violations:
    print(f"   - {e}")

total_files = len([f for f in os.listdir(GLOSSARY_DIR) if f.endswith(".mdx")])
total_issues = len(schema_errors) + len(slug_errors) + len(locale_errors) + len(category_errors) + len(short_missing) + len(geo_violations)

print(f"\n{'=' * 60}")
print(f"Files checked: {total_files}")
print(f"Total issues:  {total_issues}")
if total_issues == 0:
    print("ALL CLEAR")

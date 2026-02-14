#!/usr/bin/env python3
"""Propagate References sections from EN to NL/FR/DE locale files."""
import io, os, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
LOCALES = ["nl", "fr", "de"]

propagated = 0
skipped = 0

for f in sorted(os.listdir(GLOSSARY_DIR)):
    if not f.endswith("-en.mdx"):
        continue

    slug = f.replace("-en.mdx", "")
    en_path = os.path.join(GLOSSARY_DIR, f)

    with open(en_path, encoding="utf-8") as fh:
        en_content = fh.read()

    refs_idx = en_content.find("## References")
    if refs_idx == -1:
        continue

    en_refs = en_content[refs_idx:].strip()

    for loc in LOCALES:
        loc_path = os.path.join(GLOSSARY_DIR, f"{slug}-{loc}.mdx")
        if not os.path.exists(loc_path):
            continue

        with open(loc_path, encoding="utf-8") as fh:
            loc_content = fh.read()

        if "## References" in loc_content:
            skipped += 1
            continue

        # Append references
        loc_content = loc_content.rstrip() + "\n\n" + en_refs + "\n"
        with open(loc_path, "w", encoding="utf-8") as fh:
            fh.write(loc_content)
        propagated += 1

print(f"Propagated: {propagated} files")
print(f"Already had refs: {skipped} files")

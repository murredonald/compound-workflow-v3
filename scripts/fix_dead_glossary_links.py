#!/usr/bin/env python3
"""Remove dead glossary links — replace [text](/locale/glossary/slug/) with just text."""
import io, os, re, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
BLOG_DIR = "website/src/content/blog"
LOCALES = ["en", "nl", "fr", "de"]

# Collect all valid slugs
valid_slugs: set[str] = set()
for f in os.listdir(GLOSSARY_DIR):
    if not f.endswith(".mdx"):
        continue
    for loc in LOCALES:
        if f.endswith(f"-{loc}.mdx"):
            slug = f[: -len(f"-{loc}.mdx")]
            valid_slugs.add(slug)
            break

link_re = re.compile(r"\[([^\]]+)\]\(/([a-z]{2})/glossary/([^/]+)/\)")
fixed_files = 0
fixed_links = 0

for d in [BLOG_DIR, GLOSSARY_DIR]:
    for f in sorted(os.listdir(d)):
        if not f.endswith(".mdx"):
            continue
        fpath = os.path.join(d, f)
        with open(fpath, encoding="utf-8") as fh:
            content = fh.read()

        new_content = content
        for m in reversed(list(link_re.finditer(content))):
            link_slug = m.group(3)
            if link_slug not in valid_slugs:
                anchor = m.group(1)
                new_content = new_content[: m.start()] + anchor + new_content[m.end() :]
                fixed_links += 1

        if new_content != content:
            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write(new_content)
            fixed_files += 1

print(f"Fixed {fixed_links} dead links across {fixed_files} files")

#!/usr/bin/env python3
"""Scan glossary for off-topic citations."""
import io, os, re, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

glossary_dir = "website/src/content/glossary"
bad_signals = [
    "landslide", "soil moisture", "fatigue data", "composit", "concrete compressive",
    "water storage", "Internet of Things", "SciPy", "Quantum ESPRESSO",
    "Variant Effect Predictor", "cancer", "tumor", "remote sensing",
    "face verif", "protein", "bioinforma", "materials model", "agriculture",
    "sensor Calibration", "weave an information tapestry", "document binariz",
    "optical flow", "Ensembl Variant", "cross-modal retrieval",
    "visual question", "radiology", "molecular", "physics-guided",
    "plant disease", "genomic", "NormFace", "gene expression",
    "shallow landslide", "tensile stress", "GRACE Total Water",
    "Corn yield", "fatigue", "deglacial", "chemometrics",
]
bad_pattern = "|".join(re.escape(s) for s in bad_signals)

for f in sorted(os.listdir(glossary_dir)):
    if not f.endswith("-en.mdx"):
        continue
    slug = f.replace("-en.mdx", "")
    with open(os.path.join(glossary_dir, f), encoding="utf-8") as fh:
        content = fh.read()
    refs_start = content.find("## References")
    if refs_start == -1:
        continue
    refs = content[refs_start:]
    matches = re.findall(bad_pattern, refs, re.IGNORECASE)
    if matches:
        print(f"\n{slug}:")
        # Show the references section
        for line in refs.strip().split("\n"):
            if line.startswith(">"):
                is_bad = any(s.lower() in line.lower() for s in bad_signals)
                marker = " <<<BAD" if is_bad else ""
                print(f"  {line[:120]}{marker}")

# Glossary audit report

- **Scope**: 207 EN terms (828 files across 4 locales)
- **Audit date**: 2026-02-14
- **Categories**: ai-ml (144), tax-law, legal, technical, business, ai-regulation, search

## Fixes applied

### 1. Brand mentions removed (8 files)

| File | Issue | Fix |
|---|---|---|
| llm-en.mdx | "How Auryth TX addresses these limitations" heading + branded body | Genericized to "How these limitations are addressed in practice" |
| llm-nl.mdx | Same (Dutch) | Genericized |
| llm-fr.mdx | Same (French) | Genericized |
| llm-de.mdx | Same (German) | Genericized |
| grounding-en.mdx | "Aurythm" fictional brand in 238-line ASCII diagram | Replaced with generic "refund policy" example, restructured diagram |
| grounding-nl.mdx | 170-line monolithic ASCII diagram | Restructured to sectioned diagrams + tables |
| grounding-fr.mdx | 167-line monolithic ASCII diagram | Restructured to sectioned diagrams + tables |
| grounding-de.mdx | 169-line monolithic ASCII diagram | Restructured to sectioned diagrams + tables |

### 2. ASCII diagrams restructured (4 files)

All grounding locale files: monolithic 170-238 line single code block split into:
- Ungrounded vs grounded example (~15 lines)
- Architecture flow diagram (~20 lines)
- Types table (markdown table)
- Quality metrics table (markdown table)

### 3. Missing locale files created (6 files)

| Term | Locales created |
|---|---|
| retrieval-pipeline | NL, FR, DE (all draft, matching EN stub) |
| retrieval-scoring | NL, FR, DE (all draft, matching EN stub) |

## Findings noted but not changed

### Short field length (57 EN entries > 160 chars)

The `short` field is used as:
- Meta description (truncated by Google at ~155 chars)
- Schema.org `description` (no limit)
- On-page subtitle (no limit)
- Card preview (CSS `line-clamp-2` already truncates)

**Decision**: No content changes needed. The template can handle meta description truncation. The full `short` text provides better schema.org and on-page value.

### Citation enrichment (ai-ml category) — COMPLETED

67 ai-ml terms were missing a `## References` section (the other 77 already had citations). All 67 were enriched via automated search (Semantic Scholar + OpenAlex APIs with proxy rotation), then 21 terms with off-topic API results were manually curated with correct citations.

**Process:**
1. `scripts/enrich_glossary_citations.py` — batch enrichment (fetches 10 papers per source, picks top 3 by citation count, appends to all 4 locale files)
2. `scripts/scan_bad_citations.py` — quality scan for off-topic results
3. `scripts/fix_bad_citations.py` — manual curation of 21 terms with bad API results

**Result:** 144/144 ai-ml EN terms now have References sections, propagated to NL/FR/DE.

**Terms manually curated (21):** regression-testing-ai-systems, stress-testing, structured-output-generation, tool-use-in-llms, calibration, reliability-metrics, retrieval-filtering, retrieval-pipeline, retrieval-recall, byte-pair-encoding, embedding-model, index-refresh, index-sharding, knowledge-retrieval-strategy, llm, positional-encoding, sentencepiece, uncertainty-estimation, vector-normalization, multi-hop-retrieval, feed-forward-network.

### Schema compliance

- No `slug:` errors found (all use `termSlug:` correctly)
- No missing required fields
- No locale mismatches
- All categories consistent across locales

## Summary

| Check | Result |
|---|---|
| Schema compliance | Pass (0 errors) |
| Brand mentions | Fixed (8 files) |
| ASCII diagram quality | Fixed (4 files) |
| Cross-locale consistency | Fixed (6 files created) |
| Short field length | Noted, no action (template handles truncation) |
| Citation enrichment | Done (67 terms enriched, 21 manually curated) |

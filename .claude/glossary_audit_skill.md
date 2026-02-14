# Glossary audit skill — auryth-tx-glossary-audit

## Purpose

Audit and fix glossary entries for quality, consistency, and GEO-readiness. Lightweight quality gate focused on visual formatting, content accuracy, and schema compliance.

---

## Trigger

Use when the user says:

- "audit glossary"
- "check glossary entries"
- "fix glossary"
- "/glossary-audit"
- "glossary quality check"

---

## Audit Checklist

### 1. Schema Compliance

Check each file has valid frontmatter:

```yaml
---
term: "Required"           # Display name
termSlug: "required"       # URL slug (NOT "slug")
short: "Required"          # <160 chars TL;DR
category: "ai-ml"          # tax-law | ai-ml | legal | technical | business
category_name: "Required"  # Localized category name
related: []                # Array of termSlugs
synonyms: []               # Alternative names
locale: "en"               # en | nl | fr | de
draft: false               # boolean
---
```

**Common errors:**
- Using `slug` instead of `termSlug` (Astro reserves `slug`)
- Missing required fields
- Wrong locale value
- Category mismatch between files

### 2. ASCII Diagram Quality

**Red flags to fix:**

```
❌ BAD: Misaligned boxes, inconsistent borders
│  │  cos(180°) = -1.0 → Opposite direction              │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │

❌ BAD: Mixed box-drawing characters
+---+     vs    ┌───┐
|   |           │   │
+---+           └───┘

❌ BAD: Monolithic 200+ line diagrams that could be split or trimmed
❌ BAD: Diagrams that don't render in monospace
```

**Good ASCII patterns:**

```
✅ GOOD: Simple flow (preferred)
Input → Process → Output

✅ GOOD: Clean box diagram
┌─────────────┐
│  Component  │
└─────────────┘

✅ GOOD: Minimal hierarchy
Question
    ↓
  Embed → Search → Retrieve
    ↓
Response
```

**Fix strategy:**
1. Simplify bloated diagrams but don't oversimplify — they should be visually clean and readable, not minimal for the sake of it
2. Use consistent Unicode box characters: `┌ ─ ┐ │ └ ┘ → ▶ ↓`
3. No hard line limit — but 200+ line monolithic diagrams clearly need trimming. A well-structured 30-40 line diagram is fine
4. Test in fixed-width font before committing

### 3. Citation Verification

**For AI/ML terms (category: ai-ml):**
- Minimum 3 citations for foundational concepts (RAG, LLM, embeddings)
- Citations must include: Author et al. (Year), "[Title](link)", Venue
- Links should be dofollow to arXiv/DOI
- Verify paper exists and title/year match

**Red flags:**
- Generic "studies show" without citation
- Broken arXiv links
- Wrong year or venue
- Citing blog posts as academic sources

**Skip citations for:**
- Simple technical terms (tokenization, inference)
- Business/legal terms (unless controversial)

### 3a. Expanding Sources with Academic Search API

When a glossary term has insufficient or broken citations, use the **academic search script** to find authoritative sources via Semantic Scholar and OpenAlex APIs (both free, no auth required).

**When to use:**
- Term has < 3 citations but is a foundational AI concept
- Existing citations have dead links
- Claims need academic backing
- Term is new and lacks references

**How to search (via terminal):**

```powershell
# Default: fetch 10 per source, pick top 3 by citation count, glossary-ready output
python scripts/academic_search.py "retrieval augmented generation"

# Custom fetch/top counts
python scripts/academic_search.py "large language model hallucination" --fetch 15 --top 5

# Raw JSON output for manual curation
python scripts/academic_search.py "cosine similarity embeddings" --format json

# For niche/recent topics not well indexed (opens browser)
python scripts/direct_academic_search.py "Belgian tax regulation AI"
```

**The script searches (with exponential backoff + jitter):**
- Semantic Scholar (arXiv, PubMed, ACL, DBLP, IEEE, Springer, Elsevier)
- OpenAlex (Crossref, SSRN, arXiv, DOAJ, Unpaywall)

**Citation workflow: Fetch 10, Pick 3**
1. Run search — script fetches 10 per source, deduplicates, picks top 3 by citation count
2. Output is in glossary-ready blockquote format by default
3. Review the 3 picks and paste directly into the `## References` section
4. If results are poor, try alternate search terms or use `--fetch 15 --top 5` for more candidates

**Selection criteria (automated by citation count, verify manually):**
| Priority | Source Type | Why |
|----------|-------------|-----|
| 1 | arXiv with 1000+ citations | Foundational, widely recognized |
| 2 | NeurIPS/ICML/ACL proceedings | Peer-reviewed, high quality |
| 3 | Survey papers | Comprehensive, good for linking |
| 4 | Recent papers (2023+) | Current state of art |

**Citation format (script outputs this directly):**

```markdown
## References

- Vaswani et al. (2017), "[Attention Is All You Need](https://arxiv.org/abs/1706.03762)", NeurIPS.
- Lewis et al. (2020), "[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)", NeurIPS.
```

**Cross-locale propagation:** Citations are language-neutral (author names, paper titles, venues stay in English). Copy the same References section to all 4 locale files (EN, NL, FR, DE).

Or use `fetch_webpage` tool to verify and extract metadata.

**Workflow:**
1. Identify terms needing more sources (audit finds < 3 citations)
2. Run `python scripts/academic_search.py "{term}" --limit 20`
3. Select best 2-3 papers from results
4. Verify links work
5. Add to References section with proper formatting
6. Update all 4 locale files with same citations

### 4. Cross-Locale Consistency

For each termSlug, verify all 4 locales exist:
- `{termSlug}-en.mdx`
- `{termSlug}-nl.mdx`
- `{termSlug}-fr.mdx`
- `{termSlug}-de.mdx`

**Must be identical across locales:**
- `termSlug`
- `category`
- `related` array

**Must be translated:**
- `term` (sometimes same)
- `short`
- `category_name`
- `synonyms`
- Body content

### 5. Content Quality

**Check for:**
- [ ] Definition section exists and is clear (2-3 sentences)
- [ ] "Why it matters" is domain-agnostic (no product mentions)
- [ ] Q&A section has relevant questions
- [ ] Related terms link to existing glossary entries
- [ ] No marketing language or promotional tone

**GEO requirements:**
- No mentions of "Auryth TX" in body content
- Examples should be generic ("a question", not "a tax question")
- Content should be educational, not sales-focused

### 6. GEO Audit (Generative Engine Optimization)

Ensure glossary entries are optimized for AI extraction by Gemini, ChatGPT, Perplexity, Claude, etc.

**GEO Compliance Checklist:**

| Check | Pass | Fail | Fix |
|-------|------|------|-----|
| `short` field is AI-extractable | < 160 chars, complete definition | Too long, vague, or truncated sentence | Rewrite as standalone TL;DR |
| Definition section is self-contained | First paragraph answers "What is X?" without context | Requires reading whole article | Rewrite first 2 sentences |
| No brand mentions in body | Zero mentions of "Auryth", company names | Product mentions, CTAs, pricing | Remove or genericize |
| Examples are domain-agnostic | Generic: "a document", "a query" | Domain-specific: "a tax return" | Replace with neutral examples |
| Q&A uses natural questions | "What is...", "How does...", "Why use..." | Marketing questions, leading questions | Rewrite as search queries |
| Internal links use termSlug | `[RAG](/en/glossary/rag/)` | Broken links, missing links | Fix paths, add missing |
| Citations have dofollow links | `[Title](https://arxiv.org/...)` | nofollow, rel="noopener" only | Remove nofollow |

**GEO Red Flags to Fix:**

```markdown
❌ BAD: "short" too long or incomplete
short: "RAG is a technique that combines retrieval mechanisms with generation capabilities to produce more accurate and contextually relevant responses by grounding the output in retrieved documents"
# 200+ chars, will be truncated

✅ GOOD: Concise, complete
short: "RAG grounds LLM responses in retrieved documents, reducing hallucinations and improving accuracy."
# ~95 chars, standalone definition

❌ BAD: Brand mention in body
"Auryth TX uses RAG to provide accurate tax answers..."

✅ GOOD: Generic example
"Legal research platforms use RAG to provide accurate answers grounded in case law..."

❌ BAD: Domain-specific example
"When a tax advisor asks about inheritance tax rates..."

✅ GOOD: Domain-agnostic
"When a user asks about complex regulatory requirements..."
```

**GEO Patching Workflow:**

1. **Scan for violations:**
   ```powershell
   # Find brand mentions
   Select-String -Path "website/src/content/glossary/*.mdx" -Pattern "Auryth|auryth" | Select-Object Path, Line
   
   # Find long short fields
   Get-ChildItem website/src/content/glossary/*.mdx | ForEach-Object {
     $content = Get-Content $_.FullName -Raw
     if ($content -match 'short: "([^"]{160,})"') {
       Write-Host "$($_.Name): short field too long ($($matches[1].Length) chars)"
     }
   }
   ```

2. **Patch violations:**
   - Read the file
   - Identify the GEO violation
   - Rewrite the problematic section
   - Update all 4 locale files consistently

3. **Verify AI extractability:**
   ```
   Test: Can this definition stand alone in a Google AI Overview?
   Test: Would ChatGPT cite this as a reliable definition?
   Test: Does the first paragraph answer the search query?
   ```

**When to Rewrite vs Patch:**

| Scenario | Action |
|----------|--------|
| `short` too long | Patch: Condense to < 160 chars |
| Brand mention in example | Patch: Replace with generic |
| Entire definition is product-focused | Rewrite: Create educational content |
| Missing Q&A section | Rewrite: Add 3-4 natural questions |
| Weak citations | Patch: Add via academic search |

---

## Audit Output Format

```markdown
## Glossary Audit Report

### Schema Issues
| File | Issue | Fix |
|------|-------|-----|
| llm-de.mdx | Missing `termSlug` | Add `termSlug: "llm"` |

### ASCII Issues
| File | Problem | Action |
|------|---------|--------|
| cosine-similarity-en.mdx | Misaligned boxes (15+ lines) | Simplify to flow diagram |

### Citation Issues
| File | Problem | Action |
|------|---------|--------|
| rag-en.mdx | Only 2 citations | Run: `python scripts/academic_search.py "RAG" --limit 20` |

### GEO Issues
| File | Problem | Action |
|------|---------|--------|
| embeddings-en.mdx | `short` 185 chars | Rewrite to < 160 chars |
| llm-nl.mdx | Brand mention | Remove "Auryth" reference |
| rag-fr.mdx | Domain-specific example | Genericize "tax advisor" → "user" |

### Missing Locales
| termSlug | Missing |
|----------|---------|
| new-term | fr, de |

### Summary
- ✅ Schema: X/Y files valid
- ⚠️ ASCII: X files need cleanup
- ✅ Citations: X/Y terms properly cited
- ⚠️ GEO: X files need patching
- ⚠️ Locales: X terms incomplete
```

---

## Quick Fixes

### Fix misaligned ASCII

Replace complex box diagrams with simple flows:

```markdown
## Before (bad)
┌──────────────────────────────────────────────────────────────┐
│                     COSINE SIMILARITY                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  cos(0°) = 1.0 → Identical direction                    │  │

## After (good)
Vector A → Dot Product → Normalize → Similarity Score (0 to 1)
```

### Fix missing termSlug

```yaml
# Before
slug: "llm"  # ❌ Astro reserves this

# After
termSlug: "llm"  # ✅ Correct field name
```

### Add missing citation

```markdown
## References

> Lewis et al. (2020), "[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)", NeurIPS. [11,200+ citations]
```

---

## Batch Commands

```bash
# List all glossary files
Get-ChildItem website/src/content/glossary/*.mdx | Measure-Object

# Find files missing termSlug
Select-String -Path "website/src/content/glossary/*.mdx" -Pattern "^termSlug:" -NotMatch | Select-Object Filename -Unique

# Find complex ASCII (lines with box chars)
Select-String -Path "website/src/content/glossary/*.mdx" -Pattern "[┌┐└┘│─]" | Group-Object Filename | Where-Object Count -gt 10
```

---

## Priority Order

1. **Schema errors** — blocks site build
2. **GEO violations** — affects AI extractability (brand mentions, long `short` fields)
3. **Citation gaps** — authority signals, use `academic_search.py`
4. **Missing locales** — incomplete coverage
5. **ASCII cleanup** — visual quality
6. **Content polish** — nice to have

---

## Adding New Categories

If a term doesn't fit existing categories, you can add a new one:

### Current Categories

| Key | EN | NL | FR | DE |
|-----|----|----|----|----|
| `tax-law` | Tax Law | Fiscaal recht | Droit fiscal | Steuerrecht |
| `ai-ml` | AI & Machine Learning | AI & Machine Learning | IA & Machine Learning | KI & Machine Learning |
| `ai-regulation` | AI Regulation | AI-regelgeving | Réglementation IA | KI-Regulierung |
| `search` | Search & Retrieval | Zoeken & Retrieval | Recherche & Récupération | Suche & Retrieval |
| `business` | Business | Business | Business | Business |

### To Add a New Category

1. **Choose a slug** — lowercase, hyphenated (e.g., `data-privacy`)

2. **Define translations** — all 4 locales:
   ```
   data-privacy → Data Privacy | Gegevensprivacy | Protection des données | Datenschutz
   ```

3. **Update glossary_builder_skill.md** — add to Categories table

4. **Create category index page** (optional) — if you want `/{locale}/glossary/category/{new-category}/`

5. **Use in frontmatter**:
   ```yaml
   category: "data-privacy"
   category_name: "Data Privacy"  # Localized per file
   ```

### When to Create vs Reuse

**Create new category when:**
- 5+ terms would fit the new category
- Existing categories are a poor semantic fit
- Users would expect to browse by this grouping

**Reuse existing category when:**
- Only 1-2 terms would use it
- Term is adjacent to existing category (e.g., "encryption" → `technical`)
- Category would be too narrow

---

## Amending Existing Categories

### Renaming a Category

1. **Update all glossary files** using that category:
   ```powershell
   # Find all files using the old category
   Get-ChildItem website/src/content/glossary/*.mdx | Select-String 'category: "old-slug"'
   
   # Bulk update category slug
   Get-ChildItem website/src/content/glossary/*.mdx | ForEach-Object {
     (Get-Content $_.FullName) -replace 'category: "old-slug"', 'category: "new-slug"' | Set-Content $_.FullName
   }
   ```

2. **Update `category_name`** in all 4 locale variants:
   ```powershell
   # EN files
   Get-ChildItem website/src/content/glossary/*-en.mdx | ForEach-Object {
     (Get-Content $_.FullName) -replace 'category_name: "Old Name"', 'category_name: "New Name"' | Set-Content $_.FullName
   }
   # Repeat for -nl.mdx, -fr.mdx, -de.mdx with localized names
   ```

3. **Update glossary_builder_skill.md** categories table

4. **Update category index pages** if they exist at `/{locale}/glossary/category/`

### Changing Category Translations

If only the display name needs updating (not the slug):

```powershell
# Example: Change "AI & Machine Learning" to "Artificial Intelligence"
Get-ChildItem website/src/content/glossary/*-en.mdx | ForEach-Object {
  (Get-Content $_.FullName) -replace 'category_name: "AI & Machine Learning"', 'category_name: "Artificial Intelligence"' | Set-Content $_.FullName
}
```

### Merging Categories

When consolidating two categories into one:

1. **Decide which slug to keep** (usually the broader one)

2. **Update all files** from the deprecated category:
   ```powershell
   # Move "data-privacy" terms into "legal"
   Get-ChildItem website/src/content/glossary/*.mdx | ForEach-Object {
     (Get-Content $_.FullName) -replace 'category: "data-privacy"', 'category: "legal"' | Set-Content $_.FullName
   }
   ```

3. **Update category_name** for affected files (per locale)

4. **Remove deprecated category** from documentation

### Splitting a Category

When a category gets too broad:

1. **Identify terms** that should move to new category
2. **Create new category** (see "Adding New Categories" above)
3. **Update specific files** — don't bulk replace, review each:
   ```powershell
   # List candidates for review
   Get-ChildItem website/src/content/glossary/*.mdx | Select-String 'category: "technical"' | Select-Object Path
   ```
4. **Manually update** files that fit the new category better

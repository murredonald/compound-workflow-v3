# Glossary Linker Skill — Smart Internal Linking

## Purpose

Scan blog posts and glossary items to insert contextual links to glossary definitions. Links are added where they **add value** for the reader — not mechanically on every keyword hit.

The goal is user-friendly knowledge navigation, not SEO keyword stuffing.

---

## Trigger

Use when the user says:

- "link glossary"
- "add glossary links"
- "link blog to glossary"
- "internal linking"
- "cross-link terms"
- "/link"
- "glossary linker"
- "connect content to glossary"

---

## Pre-flight Checks

Before linking, verify:

1. **Glossary term exists for target locale**
   ```powershell
   # Check if term exists for all 4 locales
   $term = "rag"
   @("en","nl","fr","de") | ForEach-Object { 
     Test-Path "website/src/content/glossary/$term-$_.mdx" 
   }
   ```
   Only link to terms that exist. If `rag-de.mdx` is missing, don't insert German links to RAG.

2. **Term is not draft**
   ```powershell
   # Check draft status
   Select-String -Path "website/src/content/glossary/rag-en.mdx" -Pattern '^draft:\s*true'
   ```
   Never link to `draft: true` glossary entries.

3. **Source file is body content (not config/schema)**
   Only process `.mdx` files in `content/blog/` and `content/glossary/`.

---

## Principles

### 1. First mention only

Link the **first meaningful mention** of each term per article. Never link the same term twice in one document. Headlines and pull quotes don't count — link in body text.

### 2. Value-add linking

Ask: "Would a reader benefit from accessing the definition here?" 

**Link when:**
- Term is introduced without explanation
- Context assumes reader knows the concept
- Definition adds nuance beyond what the sentence provides

**Don't link when:**
- Term is already explained in the paragraph
- Article itself IS the canonical source for that term
- Link would interrupt reading flow at a critical point

### 3. Natural anchor text

Exact term match is ideal, but natural variations are fine:

| Glossary term | Valid anchors |
|---------------|---------------|
| `rag` | RAG, retrieval-augmented generation, RAG system, RAG pipeline |
| `hallucination` | hallucination, hallucinations, AI hallucination, fabricated output |
| `llm` | LLM, LLMs, large language model, language model |
| `eu-ai-act` | EU AI Act, AI Act, Regulation 2024/1689 |
| `embeddings` | embedding, embeddings, vector embedding, embedding model |
| `semantic-search` | semantic search, semantic retrieval, meaning-based search |

Choose the anchor that sounds most natural in context. Paraphrased anchors are acceptable if the destination clearly matches:

```markdown
<!-- OK: natural anchor -->
...the system uses [retrieval-augmented generation](/en/glossary/rag/) to...

<!-- OK: paraphrased -->
...generates [vector representations](/en/glossary/embeddings/) of documents...

<!-- BAD: forced keyword -->
...the [RAG](/en/glossary/rag/) pipeline [RAG](/en/glossary/rag/)...
```

### 4. Locale-aware linking

Always link to the **same locale** as the source document:

| Source file | Link pattern |
|-------------|--------------|
| `*-en.mdx` | `[anchor](/en/glossary/{termSlug}/)` |
| `*-nl.mdx` | `[anchor](/nl/glossary/{termSlug}/)` |
| `*-fr.mdx` | `[anchor](/fr/glossary/{termSlug}/)` |
| `*-de.mdx` | `[anchor](/de/glossary/{termSlug}/)` |

### 5. Don't over-link

Target **3-7 glossary links per 1000 words**. More creates link fatigue. Less might mean missed opportunities.

---

## Exclusion Zones — NEVER Link Here

### Zone 1: Frontmatter

```yaml
---
title: "Understanding RAG systems"  # ← DON'T LINK
description: "How LLMs use RAG..."  # ← DON'T LINK
tags: ["RAG", "LLM", "AI"]          # ← DON'T LINK
---
```

**Detection:** Content between `---` markers at file start. Skip lines 1 through second `---`.

### Zone 2: Code blocks

````markdown
```python
# DON'T LINK inside code
embeddings = model.encode(text)  # ← "embeddings" stays plain
rag_pipeline.run()               # ← "rag" stays plain
```
````

**Detection:** Content between triple backticks. Also single backticks: `LLM` should NOT become `[LLM](/en/glossary/llm/)`.

### Zone 3: Existing links

```markdown
<!-- Already linked — don't double-link -->
Read about [retrieval systems](https://example.com) that use RAG...
                                                         ↑ this RAG is fine to link

<!-- But don't link inside existing link text -->
[Understanding RAG pipelines](/en/blog/rag-intro/)
              ↑ DON'T link "RAG" here — it's already anchor text
```

**Detection:** Regex to find `[...](...)`; skip content inside brackets.

### Zone 4: Headings

```markdown
## RAG Architecture Overview  ← DON'T LINK in headings
```

**Detection:** Lines starting with `#`. Link terms in body text, not headers.

### Zone 5: Image alt text

```markdown
![RAG pipeline diagram](/images/rag-diagram.png)
   ↑ DON'T link here
```

**Detection:** Content inside `![...]`.

### Zone 6: HTML/JSX tags

```markdown
<InfoBox title="What is RAG?">  ← DON'T link in attributes
  RAG stands for...             ← OK to link here
</InfoBox>
```

**Detection:** Content inside `<tag attr="...">` — specifically attribute values.

### Zone 7: Import statements

```markdown
import { RAGComponent } from './components';  ← DON'T LINK
```

**Detection:** Lines starting with `import`.

### Zone 8: Tables (header row)

```markdown
| RAG Type | Description |  ← header row — don't link
|----------|-------------|
| Basic RAG | Simple...   |  ← body rows — OK to link
```

**Detection:** Table header rows (first row after blank line, before `|---|`).

---

## Edge Cases — Handle With Care

### Case 1: Term already linked elsewhere in sentence

```markdown
<!-- Input -->
Learn about [RAG systems](/en/glossary/rag/) and how retrieval-augmented generation works.

<!-- DON'T double-link the same term -->
<!-- Keep as-is — first link covers it -->
```

**Rule:** After linking a term, don't link synonyms/variations of the SAME term in the same file.

### Case 2: Possessives and contractions

```markdown
<!-- These should link: -->
RAG's architecture  →  [RAG](/en/glossary/rag/)'s architecture
LLM's output        →  [LLM](/en/glossary/llm/)'s output

<!-- Keep the possessive outside the link -->
```

**Rule:** Link the term, leave `'s` outside the brackets.

### Case 3: Plural forms

```markdown
<!-- Input -->
LLMs are increasingly used...

<!-- Output →  link the plural -->
[LLMs](/en/glossary/llm/) are increasingly used...
```

**Rule:** Standard plurals (`LLMs`, `embeddings`, `hallucinations`) can be linked.

### Case 4: Compound term collisions

```markdown
<!-- DANGER: "semantic" appears in multiple terms -->
semantic search    →  link to /glossary/semantic-search/
semantic similarity →  link to /glossary/semantic-similarity/

<!-- DON'T link bare "semantic" — it's too ambiguous -->
```

**Rule:** Always match the **longest matching phrase first**. Prefer multi-word exact matches over single words.

### Case 5: Word boundaries

```markdown
<!-- DON'T link partial matches -->
"pre-embedding"   ← don't link "embedding" inside this
"reRAGged"        ← don't link "RAG" inside this (hypothetical)
"transformers"    ← OK to link (standard plural)

<!-- Use word boundary regex: \b -->
```

**Rule:** Use `\b` word boundaries. Term must be standalone or naturally compounded.

### Case 6: Case sensitivity for code vs prose

```markdown
<!-- In prose: case-insensitive matching -->
"The LLM generates..."  →  link
"the llm generates..."  →  link

<!-- In code: NEVER link (Zone 2), but if you did... -->
llm_model = ...         →  DON'T link (it's a variable name)
```

**Rule:** Case-insensitive in prose. Code is excluded entirely.

### Case 7: Hyphenated vs space variants

```markdown
<!-- Both should match the same term -->
"machine learning"   →  /glossary/machine-learning/
"machine-learning"   →  /glossary/machine-learning/

<!-- The termSlug uses hyphens, anchor text matches source -->
```

**Rule:** Match both hyphenated and spaced forms, preserve original in anchor.

### Case 8: Definition proximity

```markdown
<!-- DON'T link if term is explained in same paragraph -->
RAG (Retrieval-Augmented Generation) is a technique that combines search with LLMs.
↑ term defined inline — no link needed

<!-- DO link if term is used without explanation -->
The RAG pipeline failed because the vector store was empty.
↑ assumes reader knows RAG — link it
```

**Rule:** Skip linking if the term is followed by parenthetical definition or "is a/means/refers to" in the same sentence.

### Case 9: Acronym-expansion collision

```markdown
<!-- Avoid linking both variants in same paragraph -->
"Large language models (LLMs) are..."

<!-- Link one, not both -->
"[Large language models](/en/glossary/llm/) (LLMs) are..."
<!-- OR -->
"Large language models ([LLMs](/en/glossary/llm/)) are..."
```

**Rule:** When acronym and expansion appear together, link only one (prefer expansion for readability).

### Case 10: Quoted terms

```markdown
<!-- Terms in quotes might be meta-commentary -->
The term "hallucination" is perhaps misleading...
          ↑ might be discussing the word itself, not the concept

<!-- Use judgment — if discussing terminology, maybe skip -->
```

**Rule:** If term is in quotes and sentence discusses naming/terminology, consider skipping.

### Case 11: Negated or comparative context

```markdown
<!-- These contexts are OK to link -->
"Unlike traditional RAG approaches..."  →  link RAG
"This is not a hallucination..."        →  link hallucination

<!-- Negation doesn't affect linking decision -->
```

**Rule:** Link regardless of negation — reader may still want definition.

### Case 12: Terms in blockquotes

```markdown
> "RAG systems represent a paradigm shift..." — Expert quote
```

**Rule:** OK to link in blockquotes, but use lighter touch (max 1-2 per quote).

### Case 13: Locale mismatch in URL

```markdown
<!-- Source: blog-fr.mdx -->

<!-- WRONG -->
[RAG](/en/glossary/rag/)

<!-- CORRECT -->
[RAG](/fr/glossary/rag/)
```

**Rule:** Extract locale from filename (`*-{locale}.mdx`) and use in all generated links.

### Case 14: Missing locale variant

```powershell
# Before linking to /de/glossary/rag/, verify:
Test-Path "website/src/content/glossary/rag-de.mdx"
```

**Rule:** If glossary term doesn't exist for target locale, skip the link entirely. Don't link to 404.

### Case 15: Trailing slash consistency

```markdown
<!-- ALWAYS use trailing slash for consistency -->
/en/glossary/rag/   ← CORRECT
/en/glossary/rag    ← AVOID (works but inconsistent)
```

**Rule:** All glossary links end with `/`.

---

## Term Recognition Patterns

### Core matching rules

For each glossary term, recognize these patterns (case-insensitive):

```python
# Pattern structure
{
  "termSlug": "rag",
  "primary": ["RAG", "retrieval-augmented generation"],
  "variations": ["RAG system", "RAG pipeline", "RAG-based"],
  "plurals": ["RAGs"],
  "exclude_patterns": [r"drag", r"brag", r"fragment"],  # false positives containing "rag"
  "definition_indicators": [r"means", r"refers to", r"is a", r"defined as", r"\("]
}
```

### Matching priority

1. **Longest match first** — "semantic search" before "semantic"
2. **Exact phrase** — prefer "vector database" over "vector" + "database"
3. **Primary forms** — prefer official term over variations
4. **Word boundaries** — use `\b` to prevent partial matches

### False positive prevention

| Term | False positive | Prevention |
|------|----------------|------------|
| `rag` | "drag", "brag", "fragment" | Require word boundary `\bRAG\b` |
| `llm` | "llm_variable" in code | Code zone exclusion |
| `temperature` | "room temperature", "body temperature" | Context filter: AI/ML proximity |
| `prompt` | "prompt delivery", "prompt action" | Context filter: AI/ML proximity |
| `pruning` | "tree pruning", "pruning shears" | Context filter: model/network proximity |
| `inference` | "statistical inference" | May be valid — judgment call |

### Context-sensitive terms

Some terms need surrounding context to validate:

```python
CONTEXT_SENSITIVE = {
    "temperature": ["LLM", "model", "sampling", "generation", "AI"],
    "prompt": ["LLM", "AI", "model", "ChatGPT", "GPT", "generation"],
    "pruning": ["model", "neural", "network", "weights", "parameters"],
    "attention": ["transformer", "self-attention", "multi-head", "mechanism"],
    "embedding": ["vector", "model", "semantic", "representation"]
}

def should_link(term, sentence):
    if term not in CONTEXT_SENSITIVE:
        return True  # always link non-ambiguous terms
    context_words = CONTEXT_SENSITIVE[term]
    return any(word.lower() in sentence.lower() for word in context_words)
```

### Glossary term → Pattern map

| termSlug | Primary forms | Common variations | Watch for |
|----------|---------------|-------------------|-----------|
| `llm` | LLM, large language model | LLMs, language model, foundation model | — |
| `rag` | RAG, retrieval-augmented generation | RAG system, RAG pipeline, RAG approach | drag, brag |
| `hallucination` | hallucination | hallucinations, AI hallucination, fabrication | — |
| `embeddings` | embedding, embeddings | vector embedding, embedding model | re-embedding |
| `semantic-search` | semantic search | semantic retrieval, meaning-based search | Don't link "semantic" alone |
| `semantic-similarity` | semantic similarity | similarity score | Don't link "semantic" alone |
| `vector-database` | vector database | vector DB, vector store | Don't link "vector" alone |
| `fine-tuning` | fine-tuning, fine tuning | fine-tuned, finetune | — |
| `prompt` | prompt | prompts, prompting, prompt engineering | Non-AI "prompt" |
| `tokenization` | tokenization | tokenize, tokens, tokenizer | — |
| `transformer-architecture` | transformer | transformer architecture, transformer model | Electrical transformer |
| `reranking` | reranking, re-ranking | reranker, re-rank, second-stage ranking | — |
| `hybrid-search` | hybrid search | hybrid retrieval, combined search | — |
| `query-expansion` | query expansion | query rewriting, query reformulation | — |
| `wib-cir` | WIB, CIR | Wetboek Inkomstenbelastingen, Code des Impôts | — |
| `eu-ai-act` | EU AI Act | AI Act, Regulation 2024/1689 | — |
| `high-risk-ai-system` | high-risk AI | high-risk system, high risk AI system | — |
| `human-oversight` | human oversight | human-in-the-loop, human review | — |
| `responsible-ai` | responsible AI | trustworthy AI, ethical AI | — |
| `indexing-strategy` | indexing strategy | indexing approach, index architecture | — |
| `relevance-tuning` | relevance tuning | relevance optimization, ranking tuning | — |
| `inference` | inference | model inference, AI inference | Statistical inference |
| `quantization` | quantization | quantized, quantize | — |
| `lora` | LoRA | low-rank adaptation | — |
| `qlora` | QLoRA | quantized LoRA | — |
| `rlhf` | RLHF | reinforcement learning from human feedback | — |
| `temperature` | temperature (AI context) | LLM temperature, sampling temperature | Physical temp |
| `top-k` | top-k | top k sampling | — |
| `top-p` | top-p | nucleus sampling | — |
| `perplexity` | perplexity | model perplexity | Confused state |
| `ner` | named entity recognition, NER | entity extraction | — |
| `knowledge-graph` | knowledge graph | KG, knowledge base | — |
| `faiss` | FAISS | Facebook AI Similarity Search | — |
| `pinecone` | Pinecone | Pinecone vector database | Pine tree |
| `hnsw` | HNSW | hierarchical navigable small world | — |
| `tf-idf` | TF-IDF | term frequency-inverse document frequency | — |
| `inverted-index` | inverted index | posting list | — |
| `full-text-search` | full-text search | full text search, FTS | — |
| `boolean-search` | boolean search | Boolean operators, AND/OR search | — |
| `sparse-retrieval` | sparse retrieval | keyword retrieval, lexical search | — |
| `machine-learning` | machine learning | ML, machine-learning | — |
| `neural-network` | neural network | neural net, NN | — |
| `gradient-descent` | gradient descent | gradient optimization | — |
| `loss-function` | loss function | objective function | — |
| `supervised-learning` | supervised learning | supervised ML | — |
| `unsupervised-learning` | unsupervised learning | unsupervised ML | — |
| `reinforcement-learning` | reinforcement learning | RL | — |
| `distillation` | distillation (AI context) | knowledge distillation, model distillation | Alcohol distillation |
| `pruning` | pruning (AI context) | model pruning | Garden pruning |
| `model-compression` | model compression | compression | — |
| `greedy-decoding` | greedy decoding | greedy search | — |
| `self-attention` | self-attention | self attention | — |
| `multi-head-attention` | multi-head attention | MHA | — |
| `instruction-tuning` | instruction tuning | instruction-tuned | — |

---

## Workflow

### Phase 1: Discovery

1. **Load term inventory**
   ```powershell
   # Get all English glossary terms
   Get-ChildItem "website/src/content/glossary/*-en.mdx" | 
     ForEach-Object { $_.BaseName -replace '-en$','' }
   ```

2. **Select target file(s)**
   - Single file: user specifies
   - Batch: all blog posts, or all glossary items
   - Scope: `website/src/content/blog/` or `website/src/content/glossary/`

3. **Scan for linkable terms**
   ```powershell
   # Find potential matches (example for RAG)
   Select-String -Path "website/src/content/blog/*-en.mdx" `
     -Pattern '\b(RAG|retrieval-augmented generation)\b' -CaseSensitive:$false
   ```

### Phase 2: Analysis

For each file, produce a **link opportunity table**:

| Line | Current text | Term | Action | New text |
|------|--------------|------|--------|----------|
| 45 | "...the RAG pipeline retrieves..." | rag | **Link** | "...the [RAG pipeline](/en/glossary/rag/) retrieves..." |
| 52 | "...RAG systems can..." | rag | Skip (duplicate) | — |
| 78 | "...hallucinations occur when..." | hallucination | **Link** | "...[[hallucinations](/en/glossary/hallucination/) occur when..." |

### Phase 3: Link insertion

Use `replace_string_in_file` to insert links:

```markdown
<!-- Before -->
The system uses retrieval-augmented generation to ground answers in source documents.

<!-- After -->
The system uses [retrieval-augmented generation](/en/glossary/rag/) to ground answers in source documents.
```

### Phase 4: Cross-locale sync

After linking EN, repeat for NL/FR/DE versions:

| EN anchor | NL anchor | FR anchor | DE anchor |
|-----------|-----------|-----------|-----------|
| retrieval-augmented generation | retrieval-augmented generation | génération augmentée par récupération | Retrieval-Augmented Generation |
| hallucination | hallucinatie | hallucination | Halluzination |
| semantic search | semantisch zoeken | recherche sémantique | semantische Suche |

Use locale-appropriate anchor text, but always same `termSlug` in URL.

---

## Outputs

### A) Link Insertion Plan (per file)

```markdown
# Link insertion plan: {filename}

## Summary
- Terms found: 12
- Linkable (first mentions): 5
- Links inserted: 5

## Links

| Line | Term | Anchor text | Link |
|------|------|-------------|------|
| 23 | rag | RAG | `/en/glossary/rag/` |
| 45 | hallucination | hallucinations | `/en/glossary/hallucination/` |
| 67 | embeddings | vector embeddings | `/en/glossary/embeddings/` |
...

## Skipped

| Line | Term | Reason |
|------|------|--------|
| 89 | rag | Duplicate (linked at L23) |
| 102 | embeddings | Already explained in context |
...
```

### B) Batch Summary (when processing multiple files)

```markdown
# Glossary link audit — blog collection

## Stats
- Files processed: 29
- Total links inserted: 87
- Average links per file: 3.0

## Most linked terms
| Term | Count |
|------|-------|
| rag | 15 |
| hallucination | 12 |
| llm | 11 |
...

## Orphan terms (never linked)
- `greedy-decoding`
- `multi-head-attention`
- `gradient-descent`
```

---

## Anti-Patterns

### ❌ Link soup

```markdown
<!-- BAD: too many links -->
[LLMs](/en/glossary/llm/) use [transformer](/en/glossary/transformer-architecture/) 
[architectures](/en/glossary/transformer-architecture/) with [attention](/en/glossary/self-attention/) 
mechanisms to generate [tokens](/en/glossary/tokenization/).
```

### ❌ Broken flow

```markdown
<!-- BAD: link interrupts key phrase -->
The [EU AI](/en/glossary/eu-ai-act/) Act requires...

<!-- GOOD: keep phrase intact -->
The [EU AI Act](/en/glossary/eu-ai-act/) requires...
```

### ❌ Self-referential

```markdown
<!-- In rag-en.mdx (the RAG glossary page itself) -->
<!-- BAD: linking to self -->
[RAG](/en/glossary/rag/) stands for...

<!-- GOOD: no link needed, this IS the definition -->
RAG stands for...
```

### ❌ Duplicate links

```markdown
<!-- BAD: same term linked twice -->
[RAG](/en/glossary/rag/) pipelines are powerful. When building a [RAG](/en/glossary/rag/) system...

<!-- GOOD: first mention only -->
[RAG](/en/glossary/rag/) pipelines are powerful. When building a RAG system...
```

### ❌ Awkward anchor

```markdown
<!-- BAD: forced anchor text -->
...stores vectors in a database that is a [vector database](/en/glossary/vector-database/)...

<!-- GOOD: natural anchor -->
...stores vectors in a [vector database](/en/glossary/vector-database/)...
```

---

## Glossary-to-Glossary Linking

Glossary items should link to related terms in their body text:

### Rules for glossary cross-links

1. **Never self-link** — a glossary page doesn't link to itself
2. **Max 3-5 links per glossary item** — glossary entries are short, don't overwhelm
3. **Prefer linking in "Why it matters" or "Practical example" sections**
4. **Use `related:` frontmatter array** for formal relationships
5. **Use body links for contextual mentions**

### Example: rag-en.mdx

```markdown
---
term: "Retrieval-Augmented Generation"
termSlug: "rag"
related: ["embeddings", "vector-database", "hallucination"]
...
---

## Definition

RAG combines [large language models](/en/glossary/llm/) with real-time document 
retrieval to reduce [hallucinations](/en/glossary/hallucination/).

## Why it matters

Traditional [LLMs](/en/glossary/llm/) — skip, already linked above — generate 
answers from training data alone. RAG grounds responses in actual documents 
stored in a [vector database](/en/glossary/vector-database/).
```

---

## Batch Mode

### Process all blog posts

```powershell
# Get all EN blog posts
$blogs = Get-ChildItem "website/src/content/blog/*-en.mdx"

# For each, run the linker workflow
foreach ($blog in $blogs) {
    # Scan, analyze, insert links
    # Then process NL/FR/DE variants
}
```

### Process all glossary items

```powershell
# Get all EN glossary items
$glossary = Get-ChildItem "website/src/content/glossary/*-en.mdx"

# For each, run cross-linking
foreach ($term in $glossary) {
    # Skip self-links
    # Find related terms mentioned
    # Insert first-mention links
}
```

---

## Quality Checks

### Pre-commit checklist

Before committing links:

**Structural integrity:**
- [ ] No duplicate links to same term in one file
- [ ] No self-links in glossary items
- [ ] All links use correct locale (matches source file)
- [ ] No links in excluded zones (frontmatter, code, headings)
- [ ] No nested links (link inside existing anchor text)
- [ ] All linked terms actually exist (no 404s)
- [ ] No links to draft glossary items

**Content quality:**
- [ ] Anchor text reads naturally in sentence
- [ ] Link doesn't break mid-phrase or mid-word
- [ ] Context-sensitive terms have appropriate surrounding context
- [ ] No false positives (e.g., "room temperature" → LLM temperature)

**Density & balance:**
- [ ] Link density is 3-7 per 1000 words (not excessive)
- [ ] Links distributed throughout article (not all in first paragraph)
- [ ] Related terms in frontmatter are linked in body where natural
- [ ] Important terms not missed

### Automated validation script

```powershell
function Invoke-LinkValidation {
    param([string]$filePath)
    
    $errors = @()
    $warnings = @()
    $content = Get-Content $filePath -Raw
    $locale = $filePath -replace '.*-([a-z]{2})\.mdx$','$1'
    
    # 1. Check for duplicate links
    $links = [regex]::Matches($content, '/[a-z]{2}/glossary/([^/]+)/')
    $slugs = $links | ForEach-Object { $_.Groups[1].Value }
    $duplicates = $slugs | Group-Object | Where-Object { $_.Count -gt 1 }
    if ($duplicates) {
        $errors += "Duplicate links: $($duplicates.Name -join ', ')"
    }
    
    # 2. Check locale consistency
    $wrongLocale = [regex]::Matches($content, "/([a-z]{2})/glossary/") | 
        Where-Object { $_.Groups[1].Value -ne $locale }
    if ($wrongLocale) {
        $errors += "Wrong locale in links (expected $locale)"
    }
    
    # 3. Check for dead links
    $links | ForEach-Object {
        $slug = $_.Groups[1].Value
        if (-not (Test-Path "website/src/content/glossary/$slug-$locale.mdx")) {
            $errors += "Dead link: /glossary/$slug/"
        }
    }
    
    # 4. Check link density
    $wordCount = ($content -split '\s+').Count
    $linkCount = $links.Count
    $density = $linkCount / ($wordCount / 1000)
    if ($density -gt 10) {
        $warnings += "High link density: $([math]::Round($density,1)) per 1000 words"
    }
    if ($density -lt 2 -and $wordCount -gt 500) {
        $warnings += "Low link density: $([math]::Round($density,1)) per 1000 words"
    }
    
    # 5. Check for links in headings
    $headingLinks = [regex]::Matches($content, '^#+.*\[.*\]\(/[a-z]{2}/glossary/', [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if ($headingLinks.Count -gt 0) {
        $errors += "Links found in headings"
    }
    
    return @{
        File = $filePath
        Errors = $errors
        Warnings = $warnings
        Links = $linkCount
        Words = $wordCount
        Valid = ($errors.Count -eq 0)
    }
}

# Run on single file
$result = Invoke-LinkValidation "website/src/content/blog/ai-hallucinaties-fiscaal-en.mdx"
if (-not $result.Valid) {
    Write-Host "ERRORS:" -ForegroundColor Red
    $result.Errors | ForEach-Object { Write-Host "  - $_" }
}
```

---

## Integration with Other Skills

### After blog publishing

Run glossary linker on new blog posts as the final polish step.

### After glossary creation

Run glossary linker on the new term to add cross-links, then scan existing content for linking opportunities to the new term.

### Periodic audit

Monthly batch run across all content to catch:
- New terms added to glossary but not linked anywhere
- Content updated but links not refreshed
- Broken links (term renamed/deleted)

---

## Quick Reference

### Link format by locale

```markdown
EN: [anchor text](/en/glossary/{termSlug}/)
NL: [anchor tekst](/nl/glossary/{termSlug}/)
FR: [texte d'ancrage](/fr/glossary/{termSlug}/)
DE: [Ankertext](/de/glossary/{termSlug}/)
```

### Common commands

```powershell
# Find all mentions of "RAG" in blog posts
Select-String -Path "website/src/content/blog/*.mdx" -Pattern '\bRAG\b'

# Find files missing glossary links
Select-String -Path "website/src/content/blog/*-en.mdx" -Pattern '/en/glossary/' -NotMatch

# Count links per file
Select-String -Path "website/src/content/blog/ai-hallucinaties-fiscaal-en.mdx" -Pattern '/en/glossary/' | Measure-Object
```

---

## Validation & Testing

### Pre-insertion validation

Before inserting any link, verify:

```powershell
# 1. Glossary term exists for all target locales
function Test-GlossaryExists {
    param([string]$termSlug, [string[]]$locales = @("en","nl","fr","de"))
    $missing = @()
    foreach ($locale in $locales) {
        $path = "website/src/content/glossary/$termSlug-$locale.mdx"
        if (-not (Test-Path $path)) {
            $missing += $locale
        }
    }
    return $missing
}

# 2. Term is not draft
function Test-NotDraft {
    param([string]$termSlug, [string]$locale)
    $path = "website/src/content/glossary/$termSlug-$locale.mdx"
    $content = Get-Content $path -Raw
    return $content -notmatch 'draft:\s*true'
}

# 3. Term isn't self-referencing (for glossary files)
function Test-NotSelfLink {
    param([string]$sourceFile, [string]$termSlug)
    $sourceTerm = [System.IO.Path]::GetFileNameWithoutExtension($sourceFile) -replace '-[a-z]{2}$',''
    return $sourceTerm -ne $termSlug
}
```

### Post-insertion validation

After inserting links, verify:

```powershell
# 1. No duplicate links in file
function Test-NoDuplicateLinks {
    param([string]$filePath)
    $content = Get-Content $filePath -Raw
    $matches = [regex]::Matches($content, '\[([^\]]+)\]\((/[a-z]{2}/glossary/[^)]+/)\)')
    $seen = @{}
    foreach ($match in $matches) {
        $url = $match.Groups[2].Value
        if ($seen.ContainsKey($url)) {
            return @{ Valid = $false; Duplicate = $url; Lines = @($seen[$url], $match.Index) }
        }
        $seen[$url] = $match.Index
    }
    return @{ Valid = $true }
}

# 2. Links use correct locale
function Test-LocaleConsistency {
    param([string]$filePath)
    $fileLocale = $filePath -replace '.*-([a-z]{2})\.mdx$','$1'
    $content = Get-Content $filePath -Raw
    $matches = [regex]::Matches($content, '/([a-z]{2})/glossary/')
    foreach ($match in $matches) {
        if ($match.Groups[1].Value -ne $fileLocale) {
            return @{ Valid = $false; Expected = $fileLocale; Found = $match.Groups[1].Value }
        }
    }
    return @{ Valid = $true }
}

# 3. No broken links (term exists)
function Test-NoDeadLinks {
    param([string]$filePath)
    $content = Get-Content $filePath -Raw
    $matches = [regex]::Matches($content, '/([a-z]{2})/glossary/([^/]+)/')
    $dead = @()
    foreach ($match in $matches) {
        $locale = $match.Groups[1].Value
        $slug = $match.Groups[2].Value
        $path = "website/src/content/glossary/$slug-$locale.mdx"
        if (-not (Test-Path $path)) {
            $dead += "/$locale/glossary/$slug/"
        }
    }
    return @{ Valid = ($dead.Count -eq 0); DeadLinks = $dead }
}
```

### Build validation

After linking, confirm site still builds:

```powershell
cd website
npm run build 2>&1 | Select-String -Pattern "error|Error|ERROR"
```

---

## Rollback Procedures

### Undo single file

If a file was incorrectly linked:

```powershell
# Option 1: Git restore (if not committed)
git checkout -- "website/src/content/blog/article-en.mdx"

# Option 2: Git revert (if committed)
git revert HEAD --no-commit  # then selectively restore

# Option 3: Manual removal
# Find and remove all glossary links from file
$content = Get-Content "website/src/content/blog/article-en.mdx" -Raw
$cleaned = $content -replace '\[([^\]]+)\]\(/[a-z]{2}/glossary/[^)]+/\)', '$1'
Set-Content "website/src/content/blog/article-en.mdx" -Value $cleaned
```

### Undo batch operation

If an entire batch run went wrong:

```powershell
# Reset all mdx files to last commit
git checkout HEAD -- "website/src/content/blog/*.mdx"
git checkout HEAD -- "website/src/content/glossary/*.mdx"
```

### Selective removal

Remove links to a specific term (e.g., if term was deleted):

```powershell
# Remove all links to /en/glossary/rag/ across blog posts
Get-ChildItem "website/src/content/blog/*-en.mdx" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $updated = $content -replace '\[([^\]]+)\]\(/en/glossary/rag/\)', '$1'
    if ($content -ne $updated) {
        Set-Content $_.FullName -Value $updated
        Write-Host "Removed RAG links from: $($_.Name)"
    }
}
```

---

## Troubleshooting

### Problem: Link inserted in wrong location

**Symptoms:** Link appears in code block, frontmatter, or heading.

**Diagnosis:**
```powershell
# Check if link is in excluded zone
Select-String -Path "file.mdx" -Pattern '\[.*\]\(/en/glossary/' -Context 3,3
```

**Solution:** Remove link manually, update zone detection logic.

### Problem: Same term linked multiple times

**Symptoms:** Article has 3+ links to same glossary term.

**Diagnosis:**
```powershell
# Count links per term
Select-String -Path "file.mdx" -Pattern '/en/glossary/rag/' | Measure-Object
```

**Solution:** Keep first link, remove duplicates:
```powershell
# Manual: find second occurrence and de-link
```

### Problem: Link to non-existent locale

**Symptoms:** 404 on German glossary link.

**Diagnosis:**
```powershell
# Verify term exists for locale
Test-Path "website/src/content/glossary/rag-de.mdx"
```

**Solution:** Either create missing locale file or remove the link.

### Problem: False positive linking

**Symptoms:** "The room temperature was..." incorrectly links "temperature" to LLM glossary.

**Diagnosis:** Context-sensitive term matched without AI context.

**Solution:** 
1. Add term to `CONTEXT_SENSITIVE` filter
2. Manually remove incorrect link
3. Improve proximity check

### Problem: Anchor text split across lines

**Symptoms:** 
```markdown
[retrieval-augmented
generation](/en/glossary/rag/)  ← broken rendering
```

**Solution:** Ensure anchor text is single-line. If replacing multi-word phrase, handle line breaks:
```powershell
# Normalize line breaks before matching
$content = $content -replace '(\w)\r?\n(\w)', '$1 $2'
```

### Problem: Nested link attempt

**Symptoms:** 
```markdown
[[RAG](/en/glossary/rag/) systems](/en/blog/...)  ← invalid markdown
```

**Diagnosis:** Attempted to link inside existing link anchor.

**Solution:** Zone 3 (existing links) detection should catch this. If not, improve regex:
```regex
# Detect existing link: \[([^\]]*)\]\([^)]+\)
# Skip matching inside first capture group
```

---

## Locale-Specific Anchor Text

### Common translations

| EN | NL | FR | DE |
|----|----|----|-----|
| retrieval-augmented generation | retrieval-augmented generation | génération augmentée par récupération | Retrieval-Augmented Generation |
| large language model | groot taalmodel | grand modèle de langage | großes Sprachmodell |
| hallucination | hallucinatie | hallucination | Halluzination |
| semantic search | semantisch zoeken | recherche sémantique | semantische Suche |
| vector database | vectordatabase | base de données vectorielle | Vektordatenbank |
| fine-tuning | fijnafstemming | réglage fin | Feinabstimmung |
| embedding | inbedding | plongement | Einbettung |
| knowledge graph | kennisgraaf | graphe de connaissances | Wissensgraph |
| inference | inferentie | inférence | Inferenz |
| EU AI Act | EU AI-verordening | Règlement européen sur l'IA | EU-KI-Verordnung |

### When to translate vs preserve

- **Preserve English:** Technical acronyms (RAG, LLM, RLHF, FAISS)
- **Translate:** Full terms that have established translations
- **Mixed:** "EU AI Act" → German "EU-KI-Verordnung" but French keeps "AI Act"

### Locale validation matrix

Before batch processing, verify anchor translations exist:

```powershell
$terms = @("rag", "llm", "hallucination", "embeddings")
$locales = @("en", "nl", "fr", "de")

foreach ($term in $terms) {
    foreach ($locale in $locales) {
        $path = "website/src/content/glossary/$term-$locale.mdx"
        if (Test-Path $path) {
            $content = Get-Content $path -First 10
            $termName = ($content | Select-String -Pattern '^term:\s*"([^"]+)"').Matches.Groups[1].Value
            Write-Host "$term-$locale : $termName"
        } else {
            Write-Host "$term-$locale : MISSING" -ForegroundColor Red
        }
    }
}
```

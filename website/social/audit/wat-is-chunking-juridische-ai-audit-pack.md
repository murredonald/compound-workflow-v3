# Audit pack — wat-is-chunking-juridische-ai

## Post details
- **Slug**: wat-is-chunking-juridische-ai
- **Category**: ai-explained
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | Claude 200K tokens, GPT-4.1 1M tokens | PARTIALLY VERIFIED — Claude also supports 1M tokens by publication date | Fixed to "both support up to a million tokens" |
| 2 | "Lost in the middle" effect (Liu et al. 2024) | VERIFIED — TACL 12, 157-173, arXiv:2307.03172 | Added full citation with DOI |
| 3 | €2-15 per query for 1M tokens | PLAUSIBLE — accurate for GPT-4.1 and Claude Sonnet; low for Opus | Kept (range covers most-used models) |
| 4 | WIB 92 has over 500 articles | VERIFIED — articles numbered to 551+ with bis/ter variants | Kept |
| 5 | Single article can run 2,000-3,000 words | PLAUSIBLE — true for longest articles; unverifiable at precision | Kept |
| 6 | Article 171 WIB 92 structure (separate taxation) | VERIFIED — standard Belgian tax provision | Kept |
| 7 | VCF hierarchical numbering system | VERIFIED — e.g. Art. 2.10.4.0.1 encodes position | Kept |
| 8 | "behoudens/tenzij/mits" pattern in Belgian law | VERIFIED — standard Belgian legislative drafting pattern | Kept |

## Changes applied (all 4 locales)

1. **Context window claim**: Changed "Claude processes up to 200,000 tokens, GPT-4.1 handles a million" → "both Claude and GPT-4.1 now support up to a million tokens" — Claude 1M context available since late 2025/early 2026
2. **Liu et al. citation**: Added full authors, DOI link, and volume/page: "Liu, N.F. et al. (2024). [Lost in the Middle](https://doi.org/10.1162/tacl_a_00638). Transactions of the ACL, 12, 157-173."

## Flagged but not changed

- The €2-15 per query range understates cost for Opus-class models ($30/M input tokens for long context), but the post says "depending on the model" which provides adequate qualification
- "2,000-3,000 words" for long Belgian tax articles is plausible but not independently verifiable — kept as it illustrates the point without making a precise factual claim
- ResearchGate, Milvus, Weaviate, and Elvex citations are industry/blog sources — acceptable for a technical explainer post about chunking methodology

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | Clear chunking definition, code hierarchy diagram, pipeline chain |
| Authoritative citations | 1/2 | Liu et al. (TACL) is strong; other sources are industry blogs |
| Concise extractable answers | 2/2 | "What is chunking" definition, three reasons why needed, three evaluation questions |
| Logical structure | 2/2 | Why chunks → naive chunking fails → legal-boundary chunking → metadata → cascade → practitioner advice |
| Specificity | 2/2 | Real Belgian articles (171, 215 WIB 92), VCF numbering, behoudens/tenzij/mits pattern |
| Freshness signals | 1/2 | 2024-2026 model specs mentioned but no specific Belgian law changes referenced |
| **Total** | **10/12** | |

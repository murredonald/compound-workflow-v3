# Audit pack — wat-is-reranking

## Post details
- **Slug**: wat-is-reranking
- **Category**: ai-explained
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | Cross-encoders process query-document pairs jointly | VERIFIED — standard architecture distinction | Kept |
| 2 | Bi-encoders encode query and document independently | VERIFIED — standard architecture distinction | Kept |
| 3 | Cross-encoders are too slow for full-corpus search | VERIFIED — O(n) vs O(1) lookup, standard IR knowledge | Kept |
| 4 | Harvey AI BigLaw Bench: 30% improvement with reranking | VERIFIED — Harvey benchmarks | Kept |
| 5 | Elastic: 39% improvement with reranker | VERIFIED — Elastic search relevance benchmarks | Kept |
| 6 | Nogueira & Cho (2019) passage re-ranking with BERT | VERIFIED — seminal paper on neural reranking | Kept |
| 7 | Khattab & Zaharia (2020) ColBERT | VERIFIED — Stanford ColBERT paper | Kept |
| 8 | Two-stage retrieval: fast recall → precise reranking | VERIFIED — standard IR pipeline architecture | Kept |

## Changes applied
None — all claims verified.

## Flagged but not changed
- NL/FR/DE "Related articles" sections may contain EN-locale URLs — systematic localization issue

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | Bi-encoder vs cross-encoder comparison, pipeline diagram description |
| Authoritative citations | 2/2 | Nogueira & Cho, Khattab & Zaharia, Harvey, Elastic — all verified |
| Concise extractable answers | 2/2 | Clear "what is reranking" definition, concrete improvement percentages |
| Logical structure | 2/2 | Problem → first-stage → reranking → comparison → evaluation |
| Specificity | 2/2 | 30% and 39% improvements, Belgian tax law retrieval examples |
| Freshness signals | 2/2 | Harvey 2024, Elastic 2024 benchmarks |
| **Total** | **12/12** | |

# Audit pack — hybride-zoektechnologie

## Post details
- **Slug**: hybride-zoektechnologie
- **Category**: ai-explained
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | BM25 is a keyword/sparse retrieval algorithm | VERIFIED — standard IR textbook knowledge | Kept |
| 2 | BM25 uses TF-IDF weighting with document length normalization | VERIFIED | Kept |
| 3 | Semantic search uses dense vector embeddings | VERIFIED — standard NLP/IR knowledge | Kept |
| 4 | Reciprocal Rank Fusion (RRF) combines ranked lists | VERIFIED — Cormack et al. (2009) | Kept |
| 5 | RRF formula: 1/(k+rank) with k=60 default | VERIFIED — original RRF paper | Kept |
| 6 | BM25 excels at exact article number lookups | VERIFIED — well-established IR finding | Kept |
| 7 | Semantic search captures conceptual similarity | VERIFIED — standard embedding behavior | Kept |
| 8 | Hybrid outperforms either method alone | VERIFIED — consistent finding across BEIR, MTEB benchmarks | Kept |
| 9 | Rosa et al. (2023) BM25 strong baseline in COLIEE | VERIFIED — COLIEE legal retrieval competition results | Kept |
| 10 | Karpukhin et al. (2020) DPR paper | VERIFIED — Facebook AI Research, widely cited | Kept |

## Changes applied
None — all claims verified.

## Flagged but not changed
- NL/FR/DE "Related articles" sections may contain EN-locale URLs — systematic localization issue, not a factual error

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | BM25 vs semantic comparison table, RRF formula, worked example |
| Authoritative citations | 2/2 | Karpukhin et al. (DPR), Cormack et al. (RRF), Rosa et al. (COLIEE) |
| Concise extractable answers | 2/2 | Clear definitions, concrete Belgian tax examples |
| Logical structure | 2/2 | Problem → BM25 → semantic → hybrid → RRF → evaluation |
| Specificity | 2/2 | Exact formula, specific Belgian article examples, concrete retrieval scenarios |
| Freshness signals | 2/2 | 2023-2024 citations, current Belgian tax law examples |
| **Total** | **12/12** | |

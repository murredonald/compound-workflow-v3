# Audit pack: wat-is-rag

**Audited:** 2026-02-14
**Post date:** 2026-02-14
**Locales corrected:** EN, NL, FR, DE

---

## A) Claim ledger

| claim_id | type | risk | drift | disposition | authority tier | notes |
|----------|------|------|-------|-------------|----------------|-------|
| C001 | TAX_LAW | medium | low | VERIFIED | T1 | 29.58% for AJ 2019 correct |
| C002 | COMPETITOR | high | high | CORRECTED | T3 | Harvey funding now $1.2B; approach evolved beyond fine-tuning |
| C003 | TECH_MECHANISM | low | low | VERIFIED | — | RAG concept, BM25, RRF, cross-encoder all standard NLP |
| C004 | STATISTIC | medium | medium | VERIFIED | T1 | 17-33% and 58-88% (cross-ref posts 1-2) |
| C005 | CITATION | medium | low | CORRECTED | — | Schwarcz has 6 authors, not 2; fixed to "et al." |
| C006 | CITATION | low | low | VERIFIED | — | Lewis (2020) and Magesh (2025) both correct |

## B) Change log

1. **Harvey funding**: "hundreds of millions" → "over a billion dollars" (actual: $1.2B as of Feb 2026)
2. **Harvey approach**: Added "initially" — Harvey has since evolved to multi-model orchestration
3. **Citations**: Added dofollow links to all 3; fixed Schwarcz to "et al." (6 authors)

## C) Visual actions

| Visual | Action | Reason |
|--------|--------|--------|
| rag-pipeline-steps-*-dark.png | KEEP | Architecture description unchanged |
| fine-tuning-vs-rag-comparison-*-dark.png | KEEP | Comparison still architecturally valid |

## D) GEO score: 10/12

Strong educational content; clear RAG definition; structured comparisons. Missing explicit Q&A section.

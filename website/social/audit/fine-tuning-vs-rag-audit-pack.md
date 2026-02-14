# Audit pack — fine-tuning-vs-rag

**Audited:** 2026-02-14
**Locales:** en, nl, fr, de

## Claim ledger

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| C001 | Harvey raised over a billion dollars | VERIFIED | Harvey AI blog — Series E announcement; total funding now ~$1.2B |
| C002 | Harvey built system on fine-tuning | VERIFIED | Harvey blog + media coverage |
| C003 | 97% lawyer preference for Harvey custom model | VERIFIED | Referenced in Harvey materials and Bloomberg reporting |
| C004 | Programmawet July 2025 changed investment deduction regime | VERIFIED | Belgian legislative record |
| C005 | Fine-tuning costs $10-50k per iteration | VERIFIED | Industry estimates consistent with published ranges |
| C006 | RAFT = Retrieval-Augmented Fine-Tuning | VERIFIED | Term used in academic literature |
| C007 | Citation 2 author listed as "Ovadia, O." for arXiv:2403.01432 | WRONG | Actual authors: Soudani, H., Kanoulas, E. & Hasibi, F. |
| C008 | Capital gains tax legislated 2025 | VERIFIED | Legislated in 2025, effective 2026; context is defensible |

## Change log

| Locale | Line | Old | New | Reason |
|--------|------|-----|-----|--------|
| en | 13 | raised over $800 million | raised over a billion dollars | Already fixed in prior session — Harvey total funding now ~$1.2B |
| nl | 13 | meer dan 800 miljoen dollar | meer dan een miljard dollar | Same |
| fr | 13 | plus de 800 millions de dollars | plus d'un milliard de dollars | Same |
| de | 13 | über 800 Millionen Dollar | über eine Milliarde Dollar | Same |
| all | citations | Ovadia, O. et al. (2024) | Soudani, H., Kanoulas, E. & Hasibi, F. (2024) | Wrong author attribution — arXiv:2403.01432 is by Soudani et al. |
| all | citations | No dofollow links | Added dofollow links to all 3 citations | Harvey blog, arXiv papers |

## Visual audit

- `fine-tuning-vs-rag-comparison-en-dark.png` — comparison table graphic, 7 criteria. Content matches article table. OK.
- `architecture-decision-tree-en-dark.png` — decision tree. Content is advisory, no factual claims to verify. OK.
- NL/FR/DE have localized equivalents. OK.

## GEO audit

| Dimension | Score | Note |
|-----------|-------|------|
| Structured data (tables, lists) | 2 | Comparison table + limitation bullets |
| Definitional clarity | 2 | Clear "What X actually does" sections |
| Source attribution | 2 | Per-claim citations with dofollow links (after fix) |
| Quotable passages | 2 | Blockquote freshness test + multiple quotable lines |
| Internal linking | 1 | 3 related articles but no glossary links |
| Comparative framing | 2 | Full fine-tuning vs. RAG comparison table |
| **Total** | **11/12** | |

# Audit pack: chatgpt-vs-auryth-vergelijking

**Audited:** 2026-02-14
**Post date:** 2026-02-13
**Locales corrected:** EN, NL, FR, DE

---

## A) Claim ledger

| claim_id | type | risk | drift | disposition | authority tier | best sources | notes |
|----------|------|------|-------|-------------|----------------|--------------|-------|
| C001 | TAX_LAW | high | high | VERIFIED | T1 | PwC Belgium, FPS Finance | Standard 25% corporate tax rate |
| C002 | TAX_LAW | high | high | VERIFIED | T1 | PwC Belgium, Art. 215 WIB 92 | 20% SME rate on first €100K |
| C003 | TAX_LAW | medium | low | VERIFIED | T1 | Fiscosearch, FPS Finance | Art. 215 WIB 92 reference |
| C004 | TAX_LAW | high | high | CORRECTED | T1/T2 | Practicali, DVP-Law, BDO | Dividend distribution ceiling abolished in 2018 reform; removed from text |
| C005 | TAX_LAW | high | high | VERIFIED | T2/T3 | Curvo, Taxpatria | TOB rates 0.12%, 0.35%, 1.32% |
| C006 | TAX_LAW | high | high | VERIFIED | T2/T3 | Curvo, BUX | Accumulating ETF registered BE = 1.32% |
| C007 | TAX_LAW | high | high | VERIFIED | T2/T3 | Curvo, Fire Belgium | Accumulating ETF EEA (not BE) = 0.12% |
| C008 | STATISTIC | low | low | VERIFIED | math | 1.32/0.12 = 11 | Elevenfold difference confirmed |
| C009 | TAX_LAW | medium | medium | VERIFIED | T2 | Curvo, FSMA portal | FSMA compartment registration rule |
| C010 | TAX_LAW | high | high | VERIFIED | T2/T3 | Curvo, BUX | Distributing ETFs = 0.12% |
| C011 | TAX_LAW | high | high | VERIFIED | T2/T3 | Curvo, Taxpatria | Non-EEA = 0.35% |
| C012 | TAX_LAW | high | high | VERIFIED | T1 | PwC BE, Denis-Emmanuel Philippe | Art. 19bis WIB 92 Reynders tax |
| C013 | TAX_LAW | medium | medium | VERIFIED | T2/T3 | NN Insurance, Wikifin | Premium tax 2% on TAK 23 |
| C014 | TAX_LAW | medium | low | VERIFIED | T1/T2 | VCF Art. 2.7.1.0.6, Pareto | Gift/inheritance tax per region |
| C015 | TAX_LAW | medium | medium | VERIFIED | T2/T3 | House of Finance, AXA, Wikifin | TOB exemption within TAK 23 wrapper |
| C016 | TAX_LAW | high | high | VERIFIED | T1/T2 | Eubelius, EY Belgium, BNP Paribas | Effectentaks 0.15% > €1M |
| C017 | TAX_LAW | high | high | CORRECTED | T2/T3 | PwC BE, BDO, Freshfields | TAK 23 NOT exempt (look-through applies); fixed in all locales |
| C018 | TAX_LAW | medium | low | VERIFIED | multiple | All TAK 23 sources | At least 5 domains confirmed |
| C019 | STATISTIC | high | medium | CORRECTED | T1 (academic) | Dahl et al. (2024), JLA | 58-88% is range across LLMs (GPT-4 to Llama 2), not just ChatGPT; fixed |
| C020 | STATISTIC | high | medium | VERIFIED | T1 (academic) | Magesh et al. (2025), JELS | 17-33% for Lexis+AI, Westlaw AI |
| C021 | TECH_MECHANISM | medium | low | VERIFIED | T1 (academic) | Magesh et al. (2025) | RAG tools hallucinate less than standalone LLMs |
| C022 | CITATION | high | low | CORRECTED | — | Oxford Academic JLA | Wrong title; corrected to "Large Legal Fictions"; added DOI link |
| C023 | CITATION | high | low | CORRECTED | — | Wiley/arXiv | First author is Magesh not Dahl; corrected |
| C024 | CITATION | high | low | REMOVED | — | Harvard JOLT Digest | Fabricated: not Choi, not 2024, not peer-reviewed; replaced with Lewis et al. (2020) RAG paper |
| C025 | CITATION | medium | low | CORRECTED | — | EY NL website | Year corrected from 2024 to 2023; link added |

---

## B) Source register

| source_id | title | publisher | date | accessed | tier | URL |
|-----------|-------|-----------|------|----------|------|-----|
| S01 | Corporate taxes on income | PwC Belgium | 2025 | 2026-02-14 | T3 | https://taxsummaries.pwc.com/belgium/corporate/taxes-on-corporate-income |
| S02 | Art. 215 WIB 92 | Fiscosearch | — | 2026-02-14 | T1 | https://fiscosearch.be/article/4d5467ad-3cdd-4850-a451-c66e23b57653 |
| S03 | Hervorming vennootschapsbelasting | Practicali | — | 2026-02-14 | T3 | https://www.practicali.be/blog/hervorming-vennootschapsbelasting |
| S04 | Minimumbezoldiging verlaagd tarief | DVP-Law | — | 2026-02-14 | T3 | https://www.dvp-law.com/nl/nieuws/de-vereiste-van-de-minimumbezoldiging-... |
| S05 | TOB guide | Curvo | 2025 | 2026-02-14 | T4 | https://curvo.eu/article/tob |
| S06 | ETF taxation Belgium | Taxpatria | — | 2026-02-14 | T3 | https://www.taxpatria.be/faq/how-are-exchange-traded-funds-etfs-taxed-in-belgium/ |
| S07 | Art. 19bis BITC practice note | PwC Belgium | — | 2026-02-14 | T3 | https://news.pwc.be/belgian-tax-on-savings-income-art-19bis-bitc-important-practice-note/ |
| S08 | Capital gains on funds units | Denis-Emmanuel Philippe | — | 2026-02-14 | T3 | https://denisemmanuelphilippetax.be/en/uncategorized/capital-gains-on-funds-units-... |
| S09 | Wat is tak 23 | Wikifin | — | 2026-02-14 | T2 | https://www.wikifin.be/nl/sparen-en-beleggen/beleggingsproducten/verzekeringsproducten/levensverzekering-tak-23/wat-tak-23 |
| S10 | Erfbelasting schenking levensverzekering | Pareto | — | 2026-02-14 | T3 | https://pareto.be/nl/erfbelasting-verschuldigd-bij-het-schenken-van-een-levensverzekeringscontract/ |
| S11 | Securities accounts 0.15% | Eubelius | — | 2026-02-14 | T3 | https://www.eubelius.com/en/news/securities-accounts-are-subject-to-an-annual-tax-of-015-again |
| S12 | Exemptions financial sector | PwC Belgium | — | 2026-02-14 | T3 | https://news.pwc.be/new-tax-on-securities-accounts-exemptions-for-the-financial-sector/ |
| S13 | Large Legal Fictions | Oxford Academic (JLA) | 2024 | 2026-02-14 | T1 | https://academic.oup.com/jla/article/16/1/64/7699227 |
| S14 | Hallucination-Free? | Wiley (JELS) | 2025 | 2026-02-14 | T1 | https://onlinelibrary.wiley.com/doi/abs/10.1111/jels.12413 |
| S15 | RAG paper (arXiv) | Magesh et al. | 2024 | 2026-02-14 | T1 | https://arxiv.org/abs/2405.20362 |
| S16 | RAG for NLP Tasks | Lewis et al. (NeurIPS) | 2020 | 2026-02-14 | T1 | https://arxiv.org/abs/2005.11401 |
| S17 | Is ChatGPT uw nieuwe belastingadviseur? | EY Nederland | 2023 | 2026-02-14 | T3 | https://www.ey.com/nl_nl/insights/tax/is-chatgpt-uw-nieuwe-belastingadviseur |

---

## C) Change log

### Corrections applied (all 4 locales):

1. **Art. 215 conditions** — Removed "dividend distribution ceiling" (abolished in 2018 reform). Kept remuneration requirement + participation threshold.
2. **Effectentaks & TAK 23** — Changed "may be exempt under certain conditions" to "applies through look-through principle." TAK 23 is generally NOT exempt.
3. **Hallucination rate attribution** — Changed "ChatGPT's 58-88% rate" to "general-purpose LLMs" since the range spans GPT-4 (58%) to Llama 2 (88%).
4. **Image source attribution** — Changed "Dahl et al. (2024, 2025)" to "Dahl et al. (2024); Magesh et al. (2025)" since the 2025 paper's first author is Magesh.
5. **Citation 1** — Fixed title from news headline to actual paper title "Large Legal Fictions"; added DOI link.
6. **Citation 2** — Changed first author from "Dahl, M." to "Magesh, V."; added arXiv link.
7. **Citation 3** — REMOVED fabricated Choi citation (was actually a 2025 student blog post, not a 2024 peer-reviewed article). Replaced with Lewis et al. (2020) RAG paper.
8. **Citation 4** — Fixed year from 2024 to 2023; added URL link.

### Claims removed:
- Dividend distribution ceiling as current Art. 215 condition
- TAK 23 effectentaks exemption claim
- Fabricated Choi et al. citation

---

## D) Visual actions

| Visual | Action | Reason |
|--------|--------|--------|
| hallucination-rate-gap-dark.png | KEEP | Source attribution updated in alt text; data (58-88% vs 17-33%) still accurate |
| chatgpt-vs-specialized-tax-ai-comparison-dark.png | KEEP | No claims changed that affect this comparison table graphic |

---

## E) GEO score

| Dimension | Score | Notes |
|-----------|-------|-------|
| Domain-agnostic content | 1/2 | Article is domain-specific by design; concepts explained well but tightly coupled to Belgian tax |
| TL;DR / definition | 1/2 | No explicit TL;DR block, but the intro paragraph functions as a summary |
| Q&A pairs | 0/2 | No explicit Q&A section |
| Claim-with-source (linked) | 2/2 | Citations now all have dofollow links; inline claims reference specific articles |
| Structured comparisons | 2/2 | Comparison table present with 6 dimensions |
| Entity clarity | 2/2 | WIB 92, VCF, FSMA, WBTW all mentioned; Auryth TX named explicitly |
| **Total** | **8/12** | Meets minimum threshold |

---

## F) Risk flags

- **Defamation risk:** LOW — No accusations against ChatGPT/OpenAI; factual comparison based on experiment results
- **Drift risk:** MEDIUM — TOB rates, effectentaks threshold, corporate tax conditions are high-drift; verify annually
- **2026 capital gains tax:** NOT MENTIONED — Belgium introduced a 10% capital gains tax from Jan 2026 that affects TAK 23; may warrant a follow-up article

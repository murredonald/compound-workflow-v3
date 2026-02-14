# Audit pack: ai-hallucinaties-fiscaal

**Audited:** 2026-02-14
**Post date:** 2026-02-13
**Locales corrected:** EN, NL, FR, DE

---

## A) Claim ledger

| claim_id | type | risk | drift | disposition | authority tier | best sources | notes |
|----------|------|------|-------|-------------|----------------|--------------|-------|
| C001 | STATISTIC | high | medium | VERIFIED | T1 (academic) | Dahl et al. (2024), Magesh et al. (2025) | 17-33% and 58-88% hallucination rates |
| C002 | TAX_LAW | low | low | VERIFIED | T1 | WIB 92 | Art. 344 WIB is general anti-abuse provision |
| C003 | TAX_LAW | low | high | VERIFIED | verified in post 1 audit | — | TOB rates 0.12% vs 1.32% |
| C004 | TECH_MECHANISM | medium | low | VERIFIED | T1 (academic) | Xu et al. (2024) arXiv:2401.11817 | Mathematical inevitability of hallucination proven |
| C005 | TECH_MECHANISM | medium | medium | VERIFIED | T1 (academic) | Kalai et al. (2025) arXiv:2509.04664 | Training rewards confidence over honesty |
| C006 | INSTITUTIONAL_FACT | medium | low | VERIFIED | T2 | OVB website, Jan 2025 | AI guidelines for lawyers confirmed |
| C007 | STATISTIC | high | high | VERIFIED | T3 | Charlotin database, TheNewzzy | ~712 cases by late 2025; "over 700" accurate |
| C008 | STATISTIC | high | medium | VERIFIED | T3 | Reason.com, ABA Journal | $2,000 (Smith v. Farwell) to $31,100 (Lacey v. State Farm) |
| C009 | INSTITUTIONAL_FACT | high | high | VERIFIED | T3 | ABA Journal, Reason.com | 3 Aug 2025 federal cases confirmed (one declined monetary sanctions) |
| C010 | CITATION | high | low | CORRECTED | — | Oxford Academic JLA | Dahl title fixed to "Large Legal Fictions" |
| C011 | CITATION | medium | low | CORRECTED | — | arXiv | Kalai paper: added 2 missing authors (Vempala, Zhang) |

---

## B) Change log

### Corrections applied (all 4 locales):
1. **Citation 1 (Dahl 2024)**: Fixed title from news headline "Hallucinating Law" to actual paper title "Large Legal Fictions"; added DOI link
2. **Citation 4 (Kalai 2025)**: Added 2 missing co-authors (Vempala, S.S. & Zhang, E.); added arXiv link
3. **All citations**: Added dofollow links to source URLs

### Claims removed: None

---

## C) Visual actions

| Visual | Action | Reason |
|--------|--------|--------|
| ai-hallucination-myths-vs-reality-dark.png | KEEP | No factual claims in the graphic were invalidated |
| ai-hallucination-rates-by-the-numbers-dark.png | KEEP | Statistics verified; graphic data still accurate |

---

## D) GEO score

| Dimension | Score | Notes |
|-----------|-------|-------|
| Domain-agnostic content | 2/2 | Strong: hallucination concept explained generally before domain application |
| TL;DR / definition | 2/2 | Clear "What is an AI hallucination?" section with concise definition |
| Q&A pairs | 0/2 | No explicit Q&A section |
| Claim-with-source (linked) | 2/2 | Citations now all have dofollow links |
| Structured comparisons | 2/2 | "Five tells" table + "verification stack" table |
| Entity clarity | 2/2 | Art. 344 WIB, OVB, FSMA all named; full terms provided |
| **Total** | **10/12** | Exceeds minimum |

---

## E) Risk flags

- **Drift risk:** HIGH for case count (700+) and sanctions amounts — these grow monthly
- **August 2025 cases nuance:** One of the three courts (Rahman) declined monetary sanctions due to personal circumstances but did find Rule 11 violations

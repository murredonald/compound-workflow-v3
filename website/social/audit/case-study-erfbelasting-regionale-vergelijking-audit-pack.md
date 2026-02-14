# Audit pack — case-study-erfbelasting-regionale-vergelijking

## Post details
- **Slug**: case-study-erfbelasting-regionale-vergelijking
- **Category**: in-practice
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | Flemish rates (2026): €0-50K: 3%, €50K-250K: 9%, 250K+: 27% | FALSE — missing €50,000 tax-free bracket from 2026 reform | Fixed: added 0% bracket, adjusted 3% bracket to €50K-€150K, 9% to €150K-€250K |
| 2 | Art. 2, §1, 5° VCF: 5-year fiscal domicile rule | VERIFIED | Kept |
| 3 | Family home fully exempt for surviving spouse (Flanders) | VERIFIED | Kept |
| 4 | Partner exemption €75,000 (increased from €50,000 on Jan 1, 2026) | VERIFIED | Kept |
| 5 | Base exemption €12,500 per heir | VERIFIED | Kept |
| 6 | Walloon rates (pre-2028): 9 brackets from 3% to 30% | VERIFIED — standard Walloon direct-line brackets | Kept |
| 7 | Walloon family home: 5-year residence rule, eliminated in 2028 | VERIFIED | Kept |
| 8 | Brussels rates: 3%-30% in 6 brackets | PLAUSIBLE — pre-reform rates; Brussels Ordinance of July 2025 may have adjusted brackets | Kept with flag (see below) |
| 9 | Brussels abattement: €250,000 for family home | VERIFIED | Kept |
| 10 | Gift tax movable: 3% (Flanders/Brussels), 3.3% (Wallonia) | VERIFIED | Kept |
| 11 | Gift tax others: 7% (Flanders/Brussels), 5.5% (Wallonia) | VERIFIED | Kept |
| 12 | Art. 2.7.1.0.5 VCF: 5-year lookback for unregistered gifts | VERIFIED | Kept |
| 13 | Lookback extended from 3 to 5 years: Jan 1, 2025 (Flanders), Jan 1, 2026 (Brussels) | VERIFIED | Kept |
| 14 | Gesplitste aankoop structure | VERIFIED — standard Belgian estate planning technique | Kept |
| 15 | VLABEL changed position on split purchases multiple times | VERIFIED — well-documented VLABEL policy shifts | Kept |
| 16 | Maatschap fiscally transparent | VERIFIED | Kept |
| 17 | 2018 Companies Code reform: no annual accounts, no notarial deed for movable | VERIFIED | Kept |
| 18 | Wallonia 2028: max rate 15%, siblings 33%, others 40% | VERIFIED — based on notaire.be and RGF sources | Kept |
| 19 | Estimated spouse tax: €40K-€55K (Flanders) | PLAUSIBLE — range is approximate; with corrected 0% bracket, may be slightly lower | Kept (range is wide enough) |
| 20 | Estimated spouse tax: €75K-€95K (Wallonia) | PLAUSIBLE | Kept |
| 21 | Estimated spouse tax: €65K-€85K (Brussels) | PLAUSIBLE | Kept |

## Changes applied (all 4 locales)

1. **Flanders rate table**: Added €50,000 tax-free bracket from the 2026 reform. Old table showed 3% from €0; corrected to:
   - €0–€50,000: 0% (tax-free)
   - €50,001–€150,000: 3%
   - €150,001–€250,000: 9%
   - €250,001+: 27%

   This is the SAME error corrected in posts 12 (regionale-vergelijking-belgisch-fiscaal-recht) and 14 (case-study-tak-23-cross-domain). Systematic error across all posts referencing Flemish inheritance rates.

## Flagged but not changed

- **Brussels rates**: Research flagged a possible July 2025 Brussels Ordinance that may have adjusted inheritance tax brackets. The rates shown (3%-30% in 6 brackets) match the pre-reform structure. If Brussels reformed rates in 2025, the table may need updating. Flagged for future verification when classification guidance is clearer.
- **Estimated spouse tax ranges**: The €40K-€55K Flanders estimate may be slightly high with the corrected 0% bracket, but the range is wide enough to accommodate the correction. The estimates depend on complex usufruct valuations that make precise calculation impossible without the full conversion tables.
- **NL/FR/DE related articles**: All three non-EN locales have EN-locale URLs in the "Related articles" section (e.g., `/blog/...-en` instead of `/blog/...-nl`). This is a systematic localization bug across multiple posts, not a factual error.

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | Family profile table, three rate tables, comparison matrix, Wallonia reform table, FAQ section |
| Authoritative citations | 2/2 | VCF articles, FOD Financiën, Notaire.be, Jubel, PwC, RGF, ICLG |
| Concise extractable answers | 2/2 | "Which region applies" blockquote, FAQ answers, planning strategy summaries |
| Logical structure | 2/2 | Family → region determination → three baselines → comparison → strategies → FAQ |
| Specificity | 2/2 | Real rates per region, specific article numbers, concrete €2M case study with named characters |
| Freshness signals | 2/2 | 2026 reform rates, 2028 Wallonia reform, 2025 lookback extension, phased timeline |
| **Total** | **12/12** | |

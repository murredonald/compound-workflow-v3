# Audit pack — case-study-tak-23-cross-domain

## Post details
- **Slug**: case-study-tak-23-cross-domain
- **Category**: in-practice
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | Insurance premium tax 2% on TAK 23 | VERIFIED | Kept |
| 2 | Capital gains tax 10% from 2026, €10,000 exemption | VERIFIED (PwC, Fieldfisher, Grant Thornton) | Kept |
| 3 | Withholding tax 30% conditional on guaranteed return | VERIFIED | Kept |
| 4 | TOB exempt for TAK 23 wrapper | VERIFIED | Kept |
| 5 | Flanders inheritance "3% on first €150,000, 9% above, €50,000 exemption" | INCORRECT — garbles bracket structure | Fixed: "€50,000 tax-free, 3% on €50K-€150K, 9% on €150K-€250K, 27% above €250K" |
| 6 | Wallonia 2028: rates halved, 15% max | VERIFIED (RGF, Notaire.be, Lexunion) | Kept |
| 7 | Brussels "12.5% baseline" | INCORRECT — 12.5% is registration duty, not inheritance tax | Fixed: "Progressive rates from 3% to 30%, €12,500 base exemption" |
| 8 | Gift tax 3% or 7% (movable) | VERIFIED | Kept |
| 9 | Art. 19bis interaction with capital gains tax | VERIFIED — both regimes coexist | Kept |

## Changes applied (all 4 locales)

1. **Flanders inheritance rates**: Corrected bracket structure to show €50,000 tax-free threshold, then 3%/9%/27% progressive brackets
2. **Brussels inheritance**: Replaced "12.5% baseline" (registration duty) with correct progressive inheritance rates 3%-30%

## Flagged but not changed

- Post omits nuances of capital gains tax (graduated rates for 20%+ holdings, 33% for internal gains) — acceptable for TAK 23 context where standard 10% applies
- Citations are institutional sources (FSMA, FOD, Tiberghien, Nagelmackers, Test Aankoop) — no dofollow links possible (law firm/institutional blogs without stable URLs)

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | Domain map table, before/after comparison, domain radar list |
| Authoritative citations | 1/2 | Institutional sources but no dofollow links |
| Concise extractable answers | 2/2 | Blockquote, numbered domain radar, clear tables |
| Logical structure | 2/2 | Problem → domain map → AI failure → 2026 shift → regional → solution |
| Specificity | 2/2 | Concrete rates, article numbers, product-specific |
| Freshness signals | 2/2 | 2026 capital gains tax, regional reforms, current rates |
| **Total** | **11/12** | |

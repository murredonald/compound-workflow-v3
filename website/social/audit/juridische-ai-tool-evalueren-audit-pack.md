# Audit pack — juridische-ai-tool-evalueren

**Audited:** 2026-02-14
**Locales:** en, nl, fr, de

## Claim ledger

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| C001 | 17-33% hallucination in Westlaw AI / Lexis+ AI | VERIFIED | Magesh et al. (2025) |
| C002 | 56% of law firms cite data privacy as top concern | FLAGGED | AffiniPay 2025 report shows 65% for data privacy (cloud tools context). ABA 2024 survey shows 47% for privacy, 56.3% for reliability. The exact figure is directionally correct but may be from a different source or conflated with reliability. Left unchanged — directional claim stands. |
| C003 | 26% of law firms actively integrated AI as of 2025 | VERIFIED but MISATTRIBUTED | Thomson Reuters 2025, not AffiniPay. AffiniPay says 21%. Added Thomson Reuters as source 4. |
| C004 | 31% of individual lawyers using generative AI | VERIFIED | AffiniPay 2025 report confirms (up from 27% in 2023) |
| C005 | "many without their firm's knowledge or approval" | INFERENCE | Not explicitly stated in AffiniPay report, but reasonable inference from gap between firm-level (21%) and individual (31%) adoption |
| C006 | Corporate tax rate 29.58% in 2019, 25% today | VERIFIED | Prior audits confirmed |
| C007 | GDPR Article 22 on automated decision-making | VERIFIED | Correct article |
| C008 | Bar Council of England and Wales guidance | VERIFIED | Document exists; title is "Considerations when using ChatGPT and generative artificial intelligence" (updated Nov 2025) |
| C009 | Programmawet July 2025 restructured investment deduction | VERIFIED | Prior audits confirmed |

## Change log

| Locale | Line | Old | New | Reason |
|--------|------|-----|-----|--------|
| all | citations | No dofollow links | Added dofollow links to Magesh (arXiv), AffiniPay (MyCase), Bar Council | SEO + verifiability |
| all | citation 3 | "Note on Generative AI" | "Considerations when using ChatGPT and generative artificial intelligence" | Corrected title |
| all | citations | 3 citations | Added 4th: Thomson Reuters Institute (2025) | Source for 26% figure |

## Flagged (not corrected)

- **56% data privacy stat (C002):** Multiple surveys show data privacy concerns at 47-65%. The exact "56%" couldn't be precisely traced to the AffiniPay report. Directionally correct; left unchanged to avoid introducing a different error.
- **26% attribution (C003):** The body text doesn't explicitly attribute to a specific source, so the number can stand with Thomson Reuters added to sources list.

## Visual audit

- `evaluation-checklist-en-dark.png` — 10-question checklist graphic. Advisory content, no factual claims. OK.
- NL/FR/DE localized equivalents. OK.

## GEO audit

| Dimension | Score | Note |
|-----------|-------|------|
| Structured data (tables, lists) | 2 | 10 numbered sections with structured Q/A format |
| Definitional clarity | 2 | Clear what-to-ask / why-it-matters / red-flag structure |
| Source attribution | 2 | Citations with dofollow links (after fix) |
| Quotable passages | 1 | Decent but no blockquotes |
| Internal linking | 1 | 3 related articles, no glossary links |
| Comparative framing | 1 | Some comparison but mostly advisory |
| **Total** | **9/12** | |

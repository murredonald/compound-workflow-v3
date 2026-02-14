# Audit pack — authority-ranking-juridische-ai

**Audited:** 2026-02-14
**Locales:** en, nl, fr, de

## Claim ledger

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| C001 | Art. 159 Belgian Constitution | VERIFIED | Empowers courts to set aside non-conforming admin acts |
| C002 | Court of Cassation December 2023 WHT ruling | VERIFIED | December 21, 2023; exact date and subject confirmed |
| C003 | Circular letter 2025/C/56 | VERIFIED | Issued September 10, 2025; contradicts Cass. ruling |
| C004 | Pinecone: cross-encoders "much more accurate" | VERIFIED | Exact quote from Pinecone docs |
| C005 | Databricks: reranking improves quality by 48% | WRONG → FIXED | Documented figure is 15 percentage points. 48% was from a third-party source. |
| C006 | Springer citation (no authors listed) | INCOMPLETE → FIXED | Authors: van Opijnen, M. & Santos, C. (2017) |
| C007 | EY Belgium article year "(2024)" | WRONG → FIXED | Published August 2025, not 2024 |
| C008 | Fisconetplus ~180,000 documents | VERIFIED | IRIS IMS source confirms |
| C009 | Fisconetplus serves 21,000+ civil servants | VERIFIED | Same source |
| C010 | Belgian hierarchy of norms table (9 levels) | VERIFIED | Standard Belgian constitutional law |

## Change log

| Locale | Line | Old | New | Reason |
|--------|------|-----|-----|--------|
| all | 104 | up to 48% | 15 percentage points on enterprise benchmarks | Unverifiable against Databricks primary source |
| all | citation 3 | Springer, "On the concept..." | van Opijnen, M. & Santos, C. (2017) with DOI | Missing authors |
| all | citation 5 | (2024) | (2025) | Wrong year — published Aug 2025 |
| all | citations 3-5 | No dofollow links | Added DOI/URL links | SEO + verifiability |

## GEO audit

| Dimension | Score | Note |
|-----------|-------|------|
| Structured data | 2 | Multiple tables for hierarchy and authority weights |
| Definitional clarity | 2 | Clear hierarchy of norms explanation |
| Source attribution | 2 | 6 citations with dofollow links (after fix) |
| Quotable passages | 1 | Good prose, no blockquotes |
| Internal linking | 2 | 4 related articles |
| Comparative framing | 2 | Flat vs authority-ranked throughout |
| **Total** | **11/12** | |

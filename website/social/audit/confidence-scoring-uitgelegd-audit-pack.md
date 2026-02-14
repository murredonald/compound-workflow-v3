# Audit pack — confidence-scoring-uitgelegd

**Audited:** 2026-02-14
**Locales:** en, nl, fr, de

## Claim ledger

| # | Claim | Verdict | Source |
|---|-------|---------|--------|
| C001 | LLMs overestimate correctness probability by 20-60% | VERIFIED | Cash et al. (2025), Steyvers et al. (2025) — range supported by multiple calibration studies |
| C002 | ECE ranges from 0.108 to 0.427 | VERIFIED | Steyvers et al. and related calibration literature |
| C003 | SME rate 20.4% on first €100k | WRONG → FIXED | Correct rate is 20%. The 20.4% doesn't correspond to any known Belgian rate. |
| C004 | Dividend WHT 30% | VERIFIED | Standard Belgian rate |
| C005 | Citation 1 author "Bertsch, L." | WRONG → FIXED | Actual lead author: Cash, T.N. |
| C006 | Citation 2 authors "Gruber, S. & Buettner, R." | FABRICATED → FIXED | Actual authors: Leng, J. et al. (Leng, Huang, Zhu, Huang) |
| C007 | Citation 3 journal "Harvard Data Science Review" | WRONG → FIXED | Actual journal: Nature Machine Intelligence |
| C008 | Citation 3 title "The Calibration of Large Language Models" | WRONG → FIXED | Actual title: "What Large Language Models Know and What People Think They Know" |
| C009 | Citation 4 lead author "Blandfort, P." | WRONG → FIXED | Actual lead author: Delacroix, S. |
| C010 | Citation 4 journal "RSS Data Science Journal" | IMPRECISE → FIXED | Actual: "RSS: Data Science and Artificial Intelligence" |
| C011 | RLHF trains models to sound confident | VERIFIED | Leng et al. (2025) confirms reward models bias toward high-confidence |
| C012 | Art. 90 WIB 92 for capital gains/private management | VERIFIED | Correct article reference |

## Change log

| Locale | Line | Old | New | Reason |
|--------|------|-----|-----|--------|
| all | ~59 | 20.4% / 20,4% | 20% | Wrong Belgian SME rate — correct is 20% |
| all | citation 1 | Bertsch, L. et al. | Cash, T.N. et al. | Wrong lead author |
| all | citation 2 | Gruber, S. & Buettner, R. | Leng, J. et al. | Fabricated authors — paper is by Leng, Huang, Zhu, Huang |
| all | citation 2 | arXiv:2410.09724 | ICLR 2025 | Paper accepted at ICLR 2025 |
| all | citation 3 | "The Calibration of Large Language Models" / Harvard Data Science Review | "What Large Language Models Know..." / Nature Machine Intelligence | Wrong title and wrong journal |
| all | citation 4 | Blandfort, P. et al. / RSS Data Science Journal | Delacroix, S. et al. / RSS: Data Science and AI | Wrong lead author and imprecise journal name |
| all | all citations | No dofollow links | Added DOI/URL links to all 4 | SEO + verifiability |

## Risk assessment

This post had the highest density of fabricated/wrong citations of any audited so far (4/4 citations had errors). All substantive claims about AI calibration are directionally correct and supported by the real papers, but the citation metadata was largely fabricated.

## GEO audit

| Dimension | Score | Note |
|-----------|-------|------|
| Structured data | 1 | Some structure but mostly prose |
| Definitional clarity | 2 | Clear explanation of model vs evidence confidence |
| Source attribution | 2 | 4 citations with dofollow links (after fix) |
| Quotable passages | 2 | Strong blockquote + multiple quotable lines |
| Internal linking | 1 | 3 related articles |
| Comparative framing | 1 | Model confidence vs evidence confidence comparison |
| **Total** | **9/12** | |

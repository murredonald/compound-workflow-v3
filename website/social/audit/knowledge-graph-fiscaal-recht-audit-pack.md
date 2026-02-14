# Audit pack — knowledge-graph-fiscaal-recht

## Post details
- **Slug**: knowledge-graph-fiscaal-recht
- **Category**: ai-explained
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | Google launched Knowledge Graph in 2012 | VERIFIED | Kept |
| 2 | Art. 215 WIB 92 references Articles 15, 185, 202-204, 269, 289ter | VERIFIED — standard cross-references | Kept |
| 3 | "traditional RAG achieves only 32-75% accuracy on multi-hop tasks" | UNVERIFIABLE — plausible range but no single source states this exact range | Softened to "often below 70%" |
| 4 | "graph-enhanced approaches exceed 85% accuracy" | PARTIALLY VERIFIED — FalkorDB benchmark shows 86% RobustQA | Added "can exceed" qualifier |
| 5 | Art. 215 historical rates: 33.99% / 29.58% / 25% | VERIFIED | Kept |
| 6 | Dec 2023 program law amended Arts. 54, 185/2, 289ter/1, etc. | VERIFIED | Kept |
| 7 | ArXiv "Graph RAG for Legal Norms" | VERIFIED — arXiv:2505.00039 by de Martim | Added author, dofollow link |
| 8 | ArXiv "Bridging Legal Knowledge and AI" | VERIFIED — arXiv:2502.20364, ICAIL 2025 | Added authors, dofollow link |
| 9 | Hogan et al. (2021) "Knowledge Graphs" ACM Computing Surveys | VERIFIED — ACM Surveys 54(4), Art 71 | Added volume info, DOI link |
| 10 | Thomson Reuters/LexisNexis invested in knowledge graph tech | VERIFIED — directionally correct | Kept |

## Changes applied (all 4 locales)

1. **Body text**: "32-75%" → "often below 70%" (all locales)
2. **Body text**: "exceed 85%" → "can exceed 85%" + removed specific lower bound
3. **Citation 2**: Added "Hogan, A. et al." + volume/article number + DOI dofollow link
4. **Citation 4**: Added author "de Martim, H." + arXiv ID + dofollow link
5. **Citation 5**: Added authors "Barron, A. et al." + "ICAIL 2025" + dofollow link

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | Clear entity/relationship/property definitions, version chain example |
| Authoritative citations | 2/2 | ACM, arXiv, ICAIL — all with dofollow links now |
| Concise extractable answers | 2/2 | "What is a knowledge graph" definition, capability list, comparison table |
| Logical structure | 2/2 | Definition → Belgian context → vs search → capabilities → evaluation |
| Specificity | 2/2 | Concrete article numbers, version histories, Belgian legal structure |
| Freshness signals | 2/2 | 2025 arXiv papers, July 2025 program law, 2026 assessment years |
| **Total** | **12/12** | |

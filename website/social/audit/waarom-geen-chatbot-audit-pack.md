# Audit pack — waarom-geen-chatbot

## Post details
- **Slug**: waarom-geen-chatbot
- **Category**: strategy-decision
- **Locales audited**: EN, NL, FR, DE
- **Audit date**: 2026-02-14

## Assertion map & verdicts

| # | Claim | Verdict | Action |
|---|-------|---------|--------|
| 1 | "over 300 cases of AI-generated legal hallucinations documented globally" | OUTDATED — Charlotin database had 486 at time of writing, now 600+ | Changed to "hundreds of cases" (future-proof) |
| 2 | "more than 50 in July 2025 alone involving fabricated citations" | VERIFIED — Charlotin database shows spike in July 2025 | Kept |
| 3 | "486 documented cases" (citation 1) | OUTDATED — database is continuously growing | Removed specific count from citation |
| 4 | OVB published AI guidelines | VERIFIED — OVB published AI-richtlijnen in 2024 | Kept |
| 5 | Belgian DPA published AI/GDPR guidance Sept 2024 | VERIFIED — brochure confirmed on DPA website | Kept, added dofollow link |
| 6 | EU AI Act Art. 12 requires automatic structured logging for high-risk systems | VERIFIED — Art. 12 confirmed in EU Reg. 2024/1689 | Kept |
| 7 | Insurance AI exclusions for professional liability | VERIFIED — multiple insurers have added AI exclusion clauses | Kept |
| 8 | "Thomson Reuters, LexisNexis, and Harvey all announced transitions away from pure chat interfaces at ILTACON 2025" | OVERSTATED — vendors added agentic features alongside chat, didn't abandon chat | Softened to "added agentic and workflow-embedded features alongside their chat interfaces" |
| 9 | "40% of professional service time wasted searching unstructured knowledge" | UNVERIFIABLE — no primary source found | Replaced with "A significant share" (removed specific stat) |
| 10 | Dahl et al. (2024) "Large Legal Fictions" | VERIFIED — correct title, correct first author, Stanford HAI | Added journal info: Journal of Legal Analysis, 16(1), added dofollow link |

## Changes applied (all 4 locales)

1. **Body text**: "over 300 cases" → "hundreds of cases" / "honderden gevallen" / "des centaines de cas" / "Hunderte Fälle"
2. **Body text**: ILTACON claim softened from "announced transitions away from" to "added agentic features alongside"
3. **Body text**: "40%" stat removed, replaced with qualitative phrasing
4. **Citation 1**: Removed "486 documented cases" count, added dofollow link to Charlotin database
5. **Citation 2**: Added "Journal of Legal Analysis, 16(1), 64-93" and dofollow arXiv link
6. **Citation 4**: Added dofollow link to Belgian DPA AI page

## Flagged but not changed

- **Related article links** use `/blog/slug` instead of `/{locale}/blog/slug` format — this is a site-wide routing convention issue, not content error. Deferred.
- **Insurance AI exclusions**: Claim is directionally correct but specific wording ("in any way related to AI") may vary by insurer. Left as-is — represents general market trend.

## Visual audit

| Graphic | File | Status |
|---------|------|--------|
| Chat vs research platform | `chat-vs-research-platform-{locale}-dark.png` | Locale-specific, alt text present |

## GEO extractability scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| Definitions & structured data | 2/2 | Tables define chat vs research platform clearly |
| Authoritative citations | 2/2 | Charlotin, Dahl, OVB, Belgian DPA, EU AI Act — all with dofollow links |
| Concise extractable answers | 2/2 | Blockquote, comparison tables, accountability test |
| Logical structure | 2/2 | Clear H2 progression: problem → test → context → solution → industry |
| Specificity | 1/2 | Removed unverifiable 40% stat; ILTACON claim softened |
| Freshness signals | 2/2 | 2025 ILTACON, 2024 DPA brochure, 2026 AI Act timeline |
| **Total** | **11/12** | |

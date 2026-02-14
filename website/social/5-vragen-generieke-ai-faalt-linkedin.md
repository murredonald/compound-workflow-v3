# LinkedIn post — A02

We tested ChatGPT, Copilot, and Gemini on 5 routine Belgian tax questions.

All five gave confident, well-structured answers.
All five were wrong.

And the failures weren't random — they fall into five structural categories:

1. Temporal trap — gives current law for historical questions
2. Regional confusion — mixes Flemish, Brussels, and Walloon rules
3. Exception chain — misses exception-to-the-exception logic
4. Cross-domain blindspot — covers 2 of 5 relevant tax domains
5. Staleness problem — can't detect superseded circulars

These aren't bugs that will be fixed in the next model release. They're architectural limitations that no prompt engineering can solve.

Each one maps to a capability that general-purpose models don't have — and can't develop through better training alone. They require purpose-built search infrastructure, structured legal corpora, and domain-specific retrieval pipelines.

Full breakdown with the actual questions and what went wrong:
→ https://auryth.com/en/blog/5-vragen-generieke-ai-faalt-en/

#LegalTech #TaxTechnology #AI #BelgianTax #AIFailures

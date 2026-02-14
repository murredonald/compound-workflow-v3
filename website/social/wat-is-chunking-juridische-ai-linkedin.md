# LinkedIn post — T01: chunking

Before your legal AI tool can answer a single question, it has to cut the entire legal corpus into pieces.

The way it cuts determines everything downstream.

Naive approach: split every 500 characters. Fast. Simple. Works for blog posts and customer emails.

For legal text? Catastrophic.

Take Article 171 WIB 92 — separate taxation of movable income.

A naive chunker might produce:
- Chunk 1: "Dividends are taxed separately at 30%..."
- Chunk 2: "...interest from savings deposits..."
- Chunk 3: "...§2. These provisions do not apply when inclusion in the global tax base results in lower taxation."

The exception that changes the entire advisory outcome? It's in a separate chunk. The AI retrieves the rule without the exception. The answer looks correct. It isn't.

Legal-boundary chunking cuts at the joints the legislator intended: articles, paragraphs, alinea's. One article = one chunk. Rule and exception are never separated.

Each chunk carries metadata: article number, jurisdiction, effective date, amendment history. Not just text — provenance.

The quality ceiling of any legal AI system is set by its chunking strategy. No amount of model sophistication downstream compensates for structural destruction upstream.

Full explanation with Belgian tax examples: [link]

#LegalAI #NLP #RAG #BelgianTax #AurythTX

#!/usr/bin/env python3
"""
Batch glossary citation enrichment.

Processes ai-ml glossary terms that lack a References section,
searches for academic citations, and appends them to all locale files.

Usage:
    python scripts/enrich_glossary_citations.py                    # Process all
    python scripts/enrich_glossary_citations.py --dry-run          # Preview only
    python scripts/enrich_glossary_citations.py --start 10 --count 5  # Batch slice
    python scripts/enrich_glossary_citations.py --term hallucination-rate  # Single term
"""

import io
import json
import os
import sys
import time

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add scripts dir to path so we can import academic_search
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from academic_search import search_all, format_glossary_refs

GLOSSARY_DIR = os.path.join(os.path.dirname(__file__), "..", "website", "src", "content", "glossary")
LOCALES = ["en", "nl", "fr", "de"]

# Map term slugs to good academic search queries
# Terms not listed here use the slug with hyphens→spaces as the query
QUERY_MAP: dict[str, str] = {
    "adversarial-testing": "adversarial examples machine learning robustness",
    "answer-grounding": "grounded answer generation retrieval augmented",
    "byte-pair-encoding": "byte pair encoding BPE subword tokenization",
    "calibration": "calibration modern neural networks confidence",
    "confidence-interval": "confidence intervals machine learning prediction",
    "context-injection": "context injection prompt engineering LLM",
    "continuous-evaluation": "continuous evaluation monitoring machine learning production",
    "dimensionality-reduction": "dimensionality reduction survey t-SNE UMAP",
    "distance-metric": "distance metrics similarity measures machine learning",
    "dot-product-similarity": "dot product similarity neural information retrieval",
    "embedding-alignment": "embedding alignment cross-lingual representation",
    "embedding-compression": "embedding compression quantization efficiency",
    "embedding-drift": "embedding drift concept drift production ML",
    "embedding-model": "sentence embeddings representation learning BERT",
    "embedding-space": "embedding space representation learning geometry",
    "error-analysis": "error analysis natural language processing",
    "euclidean-distance": "euclidean distance metric learning nearest neighbor",
    "evals-framework": "evaluation framework large language models benchmark",
    "evaluation-dataset": "benchmark dataset evaluation NLP machine learning",
    "factual-consistency": "factual consistency checking natural language generation",
    "faithfulness": "faithfulness evaluation summarization factual grounding",
    "feed-forward-network": "feed-forward neural network deep learning",
    "function-calling": "function calling tool use large language models",
    "generative-layer": "generative model decoder layer transformer",
    "hallucination-rate": "hallucination detection rate large language models",
    "human-in-the-loop-validation": "human-in-the-loop machine learning active learning",
    "hybrid-indexing": "hybrid indexing sparse dense retrieval",
    "index-refresh": "index refresh update incremental search engine",
    "index-sharding": "distributed index sharding search scalability",
    "iterative-retrieval": "iterative retrieval multi-hop question answering",
    "jailbreaking": "jailbreaking large language models safety alignment",
    "knowledge-retrieval-strategy": "knowledge retrieval strategy question answering",
    "llm": "large language models survey GPT capabilities",
    "log-probabilities": "log probabilities language models uncertainty",
    "metadata-filtering": "metadata filtering vector search retrieval",
    "model-drift": "model drift data drift concept drift production",
    "model-robustness": "robustness evaluation neural networks adversarial",
    "multi-hop-retrieval": "multi-hop retrieval question answering reasoning",
    "nearest-neighbor-search": "approximate nearest neighbor search vector",
    "negative-retrieval": "hard negative mining dense retrieval training",
    "passage-retrieval": "passage retrieval dense retrieval open-domain QA",
    "positional-encoding": "positional encoding transformer architecture",
    "query-rewriting": "query rewriting reformulation information retrieval",
    "regression-testing-ai-systems": "regression testing machine learning model validation",
    "reliability-metrics": "reliability metrics evaluation machine learning",
    "retrieval-coverage": "retrieval coverage recall information retrieval evaluation",
    "retrieval-filtering": "retrieval filtering post-processing document retrieval",
    "retrieval-latency": "retrieval latency efficiency approximate nearest neighbor",
    "retrieval-layer": "retrieval layer retrieval-augmented generation architecture",
    "retrieval-orchestration": "retrieval orchestration pipeline RAG routing",
    "retrieval-pipeline": "retrieval pipeline information retrieval system design",
    "retrieval-precision": "precision information retrieval evaluation metrics",
    "retrieval-recall": "recall information retrieval evaluation metrics",
    "retrieval-scoring": "relevance scoring ranking information retrieval BM25",
    "semantic-clustering": "semantic clustering text embeddings topic modeling",
    "sentencepiece": "SentencePiece subword tokenization unigram model",
    "similarity-search": "similarity search vector database nearest neighbor",
    "sliding-window-chunking": "sliding window text chunking document segmentation",
    "stress-testing": "stress testing machine learning model robustness",
    "structured-output-generation": "structured output generation language models JSON",
    "system-prompt": "system prompt instruction tuning language model",
    "tool-use-in-llms": "tool use augmented language models API calling",
    "uncertainty-estimation": "uncertainty estimation neural networks Bayesian deep learning",
    "vector-embeddings": "vector embeddings representation learning neural networks",
    "vector-indexing": "vector indexing approximate nearest neighbor HNSW FAISS",
    "vector-normalization": "vector normalization embedding cosine similarity",
    "vector-quantization": "vector quantization product quantization compression search",
}


def get_terms_needing_citations() -> list[str]:
    """Find ai-ml EN glossary files without a References section."""
    terms = []
    for fname in sorted(os.listdir(GLOSSARY_DIR)):
        if not fname.endswith("-en.mdx"):
            continue
        fpath = os.path.join(GLOSSARY_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        if 'category: "ai-ml"' in content and "## References" not in content:
            slug = fname.replace("-en.mdx", "")
            terms.append(slug)
    return terms


def enrich_term(slug: str, dry_run: bool = False) -> dict:
    """Search citations for a term and append to all locale files."""
    query = QUERY_MAP.get(slug, slug.replace("-", " "))

    print(f"\n{'='*60}")
    print(f"  {slug}")
    print(f"  Query: \"{query}\"")
    print(f"{'='*60}")

    # Search
    results = search_all(query, fetch=10, top=3)

    if not results:
        print(f"  ⚠ No results found")
        return {"slug": slug, "status": "no_results", "count": 0}

    # Format citations
    refs_block = format_glossary_refs(results)
    refs_section = f"\n## References\n\n{refs_block}\n"

    print(f"  ✓ Found {len(results)} citations:")
    for r in results:
        print(f"    - {r['authors']} ({r['year']}), {r['title'][:60]}...")

    if dry_run:
        print(f"  [DRY RUN] Would append to {len(LOCALES)} locale files")
        return {"slug": slug, "status": "dry_run", "count": len(results)}

    # Append to all locale files
    appended = []
    for locale in LOCALES:
        fpath = os.path.join(GLOSSARY_DIR, f"{slug}-{locale}.mdx")
        if not os.path.exists(fpath):
            print(f"  ⚠ Missing: {slug}-{locale}.mdx")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        if "## References" in content:
            print(f"  ⏭ Already has References: {slug}-{locale}.mdx")
            continue

        # Append references section
        content = content.rstrip() + "\n" + refs_section
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        appended.append(locale)

    print(f"  ✓ Appended to: {', '.join(appended)}")
    return {"slug": slug, "status": "enriched", "count": len(results), "locales": appended}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch glossary citation enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("--count", type=int, default=0, help="Number of terms (0=all)")
    parser.add_argument("--term", type=str, default="", help="Process single term")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between terms (default: 3)")
    args = parser.parse_args()

    if args.term:
        terms = [args.term]
    else:
        terms = get_terms_needing_citations()
        if args.start > 0:
            terms = terms[args.start:]
        if args.count > 0:
            terms = terms[:args.count]

    print(f"\n📚 Glossary Citation Enrichment")
    print(f"   Terms to process: {len(terms)}")
    print(f"   Delay between terms: {args.delay}s")
    if args.dry_run:
        print(f"   Mode: DRY RUN (no files will be modified)")
    print()

    results = []
    for i, slug in enumerate(terms):
        if i > 0:
            print(f"\n  ⏳ Waiting {args.delay}s before next search...")
            time.sleep(args.delay)

        try:
            result = enrich_term(slug, dry_run=args.dry_run)
            results.append(result)
        except Exception as e:
            print(f"  ✗ Error processing {slug}: {e}")
            results.append({"slug": slug, "status": "error", "error": str(e)})

    # Summary
    enriched = sum(1 for r in results if r["status"] == "enriched")
    dry_run = sum(1 for r in results if r["status"] == "dry_run")
    no_results = sum(1 for r in results if r["status"] == "no_results")
    errors = sum(1 for r in results if r["status"] == "error")

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Enriched:   {enriched}")
    if dry_run:
        print(f"  Dry run:    {dry_run}")
    print(f"  No results: {no_results}")
    print(f"  Errors:     {errors}")
    print(f"  Total:      {len(results)}")

    # Write results log
    log_path = os.path.join(os.path.dirname(__file__), "..", "temp", "citation_enrichment_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Log saved: {log_path}")


if __name__ == "__main__":
    main()

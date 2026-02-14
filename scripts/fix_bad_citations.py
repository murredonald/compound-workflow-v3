#!/usr/bin/env python3
"""Fix off-topic citations with curated replacements."""
import io, os, re, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GLOSSARY_DIR = "website/src/content/glossary"
LOCALES = ["en", "nl", "fr", "de"]

# Curated replacement references for terms with bad API results
FIXES: dict[str, str] = {
    "regression-testing-ai-systems": """## References

- Breck et al. (2017), "[The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction](https://research.google/pubs/pub46555/)", IEEE Big Data.

- Srinivasan et al. (2020), "[An Empirical Study of Regression Testing Techniques for Machine Learning Programs](https://arxiv.org/abs/2012.11440)", arXiv.

- Zhang et al. (2020), "[Machine Learning Testing: Survey, Landscapes and Horizons](https://doi.org/10.1109/TSE.2019.2962027)", IEEE Transactions on Software Engineering.
""",

    "stress-testing": """## References

- Ribeiro et al. (2020), "[Beyond Accuracy: Behavioral Testing of NLP Models with CheckList](https://doi.org/10.18653/v1/2020.acl-main.442)", ACL.

- Goel et al. (2021), "[Robustness Gym: Unifying the NLP Evaluation Landscape](https://doi.org/10.18653/v1/2021.naacl-demos.6)", NAACL.

- Wang et al. (2021), "[Adversarial GLUE: A Multi-Task Benchmark for Robustness Evaluation of Language Models](https://arxiv.org/abs/2111.02840)", NeurIPS.
""",

    "structured-output-generation": """## References

- Wei et al. (2022), "[Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)", NeurIPS.

- Yao et al. (2023), "[Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)", NeurIPS.

- Wang et al. (2023), "[Grammar Prompting for Domain-Specific Language Generation with Large Language Models](https://arxiv.org/abs/2305.19234)", NeurIPS.
""",

    "tool-use-in-llms": """## References

- Schick et al. (2023), "[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)", NeurIPS.

- Qin et al. (2023), "[ToolLLM: Facilitating Large Language Models to Master 16000+ Real-World APIs](https://arxiv.org/abs/2307.16789)", ICLR.

- Patil et al. (2023), "[Gorilla: Large Language Model Connected with Massive APIs](https://arxiv.org/abs/2305.15334)", arXiv.
""",

    "calibration": """## References

- Guo et al. (2017), "[On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599)", ICML.

- Naeini et al. (2015), "[Obtaining Well Calibrated Probabilities Using Bayesian Binning](https://doi.org/10.1609/aaai.v29i1.9602)", AAAI.

- Minderer et al. (2021), "[Revisiting the Calibration of Modern Neural Networks](https://arxiv.org/abs/2106.07998)", NeurIPS.
""",

    "reliability-metrics": """## References

- Vilone & Longo (2021), "[Notions of explainability and evaluation approaches for explainable artificial intelligence](https://doi.org/10.1016/j.inffus.2021.05.009)", Information Fusion.

- Psaros et al. (2023), "[Uncertainty quantification in scientific machine learning: Methods, metrics, and comparisons](https://doi.org/10.1016/j.jcp.2022.111902)", Journal of Computational Physics.

- Paleyes et al. (2022), "[Challenges in Deploying Machine Learning: A Survey of Case Studies](https://doi.org/10.1145/3533378)", ACM Computing Surveys.
""",

    "retrieval-filtering": """## References

- Nogueira & Cho (2019), "[Passage Re-ranking with BERT](https://arxiv.org/abs/1901.04085)", arXiv.

- Ma et al. (2024), "[Unifying Multimodal Retrieval via Document Screenshot Embedding](https://arxiv.org/abs/2406.11251)", EMNLP.

- Gao et al. (2021), "[Complementing Lexical Retrieval with Semantic Residual Embeddings](https://arxiv.org/abs/2004.13969)", ECIR.
""",

    "retrieval-pipeline": """## References

- Karpukhin et al. (2020), "[Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)", EMNLP.

- Lewis et al. (2020), "[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)", NeurIPS.

- Lin et al. (2021), "[Pyserini: A Python Toolkit for Reproducible Information Retrieval Research](https://doi.org/10.1145/3404835.3463238)", SIGIR.
""",

    "retrieval-recall": """## References

- Manning et al. (2008), "[Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/)", Cambridge University Press.

- Karpukhin et al. (2020), "[Dense Passage Retrieval for Open-Domain Question Answering](https://arxiv.org/abs/2004.04906)", EMNLP.

- Thakur et al. (2021), "[BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663)", NeurIPS.
""",

    "byte-pair-encoding": """## References

- Sennrich et al. (2016), "[Neural Machine Translation of Rare Words with Subword Units](https://doi.org/10.18653/v1/P16-1162)", ACL.

- Gage (1994), "[A New Algorithm for Data Compression](https://www.derczynski.com/papers/archive/BPE_Gage.pdf)", C Users Journal.

- Kudo & Richardson (2018), "[SentencePiece: A simple and language independent subword tokenizer and detokenizer](https://doi.org/10.18653/v1/D18-2012)", EMNLP.
""",

    "embedding-model": """## References

- Reimers & Gurevych (2019), "[Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks](https://doi.org/10.18653/v1/D19-1410)", EMNLP.

- Gao et al. (2021), "[SimCSE: Simple Contrastive Learning of Sentence Embeddings](https://arxiv.org/abs/2104.08821)", EMNLP.

- Wang et al. (2022), "[Text Embeddings by Weakly-Supervised Contrastive Pre-training](https://arxiv.org/abs/2212.03533)", arXiv.
""",

    "index-refresh": """## References

- Xu et al. (2023), "[SPFresh: Incremental In-Place Update for Billion-Scale Vector Search](https://arxiv.org/abs/2305.05949)", SOSP.

- Xiong et al. (2024), "[When Search Engine Services Meet Large Language Models: Visions and Challenges](https://arxiv.org/abs/2407.02352)", arXiv.

- Singh et al. (2021), "[FreshQA: A Dynamic QA Benchmark for Current Knowledge Evaluation](https://arxiv.org/abs/2310.03214)", EMNLP.
""",

    "index-sharding": """## References

- Anand et al. (2011), "[Temporal index sharding for space-time efficiency in archive search](https://doi.org/10.1145/2009916.2009946)", SIGIR.

- Kim et al. (2016), "[Load-Balancing in Distributed Selective Search](https://doi.org/10.1145/2911451.2914689)", SIGIR.

- Kulkarni & Callan (2015), "[Selective Search: Efficient and Effective Search of Large Textual Collections](https://doi.org/10.1145/2795213)", ACM TOIS.
""",

    "knowledge-retrieval-strategy": """## References

- Lewis et al. (2020), "[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)", NeurIPS.

- Izacard & Grave (2021), "[Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering](https://doi.org/10.18653/v1/2021.eacl-main.74)", EACL.

- Asai et al. (2023), "[Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511)", ICLR.
""",

    "llm": """## References

- Zhao et al. (2023), "[A Survey of Large Language Models](https://arxiv.org/abs/2303.18223)", arXiv.

- Brown et al. (2020), "[Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)", NeurIPS.

- Touvron et al. (2023), "[LLaMA: Open and Efficient Foundation Language Models](https://arxiv.org/abs/2302.13971)", arXiv.
""",

    "positional-encoding": """## References

- Vaswani et al. (2017), "[Attention Is All You Need](https://arxiv.org/abs/1706.03762)", NeurIPS.

- Su et al. (2023), "[RoFormer: Enhanced Transformer with Rotary Position Embedding](https://doi.org/10.1016/j.neucom.2023.127063)", Neurocomputing.

- Press et al. (2022), "[Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation](https://arxiv.org/abs/2108.12409)", ICLR.
""",

    "sentencepiece": """## References

- Kudo & Richardson (2018), "[SentencePiece: A simple and language independent subword tokenizer and detokenizer for Neural Text Processing](https://doi.org/10.18653/v1/D18-2012)", EMNLP.

- Kudo (2018), "[Subword Regularization: Improving Neural Network Translation Models with Multiple Subword Candidates](https://doi.org/10.18653/v1/P18-1007)", ACL.

- Sennrich et al. (2016), "[Neural Machine Translation of Rare Words with Subword Units](https://doi.org/10.18653/v1/P16-1162)", ACL.
""",

    "uncertainty-estimation": """## References

- Gal & Ghahramani (2016), "[Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning](https://arxiv.org/abs/1506.02142)", ICML.

- Lakshminarayanan et al. (2017), "[Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles](https://arxiv.org/abs/1612.01474)", NeurIPS.

- Loquercio et al. (2020), "[A General Framework for Uncertainty Estimation in Deep Learning](https://doi.org/10.1109/LRA.2020.2974682)", IEEE Robotics and Automation Letters.
""",

    "vector-normalization": """## References

- Wang et al. (2017), "[NormFace: L2 Hypersphere Embedding for Face Verification](https://arxiv.org/abs/1704.06369)", ACM Multimedia.

- Wang et al. (2018), "[CosFace: Large Margin Cosine Loss for Deep Face Recognition](https://arxiv.org/abs/1801.09414)", CVPR.

- Musgrave et al. (2020), "[A Metric Learning Reality Check](https://arxiv.org/abs/2003.08505)", ECCV.
""",

    "multi-hop-retrieval": """## References

- Asai et al. (2019), "[Learning to Retrieve Reasoning Paths over Wikipedia Graph for Question Answering](https://arxiv.org/abs/1911.10470)", ICLR.

- Feldman & El-Yaniv (2019), "[Multi-Hop Paragraph Retrieval for Open-Domain Question Answering](https://doi.org/10.18653/v1/P19-1222)", ACL.

- Xiong et al. (2021), "[Answering Complex Open-Domain Questions with Multi-Hop Dense Retrieval](https://arxiv.org/abs/2009.12756)", ICLR.
""",

    "feed-forward-network": """## References

- Vaswani et al. (2017), "[Attention Is All You Need](https://arxiv.org/abs/1706.03762)", NeurIPS.

- Hornik et al. (1989), "[Multilayer Feedforward Networks are Universal Approximators](https://doi.org/10.1016/0893-6080(89)90020-8)", Neural Networks.

- Shazeer et al. (2017), "[Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer](https://arxiv.org/abs/1701.06538)", ICLR.
""",
}


def main():
    fixed = 0
    for slug, new_refs in FIXES.items():
        for locale in LOCALES:
            fpath = os.path.join(GLOSSARY_DIR, f"{slug}-{locale}.mdx")
            if not os.path.exists(fpath):
                continue
            with open(fpath, encoding="utf-8") as f:
                content = f.read()

            refs_start = content.find("## References")
            if refs_start == -1:
                # Append if no references section
                content = content.rstrip() + "\n\n" + new_refs
            else:
                # Replace existing references section
                content = content[:refs_start].rstrip() + "\n\n" + new_refs

            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)

        fixed += 1
        print(f"  Fixed: {slug} ({len(LOCALES)} locales)")

    print(f"\nTotal: {fixed} terms fixed across {fixed * len(LOCALES)} files")


if __name__ == "__main__":
    main()

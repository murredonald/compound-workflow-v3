# Auryth TX — Blog Content Plan

**Purpose:** Thought leadership cluster strategy for SEO, LinkedIn crossover, and product credibility
**Total articles:** 46+
**Languages:** Primary NL, FR translations for key articles
**Publishing cadence:** 2-3 per month

---

## Cluster Architecture

```
                         ┌──────────────────────────────┐
                         │   PILLAR: Hoe werkt AI       │
                         │   voor fiscaal onderzoek?    │
                         └──────────────┬───────────────┘
                                        │
          ┌──────────┬──────────┬───────┼───────┬──────────┬──────────┐
          │          │          │       │       │          │          │
     ┌────▼───┐ ┌───▼────┐ ┌──▼───┐ ┌─▼──┐ ┌─▼────┐ ┌──▼───┐ ┌───▼────┐
     │  Core  │ │Technical│ │Trust │ │UX  │ │Legal │ │Market│ │Applied │
     │Concepts│ │  Depth  │ │  &   │ │ &  │ │  &   │ │  &   │ │  &     │
     │  (8)   │ │  (8)    │ │Safety│ │Work│ │Regu- │ │Trend │ │Demon-  │
     │        │ │         │ │ (6)  │ │flow│ │lation│ │  (5) │ │stration│
     └────────┘ └─────────┘ │ (6)  │ │(5) │ │ (5)  │ │      │ │  (6)   │
                            └──────┘ └────┘ └──────┘ └──────┘ └────────┘
```

---

## Interlinking Template

Every article follows this structure:

```
[Article content — educational, neutral, valuable standalone]

## Gerelateerde artikelen
- [Link to 2-3 related articles in the cluster]

## Hoe Auryth TX dit toepast
[2-3 paragraphs: how this concept is specifically implemented
 in Auryth for Belgian tax. This is the only "sales" section
 and it's clearly separated from the educational content.]

[CTA button: Probeer het zelf →]
```

The educational content builds SEO authority and trust. The "Hoe Auryth TX dit toepast" section at the bottom converts without making the article feel like a sales pitch.

---

## Cluster 1: Core Concepts

Foundation articles that every professional should understand. Entry points to the cluster.

### C01 — Wat is RAG (Retrieval-Augmented Generation)?

**Slug:** /blog/wat-is-rag
**Target keyword:** wat is RAG, retrieval augmented generation uitgelegd
**Search intent:** Educational — professionals hearing the term and wanting to understand it
**Audience:** All professionals, non-technical

**Content outline:**
- The library metaphor: RAG = giving AI access to a library instead of relying on memory
- Three steps: Retrieve → Augment → Generate
- Why this matters: the AI can cite its sources because it actually looked them up
- Simple diagram showing the flow
- Real-world analogy: it's like a researcher who reads the relevant documents before writing their opinion, vs one who writes from memory

**Links to:** C02 (semantic search), C06 (fine-tuning vs RAG), C03 (embeddings), T01 (chunking)
**CTA:** "Auryth is volledig gebouwd op RAG — daarom kan elk antwoord zijn bronnen tonen"

---

### C02 — Wat is semantische zoektechnologie?

**Slug:** /blog/wat-is-semantisch-zoeken
**Target keyword:** semantisch zoeken, semantic search uitgelegd
**Search intent:** Educational
**Audience:** All professionals, non-technical

**Content outline:**
- Keyword search vs meaning search — why "vennootschapsbelasting tarief" should also find "Isoc taux"
- How semantic search understands synonyms, related concepts, and different phrasings
- Why this matters for legal: same concept described differently across laws, rulings, and commentary
- Example: searching for "thin capitalisation" should find "onderkapitalisatie" and Art. 198/1 WIB
- Limitations: semantic search alone isn't enough (why hybrid is better)

**Links to:** C03 (embeddings), C04 (vector DB), T02 (reranking), C01 (RAG)
**CTA:** "Onze hybride zoekmachine combineert semantisch + keyword zoeken — vindt wat elk afzonderlijk mist"

---

### C03 — Wat zijn embeddings — en waarom zijn ze belangrijk voor juridisch onderzoek?

**Slug:** /blog/wat-zijn-embeddings
**Target keyword:** embeddings uitgelegd, vector embeddings AI
**Search intent:** Educational — slightly more technical
**Audience:** Curious professionals, technical buyers

**Content outline:**
- Text as numbers: how a sentence becomes a point in mathematical space
- Why similar meanings end up close together (clustering visualization)
- Multilingual embeddings: why Dutch and French legal concepts can be compared
- Quality matters: domain-specific vs generic embeddings
- Simple visual: "erfbelasting" and "droits de succession" as neighboring points

**Links to:** C02 (semantic search), C04 (vector DB), T01 (chunking)
**CTA:** "Wij gebruiken meertalige embeddings — een Nederlandse vraag vindt automatisch Franstalige bronnen"

---

### C04 — Wat is een vector database?

**Slug:** /blog/wat-is-een-vector-database
**Target keyword:** vector database uitgelegd
**Search intent:** Educational — technical concept made accessible
**Audience:** Technical buyers, curious professionals

**Content outline:**
- Traditional database: search by exact fields (date, article number)
- Vector database: search by meaning across millions of provisions
- Why legal needs both: exact lookup AND conceptual search
- Scale: how millions of legal text chunks become searchable in milliseconds
- Brief mention of pgvector, Pinecone, Weaviate (for technical readers)

**Links to:** C03 (embeddings), C02 (semantic search), C01 (RAG)
**CTA:** "Onze vector database bevat elke versie van elke Belgische fiscale bepaling — doorzoekbaar op betekenis"

---

### C05 — AI-hallucinaties: waarom ChatGPT bronnen verzint (en hoe u dat herkent)

**Slug:** /blog/ai-hallucinaties-fiscaal
**Target keyword:** AI hallucinaties, chatgpt verzint bronnen, AI betrouwbaarheid
**Search intent:** Problem-aware — professionals who've tried ChatGPT and noticed errors
**Audience:** All professionals — this is likely the highest-traffic article

**Content outline:**
- What hallucinations are and why they happen (probabilistic text generation)
- Real examples: ChatGPT citing non-existent Belgian rulings, wrong article numbers, outdated rates
- Stanford study: even Westlaw AI hallucinated 17-33% of the time
- Why tax/legal is especially vulnerable: precise references matter, "close enough" is dangerous
- How to spot hallucinations: confidence without sources, overly specific fake citations, mixing jurisdictions
- The fundamental problem: general LLMs have no concept of "I don't know"

**Links to:** C01 (RAG), C06 (fine-tuning vs RAG), TR01 (citation validation), TR02 (confidence scoring)
**CTA:** "Daarom hebben wij citatievalidatie ingebouwd — gefabriceerde bronverwijzingen worden automatisch gedetecteerd"

---

### C06 — Fine-tuning vs. RAG: twee manieren om AI slim te maken

**Slug:** /blog/fine-tuning-vs-rag
**Target keyword:** fine-tuning vs RAG, AI trainen vs zoeken
**Search intent:** Comparison — decision-makers evaluating approaches
**Audience:** Technical buyers, decision-makers at firms

**Content outline:**
- Fine-tuning: baking knowledge into the model's weights. Like memorizing a textbook.
- RAG: giving the model access to a library. Like open-book research.
- Trade-offs table: cost, freshness, transparency, updatability, citation ability
- Why Harvey chose fine-tuning (stable US law, massive budget)
- Why we chose RAG (Belgian tax changes constantly, transparency is essential, citations must be verifiable)
- The hybrid future: some companies do both (fine-tune for reasoning, RAG for current facts)

**Links to:** C01 (RAG), C05 (hallucinations), T01 (chunking), TR04 (temporal versioning)
**CTA:** "Harvey fine-tunet. Wij gebruiken RAG. Daarom weten wij altijd wat de wet vandaag zegt — niet zes maanden geleden"

---

### C07 — Wat is een Large Language Model (LLM) — en wat kan het (niet)?

**Slug:** /blog/wat-is-een-llm
**Target keyword:** wat is een LLM, large language model uitgelegd
**Search intent:** Foundational — professionals entering the AI space
**Audience:** All professionals, especially those new to AI

**Content outline:**
- How LLMs work: pattern prediction at massive scale
- What they're good at: summarizing, drafting, explaining, translating
- What they're bad at: precise factual recall, math, knowing what they don't know
- Why "confident and wrong" is the default mode
- The key insight: LLMs are brilliant writers but unreliable researchers — which is why they need RAG

**Links to:** C01 (RAG), C05 (hallucinations), C06 (fine-tuning vs RAG)
**CTA:** "Wij combineren de schrijfkracht van een LLM met de onderzoeksprecisie van RAG — het beste van twee werelden"

---

### C08 — Wat is het verschil tussen AI, machine learning, en deep learning?

**Slug:** /blog/ai-ml-deep-learning-verschil
**Target keyword:** verschil AI machine learning deep learning
**Search intent:** Foundational — demystifying jargon
**Audience:** Non-technical professionals overwhelmed by buzzwords

**Content outline:**
- Simple nested circles: AI > Machine Learning > Deep Learning > LLMs
- Each level explained in one paragraph with a legal analogy
- Why it matters for choosing tools: not all "AI" is equal
- Cut through vendor marketing: when someone says "AI-powered," what do they actually mean?
- What to ask vendors: specific questions that reveal the actual technology

**Links to:** C07 (LLM), C01 (RAG), S01 (buyer's guide)
**CTA:** "Bij Auryth zijn we transparant over onze technologie — geen buzzwords, maar uitleg over hoe het echt werkt"

---

## Cluster 2: Technical Depth

For curious professionals and technical buyers doing due diligence. More detailed, diagram-heavy.

### T01 — Wat is chunking — en waarom is het cruciaal voor juridische AI?

**Slug:** /blog/wat-is-chunking-juridische-ai
**Target keyword:** chunking AI, document chunking legal
**Search intent:** Technical — understanding retrieval quality
**Audience:** Technical buyers, curious professionals

**Content outline:**
- The problem: AI has a limited context window. You can't feed it entire legal codes.
- Naive approach: split every 500 characters. Why this destroys legal meaning (splits mid-article, separates conditions from exceptions)
- Smart approach: split at legal boundaries — articles, paragraphs, alinea's
- Why this matters: a chunk that contains the full article with all its conditions gives much better answers than a random text fragment
- Visual: same WIB article chunked naively vs at legal boundaries
- Metadata preservation: each chunk carries its article number, effective dates, jurisdiction

**Links to:** C01 (RAG), T03 (authority ranking), T02 (reranking), C02 (semantic search)
**CTA:** "Wij chunken op juridische grenzen — artikelen, paragrafen, alinea's — nooit willekeurige teksteenheden"

---

### T02 — Wat is reranking — en waarom vindt u daarmee betere bronnen?

**Slug:** /blog/wat-is-reranking
**Target keyword:** reranking AI, cross-encoder reranking
**Search intent:** Technical
**Audience:** Technical buyers

**Content outline:**
- Two-stage search: first cast a wide net (fast), then rank carefully (smart)
- Stage 1 (retrieval): BM25 + vector search finds 50-100 candidates quickly
- Stage 2 (reranking): a cross-encoder model compares each candidate against the actual question
- Why this dramatically improves quality: the reranker can understand nuance that simple search misses
- Legal-specific reranking: boosting higher-authority sources in the ranking

**Links to:** C02 (semantic search), T03 (authority ranking), T01 (chunking)
**CTA:** "Onze reranker rankt niet alleen op relevantie — hogere bronnen in de juridische hiërarchie krijgen automatisch voorrang"

---

### T03 — Wat is authority ranking in juridische AI?

**Slug:** /blog/authority-ranking-juridische-ai
**Target keyword:** juridische hiërarchie AI, bronnen rangschikking
**Search intent:** Domain-specific — legal professionals will immediately recognize this need
**Audience:** All legal/tax professionals

**Content outline:**
- The Belgian legal hierarchy explained: Grondwet → Wet → KB → MB → Circulaire → Rechtspraak → Doctrine
- The full hierarchy with examples per level
- Why no other AI tool does this: most treat a blog post and a Cassatie arrest the same way
- Practical impact: when a circular contradicts a law, which should the AI prioritize?
- How we implement it: authority tier as a field on every chunk, boosted in reranking

**Links to:** T02 (reranking), T01 (chunking), TR04 (temporal versioning)
**CTA:** "Wij zijn de enige tool die de volledige Belgische juridische hiërarchie in het zoekalgoritme heeft ingebouwd"

---

### T04 — Wat is citatievalidatie — en hoe voorkomt het fouten?

**Slug:** /blog/wat-is-citatievalidatie
**Target keyword:** citation validation AI, bronverificatie AI
**Search intent:** Trust-building — professionals worried about AI accuracy
**Audience:** All professionals

**Content outline:**
- The problem: AI can generate plausible-sounding citations that don't exist
- How citation validation works: after the AI generates an answer, a separate system checks every cited source
- Three checks: (1) Does the source exist in our corpus? (2) Does the source actually say what the AI claims? (3) Is the source still current?
- What happens when validation fails: the citation is flagged or removed, confidence score drops
- NLI (Natural Language Inference): using a second AI model to verify claims against source text

**Links to:** C05 (hallucinations), TR02 (confidence scoring), C01 (RAG)
**CTA:** "Elk antwoord doorloopt onze citatievalidator voordat u het ziet — gefabriceerde bronnen worden automatisch gedetecteerd"

---

### T05 — Hoe werkt hybride zoektechnologie?

**Slug:** /blog/hybride-zoektechnologie
**Target keyword:** hybrid search, BM25 vector search combinatie
**Search intent:** Technical
**Audience:** Technical buyers

**Content outline:**
- Keyword search (BM25): fast, precise, great for exact article numbers and legal terms
- Semantic search (vectors): understands meaning, finds related concepts, handles synonyms
- Why you need both: keyword catches "Art. 344 WIB" exactly, semantic catches "antimisbruikbepaling" conceptually
- Reciprocal Rank Fusion: how we merge two result sets into one ranked list
- Examples where hybrid beats either alone

**Links to:** C02 (semantic search), C03 (embeddings), T02 (reranking)
**CTA:** "Onze hybride zoekmachine vindt wat geen van beide technieken alleen zou vinden"

---

### T06 — Wat is document-aware retrieval?

**Slug:** /blog/document-aware-retrieval
**Target keyword:** document context AI, whole document retrieval
**Search intent:** Technical
**Audience:** Technical buyers

**Content outline:**
- The fragment problem: most RAG systems retrieve disconnected text snippets
- Why context matters: a paragraph about an exception makes no sense without the general rule
- Whole-document retrieval: our AI sees the complete legal provision in context
- Dynamic section fetching: if the AI needs more context, it can request adjacent sections
- Sibling metadata: each chunk knows what article comes before and after it

**Links to:** T01 (chunking), C01 (RAG), T02 (reranking)
**CTA:** "Onze AI ziet complete wetsbepalingen in context — niet losgerukte fragmenten"

---

### T07 — Wat is een knowledge graph — en waarom is dat belangrijk voor fiscaal recht?

**Slug:** /blog/knowledge-graph-fiscaal-recht
**Target keyword:** knowledge graph juridisch, kennisgraaf wetgeving
**Search intent:** Technical — differentiator explanation
**Audience:** Technical buyers, curious professionals

**Content outline:**
- What a knowledge graph is: entities (articles, rulings, concepts) connected by typed relationships
- Types of connections: "amends," "interprets," "overrules," "exception_of," "cites"
- Why this matters for tax: Art. X references Art. Y which was amended by Law Z which was interpreted by Ruling W
- The exception chain problem: Belgian tax is full of rules → exceptions → exceptions-to-exceptions
- Visual: small subgraph showing how one tax provision connects to 10+ related documents
- Why no competitor has this: it requires structured ingestion, not just dumping PDFs into a search engine

**Links to:** T03 (authority ranking), T01 (chunking), TR04 (temporal versioning), C01 (RAG)
**CTA:** "Wij doorzoeken geen documenten — wij navigeren een kennisgraaf van Belgisch fiscaal recht"

---

### T08 — Hoe werkt onze ingestion pipeline?

**Slug:** /blog/ingestion-pipeline-achter-schermen
**Target keyword:** data pipeline legal AI, juridische AI data verwerking
**Search intent:** Behind-the-scenes — builds trust through transparency
**Audience:** Technical buyers, professionals curious about quality control

**Content outline:**
- Where our data comes from: Fisconetplus, official legal publications, court databases
- Four-layer quality gate: structure → quality → metadata → deduplication
- Quarantine system: new content is reviewed by administrators before becoming searchable
- Article-aware parsing: understanding legal document structure (titles, chapters, articles, paragraphs)
- Metadata extraction: effective dates, jurisdiction, authority level, cross-references
- Version management: new version of a law doesn't replace the old one — both coexist with temporal metadata
- Why this matters: garbage in = garbage out. Our corpus quality determines our answer quality.

**Links to:** T01 (chunking), TR04 (temporal versioning), T03 (authority ranking), A05 (behind the scenes)
**CTA:** "Kwaliteitscontrole begint bij de bron. Elk document doorloopt vier kwaliteitspoorten voordat het doorzoekbaar wordt."

---

## Cluster 3: Trust & Safety

Articles addressing the core concern: "Can I actually rely on this?"

### TR01 — Waarom transparantie belangrijker is dan nauwkeurigheid

**Slug:** /blog/transparantie-vs-nauwkeurigheid
**Target keyword:** AI betrouwbaarheid juridisch, transparantie AI
**Search intent:** Philosophical — thought leadership
**Audience:** Decision-makers, senior professionals

**Content outline:**
- The counterintuitive argument: a tool that's 90% accurate and honest about it is safer than one that's 95% accurate and never tells you when it's wrong
- In tax practice, the cost of false certainty is always higher than the cost of knowing your limits
- What transparency looks like in practice: confidence scores, source visibility, negative retrieval
- Why most AI tools don't do this: it's harder to sell, it requires more engineering, it means admitting imperfection
- Our philosophy: we'd rather give you an honest "we're not sure" than a convincing answer built on thin evidence

**Links to:** TR02 (confidence scoring), TR03 (negative retrieval), C05 (hallucinations)
**CTA:** "Onze belofte: niet dat we altijd gelijk hebben — maar dat u altijd weet waar u staat"

---

### TR02 — Wat is confidence scoring — en waarom is het eerlijker dan een zelfzeker antwoord?

**Slug:** /blog/confidence-scoring-uitgelegd
**Target keyword:** confidence score AI, betrouwbaarheidsscore
**Search intent:** Feature explanation — unique differentiator
**Audience:** All professionals

**Content outline:**
- What confidence scoring is: a numeric indicator of how well-supported an answer is
- Two dimensions: source coverage (how many relevant sources found) and reasoning certainty (how clearly the sources support the conclusion)
- High confidence: multiple authoritative sources agree, clear legal basis
- Low confidence: few sources found, conflicting interpretations, or relying on analogical reasoning
- Why this helps you: know when to trust immediately vs when to dig deeper yourself
- What competitors do instead: present everything with equal confidence (which means you can't tell the difference)

**Links to:** TR01 (transparency), T04 (citation validation), C05 (hallucinations)
**CTA:** "Elk antwoord op Auryth krijgt een betrouwbaarheidsscore — zodat u weet hoeveel gewicht u eraan kunt geven"

---

### TR03 — Wat is negative retrieval — en waarom vertellen wij u wat we niét gevonden hebben?

**Slug:** /blog/negative-retrieval-uitgelegd
**Target keyword:** negative retrieval AI, afwezigheid bewijs
**Search intent:** Feature explanation — unique differentiator
**Audience:** Legal/tax professionals (they'll immediately understand the value)

**Content outline:**
- In legal research, what you DON'T find matters as much as what you do
- Negative retrieval: showing which sources the system looked at and ruled out
- The "boundary of the advice" concept: knowing the limits of the answer
- Example: "No specific circular found on this topic" is valuable information — it tells you you're in interpretation territory
- Why no competitor does this: it requires tracking what was considered, not just what was returned
- The professional's judgment: negative retrieval gives you the complete picture to make your own assessment

**Links to:** TR02 (confidence scoring), TR01 (transparency), T04 (citation validation)
**CTA:** "Wij vertellen u niet alleen wat we gevonden hebben — maar ook wat we gezocht en niet gevonden hebben"

---

### TR04 — Wat is temporele versionering in juridische AI?

**Slug:** /blog/temporele-versionering-juridische-ai
**Target keyword:** temporele versionering wetgeving, point-in-time retrieval
**Search intent:** Feature explanation — unique differentiator
**Audience:** All tax professionals

**Content outline:**
- The problem: tax law changes constantly. The corporate tax rate was different in 2017, 2018, 2020, and 2024.
- What happens without temporal awareness: the AI gives you today's rate when you asked about 2019
- How we solve it: every provision carries effective_from, effective_to, and assessment year metadata
- Point-in-time retrieval: ask "what was the law in 2019?" and get the 2019 version, not today's
- Version chains: see how an article evolved over time
- Why this is hard: it requires structured ingestion that tracks amendments, not just full-text search
- Why no competitor has this: it's architecturally expensive and requires deep domain understanding

**Links to:** T01 (chunking), T08 (ingestion pipeline), T07 (knowledge graph), C06 (fine-tuning vs RAG)
**CTA:** "Elke bepaling in ons systeem draagt een effectieve datum — wij verwarren 2019 nooit met 2026"

---

### TR05 — Hoe wij omgaan met onzekerheid en tegenstrijdige bronnen

**Slug:** /blog/onzekerheid-tegenstrijdige-bronnen
**Target keyword:** AI tegenstrijdige bronnen, juridische AI onzekerheid
**Search intent:** Trust-building
**Audience:** Senior professionals worried about edge cases

**Content outline:**
- The reality: Belgian tax law contains genuine ambiguities and contradictions
- A circular may say one thing, a ruling another, and doctrine a third
- What most AI tools do: pick one and present it confidently (dangerous)
- What we do: detect contradictions, flag them, and show you all sides
- The contradiction detector: pairs of sources that disagree, surfaced explicitly
- Your judgment remains central: we give you the information, you make the call

**Links to:** TR01 (transparency), TR02 (confidence scoring), TR03 (negative retrieval), T03 (authority ranking)
**CTA:** "Wanneer bronnen tegenstrijdig zijn, tonen wij beide kanten — uw oordeel blijft het eindoordeel"

---

### TR06 — Staleness detection: hoe wij u waarschuwen wanneer uw onderzoek verouderd is

**Slug:** /blog/staleness-detection
**Target keyword:** juridisch onderzoek verouderd, wetswijziging notificatie
**Search intent:** Feature explanation — unique differentiator
**Audience:** All professionals

**Content outline:**
- The problem: you researched a topic 3 months ago, the law changed last week, your saved research is now wrong
- How we detect staleness: when a source cited in your saved answer is updated in our corpus, we flag it
- What the notification looks like: "De bronnen in dit opgeslagen onderzoek zijn gewijzigd sinds [datum]"
- Article-level subscriptions: follow specific provisions and get notified when they change
- Legislative change feed: a real-time stream of amendments, new circulars, new rulings
- Why this matters for liability: advising clients based on outdated research is a professional risk

**Links to:** TR04 (temporal versioning), T08 (ingestion pipeline), A05 (behind the scenes)
**CTA:** "Nooit meer adviseren op basis van verouderd onderzoek — wij waarschuwen u automatisch wanneer bronnen wijzigen"

---

## Cluster 4: UX & Workflow

How the product fits into daily professional practice.

### W01 — Waarom wij geen chatbot bouwen

**Slug:** /blog/waarom-geen-chatbot
**Target keyword:** juridische AI chatbot verschil, research tool vs chatbot
**Search intent:** Positioning — differentiation from ChatGPT and Creyten
**Audience:** All professionals

**Content outline:**
- Chat interface = casual, unstructured, ephemeral. Fine for brainstorming, terrible for professional research.
- Research platform = structured output, consistent format, auditable, exportable
- The AnswerCard concept: every answer has a consistent structure (conclusion, sources, exceptions, confidence, gaps)
- Why this matters: you need to save, compare, export, and defend your research. A chat transcript doesn't cut it.
- Professional workflow integration: PDF export with citation appendix, client folder organization
- Creyten comparison (without naming): "Some tools give you a chatbot with footnotes. We give you a research assistant with a structured dossier."

**Links to:** W02 (research cards), W03 (export), TR02 (confidence scoring)
**CTA:** "Een professionele onderzoekstool, geen chatbot. Elk antwoord gestructureerd, exporteerbaar, en controleerbaar."

---

### W02 — De Research Card: gestructureerde antwoorden voor professionals

**Slug:** /blog/research-card-uitgelegd
**Target keyword:** gestructureerd juridisch onderzoek AI
**Search intent:** Feature explanation — product showcase
**Audience:** All professionals

**Content outline:**
- What a Research Card contains: scope header, conclusion with inline citations, source chain (ranked by authority), exception map, negative retrieval, confidence indicators, regional comparison
- Why structure matters: you can scan, compare, and verify systematically
- Conversational refinement: follow-up questions refine the card, they don't replace it
- Saved research: build a library of cards organized by client or topic
- Compare two cards: how did the answer change when the law changed?

**Links to:** W01 (not a chatbot), W03 (export), TR02 (confidence scoring), TR03 (negative retrieval)
**CTA:** "Geen muur van tekst — een gestructureerde onderzoekskaart met bronnen, vertrouwensscore en uitzonderingenkaart"

---

### W03 — Van onderzoek naar cliëntadvies: export en dossiervorming

**Slug:** /blog/export-dossiervorming
**Target keyword:** fiscaal onderzoek exporteren, AI advies documentatie
**Search intent:** Workflow — how the tool fits into daily practice
**Audience:** All professionals

**Content outline:**
- The last mile: great research is useless if you can't use it in your client work
- PDF export with full citation appendix: professional enough to include in a client dossier
- Citation chain: every source linked, every article referenced, every temporal scope noted
- Audit trail: full log of what was asked, what was returned, when
- Why this matters for professional liability: you can demonstrate the research behind your advice

**Links to:** W01 (not a chatbot), W02 (research cards), TR04 (temporal versioning)
**CTA:** "Van onderzoeksvraag naar cliëntadvies — met een volledig geciteerd dossier in één klik"

---

### W04 — Regionale vergelijking: Vlaanderen vs. Brussel vs. Wallonië in één klik

**Slug:** /blog/regionale-vergelijking-belgisch-fiscaal-recht
**Target keyword:** erfbelasting vlaanderen brussel wallonië vergelijking, regionale belastingverschillen
**Search intent:** Feature explanation + SEO magnet (high search volume topic)
**Audience:** All Belgian tax professionals

**Content outline:**
- The Belgian complexity: three regions, three sets of rules, constantly diverging
- The daily pain: manually comparing Vlaamse Codex Fiscaliteit vs Brussels Wetboek vs Waalse Code
- How our regional comparison works: ask one question, get a side-by-side matrix
- Automatic detection: when a question involves regionalized taxes, the comparison triggers
- Examples: erfbelasting, schenkbelasting, registratierechten, onroerende voorheffing
- Why this doesn't exist elsewhere: it requires jurisdiction-tagged ingestion + multi-corpus retrieval

**Links to:** TR04 (temporal versioning), T03 (authority ranking), W02 (research cards)
**CTA:** "Eén vraag. Drie regio's. Alle tarieven, vrijstellingen en voorwaarden naast elkaar."

---

### W05 — Cross-domain analyse: van één vraag naar alle fiscale implicaties

**Slug:** /blog/cross-domain-fiscale-analyse
**Target keyword:** cross-domain fiscale analyse, alle belastinggevolgen één transactie
**Search intent:** Feature explanation — key differentiator
**Audience:** Tax professionals dealing with complex dossiers

**Content outline:**
- The TAK 23 example: one insurance product triggers income tax, insurance tax, Flemish gift/inheritance tax, potential TOB
- Current reality: professionals manually check each domain, hoping they don't miss one
- How our domain radar works: the system automatically identifies which tax domains a question touches
- Knowledge graph traversal: follow cross-references across domains
- Anti-abuse detection: automatic scan for relevant anti-abuse provisions
- The IRAC structure: Issue → Rule → Application → Conclusion, per domain
- Why this is the hardest feature to build — and the most valuable

**Links to:** T07 (knowledge graph), T03 (authority ranking), W02 (research cards), TR04 (temporal versioning)
**CTA:** "Eén vraag. Alle fiscale domeinen. Alle implicaties. Met bronnen."

---

## Cluster 5: Legal & Regulation

Positioning Auryth within the regulatory context.

### L01 — De EU AI Act en juridische AI: wat u moet weten

**Slug:** /blog/eu-ai-act-juridische-ai
**Target keyword:** EU AI Act juridisch, AI wetgeving europa advocaten
**Search intent:** Regulatory awareness — timely and evergreen
**Audience:** Decision-makers, compliance officers

**Content outline:**
- What the AI Act requires for AI tools used in legal/professional contexts
- Transparency obligations: users must know they're interacting with AI
- High-risk classification: does legal AI qualify? Current interpretations.
- What to look for in a tool: audit trails, human oversight, transparency reports
- How Auryth complies: full query logging, source transparency, confidence scoring, human-in-the-loop design

**Links to:** L02 (GDPR), S01 (buyer's guide), TR01 (transparency)
**CTA:** "Auryth is ontworpen met de AI Act in gedachten — volledige audit trails, brontransparantie, en menselijk toezicht"

---

### L02 — GDPR en juridische AI: hoe wij omgaan met uw gegevens

**Slug:** /blog/gdpr-juridische-ai
**Target keyword:** GDPR AI tool, privacy juridische AI
**Search intent:** Compliance / trust
**Audience:** Decision-makers, privacy-conscious professionals

**Content outline:**
- What data we process: queries (anonymized in telemetry), account data, research trails
- What we don't process: client documents, personal data of your clients
- EU data residency: all data stored on EU servers (Hetzner, Germany)
- GDPR rights: access, deletion, portability — all supported
- Research trail retention: you control it, default 18-24 months
- No model training on your queries: your research stays private

**Links to:** L01 (AI Act), L03 (professional liability), S01 (buyer's guide)
**CTA:** "Alle gegevens in de EU. Geen training op uw queries. Volledige GDPR-compliance."

---

### L03 — AI en beroepsaansprakelijkheid: wat als het antwoord fout is?

**Slug:** /blog/ai-beroepsaansprakelijkheid
**Target keyword:** aansprakelijkheid AI juridisch advies, AI fout fiscaal
**Search intent:** Risk management — a question every professional has
**Audience:** All professionals, especially senior partners

**Content outline:**
- The elephant in the room: what happens when an AI-assisted research answer leads to wrong advice?
- Current legal framework: AI is a tool, professional responsibility remains with the advisor
- How our design mitigates risk: confidence scoring, source citations, audit trail, disclaimers
- The importance of verification: our tool accelerates research, it doesn't replace professional judgment
- Practical recommendations: how to use AI research defensibly (document the sources, note the confidence level, verify key citations)
- Emerging insurance products for AI-assisted professional work

**Links to:** TR01 (transparency), TR02 (confidence scoring), W03 (export), L01 (AI Act)
**CTA:** "Wij bouwen geen vervanging voor uw expertise — maar een versneller die u helpt meer te vinden en minder te missen"

---

### L04 — Auteursrecht en doctrine: hoe wij omgaan met beschermde bronnen

**Slug:** /blog/auteursrecht-doctrine-ai
**Target keyword:** auteursrecht juridische AI, doctrine copyright
**Search intent:** Legal compliance — shows seriousness
**Audience:** Publishers, academics, compliance-conscious professionals

**Content outline:**
- The doctrine challenge: scholarly publications are copyrighted, but essential for comprehensive research
- Our approach: full text stored internally for RAG retrieval, but only summaries + metadata shown to users
- What you see: a summary of the doctrinal argument + citation to the publication (not the full text)
- Publisher relationships: our goal is to drive traffic to publications, not replace them
- Sensitivity tiers: public sources (full text), licensed sources (summary + metadata only)

**Links to:** T08 (ingestion pipeline), T03 (authority ranking)
**CTA:** "Wij respecteren auteursrecht door ontwerp — samenvattingen en verwijzingen, niet volledige reproducties"

---

### L05 — Meertaligheid in Belgisch fiscaal recht: waarom NL/FR essentieel is

**Slug:** /blog/meertaligheid-belgisch-fiscaal-recht
**Target keyword:** tweetalig fiscaal recht België, NL FR juridisch
**Search intent:** Feature explanation + Belgian identity
**Audience:** All Belgian professionals

**Content outline:**
- The Belgian reality: federal law is published in NL and FR, regional law varies, some rulings are monolingual
- Why monolingual tools miss half the corpus
- Cross-lingual retrieval: query in Dutch, find French sources that are relevant
- Bilingual glossary: correct legal terminology in both languages
- Practical example: searching for a concept in one language, finding the authoritative ruling in the other
- Why this is hard: legal terms in NL and FR don't map 1:1 (e.g., "onroerende voorheffing" vs "précompte immobilier")

**Links to:** C03 (embeddings), C02 (semantic search), W04 (regional comparison)
**CTA:** "Vraag in het Nederlands, vind bronnen in het Frans. Automatisch."

---

## Cluster 6: Market & Trends

Forward-looking thought leadership. LinkedIn-friendly, shareable.

### M01 — De toekomst van fiscaal onderzoek: wat verandert er (en wat niet)

**Slug:** /blog/toekomst-fiscaal-onderzoek
**Target keyword:** toekomst fiscaal beroep AI, AI belastingadviseur
**Search intent:** Thought leadership — vision piece
**Audience:** All professionals thinking about their future

**Content outline:**
- What AI will change: research speed, coverage completeness, change monitoring, routine queries
- What AI won't change: professional judgment, client relationships, strategic advice, interpretation of ambiguous law
- The augmentation thesis: the best professionals will use AI to be faster and more thorough, not to be replaced
- New skills: knowing how to evaluate AI output, how to prompt effectively, how to verify systematically
- The competitive dynamic: professionals who adopt AI research tools will have a structural advantage
- Prediction: within 5 years, NOT using AI-assisted research will be seen as negligent

**Links to:** S02 (AI-weerstand), S03 (adoption), L03 (professional liability)
**CTA:** "Wij bouwen niet een vervanging — maar een versneller. De professionals die het eerst adopteren, zullen het voordeel voelen."

---

### M02 — Waarom de Belgische markt schreeuwt om gespecialiseerde fiscale AI

**Slug:** /blog/belgische-markt-fiscale-ai
**Target keyword:** belgische fiscale AI markt, tax AI België
**Search intent:** Market analysis — positions Auryth's opportunity
**Audience:** Decision-makers, potential investors, journalists

**Content outline:**
- Belgian tax complexity: 3 regions, NL/FR/DE, federal + regional, constant changes
- The fragmented tooling landscape: Fisconetplus, Jura, Monkey — none integrated, none AI-powered
- Global AI tools don't serve Belgium: Harvey (PwC-only), Blue J (US/CA/UK), CoCounsel (US/UK)
- The only local player: Creyten (basic RAG, limited features)
- Market size: 12,000+ fiscal professionals, underserved and ready for better tools
- Why Belgium is actually a great market for AI: high complexity = high willingness to pay for solutions

**Links to:** M01 (future), S01 (buyer's guide), L01 (AI Act)
**CTA:** "Gebouwd voor de complexiteit van het Belgische fiscale landschap. Door mensen die het elke dag meemaken."

---

### M03 — Wat de Stanford hallucination study betekent voor juridische AI

**Slug:** /blog/stanford-hallucination-study-juridische-ai
**Target keyword:** Stanford AI hallucinaties juridisch, legal AI hallucination study
**Search intent:** News commentary — positions you as thought leader
**Audience:** All professionals, shareable

**Content outline:**
- Summary: Stanford researchers found even premium legal AI tools (Westlaw, LexisNexis) hallucinated 17-33% of the time
- What this means for tax professionals: even "trusted" tools fabricate sources
- Why legal AI hallucination is especially dangerous: it looks right, cites plausible-sounding sources, and professionals may not verify
- The root cause: generic RAG without citation validation
- How we address this: post-generation verification, NLI checking, confidence scoring
- The broader lesson: accuracy claims without published metrics are meaningless

**Links to:** C05 (hallucinations), T04 (citation validation), TR01 (transparency), TR02 (confidence scoring)
**CTA:** "Daarom publiceren wij onze nauwkeurigheidsmetrieken — want beloftes zonder bewijs zijn waardeloos"

---

### M04 — AI-adoptie in juridische beroepen: waar staan we in 2026?

**Slug:** /blog/ai-adoptie-juridische-beroepen-2026
**Target keyword:** AI adoptie advocaten 2026, juridische AI trends
**Search intent:** Industry overview — positions you as informed
**Audience:** All professionals, industry observers

**Content outline:**
- State of adoption: Clio Legal Trends Report data, ABA surveys
- Belgian/European context: slower than US/UK but accelerating
- What's driving adoption: competitive pressure, younger generation, better tools
- What's holding back adoption: trust concerns, liability questions, cost, inertia
- The "iPhone moment": when tools become good enough that non-adoption becomes the exception
- Predictions for 2026-2028

**Links to:** M01 (future), M02 (Belgian market), S02 (AI resistance)
**CTA:** "De professionals die nu adopteren, bouwen een structureel voordeel op. Start uw proefperiode."

---

### M05 — Harvey, Blue J, Legora: wat we kunnen leren van de grote spelers

**Slug:** /blog/wat-leren-van-grote-legal-ai-spelers
**Target keyword:** Harvey AI review, Blue J Tax, Legora legal AI vergelijking
**Search intent:** Market analysis — people searching for these competitors find your blog
**Audience:** Decision-makers evaluating options

**Content outline:**
- Harvey: $300M+ raised, PwC partnership, VLAIR benchmark leader. What they do well (scale, enterprise features) and what they miss (Belgium-specific depth, accessibility)
- Blue J: $122M raised, IBFD partnership, 90% outcome prediction. What they do well (tax-specific) and what they miss (no Belgian coverage)
- Legora: $266M raised, European focus. What they do well (European expansion) and what they miss (no tax specialization)
- Common thread: they're all enterprise-priced, US/UK-focused, and not built for Belgian tax complexity
- The gap: accessible, Belgian-specific, tax-specialized AI with full transparency

**Links to:** C06 (fine-tuning vs RAG), M02 (Belgian market), S01 (buyer's guide)
**CTA:** "Enterprise-niveau intelligentie, toegankelijk voor elke fiscalist. Dat is waar wij voor bouwen."

---

## Cluster 7: Strategic & Decision Support

Content for firm partners and decision-makers evaluating AI tools.

### S01 — Hoe evalueert u een juridische AI-tool? 10 vragen die u moet stellen

**Slug:** /blog/juridische-ai-tool-evalueren
**Target keyword:** juridische AI kiezen, AI tool evalueren advocaten
**Search intent:** High-intent — actively shopping for a tool
**Audience:** Decision-makers, managing partners

**Content outline:**
1. Where do the sources come from? (curated corpus vs internet scraping)
2. Can you verify citations? (clickable links to original sources vs opaque references)
3. Does it know when it's uncertain? (confidence scoring vs uniform confidence)
4. How current is the data? (real-time updates vs periodic retraining)
5. Does it understand legal hierarchy? (authority ranking vs flat search)
6. Can it handle temporal questions? (point-in-time retrieval vs single-version)
7. How is your data handled? (GDPR, residency, training on queries)
8. What happens when it's wrong? (audit trail, disclaimer, professional liability)
9. Can you export for professional use? (structured reports vs chat transcripts)
10. Does it publish accuracy metrics? (public dashboard vs trust-me claims)

- Each question maps to an Auryth strength — but the article is genuinely useful even for evaluating competitors

**Links to:** All clusters — this is the central conversion article
**CTA:** "Wij zijn gebouwd om elk van deze tien vragen positief te beantwoorden. Test het zelf."

---

### S02 — "Ik vertrouw AI niet voor fiscaal advies" — en terecht. Hier is waarom u het toch moet proberen.

**Slug:** /blog/ai-weerstand-fiscaal-advies
**Target keyword:** AI vertrouwen juridisch, AI sceptisch advocaat
**Search intent:** Objection handling — for the skeptics
**Audience:** Hesitant professionals, senior partners resistant to AI

**Content outline:**
- Validate the concern: AI skepticism in legal/tax is rational. Most tools ARE unreliable.
- The ChatGPT experience: professionals tried it, got burned, swore off "AI" entirely
- Why this generation of tools is different: purpose-built, source-verified, honest about uncertainty
- The analogy: early calculators were mistrusted too. "I need to check the math myself." Now nobody checks.
- The pragmatic argument: you don't have to trust the AI — trust the sources it shows you. Verify what matters. Use it to find more, not to think less.
- The competitive reality: firms that adopt will outresearch firms that don't

**Links to:** M01 (future), TR01 (transparency), S01 (buyer's guide), C05 (hallucinations)
**CTA:** "Vertrouw niet op de AI. Vertrouw op de bronnen die het u toont. Dat is wat wij bedoelen met transparantie."

---

### S03 — AI implementeren in uw fiscale praktijk: een praktische gids

**Slug:** /blog/ai-implementeren-fiscale-praktijk
**Target keyword:** AI implementatie advocatenkantoor, AI invoeren belastingkantoor
**Search intent:** How-to — ready to adopt
**Audience:** Managing partners, team leads

**Content outline:**
- Start small: one user, one use case (e.g., TOB rate lookups)
- Build trust gradually: verify the first 20 answers manually. Track accuracy yourself.
- Expand to complex queries: cross-domain analysis, temporal questions
- Team rollout: shared templates, query library, best practices
- Measure ROI: time saved per dossier, queries per day, topics covered
- Common pitfalls: over-reliance without verification, under-utilization due to distrust, not leveraging export features

**Links to:** S01 (buyer's guide), S02 (AI resistance), W02 (research cards), W03 (export)
**CTA:** "Begin met 14 dagen gratis. Verifieer de eerste 20 antwoorden zelf. Oordeel dan."

---

### S04 — Hoeveel tijd bespaart fiscale AI? Een realistische inschatting.

**Slug:** /blog/tijdsbesparing-fiscale-ai
**Target keyword:** AI tijdsbesparing advocaat, hoeveel tijd bespaart AI
**Search intent:** ROI calculation — decision support
**Audience:** Decision-makers evaluating purchase

**Content outline:**
- Current time spent: 2-4 hours on complex cross-domain research (from our persona research)
- With Auryth: 15-30 minutes for the same scope (initial answer + verification)
- Conservative estimate: 1-2 hours saved per complex dossier
- At billing rates of €150-400/hr: one saved hour per week = €600-1,600/month in capacity
- Against pricing of €99-299/month: ROI of 5-15x
- Soft benefits: broader coverage (catch provisions you would have missed), change monitoring, audit trail
- Honest caveat: not every query saves time. Simple lookups might be faster in Fisconetplus. Complex research is where the value compounds.

**Links to:** S01 (buyer's guide), S03 (implementation), M01 (future)
**CTA:** "€99/maand. Eén complex dossier per week sneller afgerond. De ROI spreekt voor zich."

---

### S05 — Kosten-batenanalyse: Auryth TX vs. traditioneel bronnenonderzoek

**Slug:** /blog/kosten-baten-fiscale-ai
**Target keyword:** kosten AI vs manueel onderzoek, ROI fiscale AI
**Search intent:** Decision support — budget justification
**Audience:** Decision-makers needing to justify the expense

**Content outline:**
- Current costs: Monkey (€X/yr) + Jura (€X/yr) + Fisconetplus (free but time-intensive) + your hours
- AI-assisted costs: Auryth subscription + reduced research time
- Break-even calculation: at what point does the subscription pay for itself?
- The hidden costs of not using AI: missed provisions, outdated research, competitive disadvantage
- Comparison with enterprise alternatives: Harvey/CoCounsel at €200+/user vs Auryth at €99/user

**Links to:** S04 (time savings), S01 (buyer's guide), M02 (Belgian market)
**CTA:** "Bereken uw eigen ROI. Start gratis en meet het verschil."

---

## Cluster 8: Applied & Demonstration

Show-don't-tell content. Highest engagement, most shareable.

### A01 — Ik vroeg ChatGPT en Auryth dezelfde fiscale vraag — dit is wat er gebeurde

**Slug:** /blog/chatgpt-vs-auryth-vergelijking
**Target keyword:** chatgpt belastingen, chatgpt fiscaal advies test
**Search intent:** Curiosity — highest traffic potential
**Audience:** Everyone — this is your viral article

**Content outline:**
- Pick 3 questions of increasing complexity
- Question 1 (simple): "Wat is het tarief vennootschapsbelasting?" — both get it right, but Auryth cites the source
- Question 2 (temporal): "Wat was het TOB-tarief op accumulerende ETFs in 2021?" — ChatGPT gives 2026 rate, Auryth gives 2021 rate with version history
- Question 3 (cross-domain): "Wat zijn alle fiscale gevolgen van een TAK 23 product?" — ChatGPT gives partial, confident answer. Auryth gives structured multi-domain analysis with gaps identified.
- Screenshots of both answers
- Analysis: not "ChatGPT is bad" but "different tools for different purposes"
- The takeaway: for professional tax research, you need a purpose-built tool

**Links to:** C05 (hallucinations), C01 (RAG), TR02 (confidence scoring), W02 (research cards)
**CTA:** "Probeer het zelf. Stel uw eigen vraag en vergelijk."

---

### A02 — 5 fiscale vragen waar generieke AI gegarandeerd faalt

**Slug:** /blog/5-vragen-generieke-ai-faalt
**Target keyword:** AI fiscaal advies fouten, ChatGPT belasting fouten
**Search intent:** Problem-aware — professionals who've been burned
**Audience:** All professionals

**Content outline:**
1. Temporal: "Welk tarief gold in [historisch jaar]?" — AI gives current rate
2. Regional: "Wat is het tarief erfbelasting in Brussel voor neven?" — AI confuses Flemish and Brussels rates
3. Exception chain: "Is er een uitzondering op Art. 344 WIB?" — AI misses the exception-to-the-exception
4. Cross-domain: "Alle fiscale gevolgen van X" — AI covers 2 of 5 domains
5. Legislative change: "Is deze circulaire nog geldig?" — AI has no concept of staleness

- Each question shows WHY purpose-built tools handle it better — not just THAT they do

**Links to:** C05 (hallucinations), TR04 (temporal versioning), W04 (regional comparison), W05 (cross-domain)
**CTA:** "Deze vijf vragen zijn precies waarvoor Auryth TX is gebouwd. Test ze zelf."

---

### A03 — Case study: TAK 23 — het ultieme cross-domain voorbeeld

**Slug:** /blog/case-study-tak-23-cross-domain
**Target keyword:** TAK 23 fiscaliteit, fiscale behandeling TAK 23
**Search intent:** Substantive legal content + product demonstration
**Audience:** Tax professionals (high-intent)

**Content outline:**
- What TAK 23 is and why it's the perfect test case for cross-domain analysis
- The domains it touches: income tax (Art. 19bis WIB), insurance tax, Flemish gift/inheritance tax, TOB, regional registration duties
- How a manual research process looks (2-3 hours, multiple databases)
- How Auryth handles it: one question, structured multi-domain AnswerCard
- Walk through the actual output: domain radar, cross-references, exception chains, confidence per domain
- What the system catches that you might miss

**Links to:** W05 (cross-domain), W02 (research cards), T07 (knowledge graph), TR02 (confidence scoring)
**CTA:** "TAK 23 is onze lakmoesproef. Als wij dit correct kunnen, kunnen wij alles."

---

### A04 — Case study: erfbelasting successieplanning — drie regio's, één analyse

**Slug:** /blog/case-study-erfbelasting-regionale-vergelijking
**Target keyword:** erfbelasting planning regio vergelijking, successieplanning drie gewesten
**Search intent:** Substantive + product demo
**Audience:** Estate planning specialists

**Content outline:**
- Scenario: wealthy family with assets in Flanders, business in Brussels, vacation property in Wallonia
- The regional complexity: different rates, different exemptions, different conditions
- How Auryth's regional comparison handles it: one question, side-by-side matrix
- Walk through the output: rates per region, applicable exemptions, key differences highlighted
- What the advisor does with this: strategic advice based on comprehensive analysis
- Time saved: what used to take an afternoon now takes 15 minutes

**Links to:** W04 (regional comparison), TR04 (temporal versioning), W02 (research cards), A03 (TAK 23 case)
**CTA:** "Drie regio's. Eén vraag. Alle tarieven, vrijstellingen en voorwaarden naast elkaar."

---

### A05 — Achter de schermen: hoe een wetswijziging door ons systeem stroomt

**Slug:** /blog/achter-schermen-wetswijziging
**Target keyword:** hoe werkt juridische AI achter schermen
**Search intent:** Transparency — builds trust
**Audience:** Curious professionals, technical buyers

**Content outline:**
- A new law is published in the Belgisch Staatsblad
- Step 1: Detection — our watcher agent picks it up
- Step 2: Ingestion — structural parsing, article-aware chunking, metadata extraction
- Step 3: Quarantine — admin reviews the parsed content
- Step 4: Approval — content enters the live corpus
- Step 5: Impact analysis — knowledge graph identifies affected provisions
- Step 6: Staleness alerts — saved research citing affected provisions is flagged
- Step 7: Change feed — subscribers to affected articles get notified
- Timeline: from Staatsblad publication to searchable in our system = hours, not weeks

**Links to:** T08 (ingestion pipeline), TR06 (staleness detection), TR04 (temporal versioning), T07 (knowledge graph)
**CTA:** "Wanneer de Belgische fiscale wetgeving morgen verandert, weet ons systeem het morgen."

---

### A06 — Waarom wij onze nauwkeurigheid publiceren (en waarom niemand anders dat doet)

**Slug:** /blog/waarom-wij-nauwkeurigheid-publiceren
**Target keyword:** AI nauwkeurigheid dashboard, transparantie juridische AI
**Search intent:** Trust + differentiation — your boldest claim
**Audience:** All professionals, decision-makers

**Content outline:**
- What the public accuracy dashboard shows: citation accuracy, temporal accuracy, cross-domain completeness
- How we measure: golden dataset of 70+ expert-verified questions, run continuously
- Why we publish: because trust without evidence is just marketing
- Why nobody else does this: it's risky. When your accuracy dips, everyone sees it.
- Our philosophy: we'd rather show you a real 94% than claim a fake 99%
- The improvement cycle: every inaccuracy report becomes a new test case. The system gets better every week.
- Call to action: hold us accountable. If you find an error, report it. It becomes a test case.

**Links to:** TR01 (transparency), TR02 (confidence scoring), T04 (citation validation), M03 (Stanford study)
**CTA:** "Bekijk ons live nauwkeurigheidsdashboard. Geen beloftes — bewijs."

---

## Cluster 9: Standalone & Announcements

Articles that don't fit a thematic cluster but serve specific purposes.

### X01 — Waarom AI fiscaal onderzoek in België transformeert

**Slug:** /blog/ai-transformeert-fiscaal-onderzoek
**Target keyword:** AI fiscaal onderzoek België, AI belastingadvies
**Search intent:** Educational — broad intro for professionals discovering AI for tax
**Audience:** All professionals, entry-level awareness
**Category:** insight

**Content outline:**
- How AI is reshaping the way Belgian tax professionals find, verify, and apply tax law
- The current pain: fragmented databases, manual cross-referencing, outdated results
- What AI-powered research looks like: faster retrieval, source verification, change monitoring
- Belgian-specific challenges that make AI especially valuable: 3 regions, 2 languages, constant amendments
- What this means for your practice: augmentation, not replacement

**Links to:** C01 (RAG), C05 (hallucinations), M01 (future), S02 (AI resistance)
**CTA:** "Ontdek hoe AI-ondersteund onderzoek uw fiscale praktijk kan versnellen."

---

### X02 — Belgische beurstaks (TOB): wat elke belegger moet weten

**Slug:** /blog/belgische-beurstaks-tob-overzicht
**Target keyword:** beurstaks België, TOB tarief, taks op beursverrichtingen
**Search intent:** Practical — substantive tax content, high search volume
**Audience:** Tax professionals advising investors, wealth managers
**Category:** tax-update

**Content outline:**
- What the TOB is and who pays it
- Current rate structure: 0.12% / 0.35% / 1.32% tiers with applicable instruments
- Exemptions and special cases
- Accumulating vs distributing funds — the Art. 19bis interaction
- Practical compliance: reporting obligations, payment deadlines
- Recent changes and upcoming amendments

**Links to:** TR04 (temporal versioning), W04 (regional comparison), A03 (TAK 23 case)
**CTA:** "Auryth TX houdt alle TOB-tarieven actueel — inclusief historische versies en recente wijzigingen."

---

### X03 — Het Auryth Founding Member Programma

**Slug:** /blog/founding-member-programma
**Target keyword:** Auryth founding member, early adopter fiscale AI
**Search intent:** Product announcement — conversion-focused
**Audience:** Early adopters, professionals ready to commit
**Category:** product

**Content outline:**
- What the founding member program offers: permanent pricing lock, priority access, direct input on roadmap
- Why we're doing this: we need real practitioners to stress-test the system with real questions
- What founding members get that later users won't: grandfathered pricing, founding member badge, priority support
- How to join: waitlist → invite → onboarding

**Links to:** S01 (buyer's guide), S03 (implementation), S04 (time savings)
**CTA:** "Word founding member. Vergrendel uw tarief. Help ons bouwen wat u echt nodig hebt."

---

## Publishing Schedule

### Phase 1: Pre-launch (weeks -8 to 0)

| Week | Article | Cluster | Why now |
|------|---------|---------|---------|
| -8 | A01 — ChatGPT vs Auryth | Applied | Highest traffic potential, conversation starter |
| -6 | C05 — AI hallucinaties | Core | Problem awareness, shareable |
| -4 | C01 — Wat is RAG | Core | Foundation piece, educational |

### Phase 2: Launch month (month 1)

| Week | Article | Cluster | Why now |
|------|---------|---------|---------|
| 1 | TR01 — Transparantie vs nauwkeurigheid | Trust | Core philosophy piece |
| 2 | C06 — Fine-tuning vs RAG | Core | Competitor differentiation |
| 4 | S01 — 10 vragen evaluatie | Strategic | Decision-support for trial users |

### Phase 3: Growth (months 2-4)

| Month | Articles | Cluster |
|-------|----------|---------|
| 2 | TR02 (confidence scoring), A02 (5 failing questions), S02 (AI resistance) | Trust + Applied + Strategic |
| 3 | T03 (authority ranking), W01 (not a chatbot), A03 (TAK 23 case study) | Technical + UX + Applied |
| 4 | TR04 (temporal versioning), W04 (regional comparison), S04 (time savings) | Trust + UX + Strategic |

### Phase 4: Authority building (months 5-8)

| Month | Articles | Cluster |
|-------|----------|---------|
| 5 | T01 (chunking), T07 (knowledge graph), M01 (future of tax research) | Technical + Market |
| 6 | L01 (AI Act), A04 (erfbelasting case), S03 (implementation guide) | Legal + Applied + Strategic |
| 7 | T05 (hybrid search), T02 (reranking), M03 (Stanford study) | Technical + Market |
| 8 | A05 (behind the scenes), A06 (accuracy dashboard), L03 (professional liability) | Applied + Legal |

### Phase 5: Final thought leadership (months 9-11)

| Month | Article | Cluster | Why it's thought leadership |
|-------|---------|---------|----------------------------|
| 9 | TR05 (contradictory sources) | Trust | Philosophical stance on uncertainty — no competitor touches this |
| 9 | M02 (Belgian market for tax AI) | Market | Contrarian market thesis — "small market = big opportunity" |
| 10 | M04 (AI adoption 2026) | Market | Vision piece — LinkedIn shareability |
| 10 | M05 (Harvey, Blue J, Legora) | Market | Competitive landscape — high-intent SEO capture |
| 11 | L05 (bilingual Belgian tax law) | Legal | Core Belgian identity — nobody else can write this |

### Dropped articles → absorbed by glossary

The following were cut from the blog plan. Their concepts are covered by the glossary (4-locale definitional entries with SEO density):

| Dropped | Reason | Glossary entries covering it |
|---------|--------|------------------------------|
| C02 (semantic search) | Definitional — glossary covers it | `semantic-search`, `semantic-similarity` |
| C03 (embeddings) | Definitional — glossary covers it | `embeddings`, `cosine-similarity`, `dense-retrieval` |
| C04 (vector database) | Definitional — glossary covers it | `vector-database` |
| C07 (what is an LLM) | Definitional — glossary covers it | `llm`, `deep-learning`, `neural-network` |
| C08 (AI vs ML vs DL) | Definitional — glossary covers each | `machine-learning`, `deep-learning`, `llm` |
| T06 (document-aware retrieval) | Niche technical, low search volume | `chunking-strategy`, `sparse-retrieval` |
| T08 (ingestion pipeline) | Overlaps with published A05 | `indexing-strategy`, `content-discoverability` |
| TR03 (negative retrieval) | Feature explanation, not thought leadership | *Add to glossary* |
| TR06 (staleness detection) | Feature explanation, not thought leadership | *Add to glossary* |
| W02 (research card) | Product feature showcase | *Add to glossary* |
| W03 (export/dossier) | Product feature showcase | — |
| W05 (cross-domain analysis) | Product feature explanation | *Add to glossary* |
| L02 (GDPR) | Standard compliance, no edge | `eu-ai-act`, *add GDPR glossary entry* |
| L04 (copyright/doctrine) | Too niche, no search volume | — |
| S05 (cost-benefit) | Overlaps with published S04 | — |

### Ongoing

| Cadence | Content |
|---------|---------|
| Ongoing | New articles as product features ship, legislative changes occur, or market developments warrant |
| Quarterly | Update all published articles for accuracy and freshness |

---

## SEO Keyword Map

| Article | Primary keyword | Est. monthly volume | Intent |
|---------|----------------|--------------------|---------| 
| A01 | chatgpt belastingen | High | Curiosity |
| C05 | AI hallucinaties | Growing | Problem-aware |
| C01 | wat is RAG | Growing | Educational |
| S01 | juridische AI kiezen | Low, high-intent | Decision |
| C06 | fine-tuning vs RAG | Niche | Technical |
| TR01 | AI betrouwbaarheid juridisch | Medium | Trust |
| A02 | AI fiscaal advies fouten | Medium | Problem-aware |
| T03 | juridische hiërarchie | Medium (legal students) | Educational |
| W04 | erfbelasting regio vergelijking | High | Practical |
| M03 | Stanford AI hallucinaties | Medium | News-driven |
| S04 | AI tijdsbesparing advocaat | Medium | ROI |
| A03 | TAK 23 fiscaliteit | High | Substantive |
| L01 | EU AI Act juridisch | Growing | Regulatory |
| A06 | AI nauwkeurigheid dashboard | Low, unique | Trust |
| M01 | toekomst fiscaal beroep AI | Medium | Vision |

---

## Content Production Workflow

### Weekly routine (3 hours total)

| Step | Time | Who |
|------|------|-----|
| 1. Select next article from schedule | 5 min | You |
| 2. Claude generates full draft from outline | 15 min | AI |
| 3. You review for domain accuracy + legal correctness | 45 min | You |
| 4. You add personal examples / Belgian-specific nuance | 30 min | You |
| 5. Generate FR translation of key articles | 15 min | AI |
| 6. Schedule publication + social posts | 15 min | You |
| **Total** | **~2 hours** | |

### AI prompting template for blog drafts

```
Context: Auryth TX blog, thought leadership cluster on AI for Belgian tax professionals.
Article: [Title + slug]
Outline: [Paste outline from this document]
Audience: [From article spec]
Language: Dutch (Flemish register), professional but accessible. No jargon inflation.
Tone: Expert educator. Confident but honest. Never oversell.
Length: 1,200-1,800 words.
Structure: Introduction (hook) → Main content (3-5 sections) → Gerelateerde artikelen (links) → Hoe Auryth TX dit toepast (2-3 paragraphs) → CTA.
Rules:
- Use correct Belgian legal terminology
- Include at least 1 concrete example using real Belgian tax provisions
- Never make absolute claims ("We are the only tool that..."). Use "To our knowledge" phrasing.
- Educational content should be valuable even if the reader never uses Auryth
- The "Hoe Auryth dit toepast" section is clearly separated — it's the only sales part
```

---

## Metrics

| Metric | Target (month 6) | Target (month 12) |
|--------|------------------|-------------------|
| Total articles published | 15 | 35 |
| Monthly organic traffic (blog) | 2,000 visits | 8,000 visits |
| Average time on page | >3 minutes | >3 minutes |
| Email signups from blog | 50/month | 150/month |
| Trial signups from blog | 10/month | 40/month |
| LinkedIn shares per article | 15-25 | 30-50 |
| Domain authority (Ahrefs) | 15 | 30 |
| #1 ranking keywords | 5 | 20 |

---

## Cross-Promotion Strategy

Every blog article gets:
1. **LinkedIn post** — condensed version (150-200 words) with link to full article
2. **Email mention** — included in monthly digest as "Nieuw op de blog"
3. **Internal links** — connected to 2-3 other cluster articles
4. **Product link** — "Hoe Auryth dit toepast" section at the bottom
5. **SEO long-tail pages** link back to relevant blog articles as authoritative sources

This creates a flywheel: blog builds authority → SEO drives traffic → traffic drives trials → trials drive word-of-mouth → word-of-mouth drives LinkedIn engagement → LinkedIn drives blog traffic.

---

---

## Published Articles

| ID | Title | Date | Files |
|----|-------|------|-------|
| A01 | I Asked ChatGPT and Auryth the Same Belgian Tax Questions — Here's What Happened | 2026-02-13 | chatgpt-vs-auryth-vergelijking-en.mdx (+ nl, fr, de) |
| C05 | AI hallucinations: why ChatGPT fabricates sources (and how to spot it) | 2026-02-13 | ai-hallucinaties-fiscaal-en.mdx (+ nl, fr, de) |
| C01 | What is RAG — and why it's the only architecture that makes legal AI defensible | 2026-02-14 | wat-is-rag-en.mdx (+ nl, fr, de) |
| TR01 | Why transparency matters more than accuracy in legal AI | 2026-02-14 | transparantie-vs-nauwkeurigheid-en.mdx (+ nl, fr, de) |
| C06 | Fine-tuning vs. RAG: two ways to make AI smart — and why it matters which one your tax tool chose | 2026-02-14 | fine-tuning-vs-rag-en.mdx (+ nl, fr, de) |
| S01 | How to evaluate a legal AI tool: 10 questions that actually matter | 2026-02-14 | juridische-ai-tool-evalueren-en.mdx (+ nl, fr, de) |
| TR02 | What is confidence scoring — and why it's more honest than a confident answer | 2026-02-14 | confidence-scoring-uitgelegd-en.mdx (+ nl, fr, de) |
| A02 | 5 Belgian tax questions where generic AI is guaranteed to fail | 2026-02-15 | 5-vragen-generieke-ai-faalt-en.mdx (+ nl, fr, de) |
| S02 | "I don't trust AI for tax advice" — and you're right. Here's why you should try it anyway. | 2026-02-15 | ai-weerstand-fiscaal-advies-en.mdx (+ nl, fr, de) |
| T03 | What is authority ranking — and why your legal AI tool probably ignores it | 2026-02-16 | authority-ranking-juridische-ai-en.mdx (+ nl, fr, de) |
| W01 | Why we're not building a chatbot | 2026-02-17 | waarom-geen-chatbot-en.mdx (+ nl, fr, de) |
| A03 | Case study: TAK 23 — why one product needs five tax answers | 2026-02-18 | case-study-tak-23-cross-domain-en.mdx (+ nl, fr, de) |
| TR04 | What is temporal versioning — and why your legal AI tool probably serves you yesterday's law | 2026-02-19 | temporele-versionering-juridische-ai-en.mdx (+ nl, fr, de) |
| W04 | Three regions, three tax systems: why Belgian fiscal advice requires side-by-side comparison | 2026-02-20 | regionale-vergelijking-belgisch-fiscaal-recht-en.mdx (+ nl, fr, de) |
| S04 | How much time does tax AI actually save? An honest estimate | 2026-02-21 | tijdsbesparing-fiscale-ai-en.mdx (+ nl, fr, de) |
| T01 | What is chunking — and why it's the invisible foundation of legal AI quality | 2026-02-22 | wat-is-chunking-juridische-ai-en.mdx (+ nl, fr, de) |
| T07 | What is a knowledge graph — and why it changes how AI navigates Belgian tax law | 2026-02-23 | knowledge-graph-fiscaal-recht-en.mdx (+ nl, fr, de) |
| M01 | The future of tax research: what AI changes, what it doesn't, and what that means for your practice | 2026-02-24 | toekomst-fiscaal-onderzoek-en.mdx (+ nl, fr, de) |
| L01 | The EU AI Act and legal AI: what Belgian tax professionals actually need to know | 2026-02-25 | eu-ai-act-juridische-ai-en.mdx (+ nl, fr, de) |
| A04 | Case study: estate planning across three regions — one family, three tax outcomes | 2026-02-26 | case-study-erfbelasting-regionale-vergelijking-en.mdx (+ nl, fr, de) |
| S03 | Implementing AI in your tax practice: why trust matters more than technology | 2026-02-27 | ai-implementeren-fiscale-praktijk-en.mdx (+ nl, fr, de) |
| T05 | How hybrid search works — and why your legal AI tool probably uses only half the equation | 2026-02-28 | hybride-zoektechnologie-en.mdx (+ nl, fr, de) |
| T02 | What is reranking — and why it's the difference between finding documents and finding answers | 2026-03-01 | wat-is-reranking-en.mdx (+ nl, fr, de) |
| M03 | What the Stanford hallucination study actually revealed | 2026-03-02 | stanford-hallucination-study-juridische-ai-en.mdx (+ nl, fr, de) |
| A05 | Behind the scenes: how a law change flows through a legal AI system | 2026-03-03 | achter-schermen-wetswijziging-en.mdx (+ nl, fr, de) |
| L03 | AI and professional liability: what happens when the answer is wrong? | 2026-03-04 | ai-beroepsaansprakelijkheid-en.mdx (+ nl, fr, de) |
| A06 | Why we publish our accuracy — and why almost nobody else does | 2026-03-05 | waarom-wij-nauwkeurigheid-publiceren-en.mdx (+ nl, fr, de) |
| TR05 | How we handle contradictory sources — and why most AI tools don't | 2026-03-06 | onzekerheid-tegenstrijdige-bronnen-en.mdx (+ nl, fr, de) |
| M02 | Why Belgium is the perfect market for specialized tax AI | 2026-03-07 | belgische-markt-fiscale-ai-en.mdx (+ nl, fr, de) |
| M04 | AI adoption in legal professions: where we stand in 2026 | 2026-03-08 | ai-adoptie-juridische-beroepen-2026-en.mdx (+ nl, fr, de) |
| M05 | Harvey, Blue J, Legora: what we can learn from the big players in legal AI | 2026-03-09 | wat-leren-van-grote-legal-ai-spelers-en.mdx (+ nl, fr, de) |
| L05 | Bilingual Belgian tax law: why NL/FR is a prerequisite, not a feature | 2026-03-10 | meertaligheid-belgisch-fiscaal-recht-en.mdx (+ nl, fr, de) |

---

## Blog Categories Registry

Categories are free-form strings (not an enum). Use these established values for consistency:

| Category slug (EN) | EN display | NL display | FR display | DE display |
|---------------------|------------|------------|------------|------------|
| in-practice | In Practice | In de Praktijk | En Pratique | In der Praxis |
| ai-explained | AI explained | AI uitgelegd | IA expliquée | KI erklärt |
| trust-transparency | Trust & transparency | Vertrouwen & transparantie | Confiance & transparence | Vertrauen & Transparenz |
| strategy-decision | Strategy & decision | Strategie & beslissing | Stratégie & décision | Strategie & Entscheidung |
| legal-regulatory | Legal & regulatory | Juridisch & regelgeving | Juridique & réglementation | Recht & Regulierung |

*Add new categories here as articles in other clusters are published.*

---

*Last updated: February 2026*
*Version: 2.0 — reduced plan: glossary absorbs definitional/feature content*
*Total articles planned: 32 (32 published + 0 remaining)*
*Total articles published: 32*
*Blog content plan: COMPLETE*

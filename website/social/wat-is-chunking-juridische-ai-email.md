# Email snippet — T01: chunking

**Subject:** Your legal AI tool cuts the law into pieces. Here's why the cut matters more than the model.

**Preview text:** Naive chunking splits Article 171 WIB 92 into three fragments. The exception ends up in a different chunk.

---

Before any AI system can search the law, it must first divide it into searchable pieces — a process called "chunking." Most tools use fixed-size splitting: cut every 500 characters regardless of content.

For legal text, this is catastrophic. A Belgian tax article with a general rule in §1 and a critical exception in §2 gets split into separate chunks. The AI retrieves the rule without the exception. The answer looks confident. It's wrong.

Legal-boundary chunking cuts at the joints the legislator intended: articles, paragraphs, alinea's. Rule and exception stay together. Each chunk carries metadata — article number, jurisdiction, effective date, amendment history.

We mapped exactly how this works with Belgian tax law examples, including Article 171 WIB 92 and the VCF's distinctive numbering system.

[Read the full explanation ->]

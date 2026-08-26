# RAG Resources — for building `ragdoll`

Curated sources for the mission in [MISSION.md](./MISSION.md): a platform where a user creates a
project, uploads documents, and asks questions about them.

## Knowledge — retrieval core

- [Contextual Retrieval in AI Systems — Anthropic Engineering](https://www.anthropic.com/engineering/contextual-retrieval)
  The best short primer. The six-step baseline pipeline, the naive-chunking failure mode, hard numbers
  for each improvement. Use for: pipeline shape, chunk context, reranking, and the 200,000-token rule
  for when RAG is not needed.
- [Enhancing RAG with contextual retrieval — Claude Cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
  Runnable notebook of the post above. Use for: actual code when you build ingestion.
- [Claude API documentation](https://platform.claude.com/docs)
  Use for: model ids, prompt caching, citations, token counting.

## Knowledge — evaluation

- [A complete guide to RAG evaluation — Evidently AI](https://www.evidentlyai.com/llm-guide/rag-evaluation)
  Vendor-light treatment of golden datasets and retrieval metrics. Use for: exact definitions of
  recall@k, precision@k, hit rate, NDCG@k, and the order to evaluate things in.
- [Testset generation for RAG — Ragas docs](https://docs.ragas.io/en/stable/getstarted/rag_testset_generation/)
  Generates question and answer pairs from your own documents, with a mix of simple, reasoning and
  multi-context questions. Use for: the golden set. Critical, because ragdoll is domain-agnostic and
  has no expert to write questions by hand.
- [Ragas documentation](https://docs.ragas.io/)
  Use for: faithfulness, answer relevancy, context precision, context recall once a golden set exists.

## Knowledge — the platform layer

- [Multi-tenancy in vector databases — Pinecone](https://www.pinecone.io/learn/series/vector-databases-in-production-for-busy-engineers/vector-database-multi-tenancy/)
  Clear comparison of namespace-per-tenant against metadata filtering. Use for: how to keep one
  ragdoll project's chunks from leaking into another project's search.
- [Building multi-tenant RAG applications with PostgreSQL — TigerData](https://www.tigerdata.com/blog/building-multi-tenant-rag-applications-with-postgresql-choosing-the-right-approach)
  The pgvector route: a `project_id` on every row, plus Row Level Security as the safety net, plus
  HNSW indexes for speed. Use for: deciding whether ragdoll needs a separate vector database at all.
- [Docling — IBM, open source](https://github.com/docling-project/docling)
  Layout-aware document parser. Turns PDFs into structured markdown, keeping headings and tables.
  Use for: step one of ingestion. Headings matter, because they are what naive chunking throws away.
- [LlamaParse](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
  Managed alternative to Docling. Use for: comparison, and if self-hosted parsing becomes a time sink.

## Test corpus

Four PDFs Manuel owns, held in `corpus/` and gitignored. Not redistributable, so any exercise must
regenerate derived artefacts from local files rather than committing them.

Token counts below are **exact**, from the Claude API `count_tokens` endpoint against `claude-opus-5`,
over pypdf text extraction. Reproduce with `make ingest-fresh`.

| Document | Pages | Tokens | Tok/page | Alone |
|---|---:|---:|---:|---|
| Designing Data-Intensive Applications | 613 | 481,052 | 784 | retrieve |
| Fundamentals of Data Engineering | 544 | 291,260 | 535 | retrieve |
| Swim Smooth | 360 | 190,181 | 528 | stuff |
| lakehouses.pdf | 8 | 18,338 | 2,292 | stuff |
| **Whole corpus** | **1,525** | **980,831** | 643 | **retrieve** |

What each one is for:

- **Designing Data-Intensive Applications** — the retrieval branch, and contextualising chunks against
  a section rather than a whole document. Nearly 2.5x the threshold on its own.
- **Fundamentals of Data Engineering** — overlaps DDIA heavily. Precision under near-duplicate content,
  the hardest retrieval case in the corpus.
- **Swim Smooth** — unrelated subject matter, so it is the control in project-isolation tests. A leak
  here is obvious to the eye. Also the most interesting document for routing: at 190,181 tokens it is
  **9,819 tokens under the threshold**, roughly one chapter from crossing.
- **lakehouses.pdf** — the prompt-stuffing branch. Also the densest document by far at 2,292 tokens
  per page against 784 for DDIA, because it is a two-column paper. Page count is a poor proxy for size.

The whole corpus as one project is nearly 5x the threshold; its smallest member is a ninth of it. Both
branches of the routing decision are testable with no synthetic data.

## Wisdom (Communities)

- [r/LocalLLaMA](https://reddit.com/r/LocalLLaMA)
  The main hub for practical LLM engineering. Use for: honest reports on embedding models, chunking,
  and what fails in production.
- [Latent Space Discord](https://latent.space/)
  Applied AI engineering with a strong evaluation channel. Use for: critique of your evaluation design.
  A professional scene, not a beginner classroom.

## Gaps

- No trusted source yet on ingestion job orchestration: how to run parse, chunk, embed as a durable,
  resumable, observable background job. Needed before the upload UI is built.
- No trusted source yet on embedding-model choice with real benchmarks rather than vendor claims.
  MTEB leaderboard rankings shift often and are widely gamed. Search target for a later session.
- No comparison found yet of reranker options and their cost per query.

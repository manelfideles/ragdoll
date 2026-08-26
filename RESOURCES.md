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

- **Designing Data-Intensive Applications** — 613 pages, ~398k tokens (measured, approximate).
  Over the threshold twice over on its own.
  Use for: the retrieval branch, and contextualising chunks against a section rather than a document.
- **Fundamentals of Data Engineering** — 544 pages, ~254k tokens (measured). Overlaps DDIA heavily.
  Use for: precision under near-duplicate content, the hardest retrieval case in the corpus.
- **Swim Smooth** — 360 pages, ~158k tokens (measured). Unrelated subject matter, and the only book
  that fits under the threshold on its own.
  Use for: the control in project-isolation tests. A leak here is obvious to the eye.
- **lakehouses.pdf** — 8 pages, ~14k tokens (measured). Far under the threshold, and by far the
  densest document at ~1,790 tokens per page against ~650 for DDIA. It is a two-column paper, which
  is a warning about page counts as a proxy for size.
  Use for: the prompt-stuffing branch of the routing decision.

Total is roughly 824k tokens (approximate, pypdf extraction), so the full corpus as one project is
over the threshold four times over while its smallest member is well under. Both branches are testable
with no synthetic data. Re-measure with `make ingest` once an API key is set — these figures come from
the offline estimator and are expected to move.

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

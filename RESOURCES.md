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

- [ICD-10-CM Official Guidelines FY 2026 — CMS](https://www.cms.gov/files/document/fy-2026-icd-10-cm-coding-guidelines.pdf)
  121 pages. Dense rules, nested headings, tables, and exact identifiers such as `E11.9`. A deliberately
  hard test fixture, not a product direction. Download with:
  `curl -sSL -o corpus/icd-10-cm-guidelines-fy2026.pdf <url>`
- [ICD-10-PCS Official Guidelines 2026 — CMS](https://www.cms.gov/files/document/2026-official-icd-10-pcs-coding-guidelines.pdf)
  A second document. Use for: testing that project-scoped search does not blur two similar corpora.

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

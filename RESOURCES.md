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

Token counts below are **exact**, from the Claude API `count_tokens` endpoint against
**`claude-haiku-4-5`**, the model ragdoll uses to answer, over pypdf text extraction. Reproduce with
`make ingest-fresh`.

| Document | Pages | Chars | Tokens | Tok/page | Chars/tok | Alone |
|---|---:|---:|---:|---:|---:|---|
| Designing Data-Intensive Applications | 613 | 1,432,397 | 356,264 | 581 | 4.02 | retrieve |
| Fundamentals of Data Engineering | 544 | 915,448 | 202,989 | 373 | 4.51 | retrieve |
| Swim Smooth | 360 | 568,519 | 135,659 | 377 | 4.19 | stuff |
| lakehouses.pdf | 8 | 51,532 | 13,352 | 1,669 | 3.86 | stuff |
| **Whole corpus** | **1,525** | **2,967,896** | **708,264** | **464** | **4.19** | **retrieve** |

**These counts replace an earlier set measured against `claude-opus-5`.** Haiku 4.5 tokenizes the same
characters into **25.9% to 30.3% fewer tokens**, and 27.8% fewer over the whole corpus. Token counts are
a property of the model, not of the text. Switching answering models silently rewrites every number a
routing decision depends on, so `MODEL` in `tokens.py` must track the answering model and every cached
count must be thrown away when it changes.

The offline estimator's `_CHARS_PER_TOKEN = 3.6` **changed direction** with the model. Against Opus 5 it
ran 12.7% to 21.9% **low**, which is the dangerous direction. Against Haiku 4.5 it runs 7.2% to 25.3%
**high**, which is the safe one. The constant did not move; the model under it did.

What each document is for:

- **Designing Data-Intensive Applications** — the retrieval branch, and contextualising chunks against a
  section rather than a whole document. 1.8x the threshold on its own.
- **Fundamentals of Data Engineering** — overlaps DDIA heavily, so it is precision under near-duplicate
  content, the hardest retrieval case in the corpus. It is also now **the borderline document for
  routing, at 2,989 tokens over the threshold** — roughly a chapter from flipping route.
- **Swim Smooth** — unrelated subject matter, so it is the control in project-isolation tests. A leak is
  obvious to the eye. Under Opus 5 counts it was the borderline document at 9,819 tokens under the
  threshold; under Haiku 4.5 it sits 64,341 under and is no longer close.
- **lakehouses.pdf** — the prompt-stuffing branch. Also the densest document by far at 1,669 tokens per
  page against 581 for DDIA, because it is a two-column paper. Page count is a poor proxy for size.

The whole corpus as one project is 3.5x the threshold; its smallest member is a fifteenth of it. Both
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

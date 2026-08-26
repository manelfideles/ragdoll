# RAG Resources

Curated sources for the mission in [MISSION.md](./MISSION.md): build a document-management
platform that feeds a RAG pipeline and an embeddable chatbot for medical coders.

## Knowledge

- [Contextual Retrieval in AI Systems — Anthropic Engineering](https://www.anthropic.com/engineering/contextual-retrieval)
  The single best short primer. Gives the six-step baseline pipeline, the naive-chunking failure
  mode, and hard numbers for each improvement. Use for: pipeline shape, chunk context, reranking,
  and the 200,000-token rule for when RAG is not needed.
- [Enhancing RAG with contextual retrieval — Claude Cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
  Runnable notebook version of the post above. Use for: actual code when you build ingestion.
- [A complete guide to RAG evaluation — Evidently AI](https://www.evidentlyai.com/llm-guide/rag-evaluation)
  Clear, vendor-light treatment of golden datasets and retrieval metrics. Use for: building the
  test set, and the exact definitions of recall@k, precision@k, hit rate, NDCG@k.
- [Ragas documentation](https://docs.ragas.io/)
  The standard open-source RAG evaluation library. Use for: computing faithfulness, answer
  relevancy, context precision, context recall once a golden set exists.
- [Claude API documentation](https://platform.claude.com/docs)
  Use for: model ids, prompt caching, tool use, citations.

## Corpus (the documents the project will index)

- [ICD-10-CM Official Guidelines for Coding and Reporting, FY 2026 — CMS](https://www.cms.gov/files/document/fy-2026-icd-10-cm-coding-guidelines.pdf)
  Free, official, real. This is the project corpus. Roughly 120 pages of dense coding rules.
- [ICD-10-PCS Official Guidelines 2026 — CMS](https://www.cms.gov/files/document/2026-official-icd-10-pcs-coding-guidelines.pdf)
  Second document. Adds the multi-document problem that makes the platform necessary.
- [CDC NCHS ICD-10-CM publication archive](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/)
  Prior-year versions. Use for: the document-versioning problem, which is a real coder pain point.

## Wisdom (Communities)

- [r/LocalLLaMA](https://reddit.com/r/LocalLLaMA)
  The main hub for practical LLM engineering talk. Use for: retrieval and embedding-model debates,
  honest reports of what works in production.
- [Latent Space Discord](https://latent.space/)
  Applied AI engineering. Has a strong evaluation channel. Use for: critique of your evaluation
  design. Professional scene, not a beginner classroom.

## Gaps

- No community of medical coders found yet. This is the biggest gap: without coders, the golden
  question set is guessed, not observed. Search targets for a later session: AAPC forums, AHIMA
  communities, r/MedicalCoding.
- No trusted source yet on embeddable chat widget architecture (iframe isolation, CORS, auth).

# Retrieval fundamentals are held at recognition level

Manuel read explainer 01 and scored 6/6 on its quiz. The questions covered: defending a pipeline
against prompt stuffing, diagnosing a missed passage as a search failure rather than a model failure,
what contextual retrieval prepends, why BM25 survives next to embeddings, why reranking beats a wide
prompt, and why the golden set is built first.

**Evidence**: 6/6, first attempt, no retries. But the quiz was multiple choice, so this is recognition,
not production. Treated as a solid floor rather than mastery.

**Implications**
- Do not re-teach the pipeline shape, hybrid search, reranking or the token threshold.
- The zone of proximal development has moved from *what the parts are* to *choosing between them under
  constraints*. Teach through design decisions with trade-offs, not through definitions.
- [[GLOSSARY.md]] now holds the core pipeline terms. `recall@k` is held back until he computes one.
- Next: build the golden set against the ICD-10-CM corpus, then score a deliberately dumb pipeline.

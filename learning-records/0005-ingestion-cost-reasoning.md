# Ingestion reasoning is sound; two gaps found in cost and isolation

Manuel answered three free-recall transfer questions on explainer 01. Result: strong on the routing
decision, one 10x arithmetic error on ingest cost, and the isolation leak located in the wrong place.

**What he got right, unprompted**
- Crossing the 200k threshold leaves a project with nothing indexed, because staying under it means
  skipping chunking and embedding at ingest. This is the real production failure and he named it
  without hints.
- Contextual retrieval means one model call per chunk, and that belongs in a background job rather
  than a request. Correct instinct, and it holds for real corpora.
- Project isolation is done with a `project_id` on the document and on every chunk.

**Gap 1: order of magnitude on chunk counts.** He estimated ~50k tokens for a 121-page PDF (good, the
true figure is close) but then computed 1,000 chunks at 500 tokens each. It is 100. The conclusion
changed with it: he predicted a 30-minute upload, where the real figure is about 3 minutes sequential
and seconds with concurrency. Cost with prompt caching is roughly $0.05, not a concern at all.

**Gap 2: prompt caching was absent from the cost model.** Anthropic's $1.02 per million document tokens
depends on the document sitting in a cached prefix while each chunk call reuses it. Without caching the
same work costs about ten times more. He did not mention caching, so his cost intuition for contextual
retrieval is currently pessimistic by an order of magnitude.

**Gap 3: where isolation leaks.** He said the leak would appear when fusing the BM25 and embedding
results. That is where it becomes *visible*. It originates in whichever index's filter was forgotten,
and that is usually BM25, because it is a separate store with different filter syntax and therefore a
separate code path. He did not reach the structural defence: push isolation below the application, with
Postgres Row Level Security or a namespace per project, so that forgetting becomes impossible rather
than merely unlikely.

**Implications**
- Teach `recall@k` and the golden set next, as planned. These gaps are cost and plumbing, not retrieval
  quality, and the workspace rule in MISSION.md says score retrieval before building platform features.
- Before any ingestion code is written, cover: prompt caching in the contextualisation loop, and the
  fact that contextual retrieval as published assumes a document that fits in one prompt. A 613-page
  book must be contextualised against a section, not the whole document. This is a real limitation of
  the technique and it applies directly to the new corpus.
- Watch for order-of-magnitude slips. He reasons well and arithmetic is the weak link, so future
  exercises should ask him to state units and check magnitudes explicitly.

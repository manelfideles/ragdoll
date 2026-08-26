# Index always; anchor the golden set to the document, not the chunk

Session of 2026-08-26. Four decisions, one new gap, one correction to an earlier figure.

## Decisions

**Answering model is `claude-haiku-4-5`.** Chosen to limit spend. Consequence he identified himself:
the 200,000-token threshold was inherited from Anthropic's post, where it happened to equal the
context window of the models of the day. Haiku 4.5's window *is* 200,000 tokens, so the threshold must
be tailored to the model and must sit below the window, because the window also holds the system
prompt, the question and the answer. Swim Smooth, at 190,181 tokens, does not fit Haiku 4.5's window
on the stuff route. **Deriving the new threshold is deferred**, not dropped — see Open below.

**Index every project. Route at query time.** He proposed always indexing rather than letting the
threshold gate ingestion. This decouples two decisions the code had welded together: *do we build an
index* (ingest time, now always yes) and *do we stuff or retrieve* (query time, still the threshold).
It removes the failure he named unprompted in [[0005-ingestion-cost-reasoning]] — a project that
crosses the threshold with nothing indexed — because the index always exists. `routing.py` is unchanged
and still pure; it is called from a different place. Cost of always indexing is zero in dollars:
embeddings are local and the dumb pipeline has no per-chunk model call.

**No vector store for the baseline.** The corpus is ~980,831 tokens, so roughly 2,000 chunks at 500
tokens. Brute-force cosine similarity over 2,000 vectors is instant. A store solves a problem that does
not exist yet, and deferring it means the store decision gets made with a recall score in hand.

**Golden set ground truth is `(document, start_char, end_char)` into the extracted text.** Not chunk
IDs, and not offsets within a chunk. Chunks store the same span, and recall@k is a span-overlap test.
Reasons: chunk IDs do not exist when the golden set is built; Docling will replace `parse.py` and move
every chunk boundary; and `MISSION.md` already requires document offsets on chunks for clickable
citations, so the join is free.

**Direct API calls, not Ragas.** Ragas was chosen and then rejected within the session. Its 0.4.3
release hard-depends on `openai`, `langchain_openai` and `tiktoken` — the last of which `tokens.py`
explicitly forbids. His stated reason for rejecting it is the better one: the goal is to learn how
retrieval works, and a framework hides the generation prompt, which is the artefact he would have to
defend.

## What he got right

- Q3 of the estimator exercise: picked the lowest chars-per-token ratio, with the correct reason —
  overcounting is the safe direction, because undercounting routes a project to stuff with no index.
- Challenged whether the offline estimator should exist at all. It should not, in its current form; a
  tightened constant improves a printed report and no decision. Questioning whether a component earns
  its place is a level up from tuning it.
- Cut scope hard and repeatedly toward the measurable goal, and asked "why do we need a golden set"
  rather than accepting it. Both are the right instincts for a 2-4 hour weekly budget.

## New gap: durability of artefacts under change

Asked what `X` would be in "recall@5 rose from 0.61 to 0.84 when I changed X", he named contextual
retrieval and reranking — retrieval-stage improvements — and missed **chunking**, which is the largest
lever and the one already on his own roadmap via Docling. He then chose a ground truth anchored to
chunk IDs plus in-chunk offsets, which his own next planned change would destroy.

Both halves are the same blind spot: reasoning about the system as it is now, rather than about what
will change under it. His precision instinct was correct; the anchor was one level too low.

**How to teach against it**: when he proposes a data structure or an artefact, ask what breaks when the
layer beneath it changes. This is not an arithmetic gap and it is not a retrieval gap.

Gap 1 from [[0005-ingestion-cost-reasoning]], order-of-magnitude arithmetic, was **not tested** this
session — the exercise that would have tested it was deferred. Treat it as still open.

## Correction

The previous handoff recorded the offline estimator as low by 19.0% on the whole corpus. The correct
figure is **15.9%**, recomputed from `.ragdoll/ingest-cache.json`. The four per-document figures were
right. He was shown the correction.

## Applied at the end of the session: the model swap, and what it revealed

He asked for `MODEL` to change to `claude-haiku-4-5` and for the corpus to be re-counted. Done, and the
result is a better teaching artefact than the exercise it replaces.

**Haiku 4.5 tokenizes the same characters into 25.9% to 30.3% fewer tokens than Opus 5** — 27.8% fewer
over the whole corpus, 980,831 down to 708,264. Nobody predicted a swing that large, including me. Token
counts are a property of the model, not of the text, and a model swap silently rewrites every number a
routing decision rests on.

Two things fell out of it that are worth using next session, because both land on his new gap:

1. **The borderline document moved.** Swim Smooth was 9,819 tokens under the threshold and was the
   showpiece for "an approximate count must never decide a route". It now sits 64,341 under. The
   borderline case is now Fundamentals of Data Engineering, 2,989 tokens over.
2. **The offline estimator flipped direction.** `_CHARS_PER_TOKEN = 3.6` ran 12.7% to 21.9% low against
   Opus 5, the dangerous direction, and runs 7.2% to 25.3% high against Haiku 4.5, the safe one. The
   constant did not move. The model under it did. **His Q3 reasoning is still right and every constant
   he derived is now wrong** — the measured range is 3.86 to 4.51, not 2.81 to 3.14.

That is the same lesson as his new gap, arriving from a different direction: an artefact anchored to
something that changes beneath it does not survive. He anchored a constant to a tokenizer. Show him this
before re-running the estimator exercise.

## Open

- Derive `THRESHOLD_TOKENS` for `claude-haiku-4-5`: 200,000 minus system prompt, question, answer room,
  prompt-wrapper overhead and a quality margin. Also revisit `HYSTERESIS_TOKENS`, currently 20,000.
- Reshape the offline estimator as a two-sided bound: lower from the highest chars-per-token ratio,
  upper from the lowest. `upper < threshold` proves STUFF, `lower >= threshold` proves RETRIEVE, and
  anything else is UNDECIDED. On the corpus this gives three correct certain answers and returns
  UNDECIDED for the genuinely borderline document. **Re-derive the constants against Haiku 4.5 first:
  the range is 3.86 to 4.51.** Caveat he must set: a range measured on four English prose PDFs against
  one tokenizer is not a bound, and must be widened.
- The golden set holds verbatim extracts from copyrighted PDFs, so it is gitignored like the corpus.
  **recall@5 will therefore not be reproducible from a clone.** He needs a ready answer for that.

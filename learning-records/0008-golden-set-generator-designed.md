# The golden set generator, designed end to end

Second session of 2026-08-26, following [[0007-index-always-and-golden-set-anchoring]]. Twenty-one
decisions, no code. The session was a grilling: every branch of the design was put to him and settled
before anything was built.

## Decisions

**Ground truth is the verbatim quote, not the offset.** This reverses the anchor chosen in 0007.
That record settled on `(document, start_char, end_char)` into the extracted text, with the correct
reason that chunk IDs die when the chunker changes. But the extracted text is also an output, and
`parse.py` is scheduled to be replaced by Docling, which will rewrite every offset. The anchor was one
layer above the chunker and still below the planned change. The golden set now stores
`(document, page, quote)`, and offsets are computed at score time by searching the current extracted
text. Offsets are never stored — a stored offset is correct on the day it is written and invites a
later reader to trust it afterwards.

**The lookup is a normalised exact match.** Collapse whitespace runs, strip soft hyphens and
hyphen-plus-newline, keep case, and hold an index table back to real positions. Zero matches is a hard
failure and a real signal about the parser. More than one match goes to hand review. Fuzzy matching
was rejected: a similarity threshold is a second knob, and it can return the wrong span quietly, which
is the worst failure this artefact can have.

**The metric is hit rate@5, not recall@5.** `GLOSSARY.md` defines recall@k over *all* passages that
truly answer a question. That denominator is unknowable here: DDIA and Fundamentals of Data Engineering
overlap heavily, and he cannot hand-search 1,500 pages for alternative answers to 50 questions. So the
golden set holds one span per question, and the number measures whether the passage the question was
written from appeared in the top 5. It is a **lower bound** on true recall — the same safe direction he
chose himself for the token estimator in 0007. This makes `MISSION.md` wrong where it says "recall@5
rose from 0.61 to 0.84"; both files need editing.

**A hit is union coverage of 0.5 across the top k**, not per-chunk containment and not any overlap.
Containment punishes the chunker for a boundary inside the quote even when both halves were retrieved
and the answering model would still see the whole thing. Any-overlap rewards a chunk that brushes the
span by five characters. Union is the right unit because the answering model receives all k chunks at
once. The 0.5 is stated, not measured, and is to be documented the way `THRESHOLD_TOKENS` is.

**Fifty questions, one per page, fifty distinct pages.** Standard error at 50 is about 0.065, so the
set resolves a change of roughly 0.15 and no smaller. Two questions from one page succeed or fail
together, so they are not two measurements; one per page also puts more of the two overlapping books
into contact. Pages are stratified per document by length with a fixed seed. Only pages that extract to
zero characters are skipped — a minimum-length filter was rejected because it would drop 12% of Swim
Smooth against 4.4% of DDIA, and the hand review already catches the questions a thin page produces.

**Opus 5 writes the questions; Haiku 4.5 still answers.** Generating 50 questions costs $0.13 on Haiku,
$0.63 on Opus 5, so cost cannot decide it. The risk with a weak generator is not the bill: it writes
questions that echo the passage's rare words, BM25 finds them with no effort, and the hit rate is high
for the wrong reason. The "same model writes and answers" worry does not apply — retrieval uses
embeddings and BM25, so the answering model never sees the question at scoring time.

**Two files, and the generator never writes the reviewed one.** Generator writes
`.ragdoll/golden/candidates.jsonl`; review writes `.ragdoll/golden/golden.jsonl`. Under the accepted
risk below, a careless re-run of the generator is the most likely way the reviewed work is lost, and
two paths make that impossible by construction rather than by care.

**Review is a resumable CLI loop with four verdicts**: accept, edit-then-accept, reject as too generic,
reject as not answered by the quote. Decisions are written per keystroke because the pass sits inside a
session doing other work. Pass one is 30 items and exists to measure the accept rate and fix the
generation prompt; pass two is sized from that measured rate to land on exactly 50 accepted.

## Accepted risks, chosen with the consequence stated

**The set is not published.** Nobody can check the questions or the score.

**The set has no backup and cannot be regenerated.** It is gitignored, Opus 5 is non-deterministic, and
`temperature` is rejected on it, so the questions will never come back. `git clean -xfd` destroys the
review labour. He was offered a location outside the working tree and declined it.

## What he got right

- Accepted the metric rename to hit rate@5 without argument. Keeping the flattering label would have
  cost nothing today and made the number indefensible later.
- Cut 100 questions to 50 unprompted. Consistent with the scope discipline praised in 0007.
- Took the durability reversal on the anchor immediately, one session after choosing the old one.

## Gap check

The gap named in 0007 — reasoning about the system as it is, rather than about what will change under
it — was the subject of half this session, but it is **not demonstrated closed**. Every durability hole
was raised by the teacher and agreed by him. He did not find one himself. Two data points cut against
closure: he had chosen the offset anchor only one session earlier, and he accepted an unbackupable,
unregenerable artefact when the alternative cost twenty minutes.

He also chose to skip only empty pages, against a recommendation to filter at 500 characters. There is
a good argument for his choice — the length filter trades a saved API call for an uneven sampling bias
— but he did not state it, so it is unknown whether he saw it.

Gap 1 from [[0005-ingestion-cost-reasoning]], order-of-magnitude arithmetic, was again **not tested**.
Standard-error figures were handed to him rather than derived by him. Treat it as still open.

## Open

Carried from 0007, still open:
- Derive `THRESHOLD_TOKENS` for `claude-haiku-4-5`, and revisit `HYSTERESIS_TOKENS`.
- Reshape the offline estimator as a two-sided bound, with constants re-derived against Haiku 4.5.
- A ready answer for why the score is not reproducible from a clone.

New:
- **The next session must produce a number.** This session ships the generator and the review loop
  only, and that is not finished work. `MISSION.md` says no platform feature gets built until the
  retrieval behind it has a score, and a golden set with nothing attached is exactly the artefact that
  rule exists to prevent. Next: a fixed 500-token chunker, local embeddings, brute-force cosine over
  roughly 2,000 vectors, the scorer, and a real hit rate@5.
- Edit `GLOSSARY.md` to add **hit rate@k** as the metric actually computed, leaving recall@k in Pending.
- Edit `MISSION.md`, which currently claims a recall@5 figure it will not measure.
- The 0.5 union-coverage threshold is unmeasured. Print the coverage distribution across the 50
  questions; if every value lands near 1.0 or 0.0, the threshold never mattered and he can say so.

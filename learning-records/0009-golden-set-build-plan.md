---
artifact: plan
source: /var/folders/6y/v2t6w21d069cyw2c2ssx03bc0000gp/T/ragdoll-golden-set-handoff.md
authority: learning-records/0008-golden-set-generator-designed.md
skill: plan
created: 2026-08-27
status: approved
---

# Build plan — golden set generator and review loop

Approved by Manuel on 2026-08-27. There is no Jira ticket, so this file is the plan artefact.
The design authority stays [[0008-golden-set-generator-designed]]. This file says *how* to build
it, never *what* to build. Where the two disagree, 0008 wins.

## Conflict found during planning, and its agreed fix

The handoff says sample **50 pages, one question each**. It also says pass two must be sized from
the measured accept rate to land on **exactly 50 accepted**. Both cannot hold. At a 70% accept
rate, 50 candidates give about 35 accepted, and reaching 50 needs about 72 candidates.

Agreed fix, which reverses no decision in 0008: the stratified sample is a **seeded permutation of
every eligible page**, not a fixed list of 50. `generate` takes the first 50 from it. Pass two
extends from the same permutation. Pages stay distinct, and the seed and the stratification stay
honest.

## User story

As the ragdoll author, I want 50 hand-reviewed questions anchored to verbatim quotes, so that the
next session can compute a real hit rate@5.

## Acceptance criteria

- [ ] `ragdoll golden generate` writes `.ragdoll/golden/candidates.jsonl`; it never writes `golden.jsonl`.
- [ ] `ragdoll golden review` writes `.ragdoll/golden/golden.jsonl`; it is the only writer of that path.
- [ ] Every record holds `id`, `document`, `page` (1-indexed), `question`, `quote`, `match_count`,
      `echo_score`. No `start_char`, no `end_char`, no page text.
- [ ] File metadata holds `seed`, `model`, `prompt_version`, `parser_version`, `generated_at`.
- [ ] Sampling is stratified per document by page count, uses a fixed seed, skips only
      zero-character pages (30 of 1,525), and gives distinct pages.
- [ ] A quote with 0 normalised matches is dropped and logged loudly. More than 1 match is kept and
      marked for review.
- [ ] A question containing `this passage`, `this text`, `this chapter`, `this document`,
      `the excerpt`, or `above` is rejected automatically.
- [ ] `echo_score` is printed, never used to reject.
- [ ] Review is resumable: kill it mid-pass, restart, and it continues at the next undecided candidate.
- [ ] `golden.jsonl` ends with exactly 50 accepted questions.
- [ ] `GLOSSARY.md` defines **hit rate@k**; `MISSION.md` no longer claims a recall@5 figure.
- [ ] `make check` (ruff, ty, pytest) is green.

## Technical approach

New module `packages/pipeline/src/ragdoll/golden.py`, plus a `golden` sub-app in `cli.py` beside
`ingest` and `route`. The module opens with a docstring that says why it exists and what it
refuses to do, like `parse.py` and `tokens.py`.

Four parts inside `golden.py`:

1. **`normalise(text)`** — collapses whitespace runs to one space, strips soft hyphens and
   hyphen-plus-newline, keeps case. Returns the normalised string and an index table back to real
   positions. Offsets go to the caller and are never written to disk.
2. **`sample_pages(...)`** — seeded, stratified permutation of eligible pages.
3. **`generate(...)`** — one Opus 5 call per page, with the sampled page plus one page each side,
   clamped at document ends. Asks for a standalone question and the exact sentences used. The
   quote must **start** inside the sampled page.
4. **`review(...)`** — the keystroke loop, four verdicts, one disk write per keystroke.

One change outside the module: `parse.py` keeps the per-page texts. Today `parse_pdf` joins pages
with `\n\n` and throws the list away. Add `parse_pages(path) -> list[str]` and make `parse_pdf`
call it. The cache and `ingest` are untouched.

Two definitions the design left open. State them in code the way `THRESHOLD_TOKENS` is stated:

- **Uncommon word**, for `echo_score`: a question word of 4 or more characters that is not in a
  small stopword list. The comparison is case-insensitive; the stored quote is never casefolded.
- **`parser_version`**: a hand-bumped string constant, starting at `pypdf-1`.

Load the `claude-api` skill before writing the Opus 5 call. `temperature` and `budget_tokens` are
both rejected on Opus 5, and a stale request shape fails with a 400.

## Tracer-bullet slices

| # | Slice | Mode | Modules touched | Demoable as |
|---|-------|------|-----------------|-------------|
| S1 | Page-level parse and seeded stratified sample | AFK | `parse.py`, `golden.py`, `cli.py`, `tests/test_golden_sample.py` | `ragdoll golden generate --dry-run` prints 50 distinct `(document, page)` rows; the same seed prints the same rows twice; no API call |
| S2 | Normalised quote lookup with index table | AFK | `golden.py`, `tests/test_golden_lookup.py` | Green tests: soft hyphen, hyphen-newline, whitespace run, 0 matches, 2 matches, case kept |
| S3 | One real Opus 5 call, one candidate on disk | HITL | `golden.py`, `cli.py` | `ragdoll golden generate --limit 1` appends one valid record to `candidates.jsonl` |
| S4 | Filters, echo score, full 50-page run | AFK | `golden.py`, `tests/test_golden_filters.py` | `candidates.jsonl` holds about 50 records; rejects and 0-match drops are logged; the echo score distribution is printed |
| S5 | Resumable review loop, pass one of 30 | HITL | `golden.py`, `cli.py`, `tests/test_golden_review.py` | Kill it mid-pass, restart, it resumes; `golden.jsonl` grows; the accept rate is reported |
| S6 | Prompt fix, sample extension, pass two to 50 accepted | HITL | `golden.py` (prompt version bump) | `golden.jsonl` holds exactly 50 accepted records |
| S7 | Documentation correction | AFK | `GLOSSARY.md`, `MISSION.md` | `hit rate@k` is defined; recall@k stays in Pending; the MISSION claim is removed |

S3, S5 and S6 need Manuel at the keyboard. S1, S2, S4 and S7 do not.

## Out of scope

Chunker, embeddings, vector store, retriever, scorer, hit-rate computation, Docling, any UI.
Publishing or backing up the golden set. A threshold for `echo_score`.

## Test plan

- **Unit**: normalisation and lookup against synthetic text; stratification proportions; seed
  stability; the reject-phrase list; `echo_score` arithmetic; resume against a part-written
  decisions file.
- **Integration**: `--dry-run` end to end over the real corpus; `--limit 1` against the real API,
  run by hand once.
- **Manual**: read the first three generated questions before the full run proceeds.

No test may commit corpus text. Fixtures are invented strings.

## Accepted risks, not to be re-raised

N=50 resolves a change of about 0.15 and no smaller. The set is unpublished, has no backup, and
cannot be regenerated. `git clean -xfd` destroys the review labour. Each consequence was stated
and chosen.

## What comes after

This plan is not finished work. The next session must ship a fixed 500-token chunker, local
embeddings, brute-force cosine, the scorer, and a real hit rate@5.

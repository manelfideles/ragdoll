---
artifact: impl-progress
ticket: golden-set
plan: learning-records/0009-golden-set-build-plan.md
skill: implement
status: in_progress
created: 2026-08-27
---

| Slice | Description                                          | Mode | Status      | Completed |
|-------|------------------------------------------------------|------|-------------|-----------|
| S1    | Page-level parse and seeded stratified sample         | AFK  | complete    | 2026-08-27 |
| S2    | Normalised quote lookup with index table              | AFK  | complete    | 2026-08-27 |
| S3    | One real Opus 5 call, one candidate on disk           | HITL | complete    | 2026-08-27 |
| S4    | Filters, echo score, full 50-page run                 | AFK  | complete    | 2026-08-27 |
| S5    | Resumable review loop, pass one of 30                 | HITL | in_progress | —         |
| S6    | Prompt fix, sample extension, pass two to 50 accepted | HITL | pending     | —         |
| S7    | Documentation correction                              | AFK  | pending     | —         |

## Carried findings — decisions still open

- **Curly punctuation loses about 10% of candidates.** In the S4 run, 5 of 50 pages were
  dropped for "quote not on the page". The parser was innocent: the page reads
  `We’ll discuss transactions`, and Opus 5 mangled the curly apostrophe while copying
  (`We\ni\nll`). Same shape as the hyphen decision settled in S2. Options: fold curly
  quotes and dashes to ASCII in a third exact pass; or tell the prompt to copy the
  punctuation byte for byte; or accept the 10% loss and size pass two around it.
  **Owner: Manuel. Decide during S6, where the prompt fix and sample extension already live.**

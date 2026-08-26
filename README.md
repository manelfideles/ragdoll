# ragdoll

[![CI](https://github.com/manelfideles/ragdoll/actions/workflows/ci.yml/badge.svg)](https://github.com/manelfideles/ragdoll/actions/workflows/ci.yml)

A platform for creating RAG pipelines. Create a project, add documents, ask questions about them.

Everything runs on your machine: parsing, chunking, indexing, storage. The one exception is token
counting, which asks the Claude API, because only the model's own tokenizer gives a number worth
making a decision on.

## Why this exists

Anthropic's guidance is that a knowledge base under 200,000 tokens should simply go in the prompt,
served with prompt caching. A retrieval pipeline cannot fetch the wrong passage if there is no
retrieval. Most RAG projects ignore this and retrieve unconditionally.

Ragdoll does not know in advance how large a project will be. One user adds a memo; another adds four
hundred contracts. So the threshold is a **runtime decision per project**, not a one-time judgement:
measure the project, stuff the prompt below the threshold, retrieve above it.

## Quick start

```sh
cp .env.example .env  # then add your key
make install          # sync the virtualenv from the lockfile
make ingest           # parse the corpus, count tokens, print the routing decision
make ci               # exactly what CI runs: ruff, ruff format --check, ty, pytest
make help             # every target
```

`make ingest` needs `ANTHROPIC_API_KEY` for exact token counts, read from `.env` or the shell — an
exported value wins over the file. Without a key you get approximate counts, clearly labelled, and the
route it prints is a guess. `make ingest-offline` skips the API deliberately.

`.env` is gitignored and no value read from it is ever printed. Copy `.env.example` to start.

## CI

One job, `quality`, on every pull request and on pushes to `main`: `ruff check`, `ruff format --check`,
`ty check`, `pytest`. It runs with **no API key**, so the suite must pass with no credentials — that
keeps it fast, free, and safe on a fork's pull request. `make ci` runs the same four commands locally.

## Layout

```
packages/pipeline/          python — ingestion, retrieval, evaluation
  src/ragdoll/
    routing.py              the threshold decision. pure, no IO
    parse.py                pdf → text (pypdf; to be replaced by a layout-aware parser)
    tokens.py               exact counts via the API, approximate offline
    cache.py                on-disk cache keyed by size and mtime
    config.py               .env loading; shell beats file, values never logged
    cli.py                  the `ragdoll` command
  tests/
corpus/                     local documents, gitignored
.github/workflows/ci.yml    the `quality` job
```

## Status

Stage one of ingestion only: parse, count, route. No chunking and no indexing yet, on purpose —
neither can be scored until a golden set exists to score them against.

Next: generate a golden set, then measure recall@5 on the dumbest possible pipeline.

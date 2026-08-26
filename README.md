# ragdoll

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
make install          # sync the virtualenv from the lockfile
make ingest           # parse the corpus, count tokens, print the routing decision
make check            # ruff, ty, pytest
make help             # every target
```

`make ingest` needs `ANTHROPIC_API_KEY` for exact token counts. Without it you get approximate counts,
clearly labelled, and the route it prints is a guess. `make ingest-offline` skips the API deliberately.

## Layout

```
packages/pipeline/          python — ingestion, retrieval, evaluation
  src/ragdoll/
    routing.py              the threshold decision. pure, no IO
    parse.py                pdf → text (pypdf; to be replaced by a layout-aware parser)
    tokens.py               exact counts via the API, approximate offline
    cache.py                on-disk cache keyed by size and mtime
    cli.py                  the `ragdoll` command
  tests/
corpus/                     local documents, gitignored
```

## Status

Stage one of ingestion only: parse, count, route. No chunking and no indexing yet, on purpose —
neither can be scored until a golden set exists to score them against.

Next: generate a golden set, then measure recall@5 on the dumbest possible pipeline.

# Mission pivot: from a medical coding chatbot to `ragdoll`, a RAG platform

Supersedes the framing in [[0002-rag-must-be-justified]].

The project is now domain-agnostic. A user creates a project, uploads documents through a UI, and
searches that project's documents. The medical coding corpus drops from product domain to test
fixture. Repository: `github.com/manelfideles/ragdoll`.

This changes what the 200,000-token threshold means. For a single fixed corpus the threshold is a
one-time judgement call. For a platform it is a **runtime decision per project**: measure the project's
token count, stuff the prompt below the threshold, retrieve above it. That routing decision is now the
most distinctive thing ragdoll can have, and almost no side-project implements it.

The pivot also adds two platform concerns that are not retrieval concerns: project isolation in the
vector store, and durable observable ingestion jobs.

**Implications**
- Golden sets must be generated from documents rather than written by a domain expert, because ragdoll
  has no expert. Ragas testset generation becomes a required tool, not an optional one.
- Scope risk is now the main threat to the mission. At 2-4 hours per week, platform plumbing can eat
  every session. The workspace rule is recorded in MISSION.md: no platform feature is built until the
  retrieval behind it has a score.
- Next session target is unchanged by the pivot: build the golden set and score the dumbest possible
  pipeline. The pivot changes what ragdoll is, not what must be measured first.

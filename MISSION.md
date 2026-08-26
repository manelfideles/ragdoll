# Mission: RAG — building `ragdoll`

## Why
Manuel wants a public, finished side-project that proves he can build production-grade RAG, and he
wants to genuinely understand retrieval instead of copying a tutorial.

The project is **ragdoll**: a platform for creating RAG pipelines. A user creates a project, uploads
documents to it through a UI, and then asks questions about those documents. Ragdoll owns the whole
path from uploaded file to cited answer, so the user never writes retrieval code.

## Success looks like
- A deployed web app. Sign in, create a project, drop in files.
- Ingestion is visible. You can watch a document move through parse, chunk, embed, index, and you
  can see where it failed.
- Search works over one project's documents only. No leakage between projects.
- Every answer shows its sources. Click a citation, land on the exact passage.
- A numeric retrieval score. You can say "recall@5 rose from 0.61 to 0.84 when I changed X."
- You can explain, without notes, why each design choice was made, and what you rejected.

## Constraints
- 2-4 hours per week. Sessions must be short and must resume from written state.
- Solo build. Prefer managed services over self-hosted infrastructure. Free tiers first.
- Ragdoll is domain-agnostic, so there is no expert to write the golden set. The evaluation set must
  be generated from the documents themselves and reviewed by hand.
- Test corpus: four PDFs Manuel already owns, in `corpus/` (gitignored, not redistributable).
  Designing Data-Intensive Applications (613 pages), Fundamentals of Data Engineering (544),
  Swim Smooth (360), lakehouses.pdf (8). Roughly 610k tokens in total.
  This corpus is deliberately awkward, which is why it is a good fixture:
  - `lakehouses.pdf` alone sits far **under** the 200k threshold. Any single book sits **over** it.
    So both branches of the routing decision are testable without inventing data.
  - Two of the books overlap heavily in subject, which is the hard case for retrieval precision.
  - Swim Smooth is unrelated to the others, so it is the control for project isolation.
  - Books have deep section trees, so contextual retrieval must work against a section rather than a
    whole document. Layout-aware parsing is therefore not optional.

## Out of scope
- Training or fine-tuning models.
- Agents, tool use, multi-step reasoning. Ragdoll retrieves and answers. Nothing more.
- Real clinical or regulated use. The medical corpus is a test fixture, not a product direction.
- HIPAA compliance, patient data, SSO, billing, enterprise multi-tenancy.
- Chat memory and multi-turn conversation, until single-turn retrieval is measurably good.

## The honest risk
Ragdoll is a platform, so it is a much larger build than a single pipeline. At 2-4 hours per week the
danger is spending every session on upload screens and job queues and never touching retrieval —
which is the part being learned, and the part a reviewer would actually probe. The rule for this
workspace: **no platform feature gets built until the retrieval behind it has a score.**

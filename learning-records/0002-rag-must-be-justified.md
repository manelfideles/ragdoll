# RAG needs justification against the prompt-stuffing baseline

The project corpus, the ICD-10-CM Official Guidelines FY 2026, is 121 pages. Anthropic's guidance is
that a knowledge base under 200,000 tokens (about 500 pages) should simply go in the prompt, with
prompt caching. So the naive version of this project does not need RAG at all.

The three things that do justify the pipeline, and which are now the project's stated reason to exist:
many documents, version filtering by date of service, and clickable citations.

**Implications**: the mission is scoped around multiple documents and versioning, not a single PDF.
Any future session that proposes a retrieval improvement must compare against the prompt-stuffing
baseline. Status: superseded by LR-0003, which reframes this for a platform.

# Mission: RAG (Retrieval-Augmented Generation)

## Why
Manuel wants a public, finished side-project that proves he can build production-grade RAG,
and he wants to actually understand retrieval instead of copying a tutorial. The project is a
document-management platform for a RAG pipeline that feeds an embeddable chatbot. Medical coders
ask the chatbot questions about medical coding practice.

## Success looks like
- A deployed platform. You upload a document, it is chunked, embedded and searchable.
- An embeddable chat widget. One `<script>` tag puts it on any page.
- Every answer shows its sources. The user can click through to the exact passage.
- A numeric quality score for retrieval. You can say "recall@5 went from 0.61 to 0.84 when I changed X."
- You can explain, without notes, why each design choice was made.

## Constraints
- 2-4 hours per week. Sessions must be short and must resume from written state.
- No access to private medical coding documents and no access to working medical coders.
  We use public documents: the ICD-10-CM Official Guidelines for Coding and Reporting (free from CDC/CMS).
- Solo build. Prefer managed services over self-hosted infrastructure.
- Small budget. Free tiers first.

## Out of scope
- Training or fine-tuning models.
- Real clinical use. This is a demonstration, not a certified coding tool.
- HIPAA compliance work. Public guideline documents only, no patient data ever.
- Multi-tenant billing, SSO, enterprise features.

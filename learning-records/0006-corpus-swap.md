# Test corpus swapped to four owned PDFs

Manuel replaced the ICD-10-CM fixture with four PDFs he owns: Designing Data-Intensive Applications
(613 pages), Fundamentals of Data Engineering (544), Swim Smooth (360), lakehouses.pdf (8).

Better fixture than the original. `lakehouses.pdf` is far under the 200k threshold and any single book
is over it, so both branches of the routing decision are testable with real data. The two data
engineering books overlap heavily, which stresses retrieval precision. Swim Smooth is the isolation
control. Deep section trees force layout-aware parsing.

**Implications**: the corpus is copyrighted and gitignored, so exercises must regenerate derived
artefacts from local files and never commit chunks or extracted text. Supersedes the corpus sections of
[[MISSION.md]] and [[RESOURCES.md]].

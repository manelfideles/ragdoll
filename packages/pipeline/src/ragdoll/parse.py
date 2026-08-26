"""Turn a PDF into text. Local, no network.

This is deliberately the dumbest parser that works: pypdf, page by page. It loses
the section tree, and the section tree is exactly what contextual retrieval needs
later, so this module is expected to be replaced by a layout-aware parser such as
Docling. It is here so that the first measurement can happen tonight.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    path: Path
    pages: int
    text: str

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def chars(self) -> int:
        return len(self.text)


def parse_pdf(path: Path) -> ParsedDocument:
    """Extract plain text from a PDF, one page at a time.

    Pages that yield nothing are kept as empty strings rather than dropped, so the
    page count stays honest. A page that extracts to nothing is usually a scan, and
    a corpus full of them means you need OCR, not a better chunker.
    """
    reader = PdfReader(path)
    pages = [(page.extract_text() or "") for page in reader.pages]
    return ParsedDocument(path=path, pages=len(pages), text="\n\n".join(pages))


def find_pdfs(directory: Path) -> list[Path]:
    """Every PDF directly inside ``directory``, sorted for stable output."""
    return sorted(p for p in directory.glob("*.pdf") if p.is_file())

"""Building the golden set: 50 hand-reviewed questions anchored to verbatim quotes.

The golden set is the only thing in this repository that cannot be rebuilt. Opus 5
is non-deterministic and the review labour is human, so a lost ``golden.jsonl`` is
lost for good. Two rules follow from that, and this module exists to enforce them:

* ``generate`` writes only ``candidates.jsonl``. It never opens ``golden.jsonl``.
* ``review`` writes only ``golden.jsonl``, one line per keystroke, so a killed pass
  loses at most the item on screen.

Ground truth is ``(document, page, quote)`` — never a character offset. An offset is
correct on the day it is written and invites a later reader to trust it after the
parser has moved underneath it. Offsets are computed at score time by searching the
extracted text as it is then.

This module refuses to guess. A quote that does not appear in its page is dropped
loudly rather than fuzzy-matched, because a similarity threshold can return the
wrong span quietly, and a quietly wrong golden set is worse than no golden set.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ragdoll.parse import find_pdfs, parse_pages

# The seed is the date the design was settled. Any fixed value would do; what matters
# is that it is written down here rather than passed in from a shell history.
DEFAULT_SEED = 20260827

# Fifty questions give a standard error of about 0.065, so the set resolves a change
# of roughly 0.15 and no smaller. Stated here, not measured. See learning record 0008.
TARGET_ACCEPTED = 50

# Bumped by hand whenever the parser changes shape. A quote is only reproducible
# against the parser that produced the page it was read from.
PARSER_VERSION = "pypdf-1"

GOLDEN_DIR = Path(".ragdoll/golden")
CANDIDATES_FILENAME = "candidates.jsonl"
GOLDEN_FILENAME = "golden.jsonl"


@dataclass(frozen=True, slots=True)
class PageRef:
    """One sampled page. ``page`` is 1-indexed, as a reader would cite it."""

    document: str
    page: int


def eligible_pages(pages: Sequence[str]) -> list[int]:
    """The 1-indexed pages worth sampling: every page that extracted any character.

    Only empty pages are skipped. A minimum-length filter was rejected: it would
    drop 12% of one book against 4.4% of another, which biases the sample by
    document, and the hand review already catches the thin questions a short page
    produces.
    """
    return [number for number, text in enumerate(pages, start=1) if text.strip()]


def sample_pages(eligible: Mapping[str, Sequence[int]], seed: int = DEFAULT_SEED) -> list[PageRef]:
    """A seeded, stratified permutation of *every* eligible page in the corpus.

    This returns an order, not a fixed list of 50. ``generate`` takes the first 50;
    a second pass takes the next n from the same order. A fixed list of 50 could not
    be extended without either repeating a page or breaking the stratification.

    Stratification is by document, allocated in proportion to eligible page count.
    Each document's pages are shuffled with their own seeded generator, then placed
    on a shared 0-to-1 line by their rank within the document. Sorting by that
    position interleaves the documents, so *any* prefix of the result is
    proportional to the documents' sizes — which is what makes the extension honest.
    """
    placed: list[tuple[float, str, int]] = []
    for document in sorted(eligible):
        pages = list(eligible[document])
        if not pages:
            continue
        rng = random.Random(f"{seed}:{document}")
        rng.shuffle(pages)
        span = len(pages)
        for rank, page in enumerate(pages):
            placed.append(((rank + 0.5) / span, document, page))

    placed.sort()
    return [PageRef(document=document, page=page) for _, document, page in placed]


def collect_pages(directory: Path) -> dict[str, list[str]]:
    """Parse every PDF in ``directory`` into per-page text, keyed by file name."""
    return {pdf.name: parse_pages(pdf) for pdf in find_pdfs(directory)}

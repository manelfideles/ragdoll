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

SOFT_HYPHEN = "\u00ad"

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


@dataclass(frozen=True, slots=True)
class Normalised:
    """A normalised string, with an index table back into its source.

    ``origins[i]`` is the position in the source string that produced
    ``text[i]``. The table is what makes normalisation safe: it lets a match found
    in the tidy text be reported against the real text, so nothing downstream has
    to re-derive a position by guessing at the transformation.
    """

    text: str
    origins: tuple[int, ...]

    def span(self, start: int, end: int) -> tuple[int, int]:
        """Map a half-open span of ``text`` back to a half-open span of the source."""
        if not 0 <= start < end <= len(self.text):
            raise ValueError(f"span {start}:{end} is outside the normalised text")
        return self.origins[start], self.origins[end - 1] + 1


@dataclass(frozen=True, slots=True)
class QuoteLookup:
    """Where a quote sits in a page, and how many times it sits there.

    ``match_count`` of 0 is a hard failure: the model quoted something the parser
    did not produce, which is a real signal about either the model or the parser.
    A count above 1 is kept and marked for review, because the page really does say
    the same thing twice and a human should decide which reading was meant.
    """

    match_count: int
    spans: tuple[tuple[int, int], ...]
    dehyphenated: bool = False
    """True when the match needed the hyphen-stripped second pass. Worth logging: it
    means the model rewrote the page's line break instead of copying it."""

    @property
    def found(self) -> bool:
        return self.match_count > 0

    @property
    def ambiguous(self) -> bool:
        return self.match_count > 1


def normalise(text: str, *, drop_hyphens: bool = False) -> Normalised:
    """Tidy a string for exact matching, keeping a way back to the original.

    Three transformations, and no more. Each one repairs damage that PDF extraction
    does to a sentence a reader would call unchanged:

    * a run of whitespace becomes one space, because line wrapping is not content;
    * a soft hyphen disappears, because it marks a break that was never a character;
    * a hyphen before a line break disappears with the break, because the word was
      split by the column width, not by the author.

    Case is kept. Casefolding would make ``Kafka`` and ``kafka`` the same span, and
    the stored quote must read back exactly as the page reads.

    ``drop_hyphens`` removes every hyphen instead of only the ones a line break
    justifies. It exists for the second pass in :func:`find_quote` and nowhere else.
    """
    out: list[str] = []
    origins: list[int] = []
    index = 0
    length = len(text)

    while index < length:
        char = text[index]

        if char == SOFT_HYPHEN:
            index += 1
            continue

        if char == "-":
            # The line-break rule runs first even when every hyphen is going to be
            # dropped, because it also swallows the break. Dropping the hyphen alone
            # would leave the newline behind as a space and split the word again.
            after = index + 1
            while after < length and text[after].isspace():
                after += 1
            crossed = text[index + 1 : after]
            if crossed and ("\n" in crossed or "\r" in crossed):
                index = after
                continue
            if drop_hyphens:
                index += 1
                continue

        if char.isspace():
            after = index
            while after < length and text[after].isspace():
                after += 1
            if out:  # leading whitespace produces nothing at all
                out.append(" ")
                origins.append(index)
            index = after
            continue

        out.append(char)
        origins.append(index)
        index += 1

    while out and out[-1] == " ":  # trailing whitespace produces nothing either
        out.pop()
        origins.pop()

    return Normalised(text="".join(out), origins=tuple(origins))


def find_quote(page: str, quote: str) -> QuoteLookup:
    """Locate ``quote`` inside ``page`` by normalised exact match.

    Two passes, both exact. The first matches the tidied page against the tidied
    quote. The second removes every hyphen from both sides, and runs only if the
    first found nothing: a model asked to copy a line-wrapped word usually repairs
    the break, and that repair is not a reason to throw a good question away.

    The second pass is still an exact string match, not a fuzzy one. There is no
    threshold to tune, and the span returned is always a span of the raw page.
    Merging ``co-operate`` with ``cooperate`` is the whole cost, and it changes
    which strings compare equal, never which text is reported.

    Overlapping matches are counted separately. Zero matches is reported as zero,
    never repaired.
    """
    for drop_hyphens in (False, True):
        needle = normalise(quote, drop_hyphens=drop_hyphens)
        if not needle.text:
            return QuoteLookup(match_count=0, spans=())

        haystack = normalise(page, drop_hyphens=drop_hyphens)
        spans: list[tuple[int, int]] = []
        at = haystack.text.find(needle.text)
        while at != -1:
            spans.append(haystack.span(at, at + len(needle.text)))
            at = haystack.text.find(needle.text, at + 1)

        if spans:
            return QuoteLookup(
                match_count=len(spans), spans=tuple(spans), dehyphenated=drop_hyphens
            )

    return QuoteLookup(match_count=0, spans=())

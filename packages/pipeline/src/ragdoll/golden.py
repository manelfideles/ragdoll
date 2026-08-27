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

import hashlib
import json
import random
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from anthropic import Anthropic
from pydantic import BaseModel

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


GENERATOR_MODEL = "claude-opus-5"
"""The model that writes the questions.

Not a cost dial. A weaker generator writes questions that echo the passage's rare
words, BM25 finds them with no effort, and the hit rate comes out high for the wrong
reason. The model that *answers* at scoring time is a separate choice, and retrieval
never sees this model's output, so there is no write-and-mark conflict.
"""

PROMPT_VERSION = "v1"
"""Bumped by hand whenever the prompt below changes. Questions written under two
different prompts are not the same instrument, and the file has to say which one ran."""

_MAX_TOKENS = 4000

REJECT_PHRASES = (
    "this passage",
    "this text",
    "this chapter",
    "this document",
    "the excerpt",
    "above",
)
"""Phrases that prove a question cannot stand alone.

A question containing one of these was written for a reader who is already looking at
the page. At scoring time there is no page, only a search box, so such a question
measures nothing. These are rejected automatically, before the quote is even checked:
it is the one judgement a machine can make as well as a human.
"""

_REJECT_PATTERNS = tuple(
    (phrase, re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)) for phrase in REJECT_PHRASES
)

_STOPWORDS = frozenset(
    [
        "about",
        "above",
        "after",
        "also",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "cannot",
        "could",
        "does",
        "doing",
        "during",
        "each",
        "from",
        "have",
        "here",
        "into",
        "itself",
        "just",
        "like",
        "made",
        "make",
        "many",
        "more",
        "most",
        "much",
        "must",
        "only",
        "other",
        "over",
        "same",
        "should",
        "since",
        "some",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "until",
        "very",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "within",
        "without",
        "would",
        "your",
    ]
)
"""A deliberately small list. ``echo_score`` is printed, never used to reject, so a
missing word costs nothing but a slightly noisier number."""

_GENERATION_SYSTEM = """\
You write questions for testing a retrieval system. A question is used to search a \
library of technical books; the search is judged on whether it returns the passage the \
question was written from.

You are given three pages of one book. Only the page marked TARGET PAGE may be used.

Write one question and quote the sentences that answer it.

The question must:
- be answerable from the target page alone;
- stand on its own, as if typed by a reader who has never seen the page. Never refer to \
"this passage", "this text", "this chapter", "this document", "the excerpt", or anything \
"above";
- name the subject in full, because a search engine sees no context;
- use ordinary phrasing, not the page's distinctive wording. If the page says \
"quorum acknowledgement", ask about waiting for confirmation from several nodes.

The quote must:
- be copied from the target page character for character, including its line breaks and \
any hyphen that splits a word across lines. Do not tidy it, join it, or shorten it with \
an ellipsis;
- start on the target page;
- be the sentences a reader needs to answer the question, and no more.\
"""


@dataclass(frozen=True, slots=True)
class Candidate:
    """One generated question, ready to be reviewed by hand.

    These are exactly the fields written to disk. No character offsets: they would be
    wrong the day the parser changes. No page text: the corpus is copyrighted and this
    file is not the place to copy it.
    """

    id: str
    document: str
    page: int
    question: str
    quote: str
    match_count: int
    echo_score: float

    def as_record(self) -> dict[str, object]:
        return {
            "id": self.id,
            "document": self.document,
            "page": self.page,
            "question": self.question,
            "quote": self.quote,
            "match_count": self.match_count,
            "echo_score": self.echo_score,
        }


def candidate_id(document: str, page: int) -> str:
    """A short, stable id for one page of one document.

    Derived from the name and the page rather than a counter, so re-running a page
    produces the same id and a duplicate is visible instead of silently doubling.
    """
    digest = hashlib.sha1(document.encode("utf-8")).hexdigest()[:8]
    return f"{digest}-p{page:04d}"


def uncommon_words(text: str) -> set[str]:
    """Words worth noticing when asking whether a question echoes its source.

    A word counts when it is 4 characters or longer and is not a stopword. Compared
    case-insensitively; nothing here ever touches the stored text.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if len(word) >= 4 and word not in _STOPWORDS}


def echo_score(question: str, quote: str) -> float:
    """The share of a question's uncommon words that also appear in its quote.

    High means the question lifted the passage's vocabulary, and any keyword search
    will find it with no understanding at all. This number is *printed and never used
    to reject*: a real reader's question about a named concept must contain that
    concept's name, so a threshold would throw away the good with the lazy.
    """
    asked = uncommon_words(question)
    if not asked:
        return 0.0
    return len(asked & uncommon_words(quote)) / len(asked)


def generic_reference(question: str) -> str | None:
    """The phrase that makes a question depend on its page, or None if it stands alone.

    Matched on word boundaries, so ``aboveground`` is not the word ``above``.
    """
    for phrase, pattern in _REJECT_PATTERNS:
        if pattern.search(question):
            return phrase
    return None


def page_window(pages: Sequence[str], page: int) -> str:
    """The sampled page with one page either side, clamped at the document ends.

    The neighbours are there so that a sentence continuing across a page break can
    still be understood; they are labelled so the model knows it may not quote them.
    """
    first = max(1, page - 1)
    last = min(len(pages), page + 1)
    parts = []
    for number in range(first, last + 1):
        label = "TARGET PAGE" if number == page else "CONTEXT PAGE"
        parts.append(f"--- {label} {number} ---\n{pages[number - 1]}")
    return "\n\n".join(parts)


class Generated(BaseModel):
    """What the model is asked to return. Validated by the SDK, not by us."""

    question: str
    quote: str


def ask_for_question(client: Anthropic, document: str, page: int, window: str) -> Generated | None:
    """One call to the generator. Returns None when the model declined to answer.

    A refusal is reported and dropped rather than retried. On textbook prose it should
    never happen, and if it does, the honest response is to look at the page.
    """
    response = client.messages.parse(
        model=GENERATOR_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_GENERATION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Book: {document}\nTarget page: {page}\n\n{window}",
            }
        ],
        output_format=Generated,
    )
    if response.stop_reason == "refusal":
        return None
    return response.parsed_output


def file_metadata(seed: int) -> dict[str, object]:
    """The header line of a candidates file: everything needed to read it later.

    Without the prompt and parser versions, two files written a week apart look
    identical and are not comparable.
    """
    return {
        "seed": seed,
        "model": GENERATOR_MODEL,
        "prompt_version": PROMPT_VERSION,
        "parser_version": PARSER_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def append_record(path: Path, record: Mapping[str, object]) -> None:
    """Append one JSON object as one line, flushed before returning.

    One line per write, and never a rewrite of the file, so a process killed halfway
    costs the record in flight and nothing already on disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def read_records(path: Path) -> list[dict[str, object]]:
    """Every record in a jsonl file, skipping the metadata header lines."""
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if "id" in record:
            records.append(record)
    return records


@dataclass(frozen=True, slots=True)
class Outcome:
    """What happened for one sampled page. A drop is data, not an exception."""

    ref: PageRef
    candidate: Candidate | None = None
    reason: str | None = None
    detail: str | None = None
    dehyphenated: bool = False

    @property
    def kept(self) -> bool:
        return self.candidate is not None


def candidates_path(root: Path | None = None) -> Path:
    """Where generated candidates go. The generator writes here and nowhere else."""
    return (root or Path.cwd()) / GOLDEN_DIR / CANDIDATES_FILENAME


def golden_path(root: Path | None = None) -> Path:
    """Where reviewed questions go. Only :func:`review` may write here."""
    return (root or Path.cwd()) / GOLDEN_DIR / GOLDEN_FILENAME


def generate(
    client: Anthropic,
    pages_by_document: Mapping[str, Sequence[str]],
    refs: Sequence[PageRef],
    *,
    seed: int = DEFAULT_SEED,
    path: Path | None = None,
) -> Iterator[Outcome]:
    """Write one question per sampled page, dropping the ones that cannot be trusted.

    Yields an outcome per page as it goes, so a caller can report progress and a
    long run can be watched. Each kept candidate is on disk before it is yielded.

    A page is dropped when the model declines, or when its quote cannot be found on
    the page it claims. Neither is repaired. The drop is the finding.
    """
    target = path or candidates_path()
    if not target.exists():
        append_record(target, file_metadata(seed))

    seen = {str(record["id"]) for record in read_records(target)}

    for ref in refs:
        identifier = candidate_id(ref.document, ref.page)
        if identifier in seen:
            yield Outcome(ref=ref, reason="already generated")
            continue

        pages = pages_by_document[ref.document]
        generated = ask_for_question(client, ref.document, ref.page, page_window(pages, ref.page))
        if generated is None:
            yield Outcome(ref=ref, reason="model refused")
            continue

        phrase = generic_reference(generated.question)
        if phrase is not None:
            yield Outcome(
                ref=ref, reason=f"question says {phrase!r}", detail=generated.question.strip()
            )
            continue

        lookup = find_quote(pages[ref.page - 1], generated.quote)
        if not lookup.found:
            # Loud on purpose. Either the model invented a sentence or the parser
            # produced text no reader would recognise, and both are worth seeing.
            yield Outcome(ref=ref, reason="quote not on the page", detail=generated.quote.strip())
            continue

        candidate = Candidate(
            id=identifier,
            document=ref.document,
            page=ref.page,
            question=generated.question.strip(),
            quote=generated.quote,
            match_count=lookup.match_count,
            echo_score=round(echo_score(generated.question, generated.quote), 3),
        )
        append_record(target, candidate.as_record())
        seen.add(identifier)
        yield Outcome(ref=ref, candidate=candidate, dehyphenated=lookup.dehyphenated)

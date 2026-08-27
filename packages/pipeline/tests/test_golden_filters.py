"""The automatic rejections, the echo score, and the append-only record file.

Every fixture is invented. Nothing here calls the API: the one place a model would be
asked for a question is replaced with a stub.
"""

from __future__ import annotations

import json

import pytest

from ragdoll import golden
from ragdoll.golden import (
    Candidate,
    Generated,
    PageRef,
    append_record,
    candidate_id,
    echo_score,
    generic_reference,
    page_window,
    read_records,
    uncommon_words,
)


@pytest.mark.parametrize(
    "phrase",
    ["this passage", "this text", "this chapter", "this document", "the excerpt", "above"],
)
def test_every_reject_phrase_is_caught(phrase):
    assert generic_reference(f"What does {phrase} say about locking?") == phrase


def test_the_match_ignores_case():
    assert generic_reference("What does This Passage claim?") == "this passage"


def test_a_standalone_question_passes():
    assert generic_reference("Why do database triggers make change capture fragile?") is None


def test_above_is_matched_as_a_word_not_a_prefix():
    assert generic_reference("How are aboveground cables rated?") is None
    assert generic_reference("What is stated above?") == "above"


def test_uncommon_words_skips_short_words_and_stopwords():
    assert uncommon_words("Why is that the log of a node") == {"node"}


def test_uncommon_words_ignores_case_and_punctuation():
    assert uncommon_words("Quorum, QUORUM; quorum!") == {"quorum"}


def test_echo_score_is_one_when_every_word_is_lifted():
    assert echo_score("quorum replication latency", "quorum replication latency here") == 1.0


def test_echo_score_is_zero_when_nothing_overlaps():
    assert echo_score("swimming stroke rhythm", "quorum replication latency") == 0.0


def test_echo_score_is_the_share_of_uncommon_words():
    assert echo_score("quorum replication", "quorum only") == 0.5


def test_echo_score_of_a_question_with_no_uncommon_words_is_zero():
    assert echo_score("why is it so?", "anything at all") == 0.0


def test_candidate_id_is_stable_and_page_specific():
    assert candidate_id("a.pdf", 7) == candidate_id("a.pdf", 7)
    assert candidate_id("a.pdf", 7) != candidate_id("a.pdf", 8)
    assert candidate_id("a.pdf", 7) != candidate_id("b.pdf", 7)


def test_page_window_takes_one_page_either_side():
    window = page_window(["one", "two", "three", "four"], 2)
    assert "TARGET PAGE 2" in window
    assert "CONTEXT PAGE 1" in window and "CONTEXT PAGE 3" in window
    assert "four" not in window


def test_page_window_clamps_at_the_document_ends():
    assert "CONTEXT PAGE 0" not in page_window(["one", "two"], 1)
    assert page_window(["one", "two"], 2).count("PAGE") == 2


def test_records_round_trip_and_the_metadata_header_is_not_a_record(tmp_path):
    path = tmp_path / "candidates.jsonl"
    append_record(path, golden.file_metadata(seed=1))
    append_record(path, Candidate("x-p1", "a.pdf", 1, "Q?", "quote", 1, 0.5).as_record())

    records = read_records(path)
    assert len(records) == 1
    assert records[0]["id"] == "x-p1"
    assert json.loads(path.read_text().splitlines()[0])["seed"] == 1


def test_a_record_holds_exactly_the_agreed_fields():
    record = Candidate("x-p1", "a.pdf", 1, "Q?", "quote", 1, 0.5).as_record()
    assert sorted(record) == [
        "document",
        "echo_score",
        "id",
        "match_count",
        "page",
        "question",
        "quote",
    ]


def _stub(monkeypatch, answers):
    """Replace the one API call with a lookup keyed by page."""
    calls = []

    def fake(client, document, page, window):
        calls.append(page)
        return answers[page]

    monkeypatch.setattr(golden, "ask_for_question", fake)
    return calls


def test_generate_writes_a_kept_candidate_and_drops_a_generic_question(monkeypatch, tmp_path):
    pages = {"a.pdf": ["Replication keeps a copy on several machines.", "Second page here."]}
    _stub(
        monkeypatch,
        {
            1: Generated(
                question="Why keep a copy on several machines?",
                quote="Replication keeps a copy on several machines.",
            ),
            2: Generated(question="What does this passage claim?", quote="Second page here."),
        },
    )

    path = tmp_path / "candidates.jsonl"
    outcomes = list(
        golden.generate(
            client=None,
            pages_by_document=pages,
            refs=[PageRef("a.pdf", 1), PageRef("a.pdf", 2)],
            path=path,
        )
    )

    assert [outcome.kept for outcome in outcomes] == [True, False]
    assert outcomes[1].reason == "question says 'this passage'"
    assert len(read_records(path)) == 1


def test_generate_drops_a_quote_that_is_not_on_the_page(monkeypatch, tmp_path):
    pages = {"a.pdf": ["The page says one thing."]}
    _stub(monkeypatch, {1: Generated(question="What is said?", quote="Something invented.")})

    outcomes = list(
        golden.generate(
            client=None,
            pages_by_document=pages,
            refs=[PageRef("a.pdf", 1)],
            path=tmp_path / "candidates.jsonl",
        )
    )
    assert outcomes[0].reason == "quote not on the page"
    assert outcomes[0].detail == "Something invented."


def test_generate_never_asks_twice_for_a_page_already_on_disk(monkeypatch, tmp_path):
    pages = {"a.pdf": ["Replication keeps a copy."]}
    answer = {
        1: Generated(question="What does replication keep?", quote="Replication keeps a copy.")
    }
    path = tmp_path / "candidates.jsonl"

    calls = _stub(monkeypatch, answer)
    refs = [PageRef("a.pdf", 1)]
    first = golden.generate(client=None, pages_by_document=pages, refs=refs, path=path)
    assert next(iter(first)).kept
    second = list(golden.generate(client=None, pages_by_document=pages, refs=refs, path=path))

    assert calls == [1]  # the second run made no call at all
    assert second[0].reason == "already generated"
    assert len(read_records(path)) == 1


def test_generate_never_touches_the_reviewed_file(monkeypatch, tmp_path):
    pages = {"a.pdf": ["Replication keeps a copy."]}
    _stub(monkeypatch, {1: Generated(question="What is kept?", quote="Replication keeps a copy.")})
    list(
        golden.generate(
            client=None,
            pages_by_document=pages,
            refs=[PageRef("a.pdf", 1)],
            path=tmp_path / "candidates.jsonl",
        )
    )
    assert not (tmp_path / golden.GOLDEN_FILENAME).exists()

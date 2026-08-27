"""Normalisation and quote lookup, against invented text only.

The rule these tests defend: a quote is found by an exact match on tidied text, and
the position reported is always a position in the untidied text.
"""

from __future__ import annotations

from ragdoll.golden import find_quote, normalise

SOFT = "­"


def test_whitespace_runs_collapse_to_one_space():
    assert normalise("a  \n\t b").text == "a b"


def test_leading_and_trailing_whitespace_disappear():
    assert normalise("  \n hello world \n ").text == "hello world"


def test_soft_hyphen_disappears():
    assert normalise(f"inter{SOFT}national").text == "international"


def test_hyphen_before_a_line_break_disappears_with_the_break():
    assert normalise("inter-\nnational").text == "international"
    assert normalise("inter-\r\n   national").text == "international"


def test_a_hyphen_inside_a_line_is_kept():
    assert normalise("write-ahead log").text == "write-ahead log"


def test_a_hyphen_before_a_plain_space_is_kept():
    assert normalise("write- ahead").text == "write- ahead"


def test_case_is_kept():
    assert normalise("Kafka And CAP").text == "Kafka And CAP"


def test_origins_map_back_to_the_source():
    source = "a  \n b"
    result = normalise(source)
    assert result.text == "a b"
    for position, character in enumerate(result.text):
        if character != " ":
            assert source[result.origins[position]] == character


def test_span_returns_source_positions():
    source = "the  write-\nahead log here"
    result = normalise(source)
    start, end = result.span(result.text.index("writeahead"), result.text.index(" log"))
    assert source[start:end] == "write-\nahead"


def test_a_quote_wrapped_across_lines_is_found_once():
    page = "Replication means keeping a copy of the same\ndata on several machines."
    lookup = find_quote(page, "keeping a copy of the same data on several machines.")
    assert lookup.match_count == 1
    assert lookup.found and not lookup.ambiguous
    start, end = lookup.spans[0]
    assert page[start:end] == "keeping a copy of the same\ndata on several machines."


def test_a_hyphenated_quote_is_found():
    page = "The write-\nahead log is appended to."
    assert find_quote(page, "The write-ahead log is appended to.").match_count == 1


def test_a_quote_that_is_not_there_is_reported_as_zero():
    lookup = find_quote("The page says one thing.", "The page says another thing.")
    assert lookup.match_count == 0
    assert not lookup.found
    assert lookup.spans == ()


def test_two_matches_are_both_returned_and_marked_ambiguous():
    page = "Kafka is a log. Something else. Kafka is a log."
    lookup = find_quote(page, "Kafka is a log.")
    assert lookup.match_count == 2
    assert lookup.ambiguous
    assert [page[a:b] for a, b in lookup.spans] == ["Kafka is a log.", "Kafka is a log."]


def test_the_match_is_case_sensitive():
    assert find_quote("Kafka is a log.", "kafka is a log.").match_count == 0


def test_an_empty_quote_matches_nothing():
    assert find_quote("any page at all", "   \n ").match_count == 0


def test_a_dehyphenated_quote_is_found_by_the_second_pass():
    page = "The write-\nahead log is appended to."
    lookup = find_quote(page, "The write-ahead log is appended to.")
    assert lookup.match_count == 1
    assert lookup.dehyphenated
    start, end = lookup.spans[0]
    assert page[start:end] == "The write-\nahead log is appended to."


def test_a_verbatim_quote_does_not_touch_the_second_pass():
    page = "The write-\nahead log is appended to."
    lookup = find_quote(page, "The write-\nahead log is appended to.")
    assert lookup.match_count == 1
    assert not lookup.dehyphenated


def test_the_second_pass_stays_exact_and_still_reports_nothing_for_a_wrong_quote():
    lookup = find_quote("The page says one thing.", "The page says another thing.")
    assert lookup.match_count == 0
    assert not lookup.dehyphenated


def test_hyphens_are_only_dropped_on_the_second_pass():
    assert normalise("write-ahead").text == "write-ahead"
    assert normalise("write-ahead", drop_hyphens=True).text == "writeahead"

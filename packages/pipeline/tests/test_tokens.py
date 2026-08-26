"""Tests for token counting.

The exactness flag matters more than the number. A route decided on an approximate
count is a guess, and the flag is what lets callers refuse to act on one.
"""

from ragdoll.tokens import count_or_estimate, estimate_tokens


def test_estimate_is_never_marked_exact():
    assert estimate_tokens("hello world").exact is False


def test_estimate_scales_with_length():
    short = estimate_tokens("a" * 100)
    long = estimate_tokens("a" * 1000)
    assert long.tokens > short.tokens


def test_estimate_of_empty_text_is_zero():
    assert estimate_tokens("").tokens == 0


def test_offline_mode_never_calls_the_api():
    # allow_api=False must not raise even with no credentials present.
    result = count_or_estimate("some text", allow_api=False)
    assert result.exact is False


def test_approximate_counts_are_flagged_in_their_string_form():
    """A number that reaches a human must carry its own uncertainty."""
    assert str(estimate_tokens("hello" * 100)).startswith("~")
    assert "approx" in str(estimate_tokens("hello" * 100))

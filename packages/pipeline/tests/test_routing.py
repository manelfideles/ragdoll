"""Tests for the routing decision.

The threshold is a boundary, and boundaries are where the bugs live, so these tests
pin the exact values on either side of it rather than testing somewhere comfortable.
"""

import pytest

from ragdoll.routing import (
    HYSTERESIS_TOKENS,
    THRESHOLD_TOKENS,
    Route,
    decide,
)


def test_empty_project_stuffs():
    assert decide(0).route is Route.STUFF


def test_just_under_the_threshold_stuffs():
    assert decide(THRESHOLD_TOKENS - 1).route is Route.STUFF


def test_exactly_on_the_threshold_retrieves():
    # The guidance says "smaller than 200,000", so the threshold itself retrieves.
    assert decide(THRESHOLD_TOKENS).route is Route.RETRIEVE


def test_well_over_the_threshold_retrieves():
    assert decide(1_000_000).route is Route.RETRIEVE


def test_headroom_is_positive_below_and_negative_above():
    assert decide(150_000).headroom == 50_000
    assert decide(250_000).headroom == -50_000


def test_negative_token_count_is_rejected():
    with pytest.raises(ValueError, match="must not be negative"):
        decide(-1)


class TestHysteresis:
    """An indexed project must not flap in and out of retrieval near the boundary."""

    def test_indexed_project_just_below_threshold_keeps_retrieving(self):
        assert decide(THRESHOLD_TOKENS - 1, already_indexed=True).route is Route.RETRIEVE

    def test_indexed_project_at_the_release_point_keeps_retrieving(self):
        release = THRESHOLD_TOKENS - HYSTERESIS_TOKENS
        assert decide(release, already_indexed=True).route is Route.RETRIEVE

    def test_indexed_project_below_the_release_point_drops_the_index(self):
        release = THRESHOLD_TOKENS - HYSTERESIS_TOKENS
        assert decide(release - 1, already_indexed=True).route is Route.STUFF

    def test_hysteresis_only_applies_to_indexed_projects(self):
        release = THRESHOLD_TOKENS - HYSTERESIS_TOKENS
        assert decide(release, already_indexed=False).route is Route.STUFF
        assert decide(release, already_indexed=True).route is Route.RETRIEVE

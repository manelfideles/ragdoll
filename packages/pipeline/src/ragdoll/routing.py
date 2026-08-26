"""The routing decision: does this project need retrieval at all?

Anthropic's guidance is that a knowledge base under 200,000 tokens, roughly 500
pages, should simply be placed in the prompt and served with prompt caching. A
retrieval pipeline cannot fetch the wrong passage if there is no retrieval.

Ragdoll never knows in advance how large a project will be, so this is a runtime
decision per project rather than a one-time judgement. Everything here is pure:
no file access, no network. That is what makes it cheap to test.

Source: https://www.anthropic.com/engineering/contextual-retrieval
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

THRESHOLD_TOKENS = 200_000
"""Below this, stuff the prompt. At or above it, retrieve."""

HYSTERESIS_TOKENS = 20_000
"""Dead zone that stops a project flapping between routes near the threshold.

A project sitting at 199,000 tokens gains a small document and crosses. Delete it
and it drops back. Without a dead zone every crossing triggers an index build or
teardown. Once a project has been indexed it stays on the retrieve route until it
falls this far back below the threshold.
"""


class Route(StrEnum):
    """What a project should do at query time."""

    STUFF = "stuff"
    RETRIEVE = "retrieve"


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    route: Route
    total_tokens: int
    threshold: int
    reason: str

    @property
    def headroom(self) -> int:
        """Tokens that can still be added before the threshold is crossed.

        Negative once the project is over the threshold.
        """
        return self.threshold - self.total_tokens


def decide(total_tokens: int, *, already_indexed: bool = False) -> RoutingDecision:
    """Choose a route for a project of ``total_tokens`` total size.

    ``already_indexed`` applies the hysteresis dead zone. Pass it when the project
    has an existing index, so that a small deletion does not tear that index down.
    """
    if total_tokens < 0:
        raise ValueError(f"total_tokens must not be negative, got {total_tokens}")

    if already_indexed:
        release = THRESHOLD_TOKENS - HYSTERESIS_TOKENS
        if total_tokens >= release:
            return RoutingDecision(
                Route.RETRIEVE,
                total_tokens,
                THRESHOLD_TOKENS,
                f"already indexed and still at or above the {release:,}-token release point",
            )
        return RoutingDecision(
            Route.STUFF,
            total_tokens,
            THRESHOLD_TOKENS,
            f"fell below the {release:,}-token release point, so the index can be dropped",
        )

    if total_tokens >= THRESHOLD_TOKENS:
        return RoutingDecision(
            Route.RETRIEVE,
            total_tokens,
            THRESHOLD_TOKENS,
            "over the threshold, so the corpus does not fit in one prompt",
        )
    return RoutingDecision(
        Route.STUFF,
        total_tokens,
        THRESHOLD_TOKENS,
        "under the threshold, so the whole corpus fits in one cached prompt",
    )

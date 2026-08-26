"""Counting tokens.

The routing decision in :mod:`ragdoll.routing` compares a project against a token
threshold, so the count has to be trustworthy. Only the model's own tokenizer gives
that, which is why this module calls the Claude API's ``count_tokens`` endpoint.

Do not substitute ``tiktoken``. That is OpenAI's tokenizer and it undercounts Claude
tokens by roughly 15 to 20 percent on prose, and by more on code. A 15 percent error
sits directly on top of a threshold decision, which is the one place it does damage.

The rough estimator below exists only so that the pipeline can be explored with no
API key. It is labelled approximate everywhere it surfaces, and it must never decide
a route in anything you would call production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MODEL = "claude-haiku-4-5"
"""The model that will read these prompts, so the model whose tokenizer decides the count.

Token counts are model-specific. This constant is not a cost dial — ``count_tokens`` runs
no inference. It must track whichever model ragdoll uses to answer, or the number means
nothing. Changing it invalidates every cached count.
"""

_CHARS_PER_TOKEN = 3.6
"""Crude prose ratio for the offline estimator. Not a tokenizer."""


@dataclass(frozen=True, slots=True)
class TokenCount:
    tokens: int
    exact: bool

    def __str__(self) -> str:
        return f"{self.tokens:,}" if self.exact else f"~{self.tokens:,} (approx)"


def estimate_tokens(text: str) -> TokenCount:
    """Offline guess from character count. Never use this to decide a route."""
    return TokenCount(tokens=int(len(text) / _CHARS_PER_TOKEN), exact=False)


def has_credentials() -> bool:
    """Whether an API key is present in the environment.

    The SDK also resolves an ``ant auth login`` profile, which this cannot see, so a
    False here means "probably not" rather than "definitely not". Callers should try
    the real count and fall back on failure rather than trusting this alone.
    """
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def count_tokens(text: str, *, model: str = MODEL) -> TokenCount:
    """Exact token count from the Claude API. Raises if credentials are missing."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    return TokenCount(tokens=response.input_tokens, exact=True)


def count_or_estimate(text: str, *, model: str = MODEL, allow_api: bool = True) -> TokenCount:
    """Exact count when possible, approximate when not.

    Returns the approximate count rather than raising, so that a missing key degrades
    the report instead of stopping it. The ``exact`` flag travels with the number so
    callers can refuse to act on a guess.
    """
    if not allow_api:
        return estimate_tokens(text)
    try:
        return count_tokens(text, model=model)
    except Exception:
        return estimate_tokens(text)

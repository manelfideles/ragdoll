"""Loading local configuration.

Ragdoll reads its one secret, the Claude API key, from the environment. A ``.env``
file at the repository root is loaded for convenience during local development.

Two rules hold here. The ``.env`` file is never committed, and no value read from it
is ever printed or logged. Only its presence and its absence are reported.
"""

from __future__ import annotations

from pathlib import Path

ENV_FILENAME = ".env"
_MARKERS = ("pyproject.toml", ".git")


def find_repo_root(start: Path | None = None) -> Path | None:
    """Walk upwards from ``start`` looking for the repository root.

    Returns None when no marker is found, rather than guessing, so that callers can
    treat "no project here" differently from "project with no .env".
    """
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in _MARKERS):
            return candidate
    return None


def load_env(start: Path | None = None) -> Path | None:
    """Load the repository's ``.env`` into the environment, if there is one.

    Existing environment variables win. A key exported in the shell should override
    a stale value left in a file, because the shell is the more deliberate act.

    Returns the path that was loaded, or None if there was nothing to load.
    """
    root = find_repo_root(start)
    if root is None:
        return None

    env_file = root / ENV_FILENAME
    if not env_file.is_file():
        return None

    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)
    return env_file

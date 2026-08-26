"""Tests for configuration loading.

The behaviour that matters is precedence. A key exported in the shell must beat a
stale value in a file, because the export is the more deliberate act and is what
someone reaches for when debugging.
"""

import os
from pathlib import Path

from ragdoll.config import find_repo_root, load_env


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").touch()
    return tmp_path


def test_finds_root_by_marker(tmp_path: Path):
    root = _make_repo(tmp_path)
    nested = root / "a" / "b"
    nested.mkdir(parents=True)

    assert find_repo_root(nested) == root.resolve()


def test_returns_none_when_no_marker_is_found(tmp_path: Path):
    # tmp_path has no pyproject.toml or .git, and neither should its parents.
    assert find_repo_root(tmp_path) is None


def test_returns_none_when_repo_has_no_env_file(tmp_path: Path):
    assert load_env(_make_repo(tmp_path)) is None


def test_loads_values_from_env_file(tmp_path: Path, monkeypatch):
    root = _make_repo(tmp_path)
    (root / ".env").write_text("RAGDOLL_TEST_VALUE=from-file\n")
    monkeypatch.delenv("RAGDOLL_TEST_VALUE", raising=False)

    assert load_env(root) == root / ".env"
    assert os.environ["RAGDOLL_TEST_VALUE"] == "from-file"


def test_existing_environment_wins_over_the_file(tmp_path: Path, monkeypatch):
    root = _make_repo(tmp_path)
    (root / ".env").write_text("RAGDOLL_TEST_VALUE=from-file\n")
    monkeypatch.setenv("RAGDOLL_TEST_VALUE", "from-shell")

    load_env(root)

    assert os.environ["RAGDOLL_TEST_VALUE"] == "from-shell"

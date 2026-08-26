"""Tests for document discovery.

Text extraction itself needs a real PDF and is covered by running the pipeline over
the corpus. What is worth pinning here is discovery, because a silently missed file
means a project is measured smaller than it is, which flips the routing decision.
"""

from pathlib import Path

from ragdoll.parse import find_pdfs


def test_finds_pdfs_and_ignores_other_files(tmp_path: Path):
    (tmp_path / "a.pdf").touch()
    (tmp_path / "b.pdf").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / ".DS_Store").touch()

    assert [p.name for p in find_pdfs(tmp_path)] == ["a.pdf", "b.pdf"]


def test_results_are_sorted_for_stable_output(tmp_path: Path):
    for name in ("zebra.pdf", "apple.pdf", "mango.pdf"):
        (tmp_path / name).touch()

    assert [p.name for p in find_pdfs(tmp_path)] == ["apple.pdf", "mango.pdf", "zebra.pdf"]


def test_empty_directory_yields_nothing(tmp_path: Path):
    assert find_pdfs(tmp_path) == []


def test_subdirectories_are_not_searched(tmp_path: Path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "deep.pdf").touch()

    # Deliberate: a project is a flat directory for now. If this changes, this test
    # is the reminder that the cache keys and the token total change with it.
    assert find_pdfs(tmp_path) == []

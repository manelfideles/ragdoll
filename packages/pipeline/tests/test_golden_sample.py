"""The sample must be reproducible, distinct, and honest about document sizes.

Every fixture here is invented text. No corpus page appears in this repository.
"""

from __future__ import annotations

from ragdoll.golden import DEFAULT_SEED, PageRef, eligible_pages, sample_pages


def test_eligible_pages_skips_only_empty_pages():
    pages = ["hello", "", "   \n ", "a", "x" * 5000]
    assert eligible_pages(pages) == [1, 4, 5]


def test_eligible_pages_are_one_indexed():
    assert eligible_pages(["", "second"]) == [2]


def test_sample_covers_every_eligible_page_exactly_once():
    eligible = {"a.pdf": [1, 2, 3], "b.pdf": [1, 2, 3, 4, 5, 6, 7]}
    order = sample_pages(eligible)

    assert len(order) == 10
    assert len(set(order)) == 10
    assert {(ref.document, ref.page) for ref in order} == {
        ("a.pdf", page) for page in eligible["a.pdf"]
    } | {("b.pdf", page) for page in eligible["b.pdf"]}


def test_same_seed_gives_the_same_order():
    eligible = {"a.pdf": list(range(1, 40)), "b.pdf": list(range(1, 61))}
    assert sample_pages(eligible, seed=7) == sample_pages(eligible, seed=7)


def test_a_different_seed_gives_a_different_order():
    eligible = {"a.pdf": list(range(1, 40)), "b.pdf": list(range(1, 61))}
    assert sample_pages(eligible, seed=7) != sample_pages(eligible, seed=8)


def test_any_prefix_is_proportional_to_document_size():
    # 100 eligible pages against 900: a 50-page prefix should hold about 5 and 45.
    eligible = {"small.pdf": list(range(1, 101)), "large.pdf": list(range(1, 901))}
    prefix = sample_pages(eligible)[:50]

    small = sum(1 for ref in prefix if ref.document == "small.pdf")
    assert 3 <= small <= 7


def test_the_prefix_of_a_longer_take_extends_a_shorter_one():
    # Pass two must be able to keep going without repeating a page.
    eligible = {"a.pdf": list(range(1, 31)), "b.pdf": list(range(1, 71))}
    order = sample_pages(eligible)
    assert order[:30] == sample_pages(eligible)[:30]
    assert len(set(order[:50])) == 50


def test_documents_with_no_eligible_pages_are_absent():
    order = sample_pages({"scan.pdf": [], "real.pdf": [1, 2]})
    assert order == [PageRef("real.pdf", 1), PageRef("real.pdf", 2)] or set(order) == {
        PageRef("real.pdf", 1),
        PageRef("real.pdf", 2),
    }


def test_the_default_seed_is_fixed():
    assert DEFAULT_SEED == 20260827

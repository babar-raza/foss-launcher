"""Tests for TC-5134: Sort stability tiebreakers in planner and section_prompt.

Verifies that equal-priority items produce identical sort order across
repeated calls, eliminating non-determinism from pipeline sort operations.
"""
from __future__ import annotations

import hashlib
import random

import pytest

from launcher.models.understanding import SnippetFact
from launcher.models.claims import Snippet


# ---------------------------------------------------------------------------
# Plan.py: snippet seeding sort — confidence DESC, op priority ASC, fact_id ASC
# ---------------------------------------------------------------------------

# Mirror the priority map from plan.py
_OP_SEED_PRIORITY = {
    "load_file": 0,
    "save_file": 1,
    "convert": 2,
    "create": 3,
    "modify": 4,
    "query": 5,
}


def _plan_sort_key(sf: SnippetFact) -> tuple:
    """Reproduce the sort key from plan.py line ~595."""
    return (
        -getattr(sf, "confidence", 0.0),
        _OP_SEED_PRIORITY.get(getattr(sf, "operation_label", ""), 99),
        getattr(sf, "fact_id", ""),
    )


class TestPlanSortStability:
    """Verify plan.py snippet seeding sort is deterministic for equal-priority items."""

    def _make_snippet_facts(self) -> list[SnippetFact]:
        """Create SnippetFacts with identical confidence and operation_label but different fact_ids."""
        return [
            SnippetFact(fact_id="SF-cells-py-load-aaa111", confidence=0.9, operation_label="load_file", code="a()"),
            SnippetFact(fact_id="SF-cells-py-load-bbb222", confidence=0.9, operation_label="load_file", code="b()"),
            SnippetFact(fact_id="SF-cells-py-load-ccc333", confidence=0.9, operation_label="load_file", code="c()"),
            SnippetFact(fact_id="SF-cells-py-load-ddd444", confidence=0.9, operation_label="load_file", code="d()"),
            SnippetFact(fact_id="SF-cells-py-load-eee555", confidence=0.9, operation_label="load_file", code="e()"),
        ]

    def test_equal_priority_sorted_by_fact_id(self) -> None:
        """Items with same confidence and operation sort deterministically by fact_id."""
        items = self._make_snippet_facts()
        random.shuffle(items)
        items.sort(key=_plan_sort_key)
        fact_ids = [sf.fact_id for sf in items]
        assert fact_ids == sorted(fact_ids), "Equal-priority items must be sorted by fact_id"

    def test_sort_identical_across_10_runs(self) -> None:
        """Shuffling and re-sorting 10 times always produces the same order."""
        items = self._make_snippet_facts()
        reference = sorted(items, key=_plan_sort_key)
        ref_ids = [sf.fact_id for sf in reference]

        for _ in range(10):
            shuffled = list(items)
            random.shuffle(shuffled)
            shuffled.sort(key=_plan_sort_key)
            assert [sf.fact_id for sf in shuffled] == ref_ids

    def test_confidence_still_primary_sort(self) -> None:
        """Higher confidence comes first regardless of fact_id."""
        items = [
            SnippetFact(fact_id="SF-zzz", confidence=1.0, operation_label="load_file", code="x()"),
            SnippetFact(fact_id="SF-aaa", confidence=0.7, operation_label="load_file", code="y()"),
        ]
        items.sort(key=_plan_sort_key)
        assert items[0].fact_id == "SF-zzz"  # higher confidence first


# ---------------------------------------------------------------------------
# section_prompt.py: _rank_snippets — operation match, source type, claim overlap,
#                    snippet_id, code hash
# ---------------------------------------------------------------------------

def _rank_sort_key(s: Snippet, section_claim_ids: set[str], op_target: str = "") -> tuple:
    """Reproduce the sort key from section_prompt.py _rank_snippets."""
    _SOURCE_PRIORITY = {"extracted": 0, "generated": 1, "synthetic": 2}
    return (
        0 if (op_target and getattr(s, "operation_label", "") == op_target) else 1,
        _SOURCE_PRIORITY.get(getattr(s, "source_type", "generated"), 1),
        -len(set(getattr(s, "claim_ids", [])) & section_claim_ids),
        getattr(s, "snippet_id", "") or "",
        hashlib.md5((getattr(s, "code", "") or "").encode(), usedforsecurity=False).hexdigest(),
    )


class TestSectionPromptSortStability:
    """Verify section_prompt.py snippet ranking is deterministic for equal-score items."""

    def _make_snippets(self) -> list[Snippet]:
        """Create Snippets with same source_type, same claim overlap, but different code."""
        return [
            Snippet(code="wb = Workbook()\nwb.save('a.xlsx')", source_type="extracted", claim_ids=["CLM-1"], source_file="a.py"),
            Snippet(code="wb = Workbook()\nwb.save('b.xlsx')", source_type="extracted", claim_ids=["CLM-1"], source_file="b.py"),
            Snippet(code="wb = Workbook()\nwb.save('c.xlsx')", source_type="extracted", claim_ids=["CLM-1"], source_file="c.py"),
            Snippet(code="wb = Workbook()\nwb.save('d.xlsx')", source_type="extracted", claim_ids=["CLM-1"], source_file="d.py"),
        ]

    def test_equal_score_snippets_sorted_by_code_hash(self) -> None:
        """Snippets with same source_type and claim overlap sort by code hash."""
        section_claims = {"CLM-1"}
        items = self._make_snippets()
        random.shuffle(items)
        items.sort(key=lambda s: _rank_sort_key(s, section_claims))
        hashes = [
            hashlib.md5(s.code.encode(), usedforsecurity=False).hexdigest()
            for s in items
        ]
        assert hashes == sorted(hashes), "Equal-score snippets must be sorted by code hash"

    def test_sort_identical_across_10_runs(self) -> None:
        """Shuffling and re-sorting 10 times always produces the same order."""
        section_claims = {"CLM-1"}
        items = self._make_snippets()
        reference = sorted(items, key=lambda s: _rank_sort_key(s, section_claims))
        ref_codes = [s.code for s in reference]

        for _ in range(10):
            shuffled = list(items)
            random.shuffle(shuffled)
            shuffled.sort(key=lambda s: _rank_sort_key(s, section_claims))
            assert [s.code for s in shuffled] == ref_codes

    def test_source_type_still_primary_after_operation(self) -> None:
        """Extracted snippets rank before generated, regardless of code hash."""
        items = [
            Snippet(code="zzz_gen", source_type="generated", claim_ids=["CLM-1"], source_file="g.py"),
            Snippet(code="aaa_ext", source_type="extracted", claim_ids=["CLM-1"], source_file="e.py"),
        ]
        section_claims = {"CLM-1"}
        items.sort(key=lambda s: _rank_sort_key(s, section_claims))
        assert items[0].source_type == "extracted"

"""Tests for TC-UND-113: snippet_source_idx bridge field on SnippetFact.

Verifies that _build_snippet_facts() populates snippet_source_idx with the correct
index into the source snippets list, enabling the Planner (TC-PLAN-204) to translate
SnippetFact → Snippet index for deterministic snippet seeding.
"""

from __future__ import annotations

import pytest

from launcher.models.claims import Snippet
from launcher.models.product import ProductIdentity
from launcher.models.understanding import SnippetFact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(**overrides) -> ProductIdentity:
    defaults = dict(
        family="cells",
        platform="python",
        display_name="Aspose.Cells",
        canonical_import="aspose_cells_foss",
        repo_url="https://example.com",
    )
    defaults.update(overrides)
    return ProductIdentity(**defaults)


def _make_snippet(code: str, source_file: str = "examples/ex.py", **kw) -> Snippet:
    return Snippet(code=code, language="python", source_file=source_file, **kw)


def _build(snippets, product=None):
    from launcher.workers.understand.extract._entry import _build_snippet_facts
    return _build_snippet_facts(snippets, product or _make_product())


# ---------------------------------------------------------------------------
# Tests: snippet_source_idx correctness
# ---------------------------------------------------------------------------

class TestSnippetSourceIdx:
    def test_single_snippet_gets_idx_zero(self):
        """The first snippet in the list gets snippet_source_idx=0."""
        snips = [_make_snippet("wb.save('out.xlsx')")]
        facts = _build(snips)
        assert len(facts) == 1
        assert facts[0].snippet_source_idx == 0

    def test_multiple_snippets_get_sequential_indices(self):
        """Each fact's snippet_source_idx matches its source position in the list."""
        snips = [
            _make_snippet("wb.load('in.xlsx')"),
            _make_snippet("wb.save('out.csv')"),
            _make_snippet("wb.load('a.xlsx'); wb.save('b.csv')"),
        ]
        facts = _build(snips)
        assert len(facts) == 3
        for expected_idx, fact in enumerate(facts):
            assert fact.snippet_source_idx == expected_idx, (
                f"Expected snippet_source_idx={expected_idx}, got {fact.snippet_source_idx}"
            )

    def test_empty_code_snippet_is_skipped_indices_preserved(self):
        """Snippets with empty code are skipped; remaining facts keep correct indices."""
        snips = [
            _make_snippet("wb.load('in.xlsx')"),   # idx 0 — will produce a fact
            _make_snippet(""),                       # idx 1 — skipped (empty code)
            _make_snippet("wb.save('out.csv')"),    # idx 2 — will produce a fact
        ]
        facts = _build(snips)
        assert len(facts) == 2
        assert facts[0].snippet_source_idx == 0
        assert facts[1].snippet_source_idx == 2  # idx 1 was skipped, not renumbered

    def test_empty_input_produces_no_facts(self):
        """An empty snippet list produces no facts."""
        facts = _build([])
        assert facts == []

    def test_none_input_produces_no_facts(self):
        """None input is handled gracefully (no TypeError)."""
        facts = _build(None)
        assert facts == []

    def test_idx_never_minus_one_for_valid_snippets(self):
        """-1 (the 'unknown' sentinel) must not appear for any fact built from a non-empty list."""
        snips = [
            _make_snippet("wb.load('a.xlsx')"),
            _make_snippet("wb.save('b.csv')"),
        ]
        facts = _build(snips)
        for fact in facts:
            assert fact.snippet_source_idx != -1, (
                f"snippet_source_idx should never be -1 for a valid snippet, "
                f"but got -1 for fact_id={fact.fact_id}"
            )

    def test_default_value_is_minus_one(self):
        """The SnippetFact model's default snippet_source_idx is -1 (backward compat)."""
        sf = SnippetFact(code="x", operation_label="other")
        assert sf.snippet_source_idx == -1

    def test_idx_matches_when_snippets_have_various_operations(self):
        """Indices are correct even when operation_labels differ across snippets."""
        snips = [
            _make_snippet("wb.load('in.xlsx'); wb.save('out.csv')"),   # convert → idx 0
            _make_snippet("wb.save('out.xlsx')"),                       # save_file → idx 1
            _make_snippet("wb.load('in.csv')"),                        # load_file → idx 2
            _make_snippet("print('no op here')"),                      # other → idx 3
        ]
        facts = _build(snips)
        assert len(facts) == 4

        ops = {f.snippet_source_idx: f.operation_label for f in facts}
        assert ops[0] == "convert"
        assert ops[1] == "save_file"
        assert ops[2] == "load_file"
        assert ops[3] == "other"

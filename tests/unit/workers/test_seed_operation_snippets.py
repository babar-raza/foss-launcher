"""Tests for TC-PLAN-204: _seed_operation_snippets() deterministic snippet seeding.

Verifies that operation-labeled snippets from extraction_db are seeded into
operation-based page roles (howto_article, format_conversion, code_snippet)
independently of claim_ids routing.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from launcher.models.claims import Snippet
from launcher.models.plan import PlannedPage
from launcher.models.understanding import ExtractionDatabase, SnippetFact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(
    page_id: str,
    page_role: str,
    assigned_snippets: list[int] | None = None,
    mandatory: bool = True,
) -> PlannedPage:
    return PlannedPage(
        page_id=page_id,
        page_role=page_role,
        title=f"Test page {page_id}",
        mandatory=mandatory,
        assigned_snippets=assigned_snippets or [],
    )


def _make_snippet(code: str = "wb.save('out.xlsx')") -> Snippet:
    return Snippet(code=code, language="python", syntax_valid=True)


def _make_snippet_fact(
    op_label: str,
    source_idx: int,
    confidence: float = 0.9,
    syntax_valid: bool = True,
) -> SnippetFact:
    return SnippetFact(
        fact_id=f"SF-test-{op_label}-{source_idx}",
        code=f"# {op_label} snippet {source_idx}",
        operation_label=op_label,
        snippet_source_idx=source_idx,
        confidence=confidence,
        syntax_valid=syntax_valid,
    )


def _make_extraction_db(snippet_facts: list[SnippetFact]) -> ExtractionDatabase:
    return ExtractionDatabase(snippet_facts=snippet_facts)


def _seed(pages, snippets, extraction_db):
    from launcher.workers.planner.plan import _seed_operation_snippets
    return _seed_operation_snippets(pages, snippets, extraction_db)


# ---------------------------------------------------------------------------
# Tests: seeding behavior
# ---------------------------------------------------------------------------

class TestSeedOperationSnippets:
    def test_howto_article_gets_convert_snippets(self):
        """howto_article pages receive convert-labeled snippets."""
        snippets = [_make_snippet(), _make_snippet(), _make_snippet()]
        db = _make_extraction_db([
            _make_snippet_fact("convert", 0),
            _make_snippet_fact("load_file", 1),
        ])
        pages = [_make_page("p/howto", "howto_article")]
        result = _seed(pages, snippets, db)

        assert len(result) == 1
        assert 0 in result[0].assigned_snippets
        assert 1 in result[0].assigned_snippets

    def test_format_conversion_gets_convert_snippets(self):
        """format_conversion pages receive convert-labeled snippets."""
        snippets = [_make_snippet(), _make_snippet()]
        db = _make_extraction_db([
            _make_snippet_fact("convert", 0),
            _make_snippet_fact("save_file", 1),
        ])
        pages = [_make_page("p/fmt", "format_conversion")]
        result = _seed(pages, snippets, db)

        assert 0 in result[0].assigned_snippets
        assert 1 in result[0].assigned_snippets

    def test_api_reference_gets_zero_seeds(self):
        """api_reference is not in ROLE_OP_MAP — should receive no seeded snippets."""
        snippets = [_make_snippet(), _make_snippet()]
        db = _make_extraction_db([
            _make_snippet_fact("convert", 0),
            _make_snippet_fact("load_file", 1),
        ])
        pages = [_make_page("p/api", "api_reference")]
        result = _seed(pages, snippets, db)

        assert result[0].assigned_snippets == []

    def test_no_duplicates_when_already_claim_assigned(self):
        """Snippets already in assigned_snippets from claim assignment are not duplicated."""
        snippets = [_make_snippet()]
        db = _make_extraction_db([_make_snippet_fact("convert", 0)])
        # Page already has snippet 0 from claim assignment
        pages = [_make_page("p/howto", "howto_article", assigned_snippets=[0])]
        result = _seed(pages, snippets, db)

        assert result[0].assigned_snippets.count(0) == 1  # exactly once, not duplicated

    def test_max_seeded_cap_enforced(self):
        """At most _MAX_SEEDED_SNIPPETS=3 snippets are seeded per page."""
        from launcher.workers.planner.plan import _MAX_SEEDED_SNIPPETS

        n = _MAX_SEEDED_SNIPPETS + 2  # e.g. 5 candidates
        snippets = [_make_snippet() for _ in range(n)]
        facts = [_make_snippet_fact("convert", i) for i in range(n)]
        db = _make_extraction_db(facts)
        pages = [_make_page("p/howto", "howto_article")]
        result = _seed(pages, snippets, db)

        assert len(result[0].assigned_snippets) == _MAX_SEEDED_SNIPPETS

    def test_extraction_db_none_returns_pages_unchanged(self):
        """When extraction_db is None, pages are returned as-is."""
        snippets = [_make_snippet()]
        pages = [_make_page("p/howto", "howto_article")]
        result = _seed(pages, snippets, None)

        assert result == pages
        assert result[0].assigned_snippets == []

    def test_syntax_invalid_snippets_excluded(self):
        """SnippetFacts with syntax_valid=False are not seeded."""
        snippets = [_make_snippet(), _make_snippet()]
        db = _make_extraction_db([
            _make_snippet_fact("convert", 0, syntax_valid=False),
            _make_snippet_fact("load_file", 1, syntax_valid=True),
        ])
        pages = [_make_page("p/howto", "howto_article")]
        result = _seed(pages, snippets, db)

        assert 0 not in result[0].assigned_snippets
        assert 1 in result[0].assigned_snippets

    def test_out_of_bounds_snippet_source_idx_excluded(self):
        """snippet_source_idx values outside [0, len(snippets)) are silently skipped."""
        snippets = [_make_snippet()]  # only 1 snippet (idx 0)
        db = _make_extraction_db([
            _make_snippet_fact("convert", 99),   # out of bounds
            _make_snippet_fact("convert", -1),   # sentinel
            _make_snippet_fact("load_file", 0),  # valid
        ])
        pages = [_make_page("p/howto", "howto_article")]
        result = _seed(pages, snippets, db)

        assert result[0].assigned_snippets == [0]

    def test_higher_confidence_seeded_first(self):
        """Candidates are sorted by confidence DESC — higher confidence snippets take priority."""
        snippets = [_make_snippet(), _make_snippet(), _make_snippet()]
        db = _make_extraction_db([
            _make_snippet_fact("convert", 0, confidence=0.7),
            _make_snippet_fact("convert", 1, confidence=1.0),  # highest
            _make_snippet_fact("convert", 2, confidence=0.9),
        ])
        # Cap at 2 to observe ordering
        import launcher.workers.planner.plan as plan_mod
        original_max = plan_mod._MAX_SEEDED_SNIPPETS
        plan_mod._MAX_SEEDED_SNIPPETS = 2
        try:
            pages = [_make_page("p/howto", "howto_article")]
            result = _seed(pages, snippets, db)
        finally:
            plan_mod._MAX_SEEDED_SNIPPETS = original_max

        # idx 1 (confidence=1.0) and idx 2 (confidence=0.9) should be seeded; 0 not
        assert 1 in result[0].assigned_snippets
        assert 2 in result[0].assigned_snippets
        assert 0 not in result[0].assigned_snippets

    def test_convert_op_preferred_over_load_when_equal_confidence(self):
        """With equal confidence, convert beats load_file (operation priority)."""
        snippets = [_make_snippet(), _make_snippet(), _make_snippet()]
        db = _make_extraction_db([
            _make_snippet_fact("load_file", 0, confidence=0.9),
            _make_snippet_fact("convert", 1, confidence=0.9),   # same confidence, higher op priority
            _make_snippet_fact("save_file", 2, confidence=0.9),
        ])
        import launcher.workers.planner.plan as plan_mod
        original_max = plan_mod._MAX_SEEDED_SNIPPETS
        plan_mod._MAX_SEEDED_SNIPPETS = 1
        try:
            pages = [_make_page("p/fmt", "format_conversion")]
            result = _seed(pages, snippets, db)
        finally:
            plan_mod._MAX_SEEDED_SNIPPETS = original_max

        assert result[0].assigned_snippets == [1]  # convert wins

    def test_empty_snippet_facts_returns_pages_unchanged(self):
        """No seeding occurs when extraction_db has no snippet_facts."""
        snippets = [_make_snippet()]
        db = _make_extraction_db([])
        pages = [_make_page("p/howto", "howto_article")]
        result = _seed(pages, snippets, db)

        assert result[0].assigned_snippets == []

    def test_non_seeded_pages_pass_through_unmodified(self):
        """Pages with non-operation roles pass through without modification."""
        snippets = [_make_snippet()]
        db = _make_extraction_db([_make_snippet_fact("convert", 0)])
        landing = _make_page("p/landing", "landing")
        api_ref = _make_page("p/api", "api_reference")
        pages = [landing, api_ref]
        result = _seed(pages, snippets, db)

        assert result[0].assigned_snippets == []
        assert result[1].assigned_snippets == []

"""Unit tests for TC-3877 — snippet-driven claim extraction enrichment."""
from __future__ import annotations

import pytest

from launcher.models.claims import Snippet
from launcher.workers.understand.extract import (
    _SNIPPET_CHAR_BUDGET,
    _SNIPPET_SAMPLE_MAX,
    _build_snippet_context,
)


def _make_snippet(code: str, language: str = "python") -> Snippet:
    return Snippet(code=code, language=language)


class TestBuildSnippetContextEmpty:
    def test_empty_list_returns_empty_string(self) -> None:
        result = _build_snippet_context([])
        assert result == ""

    def test_none_equivalent_empty_list(self) -> None:
        # Calling with empty is the documented contract
        result = _build_snippet_context([])
        assert result == ""


class TestBuildSnippetContextBasic:
    def test_single_snippet_returns_block(self) -> None:
        s = _make_snippet("import aspose_cells_foss as ac\nwb = ac.Workbook()")
        result = _build_snippet_context([s])
        assert "CODE EXAMPLES" in result
        assert "```python" in result
        assert "ac.Workbook()" in result

    def test_header_present(self) -> None:
        s = _make_snippet("x = 1")
        result = _build_snippet_context([s])
        assert "CODE EXAMPLES" in result
        assert "api" in result.lower()  # instructions mention api-kind claims

    def test_multiple_snippets_joined(self) -> None:
        snippets = [_make_snippet(f"x = {i}") for i in range(5)]
        result = _build_snippet_context(snippets)
        for i in range(5):
            assert f"x = {i}" in result


class TestBuildSnippetContextDeduplication:
    def test_exact_duplicate_included_once(self) -> None:
        code = "import aspose_cells_foss as ac"
        s1 = _make_snippet(code)
        s2 = _make_snippet(code)
        result = _build_snippet_context([s1, s2])
        assert result.count("import aspose_cells_foss as ac") == 1

    def test_dedup_by_full_sha256(self) -> None:
        # TC-4210: deduplication now uses SHA-256 of the full code string.
        # Two snippets that share the same first 200 chars but differ after
        # must BOTH appear in the output (they have different SHA-256 hashes).
        prefix = "a" * 200
        s1 = _make_snippet(prefix + "SUFFIX_A")
        s2 = _make_snippet(prefix + "SUFFIX_B")
        result = _build_snippet_context([s1, s2])
        # Both snippets are distinct by SHA-256 — both must survive dedup
        assert "SUFFIX_A" in result
        assert "SUFFIX_B" in result

    def test_distinct_snippets_all_included(self) -> None:
        snippets = [_make_snippet(f"code_block_{i}") for i in range(5)]
        result = _build_snippet_context(snippets)
        for i in range(5):
            assert f"code_block_{i}" in result


class TestBuildSnippetContextCharCap:
    def test_char_budget_respected(self) -> None:
        # Each snippet is ~200 chars; budget is 8000 chars
        large_code = "x = " + "a" * 196  # ~200 chars per snippet
        snippets = [_make_snippet(large_code + f"_{i}") for i in range(60)]
        result = _build_snippet_context(snippets)
        # Total snippet block content should not grossly exceed budget
        # (header adds ~50 chars, so allow some headroom)
        assert len(result) <= _SNIPPET_CHAR_BUDGET + 200

    def test_stops_at_sample_max(self) -> None:
        # Small snippets that easily fit in budget
        snippets = [_make_snippet(f"x{i} = {i}") for i in range(100)]
        result = _build_snippet_context(snippets)
        # Count occurrences of ```python — each snippet starts with one
        count = result.count("```python")
        assert count <= _SNIPPET_SAMPLE_MAX

    def test_snippet_exceeding_budget_not_added(self) -> None:
        # First snippet is small (fits)
        small = _make_snippet("x = 1")
        # Second snippet is huge (won't fit)
        huge = _make_snippet("y = " + "z" * _SNIPPET_CHAR_BUDGET)
        result = _build_snippet_context([small, huge])
        assert "x = 1" in result
        # The huge snippet starts with "y = zzz..." — should not appear
        assert "y = " + "z" * 10 not in result


class TestBuildSnippetContextConstants:
    def test_sample_max_is_30(self) -> None:
        assert _SNIPPET_SAMPLE_MAX == 30

    def test_char_budget_is_3000(self) -> None:
        assert _SNIPPET_CHAR_BUDGET == 3_000


class TestSnippetBlockInSourceMaterial:
    """Verify _call_llm_extract appends snippet block via integration-style test."""

    def test_snippet_block_appended_to_source_material(self) -> None:
        """_build_snippet_context output is non-empty when snippets present."""
        snippets = [_make_snippet("wb = Workbook()"), _make_snippet("ws = wb.worksheets[0]")]
        block = _build_snippet_context(snippets)
        assert block != ""
        assert "Workbook()" in block

    def test_empty_snippets_produce_no_block(self) -> None:
        """Empty snippet list produces empty string — no pollution of source_material."""
        block = _build_snippet_context([])
        assert block == ""

    def test_source_material_unchanged_when_no_snippets(self) -> None:
        """Simulates the guard in _call_llm_extract: only append when non-empty."""
        source_material = "original content"
        snippet_block = _build_snippet_context([])
        if snippet_block:
            source_material = source_material + snippet_block
        assert source_material == "original content"

    def test_source_material_extended_when_snippets_present(self) -> None:
        """Simulates the guard in _call_llm_extract: appended when snippets present."""
        source_material = "original content"
        snippets = [_make_snippet("wb = Workbook()")]
        snippet_block = _build_snippet_context(snippets)
        if snippet_block:
            source_material = source_material + snippet_block
        assert source_material.startswith("original content")
        assert "CODE EXAMPLES" in source_material
        assert "Workbook()" in source_material

"""Tests for launcher.shared.keyword_research."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.shared.keyword_research import (
    KeywordResearchBundle,
    _assign_per_page_keywords,
    _deduplicate,
    _extract_claim_keywords,
    _extract_claim_texts,
    _generate_search_patterns,
    research_keywords,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def cache_root(tmp_path: Path) -> Path:
    return tmp_path / ".seo_cache"


@pytest.fixture()
def sample_claims() -> list[dict[str, str]]:
    return [
        {"text": "Supports reading and writing Excel XLSX files"},
        {"text": "Convert spreadsheets to PDF format using Python"},
        {"text": "Load CSV files and manipulate cell data programmatically"},
        {"text": "Export worksheets to HTML with formatting preserved"},
        {"text": "Performance optimized for large spreadsheet processing"},
    ]


# ------------------------------------------------------------------
# KeywordResearchBundle model
# ------------------------------------------------------------------


class TestKeywordResearchBundle:
    def test_defaults(self) -> None:
        bundle = KeywordResearchBundle()
        assert bundle.primary_keywords == []
        assert bundle.long_tail == []
        assert bundle.per_page == {}
        assert bundle.sources == {}
        assert bundle.gemini_available is False

    def test_serialization(self) -> None:
        bundle = KeywordResearchBundle(
            primary_keywords=["excel", "python"],
            long_tail=["convert xlsx to pdf python"],
            sources={"claims": ["excel", "xlsx"]},
        )
        data = bundle.model_dump()
        restored = KeywordResearchBundle.model_validate(data)
        assert restored.primary_keywords == ["excel", "python"]


# ------------------------------------------------------------------
# Claim text extraction
# ------------------------------------------------------------------


class TestExtractClaimTexts:
    def test_from_dicts(self, sample_claims: list[dict[str, str]]) -> None:
        texts = _extract_claim_texts(sample_claims)
        assert len(texts) == 5
        assert "Supports reading and writing Excel XLSX files" in texts

    def test_from_objects(self) -> None:
        class FakeClaim:
            def __init__(self, text: str) -> None:
                self.text = text

        claims = [FakeClaim("Claim one"), FakeClaim("Claim two")]
        texts = _extract_claim_texts(claims)
        assert texts == ["Claim one", "Claim two"]

    def test_empty(self) -> None:
        assert _extract_claim_texts([]) == []

    def test_mixed_dict_keys(self) -> None:
        claims = [{"claim_text": "From claim_text key"}]
        texts = _extract_claim_texts(claims)
        assert texts == ["From claim_text key"]


# ------------------------------------------------------------------
# Claim keyword extraction
# ------------------------------------------------------------------


class TestExtractClaimKeywords:
    def test_extracts_significant_words(self) -> None:
        texts = [
            "Supports reading and writing Excel XLSX files",
            "Convert spreadsheets to PDF format",
        ]
        keywords = _extract_claim_keywords(texts)
        assert "excel" in keywords
        assert "supports" in keywords
        assert "convert" in keywords
        # Stop words excluded.
        assert "and" not in keywords
        assert "the" not in keywords

    def test_frequency_ordering(self) -> None:
        texts = ["python python python excel excel cells"]
        keywords = _extract_claim_keywords(texts)
        assert keywords[0] == "python"  # Most frequent.
        assert keywords[1] == "excel"

    def test_max_20(self) -> None:
        texts = [" ".join(f"word{i}" for i in range(50))]
        keywords = _extract_claim_keywords(texts)
        assert len(keywords) <= 20

    def test_empty(self) -> None:
        assert _extract_claim_keywords([]) == []


# ------------------------------------------------------------------
# Search pattern generation
# ------------------------------------------------------------------


class TestGenerateSearchPatterns:
    def test_basic_patterns(self) -> None:
        patterns = _generate_search_patterns("Cells", "cells", "python", [])
        assert any("install" in p for p in patterns)
        assert any("tutorial" in p for p in patterns)
        assert any("api reference" in p for p in patterns)

    def test_verb_extraction(self) -> None:
        claim_texts = ["Convert files to PDF format"]
        patterns = _generate_search_patterns("Cells", "cells", "python", claim_texts)
        assert any("convert" in p for p in patterns)

    def test_deduplicated(self) -> None:
        patterns = _generate_search_patterns("Cells", "cells", "python", [])
        assert len(patterns) == len(set(p.lower() for p in patterns))


# ------------------------------------------------------------------
# Per-page assignment
# ------------------------------------------------------------------


class TestAssignPerPageKeywords:
    def test_assigns_to_known_slugs(self) -> None:
        keywords = ["install python", "api reference guide", "troubleshoot errors"]
        per_page = _assign_per_page_keywords(keywords, "cells", "python")
        assert "installation" in per_page
        assert "install python" in per_page["installation"]
        assert "api-overview" in per_page
        assert "api reference guide" in per_page["api-overview"]

    def test_base_keywords_always_present(self) -> None:
        per_page = _assign_per_page_keywords([], "cells", "python")
        for slug_kws in per_page.values():
            assert "cells" in slug_kws
            assert "python" in slug_kws

    def test_capped_at_8(self) -> None:
        keywords = [f"install keyword {i}" for i in range(20)]
        per_page = _assign_per_page_keywords(keywords, "cells", "python")
        for slug_kws in per_page.values():
            assert len(slug_kws) <= 8


# ------------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------------


class TestDeduplicate:
    def test_removes_duplicates(self) -> None:
        assert _deduplicate(["a", "A", "b", "B"]) == ["a", "b"]

    def test_preserves_order(self) -> None:
        assert _deduplicate(["c", "a", "b"]) == ["c", "a", "b"]

    def test_strips_whitespace(self) -> None:
        assert _deduplicate(["  hello  ", "hello"]) == ["hello"]

    def test_empty(self) -> None:
        assert _deduplicate([]) == []


# ------------------------------------------------------------------
# Full research_keywords (offline / local only)
# ------------------------------------------------------------------


class TestResearchKeywordsOffline:
    def test_offline_mode(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
        )
        assert isinstance(bundle, KeywordResearchBundle)
        assert bundle.gemini_available is False
        # Should have claims + patterns sources.
        assert "claims" in bundle.sources
        assert "patterns" in bundle.sources
        # Should NOT have trends, suggest, gemini.
        assert "trends" not in bundle.sources
        assert "suggest" not in bundle.sources
        assert "gemini" not in bundle.sources

    def test_offline_produces_keywords(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
        )
        assert len(bundle.primary_keywords) > 0
        assert bundle.cached_at != ""

    def test_no_claims_still_works(self, cache_root: Path) -> None:
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=[],
            cache_root=cache_root,
            offline=True,
        )
        assert isinstance(bundle, KeywordResearchBundle)
        # Patterns should still produce keywords.
        assert "patterns" in bundle.sources

    def test_per_page_populated(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
        )
        assert len(bundle.per_page) > 0
        assert "installation" in bundle.per_page

    def test_cache_populated(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
        )
        # Cache dir should exist with files.
        cache_dir = cache_root / "cells" / "python"
        assert cache_dir.exists()

    def test_primary_capped_at_8(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
        )
        assert len(bundle.primary_keywords) <= 8

    def test_long_tail_are_multi_word(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
        )
        for kw in bundle.long_tail:
            assert len(kw.split()) >= 3, f"Long-tail keyword '{kw}' has < 3 words"


# ------------------------------------------------------------------
# Degradation: no Gemini key
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# Family-specific Trends queries (SEO-10)
# ------------------------------------------------------------------


class TestTrendsQueries:
    @patch("launcher.shared.keyword_research._fetch_trends_keywords")
    def test_trends_uses_family_terms_for_known_family(
        self, mock_fetch: MagicMock, cache_root: Path, sample_claims: list[dict[str, str]],
    ) -> None:
        """Trends source is called when online (not offline)."""
        mock_fetch.return_value = ["python excel", "openpyxl"]
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=False,
        )
        mock_fetch.assert_called_once()
        assert "trends" in bundle.sources

    @patch("launcher.shared.keyword_research._fetch_trends_keywords")
    def test_trends_empty_results_still_produces_bundle(
        self, mock_fetch: MagicMock, cache_root: Path, sample_claims: list[dict[str, str]],
    ) -> None:
        """Empty trends results don't crash; bundle still has other sources."""
        mock_fetch.return_value = []
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=False,
        )
        assert "trends" not in bundle.sources  # Empty = not added.
        assert "claims" in bundle.sources
        assert "patterns" in bundle.sources

    def test_family_trend_terms_known_families(self) -> None:
        """Known families have broader queries defined."""
        from launcher.shared.keyword_research import _FAMILY_TREND_TERMS

        assert "cells" in _FAMILY_TREND_TERMS
        assert "python excel" in _FAMILY_TREND_TERMS["cells"]
        assert "pdf" in _FAMILY_TREND_TERMS
        assert "words" in _FAMILY_TREND_TERMS

    def test_family_trend_terms_unknown_family_not_present(self) -> None:
        """Unknown families are not in the map (fallback handled in function)."""
        from launcher.shared.keyword_research import _FAMILY_TREND_TERMS

        assert "unknown_product" not in _FAMILY_TREND_TERMS


# ------------------------------------------------------------------
# Degradation: no Gemini key
# ------------------------------------------------------------------


class TestDegradation:
    def test_no_gemini_key(self, cache_root: Path, sample_claims: list[dict[str, str]]) -> None:
        """Without Gemini key, should still produce results from other sources."""
        bundle = research_keywords(
            product_name="Aspose.Cells FOSS for Python",
            family="cells",
            platform="python",
            claims=sample_claims,
            cache_root=cache_root,
            offline=True,
            gemini_api_key="",
        )
        assert bundle.gemini_available is False
        assert len(bundle.primary_keywords) > 0

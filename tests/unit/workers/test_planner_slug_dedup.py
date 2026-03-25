"""TC-5157: Tests for planner semantic slug deduplication."""
from __future__ import annotations

import pytest

from launcher.workers.planner.plan import (
    _normalize_slug_for_dedup,
    _dedup_pages_by_normalized_slug,
)


class TestNormalizeSlugForDedup:
    """Test slug normalization for dedup comparison."""

    def test_strips_in_python_suffix(self):
        assert _normalize_slug_for_dedup("load-3d-models-in-python") == "load-3d-models"

    def test_strips_python_suffix(self):
        assert _normalize_slug_for_dedup("load-3d-models-python") == "load-3d-models"

    def test_strips_for_python_suffix(self):
        assert _normalize_slug_for_dedup("load-3d-models-for-python") == "load-3d-models"

    def test_strips_typescript_suffix(self):
        assert _normalize_slug_for_dedup("load-models-in-typescript") == "load-models"

    def test_strips_how_to_prefix(self):
        assert _normalize_slug_for_dedup("how-to-load-models") == "load-models"

    def test_strips_both_prefix_and_suffix(self):
        assert _normalize_slug_for_dedup("how-to-load-3d-models-in-python") == "load-3d-models"

    def test_near_identical_slugs_normalize_equal(self):
        a = _normalize_slug_for_dedup("how-to-load-3d-models-in-python")
        b = _normalize_slug_for_dedup("how-to-load-3d-models-python")
        assert a == b

    def test_case_insensitive(self):
        assert _normalize_slug_for_dedup("Load-Models-In-Python") == "load-models"

    def test_no_suffix_unchanged(self):
        assert _normalize_slug_for_dedup("faq") == "faq"

    def test_index_slug_unchanged(self):
        assert _normalize_slug_for_dedup("_index") == "_index"

    def test_distinct_topics_remain_distinct(self):
        a = _normalize_slug_for_dedup("convert-csv-to-json-python")
        b = _normalize_slug_for_dedup("convert-xlsx-to-pdf-python")
        assert a != b


class TestDedupPagesByNormalizedSlug:
    """Test semantic dedup of page lists."""

    def _make_page(
        self, slug: str, page_role: str = "howto_article",
        mandatory: bool = False, n_claims: int = 0,
    ) -> dict:
        return {
            "page_id": f"kb/{slug}",
            "slug": slug,
            "page_role": page_role,
            "mandatory": mandatory,
            "assigned_claims": [f"c{i}" for i in range(n_claims)],
            "title": slug.replace("-", " ").title(),
        }

    def test_no_duplicates_unchanged(self):
        pages = [
            self._make_page("convert-csv-to-json-python"),
            self._make_page("load-spreadsheets-python"),
        ]
        result = _dedup_pages_by_normalized_slug(pages)
        assert len(result) == 2

    def test_removes_duplicate_keeps_richer(self):
        pages = [
            self._make_page("how-to-load-3d-models-in-python", n_claims=3),
            self._make_page("how-to-load-3d-models-python", n_claims=5),
        ]
        result = _dedup_pages_by_normalized_slug(pages)
        assert len(result) == 1
        assert result[0]["slug"] == "how-to-load-3d-models-python"  # richer

    def test_different_roles_not_merged(self):
        pages = [
            self._make_page("faq", page_role="faq", n_claims=3),
            self._make_page("faq", page_role="troubleshooting", n_claims=5),
        ]
        result = _dedup_pages_by_normalized_slug(pages)
        assert len(result) == 2  # different roles, not merged

    def test_mandatory_never_dropped(self):
        pages = [
            self._make_page("load-models-python", mandatory=True, n_claims=1),
            self._make_page("load-models-in-python", mandatory=False, n_claims=10),
        ]
        result = _dedup_pages_by_normalized_slug(pages)
        # Mandatory is never dropped — both may be kept, or mandatory wins
        mandatory_pages = [p for p in result if p["mandatory"]]
        assert len(mandatory_pages) >= 1

    def test_three_way_dedup(self):
        pages = [
            self._make_page("load-models-python", n_claims=1),
            self._make_page("load-models-in-python", n_claims=5),
            self._make_page("how-to-load-models-for-python", n_claims=3),
        ]
        result = _dedup_pages_by_normalized_slug(pages)
        assert len(result) == 1
        assert result[0]["slug"] == "load-models-in-python"  # richest

    def test_empty_input(self):
        assert _dedup_pages_by_normalized_slug([]) == []

    def test_single_page(self):
        pages = [self._make_page("faq")]
        result = _dedup_pages_by_normalized_slug(pages)
        assert len(result) == 1

    def test_preserves_order(self):
        pages = [
            self._make_page("aaa-python", page_role="howto_article", n_claims=3),
            self._make_page("zzz-python", page_role="howto_article", n_claims=3),
            self._make_page("mmm-python", page_role="howto_article", n_claims=3),
        ]
        result = _dedup_pages_by_normalized_slug(pages)
        assert len(result) == 3
        slugs = [p["slug"] for p in result]
        assert slugs == ["aaa-python", "zzz-python", "mmm-python"]

"""Tests for _shared.slug_constants module (TC-2601).

Validates the canonical family keyword map, topic category map,
REQUIRED_TOPIC_CATEGORIES derivation, and extract_family_keyword()
with and without family_capabilities registry override.
"""

from __future__ import annotations

import pytest

from src.launch.workers._shared.slug_constants import (
    FAMILY_KEYWORD_MAP,
    TOPIC_CATEGORY_MAP,
    REQUIRED_TOPIC_CATEGORIES,
    extract_family_keyword,
)


# ---------------------------------------------------------------------------
# FAMILY_KEYWORD_MAP
# ---------------------------------------------------------------------------


class TestFamilyKeywordMap:
    """Verify the canonical family keyword map contents."""

    def test_contains_3d(self):
        assert FAMILY_KEYWORD_MAP["3d"] == "3d-models"

    def test_contains_threed_alias(self):
        assert FAMILY_KEYWORD_MAP["threed"] == "3d-models"

    def test_contains_cells(self):
        assert FAMILY_KEYWORD_MAP["cells"] == "spreadsheets"

    def test_contains_note(self):
        assert FAMILY_KEYWORD_MAP["note"] == "notebooks"

    def test_contains_words(self):
        assert FAMILY_KEYWORD_MAP["words"] == "documents"

    def test_contains_pdf(self):
        assert FAMILY_KEYWORD_MAP["pdf"] == "pdf-files"

    def test_contains_slides(self):
        assert FAMILY_KEYWORD_MAP["slides"] == "presentations"

    def test_contains_imaging(self):
        assert FAMILY_KEYWORD_MAP["imaging"] == "images"


# ---------------------------------------------------------------------------
# TOPIC_CATEGORY_MAP
# ---------------------------------------------------------------------------


class TestTopicCategoryMap:
    """Verify the canonical topic category map contents."""

    def test_open_maps_to_load_file(self):
        assert TOPIC_CATEGORY_MAP["open"] == "load_file"

    def test_load_maps_to_load_file(self):
        assert TOPIC_CATEGORY_MAP["load"] == "load_file"

    def test_save_maps_to_save_file(self):
        assert TOPIC_CATEGORY_MAP["save"] == "save_file"

    def test_convert_maps_to_convert_formats(self):
        assert TOPIC_CATEGORY_MAP["convert"] == "convert_formats"

    def test_fix_maps_to_troubleshoot(self):
        assert TOPIC_CATEGORY_MAP["fix"] == "troubleshoot"

    def test_performance_maps_to_optimize(self):
        assert TOPIC_CATEGORY_MAP["performance"] == "optimize_performance"


# ---------------------------------------------------------------------------
# REQUIRED_TOPIC_CATEGORIES (derived from map — cannot drift)
# ---------------------------------------------------------------------------


class TestRequiredTopicCategories:
    """Verify REQUIRED_TOPIC_CATEGORIES is derived from TOPIC_CATEGORY_MAP."""

    def test_is_frozenset(self):
        assert isinstance(REQUIRED_TOPIC_CATEGORIES, frozenset)

    def test_contains_all_five_categories(self):
        expected = {
            "load_file",
            "save_file",
            "convert_formats",
            "troubleshoot",
            "optimize_performance",
        }
        assert REQUIRED_TOPIC_CATEGORIES == expected

    def test_derived_from_map_values(self):
        """REQUIRED_TOPIC_CATEGORIES must exactly equal the set of map values."""
        assert REQUIRED_TOPIC_CATEGORIES == frozenset(set(TOPIC_CATEGORY_MAP.values()))

    def test_count_is_five(self):
        assert len(REQUIRED_TOPIC_CATEGORIES) == 5


# ---------------------------------------------------------------------------
# extract_family_keyword() — without registry
# ---------------------------------------------------------------------------


class TestExtractFamilyKeywordNoRegistry:
    """Test extract_family_keyword() without family_capabilities."""

    def test_3d_slug(self):
        assert extract_family_keyword("3d") == "3d-models"

    def test_cells_slug(self):
        assert extract_family_keyword("cells") == "spreadsheets"

    def test_note_slug(self):
        assert extract_family_keyword("note") == "notebooks"

    def test_words_slug(self):
        assert extract_family_keyword("words") == "documents"

    def test_pdf_slug(self):
        assert extract_family_keyword("pdf") == "pdf-files"

    def test_slides_slug(self):
        assert extract_family_keyword("slides") == "presentations"

    def test_imaging_slug(self):
        assert extract_family_keyword("imaging") == "images"

    def test_unknown_fallback(self):
        assert extract_family_keyword("barcode") == "files"

    def test_case_insensitive(self):
        assert extract_family_keyword("Cells") == "spreadsheets"
        assert extract_family_keyword("3D") == "3d-models"

    def test_substring_match(self):
        """Product slugs like 'aspose-3d-python' should match '3d'."""
        assert extract_family_keyword("aspose-3d-python") == "3d-models"

    def test_empty_slug_fallback(self):
        assert extract_family_keyword("") == "files"


# ---------------------------------------------------------------------------
# extract_family_keyword() — with registry override
# ---------------------------------------------------------------------------


class TestExtractFamilyKeywordWithRegistry:
    """Test extract_family_keyword() with family_capabilities registry."""

    def test_registry_keyword_overrides_map(self):
        registry = {"keyword": "custom-models"}
        assert extract_family_keyword("3d", registry) == "custom-models"

    def test_registry_with_empty_keyword_falls_back(self):
        registry = {"keyword": ""}
        assert extract_family_keyword("3d", registry) == "3d-models"

    def test_registry_without_keyword_field_falls_back(self):
        registry = {"family": "3d"}
        assert extract_family_keyword("3d", registry) == "3d-models"

    def test_none_registry_uses_map(self):
        assert extract_family_keyword("cells", None) == "spreadsheets"

    def test_registry_overrides_for_unknown_family(self):
        registry = {"keyword": "barcodes"}
        assert extract_family_keyword("barcode", registry) == "barcodes"

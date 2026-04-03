"""Tests for TC-HEAL-005 and TC-SEO-602: seo_metadata keyword filtering.

Verifies that _is_irrelevant_keyword() correctly rejects question-pattern and
comparison keywords while accepting product-relevant terms.
Also verifies _enhance_keywords() frequency threshold (TC-SEO-602).
"""
from __future__ import annotations

import pytest

from launcher.workers.generate.seo_metadata import _enhance_keywords, _is_irrelevant_keyword


class TestIsIrrelevantKeyword:
    """TC-HEAL-005: _is_irrelevant_keyword() reject/accept classification."""

    # --- Reject cases (bad keywords that must be filtered) ---

    def test_question_pattern_is_rejected(self):
        """'is .net 3.5 safe' starts with question word → rejected."""
        assert _is_irrelevant_keyword("is .net 3.5 safe") is True

    def test_cost_keyword_rejected(self):
        """'shapr 3d cost' contains cost → rejected."""
        assert _is_irrelevant_keyword("shapr 3d cost") is True

    def test_difference_between_rejected(self):
        """'difference between dotnet and dotnet framework' → rejected."""
        assert _is_irrelevant_keyword("difference between dotnet and dotnet framework") is True

    def test_symptom_keyword_rejected(self):
        """'3d symptoms' contains symptom word → rejected."""
        assert _is_irrelevant_keyword("3d symptoms") is True

    def test_how_question_rejected(self):
        """'how to open obj file' starts with question word → rejected."""
        assert _is_irrelevant_keyword("how to open obj file") is True

    def test_pricing_keyword_rejected(self):
        """'aspose cells pricing' contains pricing → rejected."""
        assert _is_irrelevant_keyword("aspose cells pricing") is True

    def test_vs_comparison_rejected(self):
        """'aspose vs openpyxl' contains 'vs ' → rejected."""
        assert _is_irrelevant_keyword("aspose vs openpyxl") is True

    def test_safe_word_rejected(self):
        """'is this library safe to use' → rejected via question-opener ('is '), NOT \bsafe\b.

        SR-01: \bsafe\b was removed because it caused false positives on legitimate doc
        keywords like 'thread-safe', 'type-safe'. The question-opener pattern handles
        this case (starts with 'is ').
        """
        assert _is_irrelevant_keyword("is this library safe to use") is True

    def test_alternative_keyword_rejected(self):
        """'aspose alternative open source' contains alternative → rejected."""
        assert _is_irrelevant_keyword("aspose alternative open source") is True

    # --- Accept cases (product-relevant keywords that must NOT be filtered) ---

    def test_product_library_keyword_accepted(self):
        """'dotnet 3d library' is product-relevant → accepted."""
        assert _is_irrelevant_keyword("dotnet 3d library") is False

    def test_aspose_model_loading_accepted(self):
        """'aspose 3d model loading' is product-relevant → accepted."""
        assert _is_irrelevant_keyword("aspose 3d model loading") is False

    def test_python_spreadsheet_api_accepted(self):
        """'python spreadsheet api' is product-relevant → accepted."""
        assert _is_irrelevant_keyword("python spreadsheet api") is False

    def test_csharp_3d_conversion_accepted(self):
        """'csharp 3d file conversion' is product-relevant → accepted."""
        assert _is_irrelevant_keyword("csharp 3d file conversion") is False

    def test_java_slides_export_accepted(self):
        """'java slides export pptx' is product-relevant → accepted."""
        assert _is_irrelevant_keyword("java slides export pptx") is False

    def test_vs_without_trailing_space_accepted(self):
        """'aspose.cells vs.' (no trailing space after vs) → accepted (edge case)."""
        # The pattern requires 'vs ' (with space) so 'vs.' at end-of-string is safe
        assert _is_irrelevant_keyword("aspose.cells vs.") is False

    def test_thread_safe_keyword_accepted(self):
        """SR-01 regression: 'thread-safe programming' must NOT be rejected.

        \bsafe\b was removed because it matched hyphenated compound words like
        thread-safe, type-safe, fail-safe — all legitimate product doc keywords.
        """
        assert _is_irrelevant_keyword("thread-safe programming") is False

    def test_type_safe_keyword_accepted(self):
        """SR-01 regression: 'type-safe operations' must NOT be rejected."""
        assert _is_irrelevant_keyword("type-safe operations") is False

    def test_memory_safe_keyword_accepted(self):
        """SR-01 regression: 'memory safe code generation' must NOT be rejected."""
        assert _is_irrelevant_keyword("memory safe code generation") is False


class TestEnhanceKeywordsFrequencyThreshold:
    """TC-SEO-602: _enhance_keywords() must require word_freq >= 2 for claim-derived terms."""

    def _make_claim(self, text: str) -> object:
        from launcher.models.claims import Claim
        return Claim(claim_id="c1", text=text, kind="feature")

    def test_single_occurrence_word_excluded(self):
        """TC-SEO-602: word appearing in only 1 claim is NOT added as keyword."""
        # "voronoi" appears only once; should not be added
        claims = [
            self._make_claim("voronoi diagram support for specialized charts"),
            self._make_claim("spreadsheet workbook loading from bytes"),
            self._make_claim("worksheet column width adjustment"),
        ]
        result = _enhance_keywords([], claims, "cells")
        assert "voronoi" not in result

    def test_repeated_word_included(self):
        """TC-SEO-602: word appearing in >= 2 claims IS added as keyword."""
        claims = [
            self._make_claim("workbook loading from bytes stream"),
            self._make_claim("workbook saving with password encryption"),
            self._make_claim("worksheet column width adjustment"),
        ]
        result = _enhance_keywords([], claims, "cells")
        assert "workbook" in result

    def test_planner_keywords_unaffected_by_threshold(self):
        """TC-SEO-602: planner-supplied keywords bypass the frequency filter."""
        claims = [self._make_claim("some claim text about spreadsheets")]
        result = _enhance_keywords(["excel python library"], claims, "cells")
        assert "excel python library" in result

    def test_empty_claims_yields_no_claim_keywords(self):
        """TC-SEO-602: no claim words → no crash, list is empty (except family_kw)."""
        result = _enhance_keywords([], [], "cells")
        # Only family keyword should be present
        assert isinstance(result, list)
        assert len(result) <= 1  # at most family_kw

"""Tests for TC-HO-05: conversion_pairs injection for conversion headings."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="threed", platform="python",
        display_name="Aspose.3D", canonical_import="aspose_threed",
        repo_url="https://example.com",
    )


def _make_page() -> PlannedPage:
    return PlannedPage(
        page_id="test-page",
        page_role="how_to_convert",
        title="Convert FBX to GLTF",
        assigned_claims=["CLM-001"],
    )


def _make_section(heading: str) -> SkeletonSection:
    return SkeletonSection(heading=heading, level=2, required=True, content_hint="desc", min_words=30, max_words=300)


def _make_claim() -> Claim:
    return Claim(
        claim_id="CLM-001",
        text="Supports FBX to GLTF conversion.",
        kind="api",
        evidence=[],
    )


class TestFormatConversionPairs:
    """Unit tests for _format_conversion_pairs helper."""

    def test_conversion_heading_with_pairs(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "FBX", "target": "GLTF"}, {"source": "OBJ", "target": "STL"}]
        result = _format_conversion_pairs(pairs, "Convert FBX Files")
        assert "SUPPORTED CONVERSION PAIRS" in result
        assert "FBX" in result
        assert "GLTF" in result
        assert "\u2192" in result  # arrow character

    def test_export_heading_matches(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "PDF", "target": "DOCX"}]
        result = _format_conversion_pairs(pairs, "Export to Word")
        assert "SUPPORTED CONVERSION PAIRS" in result

    def test_transform_heading_matches(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "A", "target": "B"}]
        result = _format_conversion_pairs(pairs, "Transform Data")
        assert "SUPPORTED CONVERSION PAIRS" in result

    def test_save_as_heading_matches(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "X", "target": "Y"}]
        result = _format_conversion_pairs(pairs, "Save as PDF")
        assert "SUPPORTED CONVERSION PAIRS" in result

    def test_output_heading_matches(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "A", "target": "B"}]
        result = _format_conversion_pairs(pairs, "Output Formats")
        assert "SUPPORTED CONVERSION PAIRS" in result

    def test_non_conversion_heading_no_injection(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "FBX", "target": "GLTF"}]
        result = _format_conversion_pairs(pairs, "Overview")
        assert result == ""

    def test_prerequisites_heading_no_injection(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "A", "target": "B"}]
        result = _format_conversion_pairs(pairs, "Prerequisites")
        assert result == ""

    def test_none_pairs_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        assert _format_conversion_pairs(None, "Convert Files") == ""

    def test_empty_pairs_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        assert _format_conversion_pairs([], "Convert Files") == ""

    def test_caps_at_eight_pairs(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": f"SRC{i}", "target": f"TGT{i}"} for i in range(12)]
        result = _format_conversion_pairs(pairs, "Convert Files")
        assert "SRC7" in result
        assert "SRC8" not in result

    def test_pairs_missing_source_or_target_skipped(self):
        from launcher.workers.generate.section_prompt import _format_conversion_pairs
        pairs = [{"source": "", "target": "PDF"}, {"source": "FBX", "target": ""}]
        result = _format_conversion_pairs(pairs, "Convert Files")
        assert result == ""  # no valid pairs → empty


class TestBuildSectionPromptConversionPairs:
    """Integration tests for conversion_pairs in build_section_prompt."""

    def test_conversion_heading_injects_pairs(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        pairs = [{"source": "FBX", "target": "GLTF"}]
        result = build_section_prompt(
            _make_section("Convert FBX to GLTF"), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], conversion_pairs=pairs,
        )
        assert "SUPPORTED CONVERSION PAIRS" in result
        assert "FBX" in result

    def test_non_conversion_heading_no_pairs(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        pairs = [{"source": "FBX", "target": "GLTF"}]
        result = build_section_prompt(
            _make_section("Overview"), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], conversion_pairs=pairs,
        )
        assert "SUPPORTED CONVERSION PAIRS" not in result

    def test_none_pairs_no_block(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        result = build_section_prompt(
            _make_section("Convert FBX to GLTF"), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], conversion_pairs=None,
        )
        assert "SUPPORTED CONVERSION PAIRS" not in result

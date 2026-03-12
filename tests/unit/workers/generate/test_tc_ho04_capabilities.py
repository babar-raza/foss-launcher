"""Tests for TC-HO-04: capabilities injection into section prompt."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="note", platform="python",
        display_name="Aspose.Note", canonical_import="aspose_note_foss",
        repo_url="https://example.com",
    )


def _make_page(**overrides) -> PlannedPage:
    defaults = dict(
        page_id="test-page",
        page_role="howto_article",
        title="Test Page",
        assigned_claims=["CLM-001"],
    )
    defaults.update(overrides)
    return PlannedPage(**defaults)


def _make_section(heading: str = "Overview") -> SkeletonSection:
    return SkeletonSection(heading=heading, level=2, required=True, content_hint="desc", min_words=30, max_words=300)


def _make_claim(claim_id: str = "CLM-001") -> Claim:
    return Claim(
        claim_id=claim_id,
        text="Supports OneNote files.",
        kind="api",
        evidence=[],
    )


class TestFormatCapabilities:
    """Unit tests for _format_capabilities helper."""

    def test_non_empty_caps_returns_block(self):
        from launcher.workers.generate.section_prompt import _format_capabilities
        caps = [
            {"text": "Load OneNote documents from disk", "source": "README"},
            {"text": "Save to PDF format", "source": "README"},
        ]
        result = _format_capabilities(caps)
        assert "PRODUCT CAPABILITIES" in result
        assert "Load OneNote documents from disk" in result
        assert "Save to PDF format" in result

    def test_caps_at_five_entries(self):
        from launcher.workers.generate.section_prompt import _format_capabilities
        caps = [{"text": f"Cap {i}"} for i in range(10)]
        result = _format_capabilities(caps)
        # Should only include first 5
        assert "Cap 4" in result
        assert "Cap 5" not in result

    def test_none_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_capabilities
        assert _format_capabilities(None) == ""

    def test_empty_list_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_capabilities
        assert _format_capabilities([]) == ""

    def test_missing_text_key_handled_gracefully(self):
        from launcher.workers.generate.section_prompt import _format_capabilities
        caps = [{"description": "no text key here"}]
        result = _format_capabilities(caps)
        assert result == ""  # no valid text → empty block

    def test_caps_with_only_empty_text_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_capabilities
        caps = [{"text": ""}]
        assert _format_capabilities(caps) == ""


class TestBuildSectionPromptCapabilities:
    """Integration tests: build_section_prompt with capabilities parameter."""

    def test_capabilities_block_in_prompt(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        caps = [{"text": "Convert OBJ to FBX"}, {"text": "Supports UTF-8 encoding"}]
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], capabilities=caps,
        )
        assert "PRODUCT CAPABILITIES" in result
        assert "Convert OBJ to FBX" in result
        assert "Supports UTF-8 encoding" in result

    def test_capabilities_none_no_block(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], capabilities=None,
        )
        assert "PRODUCT CAPABILITIES" not in result

    def test_capabilities_empty_list_no_block(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], capabilities=[],
        )
        assert "PRODUCT CAPABILITIES" not in result

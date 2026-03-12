"""Tests for TC-HO-06: missing_info DO NOT CLAIM guard injection."""
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


def _make_page() -> PlannedPage:
    return PlannedPage(
        page_id="test-page",
        page_role="howto_article",
        title="Test Page",
        assigned_claims=["CLM-001"],
    )


def _make_section() -> SkeletonSection:
    return SkeletonSection(heading="Installation", level=2, required=True, content_hint="desc", min_words=30, max_words=300)


def _make_claim() -> Claim:
    return Claim(
        claim_id="CLM-001",
        text="Supports loading files.",
        kind="api",
        evidence=[],
    )


class TestFormatMissingInfo:
    """Unit tests for _format_missing_info helper."""

    def test_non_empty_missing_info_returns_block(self):
        from launcher.workers.generate.section_prompt import _format_missing_info
        from launcher.models.understanding import MissingInfoEntry
        entries = [
            MissingInfoEntry(field="format_matrix", reason="no tree-sitter grammar for Rust"),
            MissingInfoEntry(field="install_recipe", reason="no setup.py found"),
        ]
        result = _format_missing_info(entries)
        assert "DO NOT CLAIM OR INVENT" in result
        assert "format_matrix" in result
        assert "install_recipe" in result
        assert "no tree-sitter grammar for Rust" in result

    def test_none_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_missing_info
        assert _format_missing_info(None) == ""

    def test_empty_list_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_missing_info
        assert _format_missing_info([]) == ""

    def test_dict_entries_handled(self):
        from launcher.workers.generate.section_prompt import _format_missing_info
        entries = [{"field": "format_matrix", "reason": "extraction failed"}]
        result = _format_missing_info(entries)
        assert "DO NOT CLAIM OR INVENT" in result
        assert "format_matrix" in result

    def test_entry_without_reason_still_emits(self):
        from launcher.workers.generate.section_prompt import _format_missing_info
        from launcher.models.understanding import MissingInfoEntry
        entry = MissingInfoEntry(field="capabilities", reason="")
        result = _format_missing_info([entry])
        assert "DO NOT CLAIM OR INVENT: capabilities" in result

    def test_entries_without_field_skipped(self):
        from launcher.workers.generate.section_prompt import _format_missing_info
        entries = [{"reason": "no field name here"}]
        result = _format_missing_info(entries)
        assert result == ""


class TestBuildSectionPromptMissingInfo:
    """Integration tests for missing_info in build_section_prompt."""

    def test_missing_info_block_appears_near_top(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        from launcher.models.understanding import MissingInfoEntry
        entries = [MissingInfoEntry(field="install_recipe", reason="no pyproject.toml")]
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], missing_info=entries,
        )
        assert "DO NOT CLAIM OR INVENT" in result
        assert "install_recipe" in result
        # Block should appear near the top
        idx = result.index("DO NOT CLAIM OR INVENT")
        assert idx < 500, "DO NOT CLAIM block should appear near top of prompt"

    def test_none_missing_info_no_block(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], missing_info=None,
        )
        assert "DO NOT CLAIM OR INVENT" not in result

    def test_empty_missing_info_no_block(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], missing_info=[],
        )
        assert "DO NOT CLAIM OR INVENT" not in result

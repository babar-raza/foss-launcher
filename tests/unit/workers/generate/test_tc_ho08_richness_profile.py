"""Tests for TC-HO-08A: richness profile injection into section prompt."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier
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
    return SkeletonSection(heading="Overview", level=2, required=True, content_hint="desc", min_words=30, max_words=300)


def _make_claim() -> Claim:
    return Claim(
        claim_id="CLM-001",
        text="Supports OneNote.",
        kind="api",
        evidence=[],
    )


class TestFormatRichnessProfile:
    """Unit tests for _format_richness_profile helper."""

    def test_tier_a_returns_profile_block(self):
        from launcher.workers.generate.section_prompt import _format_richness_profile
        rt = RichnessResult(tier=RichnessTier.A, score=9, reason="rich docs; many examples", code_evidence_sparse=False)
        result = _format_richness_profile(rt)
        assert "REPOSITORY PROFILE" in result
        assert "Richness Tier: A" in result
        assert "rich docs" in result
        assert "many examples" in result

    def test_tier_c_sparse_includes_warning(self):
        from launcher.workers.generate.section_prompt import _format_richness_profile
        rt = RichnessResult(tier=RichnessTier.C, score=2, reason="minimal docs", code_evidence_sparse=True)
        result = _format_richness_profile(rt)
        assert "REPOSITORY PROFILE" in result
        assert "Richness Tier: C" in result
        assert "Do not fabricate code examples" in result

    def test_tier_c_not_sparse_no_fabrication_warning(self):
        from launcher.workers.generate.section_prompt import _format_richness_profile
        rt = RichnessResult(tier=RichnessTier.C, score=2, reason="minimal docs", code_evidence_sparse=False)
        result = _format_richness_profile(rt)
        assert "REPOSITORY PROFILE" in result
        assert "Do not fabricate code examples" not in result

    def test_none_returns_empty(self):
        from launcher.workers.generate.section_prompt import _format_richness_profile
        assert _format_richness_profile(None) == ""

    def test_reason_semicolon_split(self):
        from launcher.workers.generate.section_prompt import _format_richness_profile
        rt = RichnessResult(tier=RichnessTier.B, score=6, reason="good API docs; few examples; no tutorials", code_evidence_sparse=False)
        result = _format_richness_profile(rt)
        assert "good API docs" in result
        assert "few examples" in result
        assert "no tutorials" in result

    def test_tier_a_no_fabrication_warning(self):
        from launcher.workers.generate.section_prompt import _format_richness_profile
        rt = RichnessResult(tier=RichnessTier.A, score=9, reason="comprehensive", code_evidence_sparse=True)
        result = _format_richness_profile(rt)
        # Only Tier C gets the fabrication warning
        assert "Do not fabricate code examples" not in result


class TestBuildSectionPromptRichnessProfile:
    """Integration tests for richness_tier_obj in build_section_prompt."""

    def test_tier_c_sparse_adds_profile_and_warning(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        rt = RichnessResult(tier=RichnessTier.C, score=2, reason="minimal docs", code_evidence_sparse=True)
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], richness_tier_obj=rt,
        )
        assert "REPOSITORY PROFILE" in result
        assert "Do not fabricate code examples" in result

    def test_tier_a_adds_profile_no_warning(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        rt = RichnessResult(tier=RichnessTier.A, score=9, reason="comprehensive; many tests", code_evidence_sparse=False)
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], richness_tier_obj=rt,
        )
        assert "REPOSITORY PROFILE" in result
        assert "Do not fabricate code examples" not in result

    def test_none_richness_tier_no_profile(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], richness_tier_obj=None,
        )
        assert "REPOSITORY PROFILE" not in result

    def test_profile_block_near_top(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        rt = RichnessResult(tier=RichnessTier.B, score=6, reason="moderate docs", code_evidence_sparse=False)
        result = build_section_prompt(
            _make_section(), 0, 1, _make_page(), _make_product(),
            [_make_claim()], [], richness_tier_obj=rt,
        )
        idx = result.index("REPOSITORY PROFILE")
        assert idx < 800, "REPOSITORY PROFILE should appear near top of prompt"

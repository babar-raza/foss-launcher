"""FPRSR05SR-02: Unit tests for intro-quality directive injection in build_section_prompt.

Verifies FPRSR05SR-01: the directive:
- IS injected for getting_started pages at section_index == 0 (intro)
- is NOT injected for getting_started pages at section_index > 0 (non-intro sections)
- is NOT injected for non-getting-started page roles
- uses the real product display_name (not a literal '[product name]')
"""
from __future__ import annotations

import pytest

try:
    from launcher.workers.generate.section_prompt import build_section_prompt
    from launcher.models.plan import PlannedPage
    from launcher.models.product import ProductIdentity
    from launcher.shared.page_skeletons import SkeletonSection
    _HAS_BSP = True
except ImportError:
    _HAS_BSP = False


def _section(heading: str = "Introduction") -> "SkeletonSection":
    return SkeletonSection(
        heading=heading,
        level=2,
        required=True,
        content_hint="",
        min_words=0,
        max_words=0,
    )


def _page(page_role: str) -> "PlannedPage":
    return PlannedPage(
        page_id=f"test-{page_role}",
        page_role=page_role,
        title=f"Test {page_role}",
    )


def _product(display_name: str = "Aspose.Cells for Python") -> "ProductIdentity":
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name=display_name,
        canonical_import="aspose-cells-python",
        repo_url="https://example.com/repo",
    )


@pytest.mark.skipif(not _HAS_BSP, reason="build_section_prompt not importable")
class TestFPRSR05RouteDirective:
    """FPRSR05SR-02: Intro-quality directive injection behaviour."""

    def _call(self, page_role: str, section_index: int = 0, display_name: str = "Aspose.Cells for Python") -> str:
        return build_section_prompt(
            section=_section(),
            section_index=section_index,
            section_count=4,
            page=_page(page_role),
            product=_product(display_name),
            claims=[],
            snippets=[],
        )

    def test_directive_injected_for_intro_section(self):
        """Directive fires for getting_started at section_index=0."""
        result = self._call("getting_started", section_index=0)
        assert "INTRO QUALITY REQUIREMENT" in result

    def test_directive_uses_real_product_name_not_literal(self):
        """Directive contains the actual product display_name, not '[product name]'."""
        result = self._call("getting_started", section_index=0, display_name="Aspose.Slides for Python")
        assert "Aspose.Slides for Python" in result
        assert "[product name]" not in result

    def test_directive_not_injected_for_non_intro_sections(self):
        """Directive must NOT fire for section_index > 0 (System Requirements, etc.)."""
        for idx in (1, 2, 3):
            result = self._call("getting_started", section_index=idx)
            assert "INTRO QUALITY REQUIREMENT" not in result, f"Directive fired for section_index={idx}"

    def test_directive_not_injected_for_howto_role(self):
        """Directive must NOT fire for non-getting-started roles."""
        result = self._call("howto_article", section_index=0)
        assert "INTRO QUALITY REQUIREMENT" not in result

    def test_directive_not_injected_for_landing_role(self):
        """Directive must NOT fire for landing page role."""
        result = self._call("landing", section_index=0)
        assert "INTRO QUALITY REQUIREMENT" not in result

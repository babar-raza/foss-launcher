"""Tests for HG-11 evidence injection in build_section_prompt.

Verifies that:
- Known limitations from product_evidence are injected into the prompt
- API class identifier guard is injected to prevent hallucinated class names
- Both blocks are absent when input data is empty
- Both blocks are capped at reasonable lengths
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers — build minimal inputs for build_section_prompt
# ---------------------------------------------------------------------------

def _make_product(display_name: str = "TestLib", platform: str = "python"):
    from launcher.models.product import ProductIdentity
    return ProductIdentity(
        family="testlib",
        platform=platform,
        display_name=display_name,
        canonical_import="testlib",
        repo_url="https://github.com/example/testlib",
    )


def _make_page(page_role: str = "overview"):
    from launcher.models.plan import PlannedPage
    return PlannedPage(
        page_id="test-page",
        title="Test Page",
        page_role=page_role,
        assigned_claims=[],
        assigned_snippets=[],
        frontmatter={},
    )


def _make_section(heading: str = "Introduction"):
    from launcher.shared.page_skeletons import SkeletonSection
    return SkeletonSection(
        heading=heading,
        content_hint="Describe the product.",
        level=2,
        required=True,
        min_words=100,
        max_words=300,
    )


def _make_limitation(feature: str, constraint: str, status: str = "warning"):
    """Create a simple namespace object mimicking LimitationEntry."""
    class _Lim:
        pass
    lim = _Lim()
    lim.feature = feature
    lim.constraint = constraint
    lim.status = status
    return lim


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHG11EvidenceInjection:
    """HG-11: Limitations and API identifier guard injection into section prompt."""

    def test_limitations_block_appears_in_prompt(self):
        """Limitations from product_evidence are visible in the generated prompt."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        lims = [
            _make_limitation("FBX export", "not supported", "unsupported"),
            _make_limitation("Async operations", "experimental", "experimental"),
        ]

        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
            limitations=lims,
        )

        assert "KNOWN LIMITATIONS" in prompt, "Limitations header must appear in prompt"
        assert "FBX export" in prompt, "First limitation feature must appear"
        assert "not supported" in prompt, "First limitation constraint must appear"
        assert "Async operations" in prompt, "Second limitation feature must appear"
        assert "[unsupported]" in prompt, "Status tag must appear for unsupported"

    def test_limitations_block_absent_when_empty(self):
        """No limitations block when limitations list is empty."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
            limitations=[],
        )
        assert "KNOWN LIMITATIONS" not in prompt

    def test_limitations_block_absent_when_none(self):
        """No limitations block when limitations is None."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
            limitations=None,
        )
        assert "KNOWN LIMITATIONS" not in prompt

    def test_limitations_capped_at_ten(self):
        """Only 10 limitations are included even when more are provided."""
        from launcher.workers.generate.section_prompt import _format_limitations

        lims = [_make_limitation(f"Feature {i}", f"constraint {i}") for i in range(20)]
        result = _format_limitations(lims)
        # 10 bullet points max
        assert result.count("- Feature") == 10

    def test_api_ids_guard_appears_in_prompt(self):
        """Known API class names guard is injected when api_identifiers provided."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        identifiers = ["Scene", "Node", "Mesh", "Material", "ObjSaveOptions"]

        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(display_name="MyLib"), [], [],
            api_identifiers=identifiers,
        )

        assert "KNOWN API CLASSES FOR MYLIB" in prompt, "Guard header must appear"
        assert "Scene" in prompt, "Class name must appear in guard"
        assert "DO NOT invent" in prompt, "Prohibition language must appear"

    def test_api_ids_guard_absent_when_empty(self):
        """No API guard when api_identifiers is empty."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
            api_identifiers=[],
        )
        assert "KNOWN API CLASSES" not in prompt

    def test_api_ids_guard_capped_at_thirty(self):
        """API identifiers guard includes at most 30 names."""
        from launcher.workers.generate.section_prompt import _format_api_ids_guard

        # 50 capitalized class names
        ids = [f"Class{i}" for i in range(50)]
        result = _format_api_ids_guard(ids, "TestLib")
        # Count how many "Class" tokens appear
        parts = result.split(",")
        assert len(parts) <= 30, "Guard must be capped at 30 identifiers"

    def test_both_blocks_injected_together(self):
        """Both limitations and API guard can coexist in the same prompt."""
        from launcher.workers.generate.section_prompt import build_section_prompt

        lims = [_make_limitation("OBJ import", "read-only", "warning")]
        ids = ["Scene", "Node"]

        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
            limitations=lims,
            api_identifiers=ids,
        )
        assert "KNOWN LIMITATIONS" in prompt
        assert "KNOWN API CLASSES" in prompt
        assert "OBJ import" in prompt
        assert "Scene" in prompt


# ---------------------------------------------------------------------------
# HG-14: Format-option class pattern guard tests
# ---------------------------------------------------------------------------

class TestHG14HallucinationPrevention:
    """HG-14: Format-option class pattern guard in HALLUCINATION PREVENTION section."""

    def test_format_option_guard_in_template(self):
        """section_writer.txt HALLUCINATION PREVENTION contains format-option guard."""
        from pathlib import Path
        template_path = (
            Path(__file__).parents[4]
            / "src" / "launcher" / "prompts" / "section_writer.txt"
        )
        text = template_path.read_text(encoding="utf-8")
        assert "LoadOptions" in text, "Guard must mention LoadOptions pattern"
        assert "SaveOptions" in text, "Guard must mention SaveOptions pattern"

    def test_format_option_guard_in_prompt(self):
        """build_section_prompt() output includes format-option guard from template."""
        from launcher.workers.generate.section_prompt import build_section_prompt
        prompt = build_section_prompt(
            _make_section(), 0, 1,
            _make_page(), _make_product(), [], [],
        )
        assert "LoadOptions" in prompt, "Prompt must contain LoadOptions guard"
        assert "SaveOptions" in prompt, "Prompt must contain SaveOptions guard"

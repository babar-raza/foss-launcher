"""Unit tests for _gap_fill_code_block spec-driven + synthesis fallback (TC-DFR-007).

Verifies that:
1. Extracted snippets are still preferred (existing behavior)
2. Synthesis from API surface fires when no extracted snippets exist
3. Placeholder fallback still works when synthesis is unavailable
4. Sections with existing code blocks are not double-filled
5. Keyword-based trigger is preserved as fallback
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from launcher.models.claims import Snippet
from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.workers.generate.worker import _gap_fill_code_block


def _make_section(heading: str, blocks: list[BlockIR] | None = None) -> SectionIR:
    """Helper: create a SectionIR with the given heading and blocks."""
    return SectionIR(
        section_id=heading.lower().replace(" ", "_"),
        heading=heading,
        level=2,
        blocks=blocks or [BlockIR(type=BlockType.paragraph, content="Some prose content.")],
    )


def _make_product(**overrides):
    """Helper: create a mock ProductIdentity."""
    p = MagicMock()
    p.runtime_import = overrides.get("runtime_import", "aspose.cells")
    p.canonical_import = overrides.get("canonical_import", "aspose.cells")
    p.display_name = overrides.get("display_name", "Aspose.Cells")
    p.platform = overrides.get("platform", "python")
    return p


def _make_extracted_snippet(code: str = "wb = Workbook()\nwb.save('out.xlsx')") -> Snippet:
    """Helper: create an extracted snippet."""
    return Snippet(
        code=code,
        language="python",
        source_type="extracted",
        claim_ids=["c1"],
    )


# ---------------------------------------------------------------------------
# Existing behavior: extracted snippets preferred
# ---------------------------------------------------------------------------

class TestExtractedSnippetPreferred:
    """Extracted snippets are used when available (existing TC-3878 behavior)."""

    def test_extracted_snippet_used(self):
        """Section gets extracted snippet code, not placeholder."""
        section = _make_section("Quick Start")
        product = _make_product()
        snippet = _make_extracted_snippet()

        result = _gap_fill_code_block(section, product, [snippet])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "Workbook()" in code_blocks[0].content

    def test_extracted_snippet_has_section_label(self):
        """Extracted snippet gets section heading prepended (TC-5112)."""
        section = _make_section("Installation")
        product = _make_product()
        snippet = _make_extracted_snippet()

        result = _gap_fill_code_block(section, product, [snippet])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert code_blocks[0].content.startswith("# Installation")

    def test_non_extracted_snippet_skipped(self):
        """Snippets with source_type != 'extracted' are not used."""
        section = _make_section("Usage")
        product = _make_product()
        snippet = Snippet(
            code="synth code",
            language="python",
            source_type="synthetic",
            claim_ids=["c1"],
        )

        result = _gap_fill_code_block(section, product, [snippet])

        # Should fall through to placeholder (no synthesis api_surface provided)
        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "See API reference" in code_blocks[0].content


# ---------------------------------------------------------------------------
# TC-DFR-007: Synthesis fallback
# ---------------------------------------------------------------------------

class TestSynthesisFallback:
    """When no extracted snippets exist, synthesis from API surface is attempted."""

    def test_synthesis_fires_when_no_extracted_snippets(self):
        """With api_surface but no extracted snippets, synthesis is attempted."""
        section = _make_section("Quick Start")
        product = _make_product()
        api_surface = MagicMock()
        api_surface.class_briefs = [MagicMock(name="Workbook")]

        synth_snippet = MagicMock()
        synth_snippet.code = "from aspose.cells import Workbook\nwb = Workbook()"
        synth_snippet.language = "python"

        with patch(
            "launcher.workers.generate._code_synthesis.synthesize_section_snippet",
            return_value=synth_snippet,
        ) as mock_synth:
            result = _gap_fill_code_block(
                section, product, [],
                api_surface=api_surface,
                page_role="howto_article",
                claims=[],
            )

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "Workbook" in code_blocks[0].content

    def test_synthesis_skipped_when_no_api_surface(self):
        """Without api_surface, synthesis is not attempted — falls to placeholder."""
        section = _make_section("Implementation")
        product = _make_product()

        result = _gap_fill_code_block(
            section, product, [],
            api_surface=None,
            page_role="howto_article",
        )

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "See API reference" in code_blocks[0].content

    def test_synthesis_failure_falls_to_placeholder(self):
        """If synthesis returns None, placeholder is used."""
        section = _make_section("Quick Start")
        product = _make_product()
        api_surface = MagicMock()
        api_surface.class_briefs = []

        with patch(
            "launcher.workers.generate._code_synthesis.synthesize_section_snippet",
            return_value=None,
        ):
            result = _gap_fill_code_block(
                section, product, [],
                api_surface=api_surface,
                page_role="howto_article",
            )

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "See API reference" in code_blocks[0].content

    def test_synthesis_exception_falls_to_placeholder(self):
        """If synthesis raises, placeholder is used (non-fatal)."""
        section = _make_section("Quick Start")
        product = _make_product()
        api_surface = MagicMock()

        with patch(
            "launcher.workers.generate._code_synthesis.synthesize_section_snippet",
            side_effect=RuntimeError("synthesis broke"),
        ):
            result = _gap_fill_code_block(
                section, product, [],
                api_surface=api_surface,
                page_role="howto_article",
            )

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "See API reference" in code_blocks[0].content

    def test_extracted_preferred_over_synthesis(self):
        """When both extracted snippets and api_surface exist, extracted wins."""
        section = _make_section("Usage")
        product = _make_product()
        snippet = _make_extracted_snippet("real_code = True")
        api_surface = MagicMock()

        result = _gap_fill_code_block(
            section, product, [snippet],
            api_surface=api_surface,
            page_role="howto_article",
        )

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert "real_code" in code_blocks[0].content


# ---------------------------------------------------------------------------
# Placeholder fallback (unchanged behavior)
# ---------------------------------------------------------------------------

class TestPlaceholderFallback:
    """When no snippets and no api_surface, placeholder is generated."""

    def test_placeholder_includes_import(self):
        """Placeholder contains import statement for the product."""
        section = _make_section("Overview")
        product = _make_product(runtime_import="aspose.cells")

        result = _gap_fill_code_block(section, product, [])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert len(code_blocks) == 1
        assert "import aspose.cells" in code_blocks[0].content

    def test_placeholder_has_section_label(self):
        """Placeholder code gets section heading (TC-5112 dedup)."""
        section = _make_section("Save Spreadsheet")
        product = _make_product()

        result = _gap_fill_code_block(section, product, [])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert code_blocks[0].content.startswith("# Save Spreadsheet")

    def test_empty_snippets_falls_to_placeholder(self):
        """Empty snippet list triggers placeholder."""
        section = _make_section("Example")
        product = _make_product()

        result = _gap_fill_code_block(section, product, [])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert "See API reference" in code_blocks[0].content


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases for gap-fill behavior."""

    def test_oversized_snippet_skipped(self):
        """Extracted snippet over 2000 chars is skipped (TC-5110)."""
        section = _make_section("Usage")
        product = _make_product()
        big_snippet = _make_extracted_snippet("x = 1\n" * 500)  # > 2000 chars

        result = _gap_fill_code_block(section, product, [big_snippet])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        # Should fall through to placeholder
        assert "See API reference" in code_blocks[0].content

    def test_empty_code_snippet_skipped(self):
        """Extracted snippet with empty code is skipped."""
        section = _make_section("Usage")
        product = _make_product()
        empty_snippet = _make_extracted_snippet("   ")

        result = _gap_fill_code_block(section, product, [empty_snippet])

        code_blocks = [b for b in result.blocks if "code" in str(b.type).lower()]
        assert "See API reference" in code_blocks[0].content

    def test_prose_blocks_preserved(self):
        """Original prose blocks are preserved after gap-fill."""
        section = _make_section("Usage")
        product = _make_product()

        result = _gap_fill_code_block(section, product, [])

        para_blocks = [b for b in result.blocks if "paragraph" in str(b.type).lower()]
        assert len(para_blocks) == 1
        assert para_blocks[0].content == "Some prose content."

"""Tests for IR renderer defense-in-depth claim citation stripping (TC-3821)."""
from __future__ import annotations

from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.shared.ir_renderer import render_page, _render_block


class TestIRRendererClaimStripping:
    """Verify claim citations are stripped at render time for all block types."""

    def test_paragraph_citations_stripped(self):
        """[CLM-xxx] in paragraph block content is removed at render time."""
        block = BlockIR(type=BlockType.paragraph, content="Feature supported [CLM-cells-abc].")
        rendered = _render_block(block)
        assert "[CLM-" not in rendered
        assert rendered == "Feature supported."

    def test_code_block_citations_stripped(self):
        """Code block content IS stripped — defense-in-depth (TC-3821)."""
        block = BlockIR(type=BlockType.code, content="x = 1  # [CLM-cells-abc]", language="python")
        rendered = _render_block(block)
        assert "[CLM-cells-abc]" not in rendered
        assert "x = 1  #" not in rendered  # no dangling comment
        assert "x = 1" in rendered

    def test_code_block_multiline_citation_cleanup(self):
        """Multi-line code block: citations removed, no trailing whitespace."""
        block = BlockIR(
            type=BlockType.code,
            content="x = 1  # [CLM-a]\nprint('hi')\ny = 2 [CLM-b]",
            language="python",
        )
        rendered = _render_block(block)
        assert "[CLM-" not in rendered
        assert "x = 1" in rendered
        assert "print('hi')" in rendered
        assert "y = 2" in rendered
        # No trailing whitespace on any line inside the fence
        fence_body = rendered.split("\n")[1:-1]  # strip ```python and ```
        for line in fence_body:
            assert line == line.rstrip(), f"Trailing whitespace: {line!r}"

    def test_list_items_citations_stripped(self):
        """[CLM-xxx] in list block items is removed at render time."""
        block = BlockIR(type=BlockType.list, content="", items=["first [CLM-a]", "second"])
        rendered = _render_block(block)
        assert "[CLM-" not in rendered
        assert "- first" in rendered
        assert "- second" in rendered

    def test_heading_citations_stripped(self):
        """[CLM-xxx] in heading block content is removed at render time."""
        block = BlockIR(type=BlockType.heading, content="Overview [CLM-cells-abc]", level=2)
        rendered = _render_block(block)
        assert "[CLM-" not in rendered
        assert "## Overview" in rendered

    def test_table_citations_stripped(self):
        """[CLM-xxx] in table block content is removed at render time."""
        block = BlockIR(type=BlockType.table, content="| Col [CLM-a] | Val |\n|---|---|\n| data | ok |")
        rendered = _render_block(block)
        assert "[CLM-" not in rendered
        assert "| Col | Val |" in rendered

    def test_callout_citations_stripped(self):
        """[CLM-xxx] in callout block content is removed at render time."""
        block = BlockIR(type=BlockType.callout, content="Important note [CLM-cells-abc].")
        rendered = _render_block(block)
        assert "[CLM-" not in rendered
        assert "Important note." in rendered

    def test_full_page_render_strips_citations(self):
        """End-to-end: render_page strips citations from all non-code blocks."""
        page_ir = PageIR(
            page_id="test-page",
            page_role="overview",
            title="Test",
            frontmatter={
                "title": "Test",
                "slug": "test",
                "type": "overview",
                "url": "/cells/python/test/",
                "weight": 1,
                "family": "cells",
                "platform": "python",
                "page_role": "overview",
            },
            sections=[
                SectionIR(
                    section_id="overview",
                    heading="Overview",
                    level=2,
                    blocks=[
                        BlockIR(type=BlockType.paragraph, content="Text [CLM-a]."),
                        BlockIR(type=BlockType.code, content="# [CLM-b]", language="python"),
                    ],
                ),
            ],
        )
        rendered = render_page(page_ir)
        assert "Text." in rendered
        assert "[CLM-a]" not in rendered
        # Code block should also strip citations (defense-in-depth, TC-3821)
        assert "[CLM-b]" not in rendered

    def test_clean_content_unchanged(self):
        """Content without claim citations renders identically."""
        block = BlockIR(type=BlockType.paragraph, content="Clean paragraph with no metadata.")
        rendered = _render_block(block)
        assert rendered == "Clean paragraph with no metadata."

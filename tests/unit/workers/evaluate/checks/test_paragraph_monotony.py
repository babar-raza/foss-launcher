"""Tests for paragraph_monotony check (TC-PROSE-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.paragraph_monotony import check_paragraph_monotony


class TestParagraphMonotony:
    def test_varied_paragraphs_pass(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "This is a longer paragraph that explains the core concept in detail. "
            "It covers multiple aspects of the library and provides context for "
            "the examples that follow below.\n\n"
            "Short paragraph here.\n\n"
            "Another longer paragraph with more detail about the implementation "
            "approach and the reasoning behind the design decisions made.\n\n"
            "Brief note about a specific case.\n"
        )
        findings = check_paragraph_monotony(content, "test-page")
        assert len(findings) == 0

    def test_four_short_paragraphs_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Features\n\n"
            "The library supports OBJ format loading from local disk files.\n\n"
            "The library supports STL format saving to the output directory.\n\n"
            "The library supports glTF import and export for modern workflows.\n\n"
            "The library supports FBX read operations on binary mesh data.\n\n"
            "The library supports 3MF writing capability for additive manufacturing.\n"
        )
        findings = check_paragraph_monotony(content, "test-page")
        assert len(findings) >= 1
        assert findings[0].check == "paragraph_monotony"
        assert findings[0].severity == "low"

    def test_code_blocks_not_counted(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Example\n\n"
            "Short intro line here.\n\n"
            "```python\nimport something\n```\n\n"
            "Short result line here.\n\n"
            "```python\nimport another\n```\n\n"
            "Short ending line here.\n"
        )
        # Code blocks are stripped, so only 3 short paragraphs remain (< 4 threshold)
        findings = check_paragraph_monotony(content, "test-page")
        assert len(findings) == 0

    def test_list_items_not_counted_as_paragraphs(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Features\n\n"
            "- Feature one\n- Feature two\n- Feature three\n\n"
            "- Another one\n- Another two\n\n"
            "Final paragraph with more detail about the features listed above.\n"
        )
        findings = check_paragraph_monotony(content, "test-page")
        assert len(findings) == 0

    def test_very_short_fragments_ignored(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Notes\n\n"
            "Yes.\n\n"
            "No.\n\n"
            "Maybe.\n\n"
            "OK.\n"
        )
        # These are below _SHORT_PARAGRAPH_MIN_WORDS, so not counted
        findings = check_paragraph_monotony(content, "test-page")
        assert len(findings) == 0

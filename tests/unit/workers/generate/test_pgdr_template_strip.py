"""TC-5134: PGDR template echo stripping tests.

Verifies that _strip_template_echo_from_blocks() removes scaffold/template
text from paragraph blocks while preserving code blocks and legitimate content.
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType
from launcher.workers.generate.worker import _strip_template_echo_from_blocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _para(text: str) -> BlockIR:
    """Create a paragraph BlockIR."""
    return BlockIR(type=BlockType.paragraph, content=text)


def _code(text: str) -> BlockIR:
    """Create a code BlockIR."""
    return BlockIR(type=BlockType.code, content=text)


# ---------------------------------------------------------------------------
# Tests — scaffold phrases are stripped
# ---------------------------------------------------------------------------

class TestScaffoldStripped:
    """Paragraph blocks containing scaffold text are cleaned."""

    def test_todo_removed(self):
        """Paragraph with 'TODO' is stripped."""
        blocks = [_para("TODO: add content here")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0  # entire block removed (only scaffold)

    def test_tbd_removed(self):
        """Paragraph with 'TBD' is stripped."""
        blocks = [_para("TBD")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0

    def test_placeholder_bracket_removed(self):
        """Paragraph with '[placeholder]' is stripped."""
        blocks = [_para("[placeholder]")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0

    def test_section_title_bracket_removed(self):
        """Paragraph with '[section title]' is stripped."""
        blocks = [_para("[section title]")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0

    def test_content_to_be_generated_removed(self):
        """Paragraph with '[content to be generated]' is stripped."""
        blocks = [_para("[Content to be generated]")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0

    def test_multiline_only_scaffold_lines_removed(self):
        """Multi-line paragraph: only scaffold lines removed, rest preserved."""
        blocks = [_para("This is real content.\nTODO: finish this\nMore real content.")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 1
        assert "real content" in result[0].content
        assert "TODO" not in result[0].content

    def test_all_lines_scaffold_block_removed(self):
        """All lines are scaffold → entire block removed."""
        blocks = [_para("TODO\nTBD\n[placeholder]")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0

    def test_case_insensitive(self):
        """Scaffold matching is case-insensitive."""
        blocks = [_para("todo: something")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests — code blocks preserved
# ---------------------------------------------------------------------------

class TestCodePreserved:
    """Code blocks are never modified, even with scaffold phrases."""

    def test_todo_in_code_preserved(self):
        """Code block with TODO comment → preserved unchanged."""
        blocks = [_code("# TODO: implement this\ndef foo():\n    pass")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 1
        assert result[0].content == blocks[0].content

    def test_tbd_in_code_preserved(self):
        """Code block with TBD → preserved."""
        blocks = [_code("x = 'TBD'")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 1
        assert result[0].content == "x = 'TBD'"


# ---------------------------------------------------------------------------
# Tests — legitimate content preserved
# ---------------------------------------------------------------------------

class TestLegitimatePreserved:
    """Non-scaffold paragraph content is not modified."""

    def test_normal_paragraph_unchanged(self):
        """Normal paragraph → unchanged."""
        blocks = [_para("This is a normal paragraph about the API.")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 1
        assert result[0].content == "This is a normal paragraph about the API."

    def test_todolist_not_stripped(self):
        """'TodoList' is not standalone 'todo' → preserved."""
        blocks = [_para("Use the TodoList component to manage tasks.")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 1
        assert "TodoList" in result[0].content

    def test_empty_paragraph_unchanged(self):
        """Empty paragraph → preserved (no crash)."""
        blocks = [_para("")]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 1
        assert result[0].content == ""

    def test_mixed_blocks_only_scaffold_paragraphs_stripped(self):
        """Mix of code, paragraph, scaffold paragraph → only scaffold removed."""
        blocks = [
            _para("Real content about the library."),
            _code("import aspose.cells_foss"),
            _para("TODO: write more"),
            _para("Another real paragraph."),
        ]
        result = _strip_template_echo_from_blocks(blocks)
        assert len(result) == 3
        assert result[0].content == "Real content about the library."
        assert result[1].content == "import aspose.cells_foss"
        assert result[2].content == "Another real paragraph."


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Empty lists, claim_ids preservation."""

    def test_empty_block_list(self):
        """Empty block list → empty result."""
        assert _strip_template_echo_from_blocks([]) == []

    def test_claim_ids_preserved_after_strip(self):
        """When scaffold lines are stripped but content remains, claim_ids carry over."""
        block = BlockIR(
            type=BlockType.paragraph,
            content="Good content.\nTODO: fix this",
            claim_ids=["CLM-001", "CLM-002"],
        )
        result = _strip_template_echo_from_blocks([block])
        assert len(result) == 1
        assert result[0].claim_ids == ["CLM-001", "CLM-002"]
        assert "TODO" not in result[0].content

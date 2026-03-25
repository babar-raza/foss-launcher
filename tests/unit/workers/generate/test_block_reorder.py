"""TC-GLD-017: Tests for prose-before-code block reordering logic.

Verifies that when golden block_sequence starts with "paragraph" and the
generated section starts with a code block, the first paragraph is moved
before the first code block — unless the paragraph contains a forward-reference
phrase like "shown below".
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType, SectionIR


def _apply_prose_before_code_reorder(
    blocks: list[BlockIR],
    golden_block_sequence: list[str] | None,
) -> list[BlockIR]:
    """Extract the reorder logic from worker.py for isolated testing.

    This mirrors the TC-GLD-017 block in generate/worker.py exactly.
    """
    _gbs = golden_block_sequence or []
    _blocks = list(blocks)
    if (
        _gbs and _gbs[0] == "paragraph"
        and _blocks and _blocks[0].type == BlockType.code
    ):
        _para_idx = next(
            (i for i, b in enumerate(_blocks) if b.type == BlockType.paragraph),
            None,
        )
        if _para_idx is not None and _para_idx > 0:
            _para_text = (_blocks[_para_idx].content or "").rstrip()
            _fwd_refs = ("shown below", "as follows", "following code", "example below")
            if not any(ref in _para_text.lower() for ref in _fwd_refs):
                _para = _blocks.pop(_para_idx)
                _blocks.insert(0, _para)
    return _blocks


class TestProseBeforeCodeReorder:
    """TC-GLD-017: Prose-before-code block reordering."""

    def test_reorder_moves_paragraph_before_code(self):
        """When golden expects paragraph first and section starts with code, reorder."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose"),
            BlockIR(type=BlockType.paragraph, content="This section explains the API."),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code"])
        assert result[0].type == BlockType.paragraph
        assert result[1].type == BlockType.code

    def test_no_reorder_when_already_paragraph_first(self):
        """When section already starts with paragraph, no change."""
        blocks = [
            BlockIR(type=BlockType.paragraph, content="Intro text."),
            BlockIR(type=BlockType.code, content="import aspose"),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code"])
        assert result[0].type == BlockType.paragraph
        assert result[1].type == BlockType.code

    def test_no_reorder_when_golden_expects_code_first(self):
        """When golden block_sequence starts with 'code', no reorder."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose"),
            BlockIR(type=BlockType.paragraph, content="Explanation."),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["code", "paragraph"])
        assert result[0].type == BlockType.code

    def test_no_reorder_when_no_golden_sequence(self):
        """When golden_block_sequence is None, no reorder."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose"),
            BlockIR(type=BlockType.paragraph, content="Explanation."),
        ]
        result = _apply_prose_before_code_reorder(blocks, None)
        assert result[0].type == BlockType.code

    def test_skip_reorder_on_forward_reference_shown_below(self):
        """Paragraph with 'shown below' must NOT be reordered."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose"),
            BlockIR(type=BlockType.paragraph, content="The code is shown below:"),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code"])
        assert result[0].type == BlockType.code

    def test_skip_reorder_on_forward_reference_as_follows(self):
        """Paragraph with 'as follows' must NOT be reordered."""
        blocks = [
            BlockIR(type=BlockType.code, content="x = 1"),
            BlockIR(type=BlockType.paragraph, content="The implementation is as follows:"),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code"])
        assert result[0].type == BlockType.code

    def test_skip_reorder_on_forward_reference_following_code(self):
        """Paragraph with 'following code' must NOT be reordered."""
        blocks = [
            BlockIR(type=BlockType.code, content="x = 1"),
            BlockIR(type=BlockType.paragraph, content="Use the following code to convert:"),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code"])
        assert result[0].type == BlockType.code

    def test_no_reorder_when_no_paragraph_exists(self):
        """When all blocks are code (no paragraph), no reorder and no crash."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose"),
            BlockIR(type=BlockType.code, content="wb = Workbook()"),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code"])
        assert result[0].type == BlockType.code
        assert len(result) == 2

    def test_reorder_with_multiple_blocks(self):
        """Reorder works correctly with code, list, paragraph sequence."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose"),
            BlockIR(type=BlockType.list, content="- item 1\n- item 2"),
            BlockIR(type=BlockType.paragraph, content="This is the intro."),
        ]
        result = _apply_prose_before_code_reorder(blocks, ["paragraph", "code", "list"])
        assert result[0].type == BlockType.paragraph
        assert result[1].type == BlockType.code
        assert result[2].type == BlockType.list

    def test_empty_blocks_no_crash(self):
        """Empty block list must not crash."""
        result = _apply_prose_before_code_reorder([], ["paragraph", "code"])
        assert result == []

"""TC-GEN-301 / HG-22: Post-generate method verification against class_briefs.

Tests verify that _strip_hallucinated_method_calls():
1. Strips blocks with 2+ unknown tracked methods
2. Comments out single unknown method lines
3. Preserves blocks with all valid methods
4. Ignores untracked receivers
5. Ignores non-Python blocks
6. Is a no-op when class_method_map is empty
"""
from __future__ import annotations

from launcher.models.page_ir import BlockIR, BlockType
from launcher.workers.generate.section_validator import _strip_hallucinated_method_calls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _code_block(code: str, language: str = "python") -> BlockIR:
    return BlockIR(type=BlockType.code, content=code, language=language)


def _para_block(text: str) -> BlockIR:
    return BlockIR(type=BlockType.paragraph, content=text)


# Shared fixtures
_PUBLIC_CLASSES = {"Workbook", "Worksheet", "Cells"}
_CLASS_METHOD_MAP = {
    "Workbook": frozenset({"save", "load", "create_worksheet"}),
    "Worksheet": frozenset({"get_cell", "set_value"}),
    "Cells": frozenset({"clear", "merge"}),
}


# ---------------------------------------------------------------------------
# Block stripping (2+ unknown methods)
# ---------------------------------------------------------------------------

class TestBlockStripping:
    """Blocks with 2+ hallucinated tracked methods are stripped entirely."""

    def test_two_unknown_methods_strips_block(self):
        code = "wb = Workbook()\nwb.create_chart()\nwb.export_pdf()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 0

    def test_three_unknown_methods_strips_block(self):
        code = "wb = Workbook()\nwb.a()\nwb.b()\nwb.c()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 0

    def test_mixed_valid_and_two_unknown_strips(self):
        code = "wb = Workbook()\nwb.save('out.xlsx')\nwb.fake_a()\nwb.fake_b()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Single method comment-out
# ---------------------------------------------------------------------------

class TestSingleMethodCommentOut:
    """Blocks with exactly 1 hallucinated tracked method get the line commented."""

    def test_one_unknown_method_commented(self):
        code = "wb = Workbook()\nwb.save('out.xlsx')\nwb.create_chart()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].type == BlockType.code
        assert "# HG-22:" in result[0].content
        assert "wb.save" in result[0].content  # valid line preserved
        assert "create_chart" in result[0].content  # present in comment

    def test_commented_line_preserves_rest(self):
        code = "wb = Workbook()\nwb.load('in.xlsx')\nwb.fake_method()\nprint('done')"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        lines = result[0].content.split("\n")
        # Original 4 lines preserved
        assert len(lines) == 4
        # Line 2 (index 2) is commented
        assert lines[2].startswith("# HG-22:")
        # Other lines unchanged
        assert lines[0] == "wb = Workbook()"
        assert lines[1] == "wb.load('in.xlsx')"
        assert lines[3] == "print('done')"


# ---------------------------------------------------------------------------
# Valid methods preserved
# ---------------------------------------------------------------------------

class TestValidMethodsPreserved:
    """Blocks with all valid methods pass through unchanged."""

    def test_all_valid_methods_preserved(self):
        code = "wb = Workbook()\nwb.save('out.xlsx')\nwb.load('in.xlsx')"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].content == code

    def test_no_method_calls_preserved(self):
        code = "x = 1\ny = 2\nprint(x + y)"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].content == code


# ---------------------------------------------------------------------------
# Untracked receivers
# ---------------------------------------------------------------------------

class TestUntrackedReceivers:
    """Untracked receivers pass through — no false positives."""

    def test_untracked_receiver_passes(self):
        code = "obj.create_chart()\nobj.export_pdf()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].content == code

    def test_dict_get_passes(self):
        code = 'my_dict = {"a": 1}\nresult = my_dict.get("a")'
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].content == code


# ---------------------------------------------------------------------------
# Non-Python and edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Non-Python blocks, empty maps, comment-only blocks."""

    def test_non_python_block_passes(self):
        code = "const wb = new Workbook();\nwb.fakeMethod();"
        blocks = [_code_block(code, language="javascript")]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].content == code

    def test_empty_class_method_map_noop(self):
        code = "wb = Workbook()\nwb.create_chart()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(blocks, {}, _PUBLIC_CLASSES)
        assert len(result) == 1
        assert result[0].content == code

    def test_empty_public_classes_noop(self):
        code = "wb = Workbook()\nwb.create_chart()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(blocks, _CLASS_METHOD_MAP, set())
        assert len(result) == 1
        assert result[0].content == code

    def test_paragraph_block_passes(self):
        blocks = [_para_block("Call wb.fake_method() to export.")]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert result[0].type == BlockType.paragraph

    def test_comment_lines_not_scanned(self):
        """Method calls in comments should not trigger HG-22."""
        code = "wb = Workbook()\n# wb.create_chart()\nwb.save('out.xlsx')"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert "# HG-22:" not in result[0].content  # no comment-out applied

    def test_lowercase_class_name_receiver_tracked(self):
        """'workbook.fake()' where 'workbook' matches known class Workbook."""
        code = "workbook.fake_method()\nworkbook.also_fake()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        # 2 unknown methods on tracked receiver → stripped
        assert len(result) == 0

    def test_empty_code_block_passes(self):
        blocks = [_code_block("")]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1

    def test_private_methods_skipped(self):
        """Methods starting with _ are not checked."""
        code = "wb = Workbook()\nwb._internal_method()"
        blocks = [_code_block(code)]
        result = _strip_hallucinated_method_calls(
            blocks, _CLASS_METHOD_MAP, _PUBLIC_CLASSES,
        )
        assert len(result) == 1
        assert "# HG-22:" not in result[0].content

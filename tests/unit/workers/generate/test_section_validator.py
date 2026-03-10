"""Tests for TC-3817: section_validator heading split (Change D)."""

from __future__ import annotations

import json

import pytest

from launcher.models.page_ir import BlockIR, BlockType
from launcher.models.product import ProductIdentity


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="note", platform="python",
        display_name="Aspose.Note", canonical_import="aspose_note_foss",
        repo_url="https://example.com",
    )


class TestHeadingSplit:
    """Change D: Overlong heading blocks are split into heading + paragraph."""

    def test_short_heading_not_split(self):
        from launcher.workers.generate.section_validator import parse_and_validate_blocks

        product = _make_product()
        blocks_json = json.dumps([
            {"type": "heading", "content": "What is Aspose.Note?", "level": 3, "claim_ids": []},
            {"type": "paragraph", "content": "It is a library.", "claim_ids": []},
        ])
        result = parse_and_validate_blocks(blocks_json, product, set(), [])
        assert result is not None
        headings = [b for b in result if b.type == BlockType.heading]
        assert len(headings) == 1

    def test_overlong_heading_split(self):
        from launcher.workers.generate.section_validator import parse_and_validate_blocks

        product = _make_product()
        long_heading = (
            "What formats does Aspose.Note support? Aspose.Note supports OneNote, "
            "PDF, and image formats including PNG and JPEG for comprehensive document processing."
        )
        assert len(long_heading) > 80

        blocks_json = json.dumps([
            {"type": "heading", "content": long_heading, "level": 3, "claim_ids": ["CLM-001"]},
        ])
        result = parse_and_validate_blocks(blocks_json, product, {"CLM-001"}, [])
        assert result is not None
        assert len(result) == 2
        assert result[0].type == BlockType.heading
        assert result[1].type == BlockType.paragraph
        # Heading should be the question part
        assert len(result[0].content) < len(long_heading)

    def test_heading_without_sentence_break_not_split(self):
        from launcher.workers.generate.section_validator import parse_and_validate_blocks

        product = _make_product()
        # Long heading but no sentence break — shouldn't split
        long_heading = "A" * 100
        blocks_json = json.dumps([
            {"type": "heading", "content": long_heading, "level": 3, "claim_ids": []},
        ])
        result = parse_and_validate_blocks(blocks_json, product, set(), [])
        assert result is not None
        assert len(result) == 1


# ---------------------------------------------------------------------------
# HG-16: Hallucinated code block repair tests
# ---------------------------------------------------------------------------

class TestHG16HallucinatedCodeBlockRepair:
    """HG-16: Post-generation hallucinated code block removal."""

    def _make_code_block(self, code: str, lang: str = "python") -> "BlockIR":
        return BlockIR(type=BlockType.code, content=code, language=lang, claim_ids=[])

    def _make_para_block(self, text: str) -> "BlockIR":
        return BlockIR(type=BlockType.paragraph, content=text, claim_ids=[])

    def test_hallucinated_class_code_block_removed(self):
        """Code block referencing a class not in public_classes must be removed."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene", "Node", "Mesh"}
        code = "import aspose.threed\nscene = ObjLoadOptions()"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 0, "Code block with hallucinated class must be removed"

    def test_valid_class_code_block_kept(self):
        """Code block using only known classes must be preserved."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene", "Node", "Mesh"}
        code = "import aspose.threed\nscene = Scene.from_file('input.fbx')"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Code block with valid class must be kept"

    def test_non_python_block_preserved(self):
        """Non-Python code blocks must pass through unchanged regardless of class names."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        code = "const obj = new ObjLoadOptions();"
        blocks = [self._make_code_block(code, lang="typescript")]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Non-Python block must pass through unchanged"

    def test_empty_public_classes_skips_repair(self):
        """Empty public_classes must skip the repair pass entirely."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes: set = set()
        code = "import aspose.threed\nscene = ObjLoadOptions()"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Empty public_classes must skip repair (no false positives)"

    def test_prose_block_always_preserved(self):
        """Prose blocks must never be removed, even if they mention hallucinated names."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        blocks = [self._make_para_block("Use ObjLoadOptions to configure loading.")]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Prose blocks must never be removed"

    # HG-17: comment false-positive tests

    def test_comment_with_capitalized_word_preserved(self):
        """HG-17: Block with capitalized word ONLY in comment must NOT be removed."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        # 'Load' appears only in a comment; actual code uses only Scene
        code = "scene = Scene.from_file('input.fbx')\n# Load the scene file"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Comment word 'Load' must not trigger block removal"

    def test_hallucinated_name_in_comment_only_is_preserved(self):
        """HG-17: Block where hallucinated class appears ONLY in comment is preserved."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        # ObjLoadOptions appears only in a comment; actual code uses only Scene
        code = "scene = Scene()\n# Use ObjLoadOptions for legacy formats"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "ObjLoadOptions in comment only must not remove block"

    def test_hallucinated_class_in_code_not_comment_still_removed(self):
        """HG-17: Block where hallucinated name appears in actual code is still removed."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        # ObjLoadOptions is used in code (not just comment)
        code = "scene = Scene()\nobj = ObjLoadOptions()\n# Export scene"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 0, "ObjLoadOptions in code (not comment) must trigger removal"

    # HG-18: CamelCase-only detection tests

    def test_single_word_capitalized_variable_preserved(self):
        """HG-18: Single-word capitalized variable names must NOT trigger removal."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        # Author, Title — single-word capitalized, not CamelCase class names
        code = "Author = 'Aspose'\nTitle = 'Getting Started'\nscene = Scene()"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Single-word capitalized variables (Author, Title) must not remove block"

    def test_all_caps_constant_preserved(self):
        """HG-18: All-caps constants (STL, ASCII, STL_ASCII) must not trigger removal."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene"}
        code = "STL_FORMAT = 'stl'\nASCII_MODE = True\nscene = Scene()"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "All-caps constants (STL, ASCII) must not trigger removal"

    # HG-20: PascalCase+digit detection tests

    def test_pascal_digit_hallucinated_class_removed(self):
        """HG-20: PascalCase+digit class names (Vector3) not in public_classes are removed."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene", "Node"}
        # Vector3 is NOT in public_classes — block must be removed
        code = "scene = Scene()\npos = Vector3(1.0, 2.0, 3.0)"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 0, "Vector3 not in public_classes must trigger block removal"

    def test_pascal_digit_in_public_classes_preserved(self):
        """HG-20: PascalCase+digit class in public_classes must NOT trigger removal."""
        from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
        public_classes = {"Scene", "Vector3"}
        # Vector3 IS in public_classes — block must be preserved
        code = "scene = Scene()\npos = Vector3(1.0, 2.0, 3.0)"
        blocks = [self._make_code_block(code)]
        result = _strip_hallucinated_code_blocks(blocks, public_classes)
        assert len(result) == 1, "Vector3 in public_classes must preserve block"

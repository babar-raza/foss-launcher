"""Tests for post-LLM Python code validation helpers (v2 pipeline).

Verifies:
- _detect_identifier_omitted_in_code (FPR-01)
- _scan_code_block_api_identifiers (FPR-03)
- _accept_code_block syntax rejection (FPR-04)
- section_validator output sanitization (TC-SAN-01)
"""
from __future__ import annotations

from launcher.models.page_ir import BlockIR, BlockType
from launcher.workers.generate.worker import _detect_identifier_omitted_in_code


# ---------------------------------------------------------------------------
# TC-SAN-01: Output sanitization tests
# ---------------------------------------------------------------------------


class TestStripSourceComments:
    """TC-SAN-01: _strip_claim_comments strips CLM-xxx metadata comments."""

    def test_claim_comment_still_stripped(self):
        from launcher.workers.generate.section_validator import _strip_claim_comments
        code = "# Claims: CLM-cells-abc123\nprint('hello')"
        result = _strip_claim_comments(code)
        assert "CLM-" not in result
        assert "print('hello')" in result

    def test_normal_comments_preserved(self):
        from launcher.workers.generate.section_validator import _strip_claim_comments
        code = "# This is a user comment\nprint('hello')"
        result = _strip_claim_comments(code)
        assert "# This is a user comment" in result


class TestListOfListsTable:
    """TC-SAN-01: _validate_table_content handles JSON array-of-dicts and pipe tables."""

    def test_dict_array_still_works(self):
        from launcher.workers.generate.section_validator import _validate_table_content
        content = '[{"Format": "Excel", "Extension": ".xlsx"}, {"Format": "CSV", "Extension": ".csv"}]'
        result = _validate_table_content(content)
        assert "| Format | Extension |" in result
        assert "| Excel | .xlsx |" in result

    def test_pipe_table_passthrough(self):
        from launcher.workers.generate.section_validator import _validate_table_content
        content = "| A | B |\n| --- | --- |\n| 1 | 2 |"
        result = _validate_table_content(content)
        assert result == content


# ===========================================================================
# FPR-01: identifier-omitted sentinel detection in code blocks
# ===========================================================================


class TestIdentifierOmittedInCode:
    """FPR-01 (2026-03-22): _detect_identifier_omitted_in_code must flag code
    blocks that contain '[identifier omitted]' so the generate worker can log
    and surface the issue for remediation.
    """

    def test_clean_code_block_returns_empty(self):
        """A code block with no sentinel returns no violations."""
        blocks = [
            BlockIR(type=BlockType.code, content="wb = Workbook()\nwb.save('out.xlsx')"),
        ]
        assert _detect_identifier_omitted_in_code(blocks) == []

    def test_sentinel_in_code_block_detected(self):
        """A code block containing '[identifier omitted]' is flagged."""
        blocks = [
            BlockIR(type=BlockType.code, content="import xml.etree.[identifier omitted] as ET"),
        ]
        violations = _detect_identifier_omitted_in_code(blocks)
        assert violations == [1]

    def test_sentinel_in_prose_block_ignored(self):
        """The sentinel in a prose/paragraph block is NOT flagged (expected repair output)."""
        blocks = [
            BlockIR(type=BlockType.paragraph, content="Use the [identifier omitted] class."),
        ]
        assert _detect_identifier_omitted_in_code(blocks) == []

    def test_multiple_code_blocks_correct_indices(self):
        """When multiple code blocks have the sentinel, all their 1-based indices are returned."""
        blocks = [
            BlockIR(type=BlockType.code, content="x = 1"),                              # clean
            BlockIR(type=BlockType.code, content="ws = [identifier omitted]()"),        # violation
            BlockIR(type=BlockType.paragraph, content="[identifier omitted] is bad"),   # prose → ignored
            BlockIR(type=BlockType.code, content="y = [identifier omitted].open()"),    # violation
        ]
        violations = _detect_identifier_omitted_in_code(blocks)
        assert violations == [2, 4]


# ===========================================================================
# FPR-03: api_surface PascalCase scan for unknown class identifiers
# ===========================================================================


class TestApiSurfaceCodeScan:
    """FPR-03 (2026-03-22): _scan_code_block_api_identifiers must detect PascalCase
    identifiers not in public_classes and return them for WARNING emission.
    """

    @staticmethod
    def _scan(code: str, public_classes: set[str]) -> list[str]:
        from launcher.workers.generate.worker import _scan_code_block_api_identifiers
        return _scan_code_block_api_identifiers(code, public_classes)

    def test_unknown_class_detected(self):
        """A PascalCase class not in public_classes is returned."""
        code = "ws = Worksheet()\nws.save('out.xlsx')"
        result = self._scan(code, {"Workbook", "WorksheetCollection"})
        assert "Worksheet" in result

    def test_known_class_passes(self):
        """A PascalCase class that is in public_classes is not returned."""
        code = "wb = Workbook()\nwb.save('out.xlsx')"
        result = self._scan(code, {"Workbook"})
        assert result == []

    def test_builtin_types_not_flagged(self):
        """Standard Python builtins (True, False, None, Optional) are not flagged."""
        code = "x: Optional[str] = None\nif True:\n    pass"
        result = self._scan(code, {"Workbook"})
        assert result == []

    def test_empty_public_classes_skips_check(self):
        """When public_classes is empty, no scan is performed."""
        code = "ws = Worksheet()\nwb = Workbook()"
        result = self._scan(code, set())
        assert result == []

    def test_comment_content_not_flagged(self):
        """PascalCase words in inline comments are not flagged."""
        code = "wb = Workbook()  # Load the WorksheetManager\nwb.save('out.xlsx')"
        result = self._scan(code, {"Workbook"})
        # WorksheetManager is after '#' and should be stripped before scanning
        assert "WorksheetManager" not in result

    def test_exception_types_not_flagged(self):
        """FPRSR-01: Standard exception types are not flagged as unknown API identifiers."""
        code = (
            "try:\n"
            "    result = wb.save('out.xlsx')\n"
            "except Exception as e:\n"
            "    raise ValueError(str(e)) from e\n"
        )
        result = self._scan(code, {"Workbook"})
        assert "Exception" not in result
        assert "ValueError" not in result

    def test_stdlib_io_and_abc_not_flagged(self):
        """FPRSR-01: stdlib PascalCase names (StringIO, ABC, Enum) are not flagged."""
        code = (
            "from io import StringIO\n"
            "from abc import ABC\n"
            "from enum import Enum\n"
            "buf = StringIO()\n"
        )
        result = self._scan(code, {"Workbook"})
        assert "StringIO" not in result
        assert "ABC" not in result
        assert "Enum" not in result


# ===========================================================================
# FPR-04: Python code block syntax rejection in generate sandwich
# ===========================================================================


class TestCodeBlockSyntaxRejection:
    """FPR-04 (2026-03-22): _accept_code_block must reject Python blocks with
    syntax errors so the generate retry loop can trigger a corrective prompt.
    """

    @staticmethod
    def _accept(code: str, lang: str) -> bool:
        from launcher.workers.generate.worker import _accept_code_block
        return _accept_code_block(code, lang)

    def test_invalid_python_rejected(self):
        """A Python block with a syntax error is rejected (returns False)."""
        assert not self._accept("def foo(\n    pass", "python")

    def test_valid_python_accepted(self):
        """A syntactically valid Python block is accepted (returns True)."""
        code = "from aspose.cells_foss import Workbook\nwb = Workbook()\nwb.save('out.xlsx')"
        assert self._accept(code, "python")

    def test_non_python_block_accepted(self):
        """Non-Python language blocks are never syntax-checked (always accepted)."""
        assert self._accept("const x = 1;\nconsole.log(x);", "javascript")
        assert self._accept("<div>Hello</div>", "html")
        assert self._accept("public class Foo { }", "csharp")

    def test_pip_install_skipped(self):
        """Shell-style pip install lines are not ast-parsed and always accepted."""
        assert self._accept("pip install aspose-cells-foss", "python")

    def test_empty_block_accepted(self):
        """Empty or whitespace-only blocks pass through without error."""
        assert self._accept("", "python")
        assert self._accept("   \n\t  ", "python")

"""TC-DFR-001: Tests for post-LLM Python code validation and import canonicalization.

Verifies that:
- _validate_python_syntax detects syntax errors in Python code blocks
- _canonicalize_python_imports replaces non-canonical imports
- Stdlib imports are never modified
- Non-code blocks pass through unchanged
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType

try:
    from launcher.workers.generate.worker import (
        _canonicalize_python_imports,
        _is_close_variant,
        _looks_like_python,
        _validate_python_syntax,
    )
except ImportError:  # pragma: no cover — guard for refactored worker versions
    _canonicalize_python_imports = None  # type: ignore[assignment]
    _is_close_variant = None  # type: ignore[assignment]
    _looks_like_python = None  # type: ignore[assignment]
    _validate_python_syntax = None  # type: ignore[assignment]

from launcher.workers.generate.worker import _detect_identifier_omitted_in_code


class TestValidatePythonSyntax:
    """TC-DFR-001: Python syntax validation via ast.parse()."""

    def test_valid_code_no_errors(self):
        """Valid Python code produces no errors."""
        blocks = [
            BlockIR(type=BlockType.code, content="import os\nx = 1 + 2\nprint(x)"),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_syntax_error_detected(self):
        """Unclosed parenthesis produces a syntax error."""
        blocks = [
            BlockIR(type=BlockType.code, content="print(x"),
        ]
        errors = _validate_python_syntax(blocks)
        assert len(errors) == 1
        assert "Code block 1" in errors[0]

    def test_missing_colon_detected(self):
        """Missing colon in def statement produces a syntax error."""
        blocks = [
            BlockIR(type=BlockType.code, content="def foo()\n    pass"),
        ]
        errors = _validate_python_syntax(blocks)
        assert len(errors) == 1

    def test_multiple_blocks_mixed(self):
        """Only invalid blocks produce errors."""
        blocks = [
            BlockIR(type=BlockType.code, content="x = 1"),
            BlockIR(type=BlockType.code, content="y = ("),
            BlockIR(type=BlockType.paragraph, content="Some text"),
        ]
        errors = _validate_python_syntax(blocks)
        assert len(errors) == 1
        assert "Code block 2" in errors[0]

    def test_paragraph_blocks_ignored(self):
        """Non-code blocks are not validated."""
        blocks = [
            BlockIR(type=BlockType.paragraph, content="This is not code: def foo("),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_empty_code_block_ignored(self):
        """Empty code blocks don't cause errors."""
        blocks = [
            BlockIR(type=BlockType.code, content=""),
            BlockIR(type=BlockType.code, content="   "),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_shell_commands_skipped(self):
        """Shell commands (pip install, python -m) are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content="pip install aspose-cells-foss"),
            BlockIR(type=BlockType.code, content="$ python -m pytest"),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_valid_multiline_code(self):
        """Multi-line valid Python produces no errors."""
        blocks = [
            BlockIR(type=BlockType.code, content=(
                "from aspose.cells_foss import Workbook\n"
                "\n"
                "wb = Workbook()\n"
                "ws = wb.worksheets[0]\n"
                "ws.cells.get('A1').put_value('Hello')\n"
                "wb.save('output.xlsx')\n"
                "print('Done')"
            )),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_javascript_block_skipped(self):
        """SR-01: JavaScript code blocks are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content="const x = 1;\nconsole.log(x);"),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_bash_block_skipped(self):
        """SR-01: Bash script blocks are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content="#!/bin/bash\necho 'hello'\nexit 0"),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_yaml_block_skipped(self):
        """SR-01: YAML content blocks are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content="---\nname: test\nversion: 1.0"),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_json_block_skipped(self):
        """SR-01: JSON blocks are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content='{"key": "value", "num": 42}'),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_html_block_skipped(self):
        """SR-01: HTML blocks are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content="<div>Hello</div>"),
        ]
        assert _validate_python_syntax(blocks) == []

    def test_typescript_export_skipped(self):
        """SR-01: TypeScript export blocks are not ast-parsed."""
        blocks = [
            BlockIR(type=BlockType.code, content="export function foo() {\n  return 1;\n}"),
        ]
        assert _validate_python_syntax(blocks) == []


class TestLooksLikePython:
    """SR-01: Python heuristic detection."""

    def test_import_is_python(self):
        assert _looks_like_python("import os\nprint('hi')")

    def test_from_import_is_python(self):
        assert _looks_like_python("from pathlib import Path")

    def test_def_is_python(self):
        assert _looks_like_python("def foo():\n    pass")

    def test_class_is_python(self):
        assert _looks_like_python("class MyClass:\n    pass")

    def test_print_is_python(self):
        assert _looks_like_python("print('hello world')")

    def test_assignment_is_python(self):
        assert _looks_like_python("x = 42\ny = 'hello'")

    def test_const_is_not_python(self):
        assert not _looks_like_python("const x = 1;")

    def test_function_js_is_not_python(self):
        assert not _looks_like_python("function foo() { return 1; }")

    def test_shebang_is_not_python(self):
        assert not _looks_like_python("#!/bin/bash\necho hi")

    def test_yaml_frontmatter_is_not_python(self):
        assert not _looks_like_python("---\nkey: value")

    def test_json_object_is_not_python(self):
        assert not _looks_like_python('{"key": "value"}')

    def test_html_is_not_python(self):
        assert not _looks_like_python("<div>text</div>")

    def test_empty_is_not_python(self):
        assert not _looks_like_python("")

    def test_console_log_is_not_python(self):
        assert not _looks_like_python("console.log('hello');")

    def test_export_is_not_python(self):
        assert not _looks_like_python("export default class Foo {}")


class TestCanonicalizePythonImports:
    """TC-DFR-001: Import canonicalization."""

    def test_replaces_close_variant(self):
        """Non-canonical import close to canonical is replaced with runtime form."""
        blocks = [
            BlockIR(type=BlockType.code, content="import aspose_cell\nx = 1"),
        ]
        result = _canonicalize_python_imports(blocks, "aspose_cells_foss", "aspose.cells_foss")
        code = result[0].content or ""
        # TC-5133: Close variant rewrites to runtime import (aspose.cells_foss)
        assert "aspose.cells_foss" in code

    def test_preserves_stdlib(self):
        """Stdlib imports (os, sys, json) are never modified."""
        blocks = [
            BlockIR(type=BlockType.code, content="import os\nimport json\nimport sys"),
        ]
        result = _canonicalize_python_imports(blocks, "aspose_cells_foss", "")
        assert result[0].content == blocks[0].content

    def test_preserves_canonical_import(self):
        """Already-canonical imports are not modified."""
        blocks = [
            BlockIR(type=BlockType.code, content="from aspose_cells_foss import Workbook"),
        ]
        result = _canonicalize_python_imports(blocks, "aspose_cells_foss", "")
        assert result[0].content == blocks[0].content

    def test_preserves_runtime_import(self):
        """Runtime imports are not modified."""
        blocks = [
            BlockIR(type=BlockType.code, content="from aspose.cells_foss import Workbook"),
        ]
        result = _canonicalize_python_imports(blocks, "aspose_cells_foss", "aspose.cells_foss")
        assert result[0].content == blocks[0].content

    def test_paragraph_blocks_unchanged(self):
        """Non-code blocks pass through."""
        blocks = [
            BlockIR(type=BlockType.paragraph, content="import fake_module"),
        ]
        result = _canonicalize_python_imports(blocks, "aspose_cells_foss", "")
        assert result[0].content == blocks[0].content

    def test_no_canonical_no_modification(self):
        """When no canonical import, blocks pass through."""
        blocks = [
            BlockIR(type=BlockType.code, content="import something"),
        ]
        result = _canonicalize_python_imports(blocks, "", "")
        assert result[0].content == blocks[0].content


class TestIsCloseVariant:
    """TC-DFR-001: Close variant detection."""

    def test_exact_match(self):
        assert _is_close_variant("aspose_cells", "aspose_cells")

    def test_substring_match(self):
        assert _is_close_variant("aspose_cell", "aspose_cells")

    def test_substring_reverse(self):
        assert _is_close_variant("aspose_cells_foss", "aspose_cells")

    def test_typo_one_char(self):
        assert _is_close_variant("aspose_celss", "aspose_cells")

    def test_too_different(self):
        assert not _is_close_variant("numpy", "aspose_cells")

    def test_case_insensitive(self):
        assert _is_close_variant("Aspose_Cells", "aspose_cells")

    def test_hyphen_underscore_normalized(self):
        assert _is_close_variant("aspose-cells", "aspose_cells")


# ---------------------------------------------------------------------------
# TC-SAN-01: Output sanitization tests
# ---------------------------------------------------------------------------


class TestStripSourceComments:
    """TC-SAN-01: _strip_claim_comments also removes # source: snippet_N."""

    def test_source_comment_stripped(self):
        from launcher.workers.generate.section_validator import _strip_claim_comments
        code = "# source: snippet_3\nfrom aspose.cells_foss import Workbook\nwb = Workbook()"
        result = _strip_claim_comments(code)
        assert "# source:" not in result
        assert "from aspose.cells_foss import Workbook" in result

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
    """TC-SAN-01: _validate_table_content handles list-of-lists format."""

    def test_list_of_lists_converted(self):
        from launcher.workers.generate.section_validator import _validate_table_content
        content = "[['Format', 'Extension', 'Notes'], ['Excel', '.xlsx', 'Full support'], ['CSV', '.csv', 'Import via Workbook']]"
        result = _validate_table_content(content)
        assert "| Format | Extension | Notes |" in result
        assert "| Excel | .xlsx | Full support |" in result
        assert "| CSV | .csv | Import via Workbook |" in result

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


class TestIsTestSnippet:
    """TC-SAN-01: _is_test_snippet filters test code from injection."""

    def test_unittest_detected(self):
        from launcher.workers.generate.worker import _is_test_snippet
        code = "import unittest\nclass TestFoo(unittest.TestCase):\n    def test_bar(self):\n        self.assertEqual(1, 1)"
        assert _is_test_snippet(code)

    def test_pytest_detected(self):
        from launcher.workers.generate.worker import _is_test_snippet
        code = "import pytest\ndef test_something():\n    assert True"
        assert _is_test_snippet(code)

    def test_normal_code_not_flagged(self):
        from launcher.workers.generate.worker import _is_test_snippet
        code = "from aspose.cells_foss import Workbook\nwb = Workbook()\nwb.save('out.xlsx')"
        assert not _is_test_snippet(code)

    def test_assert_in_test_class(self):
        from launcher.workers.generate.worker import _is_test_snippet
        code = "class TestManualPageBreaks(unittest.TestCase):\n    def setUp(self):\n        pass"
        assert _is_test_snippet(code)


class TestBareClmStripping:
    """TC-SAN-01: ir_renderer strips bare CLM-xxx: prefixes from prose."""

    def test_bare_prefix_stripped(self):
        from launcher.shared.ir_renderer import _strip_internal_markers
        text = "CLM-cells-dc36dc: Create, read, and modify Excel files."
        result = _strip_internal_markers(text)
        assert "CLM-" not in result
        assert "Create, read, and modify Excel files." in result

    def test_bracket_citation_still_stripped(self):
        from launcher.shared.ir_renderer import _strip_internal_markers
        text = "This is a feature [CLM-cells-abc123] description."
        result = _strip_internal_markers(text)
        assert "[CLM-" not in result
        assert "This is a feature" in result

    def test_normal_text_unchanged(self):
        from launcher.shared.ir_renderer import _strip_internal_markers
        text = "This is normal text without any markers."
        result = _strip_internal_markers(text)
        assert result == text


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

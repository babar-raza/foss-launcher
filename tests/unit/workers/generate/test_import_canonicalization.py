"""TC-5133: Import canonicalization fix tests.

Verifies that _canonicalize_python_imports() correctly rewrites pip-package-name
imports (e.g. import aspose_cells_foss) to runtime import form
(e.g. import aspose.cells_foss).
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType
from launcher.workers.generate.worker import _canonicalize_python_imports


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _code_block(code: str) -> BlockIR:
    """Create a code BlockIR."""
    return BlockIR(type=BlockType.code, content=code)


def _para_block(text: str) -> BlockIR:
    """Create a paragraph BlockIR."""
    return BlockIR(type=BlockType.paragraph, content=text)


def _get_code(blocks: list[BlockIR], idx: int = 0) -> str:
    """Extract code content from the idx-th code block."""
    codes = [b for b in blocks if b.type == BlockType.code]
    return codes[idx].content if idx < len(codes) else ""


# ---------------------------------------------------------------------------
# Tests — pip-name → runtime rewrite (the core bug fix)
# ---------------------------------------------------------------------------

class TestPipNameRewrite:
    """TC-5133: pip package name imports are rewritten to runtime form."""

    CANONICAL = "aspose_cells_foss"  # pip package name (no dots)
    RUNTIME = "aspose.cells_foss"    # Python import path (with dot)

    def test_import_pip_name_rewritten(self):
        """import aspose_cells_foss → import aspose.cells_foss"""
        blocks = [_code_block("import aspose_cells_foss\nprint('hello')")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        assert "import aspose.cells_foss" in _get_code(result)
        assert "aspose_cells_foss" not in _get_code(result)

    def test_from_pip_name_rewritten(self):
        """from aspose_cells_foss import Workbook → from aspose.cells_foss import Workbook"""
        blocks = [_code_block("from aspose_cells_foss import Workbook")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        code = _get_code(result)
        assert "from aspose.cells_foss import Workbook" in code
        assert "aspose_cells_foss" not in code

    def test_from_pip_name_multiple_imports(self):
        """from aspose_cells_foss import Workbook, Worksheet"""
        blocks = [_code_block("from aspose_cells_foss import Workbook, Worksheet")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        code = _get_code(result)
        assert "from aspose.cells_foss import Workbook, Worksheet" in code

    def test_import_as_rewritten(self):
        """import aspose_cells_foss as ac → import aspose.cells_foss as ac"""
        blocks = [_code_block("import aspose_cells_foss as ac")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        code = _get_code(result)
        assert "import aspose.cells_foss as ac" in code


# ---------------------------------------------------------------------------
# Tests — already-correct imports are unchanged
# ---------------------------------------------------------------------------

class TestCorrectImportsUnchanged:
    """Runtime imports and stdlib are not modified."""

    CANONICAL = "aspose_cells_foss"
    RUNTIME = "aspose.cells_foss"

    def test_runtime_import_unchanged(self):
        """import aspose.cells_foss is already correct → no change."""
        blocks = [_code_block("import aspose.cells_foss")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        assert _get_code(result) == "import aspose.cells_foss"

    def test_from_runtime_import_unchanged(self):
        """from aspose.cells_foss import Workbook → unchanged."""
        blocks = [_code_block("from aspose.cells_foss import Workbook")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        assert "from aspose.cells_foss import Workbook" in _get_code(result)

    def test_stdlib_unchanged(self):
        """import os, import json, from pathlib import Path → unchanged."""
        code = "import os\nimport json\nfrom pathlib import Path"
        blocks = [_code_block(code)]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        assert _get_code(result) == code

    def test_paragraph_blocks_unchanged(self):
        """Paragraph blocks are never modified."""
        blocks = [_para_block("Use import aspose_cells_foss to get started.")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        assert result[0].content == "Use import aspose_cells_foss to get started."

    def test_empty_code_block_unchanged(self):
        """Empty code block → no crash."""
        blocks = [_code_block("")]
        result = _canonicalize_python_imports(blocks, self.CANONICAL, self.RUNTIME)
        assert result[0].content == ""


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases: no runtime, dotted canonical, mixed blocks."""

    def test_no_runtime_falls_back_to_canonical(self):
        """When runtime_import is empty, use canonical as-is."""
        blocks = [_code_block("import something_else")]
        result = _canonicalize_python_imports(blocks, "mypackage", "")
        # No rewrite map since runtime is empty — close variant check applies
        assert len(result) == 1

    def test_no_canonical_no_runtime_is_noop(self):
        """Both empty → return blocks unchanged."""
        blocks = [_code_block("import aspose_cells_foss")]
        result = _canonicalize_python_imports(blocks, "", "")
        assert _get_code(result) == "import aspose_cells_foss"

    def test_canonical_equals_runtime_no_rewrite(self):
        """When canonical == runtime, no rewrite map is built."""
        blocks = [_code_block("import requests")]
        result = _canonicalize_python_imports(blocks, "requests", "requests")
        assert _get_code(result) == "import requests"

    def test_dotted_canonical_with_runtime(self):
        """canonical_import='aspose.cells', runtime_import='aspose.cells' → no rewrite."""
        blocks = [_code_block("import aspose.cells")]
        result = _canonicalize_python_imports(blocks, "aspose.cells", "aspose.cells")
        assert _get_code(result) == "import aspose.cells"

    def test_multiple_code_blocks(self):
        """Multiple code blocks are all fixed."""
        blocks = [
            _code_block("import aspose_cells_foss"),
            _para_block("Some text"),
            _code_block("from aspose_cells_foss import Worksheet"),
        ]
        result = _canonicalize_python_imports(
            blocks, "aspose_cells_foss", "aspose.cells_foss"
        )
        assert "import aspose.cells_foss" in result[0].content
        assert result[1].content == "Some text"
        assert "from aspose.cells_foss import Worksheet" in result[2].content

    def test_mixed_correct_and_wrong_in_same_block(self):
        """Block with both correct and wrong imports."""
        code = "import os\nimport aspose_cells_foss\nfrom aspose.cells_foss import Workbook"
        blocks = [_code_block(code)]
        result = _canonicalize_python_imports(
            blocks, "aspose_cells_foss", "aspose.cells_foss"
        )
        lines = _get_code(result).split("\n")
        assert lines[0] == "import os"
        assert lines[1] == "import aspose.cells_foss"
        assert lines[2] == "from aspose.cells_foss import Workbook"

    def test_submodule_import_preserved(self):
        """from aspose.cells_foss.sub import X → unchanged (runtime root matches)."""
        blocks = [_code_block("from aspose.cells_foss.sub import Helper")]
        result = _canonicalize_python_imports(
            blocks, "aspose_cells_foss", "aspose.cells_foss"
        )
        assert "from aspose.cells_foss.sub import Helper" in _get_code(result)


# ---------------------------------------------------------------------------
# TC-GEN-302: _normalize_imports case-insensitive rewriting
# ---------------------------------------------------------------------------

from launcher.workers.generate.section_validator import _normalize_imports


class TestNormalizeImportsCaseInsensitive:
    """TC-GEN-302: _normalize_imports must handle uppercase Aspose variants."""

    def test_uppercase_aspose_rewritten(self):
        """import Aspose.ThreeD → import aspose.threed"""
        code = "import Aspose.ThreeD"
        result = _normalize_imports(
            code, "aspose_3d_foss", ["aspose.threed"],
            runtime_import="aspose.threed",
        )
        assert "import aspose.threed" in result
        assert "Aspose.ThreeD" not in result

    def test_from_uppercase_aspose_rewritten(self):
        """from Aspose.Cells import Workbook → from aspose.cells import Workbook"""
        code = "from Aspose.Cells import Workbook"
        result = _normalize_imports(
            code, "aspose_cells_foss", ["aspose.cells"],
            runtime_import="aspose.cells",
        )
        assert "from aspose.cells import Workbook" in result
        assert "Aspose.Cells" not in result

    def test_all_caps_rewritten(self):
        """import ASPOSE.CELLS → import aspose.cells"""
        code = "import ASPOSE.CELLS"
        result = _normalize_imports(
            code, "aspose_cells_foss", ["aspose.cells"],
            runtime_import="aspose.cells",
        )
        assert "import aspose.cells" in result

    def test_lowercase_still_rewritten(self):
        """import aspose.threed → import aspose.threed (already correct, no change)."""
        code = "import aspose.threed"
        result = _normalize_imports(
            code, "aspose_3d_foss", ["aspose.threed"],
            runtime_import="aspose.threed",
        )
        assert "import aspose.threed" in result

    def test_non_aspose_imports_unchanged(self):
        """import numpy, import json → unchanged."""
        code = "import numpy\nimport json"
        result = _normalize_imports(
            code, "aspose_cells_foss", ["aspose.cells"],
            runtime_import="aspose.cells",
        )
        assert "import numpy" in result
        assert "import json" in result


# ---------------------------------------------------------------------------
# TC-GEN-302: _sanitize_code_blocks full-path matching
# ---------------------------------------------------------------------------

from launcher.workers.generate.worker import _sanitize_code_blocks


class TestSanitizeCodeBlocksFullPath:
    """TC-GEN-302: _sanitize_code_blocks uses full dotted path matching, not prefix-only."""

    def test_valid_runtime_import_passes(self):
        """import aspose.threed when allowlist has aspose.threed → kept."""
        blocks = [_code_block("import aspose.threed\nscene = Scene()")]
        result = _sanitize_code_blocks(blocks, "aspose.threed", ["aspose.threed"])
        assert len(result) == 1
        assert result[0].type == BlockType.code

    def test_wrong_import_stripped(self):
        """import Aspose.FakeModule not in allowlist → stripped."""
        blocks = [_code_block("import Aspose.FakeModule\nx = 1")]
        result = _sanitize_code_blocks(blocks, "aspose_3d_foss", ["aspose.threed"])
        # Block should be converted to prose (stripped)
        assert result[0].type == BlockType.paragraph

    def test_wrong_cased_import_not_in_allowlist_stripped(self):
        """import Aspose.ThreeD when allowlist is aspose.threed → passes (case matches lowered)."""
        blocks = [_code_block("import Aspose.ThreeD\nscene = Scene()")]
        # Note: Aspose.ThreeD lowered = aspose.threed = in allowlist → should PASS
        result = _sanitize_code_blocks(blocks, "aspose_3d_foss", ["aspose.threed"])
        assert result[0].type == BlockType.code

    def test_paragraph_blocks_unchanged(self):
        """Paragraph blocks pass through regardless."""
        blocks = [_para_block("Use import Aspose.ThreeD to start.")]
        result = _sanitize_code_blocks(blocks, "aspose_3d_foss", ["aspose.threed"])
        assert result[0].type == BlockType.paragraph
        assert "Aspose.ThreeD" in result[0].content

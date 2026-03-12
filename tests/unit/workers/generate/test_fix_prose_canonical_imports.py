"""Tests for _fix_prose_canonical_imports (TC-3888)."""
from __future__ import annotations

import pytest

from launcher.workers.generate.worker import _fix_prose_canonical_imports
from launcher.models.page_ir import BlockIR


def _prose(content: str) -> BlockIR:
    return BlockIR(type="paragraph", content=content)


def _code(content: str, language: str = "python") -> BlockIR:
    return BlockIR(type="code", content=content, language=language)


class TestFixProseCanonicalImports:
    def test_pip_install_replaced(self) -> None:
        block = _prose("Install via `pip install Aspose.Cells` to use.")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "Install via `pip install aspose_cells_foss` to use."

    def test_import_replaced(self) -> None:
        block = _prose("Then run `import Aspose.Cells` in your script.")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "Then run `import aspose_cells_foss` in your script."

    def test_from_import_replaced(self) -> None:
        block = _prose("Use `from Aspose.Cells import Workbook` to get started.")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "Use `from aspose_cells_foss import Workbook` to get started."

    def test_pip3_replaced(self) -> None:
        block = _prose("Run `pip3 install aspose.cells` in the terminal.")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "Run `pip3 install aspose_cells_foss` in the terminal."

    def test_code_block_not_modified(self) -> None:
        block = _code("import Aspose.Cells\nworkbook = Workbook()")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "import Aspose.Cells\nworkbook = Workbook()"

    def test_display_name_prose_not_affected(self) -> None:
        block = _prose("Aspose.Cells is a spreadsheet library for Python.")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "Aspose.Cells is a spreadsheet library for Python."

    def test_correct_import_unchanged(self) -> None:
        block = _prose("Use `import aspose_cells_foss` to start.")
        result = _fix_prose_canonical_imports([block], "aspose_cells_foss")
        assert result[0].content == "Use `import aspose_cells_foss` to start."

    def test_empty_canonical_import_returns_unchanged(self) -> None:
        block = _prose("Use `import Aspose.Cells`.")
        result = _fix_prose_canonical_imports([block], "")
        assert result[0].content == "Use `import Aspose.Cells`."

    def test_none_canonical_import_returns_unchanged(self) -> None:
        block = _prose("Use `pip install Aspose.Cells`.")
        result = _fix_prose_canonical_imports([block], None)  # type: ignore[arg-type]
        assert result[0].content == "Use `pip install Aspose.Cells`."

    def test_multiple_blocks_mixed(self) -> None:
        blocks = [
            _prose("Use `pip install Aspose.Cells` to install."),
            _code("import aspose_cells_foss"),
            _prose("Then `import Aspose.Cells` in the script."),
        ]
        result = _fix_prose_canonical_imports(blocks, "aspose_cells_foss")
        assert result[0].content == "Use `pip install aspose_cells_foss` to install."
        assert result[1].content == "import aspose_cells_foss"  # code block unchanged
        assert result[2].content == "Then `import aspose_cells_foss` in the script."

"""Tests for TC-3908 fixes: wrong python language tag + empty hrefs."""
from __future__ import annotations

import pytest

from launcher.workers.generate.worker import _normalize_code_languages, _fix_empty_hrefs
from launcher.models.page_ir import BlockIR


def _code(content: str, language: str = "") -> BlockIR:
    return BlockIR(type="code", content=content, language=language)


def _prose(content: str) -> BlockIR:
    return BlockIR(type="paragraph", content=content)


def _list_block(items: list[str]) -> BlockIR:
    return BlockIR(type="list", items=items)


class TestNormalizeCodeLanguagesTC3908:
    """TC-3908: correct explicitly wrong python tag on shell content."""

    def test_python_tagged_pip_install_corrected_to_bash(self) -> None:
        block = _code("pip install aspose_cells_foss", "python")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_py_tagged_pip_install_corrected_to_bash(self) -> None:
        block = _code("pip install somelib", "py")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_python_tagged_real_python_unchanged(self) -> None:
        block = _code("import aspose_cells_foss\nwb = Workbook()", "python")
        result = _normalize_code_languages([block])
        assert result[0].language == "python"

    def test_python_tagged_comment_first_line_unchanged(self) -> None:
        """Comment line starting with # does not trigger shell detection."""
        block = _code("# pip install is not needed here\nwb = Workbook()", "python")
        result = _normalize_code_languages([block])
        assert result[0].language == "python"

    def test_bash_tagged_pip_install_unchanged(self) -> None:
        """Already correctly tagged bash blocks are left alone."""
        block = _code("pip install aspose_cells_foss", "bash")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_untagged_pip_install_gets_bash(self) -> None:
        """Untagged shell block still gets bash (original TC-3887 behavior)."""
        block = _code("pip install aspose_cells_foss", "")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_untagged_python_code_gets_python(self) -> None:
        block = _code("wb = Workbook()", "")
        result = _normalize_code_languages([block])
        assert result[0].language == "python"

    def test_javascript_tagged_unchanged(self) -> None:
        """Non-python explicit tags are not modified."""
        block = _code("console.log('hello')", "javascript")
        result = _normalize_code_languages([block])
        assert result[0].language == "javascript"


class TestFixEmptyHrefs:
    """TC-3908: strip empty/unclosed href links from prose and list blocks."""

    def test_empty_href_in_prose_stripped(self) -> None:
        block = _prose("See [Aspose.Cells documentation]() for details.")
        result = _fix_empty_hrefs([block])
        assert result[0].content == "See Aspose.Cells documentation for details."

    def test_unclosed_href_in_prose_stripped(self) -> None:
        """[text]( at end of line → text."""
        block = _prose("- [Aspose.Cells for Python via .NET documentation](\n- [Other link](https://example.com)")
        result = _fix_empty_hrefs([block])
        assert "[" not in result[0].content.split("\n")[0]
        assert "Aspose.Cells for Python via .NET documentation" in result[0].content

    def test_valid_href_not_stripped(self) -> None:
        block = _prose("See [Aspose.Cells](https://aspose.com) for details.")
        result = _fix_empty_hrefs([block])
        assert result[0].content == "See [Aspose.Cells](https://aspose.com) for details."

    def test_empty_href_in_list_item_stripped(self) -> None:
        block = _list_block([
            "[Aspose.Cells documentation]()",
            "[OpenPyXL](https://openpyxl.readthedocs.io/)",
        ])
        result = _fix_empty_hrefs([block])
        assert result[0].items[0] == "Aspose.Cells documentation"
        assert result[0].items[1] == "[OpenPyXL](https://openpyxl.readthedocs.io/)"

    def test_code_block_not_modified(self) -> None:
        block = _code("[text]()")
        result = _fix_empty_hrefs([block])
        assert result[0].content == "[text]()"

    def test_no_empty_hrefs_unchanged(self) -> None:
        block = _prose("Normal prose with no links.")
        result = _fix_empty_hrefs([block])
        assert result[0].content == "Normal prose with no links."

    def test_multiple_empty_hrefs_all_stripped(self) -> None:
        block = _prose("See [A]() and [B]() for info.")
        result = _fix_empty_hrefs([block])
        assert result[0].content == "See A and B for info."

"""Tests for _canonicalize_product_name in section_validator (TC-QF-01)."""
from __future__ import annotations

from launcher.workers.generate.section_validator import _canonicalize_product_name


def test_aspire_cells_fixed():
    """'Aspire.Cells' is corrected to 'Aspose.Cells'."""
    text = "The Aspire.Cells library provides spreadsheet support."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert "Aspire.Cells" not in result
    assert "Aspose.Cells" in result


def test_aspuse_note_fixed():
    """'Aspuse.Note' is corrected to 'Aspose.Note'."""
    text = "Use Aspuse.Note for notebook processing."
    result = _canonicalize_product_name(text, "Aspose.Note")
    assert "Aspuse.Note" not in result
    assert "Aspose.Note" in result


def test_apose_fixed():
    """'Apose.Cells' is corrected to 'Aspose.Cells'."""
    text = "Apose.Cells handles Excel files."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert "Apose.Cells" not in result
    assert "Aspose.Cells" in result


def test_aspsoe_fixed():
    """'Aspsoe.Cells' is corrected to 'Aspose.Cells'."""
    text = "Aspsoe.Cells is a library."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert "Aspsoe.Cells" not in result
    assert "Aspose.Cells" in result


def test_asopse_fixed():
    """'Asopse.Cells' is corrected to 'Aspose.Cells'."""
    text = "Asopse.Cells provides parsing."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert "Asopse.Cells" not in result
    assert "Aspose.Cells" in result


def test_space_dot_fixed():
    """'Aspose. Cells' (space after dot) is corrected to 'Aspose.Cells'."""
    text = "The Aspose. Cells library loads workbooks."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert "Aspose. Cells" not in result
    assert "Aspose.Cells" in result


def test_correct_name_unchanged():
    """Already correct 'Aspose.Cells' stays unchanged."""
    text = "Aspose.Cells is the best choice."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert result == text


def test_doubled_qualifier_fixed():
    """'for Python for Python' is collapsed to 'for Python'."""
    text = "Install Aspose.Cells for Python for Python via pip."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    assert "for Python for Python" not in result
    assert "for Python" in result


def test_code_block_not_touched():
    """Misspellings inside code blocks are preserved."""
    text = "Use Aspire.Cells:\n\n```python\nimport Aspire.Cells\n```\n\nDone."
    result = _canonicalize_product_name(text, "Aspose.Cells")
    # Prose part should be fixed
    assert result.startswith("Use Aspose.Cells")
    # Code block should preserve the misspelling
    assert "import Aspire.Cells" in result


def test_empty_content_safe():
    """Empty content returns empty without error."""
    assert _canonicalize_product_name("", "Aspose.Cells") == ""


def test_no_product_name_safe():
    """Empty product_name returns content unchanged."""
    text = "Some text."
    assert _canonicalize_product_name(text, "") == text


def test_product_name_no_dot_safe():
    """Product name without dot returns content unchanged."""
    text = "Some text with Aspire."
    assert _canonicalize_product_name(text, "Aspose") == text

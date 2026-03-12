"""Tests for _dedup_code_blocks in ir_renderer — TC-3873."""
from __future__ import annotations

import pytest

from launcher.shared.ir_renderer import _dedup_code_blocks, _normalize_code


class TestNormalizeCode:
    def test_strips_whitespace(self):
        code = "  x = 1  \n  y = 2  "
        assert _normalize_code(code) == "x = 1\ny = 2"

    def test_strips_trailing_newline(self):
        code = "x = 1\n"
        assert _normalize_code(code) == "x = 1"


class TestDedupCodeBlocks:
    """Core deduplication behavior tests."""

    _BLOCK_A = (
        "```python\n"
        "from aspose_cells_foss import Workbook\n"
        "import os\n"
        "import io\n"
        "wb = Workbook()\n"
        "wb.save('out.xlsx')\n"
        "```"
    )

    _BLOCK_B = (
        "```python\n"
        "from aspose_cells_foss import License\n"
        "lic = License()\n"
        "lic.set_license('license.lic')\n"
        "print('Licensed')\n"
        "```"
    )

    def test_no_duplicates_unchanged(self):
        content = f"## Section 1\n\n{self._BLOCK_A}\n\n## Section 2\n\n{self._BLOCK_B}\n"
        result = _dedup_code_blocks(content)
        assert self._BLOCK_A in result
        assert self._BLOCK_B in result

    def test_exact_duplicate_removed(self):
        content = (
            f"## Section 1\n\n{self._BLOCK_A}\n\n"
            f"## Section 2\n\n{self._BLOCK_A}\n"
        )
        result = _dedup_code_blocks(content)
        # First occurrence kept, second removed
        assert result.count("from aspose_cells_foss import Workbook") == 1

    def test_triple_duplicate_only_first_kept(self):
        content = (
            f"## S1\n\n{self._BLOCK_A}\n\n"
            f"## S2\n\n{self._BLOCK_A}\n\n"
            f"## S3\n\n{self._BLOCK_A}\n"
        )
        result = _dedup_code_blocks(content)
        assert result.count("wb = Workbook()") == 1

    def test_distinct_blocks_both_kept(self):
        content = (
            f"## Section 1\n\n{self._BLOCK_A}\n\n"
            f"## Section 2\n\n{self._BLOCK_B}\n"
        )
        result = _dedup_code_blocks(content)
        assert "wb.save" in result
        assert "lic.set_license" in result

    def test_short_block_below_threshold_not_deduped(self):
        """Single-line pip install or 2-line import blocks must be preserved."""
        short_block = "```python\nimport os\n```"
        content = f"## S1\n\n{short_block}\n\n## S2\n\n{short_block}\n"
        result = _dedup_code_blocks(content)
        # Both occurrences kept (below _DEDUP_MIN_LINES=3)
        assert result.count("import os") == 2

    def test_whitespace_variants_treated_as_same(self):
        """Trailing whitespace differences are normalized — treated as duplicate."""
        block_with_trailing = (
            "```python\n"
            "from aspose_cells_foss import Workbook   \n"
            "import os  \n"
            "import io  \n"
            "wb = Workbook()\n"
            "wb.save('out.xlsx')\n"
            "```"
        )
        content = (
            f"## S1\n\n{self._BLOCK_A}\n\n"
            f"## S2\n\n{block_with_trailing}\n"
        )
        result = _dedup_code_blocks(content)
        assert result.count("wb.save") == 1

    def test_no_triple_blank_lines(self):
        """Blank lines introduced by removed blocks are collapsed."""
        content = (
            f"## S1\n\n{self._BLOCK_A}\n\n"
            f"## S2\n\n{self._BLOCK_A}\n\n"
            f"## S3\n\nSome text.\n"
        )
        result = _dedup_code_blocks(content)
        assert "\n\n\n" not in result

    def test_empty_string_input(self):
        assert _dedup_code_blocks("") == ""

    def test_no_code_blocks_unchanged(self):
        content = "## Section\n\nSome prose text.\n"
        result = _dedup_code_blocks(content)
        assert result == content

    def test_different_language_tags_same_body_deduped(self):
        """Deduplication is keyed on body content only — language tag is ignored.
        If two blocks have identical bodies (but different language tags),
        the second is treated as a duplicate and removed. This is intentional:
        copy-pasted code blocks are duplicates regardless of tag label."""
        block_py = (
            "```python\n"
            "from aspose_cells_foss import Workbook\n"
            "wb = Workbook()\n"
            "wb.save('out.xlsx')\n"
            "wb.close()\n"
            "```"
        )
        block_js = (
            "```javascript\n"
            "from aspose_cells_foss import Workbook\n"
            "wb = Workbook()\n"
            "wb.save('out.xlsx')\n"
            "wb.close()\n"
            "```"
        )
        content = f"## S1\n\n{block_py}\n\n## S2\n\n{block_js}\n"
        result = _dedup_code_blocks(content)
        # First block kept, second removed (same body = duplicate)
        assert "```python" in result
        assert "```javascript" not in result

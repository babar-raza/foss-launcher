"""TC-2821: Tests for gate_product_name_integrity.

Covers:
- Corrupted brand names detected ("Aspose. Note" → error)
- Clean brand names pass ("Aspose.Note" → no issues)
- Code fences are skipped (no false positives from code)
- Severity escalation by profile
- Empty/missing site dir → graceful pass
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_product_name_integrity import (
    execute_gate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProductNameIntegrity:

    def test_clean_content_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspose.Note is great for OneNote.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_corrupted_name_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Use Aspose. Note for OneNote processing.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "PRODUCT_NAME_CORRUPTED"

    def test_corrupted_cells_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspose. Cells handles spreadsheets.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_double_space_corruption(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspose.  Words for Python.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_code_fence_skipped(self, tmp_path):
        """Corrupted name inside code fence should NOT be flagged."""
        run_dir = tmp_path / "run"
        content = "Good text.\n\n```python\n# Aspose. Note example\n```\n\nMore good text."
        _write_md(run_dir, "page.md", content)
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_prod_profile_blocker_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Use Aspose. Note library.")
        passed, issues = execute_gate(run_dir, "prod")
        assert passed is False
        assert issues[0]["severity"] == "blocker"

    def test_local_profile_warn_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Use Aspose. Note library.")
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True  # warn doesn't fail gate
        assert issues[0]["severity"] == "warn"

    def test_multiple_corruptions_all_flagged(self, tmp_path):
        run_dir = tmp_path / "run"
        content = "Aspose. Note and Aspose. Cells are both corrupted."
        _write_md(run_dir, "page.md", content)
        passed, issues = execute_gate(run_dir, "ci")
        assert len(issues) >= 2

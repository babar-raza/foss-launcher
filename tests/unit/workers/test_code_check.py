"""Tests for check_code — TC-3872: stdlib import allowlist."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.code import check_code, _extract_module_name


def _make_content(code: str, lang: str = "python") -> str:
    return f"---\ntitle: Test\nslug: test\n---\n\n```{lang}\n{code}\n```\n"


class TestExtractModuleName:
    def test_simple_import(self):
        assert _extract_module_name("import os") == "os"

    def test_dotted_import(self):
        assert _extract_module_name("import os.path") == "os"

    def test_from_import(self):
        assert _extract_module_name("from pathlib import Path") == "pathlib"

    def test_from_dotted_import(self):
        assert _extract_module_name("from xml.etree import ElementTree") == "xml"

    def test_import_alias(self):
        assert _extract_module_name("import aspose_cells_foss as cells") == "aspose_cells_foss"

    def test_empty_string(self):
        assert _extract_module_name("") == ""


class TestStdlibAllowlist:
    """TC-3872: stdlib imports must not be flagged alongside canonical."""

    CANONICAL = "aspose_cells_foss"

    def _check(self, code: str) -> list:
        content = _make_content(code)
        return check_code(content, "test", canonical_import=self.CANONICAL)

    def test_os_import_not_flagged(self):
        code = "import os\nimport aspose_cells_foss as cells\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_io_import_not_flagged(self):
        code = "import io\nfrom aspose_cells_foss import Workbook\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_pathlib_import_not_flagged(self):
        code = "from pathlib import Path\nimport aspose_cells_foss as cells\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_sys_import_not_flagged(self):
        code = "import sys\nfrom aspose_cells_foss import License\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_json_import_not_flagged(self):
        code = "import json\nimport aspose_cells_foss as cells\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_multiple_stdlib_imports_not_flagged(self):
        code = (
            "import os\nimport io\nfrom pathlib import Path\n"
            "import aspose_cells_foss as cells\n\ncells.Workbook()\n"
        )
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_competing_library_still_flagged(self):
        """openpyxl and xlrd are competing packages — must still be caught."""
        code = "import openpyxl\nfrom aspose_cells_foss import Workbook\n"
        findings = self._check(code)
        assert any("Import not in allowlist" in f.message for f in findings)

    def test_pandas_still_flagged(self):
        code = "import pandas as pd\nfrom aspose_cells_foss import Workbook\n"
        findings = self._check(code)
        assert any("Import not in allowlist" in f.message for f in findings)

    def test_canonical_import_itself_not_flagged(self):
        code = "import aspose_cells_foss as cells\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_from_canonical_not_flagged(self):
        code = "from aspose_cells_foss import Workbook, License\n"
        findings = self._check(code)
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_user_allowlist_overrides(self):
        """User-configured allowlist allows additional third-party packages."""
        code = "import numpy as np\nfrom aspose_cells_foss import Workbook\n"
        content = _make_content(code)
        findings = check_code(content, "test", canonical_import=self.CANONICAL, import_allowlist=["numpy"])
        assert not any("Import not in allowlist" in f.message for f in findings)

    def test_no_canonical_import_skips_check(self):
        """When canonical_import is empty, import check is skipped entirely."""
        code = "import openpyxl\n"
        content = _make_content(code)
        findings = check_code(content, "test", canonical_import="")
        assert not any("Import not in allowlist" in f.message for f in findings)


class TestRuntimeImport:
    """TC-HYBRID-01: runtime_import separates pip package name from runtime module path."""

    def test_check_code_runtime_import_valid(self):
        """check_code accepts aspose.threed when runtime_import='aspose.threed'."""
        content = '```python\nimport aspose.threed\n\nscene = aspose.threed.Scene()\n```'
        findings = check_code(
            content, "test-slug",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
        )
        import_findings = [f for f in findings if "Import not in allowlist" in f.message]
        assert not import_findings, f"Expected no import findings, got: {import_findings}"

    def test_check_code_runtime_import_rejects_pip_name(self):
        """check_code rejects pip name import when runtime_import='aspose.threed'."""
        content = '```python\nimport aspose_3d_foss\n\nscene = aspose_3d_foss.Scene()\n```'
        findings = check_code(
            content, "test-slug",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
        )
        import_findings = [f for f in findings if "Import not in allowlist" in f.message]
        assert import_findings, "Expected import finding for pip-name import when runtime_import set"

    def test_check_code_no_runtime_import_fallback(self):
        """When runtime_import is empty, falls back to canonical_import for validation."""
        content = '```python\nimport aspose_3d_foss\n\nscene = aspose_3d_foss.Scene()\n```'
        findings = check_code(
            content, "test-slug",
            canonical_import="aspose_3d_foss",
            runtime_import="",
        )
        import_findings = [f for f in findings if "Import not in allowlist" in f.message]
        assert not import_findings, f"Expected no import findings with fallback to canonical, got: {import_findings}"


class TestExistingBehavior:
    """Regression tests — pre-existing logic must not change."""

    def test_missing_language_tag_flagged(self):
        content = "---\ntitle: T\nslug: t\n---\n\n```\nsome code\n```\n"
        findings = check_code(content, "t")
        assert any("missing language tag" in f.message for f in findings)

    def test_python_syntax_error_flagged(self):
        content = _make_content("def broken(\n")
        findings = check_code(content, "test")
        assert any("syntax error" in f.message.lower() for f in findings)

    def test_valid_python_no_findings(self):
        content = _make_content("x = 1\nprint(x)\n")
        findings = check_code(content, "test")
        assert findings == []

    def test_no_code_blocks_no_findings(self):
        content = "---\ntitle: T\nslug: t\n---\n\nNo code here.\n"
        findings = check_code(content, "test")
        assert findings == []

    def test_shell_command_not_ast_validated(self):
        content = _make_content("pip install aspose-cells-foss")
        findings = check_code(content, "test")
        assert not any("syntax error" in f.message.lower() for f in findings)

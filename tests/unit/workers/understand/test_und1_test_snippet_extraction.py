"""Tests for UND-1 (TC-5205): test function snippet extraction from repo test files.

Verifies quality filters, boilerplate stripping, length caps, and dedup behavior
of _extract_test_snippets().
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from launcher.workers.understand.extract._snippets import (
    _extract_test_snippets,
    _UND1_MAX_NONCOMMENT_LINES,
    _UND1_MIN_NONCOMMENT_LINES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(canonical_import: str = "aspose_cells_foss") -> MagicMock:
    p = MagicMock()
    p.canonical_import = canonical_import
    p.runtime_import = canonical_import
    p.lang_tag = "python"
    return p


def _make_api_surface(public_classes: list[str] | None = None) -> MagicMock:
    surface = MagicMock()
    surface.public_classes = public_classes or ["Workbook", "Worksheet", "Cell"]
    surface.class_briefs = []
    surface.enums = []
    surface.import_allowlist = [f"{_make_product().canonical_import}"]
    return surface


def _make_repo_info(test_paths: list[str]) -> MagicMock:
    ri = MagicMock()
    ri.test_paths = test_paths
    ri.example_paths = []
    ri.doc_paths = []
    ri.source_paths = []
    ri.file_tree = []
    return ri


def _write_test_file(tmp_path: Path, filename: str, content: str) -> Path:
    f = tmp_path / filename
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Test 1: Basic extraction — test function with PascalCase class is extracted
# ---------------------------------------------------------------------------

def test_extract_test_snippets_basic(tmp_path):
    """A test function referencing a public class should be extracted."""
    src = """\
        from aspose_cells_foss import Workbook

        def test_load_workbook():
            wb = Workbook("test.xlsx")
            wb.save("out.xlsx")
    """
    _write_test_file(tmp_path, "test_basic.py", src)

    product = _make_product()
    api_surface = _make_api_surface(["Workbook"])
    repo_info = _make_repo_info(["test_basic.py"])
    seen: set[str] = set()

    snippets = _extract_test_snippets(tmp_path, repo_info, product, api_surface, [], seen)

    assert len(snippets) >= 1, "Expected at least one snippet from the test function"
    codes = [s.code for s in snippets]
    assert any("Workbook" in c for c in codes), "Workbook class usage should appear in extracted snippet"
    # Verify syntax validity
    for s in snippets:
        assert s.syntax_valid is True
        ast.parse(s.code)  # must not raise
    # Verify source metadata
    for s in snippets:
        assert s.source_type == "extracted"
        assert s.language == "python"
        assert s.source_file == "test_basic.py"


# ---------------------------------------------------------------------------
# Test 2: setUp/tearDown methods are NOT extracted
# ---------------------------------------------------------------------------

def test_extract_test_snippets_skips_setup(tmp_path):
    """setUp and tearDown methods must never appear as extracted snippets."""
    src = """\
        from aspose_cells_foss import Workbook
        import unittest

        class TestWorkbook(unittest.TestCase):
            def setUp(self):
                self.wb = Workbook()

            def tearDown(self):
                del self.wb

            def test_create(self):
                wb = Workbook("demo.xlsx")
                wb.save("out.xlsx")
    """
    _write_test_file(tmp_path, "test_setup.py", src)

    product = _make_product()
    api_surface = _make_api_surface(["Workbook"])
    repo_info = _make_repo_info(["test_setup.py"])
    seen: set[str] = set()

    snippets = _extract_test_snippets(tmp_path, repo_info, product, api_surface, [], seen)

    # None of the extracted snippets should contain the setUp / tearDown bodies
    # (setUp contains "self.wb = Workbook()" and tearDown "del self.wb")
    for s in snippets:
        # The function name "setUp" should not appear as a standalone snippet body
        assert "def setUp" not in s.code, "setUp body leaked into snippets"
        assert "def tearDown" not in s.code, "tearDown body leaked into snippets"


# ---------------------------------------------------------------------------
# Test 3: Functions exceeding _UND1_MAX_NONCOMMENT_LINES are NOT extracted
# ---------------------------------------------------------------------------

def test_extract_test_snippets_skips_long_functions(tmp_path):
    """Functions with more than _UND1_MAX_NONCOMMENT_LINES non-comment lines are skipped."""
    # Build a function with 65 substantive lines
    body_lines = ["    wb = Workbook()"] + [f"    x{i} = wb" for i in range(64)]
    body = "\n".join(body_lines)

    src = f"""\
from aspose_cells_foss import Workbook

def test_long_function():
{body}
"""
    _write_test_file(tmp_path, "test_long.py", src)

    product = _make_product()
    api_surface = _make_api_surface(["Workbook"])
    repo_info = _make_repo_info(["test_long.py"])
    seen: set[str] = set()

    snippets = _extract_test_snippets(tmp_path, repo_info, product, api_surface, [], seen)

    # The long function should be excluded
    for s in snippets:
        nc = [ln for ln in s.code.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        assert len(nc) <= _UND1_MAX_NONCOMMENT_LINES, (
            f"Snippet has {len(nc)} non-comment lines, exceeds cap of {_UND1_MAX_NONCOMMENT_LINES}"
        )


# ---------------------------------------------------------------------------
# Test 4: Assertion lines are stripped from extracted snippets
# ---------------------------------------------------------------------------

def test_extract_test_snippets_strips_assertions(tmp_path):
    """self.assertEqual / self.assertIsNotNone lines should not appear in extracted snippets."""
    src = """\
        from aspose_cells_foss import Workbook

        def test_save_strips_assertions():
            wb = Workbook("test.xlsx")
            result = wb.save("out.xlsx")
            self.assertEqual(result, True)
            self.assertIsNotNone(wb)
    """
    _write_test_file(tmp_path, "test_assertions.py", src)

    product = _make_product()
    api_surface = _make_api_surface(["Workbook"])
    repo_info = _make_repo_info(["test_assertions.py"])
    seen: set[str] = set()

    snippets = _extract_test_snippets(tmp_path, repo_info, product, api_surface, [], seen)

    for s in snippets:
        assert "assertEqual" not in s.code, "assertEqual leaked into snippet"
        assert "assertIsNotNone" not in s.code, "assertIsNotNone leaked into snippet"


# ---------------------------------------------------------------------------
# Test 5: Extracted snippets are syntactically valid Python
# ---------------------------------------------------------------------------

def test_extract_test_snippets_validates_syntax(tmp_path):
    """Every extracted snippet must be parseable by ast.parse()."""
    src = """\
        from aspose_cells_foss import Workbook, Worksheet

        def test_worksheet_access():
            wb = Workbook("test.xlsx")
            ws = wb.worksheets[0]
            ws.cells["A1"].value = "Hello"
            wb.save("output.xlsx")

        def test_add_worksheet():
            wb = Workbook()
            wb.worksheets.add("Sheet2")
            wb.save("workbook.xlsx")
    """
    _write_test_file(tmp_path, "test_syntax.py", src)

    product = _make_product()
    api_surface = _make_api_surface(["Workbook", "Worksheet"])
    repo_info = _make_repo_info(["test_syntax.py"])
    seen: set[str] = set()

    snippets = _extract_test_snippets(tmp_path, repo_info, product, api_surface, [], seen)

    assert len(snippets) >= 1, "Expected at least one valid snippet"
    for s in snippets:
        try:
            ast.parse(s.code)
        except SyntaxError as exc:
            pytest.fail(f"Extracted snippet has invalid Python syntax: {exc}\n---\n{s.code}")
        assert s.syntax_valid is True


# ---------------------------------------------------------------------------
# Test 6: Dedup — same snippet from two different files is only added once
# ---------------------------------------------------------------------------

def test_extract_test_snippets_dedup_via_shared_seen_hashes(tmp_path):
    """If seen_hashes already contains the snippet hash, it should not be re-added."""
    src = """\
from aspose_cells_foss import Workbook

def test_create_workbook():
    wb = Workbook("demo.xlsx")
    wb.save("out.xlsx")
"""
    f1 = tmp_path / "test_a.py"
    f2 = tmp_path / "test_b.py"
    f1.write_text(src, encoding="utf-8")
    f2.write_text(src, encoding="utf-8")

    product = _make_product()
    api_surface = _make_api_surface(["Workbook"])
    repo_info = _make_repo_info(["test_a.py", "test_b.py"])
    seen: set[str] = set()

    snippets = _extract_test_snippets(tmp_path, repo_info, product, api_surface, [], seen)

    # Even though both files have identical code, only one snippet should be produced
    codes = [s.code for s in snippets]
    # Count unique codes
    unique = set(codes)
    assert len(codes) == len(unique), (
        f"Duplicate snippets produced from identical test files: {len(codes)} snippets, {len(unique)} unique"
    )

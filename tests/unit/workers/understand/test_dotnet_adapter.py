"""Tests for TC-4215: C# (.NET) adapter — typed method extraction via ts_analyzer.

Verifies that DotNetExtractor.extract_class_details() populates method_details
and property_details via ts_analyzer with explicit language="csharp".

Note: "csharp" maps via _LANG_PACK_ALIASES to "_c_sharp_separate", which loads
the tree_sitter_c_sharp package (installed separately).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.models.product import ProductIdentity


def _make_product(**overrides) -> ProductIdentity:
    defaults = dict(
        family="cells",
        platform="dotnet",
        display_name="Aspose.Cells for .NET",
        canonical_import="Aspose.Cells",
        repo_url="https://example.com",
    )
    defaults.update(overrides)
    return ProductIdentity(**defaults)


# ---------------------------------------------------------------------------
# C# fixture source
# ---------------------------------------------------------------------------

_CS_CLASS_SOURCE = """\
using System;

namespace Aspose.Cells
{
    /// <summary>
    /// Represents an Excel workbook.
    /// </summary>
    public class Workbook
    {
        /// <summary>Gets the worksheets collection.</summary>
        public WorksheetCollection Worksheets { get; private set; }

        /// <summary>
        /// Load a workbook from the specified file path.
        /// </summary>
        /// <param name="filePath">Path to the Excel file.</param>
        /// <returns>True if loaded successfully.</returns>
        public bool Load(string filePath)
        {
            return true;
        }

        /// <summary>
        /// Save the workbook to the specified path.
        /// </summary>
        /// <param name="outputPath">Destination file path.</param>
        /// <param name="format">Output file format.</param>
        public void Save(string outputPath, FileFormatType format)
        {
            // implementation
        }

        /// <summary>
        /// Create an empty workbook instance.
        /// </summary>
        public static Workbook Create()
        {
            return new Workbook();
        }
    }

    /// <summary>Supported file format types.</summary>
    public enum FileFormatType
    {
        Xlsx = 0,
        Csv = 1,
        Pdf = 2,
    }
}
"""


class TestDotNetAdapterTypedMethods:
    """TC-4215: C# adapter — typed method extraction."""

    def test_extract_class_details_returns_method_details(self, tmp_path: Path):
        """extract_class_details returns method_details for a C# class."""
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        cs_file = tmp_path / "Workbook.cs"
        cs_file.write_text(_CS_CLASS_SOURCE, encoding="utf-8")

        extractor = DotNetExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(cs_file, tmp_path, product)

        assert isinstance(classes, list), "extract_class_details must return a list"
        assert len(classes) >= 1, "At least one class (Workbook) must be extracted"

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None, "Workbook class must be extracted"

        method_details = workbook.get("method_details", [])
        assert len(method_details) > 0, "method_details must be non-empty for Workbook"

        method_names = [m["name"] for m in method_details]
        assert "Load" in method_names, "'Load' method must appear in method_details"
        assert "Save" in method_names, "'Save' method must appear in method_details"

    def test_method_has_parameter_info(self, tmp_path: Path):
        """Load(string filePath) must have parameter information."""
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        cs_file = tmp_path / "Workbook.cs"
        cs_file.write_text(_CS_CLASS_SOURCE, encoding="utf-8")

        extractor = DotNetExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(cs_file, tmp_path, product)

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None

        method_details = workbook.get("method_details", [])
        load_method = next((m for m in method_details if m["name"] == "Load"), None)
        assert load_method is not None, "Load method must be in method_details"

        params = load_method.get("parameters", [])
        assert len(params) >= 1, "Load(string filePath) must have at least one parameter"

    def test_enum_class_extracted(self, tmp_path: Path):
        """C# enum FileFormatType must be extracted with is_enum=True and populated members.

        TC-GAP-02: ts_analyzer now handles 'enum_member_declaration_list' (C# grammar)
        in addition to 'enum_body' (TypeScript). This test asserts that enum_members
        is fully populated for C# enums.
        """
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        cs_file = tmp_path / "Workbook.cs"
        cs_file.write_text(_CS_CLASS_SOURCE, encoding="utf-8")

        extractor = DotNetExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(cs_file, tmp_path, product)

        enum_class = next((c for c in classes if c["name"] == "FileFormatType"), None)
        assert enum_class is not None, "FileFormatType enum must be extracted"
        assert enum_class.get("is_enum", False) is True, "is_enum must be True for C# enum"
        assert isinstance(enum_class.get("enum_members", []), list), "enum_members must be a list"
        member_names = [m["name"] for m in enum_class.get("enum_members", [])]
        assert len(member_names) > 0, "C# enum_members must be populated after TC-GAP-02"
        assert "Xlsx" in member_names, "'Xlsx' must be in FileFormatType enum_members"
        assert "Csv" in member_names, "'Csv' must be in FileFormatType enum_members"
        assert "Pdf" in member_names, "'Pdf' must be in FileFormatType enum_members"

    def test_uses_csharp_language_explicitly(self, tmp_path: Path):
        """Adapter must call ts_analyzer with language='csharp'."""
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        cs_file = tmp_path / "Workbook.cs"
        cs_file.write_text(_CS_CLASS_SOURCE, encoding="utf-8")

        extractor = DotNetExtractor()
        product = _make_product()

        captured_langs: list[str] = []

        from launcher.shared.ts_analyzer import analyzer as _orig_analyzer
        orig_analyze = _orig_analyzer.analyze_file

        def _mock_analyze(path, language, **kw):
            captured_langs.append(language)
            return orig_analyze(path, language, **kw)

        with patch(
            "launcher.shared.ts_analyzer.analyzer.analyze_file",
            side_effect=_mock_analyze,
        ):
            classes = extractor.extract_class_details(cs_file, tmp_path, product)

        assert "csharp" in captured_langs, "C# adapter must dispatch with language='csharp'"

    def test_fallback_when_ts_analyzer_raises(self, tmp_path: Path):
        """When ts_analyzer raises, adapter falls back to code_analyzer."""
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        cs_file = tmp_path / "Simple.cs"
        cs_file.write_text(
            "public class Simple { public void DoWork() {} }",
            encoding="utf-8",
        )

        extractor = DotNetExtractor()
        product = _make_product()

        with patch(
            "launcher.shared.ts_analyzer.analyzer.analyze_file",
            side_effect=RuntimeError("simulated failure"),
        ):
            classes = extractor.extract_class_details(cs_file, tmp_path, product)

        # Must not raise; fallback should return list
        assert isinstance(classes, list)

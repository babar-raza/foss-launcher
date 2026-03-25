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


# ===========================================================================
# UND-02: XML doc comment extraction tests
# ===========================================================================


class TestXmlDocCommentExtraction:
    """UND-02: Verify XML doc comment extraction and enrichment."""

    def test_extract_xml_doc_comment_basic(self):
        from launcher.workers.understand.adapters._dotnet import _extract_xml_doc_comment
        lines = [
            "    /// <summary>",
            "    /// Represents a 3D scene.",
            "    /// </summary>",
            "    public class Scene",
        ]
        doc = _extract_xml_doc_comment(lines, 3)
        assert "Represents a 3D scene" in doc

    def test_extract_xml_doc_comment_multiline(self):
        from launcher.workers.understand.adapters._dotnet import _extract_xml_doc_comment
        lines = [
            "    /// <summary>",
            "    /// Loads a model from file.",
            "    /// Supports FBX and OBJ formats.",
            "    /// </summary>",
            "    public void Open(string path)",
        ]
        doc = _extract_xml_doc_comment(lines, 4)
        assert "Loads a model" in doc
        assert "FBX" in doc

    def test_extract_xml_doc_comment_none_present(self):
        from launcher.workers.understand.adapters._dotnet import _extract_xml_doc_comment
        lines = [
            "    public int Count { get; set; }",
            "    public class Scene",
        ]
        doc = _extract_xml_doc_comment(lines, 1)
        assert doc == ""

    def test_extract_xml_doc_comment_with_see_cref(self):
        from launcher.workers.understand.adapters._dotnet import _extract_xml_doc_comment
        lines = [
            '    /// <summary>',
            '    /// Opens the <see cref="Scene"/> from a stream.',
            '    /// </summary>',
            '    public void Load(Stream s)',
        ]
        doc = _extract_xml_doc_comment(lines, 3)
        assert "<see" not in doc, "XML tags should be stripped"
        assert "Opens" in doc

    def test_extract_xml_doc_comment_attribute_between(self):
        from launcher.workers.understand.adapters._dotnet import _extract_xml_doc_comment
        lines = [
            "    /// <summary>",
            "    /// Test method doc.",
            "    /// </summary>",
            "    [Obsolete]",
            "    public class OldScene",
        ]
        doc = _extract_xml_doc_comment(lines, 4)
        assert "Test method doc" in doc

    def test_enrich_populates_docstring_on_class(self):
        import tempfile
        from pathlib import Path
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        content = (
            "namespace Aspose.ThreeD {\n"
            "    /// <summary>\n"
            "    /// The main scene container.\n"
            "    /// </summary>\n"
            "    public class Scene {\n"
            "    }\n"
            "}\n"
        )
        with tempfile.NamedTemporaryFile(suffix=".cs", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            extractor = DotNetExtractor()
            classes = [{"name": "Scene"}]
            enriched = extractor._enrich_with_xml_doc_comments(file_path, classes)
            assert enriched[0].get("docstring"), "Should populate docstring from XML doc comment"
            assert "main scene container" in enriched[0]["docstring"]
        finally:
            file_path.unlink(missing_ok=True)

    def test_enrich_does_not_overwrite_existing_docstring(self):
        import tempfile
        from pathlib import Path
        from launcher.workers.understand.adapters._dotnet import DotNetExtractor

        content = (
            "namespace Aspose.ThreeD {\n"
            "    /// <summary>\n"
            "    /// New doc.\n"
            "    /// </summary>\n"
            "    public class Scene {\n"
            "    }\n"
            "}\n"
        )
        with tempfile.NamedTemporaryFile(suffix=".cs", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            file_path = Path(f.name)

        try:
            extractor = DotNetExtractor()
            classes = [{"name": "Scene", "docstring": "Existing doc"}]
            enriched = extractor._enrich_with_xml_doc_comments(file_path, classes)
            assert enriched[0]["docstring"] == "Existing doc", "Should not overwrite existing docstring"
        finally:
            file_path.unlink(missing_ok=True)


# ── SR-12: TargetFramework extraction ────────────────────────────────


class TestParseCsprojTargetFramework:
    """Verify shared_facts.target_frameworks is populated from .csproj."""

    def _make_csproj(self, tmp_path: Path, content: str) -> Path:
        csproj = tmp_path / "MyLib" / "MyLib.csproj"
        csproj.parent.mkdir(parents=True, exist_ok=True)
        csproj.write_text(content, encoding="utf-8")
        return csproj

    def test_single_target_framework(self, tmp_path):
        from launcher.workers.scout.scout import _extract_shared_facts, _walk_file_tree

        self._make_csproj(tmp_path, """\
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
    <PackageId>MyLib</PackageId>
  </PropertyGroup>
</Project>
""")
        file_tree, file_index = _walk_file_tree(tmp_path)
        sf = _extract_shared_facts(tmp_path, file_tree, file_index)
        assert sf.target_frameworks == ["net6.0"]

    def test_multi_target_frameworks_split(self, tmp_path):
        from launcher.workers.scout.scout import _extract_shared_facts, _walk_file_tree

        self._make_csproj(tmp_path, """\
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net6.0;netstandard2.0</TargetFrameworks>
    <PackageId>MyLib</PackageId>
  </PropertyGroup>
</Project>
""")
        file_tree, file_index = _walk_file_tree(tmp_path)
        sf = _extract_shared_facts(tmp_path, file_tree, file_index)
        assert "net6.0" in sf.target_frameworks
        assert "netstandard2.0" in sf.target_frameworks

    def test_no_target_framework_returns_empty(self, tmp_path):
        from launcher.workers.scout.scout import _extract_shared_facts, _walk_file_tree

        self._make_csproj(tmp_path, """\
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <PackageId>MyLib</PackageId>
  </PropertyGroup>
</Project>
""")
        file_tree, file_index = _walk_file_tree(tmp_path)
        sf = _extract_shared_facts(tmp_path, file_tree, file_index)
        assert sf.target_frameworks == []

    def test_msbuild_variable_filtered_out(self, tmp_path):
        from launcher.workers.scout.scout import _extract_shared_facts, _walk_file_tree

        self._make_csproj(tmp_path, """\
<Project>
  <PropertyGroup>
    <TargetFramework>$(DefaultTargetFramework)</TargetFramework>
  </PropertyGroup>
</Project>
""")
        file_tree, file_index = _walk_file_tree(tmp_path)
        sf = _extract_shared_facts(tmp_path, file_tree, file_index)
        assert sf.target_frameworks == []

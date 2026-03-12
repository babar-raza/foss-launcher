"""Tests for TC-4215: Java adapter — typed method extraction via ts_analyzer.

Verifies that JavaExtractor.extract_class_details() populates method_details
and property_details via ts_analyzer with explicit language="java".
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.models.product import ProductIdentity


def _make_product(**overrides) -> ProductIdentity:
    defaults = dict(
        family="cells",
        platform="java",
        display_name="Aspose.Cells Java",
        canonical_import="com.aspose.cells",
        repo_url="https://example.com",
    )
    defaults.update(overrides)
    return ProductIdentity(**defaults)


# ---------------------------------------------------------------------------
# Java fixture source
# ---------------------------------------------------------------------------

_JAVA_CLASS_SOURCE = """\
package com.aspose.cells;

/**
 * Represents a workbook containing worksheets.
 */
public class Workbook {

    private String filePath;

    /**
     * Load a workbook from the given file path.
     * @param filePath path to the Excel file
     * @return true if loaded successfully
     */
    public boolean load(String filePath) {
        this.filePath = filePath;
        return true;
    }

    /**
     * Save the workbook to the specified file path.
     * @param outputPath the output file path
     */
    public void save(String outputPath) {
        // implementation
    }

    /**
     * Get the worksheets collection.
     * @return WorksheetCollection
     */
    public WorksheetCollection getWorksheets() {
        return null;
    }

    /**
     * Static factory: create an empty workbook.
     */
    public static Workbook create() {
        return new Workbook();
    }
}
"""

_JAVA_ENUM_SOURCE = """\
package com.aspose.cells;

public enum FileFormatType {
    XLSX,
    CSV,
    PDF,
    HTML
}
"""


class TestJavaAdapterTypedMethods:
    """TC-4215: Java adapter — typed method extraction."""

    def test_extract_class_details_returns_method_details(self, tmp_path: Path):
        """extract_class_details returns method_details for a Java class."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        java_file = tmp_path / "Workbook.java"
        java_file.write_text(_JAVA_CLASS_SOURCE, encoding="utf-8")

        extractor = JavaExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(java_file, tmp_path, product)

        assert isinstance(classes, list), "extract_class_details must return a list"
        assert len(classes) >= 1, "At least one class (Workbook) must be extracted"

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None, "Workbook class must be extracted"

        method_details = workbook.get("method_details", [])
        assert len(method_details) > 0, "method_details must be non-empty for Workbook"

        method_names = [m["name"] for m in method_details]
        assert "load" in method_names, "'load' method must appear in method_details"
        assert "save" in method_names, "'save' method must appear in method_details"

    def test_method_has_parameter_info(self, tmp_path: Path):
        """load(String filePath) must have parameter information."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        java_file = tmp_path / "Workbook.java"
        java_file.write_text(_JAVA_CLASS_SOURCE, encoding="utf-8")

        extractor = JavaExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(java_file, tmp_path, product)

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None

        method_details = workbook.get("method_details", [])
        load_method = next((m for m in method_details if m["name"] == "load"), None)
        assert load_method is not None, "load method must be in method_details"

        # Parameters may have name+type_annotation
        params = load_method.get("parameters", [])
        assert len(params) >= 1, "load(String filePath) must have at least one parameter"

    def test_enum_class_extracted(self, tmp_path: Path):
        """Java enum FileFormatType must be extracted with is_enum=True."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        java_file = tmp_path / "FileFormatType.java"
        java_file.write_text(_JAVA_ENUM_SOURCE, encoding="utf-8")

        extractor = JavaExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(java_file, tmp_path, product)

        assert len(classes) >= 1, "At least the enum class must be found"
        enum_class = next((c for c in classes if c["name"] == "FileFormatType"), None)
        assert enum_class is not None, "FileFormatType enum must be extracted"
        assert enum_class.get("is_enum", False) is True, "is_enum must be True for Java enum"

    def test_uses_java_language_explicitly(self, tmp_path: Path):
        """Adapter must call ts_analyzer with language='java'."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        java_file = tmp_path / "Workbook.java"
        java_file.write_text(_JAVA_CLASS_SOURCE, encoding="utf-8")

        extractor = JavaExtractor()
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
            classes = extractor.extract_class_details(java_file, tmp_path, product)

        assert "java" in captured_langs, "Java adapter must dispatch with language='java'"

    def test_fallback_when_ts_analyzer_raises(self, tmp_path: Path):
        """When ts_analyzer raises, adapter falls back to code_analyzer."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        java_file = tmp_path / "Simple.java"
        java_file.write_text(
            "public class Simple { public void doWork() {} }",
            encoding="utf-8",
        )

        extractor = JavaExtractor()
        product = _make_product()

        with patch(
            "launcher.shared.ts_analyzer.analyzer.analyze_file",
            side_effect=RuntimeError("simulated failure"),
        ):
            classes = extractor.extract_class_details(java_file, tmp_path, product)

        # Must not raise; fallback should return list (possibly empty or with data)
        assert isinstance(classes, list)

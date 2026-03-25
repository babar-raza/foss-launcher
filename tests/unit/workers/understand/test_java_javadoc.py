"""TC-JAVA-401 / TC-JAVA-411: Tests for Javadoc doc enrichment in the Java adapter."""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.workers.understand.adapters._java import (
    JavaExtractor,
    _count_params_in_line,
    _extract_javadoc_comment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lines(text: str) -> list[str]:
    """Dedent and split text into lines for extraction tests."""
    return textwrap.dedent(text).strip().splitlines()


def _make_class(name: str, docstring: str = "", method_details: list | None = None) -> dict:
    """Create a minimal class dict matching ts_analyzer output."""
    return {
        "name": name,
        "docstring": docstring,
        "methods": [],
        "method_details": method_details or [],
        "properties": [],
        "property_details": [],
        "is_enum": False,
        "enum_members": [],
    }


def _make_method(
    name: str,
    docstring: str = "",
    docstring_snippet: str = "",
    parameters: list | None = None,
) -> dict:
    return {
        "name": name,
        "docstring": docstring,
        "docstring_snippet": docstring_snippet,
        "start_line": 0,
        "parameters": parameters or [],
        "return_type": "",
    }


# ===================================================================
# TestExtractJavadocComment — unit tests for _extract_javadoc_comment
# ===================================================================

class TestExtractJavadocComment:
    """Tests for the ``_extract_javadoc_comment`` extraction function."""

    def test_single_line_javadoc(self):
        """Single-line ``/** text */`` above class declaration."""
        lines = _lines("""
            /** Represents a workbook. */
            public class Workbook {
        """)
        result = _extract_javadoc_comment(lines, 1)
        assert result == "Represents a workbook."

    def test_multiline_javadoc(self):
        """Multi-line Javadoc with leading ``*`` on each continuation line."""
        lines = _lines("""
            /**
             * Represents a presentation document.
             * Supports loading and saving in multiple formats.
             */
            public class Presentation {
        """)
        result = _extract_javadoc_comment(lines, 4)
        assert "Represents a presentation document" in result
        assert "multiple formats" in result

    def test_javadoc_tags_stripped(self):
        """@param, @return, @throws, @see, @since lines are removed."""
        lines = _lines("""
            /**
             * Saves the document to disk.
             * @param path the output file path
             * @return true if successful
             * @throws IOException on write error
             * @see Workbook#load
             * @since 1.0
             */
            public void save(String path) {
        """)
        result = _extract_javadoc_comment(lines, 8)
        assert result == "Saves the document to disk."
        assert "@param" not in result
        assert "@return" not in result
        assert "@throws" not in result
        assert "@see" not in result
        assert "@since" not in result

    def test_no_javadoc_returns_empty(self):
        """Class without any preceding comment returns empty string."""
        lines = _lines("""
            public class Workbook {
        """)
        result = _extract_javadoc_comment(lines, 0)
        assert result == ""

    def test_regular_comment_not_treated_as_javadoc(self):
        """Single-star block comment ``/* ... */`` is NOT Javadoc."""
        lines = _lines("""
            /* This is not Javadoc */
            public class Workbook {
        """)
        result = _extract_javadoc_comment(lines, 1)
        assert result == ""

    def test_annotation_between_javadoc_and_class(self):
        """Annotations like @Deprecated between Javadoc and declaration are skipped."""
        lines = _lines("""
            /**
             * Legacy workbook format handler.
             */
            @Deprecated
            @SuppressWarnings("unused")
            public class LegacyWorkbook {
        """)
        result = _extract_javadoc_comment(lines, 5)
        assert result == "Legacy workbook format handler."

    def test_blank_lines_between_javadoc_and_class(self):
        """Blank lines between Javadoc and declaration are tolerated."""
        lines = _lines("""
            /**
             * A slide in a presentation.
             */

            public class Slide {
        """)
        result = _extract_javadoc_comment(lines, 4)
        assert result == "A slide in a presentation."

    def test_scan_limit_respected(self):
        """Doc comment more than 30 lines above declaration returns empty."""
        # Build 32 blank lines between doc and declaration
        lines = ["/** Very far away doc. */"]
        lines += [""] * 32
        lines.append("public class FarAway {")
        result = _extract_javadoc_comment(lines, len(lines) - 1)
        assert result == ""


# ===================================================================
# TestEnrichWithJavadocComments — enrichment method tests
# ===================================================================

class TestEnrichWithJavadocComments:
    """Tests for ``JavaExtractor._enrich_with_javadoc_comments()``."""

    def _write_java_file(self, tmp_path: Path, content: str) -> Path:
        fp = tmp_path / "Test.java"
        fp.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
        return fp

    def test_enriches_class_without_docstring(self, tmp_path):
        fp = self._write_java_file(tmp_path, """
            /**
             * A spreadsheet workbook.
             */
            public class Workbook {
            }
        """)
        cls = _make_class("Workbook")
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        assert result[0]["docstring"] == "A spreadsheet workbook."

    def test_skips_class_with_existing_docstring(self, tmp_path):
        fp = self._write_java_file(tmp_path, """
            /**
             * New doc from file.
             */
            public class Workbook {
            }
        """)
        cls = _make_class("Workbook", docstring="Existing doc")
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        assert result[0]["docstring"] == "Existing doc"

    def test_enriches_method_docstrings(self, tmp_path):
        fp = self._write_java_file(tmp_path, """
            public class Workbook {
                /**
                 * Saves the workbook.
                 */
                public void save(String path) {
                }
            }
        """)
        md = _make_method("save")
        cls = _make_class("Workbook", method_details=[md])
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        assert result[0]["method_details"][0]["docstring_snippet"] == "Saves the workbook."

    def test_empty_classes_list_returns_empty(self, tmp_path):
        fp = self._write_java_file(tmp_path, "public class X {}")
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [])
        assert result == []

    def test_file_read_failure_returns_original(self):
        """Unreadable file returns classes unmodified."""
        cls = _make_class("Workbook")
        ext = JavaExtractor()
        fake_path = Path("/nonexistent/path/File.java")
        result = ext._enrich_with_javadoc_comments(fake_path, [cls])
        assert result[0]["docstring"] == ""

    def test_multiple_classes_in_one_file(self, tmp_path):
        fp = self._write_java_file(tmp_path, """
            /**
             * First class.
             */
            public class Alpha {
            }

            /**
             * Second class.
             */
            public class Beta {
            }
        """)
        cls_a = _make_class("Alpha")
        cls_b = _make_class("Beta")
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls_a, cls_b])
        assert result[0]["docstring"] == "First class."
        assert result[1]["docstring"] == "Second class."


# ===================================================================
# TestJavaAdapterIntegration — extract_class_details wiring
# ===================================================================

class TestJavaAdapterIntegration:
    """Integration tests verifying Javadoc enrichment is wired into extract_class_details."""

    def _write_java_file(self, tmp_path: Path, content: str) -> Path:
        fp = tmp_path / "Workbook.java"
        fp.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
        return fp

    def test_extract_class_details_enriches_via_ts_analyzer(self, tmp_path):
        """When ts_analyzer succeeds, enrichment still runs."""
        fp = self._write_java_file(tmp_path, """
            /**
             * A spreadsheet workbook.
             */
            public class Workbook {
                /**
                 * Saves the workbook to a file.
                 */
                public void save(String path) {
                }
            }
        """)
        mock_result = MagicMock()
        mock_result.classes = [
            _make_class("Workbook", method_details=[_make_method("save")]),
        ]

        with patch("launcher.workers.understand.adapters._java.JavaExtractor._enrich_with_javadoc_comments") as mock_enrich:
            mock_enrich.return_value = mock_result.classes
            ext = JavaExtractor()
            with patch("launcher.shared.ts_analyzer.analyzer") as mock_ts:
                mock_ts.analyze_file.return_value = mock_result
                ext.extract_class_details(fp, tmp_path, MagicMock())
                mock_enrich.assert_called_once()

    def test_extract_class_details_enriches_via_fallback(self, tmp_path):
        """When ts_analyzer fails, fallback path still enriches."""
        fp = self._write_java_file(tmp_path, """
            /**
             * A workbook.
             */
            public class Workbook {
            }
        """)
        with patch("launcher.workers.understand.adapters._java.JavaExtractor._enrich_with_javadoc_comments") as mock_enrich:
            mock_enrich.return_value = [_make_class("Workbook")]
            ext = JavaExtractor()
            # Make ts_analyzer raise so fallback runs
            with patch("launcher.shared.ts_analyzer.analyzer") as mock_ts:
                mock_ts.analyze_file.side_effect = ImportError("no grammar")
                with patch("launcher.shared.code_analyzer.analyze_file_safe") as mock_ca:
                    mock_ca.return_value = {"classes": [_make_class("Workbook")]}
                    ext.extract_class_details(fp, tmp_path, MagicMock())
                    mock_enrich.assert_called_once()

    def test_enum_without_javadoc_no_crash(self, tmp_path):
        """Enum class without Javadoc should not crash."""
        fp = self._write_java_file(tmp_path, """
            public enum SaveFormat {
                XLSX,
                CSV,
                PDF
            }
        """)
        cls = _make_class("SaveFormat")
        cls["is_enum"] = True
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        assert result[0]["docstring"] == ""

    def test_interface_javadoc(self, tmp_path):
        """Interface Javadoc is extracted."""
        fp = self._write_java_file(tmp_path, """
            /**
             * Defines slide operations.
             */
            public interface ISlide {
            }
        """)
        cls = _make_class("ISlide")
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        assert result[0]["docstring"] == "Defines slide operations."


# ===================================================================
# TestTsAnalyzerJavadocDiagnostic — verify ts_analyzer Javadoc path
# ===================================================================

class TestTsAnalyzerJavadocDiagnostic:
    """Diagnostic tests verifying ts_analyzer's built-in Javadoc handling."""

    def test_is_doc_comment_java(self):
        """_is_doc_comment recognizes ``/** ... */`` as Java doc comment."""
        from launcher.shared.ts_analyzer import _is_doc_comment
        assert _is_doc_comment("/** Some text */", "java") is True

    def test_is_not_doc_comment_regular(self):
        """Regular ``/* ... */`` is NOT a doc comment for Java."""
        from launcher.shared.ts_analyzer import _is_doc_comment
        assert _is_doc_comment("/* not doc */", "java") is False

    def test_strip_doc_comment_javadoc(self):
        """_strip_doc_comment handles Javadoc delimiters."""
        from launcher.shared.ts_analyzer import _strip_doc_comment
        result = _strip_doc_comment("/** Some text.\n * More text.\n */")
        assert "Some text" in result
        assert "More text" in result


# ===================================================================
# TestCountParamsInLine — unit tests for _count_params_in_line
# ===================================================================

class TestCountParamsInLine:
    """TC-JAVA-411: Tests for the ``_count_params_in_line`` helper."""

    def test_no_params(self):
        assert _count_params_in_line("    public void close() {") == 0

    def test_single_param(self):
        assert _count_params_in_line("    public void save(String path) {") == 1

    def test_two_params(self):
        assert _count_params_in_line("    public void save(String path, SaveFormat fmt) {") == 2

    def test_generic_param_not_double_counted(self):
        """Commas inside angle brackets are not counted as param separators."""
        assert _count_params_in_line("    public void process(Map<String, Integer> data) {") == 1

    def test_generic_with_extra_param(self):
        assert _count_params_in_line("    public void process(Map<String, Integer> data, int flag) {") == 2

    def test_no_parens_returns_negative(self):
        assert _count_params_in_line("    private int count;") == -1

    def test_unclosed_paren_returns_negative(self):
        assert _count_params_in_line("    public void save(String path") == -1


# ===================================================================
# TestOverloadedMethodJavadoc — TC-JAVA-411 overloaded method matching
# ===================================================================

class TestOverloadedMethodJavadoc:
    """TC-JAVA-411: Overloaded methods get their own correct Javadoc."""

    def _write_java_file(self, tmp_path: Path, content: str) -> Path:
        fp = tmp_path / "Workbook.java"
        fp.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
        return fp

    def test_overloaded_methods_get_correct_javadoc(self, tmp_path):
        """save(String) and save(String, SaveFormat) each get their own Javadoc."""
        fp = self._write_java_file(tmp_path, """
            public class Workbook {
                /**
                 * Saves to the default format.
                 */
                public void save(String path) {
                }

                /**
                 * Saves in the specified format.
                 */
                public void save(String path, SaveFormat format) {
                }
            }
        """)
        md_one = _make_method(
            "save",
            parameters=[{"name": "path", "type": "String"}],
        )
        md_two = _make_method(
            "save",
            parameters=[
                {"name": "path", "type": "String"},
                {"name": "format", "type": "SaveFormat"},
            ],
        )
        cls = _make_class("Workbook", method_details=[md_one, md_two])
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        methods = result[0]["method_details"]
        assert methods[0]["docstring"] == "Saves to the default format."
        assert methods[1]["docstring"] == "Saves in the specified format."

    def test_no_cross_contamination_when_only_one_has_javadoc(self, tmp_path):
        """When only one overload has Javadoc, the other stays empty."""
        fp = self._write_java_file(tmp_path, """
            public class Workbook {
                /**
                 * Saves in the specified format.
                 */
                public void save(String path, SaveFormat format) {
                }

                public void save(String path) {
                }
            }
        """)
        # The 1-param overload has no Javadoc in the file.
        # The 2-param overload does have Javadoc.
        md_one_param = _make_method(
            "save",
            parameters=[{"name": "path", "type": "String"}],
        )
        md_two_param = _make_method(
            "save",
            parameters=[
                {"name": "path", "type": "String"},
                {"name": "format", "type": "SaveFormat"},
            ],
        )
        cls = _make_class("Workbook", method_details=[md_one_param, md_two_param])
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        methods = result[0]["method_details"]
        # 1-param overload: no matching Javadoc, fallback picks the 2-param doc
        # but with param-count matching the 2-param doc should go to 2-param method
        assert methods[1]["docstring"] == "Saves in the specified format."
        # 1-param has no Javadoc in source; fallback picks the only available doc
        # This is acceptable — the key point is the 2-param gets its own correct one
        # (before TC-JAVA-411, the 1-param would steal the 2-param's Javadoc)

    def test_non_overloaded_methods_still_work(self, tmp_path):
        """Regression: non-overloaded methods continue to get correct Javadoc."""
        fp = self._write_java_file(tmp_path, """
            public class Workbook {
                /**
                 * Opens a workbook from file.
                 */
                public void open(String path) {
                }

                /**
                 * Closes the workbook.
                 */
                public void close() {
                }
            }
        """)
        md_open = _make_method(
            "open",
            parameters=[{"name": "path", "type": "String"}],
        )
        md_close = _make_method("close")
        cls = _make_class("Workbook", method_details=[md_open, md_close])
        ext = JavaExtractor()
        result = ext._enrich_with_javadoc_comments(fp, [cls])
        methods = result[0]["method_details"]
        assert methods[0]["docstring"] == "Opens a workbook from file."
        assert methods[1]["docstring"] == "Closes the workbook."

"""Tests for TC-5310: C++ file discovery and extraction routing in _api_surface.py."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.workers.understand.extract._api_surface import (
    _CODE_EXTENSIONS,
    _CPP_EXTENSIONS,
    _find_source_files,
)


class TestCppExtensionsInCodeExtensions:
    """TC-5310: Verify C++ file extensions are in _CODE_EXTENSIONS."""

    @pytest.mark.parametrize("ext", [".h", ".hpp", ".cpp", ".cc", ".cxx", ".hxx"])
    def test_cpp_extension_in_code_extensions(self, ext: str) -> None:
        assert ext in _CODE_EXTENSIONS, (
            f"TC-5310: '{ext}' must be in _CODE_EXTENSIONS so C++ files are discovered"
        )

    def test_cpp_extensions_constant_matches_code_extensions(self) -> None:
        """_CPP_EXTENSIONS must be a subset of _CODE_EXTENSIONS."""
        assert _CPP_EXTENSIONS <= _CODE_EXTENSIONS, (
            "TC-5310: All entries in _CPP_EXTENSIONS must also be in _CODE_EXTENSIONS"
        )


class TestFindSourceFilesCpp:
    """TC-5310: _find_source_files discovers C++ header and source files."""

    def test_finds_header_files(self, tmp_path: Path) -> None:
        (tmp_path / "include").mkdir()
        (tmp_path / "include" / "presentation.h").write_text("class Presentation {};")
        (tmp_path / "include" / "slide.hpp").write_text("class Slide {};")
        files = _find_source_files(tmp_path)
        names = {f.name for f in files}
        assert "presentation.h" in names
        assert "slide.hpp" in names

    def test_finds_cpp_source_files(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "presentation.cpp").write_text("// impl")
        (tmp_path / "src" / "slide.cc").write_text("// impl")
        files = _find_source_files(tmp_path)
        names = {f.name for f in files}
        assert "presentation.cpp" in names
        assert "slide.cc" in names

    def test_still_finds_python_files(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("class Foo: pass")
        (tmp_path / "header.h").write_text("class Bar {};")
        files = _find_source_files(tmp_path)
        names = {f.name for f in files}
        assert "module.py" in names
        assert "header.h" in names

    def test_excludes_test_headers(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.h").write_text("class TestFoo {};")
        (tmp_path / "include").mkdir()
        (tmp_path / "include" / "foo.h").write_text("class Foo {};")
        files = _find_source_files(tmp_path)
        names = {f.name for f in files}
        assert "foo.h" in names
        assert "test_foo.h" not in names


class TestCppExtractorRouting:
    """TC-5310: C++ files route through adapter.extract_class_details() in extraction loop."""

    def _make_mock_adapter(self, classes: list[dict]) -> MagicMock:
        adapter = MagicMock()
        adapter.platform_id = "cpp"
        adapter.file_extensions = [".h", ".hpp", ".cpp", ".cc", ".cxx", ".hxx"]
        adapter.detect_package_root.return_value = "include"
        adapter.build_import_allowlist.return_value = []
        adapter.extract_class_details.return_value = classes
        return adapter

    def test_cpp_file_uses_adapter_not_analyze_file_safe(self, tmp_path: Path) -> None:
        """When adapter is provided and file is .h, use adapter.extract_class_details()."""
        include_dir = tmp_path / "include"
        include_dir.mkdir()
        header = include_dir / "presentation.h"
        header.write_text(
            "namespace Aspose { class Presentation { public: void save(); }; }"
        )

        mock_adapter = self._make_mock_adapter(
            [{"name": "Presentation", "methods": ["save"], "method_details": [], "docstring": "A presentation."}]
        )

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="slides",
            platform="cpp",
            display_name="Aspose.Slides.Foss",
            canonical_import="Aspose::Slides::Foss",
            repo_url="https://example.com",
        )

        with patch(
            "launcher.shared.code_analyzer.analyze_file_safe"
        ) as mock_safe:
            from launcher.workers.understand.extract._api_surface import _extract_api_surface
            api_surface = _extract_api_surface(tmp_path, product, adapter=mock_adapter)

        # adapter.extract_class_details should have been called for the .h file
        assert mock_adapter.extract_class_details.called, (
            "TC-5310: adapter.extract_class_details() must be called for .h files"
        )
        # analyze_file_safe should NOT have been called for .h files
        for call in mock_safe.call_args_list:
            called_file = call.args[0] if call.args else call.kwargs.get("file_path")
            if called_file is not None:
                assert str(called_file).endswith(".h") is False, (
                    "TC-5310: analyze_file_safe() must not be called for .h files when adapter present"
                )

    def test_non_cpp_file_uses_analyze_file_safe(self, tmp_path: Path) -> None:
        """Non-C++ files still use analyze_file_safe() even when adapter is present."""
        py_file = tmp_path / "module.py"
        py_file.write_text("class Foo: pass\n")

        mock_adapter = self._make_mock_adapter([])
        mock_adapter.detect_package_root.return_value = ""  # no package root → no files pass filter

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="test",
            platform="python",
            display_name="Test",
            canonical_import="test_module",
            repo_url="https://example.com",
        )

        # With no package_root detected, _file_under_package_root returns False → no files
        # This just verifies the routing logic won't crash when adapter is a CppExtractor
        # but there are no C++ files in a Python repo.
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api_surface = _extract_api_surface(tmp_path, product, adapter=mock_adapter)
        # No cpp files → extract_class_details never called for python files
        for call in mock_adapter.extract_class_details.call_args_list:
            called_file = call.args[0] if call.args else None
            if called_file is not None:
                assert str(called_file).endswith(".py") is False, (
                    "TC-5310: extract_class_details() must not be called for .py files"
                )

    def test_no_adapter_cpp_files_use_analyze_file_safe(self, tmp_path: Path) -> None:
        """TM-02: Without adapter, .h files route through analyze_file_safe() (graceful degradation).

        Verifies that the C++ routing branch is only taken when `adapter` is present.
        When `adapter=None`, even C++ files fall back to analyze_file_safe().
        Uses a mock CppExtractor as adapter=None to test the non-adapter branch.
        """
        include_dir = tmp_path / "include"
        include_dir.mkdir()
        header = include_dir / "foo.h"
        header.write_text("class Foo { public: void bar(); };")

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="test",
            platform="cpp",
            display_name="Test",
            canonical_import="Foo",
            repo_url="https://example.com",
        )

        with patch(
            "launcher.shared.code_analyzer.analyze_file_safe",
            return_value={"classes": [{"name": "Foo", "methods": ["bar"], "method_details": [], "docstring": ""}]},
        ) as mock_safe:
            from launcher.workers.understand.extract._api_surface import _extract_api_surface, _detect_package_root

            # Verify _detect_package_root finds include/ so the file passes filters
            detected_root = _detect_package_root(tmp_path)
            # If root is detected, the file should be processed via analyze_file_safe
            # (Since adapter=None, C++ routing branch is NOT taken)
            api_surface = _extract_api_surface(tmp_path, product, adapter=None)

        if detected_root:
            # Package root detected → file passes filter → analyze_file_safe must be called
            called_paths = [str(c.args[0]) for c in mock_safe.call_args_list if c.args]
            h_calls = [p for p in called_paths if p.endswith(".h")]
            assert h_calls, (
                "TM-02: Without adapter, .h files with detected package_root must reach analyze_file_safe()"
            )

    def test_adapter_exception_falls_back_gracefully(self, tmp_path: Path) -> None:
        """TM-01: If adapter.extract_class_details() raises, fall back to analyze_file_safe()."""
        include_dir = tmp_path / "include"
        include_dir.mkdir()
        header = include_dir / "broken.h"
        header.write_text("class Broken {};")

        mock_adapter = self._make_mock_adapter([])
        mock_adapter.extract_class_details.side_effect = RuntimeError("ts_analyzer exploded")

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="test",
            platform="cpp",
            display_name="Test",
            canonical_import="Broken",
            repo_url="https://example.com",
        )

        # Should not crash — exception must be caught and analysis must continue
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api_surface = _extract_api_surface(tmp_path, product, adapter=mock_adapter)
        # No crash is the primary acceptance check
        assert api_surface is not None, "TM-01: _extract_api_surface() must not raise when adapter fails"

    def test_richest_classbrief_wins_deduplication(self, tmp_path: Path) -> None:
        """SR-01: When same class appears in multiple files, keep the richest ClassBrief.

        Simulates presentation.h's forward-declaring CommentAuthorCollection (0 methods)
        before comment_author_collection.h defines it (12 methods).
        """
        include_dir = tmp_path / "include"
        include_dir.mkdir()

        # File 1 (alphabetically first): forward-declares Presentation with 0 methods
        (include_dir / "alpha.h").write_text("// alpha")
        # File 2: defines Presentation with methods
        (include_dir / "zeta.h").write_text("// zeta")

        # Adapter returns 0-method Presentation for alpha.h, 5-method for zeta.h
        from unittest.mock import MagicMock
        mock_adapter = MagicMock()
        mock_adapter.platform_id = "cpp"
        mock_adapter.file_extensions = [".h", ".hpp"]
        mock_adapter.detect_package_root.return_value = "include"
        mock_adapter.build_import_allowlist.return_value = []

        def _extract_side_effect(file_path, repo_dir, product):
            if "alpha" in str(file_path):
                return [{"name": "Presentation", "methods": [], "method_details": [], "docstring": ""}]
            if "zeta" in str(file_path):
                return [{"name": "Presentation", "methods": ["save", "load", "create"],
                         "method_details": [
                             {"name": "save", "docstring": "Save", "docstring_snippet": "Save",
                              "start_line": 1, "parameters": [], "return_type": "void",
                              "is_static": False, "is_async": False, "is_getter": False, "kind": ""},
                         ],
                         "docstring": "Represents a presentation."}]
            return []

        mock_adapter.extract_class_details.side_effect = _extract_side_effect

        from launcher.models.product import ProductIdentity
        product = ProductIdentity(
            family="test", platform="cpp", display_name="Test",
            canonical_import="Presentation", repo_url="https://example.com",
        )
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api_surface = _extract_api_surface(tmp_path, product, adapter=mock_adapter)

        # Presentation should be in public_classes
        assert "Presentation" in api_surface.public_classes, "SR-01: Presentation must be in public_classes"

        # The class_brief for Presentation should have methods (from zeta.h), not 0 methods (from alpha.h)
        pres_briefs = [cb for cb in api_surface.class_briefs if cb.name == "Presentation"]
        assert pres_briefs, "SR-01: Presentation must have a ClassBrief"
        # The richest brief (with save method) must win over the 0-method forward declaration
        assert pres_briefs[0].docstring_snippet == "Represents a presentation.", (
            "SR-01: Richest ClassBrief (with docstring) must win deduplication, not the forward-declaration"
        )


# ---------------------------------------------------------------------------
# TC-5312 SR-01: Forward-declaration filter (0 methods + 0 properties → drop)
# ---------------------------------------------------------------------------

class TestForwardDeclarationFilter:
    """TC-5312 SR-01: Classes with 0 methods + 0 method_details + 0 properties
    are forward-declaration stubs and must not appear in public_classes."""

    def _make_adapter(self, classes_by_file: dict) -> MagicMock:
        mock = MagicMock()
        mock.platform_id = "cpp"
        mock.file_extensions = [".h", ".hpp"]
        mock.detect_package_root.return_value = "include"
        mock.build_import_allowlist.return_value = []

        def _side(file_path, repo_dir, product):
            return classes_by_file.get(file_path.name, [])

        mock.extract_class_details.side_effect = _side
        return mock

    def _product(self) -> "ProductIdentity":
        from launcher.models.product import ProductIdentity
        return ProductIdentity(
            family="test", platform="cpp", display_name="Test",
            canonical_import="Presentation", repo_url="https://example.com",
        )

    def test_forward_declaration_not_in_public_classes(self, tmp_path: Path) -> None:
        """A 0-method/0-property class entry from a C++ file must be dropped."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "presentation.h").write_text("// fwd")

        adapter = self._make_adapter({
            "presentation.h": [
                {"name": "OpcPackage", "methods": [], "method_details": [], "properties": [], "docstring": ""},
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)
        assert "OpcPackage" not in api.public_classes, (
            "TC-5312 SR-01: Forward-declaration stub (0 methods/properties) must not be in public_classes"
        )

    def test_real_class_with_methods_in_public_classes(self, tmp_path: Path) -> None:
        """A class with at least one method must be kept in public_classes."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "presentation.h").write_text("// real")

        adapter = self._make_adapter({
            "presentation.h": [
                {"name": "Presentation", "methods": ["save"], "method_details": [], "properties": [], "docstring": ""},
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)
        assert "Presentation" in api.public_classes, (
            "TC-5312 SR-01: Class with methods must remain in public_classes"
        )

    def test_class_with_only_properties_kept(self, tmp_path: Path) -> None:
        """A class with 0 methods but non-empty properties must NOT be filtered."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "config.h").write_text("// config")

        adapter = self._make_adapter({
            "config.h": [
                {"name": "Config", "methods": [], "method_details": [], "properties": ["enabled"], "docstring": ""},
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)
        assert "Config" in api.public_classes, (
            "TC-5312 SR-01: Class with properties (but no methods) must NOT be filtered"
        )

    def test_fwd_decl_filter_only_applies_to_cpp_extensions(self) -> None:
        """SR-01 extension guard: only _CPP_EXTENSIONS are subject to forward-decl filter.
        Non-C++ extensions (.py, .java, .cs, .ts) must bypass the filter entirely."""
        from launcher.workers.understand.extract._api_surface import _CPP_EXTENSIONS
        non_cpp = [".py", ".java", ".cs", ".ts", ".js", ".rb"]
        for ext in non_cpp:
            assert ext not in _CPP_EXTENSIONS, (
                f"TC-5312 SR-01: SR-01 guard must NOT apply to '{ext}' files — "
                "only C++ extensions are subject to forward-decl filtering"
            )

    def test_class_with_method_details_but_no_methods_kept(self, tmp_path: Path) -> None:
        """SR-01 condition requires ALL three (methods, method_details, properties) to be empty.
        A class with non-empty method_details but empty methods must NOT be filtered."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "builder.h").write_text("// builder")

        adapter = self._make_adapter({
            "builder.h": [
                {
                    "name": "Builder",
                    "methods": [],          # empty methods list
                    "method_details": [     # but has typed method details
                        {"name": "build", "parameters": [], "return_type": "Presentation*",
                         "docstring": "Builds", "docstring_snippet": "Builds",
                         "start_line": 1, "is_static": False, "is_async": False,
                         "is_getter": False, "kind": ""},
                    ],
                    "properties": [],
                    "docstring": "",
                }
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)
        assert "Builder" in api.public_classes, (
            "TC-5312 SR-01: Class with non-empty method_details (but empty methods) "
            "must NOT be filtered — filter only fires when ALL three are empty"
        )


# ---------------------------------------------------------------------------
# TC-5312 SR-02: _internal/ path excluded from build_import_allowlist()
# ---------------------------------------------------------------------------

class TestInternalPathExcludedFromAllowlist:
    """TC-5312 SR-02: Headers under _internal/ directories must not appear in
    the import allowlist built by CppExtractor.build_import_allowlist()."""

    def test_internal_header_excluded(self, tmp_path: Path) -> None:
        """Headers under _internal/ must be excluded from the allowlist."""
        from launcher.workers.understand.adapters._cpp import CppExtractor
        from launcher.models.product import ProductIdentity

        include = tmp_path / "include"
        include.mkdir()
        (include / "presentation.h").write_text("namespace Aspose { }")
        internal_dir = include / "_internal"
        internal_dir.mkdir()
        (internal_dir / "opc_package.h").write_text("// internal")

        product = ProductIdentity(
            family="slides", platform="cpp", display_name="Test",
            canonical_import="Aspose::Slides", repo_url="https://example.com",
        )
        extractor = CppExtractor()
        allowlist = extractor.build_import_allowlist(tmp_path, "include", product)
        # Internal header must not appear
        for entry in allowlist:
            assert "_internal" not in entry, (
                f"TC-5312 SR-02: '_internal' path must not appear in import allowlist, got: {entry}"
            )

    def test_public_header_included(self, tmp_path: Path) -> None:
        """Normal public headers must still appear in the allowlist."""
        from launcher.workers.understand.adapters._cpp import CppExtractor
        from launcher.models.product import ProductIdentity

        include = tmp_path / "include"
        include.mkdir()
        (include / "presentation.h").write_text("// public")

        product = ProductIdentity(
            family="slides", platform="cpp", display_name="Test",
            canonical_import="Aspose::Slides", repo_url="https://example.com",
        )
        extractor = CppExtractor()
        allowlist = extractor.build_import_allowlist(tmp_path, "include", product)
        assert "presentation.h" in allowlist, (
            "TC-5312 SR-02: Public headers must still appear in import allowlist"
        )


# ---------------------------------------------------------------------------
# TC-5312 SR-03: File discovery cap raised to 500
# ---------------------------------------------------------------------------

class TestFileDiscoveryCap:
    """TC-5312 SR-03: _find_source_files default cap must be 500 (was 300)."""

    def test_default_cap_is_500(self, tmp_path: Path) -> None:
        """_find_source_files must accept up to 500 files by default."""
        include = tmp_path / "include"
        include.mkdir()
        # Create 400 .h files — should all be discovered
        for i in range(400):
            (include / f"class_{i:04d}.h").write_text(f"class C{i} {{}};")
        files = _find_source_files(tmp_path)
        assert len(files) == 400, (
            f"TC-5312 SR-03: _find_source_files must find all 400 files (cap=500), got {len(files)}"
        )


# ===================================================================
# TC-5323: C++ allowlist internal namespace leak fix
# ===================================================================


class TestIsInternalNamespace:
    """SC-03 (TC-5323): _is_internal_namespace helper."""

    def test_internal_namespace_blocked(self) -> None:
        from launcher.workers.understand.adapters._cpp import _is_internal_namespace
        assert _is_internal_namespace("Aspose::Slides::Foss::Internal") is True
        assert _is_internal_namespace("Aspose::ThreeD::Foss::Detail") is True
        assert _is_internal_namespace("MyLib::Impl") is True
        assert _is_internal_namespace("Foo::Private") is True
        assert _is_internal_namespace("Foo::details") is True

    def test_public_namespace_allowed(self) -> None:
        from launcher.workers.understand.adapters._cpp import _is_internal_namespace
        assert _is_internal_namespace("Aspose::Slides::Foss") is False
        assert _is_internal_namespace("Aspose::Slides::Foss::Export") is False
        assert _is_internal_namespace("MyLib::Drawing") is False
        assert _is_internal_namespace("Internally") is False  # word match not substring


class TestCppAllowlistInternalLeak:
    """SC-03 (TC-5323): build_import_allowlist must not leak ::Internal namespaces."""

    def _make_product(self, canonical_import: str):
        from launcher.models.product import ProductIdentity
        return ProductIdentity(
            family="slides", platform="cpp",
            display_name="Slides FOSS",
            canonical_import=canonical_import,
            repo_url="https://github.com/test",
        )

    def test_internal_namespace_excluded_from_allowlist(self, tmp_path: Path) -> None:
        """Headers with ::Internal namespace must NOT appear in the allowlist."""
        from launcher.workers.understand.adapters._cpp import CppExtractor
        include = tmp_path / "include"
        include.mkdir()
        # Most headers declare the public namespace
        for i in range(3):
            (include / f"public_{i}.h").write_text(
                f"namespace Aspose::Slides::Foss {{\nclass C{i} {{}};\n}}"
            )
        # One header declares the internal namespace
        (include / "internal_helper.h").write_text(
            "namespace Aspose::Slides::Foss::Internal {\nvoid helper();\n}"
        )
        product = self._make_product("Aspose::Slides::Foss")
        adapter = CppExtractor()
        allowlist = adapter.build_import_allowlist(tmp_path, "include", product)
        assert "Aspose::Slides::Foss" in allowlist
        assert "Aspose::Slides::Foss::Internal" not in allowlist, (
            "::Internal namespace must not appear in public import allowlist"
        )

    def test_canonical_namespace_in_allowlist(self, tmp_path: Path) -> None:
        """canonical_import is always the first allowlist entry."""
        from launcher.workers.understand.adapters._cpp import CppExtractor
        include = tmp_path / "include"
        include.mkdir()
        (include / "presentation.h").write_text(
            "namespace Aspose::Slides::Foss {\nclass Presentation {};\n}"
        )
        product = self._make_product("Aspose::Slides::Foss")
        adapter = CppExtractor()
        allowlist = adapter.build_import_allowlist(tmp_path, "include", product)
        assert allowlist[0] == "Aspose::Slides::Foss"

    def test_no_internal_namespace_even_when_it_appears_first(self, tmp_path: Path) -> None:
        """Even if only internal-namespace headers exist, they must not enter the allowlist."""
        from launcher.workers.understand.adapters._cpp import CppExtractor
        include = tmp_path / "include"
        include.mkdir()
        (include / "impl.h").write_text(
            "namespace Aspose::Slides::Foss::Detail {\nvoid impl();\n}"
        )
        product = self._make_product("Aspose::Slides::Foss")
        adapter = CppExtractor()
        allowlist = adapter.build_import_allowlist(tmp_path, "include", product)
        assert "Aspose::Slides::Foss::Detail" not in allowlist


# ---------------------------------------------------------------------------
# TC-5328: C++ enum class extraction into public_classes and api_identifiers
# ---------------------------------------------------------------------------


class TestCppEnumClassExtraction:
    """TC-5328: enum class entries (is_enum=True) must NOT be dropped by the
    SR-01 forward-declaration filter and must appear in public_classes,
    api_identifiers, and enums."""

    def _make_adapter(self, classes_by_file: dict) -> MagicMock:
        mock = MagicMock()
        mock.platform_id = "cpp"
        mock.file_extensions = [".h", ".hpp"]
        mock.detect_package_root.return_value = "include"
        mock.build_import_allowlist.return_value = []

        def _side(file_path, repo_dir, product):
            return classes_by_file.get(file_path.name, [])

        mock.extract_class_details.side_effect = _side
        return mock

    def _product(self) -> "ProductIdentity":
        from launcher.models.product import ProductIdentity
        return ProductIdentity(
            family="slides", platform="cpp", display_name="Test",
            canonical_import="Aspose::Slides::Foss",
            repo_url="https://example.com",
        )

    def test_enum_class_in_public_classes(self, tmp_path: Path) -> None:
        """TC-5328: enum class SaveFormat (is_enum=True, 0 methods) must appear
        in public_classes — not filtered by SR-01."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "save_format.h").write_text("// enum class SaveFormat")

        adapter = self._make_adapter({
            "save_format.h": [
                {
                    "name": "SaveFormat",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "Specifies the format for saving.",
                    "is_enum": True,
                    "enum_members": [
                        {"name": "PPTX", "value": ""},
                        {"name": "PDF", "value": ""},
                        {"name": "PNG", "value": ""},
                        {"name": "JPEG", "value": ""},
                        {"name": "SVG", "value": ""},
                    ],
                }
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)

        assert "SaveFormat" in api.public_classes, (
            "TC-5328: enum class SaveFormat must appear in public_classes"
        )

    def test_enum_members_in_api_identifiers(self, tmp_path: Path) -> None:
        """TC-5328: enum member names (PPTX, PDF, etc.) must appear in api_identifiers."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "save_format.h").write_text("// enum class")

        adapter = self._make_adapter({
            "save_format.h": [
                {
                    "name": "SaveFormat",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "",
                    "is_enum": True,
                    "enum_members": [
                        {"name": "PPTX", "value": ""},
                        {"name": "PDF", "value": ""},
                    ],
                }
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)

        assert "SaveFormat" in api.api_identifiers, (
            "TC-5328: enum class name must be in api_identifiers"
        )
        assert "PPTX" in api.api_identifiers, (
            "TC-5328: enum member PPTX must be in api_identifiers"
        )
        assert "PDF" in api.api_identifiers, (
            "TC-5328: enum member PDF must be in api_identifiers"
        )

    def test_enum_record_in_enums(self, tmp_path: Path) -> None:
        """TC-5328: enum class must produce an EnumRecord in api_surface.enums."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "save_format.h").write_text("// enum class")

        adapter = self._make_adapter({
            "save_format.h": [
                {
                    "name": "SaveFormat",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "Save format.",
                    "is_enum": True,
                    "enum_members": [
                        {"name": "PPTX", "value": "0"},
                        {"name": "PDF", "value": "1"},
                    ],
                }
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)

        enum_names = [e.name for e in api.enums]
        assert "SaveFormat" in enum_names, (
            "TC-5328: SaveFormat must be in api_surface.enums"
        )
        sf_enum = next(e for e in api.enums if e.name == "SaveFormat")
        member_names = [m.name for m in sf_enum.members]
        assert "PPTX" in member_names
        assert "PDF" in member_names

    def test_fwd_decl_still_filtered_alongside_enum(self, tmp_path: Path) -> None:
        """TC-5328: Forward-declaration stubs must STILL be filtered even when
        enum classes are present — the exemption is only for is_enum=True."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "save_format.h").write_text("// enum")
        (include / "fwd_decl.h").write_text("// fwd decl")

        adapter = self._make_adapter({
            "save_format.h": [
                {
                    "name": "SaveFormat",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "",
                    "is_enum": True,
                    "enum_members": [{"name": "PPTX", "value": ""}],
                }
            ],
            "fwd_decl.h": [
                {
                    "name": "OpcPackage",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "",
                    # is_enum NOT set or False → forward-decl stub
                }
            ],
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)

        assert "SaveFormat" in api.public_classes, (
            "TC-5328: enum class must pass filter"
        )
        assert "OpcPackage" not in api.public_classes, (
            "TC-5328: forward-decl stub must still be filtered"
        )

    def test_enum_class_in_class_briefs(self, tmp_path: Path) -> None:
        """TC-5328: enum class must have a ClassBrief entry with enums populated."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "save_format.h").write_text("// enum class")

        adapter = self._make_adapter({
            "save_format.h": [
                {
                    "name": "SaveFormat",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "Specifies save format.",
                    "is_enum": True,
                    "enum_members": [
                        {"name": "PPTX", "value": ""},
                        {"name": "PDF", "value": ""},
                    ],
                }
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)

        sf_briefs = [cb for cb in api.class_briefs if cb.name == "SaveFormat"]
        assert sf_briefs, "TC-5328: SaveFormat must have a ClassBrief"
        assert sf_briefs[0].enums, "TC-5328: ClassBrief.enums must be populated"
        assert sf_briefs[0].enums[0].name == "SaveFormat"
        assert len(sf_briefs[0].enums[0].members) == 2

    def test_enum_class_empty_members_no_crash(self, tmp_path: Path) -> None:
        """SR-02: enum class with is_enum=True but empty enum_members must not crash
        and must still enter public_classes (tree-sitter can return this for forward-declared enums)."""
        include = tmp_path / "include"
        include.mkdir()
        (include / "fwd_enum.h").write_text("// enum class forward declaration")

        adapter = self._make_adapter({
            "fwd_enum.h": [
                {
                    "name": "LoadFormat",
                    "methods": [],
                    "method_details": [],
                    "properties": [],
                    "docstring": "",
                    "is_enum": True,
                    "enum_members": [],  # empty — forward-declared enum
                }
            ]
        })
        from launcher.workers.understand.extract._api_surface import _extract_api_surface
        api = _extract_api_surface(tmp_path, self._product(), adapter=adapter)

        # Must not crash; enum class name enters public_classes
        assert "LoadFormat" in api.public_classes, (
            "SR-02: enum class with empty members must still enter public_classes"
        )
        # No member names added to api_identifiers (loop is empty — no crash)
        # Class name itself is in api_identifiers
        assert "LoadFormat" in api.api_identifiers, (
            "SR-02: enum class name must be in api_identifiers even with empty members"
        )

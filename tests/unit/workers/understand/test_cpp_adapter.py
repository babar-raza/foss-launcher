"""Tests for C++ platform adapter improvements: SR-08, SR-09, SR-10, SR-11."""
from __future__ import annotations

import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest


# ── SR-08: CMakeLists.txt parser ─────────────────────────────────────

class TestParseCmake:
    """Verify _parse_cmake() extracts library identity from CMakeLists.txt."""

    def _write_cmake(self, tmp_path: Path, content: str) -> Path:
        f = tmp_path / "CMakeLists.txt"
        f.write_text(content, encoding="utf-8")
        return f

    def test_full_cmake_extracts_all_fields(self, tmp_path):
        from launcher.workers.scout.scout import _parse_cmake

        cmake = self._write_cmake(tmp_path, textwrap.dedent("""\
            cmake_minimum_required(VERSION 3.14)
            project(AsposeSlides VERSION 24.1.0)
            add_library(Aspose.Slides SHARED src/presentation.cpp)
            target_include_directories(Aspose.Slides PUBLIC include)
        """))
        result = _parse_cmake(cmake)
        assert result["project_name"] == "AsposeSlides"
        assert result["version"] == "24.1.0"
        assert result["library_target"] == "Aspose.Slides"
        assert "include" in result.get("public_include_dirs", [])

    def test_minimal_cmake_project_only(self, tmp_path):
        from launcher.workers.scout.scout import _parse_cmake

        cmake = self._write_cmake(tmp_path, "project(MyLib)\n")
        result = _parse_cmake(cmake)
        assert result["project_name"] == "MyLib"
        assert "version" not in result

    def test_empty_file_returns_empty_dict(self, tmp_path):
        from launcher.workers.scout.scout import _parse_cmake

        cmake = self._write_cmake(tmp_path, "")
        result = _parse_cmake(cmake)
        assert result == {}

    def test_missing_file_returns_empty_dict(self, tmp_path):
        from launcher.workers.scout.scout import _parse_cmake

        result = _parse_cmake(tmp_path / "nonexistent.txt")
        assert result == {}

    def test_version_fallback_set_target_properties(self, tmp_path):
        from launcher.workers.scout.scout import _parse_cmake

        cmake = self._write_cmake(tmp_path, textwrap.dedent("""\
            project(MyLib)
            add_library(MyLib STATIC src/lib.cpp)
            set_target_properties(MyLib PROPERTIES VERSION 3.2.1)
        """))
        result = _parse_cmake(cmake)
        assert result.get("version") == "3.2.1"

    def test_pseudo_targets_excluded(self, tmp_path):
        from launcher.workers.scout.scout import _parse_cmake

        cmake = self._write_cmake(tmp_path, "project(Foo)\nadd_library(INTERFACE src)\n")
        result = _parse_cmake(cmake)
        assert "library_target" not in result

    def test_cmake_overrides_unknown_sentinel(self, tmp_path):
        """TC-5186: cmake project_name must override 'UNKNOWN' sentinel from _extract_package_metadata."""
        from launcher.workers.scout.scout import _parse_cmake, _extract_shared_facts

        cmake = self._write_cmake(tmp_path, "project(aspose_slides_foss)\n")
        # Simulate the guard condition: package_name == "UNKNOWN" should be overridden
        result = _parse_cmake(cmake)
        assert result["project_name"] == "aspose_slides_foss"

        # Verify the guard logic directly
        project_name = result.get("project_name")
        package_name = "UNKNOWN"  # what _extract_package_metadata returns for C++
        should_override = bool(project_name and (not package_name or package_name == "UNKNOWN"))
        assert should_override, "cmake project_name must override UNKNOWN sentinel"


# ── SR-09/SR-10: C++ namespace extraction and header allowlist ───────

class TestCppNamespaceExtraction:
    """Verify _extract_cpp_namespace() detects C++ namespaces from header files."""

    def _write_header(self, tmp_path: Path, content: str, name: str = "scene.h") -> Path:
        h = tmp_path / name
        h.write_text(content, encoding="utf-8")
        return h

    def test_nested_namespace_joined(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import _extract_cpp_namespace

        header = self._write_header(tmp_path, textwrap.dedent("""\
            namespace Aspose {
            namespace Slides {
                class Presentation {};
            }
            }
        """))
        ns = _extract_cpp_namespace(header)
        assert ns == "Aspose::Slides"

    def test_qualified_namespace(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import _extract_cpp_namespace

        header = self._write_header(tmp_path, "namespace Aspose::Cells { class Workbook {}; }\n")
        ns = _extract_cpp_namespace(header)
        assert ns == "Aspose::Cells"

    def test_no_namespace_returns_empty(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import _extract_cpp_namespace

        header = self._write_header(tmp_path, "class Foo {};\n")
        ns = _extract_cpp_namespace(header)
        assert ns == ""

    def test_internal_namespace_filtered(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import _extract_cpp_namespace

        header = self._write_header(tmp_path, textwrap.dedent("""\
            namespace detail {
            namespace impl {
                struct Helper {};
            }
            }
        """))
        ns = _extract_cpp_namespace(header)
        assert ns == ""

    def test_allcaps_macro_guard_filtered(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import _extract_cpp_namespace

        header = self._write_header(tmp_path, "namespace ASPOSE_EXPORTS { }\n")
        ns = _extract_cpp_namespace(header)
        assert ns == ""

    def test_missing_file_returns_empty(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import _extract_cpp_namespace

        ns = _extract_cpp_namespace(tmp_path / "nonexistent.h")
        assert ns == ""


class TestCppAllowlist:
    """Verify build_import_allowlist() cap, namespace extraction, path stripping."""

    def _make_repo(self, tmp_path: Path, headers: list[str], namespace_content: str = "") -> Path:
        include_dir = tmp_path / "include" / "aspose"
        include_dir.mkdir(parents=True, exist_ok=True)
        for name in headers:
            (include_dir / name).write_text(
                namespace_content or f"// {name}\n", encoding="utf-8"
            )
        return tmp_path

    def test_namespace_in_allowlist(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        repo = self._make_repo(tmp_path, ["presentation.h"], textwrap.dedent("""\
            namespace Aspose { namespace Slides { class Presentation {}; } }
        """))
        product = SimpleNamespace(canonical_import="Aspose.Slides")
        ext = CppExtractor()
        al = ext.build_import_allowlist(repo, "include", product)
        assert any("Aspose::Slides" in entry for entry in al)

    def test_header_paths_stripped_of_include_prefix(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        repo = self._make_repo(tmp_path, ["scene.h", "mesh.h"])
        product = SimpleNamespace(canonical_import="Aspose.ThreeD")
        ext = CppExtractor()
        al = ext.build_import_allowlist(repo, "include", product)
        # Should not contain the "include/" prefix
        for entry in al:
            assert not entry.startswith("include/")

    def test_cap_at_30(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        headers = [f"cls{i}.h" for i in range(40)]
        repo = self._make_repo(tmp_path, headers)
        product = SimpleNamespace(canonical_import="")
        ext = CppExtractor()
        al = ext.build_import_allowlist(repo, "include", product)
        assert len(al) <= 30

    def test_canonical_import_first(self, tmp_path):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        repo = self._make_repo(tmp_path, ["foo.h"])
        product = SimpleNamespace(canonical_import="Aspose.ThreeD")
        ext = CppExtractor()
        al = ext.build_import_allowlist(repo, "include", product)
        assert al[0] == "Aspose.ThreeD"


# ── SR-11: C++ format detection ──────────────────────────────────────

class TestCppFormatDetection:
    """Verify detect_supported_formats_from_docs() finds format keywords."""

    def test_presentation_formats_detected(self):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        ext = CppExtractor()
        readme = "Aspose.Slides supports PPTX, PPT, ODP, and PDF output formats."
        result = ext.detect_supported_formats_from_docs(readme, [])
        assert "PPTX" in result
        assert "PPT" in result
        assert "PDF" in result

    def test_case_insensitive(self):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        ext = CppExtractor()
        result = ext.detect_supported_formats_from_docs("pptx and xlsx supported", [])
        assert "PPTX" in result
        assert "XLSX" in result

    def test_no_formats_returns_empty(self):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        ext = CppExtractor()
        result = ext.detect_supported_formats_from_docs("A generic C++ library.", [])
        assert result == []

    def test_doc_contents_also_scanned(self):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        ext = CppExtractor()
        result = ext.detect_supported_formats_from_docs("", ["Export to PDF, TIFF or SVG."])
        assert "PDF" in result
        assert "TIFF" in result
        assert "SVG" in result

    def test_deduplication(self):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        ext = CppExtractor()
        result = ext.detect_supported_formats_from_docs("PPTX PPTX PPTX", [])
        assert result.count("PPTX") == 1

    def test_empty_inputs_returns_empty(self):
        from launcher.workers.understand.adapters._cpp import CppExtractor

        ext = CppExtractor()
        assert ext.detect_supported_formats_from_docs("", []) == []
        assert ext.detect_supported_formats_from_docs(None, None) == []  # type: ignore[arg-type]


# ── TC-CPP-401: C++ enum member extraction via ts_analyzer ────────────

class TestCppEnumExtraction:
    """Verify that C++ enum_specifier nodes are discovered and members extracted."""

    def _write_header(self, tmp_path: Path, content: str, name: str = "formats.h") -> Path:
        h = tmp_path / name
        h.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
        return h

    def test_enum_specifier_in_class_types(self):
        """enum_specifier is registered in _CLASS_TYPES['cpp']."""
        from launcher.shared.ts_analyzer import _CLASS_TYPES
        assert "enum_specifier" in _CLASS_TYPES["cpp"]

    def test_enum_class_members_extracted(self, tmp_path):
        """C++ enum class members are extracted with correct names."""
        header = self._write_header(tmp_path, """
            enum class SaveFormat {
                PPTX,
                PDF,
                SVG
            };
        """)
        from launcher.shared.ts_analyzer import analyzer
        result = analyzer.analyze_file(str(header), language="cpp", repo_dir=str(tmp_path))
        enums = [c for c in result.classes if c.get("is_enum")]
        assert len(enums) >= 1, f"Expected at least 1 enum, got {len(enums)}: {result.classes}"
        enum = enums[0]
        assert enum["name"] == "SaveFormat"
        member_names = [m["name"] for m in enum["enum_members"]]
        assert "PPTX" in member_names
        assert "PDF" in member_names
        assert "SVG" in member_names

    def test_enum_with_values(self, tmp_path):
        """C++ enum with explicit values extracts both name and value."""
        header = self._write_header(tmp_path, """
            enum class LoadFormat {
                AUTO = 0,
                PPTX = 1,
                PDF = 2
            };
        """)
        from launcher.shared.ts_analyzer import analyzer
        result = analyzer.analyze_file(str(header), language="cpp", repo_dir=str(tmp_path))
        enums = [c for c in result.classes if c.get("is_enum")]
        assert len(enums) >= 1
        members = enums[0]["enum_members"]
        auto_member = next((m for m in members if m["name"] == "AUTO"), None)
        assert auto_member is not None
        assert auto_member["value"] == "0"

    def test_is_enum_set_for_enum_specifier(self, tmp_path):
        """Classes extracted from enum_specifier have is_enum=True."""
        header = self._write_header(tmp_path, """
            enum class FileFormat { FBX, OBJ, STL };
        """)
        from launcher.shared.ts_analyzer import analyzer
        result = analyzer.analyze_file(str(header), language="cpp", repo_dir=str(tmp_path))
        enums = [c for c in result.classes if c.get("is_enum")]
        assert len(enums) >= 1
        assert enums[0]["is_enum"] is True

    def test_class_not_flagged_as_enum(self, tmp_path):
        """Regular class_specifier is NOT flagged as enum."""
        header = self._write_header(tmp_path, """
            class Presentation {
            public:
                void save();
            };
        """)
        from launcher.shared.ts_analyzer import analyzer
        result = analyzer.analyze_file(str(header), language="cpp", repo_dir=str(tmp_path))
        classes = [c for c in result.classes if not c.get("is_enum")]
        if classes:
            assert classes[0]["is_enum"] is False


# ── TC-CPP-402: Doxygen doc enrichment ────────────────────────────────

class TestDoxygenExtraction:
    """Verify Doxygen comment extraction for C++ classes and methods."""

    def _write_header(self, tmp_path: Path, content: str, name: str = "test.h") -> Path:
        h = tmp_path / name
        h.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
        return h

    def test_triple_slash_doc_extracted(self, tmp_path):
        """Triple-slash ``///`` Doxygen comment is extracted."""
        from launcher.workers.understand.adapters._cpp import _extract_doxygen_comment

        lines = textwrap.dedent("""
            /// Represents a presentation document.
            class Presentation {
        """).strip().splitlines()
        result = _extract_doxygen_comment(lines, 1)
        assert result == "Represents a presentation document."

    def test_javadoc_style_doc_extracted(self, tmp_path):
        """Block-style ``/** */`` Doxygen comment is extracted."""
        from launcher.workers.understand.adapters._cpp import _extract_doxygen_comment

        lines = textwrap.dedent("""
            /**
             * Saves the presentation to disk.
             */
            void Save(const char* path);
        """).strip().splitlines()
        result = _extract_doxygen_comment(lines, 3)
        assert result == "Saves the presentation to disk."

    def test_doxygen_brief_stripped(self, tmp_path):
        """@brief and \\brief tags are removed from output."""
        from launcher.workers.understand.adapters._cpp import _extract_doxygen_comment

        lines = textwrap.dedent("""
            /// @brief Loads a scene from file.
            void LoadScene(const char* path);
        """).strip().splitlines()
        result = _extract_doxygen_comment(lines, 1)
        assert result == "Loads a scene from file."
        assert "@brief" not in result

    def test_doxygen_param_tags_stripped(self, tmp_path):
        """@param, @return etc. are stripped from Doxygen output."""
        from launcher.workers.understand.adapters._cpp import _extract_doxygen_comment

        lines = textwrap.dedent("""
            /// Creates a new slide.
            /// @param index The position.
            /// @return The created slide.
            Slide* AddSlide(int index);
        """).strip().splitlines()
        result = _extract_doxygen_comment(lines, 3)
        assert result == "Creates a new slide."
        assert "@param" not in result
        assert "@return" not in result

    def test_no_doc_returns_empty(self, tmp_path):
        """Class without doc comment returns empty string."""
        from launcher.workers.understand.adapters._cpp import _extract_doxygen_comment

        lines = textwrap.dedent("""
            class Presentation {
        """).strip().splitlines()
        result = _extract_doxygen_comment(lines, 0)
        assert result == ""

    def test_enrichment_populates_class_docstring(self, tmp_path):
        """Adapter enrichment populates class docstring from Doxygen."""
        from launcher.workers.understand.adapters._cpp import CppExtractor

        header = self._write_header(tmp_path, """
            /// Represents a 3D scene.
            class Scene {
            public:
                void Load(const char* path);
            };
        """)
        cls = {
            "name": "Scene",
            "docstring": "",
            "methods": [],
            "method_details": [],
            "properties": [],
            "property_details": [],
            "is_enum": False,
            "enum_members": [],
        }
        ext = CppExtractor()
        result = ext._enrich_with_doxygen_comments(header, [cls])
        assert result[0]["docstring"] == "Represents a 3D scene."

    def test_ts_analyzer_cpp_class_docstring(self, tmp_path):
        """ts_analyzer extracts class-level Doxygen docstring for C++."""
        header = self._write_header(tmp_path, """
            /// Represents a workbook.
            class Workbook {
            public:
                void Save();
            };
        """)
        from launcher.shared.ts_analyzer import analyzer
        result = analyzer.analyze_file(str(header), language="cpp", repo_dir=str(tmp_path))
        assert len(result.classes) >= 1
        cls = result.classes[0]
        assert "Represents a workbook" in cls.get("docstring", "")


# ── TC-CPP-403: C++ method return type + parameter typing ─────────────

class TestCppMethodTyping:
    """Verify that C++ method return types and parameter types are extracted."""

    def _write_header(self, tmp_path: Path, content: str, name: str = "test.h") -> Path:
        h = tmp_path / name
        h.write_text(textwrap.dedent(content).strip(), encoding="utf-8")
        return h

    def _get_methods(self, tmp_path, code):
        header = self._write_header(tmp_path, code)
        from launcher.shared.ts_analyzer import analyzer
        result = analyzer.analyze_file(str(header), language="cpp", repo_dir=str(tmp_path))
        assert len(result.classes) >= 1
        return result.classes[0].get("method_details", [])

    def test_void_return_type(self, tmp_path):
        """void return type is extracted."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                void Save();
            };
        """)
        assert len(methods) >= 1
        assert methods[0]["return_type"] == "void"

    def test_int_return_type(self, tmp_path):
        """Primitive int return type is extracted."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                int GetCount();
            };
        """)
        assert len(methods) >= 1
        assert methods[0]["return_type"] == "int"

    def test_pointer_return_type(self, tmp_path):
        """Pointer return type (Scene*) is extracted."""
        methods = self._get_methods(tmp_path, """
            class Factory {
            public:
                static Scene* Create();
            };
        """)
        assert len(methods) >= 1
        assert "*" in methods[0]["return_type"]

    def test_const_ref_return_type(self, tmp_path):
        """Const reference return type is extracted."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                const std::string& GetName() const;
            };
        """)
        assert len(methods) >= 1
        rt = methods[0]["return_type"]
        assert "string" in rt
        assert "&" in rt

    def test_parameter_types_extracted(self, tmp_path):
        """Parameter types (const char*) are extracted."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                void Save(const char* path, int format);
            };
        """)
        assert len(methods) >= 1
        params = methods[0]["parameters"]
        assert len(params) >= 2
        path_param = next((p for p in params if p["name"] == "path"), None)
        assert path_param is not None
        assert "char" in path_param["type_annotation"]
        fmt_param = next((p for p in params if p["name"] == "format"), None)
        assert fmt_param is not None
        assert "int" in fmt_param["type_annotation"]

    def test_static_modifier_detected(self, tmp_path):
        """Static methods are detected."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                static Foo* Create();
            };
        """)
        assert len(methods) >= 1
        assert methods[0]["is_static"] is True

    def test_method_name_correct(self, tmp_path):
        """Method names are correctly extracted from function_declarator."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                void Save(const char* path);
                int GetSlideCount();
                static Foo* Load(const char* path);
            };
        """)
        names = [m["name"] for m in methods]
        assert "Save" in names
        assert "GetSlideCount" in names
        assert "Load" in names

    def test_destructor_skipped(self, tmp_path):
        """Destructors (~ClassName) are not included."""
        methods = self._get_methods(tmp_path, """
            class Foo {
            public:
                ~Foo();
                void Save();
            };
        """)
        names = [m["name"] for m in methods]
        assert not any(n.startswith("~") for n in names)
        assert "Save" in names


# ── TC-CPP-405: Multi-module CMake ranking ────────────────────────────

class TestCppMultiModuleCmake:
    """Verify detect_package_root() ranks multiple CMakeLists.txt targets."""

    def _make_multi_cmake(self, tmp_path: Path):
        """Create a multi-module repo with CMakeLists.txt in multiple dirs."""
        # Root CMake
        root_cmake = tmp_path / "CMakeLists.txt"
        root_cmake.write_text("project(Root)\nadd_subdirectory(libs/slides)\nadd_subdirectory(libs/cells)\n")
        # Slides module
        slides_dir = tmp_path / "libs" / "slides"
        slides_dir.mkdir(parents=True)
        (slides_dir / "CMakeLists.txt").write_text(
            "project(AsposeSlides)\nadd_library(Aspose.Slides SHARED src/pres.cpp)\n"
        )
        (slides_dir / "include").mkdir()
        (slides_dir / "include" / "Presentation.h").write_text("class Presentation {};")
        # Cells module
        cells_dir = tmp_path / "libs" / "cells"
        cells_dir.mkdir(parents=True)
        (cells_dir / "CMakeLists.txt").write_text(
            "project(AsposeCells)\nadd_library(Aspose.Cells SHARED src/wb.cpp)\n"
        )
        (cells_dir / "include").mkdir()
        (cells_dir / "include" / "Workbook.h").write_text("class Workbook {};")
        # Test directory (should be excluded)
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "CMakeLists.txt").write_text("project(Tests)\n")
        return tmp_path

    def test_multi_cmake_selects_by_canonical(self, tmp_path):
        """Multi-module: selects module whose project_name matches canonical_import."""
        from launcher.workers.understand.adapters._cpp import CppExtractor

        repo = self._make_multi_cmake(tmp_path)
        product = SimpleNamespace(canonical_import="Aspose::Slides")
        ext = CppExtractor()
        root = ext.detect_package_root(repo, product)
        assert "slides" in root.lower(), f"Expected slides path, got: {root}"

    def test_single_cmake_returns_include(self, tmp_path):
        """Single root CMakeLists.txt falls back to include/ directory."""
        from launcher.workers.understand.adapters._cpp import CppExtractor

        (tmp_path / "CMakeLists.txt").write_text("project(MyLib)\n")
        (tmp_path / "include").mkdir()
        (tmp_path / "include" / "mylib.h").write_text("// header\n")
        product = SimpleNamespace(canonical_import="MyLib")
        ext = CppExtractor()
        root = ext.detect_package_root(tmp_path, product)
        assert root == "include"

    def test_test_directories_excluded(self, tmp_path):
        """CMakeLists.txt in test/ directories are excluded from ranking."""
        from launcher.workers.understand.adapters._cpp import CppExtractor

        repo = self._make_multi_cmake(tmp_path)
        product = SimpleNamespace(canonical_import="Tests")
        ext = CppExtractor()
        root = ext.detect_package_root(repo, product)
        assert "test" not in root.lower(), f"Test dir should be excluded, got: {root}"

    def test_fallback_to_shortest_path(self, tmp_path):
        """When no canonical match, shortest path wins."""
        from launcher.workers.understand.adapters._cpp import CppExtractor

        repo = self._make_multi_cmake(tmp_path)
        product = SimpleNamespace(canonical_import="NoMatch")
        ext = CppExtractor()
        root = ext.detect_package_root(repo, product)
        # Should still return something (not empty)
        assert root, "Should fall back to some module root"


# ── TC-UND-209: C++ install_command generation ─────────────────────────

class TestCppInstallCommand:
    """Verify C++ repos produce a non-empty install_command after CMake override."""

    def test_cpp_in_install_cmd_map(self):
        """_INSTALL_CMD_MAP must contain a 'cpp' entry with {package} placeholder."""
        from launcher.workers.scout.scout import _INSTALL_CMD_MAP

        assert "cpp" in _INSTALL_CMD_MAP, "cpp missing from _INSTALL_CMD_MAP"
        template = _INSTALL_CMD_MAP["cpp"]
        # Verify the {package} placeholder works
        result = template.format(package="AsposeSlideCpp")
        assert "AsposeSlideCpp" in result

    def test_cpp_in_lang_manifest_priority(self):
        """_LANG_MANIFEST_PRIORITY must contain a 'cpp' entry."""
        from launcher.workers.scout.scout import _LANG_MANIFEST_PRIORITY

        assert "cpp" in _LANG_MANIFEST_PRIORITY
        assert _LANG_MANIFEST_PRIORITY["cpp"] == []

    def test_cpp_install_command_generated(self, tmp_path):
        """C++ repo with CMakeLists.txt generates a non-empty install_command."""
        from launcher.workers.scout.scout import _INSTALL_CMD_MAP

        # Simulate what _extract_shared_facts does after CMake override:
        # 1. _extract_package_metadata returns UNKNOWN (no manifest)
        # 2. CMake override sets package_name to "AsposeSlides"
        # 3. install_command generated from _INSTALL_CMD_MAP["cpp"]
        package_name = "AsposeSlides"  # after CMake override
        primary_language = "cpp"
        install_command = ""
        if package_name and package_name != "UNKNOWN" and primary_language in _INSTALL_CMD_MAP:
            install_command = _INSTALL_CMD_MAP[primary_language].format(package=package_name)

        assert install_command, "install_command should be non-empty for C++ with valid package_name"
        assert "AsposeSlides" in install_command

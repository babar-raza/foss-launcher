"""Tests for shared facts extraction in scout (capability #2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.models.understanding import FileCategory, FileEntry
from launcher.workers.understand.scout import _extract_shared_facts
from launcher.workers.understand.file_classifier import classify_file, detect_language


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    return d


def _build_file_index(files: list[str]) -> dict[str, FileEntry]:
    """Build a file_index from a list of paths using the real classifier."""
    index: dict[str, FileEntry] = {}
    for f in files:
        index[f] = FileEntry(
            category=classify_file(f),
            size_bytes=100,
            language=detect_language(f),
        )
    return index


class TestExtractSharedFacts:
    def test_empty_repo(self, repo_dir: Path) -> None:
        facts = _extract_shared_facts(repo_dir, [], {})
        # TC-4217: package_name is "UNKNOWN" sentinel when no manifest is found (not "")
        assert facts.package_name == "UNKNOWN"
        assert facts.version == ""
        assert facts.primary_language == ""
        assert facts.build_systems == []

    def test_detects_python_language(self, repo_dir: Path) -> None:
        files = ["src/main.py", "src/util.py", "src/helper.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.primary_language == "python"

    def test_detects_java_language(self, repo_dir: Path) -> None:
        files = ["src/Main.java", "src/Util.java"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.primary_language == "java"

    def test_detects_build_systems(self, repo_dir: Path) -> None:
        (repo_dir / "pyproject.toml").write_text('[project]\nname = "test"', encoding="utf-8")
        files = ["pyproject.toml", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert "pyproject" in facts.build_systems

    def test_detects_multiple_build_systems(self, repo_dir: Path) -> None:
        (repo_dir / "pyproject.toml").write_text("", encoding="utf-8")
        (repo_dir / "Makefile").write_text("", encoding="utf-8")
        files = ["pyproject.toml", "Makefile", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert "pyproject" in facts.build_systems
        assert "make" in facts.build_systems

    def test_has_tests(self, repo_dir: Path) -> None:
        files = ["src/main.py", "tests/test_main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.has_tests is True

    def test_no_tests(self, repo_dir: Path) -> None:
        files = ["src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.has_tests is False

    def test_has_ci(self, repo_dir: Path) -> None:
        files = ["src/main.py", ".github/workflows/ci.yml"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.has_ci is True

    def test_has_docs_folder(self, repo_dir: Path) -> None:
        files = ["docs/guide.md", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.has_docs_folder is True

    def test_has_examples_folder(self, repo_dir: Path) -> None:
        files = ["examples/demo.py", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.has_examples_folder is True

    def test_parses_pyproject_toml(self, repo_dir: Path) -> None:
        (repo_dir / "pyproject.toml").write_text(
            '[project]\nname = "my-package"\nversion = "1.2.3"\nlicense = "MIT"\n',
            encoding="utf-8",
        )
        files = ["pyproject.toml", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.package_name == "my-package"
        assert facts.version == "1.2.3"
        assert facts.license_type == "MIT"
        assert facts.install_command == "pip install my-package"

    def test_parses_setup_cfg(self, repo_dir: Path) -> None:
        (repo_dir / "setup.cfg").write_text(
            "[metadata]\nname = my-lib\nversion = 0.1.0\nlicense = Apache-2.0\n",
            encoding="utf-8",
        )
        files = ["setup.cfg", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.package_name == "my-lib"
        assert facts.version == "0.1.0"

    def test_pyproject_takes_precedence(self, repo_dir: Path) -> None:
        (repo_dir / "pyproject.toml").write_text(
            '[project]\nname = "from-pyproject"\n',
            encoding="utf-8",
        )
        (repo_dir / "setup.cfg").write_text(
            "[metadata]\nname = from-setup-cfg\n",
            encoding="utf-8",
        )
        files = ["pyproject.toml", "setup.cfg", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.package_name == "from-pyproject"

    def test_missing_pyproject_falls_back(self, repo_dir: Path) -> None:
        (repo_dir / "setup.cfg").write_text(
            "[metadata]\nname = fallback-pkg\n",
            encoding="utf-8",
        )
        files = ["setup.cfg", "src/main.py"]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.package_name == "fallback-pkg"

    # TC-4235: Rich metadata tests for non-Python manifest parsers

    def test_package_json_extracts_description_deps_scripts(self, repo_dir: Path) -> None:
        (repo_dir / "package.json").write_text(json.dumps({
            "name": "my-node-lib",
            "version": "1.2.3",
            "license": "MIT",
            "description": "A useful Node library",
            "dependencies": {"axios": "^1.0", "lodash": "^4.0"},
            "scripts": {"build": "tsc", "test": "jest"},
        }))
        fi = _build_file_index(["package.json"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.description == "A useful Node library"
        assert "axios" in facts.dependencies
        assert facts.package_name == "my-node-lib"

    def test_cargo_toml_extracts_description_deps(self, repo_dir: Path) -> None:
        cargo_content = (
            '[package]\nname = "my-crate"\nversion = "0.1.0"\nlicense = "MIT"\n'
            'description = "A Rust crate"\n\n[dependencies]\nserde = "1.0"\ntokio = "1.0"\n'
        )
        (repo_dir / "Cargo.toml").write_text(cargo_content)
        fi = _build_file_index(["Cargo.toml"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.description == "A Rust crate"
        assert "serde" in facts.dependencies
        assert facts.package_name == "my-crate"

    def test_pom_xml_extracts_description_deps(self, repo_dir: Path) -> None:
        pom = '''<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>com.example</groupId>
  <artifactId>my-lib</artifactId>
  <version>1.0.0</version>
  <description>A Java library</description>
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13</version>
    </dependency>
  </dependencies>
</project>'''
        (repo_dir / "pom.xml").write_text(pom)
        fi = _build_file_index(["pom.xml"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.description == "A Java library"
        assert any("junit" in d for d in facts.dependencies)
        assert facts.package_name == "com.example:my-lib"

    def test_csproj_extracts_description_deps(self, repo_dir: Path) -> None:
        csproj = '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>MyLib</AssemblyName>
    <Version>2.0.0</Version>
    <Description>A .NET library</Description>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.0" />
  </ItemGroup>
</Project>'''
        (repo_dir / "MyLib.csproj").write_text(csproj)
        fi = _build_file_index(["MyLib.csproj"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.description == "A .NET library"
        assert "Newtonsoft.Json" in facts.dependencies

    def test_gemspec_extracts_description_deps(self, repo_dir: Path) -> None:
        gemspec = '''Gem::Specification.new do |s|
  s.name = "my-gem"
  s.version = "1.0.0"
  s.license = "MIT"
  s.description = "A Ruby gem"
  s.add_runtime_dependency "rake", "~> 12.0"
  s.add_dependency "activesupport", ">= 5.0"
end'''
        (repo_dir / "my-gem.gemspec").write_text(gemspec)
        fi = _build_file_index(["my-gem.gemspec"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.description == "A Ruby gem"
        assert "rake" in facts.dependencies

    def test_platform_priority_java_uses_pom(self, repo_dir: Path) -> None:
        """Java repo should use pom.xml even when pyproject.toml is present (empty name)."""
        (repo_dir / "pyproject.toml").write_text("[project]\nname = ''\n")
        pom = '''<project xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>com.test</groupId><artifactId>java-priority</artifactId>
  <version>1.0</version><description>Java wins</description>
</project>'''
        (repo_dir / "pom.xml").write_text(pom)
        # Build file_index with java source file so primary_language=java
        (repo_dir / "Main.java").write_text("public class Main {}")
        fi = _build_file_index(["pyproject.toml", "pom.xml", "Main.java"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.package_name == "com.test:java-priority"
        assert facts.description == "Java wins"

    def test_platform_priority_python_unchanged(self, repo_dir: Path) -> None:
        """Python repo still picks up pyproject.toml (regression test)."""
        pyproject = '[project]\nname = "my-python-lib"\nversion = "3.0.0"\n'
        (repo_dir / "pyproject.toml").write_text(pyproject)
        fi = _build_file_index(["pyproject.toml"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.package_name == "my-python-lib"

    # TC-4306 tests

    def test_dotnet_build_system_detected(self, repo_dir: Path) -> None:
        """TC-4306: .csproj file in file_tree should add 'dotnet' to build_systems."""
        (repo_dir / "MyLib.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><AssemblyName>MyLib</AssemblyName></PropertyGroup></Project>')
        fi = _build_file_index(["MyLib.csproj"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert "dotnet" in facts.build_systems

    def test_multi_csproj_selects_library_not_exe(self, repo_dir: Path) -> None:
        """TC-4306: Converter (Exe) + Library (.dll) → library is selected."""
        lib_dir = repo_dir / "src" / "main" / "MyLib"
        lib_dir.mkdir(parents=True)
        exe_dir = repo_dir / "src" / "converter"
        exe_dir.mkdir(parents=True)
        lib_csproj = lib_dir / "MyLib.csproj"
        exe_csproj = exe_dir / "Converter.csproj"
        lib_csproj.write_text('<Project><PropertyGroup><AssemblyName>MyLib</AssemblyName><Version>1.0.0</Version></PropertyGroup></Project>')
        exe_csproj.write_text('<Project><PropertyGroup><OutputType>Exe</OutputType><AssemblyName>Converter</AssemblyName></PropertyGroup></Project>')
        fi = _build_file_index(["src/main/MyLib/MyLib.csproj", "src/converter/Converter.csproj"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.package_name == "MyLib"

    def test_test_csproj_excluded_when_lib_present(self, repo_dir: Path) -> None:
        """TC-4306: Test project excluded when a library project is available."""
        lib_dir = repo_dir / "src" / "main"
        lib_dir.mkdir(parents=True)
        test_dir = repo_dir / "src" / "tests"
        test_dir.mkdir(parents=True)
        (lib_dir / "MyLib.csproj").write_text('<Project><PropertyGroup><AssemblyName>MyLib</AssemblyName><Version>2.0.0</Version></PropertyGroup></Project>')
        (test_dir / "MyLib.Tests.csproj").write_text('<Project><PropertyGroup><AssemblyName>MyLib.Tests</AssemblyName></PropertyGroup></Project>')
        fi = _build_file_index(["src/main/MyLib.csproj", "src/tests/MyLib.Tests.csproj"])
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.package_name == "MyLib"

    # TC-5189 tests

    def test_canonical_import_selects_matching_csproj(self, repo_dir: Path) -> None:
        """TC-5189: canonical_import should prefer matching AssemblyName over shorter path."""
        # Converter has a shorter path but the library matches canonical_import
        conv_dir = repo_dir / "src" / "converter"
        conv_dir.mkdir(parents=True)
        lib_dir = repo_dir / "src" / "main" / "Aspose.ThreeD"
        lib_dir.mkdir(parents=True)
        conv_csproj = conv_dir / "Converter.csproj"
        lib_csproj = lib_dir / "Aspose.ThreeD.csproj"
        conv_csproj.write_text(
            '<Project><PropertyGroup><AssemblyName>Aspose.3D.Converter</AssemblyName>'
            '</PropertyGroup></Project>'
        )
        lib_csproj.write_text(
            '<Project><PropertyGroup><AssemblyName>Aspose.ThreeD</AssemblyName>'
            '<Version>1.0.0</Version></PropertyGroup></Project>'
        )
        fi = _build_file_index([
            "src/converter/Converter.csproj",
            "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj",
        ])
        facts = _extract_shared_facts(
            repo_dir, list(fi.keys()), fi, canonical_import="Aspose.ThreeD",
        )
        assert facts.package_name == "Aspose.ThreeD"
        assert "dotnet" in facts.build_systems

    def test_canonical_import_empty_falls_back_to_shortest(self, repo_dir: Path) -> None:
        """TC-5189: Without canonical_import, shortest non-test non-exe path wins."""
        short_dir = repo_dir / "src" / "A"
        short_dir.mkdir(parents=True)
        long_dir = repo_dir / "src" / "deep" / "nested" / "B"
        long_dir.mkdir(parents=True)
        (short_dir / "A.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>A</AssemblyName>'
            '<Version>1.0.0</Version></PropertyGroup></Project>'
        )
        (long_dir / "B.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>B</AssemblyName>'
            '<Version>2.0.0</Version></PropertyGroup></Project>'
        )
        fi = _build_file_index([
            "src/A/A.csproj",
            "src/deep/nested/B/B.csproj",
        ])
        # No canonical_import — should pick shorter path (A)
        facts = _extract_shared_facts(repo_dir, list(fi.keys()), fi)
        assert facts.package_name == "A"


class TestSelectMainCsproj:
    """TC-5189: Unit tests for _select_main_csproj canonical_import scoring."""

    def test_canonical_import_beats_shorter_path(self, tmp_path: Path) -> None:
        from launcher.workers.scout.scout import _select_main_csproj

        short = tmp_path / "src" / "short"
        short.mkdir(parents=True)
        deep = tmp_path / "src" / "main" / "deep"
        deep.mkdir(parents=True)
        (short / "Short.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>Short</AssemblyName></PropertyGroup></Project>'
        )
        (deep / "MyLib.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>MyLib</AssemblyName></PropertyGroup></Project>'
        )
        result = _select_main_csproj(
            sorted(tmp_path.glob("**/*.csproj")),
            repo_dir=tmp_path,
            canonical_import="MyLib",
        )
        assert result is not None
        assert result.name == "MyLib.csproj"

    def test_no_canonical_import_picks_shortest(self, tmp_path: Path) -> None:
        from launcher.workers.scout.scout import _select_main_csproj

        short = tmp_path / "src" / "A"
        short.mkdir(parents=True)
        deep = tmp_path / "src" / "x" / "y" / "B"
        deep.mkdir(parents=True)
        (short / "A.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>A</AssemblyName></PropertyGroup></Project>'
        )
        (deep / "B.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>B</AssemblyName></PropertyGroup></Project>'
        )
        result = _select_main_csproj(
            sorted(tmp_path.glob("**/*.csproj")),
            repo_dir=tmp_path,
        )
        assert result is not None
        assert result.name == "A.csproj"

    def test_canonical_import_normalized_matching(self, tmp_path: Path) -> None:
        """Dashes, underscores, and dots normalize for matching."""
        from launcher.workers.scout.scout import _select_main_csproj

        d = tmp_path / "src"
        d.mkdir(parents=True)
        (d / "Aspose.ThreeD.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>Aspose.ThreeD</AssemblyName></PropertyGroup></Project>'
        )
        (d / "Other.csproj").write_text(
            '<Project><PropertyGroup><AssemblyName>Other</AssemblyName></PropertyGroup></Project>'
        )
        # canonical_import uses dashes — should still match dot-separated AssemblyName
        result = _select_main_csproj(
            sorted(tmp_path.glob("**/*.csproj")),
            repo_dir=tmp_path,
            canonical_import="Aspose-ThreeD",
        )
        assert result is not None
        assert result.name == "Aspose.ThreeD.csproj"


# ===================================================================
# TC-5322: C/C++ primary_language merge
# ===================================================================

class TestCppPrimaryLanguageMerge:
    """SC-01 (TC-5322): .h files classify as 'c' but are C++ headers in mixed repos."""

    def test_mixed_h_and_cpp_reports_cpp(self, repo_dir: Path) -> None:
        """More .h files than .cpp should still yield primary_language='cpp'."""
        # Mirrors slides/cpp: 260 .h files vs 206 .cpp files
        files = (
            [f"include/A{i}.h" for i in range(10)]   # classified as "c"
            + [f"src/B{i}.cpp" for i in range(7)]    # classified as "cpp"
        )
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.primary_language == "cpp", (
            f"Expected 'cpp', got {facts.primary_language!r}. "
            ".h files should merge into cpp when cpp files are also present."
        )

    def test_pure_c_repo_unaffected(self, repo_dir: Path) -> None:
        """Pure C repos (.h + .c only, no .cpp) keep primary_language='c'."""
        files = [f"src/A{i}.c" for i in range(5)] + [f"include/B{i}.h" for i in range(8)]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.primary_language == "c", (
            f"Expected 'c', got {facts.primary_language!r}. "
            "Pure-C repos (no .cpp/.hpp) must not be reclassified."
        )

    def test_hpp_files_alone_report_cpp(self, repo_dir: Path) -> None:
        """A repo with only .hpp files reports 'cpp'."""
        files = [f"include/Class{i}.hpp" for i in range(5)]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.primary_language == "cpp"

    def test_cpp_install_command_generated(self, repo_dir: Path) -> None:
        """After merge, install_command uses vcpkg (cpp key in _INSTALL_CMD_MAP)."""
        cmake_content = 'cmake_minimum_required(VERSION 3.10)\nproject(aspose_slides_foss)\n'
        (repo_dir / "CMakeLists.txt").write_text(cmake_content, encoding="utf-8")
        files = [f"include/A{i}.h" for i in range(5)] + [f"src/B{i}.cpp" for i in range(3)]
        facts = _extract_shared_facts(repo_dir, files, _build_file_index(files))
        assert facts.primary_language == "cpp"
        # package_name may be extracted from CMakeLists.txt; install_command must use vcpkg if set
        if facts.package_name and facts.package_name != "UNKNOWN":
            assert facts.install_command.startswith("vcpkg install"), (
                f"Expected vcpkg install command, got {facts.install_command!r}"
            )

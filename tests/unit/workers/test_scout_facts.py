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

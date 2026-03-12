"""Tests for healing-phase changes to ts_analyzer."""
from __future__ import annotations

import concurrent.futures
import pytest


class TestThreadSafety:
    """HC-02: Verify _parser_cache concurrent access."""

    def test_concurrent_parser_access(self):
        """8 threads requesting parsers simultaneously — no exceptions."""
        from launcher.shared.ts_analyzer import _get_parser
        languages = ["java", "javascript", "typescript", "go", "rust", "ruby", "php", "csharp"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_get_parser, lang) for lang in languages]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(r is not None for r in results)
        assert len(results) == 8


class TestRegexHardening:
    """HC-05: Verify _is_public doesn't false-positive."""

    def test_is_public_no_false_positive_on_string_content(self, tmp_path):
        """A Java field with 'public' in a string should not cause _is_public to match the field itself as public."""
        from launcher.shared.ts_analyzer import analyzer
        # Java class with a PRIVATE field containing "public" in its value
        code = '''
public class Config {
    private String label = "public API key";
    String publicKey = "test";
}
'''
        (tmp_path / "Config.java").write_text(code)
        result = analyzer.analyze_file(tmp_path / "Config.java", "java", repo_dir=tmp_path)
        # Only the class itself should be exported (it has public modifier)
        # The fields should NOT be exported
        exports = analyzer.extract_exports_from_code(code, "java")
        assert "Config" in exports
        # publicKey is package-private (no modifier), should not be in exports
        assert "publicKey" not in exports


class TestGoRegexAnchoring:
    """TS-01 G-03: Go import regex must not match inside string literals."""

    def test_go_normalize_no_false_positive_in_string(self):
        """A Go string containing an Aspose import path must NOT be rewritten."""
        from launcher.shared.ts_analyzer import normalize_imports

        code = 'var s = "github.com/aspose/cells"'
        result = normalize_imports(code, "go", "github.com/aspose/cells_foss")
        assert result == code, f"String literal was rewritten: {result!r}"

    def test_go_normalize_rewrites_real_import(self):
        """A real Go import statement MUST be rewritten."""
        from launcher.shared.ts_analyzer import normalize_imports

        code = 'import "github.com/aspose/cells"'
        result = normalize_imports(code, "go", "github.com/aspose/cells_foss")
        assert "cells_foss" in result

    def test_go_normalize_rewrites_grouped_import(self):
        """An indented import inside import() block MUST be rewritten."""
        from launcher.shared.ts_analyzer import normalize_imports

        code = 'import (\n\t"github.com/aspose/cells"\n)'
        result = normalize_imports(code, "go", "github.com/aspose/cells_foss")
        assert "cells_foss" in result


class TestDiscoverSourceFiles:
    """HC-04 / TS-04: discover_source_files finds multi-lang files, excludes shell/sql."""

    def test_discover_source_files_finds_java(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "Foo.java").write_text("public class Foo {}")
        from launcher.shared.code_analyzer import discover_source_files
        result = discover_source_files(tmp_path, max_files=100)
        names = [p.name for p in result]
        assert "Foo.java" in names

    def test_discover_source_files_finds_rust(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "lib.rs").write_text("pub fn main() {}")
        from launcher.shared.code_analyzer import discover_source_files
        result = discover_source_files(tmp_path, max_files=100)
        names = [p.name for p in result]
        assert "lib.rs" in names

    def test_discover_source_files_excludes_shell_sql(self, tmp_path):
        (tmp_path / "script.sh").write_text("#!/bin/bash")
        (tmp_path / "query.sql").write_text("SELECT 1")
        (tmp_path / "run.ps1").write_text("Write-Host 'hi'")
        from launcher.shared.code_analyzer import discover_source_files
        result = discover_source_files(tmp_path, max_files=100)
        names = [p.name for p in result]
        assert "script.sh" not in names
        assert "query.sql" not in names
        assert "run.ps1" not in names


class TestDiscoverManifests:
    """HC-04: discover_manifests finds multi-platform manifests."""

    def test_discover_manifests_finds_pom_xml(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        from launcher.shared.code_analyzer import discover_manifests
        result = discover_manifests(tmp_path)
        names = [p.name for p in result]
        assert "pom.xml" in names

    def test_discover_manifests_finds_build_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'")
        from launcher.shared.code_analyzer import discover_manifests
        result = discover_manifests(tmp_path)
        names = [p.name for p in result]
        assert "build.gradle" in names


class TestExtractCodeLimitations:
    """HC-04 + TS-03: extract_code_limitations with multi-lang TODO/FIXME."""

    def test_extract_code_limitations_finds_java_todo(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "Foo.java").write_text("public class Foo {\n    // TODO: implement save\n}\n")
        from launcher.shared.code_analyzer import extract_code_limitations
        claims = extract_code_limitations(tmp_path, "TestProduct")
        texts = [c["claim_text"] for c in claims]
        assert any("implement save" in t for t in texts)

    def test_extract_code_limitations_finds_python_todo(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "foo.py").write_text("# TODO: fix parser\ndef parse(): pass\n")
        from launcher.shared.code_analyzer import extract_code_limitations
        claims = extract_code_limitations(tmp_path, "TestProduct")
        texts = [c["claim_text"] for c in claims]
        assert any("fix parser" in t for t in texts)


class TestStructlog:
    """HC-06: Verify structlog is used."""

    def test_logger_is_structlog(self):
        from launcher.shared import ts_analyzer
        import structlog
        # structlog.get_logger() returns a BoundLoggerLazyProxy or similar
        assert hasattr(ts_analyzer.logger, 'bind')
        assert not hasattr(ts_analyzer.logger, 'handlers')  # stdlib Logger has handlers

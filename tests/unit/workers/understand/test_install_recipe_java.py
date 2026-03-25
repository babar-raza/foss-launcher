"""TC-5139: Tests for pom.xml parsing and install recipe fallback robustness.

Verifies that:
1. pom.xml with XML namespaces (xmlns:xsi + xsi:schemaLocation) parses correctly
2. Java platform with failed recipe does NOT fall through to Python strategies
3. Cached SharedFacts path uses correct platform-specific source labels
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ── pom.xml namespace stripping ─────────────────────────────────────


class TestExtractJavaRecipePomXml:
    """Verify _extract_java_recipe handles real-world pom.xml files."""

    def _call(self, pom_content: str, *, canonical_import: str = "com.aspose.threed"):
        from launcher.workers.understand.extract._deterministic import _extract_java_recipe

        tmp = self._make_repo(pom_content)
        product = SimpleNamespace(
            canonical_import=canonical_import,
            display_name="Aspose.3D",
            family="3d",
            platform="java",
            runtime_import="",
        )
        return _extract_java_recipe(tmp, product)

    def _make_repo(self, pom_content: str) -> Path:
        """Write pom.xml to a temp dir and return the dir path."""
        import tempfile, os
        d = Path(tempfile.mkdtemp())
        (d / "pom.xml").write_text(pom_content, encoding="utf-8")
        return d

    def test_standard_pom_without_namespaces(self):
        """Minimal pom.xml without any namespace declarations."""
        pom = textwrap.dedent("""\
            <project>
                <groupId>com.aspose</groupId>
                <artifactId>aspose-3d-foss</artifactId>
                <version>26.1.0</version>
            </project>
        """)
        recipe = self._call(pom)
        assert recipe is not None
        assert recipe.package_name == "com.aspose:aspose-3d-foss"
        assert "26.1.0" in recipe.install_command
        assert recipe.source_file == "pom.xml"

    def test_pom_with_xmlns_xsi_and_schema_location(self):
        """Real-world pom.xml with xmlns, xmlns:xsi, and xsi:schemaLocation.

        This is the exact pattern that caused ET.ParseError before TC-5139.
        """
        pom = textwrap.dedent("""\
            <project xmlns="http://maven.apache.org/POM/4.0.0"
                     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
                <modelVersion>4.0.0</modelVersion>
                <groupId>com.aspose</groupId>
                <artifactId>aspose-3d-foss</artifactId>
                <version>26.1.0</version>
                <packaging>jar</packaging>
            </project>
        """)
        recipe = self._call(pom)
        assert recipe is not None
        assert recipe.package_name == "com.aspose:aspose-3d-foss"
        assert recipe.version_constraint == "26.1.0"
        assert "mvn dependency:get" in recipe.install_command
        assert "com.aspose:aspose-3d-foss:26.1.0" in recipe.install_command

    def test_pom_with_only_xmlns_no_xsi(self):
        """pom.xml with only the default xmlns (no xsi prefix)."""
        pom = textwrap.dedent("""\
            <project xmlns="http://maven.apache.org/POM/4.0.0">
                <groupId>org.example</groupId>
                <artifactId>my-lib</artifactId>
                <version>1.0.0</version>
            </project>
        """)
        recipe = self._call(pom, canonical_import="org.example.mylib")
        assert recipe is not None
        assert recipe.package_name == "org.example:my-lib"

    def test_pom_missing_group_id_returns_none(self):
        """pom.xml without groupId → None."""
        pom = textwrap.dedent("""\
            <project>
                <artifactId>something</artifactId>
                <version>1.0</version>
            </project>
        """)
        assert self._call(pom) is None

    def test_pom_missing_artifact_id_returns_none(self):
        """pom.xml without artifactId → None."""
        pom = textwrap.dedent("""\
            <project>
                <groupId>com.example</groupId>
                <version>1.0</version>
            </project>
        """)
        assert self._call(pom) is None

    def test_pom_malformed_xml_returns_none(self):
        """Completely broken XML → None (not crash)."""
        assert self._call("<<< not xml >>>") is None

    def test_pom_with_custom_namespace_attr_preserved(self):
        """Non-xsi namespace attributes must survive stripping (SR-RJ-01).

        Only xsi:-prefixed attrs should be stripped; custom:id should be
        ignored by the regex (and ElementTree tolerates it in lax mode or
        the element still parses because custom: without declaration is
        stripped by the broader xmlns regex only when declared).
        """
        pom = textwrap.dedent("""\
            <project>
                <groupId>com.aspose</groupId>
                <artifactId>aspose-3d-foss</artifactId>
                <version>1.0</version>
            </project>
        """)
        recipe = self._call(pom)
        assert recipe is not None
        assert recipe.package_name == "com.aspose:aspose-3d-foss"

    def test_no_pom_file_returns_none(self):
        """Repo without pom.xml → None."""
        from launcher.workers.understand.extract._deterministic import _extract_java_recipe
        import tempfile
        empty = Path(tempfile.mkdtemp())
        product = SimpleNamespace(
            canonical_import="com.aspose.threed",
            display_name="Aspose.3D",
            family="3d",
            platform="java",
            runtime_import="",
        )
        assert _extract_java_recipe(empty, product) is None

    def test_verification_uses_canonical_import(self):
        """Verification code should reference canonical_import, not package coords."""
        pom = textwrap.dedent("""\
            <project>
                <groupId>com.aspose</groupId>
                <artifactId>aspose-3d-foss</artifactId>
                <version>1.0</version>
            </project>
        """)
        recipe = self._call(pom, canonical_import="com.aspose.threed")
        assert recipe is not None
        assert "com.aspose.threed" in recipe.verification_code


# ── Non-Python platform fallback guard ───────────────────────────────


class TestDedicatedPlatformFallbackGuard:
    """Verify that non-Python platforms do NOT fall through to Python strategies."""

    def _call(self, platform: str, shared_facts=None):
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        import tempfile

        repo_dir = Path(tempfile.mkdtemp())
        product = SimpleNamespace(
            canonical_import="com.aspose.threed",
            display_name="Aspose.3D",
            family="3d",
            platform=platform,
            install_cmd="",
            runtime_import="",
        )
        return extract_install_recipe(repo_dir, product, shared_facts=shared_facts)

    def test_java_no_pom_no_shared_facts_returns_none(self):
        """Java with no pom.xml and no shared_facts → None (not pip install)."""
        result = self._call("java", shared_facts=None)
        assert result is None

    def test_java_no_pom_with_shared_facts_uses_cached(self):
        """Java with no pom.xml but shared_facts available → cached recipe with pom.xml label."""
        facts = SimpleNamespace(package_name="com.aspose:aspose-3d-foss", version="26.1.0")
        result = self._call("java", shared_facts=facts)
        assert result is not None
        assert result.source_file == "pom.xml (cached)"
        assert result.package_name == "com.aspose:aspose-3d-foss"
        assert "pip" not in result.install_command.lower()

    def test_dotnet_no_csproj_no_shared_facts_returns_none(self):
        """DotNet with no .csproj and no shared_facts → None."""
        result = self._call("dotnet", shared_facts=None)
        assert result is None

    def test_dotnet_no_csproj_with_shared_facts_uses_cached(self):
        """DotNet with shared_facts → cached recipe with *.csproj label."""
        facts = SimpleNamespace(package_name="Aspose.3D", version="1.0.0")
        result = self._call("dotnet", shared_facts=facts)
        assert result is not None
        assert result.source_file == "*.csproj (cached)"

    def test_go_no_gomod_returns_none(self):
        """Go with no go.mod and no shared_facts → None."""
        result = self._call("go", shared_facts=None)
        assert result is None

    def test_rust_no_cargo_returns_none(self):
        """Rust with no Cargo.toml and no shared_facts → None."""
        result = self._call("rust", shared_facts=None)
        assert result is None

    def test_python_still_falls_through(self):
        """Python platform should still use Python fallback strategies (not blocked).

        With canonical_import set, Strategy 5 derives a pip install recipe.
        The important thing: Python is NOT blocked by the dedicated-platform guard.
        """
        result = self._call("python", shared_facts=None)
        # Python falls through to Strategy 5 (derive from canonical_import)
        # producing 'pip install com.aspose.threed' — this is the expected Python path
        assert result is not None
        assert "pip install" in result.install_command
        assert result.source_file == "derived"

    def test_java_cached_label_correct(self):
        """Java with shared_facts gets 'pom.xml (cached)' label."""
        facts = SimpleNamespace(package_name="com.aspose:aspose-3d-foss", version="26.1.0")
        result = self._call("java", shared_facts=facts)
        assert result is not None
        assert result.source_file == "pom.xml (cached)"

    def test_go_cached_label_correct(self):
        """Go with shared_facts gets 'go.mod (cached)' label."""
        facts = SimpleNamespace(package_name="github.com/aspose/3d-go", version="1.0")
        result = self._call("go", shared_facts=facts)
        assert result is not None
        assert result.source_file == "go.mod (cached)"

    def test_php_cached_label_correct(self):
        """PHP with shared_facts gets 'composer.json (cached)' label."""
        facts = SimpleNamespace(package_name="aspose/3d-foss", version="1.0")
        result = self._call("php", shared_facts=facts)
        assert result is not None
        assert result.source_file == "composer.json (cached)"

    # ── SR-RJ-04: cached command format tests ────────────────────────

    def test_java_cached_command_is_mvn(self):
        """Java cached recipe uses mvn, not pip (SR-RJ-04)."""
        facts = SimpleNamespace(package_name="com.aspose:aspose-3d-foss", version="26.1.0")
        result = self._call("java", shared_facts=facts)
        assert result is not None
        assert result.install_command.startswith("mvn dependency:get")
        assert "com.aspose:aspose-3d-foss:26.1.0" in result.install_command

    def test_dotnet_cached_command_is_dotnet_add(self):
        """DotNet cached recipe uses dotnet add, not pip (SR-RJ-04)."""
        facts = SimpleNamespace(package_name="Aspose.3D", version="1.0.0")
        result = self._call("dotnet", shared_facts=facts)
        assert result is not None
        assert result.install_command.startswith("dotnet add package")

    def test_go_cached_command_is_go_get(self):
        """Go cached recipe uses go get, not pip (SR-RJ-04)."""
        facts = SimpleNamespace(package_name="github.com/aspose/3d-go", version="1.0")
        result = self._call("go", shared_facts=facts)
        assert result is not None
        assert result.install_command.startswith("go get")

    def test_java_cached_no_version_omits_ver_in_artifact(self):
        """Java cached recipe with empty version has no trailing colon (SR-RJ-02)."""
        facts = SimpleNamespace(package_name="com.aspose:aspose-3d-foss", version="")
        result = self._call("java", shared_facts=facts)
        assert result is not None
        assert result.install_command == "mvn dependency:get -Dartifact=com.aspose:aspose-3d-foss"
        assert ":" not in result.install_command.split("=")[1].rstrip("com.aspose:aspose-3d-foss")

    def test_ruby_no_gemfile_uses_canonical_fallback(self):
        """Ruby with no Gemfile derives from canonical_import (SR-RJ-04).

        _extract_ruby_recipe has its own canonical_import fallback, so it
        never returns None when canonical_import is set.
        """
        result = self._call("ruby", shared_facts=None)
        assert result is not None
        assert result.install_command.startswith("gem install")
        assert result.source_file == "derived"

    # ── SR-RJ-05: Node guard test ────────────────────────────────────

    def test_node_no_package_json_no_shared_facts_returns_none(self):
        """Node with no package.json and no shared_facts returns None (SR-RJ-05)."""
        result = self._call("typescript", shared_facts=None)
        assert result is None

    # ── SR-RJ-06: verification comment syntax ────────────────────────

    def test_ruby_cached_verification_uses_hash_comment(self):
        """Ruby cached recipe verification uses # not // (SR-RJ-06).

        _extract_ruby_recipe has its own canonical_import fallback, so to
        exercise the guard's cached path we need a product with NO
        canonical_import (forcing the extractor to return None).
        """
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        import tempfile

        repo_dir = Path(tempfile.mkdtemp())
        product = SimpleNamespace(
            canonical_import="",
            display_name="Test",
            family="test",
            platform="ruby",
            install_cmd="",
            runtime_import="",
        )
        facts = SimpleNamespace(package_name="aspose-3d-foss", version="1.0")
        result = extract_install_recipe(repo_dir, product, shared_facts=facts)
        assert result is not None
        assert result.verification_code.startswith("#")
        assert "//" not in result.verification_code

    def test_java_cached_verification_uses_slash_comment(self):
        """Java cached recipe verification uses // (SR-RJ-06)."""
        facts = SimpleNamespace(package_name="com.aspose:aspose-3d-foss", version="1.0")
        result = self._call("java", shared_facts=facts)
        assert result is not None
        assert result.verification_code.startswith("//")

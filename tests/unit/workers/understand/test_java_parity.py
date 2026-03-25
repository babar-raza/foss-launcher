"""TC-5140: Tests for Java platform parity — allowlist, test slicing, language markers.

Verifies that Java gets the same level of extraction quality as C#/.NET and Python.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ── Import allowlist (multi-package collection) ─────────────────────


class TestJavaAllowlistMultiPackage:
    """Verify build_import_allowlist collects all packages, not just the first."""

    def _make_repo(self, tmp_path: Path, packages: list[tuple[str, str]]):
        """Create a fake Java repo with multiple packages.

        packages: list of (relative_path, package_declaration)
        """
        src = tmp_path / "src" / "main" / "java"
        for rel, pkg in packages:
            f = src / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"package {pkg};\n\npublic class Foo {{}}\n", encoding="utf-8")
        return tmp_path

    def test_collects_multiple_packages(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        repo = self._make_repo(tmp_path, [
            ("com/aspose/threed/Scene.java", "com.aspose.threed"),
            ("com/aspose/threed/formats/ObjFormat.java", "com.aspose.threed.formats"),
            ("com/aspose/threed/shading/Material.java", "com.aspose.threed.shading"),
        ])
        product = SimpleNamespace(canonical_import="com.aspose.threed")
        ext = JavaExtractor()
        allowlist = ext.build_import_allowlist(repo, "src/main/java", product)

        assert "com.aspose.threed" in allowlist
        assert "com.aspose.threed.formats" in allowlist
        assert "com.aspose.threed.shading" in allowlist
        assert len(allowlist) == 3  # canonical + 2 sub-packages (canonical is deduped)

    def test_single_package_still_works(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        repo = self._make_repo(tmp_path, [
            ("com/example/Main.java", "com.example"),
            ("com/example/Util.java", "com.example"),
        ])
        product = SimpleNamespace(canonical_import="com.example")
        ext = JavaExtractor()
        allowlist = ext.build_import_allowlist(repo, "src/main/java", product)

        assert allowlist == ["com.example"]

    def test_no_package_root_returns_canonical_only(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        product = SimpleNamespace(canonical_import="com.aspose.threed")
        ext = JavaExtractor()
        allowlist = ext.build_import_allowlist(tmp_path, "", product)

        assert allowlist == ["com.aspose.threed"]

    def test_caps_at_20_packages(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        packages = [
            (f"com/pkg{i}/Cls.java", f"com.pkg{i}")
            for i in range(25)
        ]
        repo = self._make_repo(tmp_path, packages)
        product = SimpleNamespace(canonical_import="com.pkg0")
        ext = JavaExtractor()
        allowlist = ext.build_import_allowlist(repo, "src/main/java", product)

        assert len(allowlist) <= 20


# ── Java test slicing ────────────────────────────────────────────────


SAMPLE_JAVA_TEST = textwrap.dedent("""\
    package com.aspose.threed;

    import com.aspose.threed.Scene;
    import com.aspose.threed.Vector3;
    import org.junit.jupiter.api.Test;

    public class SceneTest {

        @Test
        public void testLoadScene() {
            Scene scene = new Scene();
            scene.open("test.obj");
            String name = scene.getRootNode().getName();
            assertEquals("expected", name);
        }

        @Test
        public void testCreateMesh() {
            Scene scene = new Scene();
            Mesh mesh = scene.getRootNode().createChildNode("box", new Box());
            Vector3 pos = mesh.getTransform().getTranslation();
            assertNotNull(pos);
            assertTrue(pos.getX() >= 0);
        }

        public void helperMethod() {
            // This is not a test method — no @Test annotation
        }
    }
""")


class TestJavaTestSlicing:
    """Verify _extract_java_test_slices extracts individual test methods."""

    def _call(self, code: str):
        from launcher.workers.understand.extract._snippets import _extract_java_test_slices

        api_surface = SimpleNamespace(
            public_classes=["Scene", "Mesh", "Vector3", "Box"],
            public_methods=[],
            import_allowlist=["com.aspose.threed"],
        )
        return _extract_java_test_slices(code, api_surface)

    def test_extracts_two_test_methods(self):
        slices = self._call(SAMPLE_JAVA_TEST)
        assert len(slices) == 2

    def test_strips_assertion_noise(self):
        slices = self._call(SAMPLE_JAVA_TEST)
        for s in slices:
            assert "assertEquals" not in s
            assert "assertNotNull" not in s
            assert "assertTrue" not in s

    def test_preserves_import_block(self):
        slices = self._call(SAMPLE_JAVA_TEST)
        for s in slices:
            assert "import com.aspose.threed.Scene" in s

    def test_excludes_non_test_methods(self):
        slices = self._call(SAMPLE_JAVA_TEST)
        for s in slices:
            assert "helperMethod" not in s

    def test_empty_file_returns_empty(self):
        assert self._call("") == []

    def test_no_tests_returns_empty(self):
        code = textwrap.dedent("""\
            package com.example;
            public class Util {
                public void doSomething() { }
            }
        """)
        assert self._call(code) == []

    def test_filter_observability_logging(self, caplog):
        """TC-UND-209: verify structured logging of snippet filter counts."""
        import logging
        with caplog.at_level(logging.DEBUG, logger="launcher.workers.understand.extract._snippets"):
            self._call(SAMPLE_JAVA_TEST)
        log_line = [r for r in caplog.records if "java_test_slicing" in r.message]
        assert len(log_line) >= 1, "Expected java_test_slicing log message"
        msg = log_line[0].message
        assert "@Test=2" in msg  # 2 @Test methods in SAMPLE_JAVA_TEST
        assert "selected=" in msg


# ── Java assertion sanitization ──────────────────────────────────────


class TestSanitizeJavaTestBody:
    """Verify _sanitize_java_test_body strips assertion noise."""

    def _call(self, lines: list[str]) -> str:
        from launcher.workers.understand.extract._snippets import _sanitize_java_test_body
        return _sanitize_java_test_body(lines)

    def test_strips_assert_equals(self):
        result = self._call(["    Scene s = new Scene();", "    assertEquals(1, 1);"])
        assert "assertEquals" not in result
        assert "Scene s = new Scene()" in result

    def test_preserves_product_code(self):
        result = self._call(["    Mesh m = new Mesh();", "    m.setName(\"box\");"])
        assert "Mesh m = new Mesh()" in result
        assert "m.setName" in result


# ── Language markers ─────────────────────────────────────────────────


class TestJavaLanguageMarkers:
    """Verify Java is registered in _LANG_MARKERS."""

    def test_java_in_lang_markers(self):
        from launcher.workers.understand.extract._snippets import _LANG_MARKERS
        assert "java" in _LANG_MARKERS

    def test_java_markers_detect_java_code(self):
        from launcher.workers.understand.extract._snippets import _LANG_MARKERS

        java_code = textwrap.dedent("""\
            import com.aspose.threed.Scene;

            public class Main {
                public static void main(String[] args) {
                    Scene scene = new Scene();
                    System.out.println("Hello");
                }
            }
        """)
        markers = _LANG_MARKERS["java"]
        hits = sum(1 for m in markers if m in java_code)
        assert hits >= 2, f"Expected 2+ marker hits, got {hits}"


# ── Java regex validation fallback ───────────────────────────────────


class TestValidateJavaRegex:
    """Verify _validate_java_regex accepts valid Java snippets."""

    def test_valid_java_class(self):
        from launcher.workers.understand.extract._snippets import _validate_java_regex

        code = textwrap.dedent("""\
            import com.aspose.threed.Scene;
            public class Main {
                public static void main(String[] args) {
                    new Scene();
                }
            }
        """)
        assert _validate_java_regex(code) is True

    def test_plain_text_rejected(self):
        from launcher.workers.understand.extract._snippets import _validate_java_regex
        assert _validate_java_regex("just some plain text here") is False


# ── SR-07: Multi-module Maven detect_package_root ────────────────────


class TestJavaDetectPackageRoot:
    """Verify detect_package_root() handles multi-module Maven repos."""

    def _make_module(self, base: Path, rel: str, artifact_id: str = "") -> None:
        java_src = base / rel / "src" / "main" / "java"
        java_src.mkdir(parents=True, exist_ok=True)
        if artifact_id:
            pom = base / rel / "pom.xml"
            pom.write_text(
                f"<project><artifactId>{artifact_id}</artifactId></project>",
                encoding="utf-8",
            )

    def test_single_module_returns_that_path(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        self._make_module(tmp_path, "")
        product = SimpleNamespace(canonical_import="com.example")
        ext = JavaExtractor()
        result = ext.detect_package_root(tmp_path, product)
        assert result == "src/main/java"

    def test_multi_module_selects_matching_artifact(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        self._make_module(tmp_path, "core", artifact_id="aspose-slides-core")
        self._make_module(tmp_path, "test-utils", artifact_id="aspose-test-utils")
        product = SimpleNamespace(canonical_import="com.aspose.slides")
        ext = JavaExtractor()
        result = ext.detect_package_root(tmp_path, product)
        # Should prefer core (matches "slides" in canonical_import vs test-utils)
        assert "core" in result

    def test_multi_module_no_match_returns_shortest(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        self._make_module(tmp_path, "moduleA")
        self._make_module(tmp_path, "deeply/nested/moduleB")
        product = SimpleNamespace(canonical_import="com.example.unrelated")
        ext = JavaExtractor()
        result = ext.detect_package_root(tmp_path, product)
        # Shorter path (fewer parts) wins
        assert "moduleA" in result

    def test_no_java_source_returns_empty(self, tmp_path):
        from launcher.workers.understand.adapters._java import JavaExtractor

        product = SimpleNamespace(canonical_import="com.example")
        ext = JavaExtractor()
        result = ext.detect_package_root(tmp_path, product)
        assert result == ""


# ── TC-UND-209: Realistic multi-module Maven fixture ─────────────────


class TestJavaMultiModuleRealistic:
    """Exercise detect_package_root() on a realistic multi-module Maven structure.

    This mirrors a real Aspose-style Java repo:
    - Root pom.xml (parent POM with <modules> listing)
    - 3 submodules each with their own pom.xml + src/main/java/
    - .java files inside each module
    """

    def _build_realistic_repo(self, tmp_path: Path) -> Path:
        """Build a realistic Maven multi-module repo structure."""
        # Root pom.xml (parent POM)
        (tmp_path / "pom.xml").write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0">
                <modelVersion>4.0.0</modelVersion>
                <groupId>com.aspose</groupId>
                <artifactId>aspose-threed-parent</artifactId>
                <version>24.1.0</version>
                <packaging>pom</packaging>
                <modules>
                    <module>core</module>
                    <module>examples</module>
                    <module>test-utils</module>
                </modules>
            </project>
        """), encoding="utf-8")

        # core module — main library, artifactId matches canonical_import
        core = tmp_path / "core"
        core.mkdir()
        (core / "pom.xml").write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0">
                <parent>
                    <artifactId>aspose-threed-parent</artifactId>
                    <groupId>com.aspose</groupId>
                    <version>24.1.0</version>
                </parent>
                <artifactId>aspose-threed</artifactId>
                <name>Aspose.3D FOSS for Java - Core</name>
            </project>
        """), encoding="utf-8")
        core_java = core / "src" / "main" / "java" / "com" / "aspose" / "threed"
        core_java.mkdir(parents=True)
        (core_java / "Scene.java").write_text(
            "package com.aspose.threed;\n\npublic class Scene {}\n", encoding="utf-8"
        )

        # examples module — demo code, different artifactId
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "pom.xml").write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0">
                <parent>
                    <artifactId>aspose-threed-parent</artifactId>
                    <groupId>com.aspose</groupId>
                    <version>24.1.0</version>
                </parent>
                <artifactId>aspose-threed-examples</artifactId>
                <name>Aspose.3D Examples</name>
            </project>
        """), encoding="utf-8")
        ex_java = examples / "src" / "main" / "java" / "com" / "aspose" / "examples"
        ex_java.mkdir(parents=True)
        (ex_java / "Demo.java").write_text(
            "package com.aspose.examples;\n\npublic class Demo {}\n", encoding="utf-8"
        )

        # test-utils module — test helpers, unrelated artifactId
        testutils = tmp_path / "test-utils"
        testutils.mkdir()
        (testutils / "pom.xml").write_text(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0">
                <parent>
                    <artifactId>aspose-threed-parent</artifactId>
                    <groupId>com.aspose</groupId>
                    <version>24.1.0</version>
                </parent>
                <artifactId>aspose-test-helpers</artifactId>
                <name>Test Helpers</name>
            </project>
        """), encoding="utf-8")
        tu_java = testutils / "src" / "main" / "java" / "com" / "aspose" / "testutil"
        tu_java.mkdir(parents=True)
        (tu_java / "TestHelper.java").write_text(
            "package com.aspose.testutil;\n\npublic class TestHelper {}\n", encoding="utf-8"
        )

        return tmp_path

    def test_selects_core_by_artifact_match(self, tmp_path):
        """canonical_import='com.aspose.threed' should select core/ module."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        repo = self._build_realistic_repo(tmp_path)
        product = SimpleNamespace(canonical_import="com.aspose.threed")
        ext = JavaExtractor()
        result = ext.detect_package_root(repo, product)
        assert result.startswith("core/"), f"Expected core/ path, got: {result}"

    def test_empty_canonical_selects_shortest_path(self, tmp_path):
        """No canonical_import should select shortest path (closest to root)."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        repo = self._build_realistic_repo(tmp_path)
        product = SimpleNamespace(canonical_import="")
        ext = JavaExtractor()
        result = ext.detect_package_root(repo, product)
        # core/ and examples/ and test-utils/ all at same depth;
        # alphabetical tiebreaker should give core/ first
        assert result, "Should return a non-empty path"

    def test_unrelated_canonical_uses_path_tiebreaker(self, tmp_path):
        """Unrelated canonical_import falls back to path-length tiebreaker."""
        from launcher.workers.understand.adapters._java import JavaExtractor

        repo = self._build_realistic_repo(tmp_path)
        product = SimpleNamespace(canonical_import="org.completely.unrelated")
        ext = JavaExtractor()
        result = ext.detect_package_root(repo, product)
        # No artifact matches → shortest path wins
        # All three are same depth, so alphabetical tiebreaker applies
        assert result, "Should return a non-empty path"
        assert "src/main/java" in result

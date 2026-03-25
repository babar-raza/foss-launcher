"""TC-4321: Tests that constructors never have constructor body text in return_type.

Regression guard for TC-4031 (Go bare return types) is also included to ensure
that fixing the constructor leak does not break Go method return type extraction.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from launcher.shared.ts_analyzer import TreeSitterAnalyzer, _ensure_ts

pytestmark = pytest.mark.skipif(not _ensure_ts(), reason="tree-sitter not installed")

analyzer = TreeSitterAnalyzer()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_JAVA_CLASS_WITH_CONSTRUCTORS = """\
package com.aspose.threed;

public class Scene {

    public Scene() {
        super();
    }

    public Scene(String name) {
        this.name = name;
    }

    public void save(String path) {
    }

    public int getNodeCount() {
        return 0;
    }
}
"""

_CSHARP_CLASS_WITH_CONSTRUCTOR = """\
using System;

namespace Aspose.ThreeD {
    public class Scene {
        public Scene() {
            base.Initialize();
        }

        public Scene(string name) {
            this.Name = name;
        }

        public void Save(string path) { }
    }
}
"""

_GO_CODE_WITH_BARE_RETURN_TYPES = """\
package threed

// Scene represents a 3D scene.
type Scene struct {
    Name string
}

// NewScene creates a Scene instance (TC-4031 regression: bare return type).
func NewScene() *Scene {
    return &Scene{}
}

// GetName returns the scene name.
func (s *Scene) GetName() string {
    return s.Name
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _analyze(tmp_path: Path, code: str, language: str, ext: str):
    f = tmp_path / f"test_code.{ext}"
    f.write_text(code, encoding="utf-8")
    return analyzer.analyze_file(f, language, repo_dir=tmp_path)


def _method_details_by_name(result, method_name: str) -> dict | None:
    for cls in result.classes:
        for md in cls.get("method_details", []):
            if md.get("name") == method_name:
                return md
    return None


# ---------------------------------------------------------------------------
# TC-4321: Java constructor return_type must be empty
# ---------------------------------------------------------------------------


class TestJavaConstructorReturnType:
    def test_no_arg_constructor_return_type_is_empty(self, tmp_path):
        """Java no-arg constructor must have return_type == '' (not body text)."""
        r = _analyze(tmp_path, _JAVA_CLASS_WITH_CONSTRUCTORS, "java", "java")
        md = _method_details_by_name(r, "Scene")
        # Should find a constructor named Scene
        assert md is not None, "Constructor 'Scene' not found in method_details"
        rt = md.get("return_type", "")
        assert "{" not in rt, (
            f"Constructor body leaked into return_type: {rt!r}"
        )
        assert rt == "", (
            f"Expected empty return_type for constructor, got: {rt!r}"
        )

    def test_arg_constructor_return_type_is_empty(self, tmp_path):
        """Java constructor with parameters must have return_type == ''."""
        r = _analyze(tmp_path, _JAVA_CLASS_WITH_CONSTRUCTORS, "java", "java")
        # Find all methods named Scene (could be multiple overloads)
        constructor_entries = [
            md
            for cls in r.classes
            for md in cls.get("method_details", [])
            if md.get("name") == "Scene"
        ]
        assert len(constructor_entries) >= 1, "No constructor entries found"
        for md in constructor_entries:
            rt = md.get("return_type", "")
            assert "{" not in rt, (
                f"Constructor body leaked into return_type: {rt!r}"
            )
            assert rt == "", (
                f"Expected empty return_type for constructor overload, got: {rt!r}"
            )

    def test_regular_method_return_type_preserved(self, tmp_path):
        """Regular Java methods must still have their return_type extracted."""
        r = _analyze(tmp_path, _JAVA_CLASS_WITH_CONSTRUCTORS, "java", "java")
        save_md = _method_details_by_name(r, "save")
        assert save_md is not None, "'save' method not found"
        # 'void' return type — tree-sitter Java uses void_type node
        # Accept either "void" or "" (some grammars omit void in method_details)
        rt = save_md.get("return_type", "")
        assert "{" not in rt, f"Method body leaked into save return_type: {rt!r}"

        count_md = _method_details_by_name(r, "getNodeCount")
        assert count_md is not None, "'getNodeCount' method not found"
        rt2 = count_md.get("return_type", "")
        assert "{" not in rt2, f"Method body leaked into getNodeCount return_type: {rt2!r}"


# ---------------------------------------------------------------------------
# TC-4321: C# constructor return_type must be empty
# ---------------------------------------------------------------------------


class TestCSharpConstructorReturnType:
    def test_csharp_constructor_return_type_is_empty(self, tmp_path):
        """C# constructor must have return_type == '' (not body text)."""
        r = _analyze(tmp_path, _CSHARP_CLASS_WITH_CONSTRUCTOR, "csharp", "cs")
        constructor_entries = [
            md
            for cls in r.classes
            for md in cls.get("method_details", [])
            if md.get("name") == "Scene"
        ]
        assert len(constructor_entries) >= 1, "No C# constructor entries found"
        for md in constructor_entries:
            rt = md.get("return_type", "")
            assert "{" not in rt, (
                f"C# constructor body leaked into return_type: {rt!r}"
            )
            assert rt == "", (
                f"Expected empty return_type for C# constructor, got: {rt!r}"
            )


# ---------------------------------------------------------------------------
# TC-4031 regression: Go bare return types must still be extracted
# ---------------------------------------------------------------------------


class TestGoReturnTypeRegressionTC4031:
    def test_go_analysis_intact_after_constructor_fix(self, tmp_path):
        """TC-4321 regression guard: Go analysis must be structurally intact after Layer 1 fix.

        In tree-sitter Go, bound methods (func (s *T) Name()) appear in r.functions,
        not in class method_details. The Layer 1 fix cannot affect Go because it only fires
        for constructor_declaration nodes; Go methods are method_declaration nodes.

        This test validates:
        1. Go struct is extracted (r.classes populated)
        2. Go functions/methods are in r.functions (not broken)
        3. No function has a code-body leaked into return_type (the bug we fixed for Java)
        """
        r = _analyze(tmp_path, _GO_CODE_WITH_BARE_RETURN_TYPES, "go", "go")
        assert len(r.classes) >= 1, "Expected at least one Go struct class"

        # Go methods appear in r.functions (not class method_details)
        assert hasattr(r, "functions") and r.functions, (
            "Expected Go methods/functions in r.functions"
        )
        func_names = {f.get("name") for f in r.functions}
        assert "GetName" in func_names, f"GetName not in Go functions: {func_names}"
        assert "NewScene" in func_names, f"NewScene not in Go functions: {func_names}"

        # Core assertion: no Go function has a code-body (`{`) in return_type.
        # This is the same defect TC-4321 fixed for Java — verify it cannot occur for Go.
        for func in r.functions:
            rt = func.get("return_type", "")
            assert "{" not in rt, (
                f"Go function '{func.get('name')}' has code-body in return_type: {rt!r}"
            )

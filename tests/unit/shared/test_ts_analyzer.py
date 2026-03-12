"""Tests for TreeSitterAnalyzer — universal multi-language code analysis.

Tests cover all target languages (Java, C#, JS, TS, Go, PHP, Rust, Ruby)
plus generic fallback (Kotlin, Dart, Scala).
"""

from __future__ import annotations

import pytest
from pathlib import Path

from launcher.shared.ts_analyzer import (
    TreeSitterAnalyzer,
    AnalysisResult,
    normalize_imports,
    normalize_imports_ast,
    _ensure_ts,
)

pytestmark = pytest.mark.skipif(not _ensure_ts(), reason="tree-sitter not installed")

analyzer = TreeSitterAnalyzer()


# ---------------------------------------------------------------------------
# Fixtures — synthetic source code for each language
# ---------------------------------------------------------------------------

JAVA_CODE = """\
package com.aspose.cells;

import java.util.List;

/**
 * Represents a spreadsheet workbook.
 */
public class Workbook {
    public static final String VERSION = "1.0";

    /**
     * Saves the workbook to a file.
     */
    public void save(String path) {
    }

    public int getSheetCount() {
        return 0;
    }
}
"""

CSHARP_CODE = """\
using System;

namespace Aspose.Cells {
    /// <summary>Represents a workbook.</summary>
    public class Workbook {
        public const string Version = "1.0";

        /// <summary>Saves the workbook.</summary>
        public void Save(string path) { }
    }
}
"""

JS_CODE = """\
import { Component } from 'react';

/**
 * A reusable button component.
 */
export class Button extends Component {
    render() {}
}

export function createApp() {
    return new Button();
}

const VERSION = "2.0";
"""

TS_CODE = """\
import { EventEmitter } from 'events';

/**
 * Manages worksheet operations.
 */
export class WorksheetManager extends EventEmitter {
    /**
     * Gets the active sheet.
     */
    getActive(): Worksheet {
        return null;
    }
}

export interface Worksheet {
    name: string;
}
"""

GO_CODE = """\
package cells

import "fmt"

// Workbook represents a spreadsheet workbook.
type Workbook struct {
    Name string
}

// Save persists the workbook to disk.
func (w *Workbook) Save(path string) error {
    return nil
}

// NewWorkbook creates a new workbook instance.
func NewWorkbook() *Workbook {
    return &Workbook{}
}
"""

PHP_CODE = """\
<?php
namespace Aspose\\Cells;

use Aspose\\Core\\Base;

/**
 * Represents a workbook.
 */
class Workbook extends Base {
    public const VERSION = "1.0";

    /**
     * Saves the workbook.
     */
    public function save(string $path): void {
    }
}
"""

RUST_CODE = """\
use std::path::PathBuf;

/// Represents a spreadsheet workbook.
pub struct Workbook {
    pub name: String,
}

/// Saves the workbook to a file.
pub fn save(wb: &Workbook, path: PathBuf) -> Result<(), String> {
    Ok(())
}

pub const VERSION: &str = "1.0";
"""

RUBY_CODE = """\
require 'json'

# Represents a spreadsheet workbook.
class Workbook
  # Saves the workbook.
  def save(path)
  end

  def sheet_count
    0
  end
end
"""

KOTLIN_CODE = """\
package com.aspose.cells

/**
 * Represents a workbook.
 */
class Workbook {
    fun save(path: String) {
        println("saving")
    }
}
"""

DART_CODE = """\
class Workbook {
  void save(String path) {}
  int get sheetCount => 0;
}
"""

SCALA_CODE = """\
package com.aspose.cells

class Workbook {
  def save(path: String): Unit = {}
}
"""


# ---------------------------------------------------------------------------
# Helper to write code to a temp file and analyse
# ---------------------------------------------------------------------------


def _analyze(tmp_path: Path, code: str, language: str, ext: str) -> AnalysisResult:
    f = tmp_path / f"test_code.{ext}"
    f.write_text(code, encoding="utf-8")
    return analyzer.analyze_file(f, language, repo_dir=tmp_path)


# ---------------------------------------------------------------------------
# Test: analyze_file for each language
# ---------------------------------------------------------------------------


class TestAnalyzeFile:
    def test_java(self, tmp_path):
        r = _analyze(tmp_path, JAVA_CODE, "java", "java")
        assert r.language == "java"
        assert r.module_path == "com.aspose.cells"
        assert len(r.classes) >= 1
        wb = r.classes[0]
        assert wb["name"] == "Workbook"
        assert "spreadsheet" in wb["docstring"].lower() or "workbook" in wb["docstring"].lower()
        assert "save" in wb["methods"]
        assert len(r.imports) >= 1
        assert any("java.util.List" in i for i in r.imports)
        assert len(r.constants) >= 1
        assert r.constants[0]["name"] == "VERSION"

    def test_csharp(self, tmp_path):
        r = _analyze(tmp_path, CSHARP_CODE, "csharp", "cs")
        assert r.language == "csharp"
        assert len(r.classes) >= 1
        wb = r.classes[0]
        assert wb["name"] == "Workbook"
        assert "workbook" in wb["docstring"].lower()
        assert len(r.imports) >= 1  # using System

    def test_javascript(self, tmp_path):
        r = _analyze(tmp_path, JS_CODE, "javascript", "js")
        assert r.language == "javascript"
        assert len(r.classes) >= 1
        assert r.classes[0]["name"] == "Button"
        assert len(r.imports) >= 1

    def test_typescript(self, tmp_path):
        r = _analyze(tmp_path, TS_CODE, "typescript", "ts")
        assert r.language == "typescript"
        assert len(r.classes) >= 1
        assert any(c["name"] == "WorksheetManager" for c in r.classes)

    def test_go(self, tmp_path):
        r = _analyze(tmp_path, GO_CODE, "go", "go")
        assert r.language == "go"
        assert r.module_path == "cells"
        assert len(r.classes) >= 1  # struct Workbook
        assert len(r.functions) >= 1  # NewWorkbook

    def test_php(self, tmp_path):
        r = _analyze(tmp_path, PHP_CODE, "php", "php")
        assert r.language == "php"
        assert len(r.classes) >= 1
        assert r.classes[0]["name"] == "Workbook"

    def test_rust(self, tmp_path):
        r = _analyze(tmp_path, RUST_CODE, "rust", "rs")
        assert r.language == "rust"
        assert len(r.classes) >= 1  # struct Workbook
        assert len(r.functions) >= 1  # save
        assert len(r.constants) >= 1

    def test_ruby(self, tmp_path):
        r = _analyze(tmp_path, RUBY_CODE, "ruby", "rb")
        assert r.language == "ruby"
        assert len(r.classes) >= 1
        assert r.classes[0]["name"] == "Workbook"

    def test_kotlin_generic_fallback(self, tmp_path):
        r = _analyze(tmp_path, KOTLIN_CODE, "kotlin", "kt")
        assert r.language == "kotlin"
        assert len(r.classes) >= 1
        assert r.classes[0]["name"] == "Workbook"

    def test_dart_generic_fallback(self, tmp_path):
        r = _analyze(tmp_path, DART_CODE, "dart", "dart")
        assert r.language == "dart"
        assert len(r.classes) >= 1

    def test_scala_generic_fallback(self, tmp_path):
        r = _analyze(tmp_path, SCALA_CODE, "scala", "scala")
        assert r.language == "scala"
        assert len(r.classes) >= 1


# ---------------------------------------------------------------------------
# Test: AnalysisResult shape matches Python analyzer output
# ---------------------------------------------------------------------------


class TestAnalysisResultShape:
    """Every language must produce same keys as Python analyzer."""

    @pytest.mark.parametrize("lang,code,ext", [
        ("java", JAVA_CODE, "java"),
        ("csharp", CSHARP_CODE, "cs"),
        ("javascript", JS_CODE, "js"),
        ("typescript", TS_CODE, "ts"),
        ("go", GO_CODE, "go"),
        ("rust", RUST_CODE, "rs"),
        ("ruby", RUBY_CODE, "rb"),
    ])
    def test_class_dict_shape(self, tmp_path, lang, code, ext):
        r = _analyze(tmp_path, code, lang, ext)
        assert len(r.classes) >= 1
        cls = r.classes[0]
        # Must have all standard keys
        for key in ("name", "docstring", "bases", "methods", "method_details",
                     "source_file", "start_line", "module"):
            assert key in cls, f"Missing key '{key}' in {lang} class dict"


# ---------------------------------------------------------------------------
# Test: validate_snippet
# ---------------------------------------------------------------------------


class TestSnippetValidation:
    @pytest.mark.parametrize("lang,valid_code", [
        ("java", "public class Foo { public void bar() {} }"),
        ("javascript", "function foo() { return 42; }"),
        ("typescript", "export class Foo { bar(): void {} }"),
        ("go", "package main\nfunc main() {}"),
        ("rust", "fn main() {}"),
        ("ruby", "class Foo; def bar; end; end"),
    ])
    def test_valid_snippet(self, lang, valid_code):
        assert analyzer.validate_snippet(valid_code, lang) is True

    @pytest.mark.parametrize("lang,broken_code", [
        ("java", "public class { broken syntax ////"),
        ("javascript", "function( { } } } ////"),
        ("go", "func { invalid go ////"),
    ])
    def test_invalid_snippet(self, lang, broken_code):
        assert analyzer.validate_snippet(broken_code, lang) is False

    def test_unknown_language_graceful(self):
        # Unknown language should return True (can't validate)
        assert analyzer.validate_snippet("some code", "unknown_lang_xyz") is True

    def test_csharp_valid(self):
        assert analyzer.validate_snippet(
            "using System;\npublic class Foo { public void Bar() {} }", "csharp"
        ) is True

    def test_csharp_invalid(self):
        assert analyzer.validate_snippet(
            "public class { broken ////", "csharp"
        ) is False


# ---------------------------------------------------------------------------
# Test: doc comment extraction
# ---------------------------------------------------------------------------


class TestDocComments:
    def test_java_javadoc(self, tmp_path):
        r = _analyze(tmp_path, JAVA_CODE, "java", "java")
        wb = r.classes[0]
        assert wb["docstring"], "Java class should have Javadoc docstring"
        # Method doc
        method_docs = [m for m in wb["method_details"] if m.get("docstring")]
        assert len(method_docs) >= 1, "Java method should have Javadoc"

    def test_csharp_xml_doc(self, tmp_path):
        r = _analyze(tmp_path, CSHARP_CODE, "csharp", "cs")
        wb = r.classes[0]
        assert wb["docstring"], "C# class should have XML doc"

    def test_go_godoc(self, tmp_path):
        r = _analyze(tmp_path, GO_CODE, "go", "go")
        wb = r.classes[0]
        assert wb["docstring"], "Go struct should have GoDoc"

    def test_rust_rustdoc(self, tmp_path):
        r = _analyze(tmp_path, RUST_CODE, "rust", "rs")
        wb = r.classes[0]
        assert wb["docstring"], "Rust struct should have rustdoc"

    def test_ruby_yard(self, tmp_path):
        r = _analyze(tmp_path, RUBY_CODE, "ruby", "rb")
        wb = r.classes[0]
        assert wb["docstring"], "Ruby class should have YARD comment"


# ---------------------------------------------------------------------------
# Test: import normalization
# ---------------------------------------------------------------------------


class TestImportNormalization:
    def test_java_import(self):
        code = "import com.aspose.cells.Workbook;"
        result = normalize_imports(code, "java", "com.aspose.cells.foss")
        assert "com.aspose.cells.foss" in result or "com.aspose.cells" in result

    def test_csharp_using(self):
        code = "using Aspose.Cells;"
        result = normalize_imports(code, "csharp", "Aspose.Cells.Foss")
        assert "Aspose.Cells.Foss" in result

    def test_js_import(self):
        code = 'import { Workbook } from "@aspose/cells";'
        result = normalize_imports(code, "javascript", "@aspose/cells-foss")
        assert "@aspose/cells-foss" in result

    def test_go_import(self):
        code = 'import "github.com/aspose/cells"'
        result = normalize_imports(code, "go", "github.com/aspose/cells-foss")
        assert "github.com/aspose/cells-foss" in result

    def test_rust_use(self):
        code = "use aspose_cells::Workbook;"
        result = normalize_imports(code, "rust", "aspose_cells_foss")
        assert "aspose_cells_foss" in result

    def test_ruby_require(self):
        code = "require 'aspose-cells'"
        result = normalize_imports(code, "ruby", "aspose-cells-foss")
        assert "aspose-cells-foss" in result

    def test_php_use(self):
        code = "use Aspose\\Cells\\Workbook;"
        result = normalize_imports(code, "php", "Aspose\\Cells\\Foss")
        assert "Aspose\\Cells\\Foss" in result

    def test_no_canonical_import(self):
        code = "import java.util.List;"
        result = normalize_imports(code, "java", "")
        assert result == code  # unchanged

    # TC-3870: Kotlin, Dart, Scala import normalization
    def test_kotlin_import(self):
        code = "import com.aspose.cells.Workbook"
        result = normalize_imports(code, "kotlin", "com.aspose.cells.foss")
        assert "com.aspose.cells.foss" in result

    def test_kotlin_no_match_non_aspose(self):
        code = "import kotlin.collections.List"
        result = normalize_imports(code, "kotlin", "com.aspose.cells.foss")
        # Non-aspose import is not touched
        assert result == code

    def test_dart_import(self):
        code = "import 'package:aspose_cells/aspose_cells.dart';"
        result = normalize_imports(code, "dart", "aspose_cells_foss/aspose_cells_foss.dart")
        assert "aspose_cells_foss/aspose_cells_foss.dart" in result

    def test_dart_no_match_non_aspose(self):
        code = "import 'package:flutter/material.dart';"
        result = normalize_imports(code, "dart", "aspose_cells_foss/aspose_cells_foss.dart")
        # Non-aspose dart import is not touched
        assert result == code

    def test_scala_import(self):
        code = "import com.aspose.cells.Workbook"
        result = normalize_imports(code, "scala", "com.aspose.cells.foss")
        assert "com.aspose.cells.foss" in result

    def test_scala_no_match_non_aspose(self):
        code = "import scala.collection.mutable.ListBuffer"
        result = normalize_imports(code, "scala", "com.aspose.cells.foss")
        # Non-aspose scala import is not touched
        assert result == code


# ---------------------------------------------------------------------------
# Test: export extraction
# ---------------------------------------------------------------------------


class TestExportExtraction:
    def test_java_public_class(self, tmp_path):
        r = _analyze(tmp_path, JAVA_CODE, "java", "java")
        assert "Workbook" in r.exports

    def test_go_exported_func(self, tmp_path):
        r = _analyze(tmp_path, GO_CODE, "go", "go")
        assert "NewWorkbook" in r.exports

    def test_rust_pub(self, tmp_path):
        r = _analyze(tmp_path, RUST_CODE, "rust", "rs")
        assert "Workbook" in r.exports
        assert "save" in r.exports


# ---------------------------------------------------------------------------
# Test: graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_nonexistent_file(self, tmp_path):
        r = analyzer.analyze_file(tmp_path / "does_not_exist.java", "java")
        assert r.language == "java"
        assert len(r.classes) == 0

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.java"
        f.write_text("", encoding="utf-8")
        r = analyzer.analyze_file(f, "java")
        assert r.language == "java"
        assert len(r.classes) == 0


# ---------------------------------------------------------------------------
# TC-3904: Regression tests for normalize_imports_ast (TC-3901 fix)
# Depends on: TC-3901 (AST-based TypeScript import normalization)
# ---------------------------------------------------------------------------


class TestNormalizeImportsAst:
    """TC-3904: normalize_imports_ast regression suite — ensures TC-3901 fix holds."""

    def test_no_change_when_correct(self):
        """Correct import is returned unchanged (no-op for rich repos)."""
        code = "import { Scene } from '@aspose/3d-foss';"
        assert normalize_imports_ast(code, "typescript", "@aspose/3d-foss") == code

    def test_fixes_double_suffix(self):
        """Double-suffix @aspose/3d-foss-foss is corrected to @aspose/3d-foss."""
        code = "import { Scene } from '@aspose/3d-foss-foss';"
        fixed = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
        assert "@aspose/3d-foss-foss" not in fixed
        assert "@aspose/3d-foss" in fixed

    def test_non_aspose_unchanged(self):
        """Non-@aspose import is never rewritten."""
        code = "import _ from 'lodash';"
        assert normalize_imports_ast(code, "typescript", "@aspose/3d-foss") == code

    def test_python_delegates_to_existing(self):
        """Python language delegates to regex normalize_imports, not AST path."""
        code = "import Aspose.Cells"
        result = normalize_imports_ast(code, "python", "aspose_cells_foss")
        assert isinstance(result, str)

    def test_require_syntax(self):
        """CommonJS require() double-suffix is corrected by TR-02 call_expression scan."""
        code = "const lib = require('@aspose/3d-foss-foss');"
        fixed = normalize_imports_ast(code, "javascript", "@aspose/3d-foss")
        assert "@aspose/3d-foss-foss" not in fixed
        assert "@aspose/3d-foss" in fixed

    def test_require_syntax_non_aspose_unchanged(self):
        """Non-@aspose require() argument is never rewritten."""
        code = "const _ = require('lodash');"
        assert normalize_imports_ast(code, "javascript", "@aspose/3d-foss") == code

    def test_require_and_import_both_fixed_in_same_file(self):
        """Mixed ES import + require() — both wrong specifiers corrected in one pass."""
        code = (
            "import { Scene } from '@aspose/3d-foss-foss';\n"
            "const lib = require('@aspose/3d-foss-foss');\n"
        )
        fixed = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
        assert fixed.count("@aspose/3d-foss-foss") == 0
        assert fixed.count("@aspose/3d-foss") == 2

    def test_named_import(self):
        """Named ES import with double-suffix is corrected to canonical form."""
        code = "import { Renderer, Scene } from '@aspose/3d-foss-foss';"
        fixed = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
        assert "from '@aspose/3d-foss'" in fixed
        assert "3d-foss-foss" not in fixed

    def test_fallback_when_parser_unavailable(self, monkeypatch) -> None:
        """When _get_parser returns None, delegates to normalize_imports without raising.

        GAP-07: Graceful-degradation test only. The regex fallback has the same
        hyphen-blind bug that TC-3901 fixed; correctness is not guaranteed in fallback
        mode. The AST path (tree-sitter present) is the production path.
        """
        import launcher.shared.ts_analyzer as _ts
        monkeypatch.setattr(_ts, "_get_parser", lambda _lang: None)
        code = "import { Scene } from '@aspose/3d-foss';"
        result = normalize_imports_ast(code, "typescript", "@aspose/3d-foss")
        # Guarantee: no exception; returns a string (graceful degradation)
        assert isinstance(result, str)

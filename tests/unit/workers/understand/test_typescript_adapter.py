"""Tests for TC-4214: TypeScript adapter Phase 3 — typed methods, properties, enums.

Verifies that TypeScriptExtractor.extract_class_details() populates
method_details, property_details, and enum_members via ts_analyzer.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.models.product import ProductIdentity


def _make_product(**overrides) -> ProductIdentity:
    defaults = dict(
        family="cells",
        platform="typescript",
        display_name="Aspose.Cells JS",
        canonical_import="@aspose/cells",
        repo_url="https://example.com",
    )
    defaults.update(overrides)
    return ProductIdentity(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TS_CLASS_SOURCE = """\
export enum FileFormat {
    XLSX = 0,
    CSV = 1,
    PDF = 2,
}

export class Workbook {
    /** The file format of this workbook. */
    fileFormat: FileFormat;

    /** Whether formulas are calculated automatically. */
    readonly calculationMode: string;

    /** Load a workbook from the given path. */
    load(filePath: string): boolean {
        return true;
    }

    /** Save the workbook to the given path. */
    save(filePath: string, format: FileFormat): void {
        // no-op
    }

    static fromBuffer(buffer: Uint8Array): Workbook {
        return new Workbook();
    }
}
"""


class TestTypeScriptAdapterTypedMethods:
    """TC-4214: TypeScript adapter Phase 3 — typed methods + enum extraction."""

    def test_extract_class_details_returns_method_details(self, tmp_path: Path):
        """extract_class_details returns method_details for a TypeScript class."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        ts_file = tmp_path / "workbook.ts"
        ts_file.write_text(_TS_CLASS_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        # Should get at least one class
        assert isinstance(classes, list), "extract_class_details must return a list"
        assert len(classes) >= 1, "At least one class (Workbook) must be extracted"

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None, "Workbook class must be found"

        # method_details is the key field that enables typed method population
        method_details = workbook.get("method_details", [])
        assert len(method_details) > 0, "method_details must be non-empty for Workbook"

        method_names = [m["name"] for m in method_details]
        assert "load" in method_names, "'load' method must appear in method_details"
        assert "save" in method_names, "'save' method must appear in method_details"

    def test_load_method_has_typed_parameter(self, tmp_path: Path):
        """load() method must have a typed 'filePath: string' parameter."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        ts_file = tmp_path / "workbook.ts"
        ts_file.write_text(_TS_CLASS_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None

        method_details = workbook.get("method_details", [])
        load_method = next((m for m in method_details if m["name"] == "load"), None)
        assert load_method is not None, "'load' must appear in method_details"

        params = load_method.get("parameters", [])
        assert len(params) >= 1, "load() must have at least one parameter"
        param_names = [p["name"] for p in params]
        assert "filePath" in param_names, "filePath parameter must be captured"

    def test_enum_members_captured(self, tmp_path: Path):
        """Enum FileFormat must have its members extracted."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        ts_file = tmp_path / "workbook.ts"
        ts_file.write_text(_TS_CLASS_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        enum_class = next((c for c in classes if c["name"] == "FileFormat"), None)
        assert enum_class is not None, "FileFormat enum must be extracted as a class"
        assert enum_class.get("is_enum", False) is True, "is_enum must be True for FileFormat"

        members = enum_class.get("enum_members", [])
        assert len(members) >= 2, "FileFormat must have at least 2 enum members"
        member_names = [m["name"] for m in members]
        assert "XLSX" in member_names, "XLSX enum member must be present"
        assert "CSV" in member_names, "CSV enum member must be present"

    def test_property_details_captured(self, tmp_path: Path):
        """Typed properties of Workbook must be extracted."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        ts_file = tmp_path / "workbook.ts"
        ts_file.write_text(_TS_CLASS_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None

        # property_details should have at least one entry
        prop_details = workbook.get("property_details", [])
        assert len(prop_details) >= 1, "Workbook must have at least one property_detail entry"

    def test_static_method_extracted(self, tmp_path: Path):
        """Static method fromBuffer must be captured with is_static=True."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        ts_file = tmp_path / "workbook.ts"
        ts_file.write_text(_TS_CLASS_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        workbook = next((c for c in classes if c["name"] == "Workbook"), None)
        assert workbook is not None

        method_details = workbook.get("method_details", [])
        static_method = next((m for m in method_details if m["name"] == "fromBuffer"), None)
        assert static_method is not None, "fromBuffer static method must be extracted"
        assert static_method.get("is_static", False) is True, "fromBuffer must be marked is_static"

    def test_fallback_when_ts_analyzer_unavailable(self, tmp_path: Path):
        """When ts_analyzer raises, adapter falls back to code_analyzer."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        ts_file = tmp_path / "simple.ts"
        ts_file.write_text("export class Foo { bar(): void {} }", encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()

        # Patch ts_analyzer to raise ImportError
        with patch(
            "launcher.workers.understand.adapters._typescript.logger",
        ):
            with patch(
                "launcher.shared.ts_analyzer.analyzer.analyze_file",
                side_effect=RuntimeError("simulated ts_analyzer failure"),
            ):
                classes = extractor.extract_class_details(ts_file, tmp_path, product)
        # Should not raise; result may be empty or have classes from code_analyzer fallback
        assert isinstance(classes, list)

    def test_tsx_file_uses_typescript_language(self, tmp_path: Path):
        """TSX files should use language='typescript' (not 'jsx')."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        tsx_file = tmp_path / "component.tsx"
        tsx_file.write_text(
            "export class MyComponent { render(): string { return ''; } }",
            encoding="utf-8",
        )

        extractor = TypeScriptExtractor()
        product = _make_product()

        captured_langs: list[str] = []

        from launcher.shared.ts_analyzer import analyzer as _orig_analyzer
        orig_analyze = _orig_analyzer.analyze_file

        def _mock_analyze(path, language, **kw):
            captured_langs.append(language)
            return orig_analyze(path, language, **kw)

        with patch(
            "launcher.shared.ts_analyzer.analyzer.analyze_file",
            side_effect=_mock_analyze,
        ):
            classes = extractor.extract_class_details(tsx_file, tmp_path, product)

        assert "typescript" in captured_langs, "TSX must dispatch with language='typescript'"


# ---------------------------------------------------------------------------
# TC-4243: .d.ts declaration file support
# ---------------------------------------------------------------------------

_DTS_INTERFACE_SOURCE = """\
export interface IWorkbook {
    load(path: string): boolean;
    save(path: string, format: number): void;
    readonly name: string;
}

export declare class Spreadsheet {
    open(path: string): IWorkbook;
}
"""

_DTS_CLASS_SOURCE = """\
export declare class Notebook {
    load(path: string): boolean;
    save(path: string): void;
}
"""

_TS_IMPL_SOURCE = """\
export class ImplOnly {
    internalMethod(): void {}
}
"""


class TestTypeScriptAdapterDtsSupport:
    """TC-4243: TypeScript adapter .d.ts declaration file support."""

    def test_dts_discovery_from_types_field(self, tmp_path: Path):
        """Adapter uses .d.ts file referenced in package.json 'types' field."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        # Set up repo: package.json with "types" pointing to index.d.ts
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "@test/pkg", "types": "index.d.ts"}),
            encoding="utf-8",
        )
        (tmp_path / "index.d.ts").write_text(_DTS_CLASS_SOURCE, encoding="utf-8")

        # Also put an impl .ts file — adapter should PREFER .d.ts
        ts_file = tmp_path / "impl.ts"
        ts_file.write_text(_TS_IMPL_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        assert isinstance(classes, list)
        names = [c["name"] for c in classes]
        # .d.ts class should appear
        assert "Notebook" in names, f"Notebook from .d.ts must be found; got {names}"

    def test_dts_discovery_fallback_to_index_dts(self, tmp_path: Path):
        """Adapter discovers index.d.ts at package root even without 'types' field."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        # package.json without "types" field
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "@test/pkg"}),
            encoding="utf-8",
        )
        # index.d.ts at package root
        (tmp_path / "index.d.ts").write_text(_DTS_CLASS_SOURCE, encoding="utf-8")

        ts_file = tmp_path / "impl.ts"
        ts_file.write_text(_TS_IMPL_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        assert isinstance(classes, list)
        names = [c["name"] for c in classes]
        assert "Notebook" in names, f"Notebook from index.d.ts must be found; got {names}"

    def test_dts_fallback_to_ts_when_no_dts(self, tmp_path: Path):
        """When no .d.ts exists, adapter uses the .ts file unchanged."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        # package.json without "types" field, no .d.ts files anywhere
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "@test/pkg"}),
            encoding="utf-8",
        )

        ts_file = tmp_path / "workbook.ts"
        ts_file.write_text(_TS_CLASS_SOURCE, encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        assert isinstance(classes, list)
        assert len(classes) >= 1, "At least one class from .ts must be found"
        names = [c["name"] for c in classes]
        assert "Workbook" in names, f"Workbook class must appear; got {names}"

    def test_interface_parsed_as_class(self, tmp_path: Path):
        """TypeScript interface in .d.ts is extracted as a class-equivalent entry."""
        from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

        (tmp_path / "package.json").write_text(
            json.dumps({"name": "@test/pkg", "types": "index.d.ts"}),
            encoding="utf-8",
        )
        (tmp_path / "index.d.ts").write_text(_DTS_INTERFACE_SOURCE, encoding="utf-8")

        ts_file = tmp_path / "impl.ts"
        ts_file.write_text("// empty\n", encoding="utf-8")

        extractor = TypeScriptExtractor()
        product = _make_product()
        classes = extractor.extract_class_details(ts_file, tmp_path, product)

        assert isinstance(classes, list)
        names = [c["name"] for c in classes]
        # IWorkbook (interface) and/or Spreadsheet (class) must appear
        assert "IWorkbook" in names or "Spreadsheet" in names, (
            f"At least one of IWorkbook/Spreadsheet must be extracted from .d.ts; got {names}"
        )

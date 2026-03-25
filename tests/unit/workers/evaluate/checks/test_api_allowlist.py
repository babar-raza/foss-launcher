"""Unit tests for check_api_allowlist (TC-QG-01)."""
from __future__ import annotations

from types import SimpleNamespace

from launcher.workers.evaluate.checks.api_allowlist import check_api_allowlist


def _page(body: str) -> str:
    return f"---\ntitle: Test Page\n---\n\n{body}\n"


def _make_surface(
    public_classes: list[str] | None = None,
    import_allowlist: list[str] | None = None,
    class_briefs: list | None = None,
    api_identifiers: list[str] | None = None,
    api_identifiers_native: list[str] | None = None,
    enums: list | None = None,
) -> SimpleNamespace:
    """Build a minimal ApiSurface-like object for testing."""
    return SimpleNamespace(
        public_classes=public_classes or [],
        import_allowlist=import_allowlist or [],
        class_briefs=class_briefs or [],
        api_identifiers=api_identifiers or [],
        api_identifiers_native=api_identifiers_native or [],
        enums=enums or [],
    )


def _make_brief(name: str, methods: list[str] | None = None, properties: list[str] | None = None):
    return SimpleNamespace(
        name=name,
        methods=methods or [],
        properties=properties or [],
        typed_methods=[],
        typed_properties=[],
    )


def test_known_class_passes():
    """`Workbook` in allowlist -> no finding."""
    surface = _make_surface(public_classes=["Workbook"])
    content = _page("## Overview\n\nUse the `Workbook` class to create spreadsheets.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert len(findings) == 0


def test_unknown_class_high():
    """`WorkbookManager` not in allowlist -> HIGH (REG-H-02: downgraded from CRITICAL)."""
    surface = _make_surface(public_classes=["Workbook"])
    content = _page("## Overview\n\nUse the `WorkbookManager` class.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].check == "api_allowlist"
    assert "WorkbookManager" in findings[0].message


def test_builtin_exempt():
    """`str`, `int`, `list` -> no finding."""
    surface = _make_surface(public_classes=["Workbook"])
    content = _page("## Types\n\nReturns a `str` value. Takes an `int` index and a `list`.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert len(findings) == 0


def test_stdlib_exempt():
    """`Path`, `json` -> no finding."""
    surface = _make_surface(public_classes=["Workbook"])
    content = _page("## Loading\n\nUse `Path` from `json` module.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert len(findings) == 0


def test_method_on_known_class():
    """`workbook.save()` where save is in class_briefs -> no finding."""
    brief = _make_brief("Workbook", methods=["save", "load"])
    surface = _make_surface(public_classes=["Workbook"], class_briefs=[brief])
    content = _page("## Saving\n\nCall `workbook.save` to save the file.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert len(findings) == 0


def test_code_block_excluded():
    """Identifier only in code block -> no finding (we check prose only)."""
    surface = _make_surface(public_classes=["Workbook"])
    content = _page(
        "## Overview\n\n"
        "Use the `Workbook` class.\n\n"
        "```python\n"
        "mgr = WorkbookManager()\n"
        "```\n"
    )
    findings = check_api_allowlist(content, surface, "test-slug")
    # WorkbookManager is only inside the code block, not in backticks in prose
    assert len(findings) == 0


def test_framework_class_exempt():
    """`DataFrame`, `Iterator` -> no finding (REG-H-02: common framework classes exempted)."""
    surface = _make_surface(public_classes=["Workbook"])
    content = _page("## Types\n\nReturns a `DataFrame` or an `Iterator` object.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert len(findings) == 0


def test_cpp_double_colon_separator():
    """`Aspose::Slides::Presentation` split on `::` — Presentation in surface -> no finding (TC-CPP-412)."""
    surface = _make_surface(
        public_classes=["Presentation"],
        import_allowlist=["Aspose.Slides"],
    )
    content = _page("## Overview\n\nUse the `Aspose::Slides::Presentation` class to open files.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    # All parts (Aspose, Slides, Presentation) are in the allowlist
    assert len(findings) == 0


def test_cpp_double_colon_unknown_class():
    """`Aspose::Slides::UnknownWidget` — UnknownWidget not in surface -> HIGH finding."""
    surface = _make_surface(
        public_classes=["Presentation"],
        import_allowlist=["Aspose.Slides"],
    )
    content = _page("## Overview\n\nUse the `Aspose::Slides::UnknownWidget` class.\n")
    findings = check_api_allowlist(content, surface, "test-slug")
    assert any(f.severity == "high" and "UnknownWidget" in f.message for f in findings)


def test_none_surface_returns_empty():
    """None api_surface -> graceful empty return."""
    content = _page("## Overview\n\nUse the `Workbook` class.\n")
    findings = check_api_allowlist(content, None, "test-slug")
    assert len(findings) == 0

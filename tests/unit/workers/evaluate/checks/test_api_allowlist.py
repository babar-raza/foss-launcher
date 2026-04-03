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


# ---------------------------------------------------------------------------
# TC-5315: Java stdlib allowlist
# ---------------------------------------------------------------------------

def _java_page(body: str) -> str:
    """Build a minimal Java-platform page for api_allowlist tests."""
    return (
        "---\n"
        "title: Java Guide\n"
        "platform: java\n"
        "---\n"
        + body
    )


def test_java_stdlib_list_not_flagged():
    """TC-5315: Java `List`, `ArrayList` in backticks must not trigger findings."""
    content = _java_page(
        "## Overview\n\nCreate a `List<String>` using `ArrayList`.\n"
    )
    surface = _make_surface(["Document"])
    findings = check_api_allowlist(content, surface, "test-java")
    stdlib_findings = [
        f for f in findings
        if "List" in f.message or "ArrayList" in f.message
    ]
    assert stdlib_findings == [], f"Java stdlib 'List'/'ArrayList' triggered findings: {stdlib_findings}"


def test_java_stdlib_map_not_flagged():
    """TC-5315: Java `Map`, `HashMap` in backticks must not trigger findings."""
    content = _java_page(
        "## Usage\n\nStore results in a `HashMap<String, Integer>` or `Map`.\n"
    )
    surface = _make_surface(["Document"])
    findings = check_api_allowlist(content, surface, "test-java")
    stdlib_findings = [
        f for f in findings
        if "HashMap" in f.message or "Map" in f.message
    ]
    assert stdlib_findings == [], f"Java stdlib 'HashMap'/'Map' triggered findings: {stdlib_findings}"


def test_java_stdlib_optional_stream_not_flagged():
    """TC-5315: Java `Optional`, `Stream` must not trigger findings."""
    content = _java_page(
        "## Overview\n\nReturns an `Optional<Document>` or use `Stream` to iterate.\n"
    )
    surface = _make_surface(["Document"])
    findings = check_api_allowlist(content, surface, "test-java")
    stdlib_findings = [
        f for f in findings
        if "Optional" in f.message or "Stream" in f.message
    ]
    assert stdlib_findings == [], f"Java stdlib 'Optional'/'Stream' triggered findings: {stdlib_findings}"


def test_java_stdlib_exception_not_flagged():
    """TC-5315: Java `IOException`, `RuntimeException` must not trigger findings."""
    content = _java_page(
        "## Error Handling\n\nCatch `IOException` or `RuntimeException`.\n"
    )
    surface = _make_surface(["Document"])
    findings = check_api_allowlist(content, surface, "test-java")
    stdlib_findings = [
        f for f in findings
        if "IOException" in f.message or "RuntimeException" in f.message
    ]
    assert stdlib_findings == [], f"Java stdlib exceptions triggered findings: {stdlib_findings}"


def test_java_unknown_identifier_still_flagged():
    """TC-5315: Unknown identifiers on Java pages are still flagged (not blanket-exempted)."""
    content = _java_page(
        "## Overview\n\nUse the `HallucinatedClass` to load files.\n"
    )
    surface = _make_surface(["Document"])
    findings = check_api_allowlist(content, surface, "test-java")
    unknown_findings = [f for f in findings if "HallucinatedClass" in f.message]
    assert unknown_findings, "Unknown class on Java page must still be flagged"


# ---------------------------------------------------------------------------
# TC-5325: C++ namespace qualifier false-positive fix
# ---------------------------------------------------------------------------

def test_cpp_namespace_qualifier_no_false_positive():
    """TC-5325: `Aspose::Slides::Foss::Presentation` — 0 findings when Presentation in public_classes.

    `_build_allowlist` must split import_allowlist on `::` so that namespace
    parts Aspose, Slides, Foss are added to member_names and not flagged.
    """
    surface = _make_surface(
        public_classes=["Presentation"],
        import_allowlist=["Aspose::Slides::Foss"],
    )
    content = _page(
        "## Overview\n\n"
        "Use `Aspose::Slides::Foss::Presentation` to create presentations.\n"
    )
    findings = check_api_allowlist(content, surface, "test-cpp-ns")
    assert len(findings) == 0, (
        f"Expected 0 findings for fully-qualified C++ ident with valid class, got: {findings}"
    )


def test_cpp_namespace_unknown_class_still_flagged():
    """TC-5325: `Aspose::Slides::Foss::UnknownClass` → HIGH finding for UnknownClass."""
    surface = _make_surface(
        public_classes=["Presentation"],
        import_allowlist=["Aspose::Slides::Foss"],
    )
    content = _page(
        "## Overview\n\n"
        "Use `Aspose::Slides::Foss::UnknownClass` to manage slides.\n"
    )
    findings = check_api_allowlist(content, surface, "test-cpp-unknown")
    high_findings = [f for f in findings if f.severity == "high" and "UnknownClass" in f.message]
    assert high_findings, (
        f"Expected HIGH finding for unknown C++ class, got: {findings}"
    )
    # Namespace qualifiers (Aspose, Slides, Foss) must NOT be flagged
    ns_findings = [
        f for f in findings
        if any(ns in f.message for ns in ("Aspose", "Slides", "Foss"))
    ]
    assert ns_findings == [], (
        f"Namespace qualifiers must not be flagged, got: {ns_findings}"
    )


def test_python_allowlist_split_unchanged():
    """TC-5325 regression: Python import_allowlist with dot-separator still works."""
    surface = _make_surface(
        public_classes=["Workbook"],
        import_allowlist=["aspose_cells_foss"],
    )
    content = _page(
        "## Overview\n\n"
        "Use `Workbook` from the `aspose_cells_foss` package.\n"
    )
    findings = check_api_allowlist(content, surface, "test-python-regression")
    # aspose_cells_foss has no dots or :: — it's a single token, should be in member_names
    assert len(findings) == 0, f"Python import_allowlist split regression: {findings}"


def test_dotted_python_allowlist_split():
    """TC-5325 regression: Dotted Python path 'aspose.cells' splits correctly."""
    surface = _make_surface(
        public_classes=["Workbook"],
        import_allowlist=["aspose.cells"],
    )
    content = _page("## Overview\n\nUse `aspose` and `cells` modules.\n")
    findings = check_api_allowlist(content, surface, "test-dotted-python")
    # 'aspose' and 'cells' are lowercase → unknown_members (MEDIUM) only if not in member_names
    # After TC-5325 fix they ARE in member_names → 0 findings
    member_findings = [
        f for f in findings
        if "aspose" in f.message or "cells" in f.message
    ]
    assert member_findings == [], f"Dotted Python path parts must be in member_names: {member_findings}"


# ---------------------------------------------------------------------------
# TC-5329: C++ stdlib exemptions
# ---------------------------------------------------------------------------

def _cpp_page(body: str) -> str:
    """Wrap body in C++ platform frontmatter."""
    return f"---\ntitle: Test C++ Page\nplatform: cpp\n---\n\n{body}\n"


def test_cpp_std_namespace_exempt():
    """TC-5329: `std` in C++ prose must not generate a finding."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("Use `std::string` to hold the file path.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    std_findings = [f for f in findings if "`std`" in f.message]
    assert std_findings == [], f"std should be exempt on cpp platform: {std_findings}"


def test_cpp_chrono_exempt():
    """TC-5329: `chrono` in C++ prose must not generate a finding."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("Use `std::chrono::seconds` for timeout.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    chrono_findings = [f for f in findings if "`chrono`" in f.message]
    assert chrono_findings == [], f"chrono should be exempt on cpp platform: {chrono_findings}"


def test_cpp_istream_exempt():
    """TC-5329: `istream` in C++ prose must not generate a finding."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("Pass an `istream` reference to load from memory.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    istream_findings = [f for f in findings if "`istream`" in f.message]
    assert istream_findings == [], f"istream should be exempt on cpp platform: {istream_findings}"


def test_cpp_u16string_exempt():
    """TC-5329: `u16string` in C++ prose must not generate a finding."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("File paths use `std::u16string` internally.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    u16_findings = [f for f in findings if "`u16string`" in f.message]
    assert u16_findings == [], f"u16string should be exempt on cpp platform: {u16_findings}"


def test_cpp_system_still_flagged():
    """TC-5329: `System` (a .NET namespace) must still generate HIGH on cpp platform."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("Use `System::DateTime` for timestamps.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    system_findings = [f for f in findings if "`System`" in f.message and f.severity == "high"]
    assert system_findings, "System (.NET namespace) must still be HIGH finding on cpp platform"


def test_cpp_invalid_op_exception_flagged():
    """TC-5329: `InvalidOperationException` (.NET) must still be HIGH on cpp platform."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("Throws `InvalidOperationException` if invalid.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    exc_findings = [f for f in findings if "InvalidOperationException" in f.message and f.severity == "high"]
    assert exc_findings, "InvalidOperationException must still be HIGH on cpp platform"


def test_cpp_valid_api_class_still_passes():
    """TC-5329: Valid API class in C++ still passes without finding."""
    surface = _make_surface(public_classes=["Presentation", "SaveFormat"])
    content = _cpp_page("Use the `Presentation` class and `SaveFormat` enum.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    api_findings = [f for f in findings if "`Presentation`" in f.message or "`SaveFormat`" in f.message]
    assert api_findings == [], f"Valid API classes must pass: {api_findings}"


def test_cpp_exception_types_exempt():
    """TC-5333-gap: C++ stdexcept types must be exempt on cpp platform."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page(
        "Throws `std::runtime_error` on parse failure. "
        "Use `std::out_of_range` for index checks. "
        "Catch `std::exception` as the base class.\n"
    )
    findings = check_api_allowlist(content, surface, "cpp-test")
    exc_findings = [
        f for f in findings
        if any(t in f.message for t in ["`runtime_error`", "`out_of_range`", "`exception`"])
    ]
    assert exc_findings == [], f"C++ exception types should be exempt: {exc_findings}"


def test_cpp_cmake_package_name_exempt():
    """TC-5333-gap: CMake package name (aspose_slides_foss) must be exempt on cpp platform."""
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page("Use `find_package(aspose_slides_foss REQUIRED)` to install.\n")
    findings = check_api_allowlist(content, surface, "cpp-test")
    cmake_findings = [f for f in findings if "`aspose_slides_foss`" in f.message]
    assert cmake_findings == [], f"CMake package name should be exempt: {cmake_findings}"


def test_cpp_platform_detection_with_long_frontmatter():
    """TC-5329-fix: C++ exemptions must apply even when platform: is past char 500.

    Real generated pages have long frontmatter (canonical, date, keywords, etc.)
    that push `platform: cpp` beyond the first 500 characters. Without the fix,
    the platform detection silently falls back to None and no C++ exemptions apply.
    """
    surface = _make_surface(public_classes=["Presentation"])
    # Build frontmatter that pushes `platform: cpp` past char 500
    long_fm = (
        "---\n"
        "canonical: https://docs.aspose.org/slides/cpp/developer-guide/installation/\n"
        "canonical_import: Aspose::Slides::Foss\n"
        "code_import: Aspose::Slides::Foss\n"
        "date: '2026-04-02T07:40:08Z'\n"
        "dateModified: '2026-04-02T08:09:23Z'\n"
        "datePublished: '2026-04-02T07:40:08Z'\n"
        "description: This library supports core presentation operations including slide\n"
        "  management, shape rendering, text formatting, and fill styles.\n"
        "display_name: Aspose.Slides FOSS for C++\n"
        "family: slides\n"
        "keywords:\n"
        "- cpp slides\n"
        "- aspose slides cpp\n"
        "platform: cpp\n"  # this lands ~char 550+
        "---\n\n"
        "Use `std::string` for text and `chrono` for timing.\n"
    )
    # Verify the frontmatter is actually long enough to trigger the bug
    assert long_fm.index("platform: cpp") > 500, "Test precondition: platform: must be past char 500"
    findings = check_api_allowlist(long_fm, surface, "cpp-install")
    std_findings = [f for f in findings if "`std`" in f.message or "`chrono`" in f.message]
    assert std_findings == [], f"C++ stdlib should be exempt even with long frontmatter: {std_findings}"


def test_cmake_required_keyword_exempt():
    """TC-5336: CMake REQUIRED keyword must be exempt on cpp platform.

    find_package(aspose_slides_foss REQUIRED) is valid cmake and REQUIRED is a
    cmake keyword, not an API class name. Must not produce api_allowlist:HIGH.
    """
    surface = _make_surface(public_classes=["Presentation"])
    content = _cpp_page(
        "Use `find_package(aspose_slides_foss REQUIRED)` in your CMakeLists.txt. "
        "After installing, link with `TARGET_LINK_LIBRARIES(myapp PRIVATE aspose_slides_foss)`. "
        "Set `cmake_minimum_required(VERSION 3.16)` at the top.\n"
    )
    findings = check_api_allowlist(content, surface, "cpp-install")
    cmake_findings = [
        f for f in findings
        if any(kw in f.message for kw in ["`REQUIRED`", "`TARGET_LINK_LIBRARIES`", "`CMake`"])
    ]
    assert cmake_findings == [], f"CMake keywords must be exempt on cpp pages: {cmake_findings}"

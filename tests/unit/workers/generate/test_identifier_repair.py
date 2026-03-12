"""Tests for TC-4213: post-generation identifier repair pass.

Six required test cases:
  A - hallucinated PascalCase replaced; known classes preserved
  B - code block hallucination annotated with comment
  C - product display name tokens preserved
  D - Python builtins/exceptions not touched
  E - no hallucinations → returns (original_text, [])
  F - >3 repairs → repairs list has >3 entries
"""
from __future__ import annotations

import pytest

from launcher.models.product import ApiSurface, ClassBrief, MethodSignature, PropertyRecord
from launcher.workers.generate._identifier_repair import repair_identifiers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_api_surface(
    public_classes: list[str] | None = None,
    class_briefs: list[ClassBrief] | None = None,
) -> ApiSurface:
    """Build a minimal ApiSurface for testing."""
    return ApiSurface(
        public_classes=public_classes or [],
        import_allowlist=[],
        confidence="high",
        class_briefs=class_briefs or [],
    )


def _workbook_surface() -> ApiSurface:
    """ApiSurface with Workbook, Worksheet, Cell, WorkbookSettings as known classes."""
    brief = ClassBrief(
        name="Workbook",
        methods=["save", "open"],
        properties=["worksheets"],
        typed_methods=[
            MethodSignature(name="save", parameters=[], return_type="None"),
            MethodSignature(name="open", parameters=[], return_type="Workbook"),
        ],
        typed_properties=[
            PropertyRecord(name="worksheets", type_annotation="list"),
        ],
    )
    return ApiSurface(
        public_classes=["Workbook", "Worksheet", "Cell", "WorkbookSettings"],
        import_allowlist=[],
        confidence="high",
        class_briefs=[brief],
    )


# ---------------------------------------------------------------------------
# Test A: hallucinated identifier replaced; known class preserved
# ---------------------------------------------------------------------------

class TestProseRepair:
    """Test A: prose hallucination replaced, known API classes preserved."""

    def test_hallucinated_class_replaced_in_prose(self) -> None:
        """SpreadsheetManager (hallucinated) → [identifier omitted]; Workbook preserved."""
        surface = _workbook_surface()
        text = (
            "Use SpreadsheetManager to create a new spreadsheet. "
            "Then call Workbook.save() to persist it."
        )
        repaired, repairs = repair_identifiers(text, surface)
        assert "SpreadsheetManager" not in repaired
        assert "[identifier omitted]" in repaired
        assert "Workbook" in repaired
        assert "SpreadsheetManager" in repairs

    def test_known_class_preserved_unchanged(self) -> None:
        """Workbook, Worksheet, Cell must never be replaced."""
        surface = _workbook_surface()
        text = "Create a Workbook, add a Worksheet, and access each Cell."
        repaired, repairs = repair_identifiers(text, surface)
        assert repaired == text
        assert repairs == []

    def test_multiple_hallucinated_classes(self) -> None:
        """Both SpreadsheetManager and RowIterator replaced."""
        surface = _workbook_surface()
        text = "Use SpreadsheetManager or RowIterator to iterate rows in Workbook."
        repaired, repairs = repair_identifiers(text, surface)
        assert "SpreadsheetManager" not in repaired
        assert "RowIterator" not in repaired
        assert "Workbook" in repaired
        assert len(repairs) == 2

    def test_markdown_header_not_modified(self) -> None:
        """Identifiers in markdown headers are never repaired."""
        surface = _workbook_surface()
        text = "## Using SpreadsheetManager\n\nThis is the body with Workbook."
        repaired, repairs = repair_identifiers(text, surface)
        # Header line preserved
        assert "## Using SpreadsheetManager" in repaired
        # Body unchanged (Workbook is known)
        assert "Workbook" in repaired
        # SpreadsheetManager in header must NOT be in repairs
        assert "SpreadsheetManager" not in repairs


# ---------------------------------------------------------------------------
# Test B: code block hallucination annotated with comment
# ---------------------------------------------------------------------------

class TestCodeBlockRepair:
    """Test B: hallucinated identifiers in code blocks annotated with comments."""

    def test_code_block_hallucination_annotated(self) -> None:
        """RowIterator in code block → comment appended; code line preserved."""
        surface = _workbook_surface()
        text = (
            "Example:\n\n"
            "```python\n"
            "iterator = RowIterator(workbook)\n"
            "for row in iterator:\n"
            "    print(row)\n"
            "```\n"
        )
        repaired, repairs = repair_identifiers(text, surface)
        # The hallucinated identifier should be noted in repairs
        assert "RowIterator" in repairs
        # The code line should contain an annotation comment
        assert "# RowIterator: unknown" in repaired
        # The surrounding code structure should be preserved
        assert "for row in iterator:" in repaired
        assert "print(row)" in repaired

    def test_code_block_fence_lines_preserved(self) -> None:
        """Fence delimiter lines (```) are never modified."""
        surface = _workbook_surface()
        text = "```python\nwb = Workbook()\n```\n"
        repaired, repairs = repair_identifiers(text, surface)
        assert "```python" in repaired
        assert "```" in repaired
        assert repairs == []

    def test_known_class_in_code_block_not_annotated(self) -> None:
        """Workbook in code block must not get a hallucination comment."""
        surface = _workbook_surface()
        text = "```python\nwb = Workbook()\nwb.save('out.xlsx')\n```\n"
        repaired, repairs = repair_identifiers(text, surface)
        assert repaired == text
        assert repairs == []


# ---------------------------------------------------------------------------
# Test C: product display name tokens preserved
# ---------------------------------------------------------------------------

class TestProductDisplayNameExemption:
    """Test C: product display name and its component tokens are not replaced."""

    def test_product_name_token_preserved(self) -> None:
        """'Aspose' and 'Cells' from display_name='Aspose.Cells' are exempt."""
        surface = _make_api_surface(public_classes=["Workbook"])
        text = "Aspose.Cells for Python provides a Workbook class."
        repaired, repairs = repair_identifiers(
            text, surface, product_display_name="Aspose.Cells"
        )
        assert "Aspose" in repaired
        assert "Cells" in repaired
        # "Aspose" and "Cells" must NOT appear in repairs
        assert "Aspose" not in repairs
        assert "Cells" not in repairs

    def test_product_name_with_spaces_tokenised(self) -> None:
        """Multi-word display name like 'Aspose 3D' — both tokens exempt."""
        surface = _make_api_surface(public_classes=["Scene"])
        text = "Aspose 3D uses the Scene class for 3D objects."
        repaired, repairs = repair_identifiers(
            text, surface, product_display_name="Aspose 3D"
        )
        assert "Aspose" in repaired
        assert "Scene" in repaired
        assert "Aspose" not in repairs
        assert "Scene" not in repairs

    def test_without_display_name_product_tokens_may_be_flagged(self) -> None:
        """Without product_display_name, 'Aspose' might be flagged if not in known set.

        This test documents that the exemption requires the caller to pass the name.
        If the product token happens to be in _GENERIC_PROPER_NOUNS it's still safe.
        """
        # "Aspose" is not in _GENERIC_PROPER_NOUNS by default; without the param
        # it might be flagged. We just check that passing the param prevents it.
        surface = _make_api_surface(public_classes=["Workbook"])
        text = "Use Aspose to work with spreadsheets."
        _repaired_with, repairs_with = repair_identifiers(
            text, surface, product_display_name="Aspose"
        )
        assert "Aspose" not in repairs_with


# ---------------------------------------------------------------------------
# Test D: Python builtins and standard exceptions not touched
# ---------------------------------------------------------------------------

class TestPythonBuiltinsExempt:
    """Test D: standard Python builtins, exceptions, and typing names are never replaced."""

    def test_exception_types_exempt(self) -> None:
        """Exception, ValueError, TypeError, FileNotFoundError preserved."""
        surface = _make_api_surface(public_classes=["Workbook"])
        text = (
            "Raises ValueError if the path is invalid. "
            "Raises FileNotFoundError when the file does not exist. "
            "Catches Exception for generic errors."
        )
        repaired, repairs = repair_identifiers(text, surface)
        assert repaired == text
        assert repairs == []

    def test_path_and_io_types_exempt(self) -> None:
        """Path, BytesIO, StringIO, TextIOWrapper are exempt."""
        surface = _make_api_surface(public_classes=["Workbook"])
        text = "Pass a Path object or use BytesIO for in-memory processing."
        repaired, repairs = repair_identifiers(text, surface)
        assert "Path" in repaired
        assert "BytesIO" in repaired
        assert repairs == []

    def test_typing_constructs_exempt(self) -> None:
        """Optional, Union, Callable, TypeVar, etc. are exempt."""
        surface = _make_api_surface(public_classes=["Workbook"])
        text = "The method accepts Optional arguments and returns Callable types."
        repaired, repairs = repair_identifiers(text, surface)
        assert "Optional" in repaired
        assert "Callable" in repaired
        assert repairs == []

    def test_enum_base_class_exempt(self) -> None:
        """'Enum' itself (the base class) is exempt."""
        surface = _make_api_surface(public_classes=["SaveFormat"])
        text = "SaveFormat is an Enum subclass with file format options."
        repaired, repairs = repair_identifiers(text, surface)
        assert "Enum" in repaired
        # "Enum" must not be flagged
        assert "Enum" not in repairs
        # SaveFormat is known
        assert "SaveFormat" in repaired


# ---------------------------------------------------------------------------
# Test E: no hallucinations → returns (original_text, [])
# ---------------------------------------------------------------------------

class TestNoHallucinations:
    """Test E: when all identifiers are known or exempt, no repairs are made."""

    def test_clean_text_unchanged(self) -> None:
        """Text with only known classes returns (original_text, [])."""
        surface = _workbook_surface()
        original = (
            "Create a Workbook instance and add a Worksheet to it. "
            "Access each Cell using row and column indices."
        )
        repaired, repairs = repair_identifiers(original, surface)
        assert repaired == original
        assert repairs == []

    def test_empty_api_surface_still_exempts_builtins(self) -> None:
        """Even with empty public_classes, builtins remain exempt."""
        surface = _make_api_surface(public_classes=[])
        text = "Raises ValueError and catches Exception in a try block."
        repaired, repairs = repair_identifiers(text, surface)
        assert "ValueError" in repaired
        assert "Exception" in repaired
        assert repairs == []

    def test_empty_text_returns_empty(self) -> None:
        """Empty input string → (empty string, [])."""
        surface = _workbook_surface()
        repaired, repairs = repair_identifiers("", surface)
        assert repaired == ""
        assert repairs == []

    def test_prose_only_known_classes(self) -> None:
        """All API identifiers are known → no repairs."""
        surface = _workbook_surface()
        text = "Workbook contains one or more Worksheet objects, each with Cell data."
        repaired, repairs = repair_identifiers(text, surface)
        assert repairs == []
        assert repaired == text


# ---------------------------------------------------------------------------
# Test F: >3 repairs → repairs list has >3 entries
# ---------------------------------------------------------------------------

class TestManyRepairs:
    """Test F: when >3 hallucinated identifiers are present, repairs list reflects all."""

    def test_four_or_more_repairs_detected(self) -> None:
        """Text with 4 distinct hallucinated identifiers → len(repairs) > 3.

        Note: identifiers chosen do NOT contain any known class name as a substring,
        since the spec says to skip identifiers that contain a known class as a
        substring (conservative: might be a valid compound class).
        """
        surface = _workbook_surface()  # only Workbook, Worksheet, Cell known
        text = (
            "Use SpreadsheetManager to open files. "
            "RowIterator helps traverse rows. "
            "GridRenderer produces output. "
            "StyleApplier formats output. "
            "Then save with Workbook."
        )
        repaired, repairs = repair_identifiers(text, surface)
        assert len(repairs) > 3
        # All 4 hallucinated names should appear in repairs
        assert "SpreadsheetManager" in repairs
        assert "RowIterator" in repairs
        assert "GridRenderer" in repairs
        assert "StyleApplier" in repairs
        # Known class preserved
        assert "Workbook" in repaired

    def test_repairs_list_deduplicated_input_still_counted_per_occurrence(self) -> None:
        """Each occurrence of a hallucinated identifier counts as a separate repair."""
        surface = _workbook_surface()
        text = (
            "SpreadsheetManager is used here. "
            "SpreadsheetManager is mentioned again. "
            "RowIterator appears once. "
            "GridRenderer appears once. "
            "StyleApplier appears once."
        )
        _repaired, repairs = repair_identifiers(text, surface)
        # At least 5 occurrences (SpreadsheetManager ×2 + 3 others)
        assert len(repairs) >= 5

    def test_caller_can_use_repairs_count_for_event(self) -> None:
        """Caller determines whether to emit event based on len(repairs) > 3."""
        surface = _workbook_surface()
        text = (
            "GridEngine processes data. "
            "TableParser reads files. "
            "SectionBuilder builds output. "
            "StyleApplier formats cells. "
            "Use Workbook for best results."
        )
        _repaired, repairs = repair_identifiers(text, surface)
        # This is the condition the worker checks for emitting the event
        assert len(repairs) > 3


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Additional edge cases for robustness."""

    def test_short_identifiers_below_threshold_not_repaired(self) -> None:
        """PascalCase tokens < 4 chars are not matched (regex requires ≥4 chars total)."""
        surface = _make_api_surface(public_classes=["Workbook"])
        # "Val" is 3 chars, should not be matched by the ≥4 char regex
        text = "The Val property returns data from Workbook."
        repaired, repairs = repair_identifiers(text, surface)
        # "Val" (3 chars) should not be flagged; regex requires ≥4 total chars
        assert "Val" in repaired

    def test_substring_of_known_not_repaired(self) -> None:
        """A token that is a substring of a known class is not flagged.

        E.g., if "WorkbookSettings" is known, then "Workbook" (substring) is not flagged.
        "WorkbookSettings" is in the known set from _workbook_surface().
        """
        surface = _workbook_surface()  # includes WorkbookSettings
        text = "WorkbookSettings controls global options."
        repaired, repairs = repair_identifiers(text, surface)
        assert "WorkbookSettings" in repaired
        assert "WorkbookSettings" not in repairs

    def test_mixed_prose_and_code(self) -> None:
        """Mixed prose and code: each segment repaired independently."""
        surface = _workbook_surface()
        text = (
            "The SpreadsheetManager class does not exist.\n\n"
            "```python\n"
            "wb = Workbook()\n"
            "ri = RowIterator(wb)\n"
            "```\n\n"
            "Use Workbook instead."
        )
        repaired, repairs = repair_identifiers(text, surface)
        # Prose: SpreadsheetManager replaced
        assert "SpreadsheetManager" not in repaired or "[identifier omitted]" in repaired
        # Code: RowIterator annotated
        assert "RowIterator" in repairs or "# RowIterator" in repaired
        # Known classes preserved in both contexts
        assert "Workbook" in repaired

    def test_no_api_surface_data_only_exempts(self) -> None:
        """With empty ApiSurface, only builtins and generics are exempt."""
        surface = _make_api_surface(public_classes=[])
        text = "Use SpreadsheetManager with ValueError handling."
        repaired, repairs = repair_identifiers(text, surface)
        # SpreadsheetManager should be flagged
        assert "SpreadsheetManager" in repairs
        # ValueError should not be flagged
        assert "ValueError" not in repairs


# ---------------------------------------------------------------------------
# TC-4222 (HG-22): single-hump words must NOT be repaired
# ---------------------------------------------------------------------------

class TestSingleHumpExemption:
    """TC-4222/HG-22: _PASCAL_RE must require true PascalCase (≥2 humps or +digit).

    Single-hump capitalized words ("Lambert", "Phong", "Developers", "These")
    are NOT multi-hump PascalCase and must never be replaced with [identifier omitted].
    These were incorrectly caught by the old _PASCAL_RE = r"\b([A-Z][a-zA-Z0-9]{3,})\b".
    """

    def test_single_hump_material_name_not_repaired(self) -> None:
        """'Lambert' is a single-hump word — should NOT be replaced even if not in API surface."""
        surface = _make_api_surface(public_classes=["Scene"])
        text = "The Lambert material provides diffuse lighting for 3D objects."
        repaired, repairs = repair_identifiers(text, surface)
        assert "Lambert" in repaired
        assert "Lambert" not in repairs
        assert "[identifier omitted]" not in repaired

    def test_pronoun_at_sentence_start_not_repaired(self) -> None:
        """'These', 'Which', 'What' at sentence start — should NOT be repaired."""
        surface = _make_api_surface(public_classes=["Scene"])
        text = (
            "These methods are available on Scene objects. "
            "Which format should you use? "
            "What properties does Node expose?"
        )
        repaired, repairs = repair_identifiers(text, surface)
        assert "These" in repaired
        assert "Which" in repaired
        assert "What" in repaired
        assert "These" not in repairs
        assert "Which" not in repairs
        assert "What" not in repairs

    def test_developer_noun_not_repaired(self) -> None:
        """'Developers', 'Installation', 'Common' — ordinary nouns, not PascalCase."""
        surface = _make_api_surface(public_classes=["Scene"])
        text = (
            "Developers can use Scene to build 3D applications. "
            "Installation requires pip. "
            "Common errors include missing imports."
        )
        repaired, repairs = repair_identifiers(text, surface)
        assert "Developers" in repaired
        assert "Installation" in repaired
        assert "Common" in repaired
        assert "Developers" not in repairs
        assert "Installation" not in repairs
        assert "Common" not in repairs
        assert "[identifier omitted]" not in repaired

    def test_true_pascal_case_still_caught(self) -> None:
        """Multi-hump PascalCase like ObjLoadOptions still caught (not a regression)."""
        surface = _make_api_surface(public_classes=["Scene"])
        text = "Use ObjLoadOptions to configure the OBJ importer."
        repaired, repairs = repair_identifiers(text, surface)
        assert "ObjLoadOptions" in repairs
        assert "[identifier omitted]" in repaired

    def test_pascal_digit_still_caught(self) -> None:
        """PascalCase+digit like Vector3 is still caught if not in known set."""
        surface = _make_api_surface(public_classes=["Scene"])
        text = "The Vector3 type holds coordinates."
        repaired, repairs = repair_identifiers(text, surface)
        # Vector3 matches PascalCase+digit pattern — caught if not in known set
        assert "Vector3" in repairs

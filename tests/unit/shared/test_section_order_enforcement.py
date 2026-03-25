"""Tests for section order enforcement in ir_renderer (TC-QF-01)."""
from __future__ import annotations

from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.shared.ir_renderer import (
    _dedup_sections,
    _enforce_section_order,
    _remove_post_terminal,
)


def _make_section(heading: str, content: str = "Some text.") -> SectionIR:
    """Helper: create a SectionIR with one paragraph block."""
    return SectionIR(
        section_id=heading.lower().replace(" ", "_"),
        heading=heading,
        level=2,
        blocks=[BlockIR(type=BlockType.paragraph, content=content)],
    )


# --- _enforce_section_order ---


def test_correct_order_unchanged():
    """Sections already in canonical order are returned unchanged."""
    sections = [
        _make_section("Overview"),
        _make_section("Key Features"),
        _make_section("Quick Start"),
        _make_section("See Also"),
    ]
    result = _enforce_section_order(sections, "landing")
    headings = [s.heading for s in result]
    assert headings == ["Overview", "Key Features", "Quick Start", "See Also"]


def test_inverted_sections_reordered():
    """Misordered sections are reordered to match skeleton."""
    sections = [
        _make_section("See Also"),
        _make_section("Quick Start"),
        _make_section("Key Features"),
        _make_section("Overview"),
    ]
    result = _enforce_section_order(sections, "landing")
    headings = [s.heading for s in result]
    assert headings == ["Overview", "Key Features", "Quick Start", "See Also"]


def test_unknown_role_unchanged():
    """Unknown page_role leaves sections in original order."""
    sections = [
        _make_section("Zebra"),
        _make_section("Alpha"),
    ]
    result = _enforce_section_order(sections, "nonexistent_role_xyz")
    headings = [s.heading for s in result]
    assert headings == ["Zebra", "Alpha"]


def test_unmatched_sections_appended():
    """Sections not in the skeleton are appended after matched ones."""
    sections = [
        _make_section("Custom Section"),
        _make_section("See Also"),
        _make_section("Overview"),
        _make_section("Key Features"),
        _make_section("Quick Start"),
    ]
    result = _enforce_section_order(sections, "landing")
    headings = [s.heading for s in result]
    # Canonical order first, then unmatched
    assert headings == [
        "Overview", "Key Features", "Quick Start", "See Also",
        "Custom Section",
    ]


def test_single_section_unchanged():
    """A single section is returned as-is (need >=2 to reorder)."""
    sections = [_make_section("Overview")]
    result = _enforce_section_order(sections, "landing")
    assert len(result) == 1
    assert result[0].heading == "Overview"


# --- _remove_post_terminal ---


def test_post_terminal_removed():
    """Content after See Also is removed."""
    sections = [
        _make_section("Overview"),
        _make_section("See Also"),
        _make_section("Leftover"),
    ]
    result = _remove_post_terminal(sections)
    headings = [s.heading for s in result]
    assert headings == ["Overview", "See Also"]


def test_no_terminal_unchanged():
    """Without a terminal section, all sections are kept."""
    sections = [
        _make_section("Overview"),
        _make_section("Methods"),
    ]
    result = _remove_post_terminal(sections)
    assert len(result) == 2


def test_terminal_at_end_unchanged():
    """Terminal section at the end keeps all sections."""
    sections = [
        _make_section("Overview"),
        _make_section("See Also"),
    ]
    result = _remove_post_terminal(sections)
    assert len(result) == 2


def test_related_resources_terminal():
    """'Related Resources' is also recognized as terminal."""
    sections = [
        _make_section("Overview"),
        _make_section("Related Resources"),
        _make_section("Extra"),
    ]
    result = _remove_post_terminal(sections)
    headings = [s.heading for s in result]
    assert headings == ["Overview", "Related Resources"]


def test_empty_sections_safe():
    """Empty section list returns empty."""
    assert _remove_post_terminal([]) == []


# --- _dedup_sections ---


def test_duplicate_merged():
    """Duplicate headings are merged into one section."""
    sections = [
        _make_section("Overview", "First paragraph."),
        _make_section("Methods", "Method content."),
        _make_section("Overview", "Second paragraph."),
    ]
    result = _dedup_sections(sections)
    headings = [s.heading for s in result]
    assert headings == ["Overview", "Methods"]
    # Merged section should have blocks from both
    assert len(result[0].blocks) == 2
    assert result[0].blocks[0].content == "First paragraph."
    assert result[0].blocks[1].content == "Second paragraph."


def test_no_duplicates_unchanged():
    """Without duplicates, sections are returned as-is."""
    sections = [
        _make_section("Overview"),
        _make_section("Methods"),
    ]
    result = _dedup_sections(sections)
    assert len(result) == 2


def test_case_insensitive_dedup():
    """Dedup is case-insensitive."""
    sections = [
        _make_section("Overview", "A."),
        _make_section("overview", "B."),
    ]
    result = _dedup_sections(sections)
    assert len(result) == 1
    assert len(result[0].blocks) == 2


def test_empty_sections_dedup_safe():
    """Empty section list returns empty."""
    assert _dedup_sections([]) == []

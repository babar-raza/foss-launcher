"""TC-5134: PGDR terminal section reorder tests.

Verifies that _reorder_terminal_sections() moves terminal sections
(See Also, References, etc.) to the end of the section list.
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType, SectionIR
from launcher.workers.generate.worker import _reorder_terminal_sections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(heading: str, content: str = "Some content.") -> SectionIR:
    """Create a minimal SectionIR with one paragraph block."""
    return SectionIR(
        section_id=heading.lower().replace(" ", "_"),
        heading=heading,
        blocks=[BlockIR(type=BlockType.paragraph, content=content)],
    )


# ---------------------------------------------------------------------------
# Tests — reorder needed
# ---------------------------------------------------------------------------

class TestReorderNeeded:
    """Terminal sections not at end → moved to end."""

    def test_see_also_before_content(self):
        """See Also in middle → moved to end."""
        sections = [_section("Overview"), _section("See Also"), _section("Advanced Usage")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Overview", "Advanced Usage", "See Also"]

    def test_references_first(self):
        """References at start → moved to end."""
        sections = [_section("References"), _section("Overview"), _section("Examples")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Overview", "Examples", "References"]

    def test_multiple_terminals_in_wrong_position(self):
        """Multiple terminal sections scattered → all moved to end, preserving order."""
        sections = [
            _section("See Also"),
            _section("Overview"),
            _section("References"),
            _section("Examples"),
        ]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == [
            "Overview", "Examples", "See Also", "References",
        ]

    def test_related_topics_moved(self):
        """Related Topics is a terminal heading."""
        sections = [_section("Related Topics"), _section("Code Examples")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Code Examples", "Related Topics"]

    def test_further_reading_moved(self):
        """Further Reading is a terminal heading."""
        sections = [_section("Further Reading"), _section("API Reference")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["API Reference", "Further Reading"]


# ---------------------------------------------------------------------------
# Tests — already correct / no change needed
# ---------------------------------------------------------------------------

class TestAlreadyCorrect:
    """Terminal sections already at end → no change."""

    def test_terminal_already_last(self):
        """See Also already at end → order preserved."""
        sections = [_section("Overview"), _section("Examples"), _section("See Also")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Overview", "Examples", "See Also"]

    def test_multiple_terminals_already_last(self):
        """Multiple terminals already at end → order preserved."""
        sections = [
            _section("Overview"),
            _section("See Also"),
            _section("References"),
        ]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Overview", "See Also", "References"]

    def test_no_terminal_sections(self):
        """No terminal sections → order preserved."""
        sections = [_section("Overview"), _section("Examples"), _section("API Reference")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Overview", "Examples", "API Reference"]


# ---------------------------------------------------------------------------
# Tests — edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Empty lists, single sections, case insensitivity."""

    def test_empty_list(self):
        """Empty section list → empty result."""
        assert _reorder_terminal_sections([]) == []

    def test_single_terminal(self):
        """Only one section and it's terminal → returned as-is."""
        sections = [_section("See Also")]
        result = _reorder_terminal_sections(sections)
        assert len(result) == 1
        assert result[0].heading == "See Also"

    def test_single_non_terminal(self):
        """Only one section and it's not terminal → returned as-is."""
        sections = [_section("Overview")]
        result = _reorder_terminal_sections(sections)
        assert len(result) == 1
        assert result[0].heading == "Overview"

    def test_case_insensitive(self):
        """Terminal heading matching is case-insensitive."""
        sections = [_section("SEE ALSO"), _section("Overview")]
        result = _reorder_terminal_sections(sections)
        assert [s.heading for s in result] == ["Overview", "SEE ALSO"]

    def test_whitespace_in_heading(self):
        """Leading/trailing whitespace in heading is stripped for matching."""
        sections = [_section("  See Also  "), _section("Overview")]
        result = _reorder_terminal_sections(sections)
        assert result[-1].heading.strip() == "See Also"
        assert result[0].heading == "Overview"

    def test_idempotent(self):
        """Running reorder twice gives the same result."""
        sections = [_section("See Also"), _section("Overview"), _section("References")]
        result1 = _reorder_terminal_sections(sections)
        result2 = _reorder_terminal_sections(result1)
        assert [s.heading for s in result1] == [s.heading for s in result2]

    def test_non_terminal_order_preserved(self):
        """Non-terminal sections maintain their relative order."""
        sections = [
            _section("See Also"),
            _section("Zulu"),
            _section("Alpha"),
            _section("Mike"),
        ]
        result = _reorder_terminal_sections(sections)
        non_terminal = [s.heading for s in result if s.heading != "See Also"]
        assert non_terminal == ["Zulu", "Alpha", "Mike"]

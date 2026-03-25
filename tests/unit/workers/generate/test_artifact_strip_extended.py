"""Tests for _strip_opener_boilerplate in section_validator (TC-QF-01)."""
from __future__ import annotations

from launcher.workers.generate.section_validator import _strip_opener_boilerplate


def test_opener_stripped():
    """Opener sentence starting with 'When working with' is removed."""
    content = (
        "## Overview\n"
        "\n"
        "When working with spreadsheets, you need tools. This library helps."
    )
    result = _strip_opener_boilerplate(content)
    assert "When working with" not in result
    assert "This library helps." in result


def test_midparagraph_kept():
    """'When working with' in the middle of a paragraph is not touched."""
    content = (
        "## Overview\n"
        "\n"
        "Do X when working with Y."
    )
    result = _strip_opener_boilerplate(content)
    assert "when working with" in result


def test_multiple_sections_stripped():
    """All sections with opener boilerplate get stripped."""
    content = (
        "## Overview\n"
        "\n"
        "When working with files, X. Real content here.\n"
        "\n"
        "## Methods\n"
        "\n"
        "When working with methods, Y. Method details here."
    )
    result = _strip_opener_boilerplate(content)
    assert result.count("When working with") == 0
    assert "Real content here." in result
    assert "Method details here." in result


def test_empty_section_safe():
    """Empty content after heading does not crash."""
    content = "## Overview\n"
    result = _strip_opener_boilerplate(content)
    assert "## Overview" in result


def test_empty_content_safe():
    """Empty string input returns empty string."""
    assert _strip_opener_boilerplate("") == ""


def test_no_headings_unchanged():
    """Content without H2 headings is returned unchanged."""
    content = "When working with spreadsheets, you need tools."
    result = _strip_opener_boilerplate(content)
    # No H2 heading, so the opener is NOT stripped (it only strips after H2)
    assert result == content


def test_opener_entire_sentence_only():
    """Only the opener sentence is removed, rest of paragraph preserved."""
    content = (
        "## Key Features\n"
        "\n"
        "When working with large datasets, performance matters. "
        "Feature A provides fast reads. Feature B enables batch writes."
    )
    result = _strip_opener_boilerplate(content)
    assert "When working with" not in result
    assert "Feature A provides fast reads." in result
    assert "Feature B enables batch writes." in result

"""Unit tests for check_opener_boilerplate (TC-QG-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.artifacts import check_opener_boilerplate


def _page(body: str) -> str:
    return f"---\ntitle: Test Page\n---\n\n{body}\n"


def test_when_working_with_opener_detected():
    """Section starts with 'When working with spreadsheets, ...' -> MEDIUM."""
    content = _page(
        "## Overview\n\n"
        "When working with spreadsheets, you often need to format cells.\n\n"
        "## Usage\n\n"
        "Call the format method to style cells.\n"
    )
    findings = check_opener_boilerplate(content, "test-slug")
    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert findings[0].check == "opener_boilerplate"


def test_when_working_with_multiple_sections():
    """3+ sections start with it -> HIGH."""
    content = _page(
        "## Loading\n\n"
        "When working with large files, you need to load them efficiently.\n\n"
        "## Saving\n\n"
        "When working with output formats, choose the right save options.\n\n"
        "## Converting\n\n"
        "When working with conversions, specify the target format.\n\n"
        "## Editing\n\n"
        "When working with cell data, use the Cell class.\n"
    )
    findings = check_opener_boilerplate(content, "test-slug")
    assert len(findings) == 1
    assert findings[0].severity == "high"


def test_when_working_with_midparagraph_ok():
    """Mid-paragraph use '... when working with large files ...' -> no finding."""
    content = _page(
        "## Overview\n\n"
        "This library is useful when working with large files.\n\n"
        "## Usage\n\n"
        "You may encounter issues when working with corrupted data.\n"
    )
    findings = check_opener_boilerplate(content, "test-slug")
    assert len(findings) == 0


def test_artifact_phrase_in_code_block_exempt():
    """Phrase inside code block -> no finding."""
    content = _page(
        "## Overview\n\n"
        "```python\n"
        "# When working with files, use this pattern\n"
        "wb = Workbook()\n"
        "```\n\n"
        "The code above shows basic usage.\n"
    )
    findings = check_opener_boilerplate(content, "test-slug")
    assert len(findings) == 0

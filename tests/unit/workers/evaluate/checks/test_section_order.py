"""Unit tests for check_section_order, check_terminal_section, check_duplicate_sections (TC-QG-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.structure import (
    check_section_order,
    check_terminal_section,
    check_duplicate_sections,
)


def _page(body: str) -> str:
    return f"---\ntitle: Test Page\n---\n\n{body}\n"


# ---------------------------------------------------------------------------
# check_section_order
# ---------------------------------------------------------------------------


def test_correct_order_passes():
    """Headings in skeleton order -> no findings."""
    content = _page(
        "## Overview\n\nIntro text.\n\n"
        "## Key Features\n\nFeature list.\n\n"
        "## Quick Start\n\nCode example.\n\n"
        "## See Also\n\n- [Link](url)\n"
    )
    findings = check_section_order(content, "test-slug", page_role="landing")
    assert len(findings) == 0


def test_inverted_order_detected():
    """'See Also' before 'Overview' -> MEDIUM finding."""
    content = _page(
        "## See Also\n\n- [Link](url)\n\n"
        "## Overview\n\nIntro text.\n\n"
        "## Key Features\n\nFeature list.\n\n"
        "## Quick Start\n\nCode example.\n"
    )
    findings = check_section_order(content, "test-slug", page_role="landing")
    assert len(findings) > 0
    assert findings[0].severity == "medium"
    assert findings[0].check == "section_order"


def test_unknown_page_role_lenient():
    """Unknown role -> no findings (graceful degradation)."""
    content = _page(
        "## Section A\n\nText.\n\n"
        "## Section B\n\nMore text.\n"
    )
    findings = check_section_order(content, "test-slug", page_role="nonexistent_role")
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# check_terminal_section
# ---------------------------------------------------------------------------


def test_content_after_see_also():
    """Additional H2 after '## See Also' -> HIGH finding."""
    content = _page(
        "## Overview\n\nIntro text.\n\n"
        "## See Also\n\n- [Link](url)\n\n"
        "## Appendix\n\nExtra content after terminal section.\n"
    )
    findings = check_terminal_section(content, "test-slug")
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].check == "terminal_section"


def test_see_also_last_no_finding():
    """See Also as last section with just links -> no finding."""
    content = _page(
        "## Overview\n\nIntro text.\n\n"
        "## See Also\n\n- [Link](url)\n"
    )
    findings = check_terminal_section(content, "test-slug")
    assert len(findings) == 0


def test_no_terminal_section_no_finding():
    """No terminal section -> no finding."""
    content = _page(
        "## Overview\n\nIntro text.\n\n"
        "## Usage\n\nUsage details.\n"
    )
    findings = check_terminal_section(content, "test-slug")
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# check_duplicate_sections
# ---------------------------------------------------------------------------


def test_duplicate_h2_detected():
    """Two '## Overview' headings -> HIGH finding."""
    content = _page(
        "## Overview\n\nFirst overview.\n\n"
        "## Overview\n\nSecond overview.\n\n"
        "## Usage\n\nUsage details.\n"
    )
    findings = check_duplicate_sections(content, "test-slug")
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].check == "duplicate_sections"
    assert "overview" in findings[0].message.lower()


def test_no_duplicates_passes():
    """Unique headings -> no findings."""
    content = _page(
        "## Overview\n\nIntro.\n\n"
        "## Usage\n\nDetails.\n\n"
        "## See Also\n\n- [Link](url)\n"
    )
    findings = check_duplicate_sections(content, "test-slug")
    assert len(findings) == 0

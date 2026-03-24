"""SR3-02: Regression tests for extract_template_sections on the getting-started template.

Guards against:
1. Structural regression: heading order/count must be stable
2. HTML comment isolation: HTML comment lines must never appear as skeleton headings
"""
from __future__ import annotations

import pytest

try:
    from launcher.content.template_loader import extract_template_sections
    _HAS_LOADER = True
except ImportError:
    _HAS_LOADER = False

_GETTING_STARTED_TEMPLATE = (
    "specs/templates/docs.aspose.org"
    "/__FAMILY__/__PLATFORM__/getting-started/_index.md"
)

_EXPECTED_HEADINGS = [
    "Introduction",
    "System Requirements",
    "Quick Install",
    "Quick Start Example",
    "What's Next",
]


@pytest.mark.skipif(not _HAS_LOADER, reason="template_loader not importable")
class TestGettingStartedSkeleton:
    """SR3-02: Skeleton extraction regression guard for the getting-started template."""

    def test_getting_started_skeleton_headings(self):
        """extract_template_sections produces exactly the expected 5 headings in order."""
        content = open(_GETTING_STARTED_TEMPLATE, encoding="utf-8").read()
        sections = extract_template_sections(content)
        headings = [s.heading for s in sections]
        assert headings == _EXPECTED_HEADINGS, (
            f"Skeleton headings changed unexpectedly.\n"
            f"Expected: {_EXPECTED_HEADINGS}\n"
            f"Got:      {headings}"
        )

    def test_html_comment_not_in_skeleton(self):
        """An HTML comment injected before __BODY_INTRO__ does NOT appear as a heading.

        This is the regression guard for FPRSR05SR-03: ensures that HTML comments
        are always discarded by extract_template_sections (H2-only regex ^##\\s+).
        """
        base_content = open(_GETTING_STARTED_TEMPLATE, encoding="utf-8").read()
        # Inject a synthetic HTML comment before __BODY_INTRO__ to simulate the
        # pre-FPRSR05SR-03 state.
        injected = base_content.replace(
            "__BODY_INTRO__",
            "<!-- INJECTED TEST COMMENT -->\n__BODY_INTRO__",
        )
        sections = extract_template_sections(injected)
        headings = [s.heading for s in sections]
        # Skeleton must be identical to the clean template
        assert headings == _EXPECTED_HEADINGS, (
            f"HTML comment leaked into skeleton: {headings}"
        )
        # Extra safety: no heading should contain HTML comment syntax
        for h in headings:
            assert "<!--" not in h and "-->" not in h, (
                f"HTML comment syntax found in heading: {h!r}"
            )

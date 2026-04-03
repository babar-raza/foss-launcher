"""Tests for heading_echo check (TC-PROSE-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.heading_echo import check_heading_echo


class TestHeadingEcho:
    def test_informative_paragraph_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading Files\n\n"
            "Use `Scene.from_file()` to load OBJ, STL, and glTF models from disk "
            "with automatic format detection.\n"
        )
        findings = check_heading_echo(content, "test-page")
        assert len(findings) == 0

    def test_heading_restatement_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading Files\n\n"
            "About loading files.\n"
        )
        findings = check_heading_echo(content, "test-page")
        assert len(findings) == 1
        assert findings[0].check == "heading_echo"
        assert findings[0].severity == "low"

    def test_longer_paragraph_not_flagged(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading Files\n\n"
            "Loading files from disk is the first step in any 3D processing pipeline. "
            "The Scene class provides from_file() which auto-detects the format, "
            "builds the node hierarchy, and returns a fully populated scene graph.\n"
        )
        findings = check_heading_echo(content, "test-page")
        assert len(findings) == 0  # too many words to be an echo

    def test_dissimilar_short_paragraph_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "Install via pip for quick setup.\n"
        )
        findings = check_heading_echo(content, "test-page")
        assert len(findings) == 0  # low Jaccard similarity

    def test_h3_headings_also_checked(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Key Features\n\n"
            "About key features.\n\n"
            "### Supported Formats\n\n"
            "About supported formats.\n"
        )
        findings = check_heading_echo(content, "test-page")
        # Both headings may flag
        assert len(findings) >= 1

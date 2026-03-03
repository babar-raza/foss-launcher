"""Tests for TC-3688: G2 section-level repetition detection."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from launch.workers.w9_validator.gates.gate_intra_page_repetition import (
    _extract_sections,
    _scan_sections,
    _SECTION_SIMILARITY_THRESHOLD,
    _MIN_SECTION_WORDS,
    execute_gate,
)


# ── _extract_sections helper ────────────────────────────────────────────────


class TestExtractSections:
    """Verify H2-section extraction from markdown."""

    def test_basic_two_sections(self):
        content = textwrap.dedent("""\
            ---
            title: Test
            ---

            ## Overview

            This is the overview section with some content here.

            ## Details

            This is the details section with different content.
        """)
        sections = _extract_sections(content)
        assert len(sections) == 2
        assert sections[0][1] == "Overview"
        assert sections[1][1] == "Details"

    def test_code_fence_excluded(self):
        content = textwrap.dedent("""\
            ## Overview

            Some text here.

            ```python
            ## Not a heading
            code = True
            ```

            ## Details

            More text here.
        """)
        sections = _extract_sections(content)
        assert len(sections) == 2
        assert all("Not a heading" not in s[2] for s in sections)

    def test_h3_not_split(self):
        """H3 headings don't create new sections."""
        content = textwrap.dedent("""\
            ## Overview

            Intro text here.

            ### Subsection

            Sub text here.

            ## Details

            Details text here.
        """)
        sections = _extract_sections(content)
        assert len(sections) == 2
        # H3 subsection text goes into the Overview section body
        assert "Sub text here" in sections[0][2]

    def test_empty_content(self):
        sections = _extract_sections("")
        assert sections == []


# ── Section-level duplicate detection ───────────────────────────────────────


class TestSectionRepeatDetection:
    """Verify section-level near-duplicate detection."""

    def _make_md(self, tmp_path: Path, content: str) -> Path:
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")
        return md_file

    def test_near_duplicate_sections_detected(self, tmp_path):
        """Two sections with very similar content trigger G2_SECTION_LEVEL_REPEAT."""
        # Same 40-word content in both sections
        shared = (
            "The library provides extensive support for spreadsheet operations "
            "including reading writing and formatting cells. Users can manipulate "
            "worksheets add formulas and export data to various formats such as "
            "PDF HTML and CSV for downstream processing."
        )
        content = f"## Overview\n\n{shared}\n\n## Summary\n\n{shared}\n"
        md_file = self._make_md(tmp_path, content)
        issues = _scan_sections(content, md_file)
        section_issues = [i for i in issues if i["error_code"] == "G2_SECTION_LEVEL_REPEAT"]
        assert len(section_issues) == 1
        assert "Overview" in section_issues[0]["message"]
        assert "Summary" in section_issues[0]["message"]
        assert section_issues[0]["severity"] == "warning"

    def test_distinct_sections_no_issues(self, tmp_path):
        """Sections with different content produce no issues."""
        content = textwrap.dedent("""\
            ## Overview

            The library handles spreadsheet operations including cell formatting
            formula evaluation and worksheet management across multiple platforms
            with extensive Python bindings for developer convenience.

            ## Installation

            To install the package use pip install from the command line terminal
            ensuring Python version three point eight or higher is available on
            the system path for proper compatibility verification.
        """)
        md_file = self._make_md(tmp_path, content)
        issues = _scan_sections(content, md_file)
        section_issues = [i for i in issues if i["error_code"] == "G2_SECTION_LEVEL_REPEAT"]
        assert len(section_issues) == 0

    def test_short_sections_skipped(self, tmp_path):
        """Sections with fewer than _MIN_SECTION_WORDS are not compared."""
        content = "## A\n\nShort.\n\n## B\n\nShort.\n"
        md_file = self._make_md(tmp_path, content)
        issues = _scan_sections(content, md_file)
        assert len(issues) == 0

    def test_section_issues_are_warnings(self, tmp_path):
        """Section-level issues have severity=warning, not error."""
        shared = (
            "This section describes the comprehensive functionality provided by "
            "the library for handling various data transformation operations on "
            "spreadsheet documents including import export and format conversion "
            "capabilities for enterprise applications."
        )
        content = f"## First\n\n{shared}\n\n## Second\n\n{shared}\n"
        md_file = self._make_md(tmp_path, content)
        issues = _scan_sections(content, md_file)
        for issue in issues:
            assert issue["severity"] == "warning"


# ── Integration: execute_gate with sections ─────────────────────────────────


class TestSectionRepeatIntegration:
    """Verify section-level detection runs as part of execute_gate."""

    def test_section_repeat_in_full_gate(self, tmp_path):
        """execute_gate picks up section-level repeats.

        Note: identical content also triggers paragraph-level errors
        (G2_INTRA_PAGE_REPEAT), so the gate may fail overall. We verify
        that section-level issues are emitted alongside paragraph-level ones.
        """
        run_dir = tmp_path / "run"
        site_dir = run_dir / "work" / "site"
        site_dir.mkdir(parents=True)

        shared = (
            "The framework provides powerful capabilities for data manipulation "
            "and transformation across multiple spreadsheet formats including "
            "reading writing converting and exporting operations with full "
            "support for formulas styles and conditional formatting rules."
        )
        content = f"## Overview\n\n{shared}\n\n## Summary\n\n{shared}\n"
        md_file = site_dir / "test.md"
        md_file.write_text(content, encoding="utf-8")

        _passed, issues = execute_gate(run_dir, "ci")
        # Section-level repeat detected
        section_issues = [i for i in issues if i["error_code"] == "G2_SECTION_LEVEL_REPEAT"]
        assert len(section_issues) >= 1
        # Section issues are warnings (not errors)
        for si in section_issues:
            assert si["severity"] == "warning"

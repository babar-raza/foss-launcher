"""Tests for prose_lead check (TC-PROSE-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.prose_lead import check_prose_lead


class TestProseLead:
    def test_clean_content_passes(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Loading Files\n\n"
            "Load a 3D model from disk using `Scene.from_file()`. "
            "This method accepts OBJ, STL, and glTF formats.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="howto_article")
        assert len(findings) == 0

    def test_generic_library_opener_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "Aspose.3D is a library that enables 3D file processing.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="howto_article")
        assert len(findings) == 1
        assert findings[0].check == "prose_lead"
        assert findings[0].severity == "medium"

    def test_in_this_section_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Features\n\n"
            "In this section we will cover the main features of the library.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="feature_blog")
        assert len(findings) == 1

    def test_when_working_with_flags(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Conversion\n\n"
            "When working with file formats, you may need to convert between them.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="howto_article")
        assert len(findings) == 1

    def test_reference_role_exempt(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "Aspose.3D is a library that does things.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="reference_object_page")
        assert len(findings) == 0

    def test_multiple_sections_each_checked(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Section A\n\n"
            "Aspose.Cells is a tool that processes spreadsheets.\n\n"
            "## Section B\n\n"
            "Load files using the `Workbook` class for efficient processing.\n\n"
            "## Section C\n\n"
            "This section covers the export capabilities.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="howto_article")
        assert len(findings) == 2  # Section A and C flag, B passes

    def test_code_blocks_not_scanned(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Example\n\n"
            "```python\n# Aspose.3D is a library that does stuff\n```\n"
            "This example shows file loading.\n"
        )
        findings = check_prose_lead(content, "test-page", page_role="howto_article")
        assert len(findings) == 0

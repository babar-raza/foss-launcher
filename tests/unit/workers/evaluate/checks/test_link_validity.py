"""TC-D-04: Tests for check_link_validity."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.link_validity import check_link_validity
from launcher.shared.linker import strip_subdomain_prefix


class TestLinkValidity:

    def test_clean_links_pass(self):
        """Valid links should not produce findings."""
        content = (
            "# Guide\n\n"
            "See the [API reference](/reference/api-overview) for details.\n"
            "Visit [PyPI](https://pypi.org/project/aspose-cells-foss/) to install.\n"
        )
        findings = check_link_validity(content, "docs/guide")
        assert findings == []

    def test_example_com_flagged(self):
        """Links to example.com should be flagged."""
        content = "See [docs](https://docs.example.com/guide) for more."
        findings = check_link_validity(content, "docs/guide")
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "example.com" in findings[0].message

    def test_link_to_placeholder_flagged(self):
        """link-to-* placeholder links should be flagged."""
        content = "See [guide](link-to-cells-guide) for details."
        findings = check_link_validity(content, "docs/guide")
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "link-to-" in findings[0].message

    def test_empty_url_flagged(self):
        """Empty URL links should be flagged."""
        content = "See [here]() for more information."
        findings = check_link_validity(content, "docs/guide")
        assert len(findings) == 1
        assert "empty URL" in findings[0].message

    def test_todo_in_url_flagged(self):
        """Links with TODO in URL should be flagged."""
        content = "See [docs](TODO-add-link) for details."
        findings = check_link_validity(content, "docs/guide")
        assert len(findings) == 1
        assert "TODO" in findings[0].message

    def test_links_in_code_blocks_ignored(self):
        """Links inside code blocks should not be flagged."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "# See https://docs.example.com/guide\n"
            "url = 'https://example.com/api'\n"
            "```\n"
        )
        findings = check_link_validity(content, "docs/guide")
        assert findings == []

    def test_multiple_broken_links_capped(self):
        """More than 3 broken links should produce summary finding."""
        content = (
            "[a](https://example.com/1) "
            "[b](https://example.com/2) "
            "[c](https://example.com/3) "
            "[d](https://example.com/4) "
            "[e](https://example.com/5)\n"
        )
        findings = check_link_validity(content, "docs/guide")
        # 3 individual + 1 summary = 4 findings
        assert len(findings) == 4
        summary = [f for f in findings if "5 broken" in f.message]
        assert len(summary) == 1

    def test_your_here_placeholder_flagged(self):
        """your-*-here placeholder links should be flagged."""
        content = "See [config](your-config-here) for setup."
        findings = check_link_validity(content, "docs/guide")
        assert len(findings) == 1

    def test_hash_only_url_flagged(self):
        """Links with only # as URL should be flagged."""
        content = "See [section](#) for details."
        findings = check_link_validity(content, "docs/guide")
        assert len(findings) == 1
        assert "empty URL" in findings[0].message

    def test_subdomain_prefix_in_url_flagged(self):
        """SR-06 / TC-LINK-01: URLs with subdomain prefix in path are flagged."""
        content = "See the [FAQ](/kb.aspose.org/cells/python/faq/) for answers."
        findings = check_link_validity(content, "docs/guide")
        subdomain_findings = [f for f in findings if "subdomain prefix" in f.message]
        assert len(subdomain_findings) == 1
        assert subdomain_findings[0].severity == "high"

    def test_clean_site_relative_url_passes(self):
        """SR-06: Clean site-relative URLs without subdomain prefix pass."""
        content = "See the [FAQ](/cells/python/faq/) for answers."
        findings = check_link_validity(content, "docs/guide")
        assert findings == []

    def test_frontmatter_not_checked(self):
        """Frontmatter links should not be checked."""
        content = (
            "---\ntitle: Test\nurl: https://example.com\n---\n"
            "# Guide\n\nNormal content with [valid link](/docs).\n"
        )
        # Frontmatter is stripped before checking
        findings = check_link_validity(content, "docs/guide")
        assert findings == []


class TestStripSubdomainPrefix:
    """SR-06 / TC-LINK-01: Unit tests for strip_subdomain_prefix."""

    def test_strips_kb_prefix(self):
        assert strip_subdomain_prefix("/kb.aspose.org/cells/python/faq/") == "/cells/python/faq/"

    def test_strips_docs_prefix(self):
        assert strip_subdomain_prefix("/docs.aspose.org/3d/python/install/") == "/3d/python/install/"

    def test_strips_reference_prefix(self):
        assert strip_subdomain_prefix("/reference.aspose.org/cells/python/workbook/") == "/cells/python/workbook/"

    def test_passthrough_clean_url(self):
        assert strip_subdomain_prefix("/cells/python/faq/") == "/cells/python/faq/"

    def test_passthrough_absolute_url(self):
        assert strip_subdomain_prefix("https://kb.aspose.org/cells/") == "https://kb.aspose.org/cells/"

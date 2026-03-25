"""Tests for contract_compliance check (TC-PQ-CC)."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.contract_compliance import check_contract_compliance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _md(body: str, page_role: str = "howto_article") -> str:
    """Wrap body in minimal frontmatter."""
    return f"---\ntitle: Test\npage_role: {page_role}\n---\n{body}"


# ---------------------------------------------------------------------------
# Product-definition opening (all non-reference roles)
# ---------------------------------------------------------------------------

class TestProductDefOpening:
    """Rule: first paragraph must not be a product definition."""

    def test_fires_on_product_definition(self):
        content = _md("Aspose.Cells is a library that provides spreadsheet processing.")
        findings = check_contract_compliance(content, "test-slug", page_role="howto_article")
        assert any(f.check == "contract_compliance" for f in findings)

    def test_fires_on_product_definition_with_backticks(self):
        content = _md("`Aspose.Cells` is a tool for processing spreadsheets.")
        findings = check_contract_compliance(content, "test-slug", page_role="workflow_page")
        assert any(f.check == "contract_compliance" for f in findings)

    def test_fires_on_the_prefix(self):
        content = _md("The Aspose.Cells is a package that enables spreadsheet work.")
        findings = check_contract_compliance(content, "test-slug", page_role="landing")
        assert any(f.check == "contract_compliance" for f in findings)

    def test_does_not_fire_on_task_opening(self):
        content = _md("This guide walks you through converting Excel to PDF.")
        findings = check_contract_compliance(content, "test-slug", page_role="howto_article")
        product_def = [f for f in findings if "product definition" in f.message]
        assert not product_def

    def test_exempt_for_api_reference(self):
        content = _md("Aspose.Cells is a library that provides spreadsheet processing.")
        findings = check_contract_compliance(content, "test-slug", page_role="api_reference")
        assert not findings

    def test_exempt_for_reference_object_page(self):
        content = _md("Aspose.Cells is a library that provides spreadsheet processing.")
        findings = check_contract_compliance(content, "test-slug", page_role="reference_object_page")
        assert not findings

    def test_exempt_for_toc(self):
        content = _md("Aspose.Cells is a library that provides spreadsheet processing.")
        findings = check_contract_compliance(content, "test-slug", page_role="toc")
        assert not findings


# ---------------------------------------------------------------------------
# FAQ Q&A structure
# ---------------------------------------------------------------------------

class TestFaqStructure:
    """Rule: FAQ H3 headings should be questions."""

    def test_fires_when_headings_are_not_questions(self):
        content = _md(
            "## FAQ\n\n"
            "### Excel Conversion\n\nSome answer.\n\n"
            "### File Loading\n\nAnother answer.\n\n"
            "### Data Export\n\nYet another answer.\n",
            page_role="faq",
        )
        findings = check_contract_compliance(content, "test-slug", page_role="faq")
        faq_findings = [f for f in findings if "FAQ" in f.message]
        assert faq_findings

    def test_does_not_fire_when_headings_are_questions(self):
        content = _md(
            "## FAQ\n\n"
            "### How do I convert Excel to PDF?\n\nUse Workbook.save().\n\n"
            "### What formats are supported?\n\nXLSX, CSV, ODS.\n",
            page_role="faq",
        )
        findings = check_contract_compliance(content, "test-slug", page_role="faq")
        faq_findings = [f for f in findings if "FAQ" in f.message]
        assert not faq_findings

    def test_tolerates_structural_headings(self):
        """Structural headings like 'See Also' should not count."""
        content = _md(
            "## FAQ\n\n"
            "### How do I save a file?\n\nUse save().\n\n"
            "### See Also\n\nRelated docs.\n",
            page_role="faq",
        )
        findings = check_contract_compliance(content, "test-slug", page_role="faq")
        faq_findings = [f for f in findings if "FAQ" in f.message]
        assert not faq_findings

    def test_not_applied_to_non_faq_roles(self):
        content = _md(
            "### Some Heading\n\nContent.\n\n### Another\n\nMore content.\n",
            page_role="howto_article",
        )
        findings = check_contract_compliance(content, "test-slug", page_role="howto_article")
        faq_findings = [f for f in findings if "FAQ" in f.message]
        assert not faq_findings


# ---------------------------------------------------------------------------
# Blog announcement opening
# ---------------------------------------------------------------------------

class TestBlogOpening:
    """Rule: blog posts must not open with the product name."""

    def test_fires_on_product_name_opening(self):
        content = _md("Aspose.Cells provides spreadsheet processing capabilities.")
        findings = check_contract_compliance(
            content, "test-slug", page_role="blog_announcement", product_name="Aspose.Cells",
        )
        blog_findings = [f for f in findings if "Blog" in f.message]
        assert blog_findings

    def test_fires_on_backticked_product_name(self):
        content = _md("`Aspose.Cells` enables high-performance Excel processing.")
        findings = check_contract_compliance(
            content, "test-slug", page_role="blog_announcement", product_name="Aspose.Cells",
        )
        blog_findings = [f for f in findings if "Blog" in f.message]
        assert blog_findings

    def test_does_not_fire_on_problem_first_opening(self):
        content = _md("Converting spreadsheets to PDF usually requires a heavy dependency.")
        findings = check_contract_compliance(
            content, "test-slug", page_role="blog_announcement", product_name="Aspose.Cells",
        )
        blog_findings = [f for f in findings if "Blog" in f.message]
        assert not blog_findings

    def test_applies_to_feature_blog(self):
        content = _md("Aspose.Cells offers chart creation features.")
        findings = check_contract_compliance(
            content, "test-slug", page_role="feature_blog", product_name="Aspose.Cells",
        )
        blog_findings = [f for f in findings if "Blog" in f.message]
        assert blog_findings


# ---------------------------------------------------------------------------
# Code presence for workflow/howto
# ---------------------------------------------------------------------------

class TestCodePresence:
    """Rule: workflow/howto pages must have code blocks."""

    def test_fires_when_no_code_blocks(self):
        # >100 words, no code blocks
        long_text = " ".join(["This is a sentence about processing."] * 20)
        content = _md(long_text, page_role="workflow_page")
        findings = check_contract_compliance(content, "test-slug", page_role="workflow_page")
        code_findings = [f for f in findings if "code" in f.message.lower()]
        assert code_findings

    def test_does_not_fire_when_code_present(self):
        content = _md(
            "## Steps\n\nHere is how:\n\n```python\nimport aspose\nwb = aspose.Workbook()\n```\n\nDone.",
            page_role="workflow_page",
        )
        findings = check_contract_compliance(content, "test-slug", page_role="workflow_page")
        code_findings = [f for f in findings if "no code" in f.message.lower()]
        assert not code_findings

    def test_not_applied_to_faq(self):
        long_text = " ".join(["This is a sentence about processing."] * 20)
        content = _md(long_text, page_role="faq")
        findings = check_contract_compliance(content, "test-slug", page_role="faq")
        code_findings = [f for f in findings if "code" in f.message.lower() and "workflow" in f.message.lower()]
        assert not code_findings


# ---------------------------------------------------------------------------
# Severity and metadata
# ---------------------------------------------------------------------------

class TestFindingMetadata:
    """Verify findings have correct severity and check name."""

    def test_severity_is_medium(self):
        content = _md("Aspose.Cells is a library that provides spreadsheet processing.")
        findings = check_contract_compliance(content, "test-slug", page_role="howto_article")
        for f in findings:
            assert f.severity == "medium"
            assert f.check == "contract_compliance"

    def test_location_is_slug(self):
        content = _md("Aspose.Cells is a library that provides spreadsheet processing.")
        findings = check_contract_compliance(content, "my-page", page_role="howto_article")
        for f in findings:
            assert f.location == "my-page"

    def test_empty_content_returns_no_findings(self):
        findings = check_contract_compliance("", "test-slug", page_role="howto_article")
        assert findings == []

    def test_short_content_no_code_check(self):
        """Very short pages should not trigger code-absence warning."""
        content = _md("Quick note.", page_role="workflow_page")
        findings = check_contract_compliance(content, "test-slug", page_role="workflow_page")
        code_findings = [f for f in findings if "no code" in f.message.lower()]
        assert not code_findings

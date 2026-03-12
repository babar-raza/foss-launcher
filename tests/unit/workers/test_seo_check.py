"""Tests for enhanced SEO checks (TC-3811)."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.seo import check_seo


def _make_content(**fm_overrides) -> str:
    """Build content string with frontmatter."""
    fm = {
        "title": "Getting Started with Aspose.Cells",
        "description": "A comprehensive guide to using Aspose.Cells for spreadsheet processing in Python applications.",
        "slug": "getting-started",
        "url": "/docs/cells/python/getting-started/",
        "seoTitle": "Aspose.Cells Getting Started | Guide",
        "canonical": "https://docs.aspose.org/cells/python/getting-started/",
        "robots": "index, follow",
        "keywords": ["python", "excel", "spreadsheets", "aspose"],
    }
    fm.update(fm_overrides)

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f'{k}: "{v}"' if isinstance(v, str) else f"{k}: {v}")
    lines.append("---")
    lines.append("\n## Overview\n\nSome content here.")
    return "\n".join(lines)


class TestSeoTitleChecks:
    def test_missing_seo_title(self):
        content = _make_content(seoTitle="")
        findings = check_seo(content, "getting-started")
        assert any("Missing seoTitle" in f.message for f in findings)

    def test_seo_title_too_long(self):
        content = _make_content(seoTitle="A" * 65)
        findings = check_seo(content, "getting-started")
        assert any("seoTitle too long" in f.message for f in findings)

    def test_seo_title_same_as_title(self):
        content = _make_content(
            title="Same Title", seoTitle="Same Title",
        )
        findings = check_seo(content, "getting-started")
        assert any("identical to title" in f.message for f in findings)

    def test_valid_seo_title_no_findings(self):
        content = _make_content()
        findings = check_seo(content, "getting-started")
        seo_title_findings = [f for f in findings if "seoTitle" in f.message]
        assert len(seo_title_findings) == 0

    def test_index_page_skips_seo_title(self):
        content = _make_content(seoTitle="", slug="_index")
        findings = check_seo(content, "_index")
        assert not any("Missing seoTitle" in f.message for f in findings)


class TestCanonicalChecks:
    def test_missing_canonical(self):
        content = _make_content(canonical="")
        findings = check_seo(content, "getting-started")
        assert any("Missing canonical" in f.message for f in findings)

    def test_non_https_canonical(self):
        content = _make_content(canonical="http://docs.aspose.org/cells/")
        findings = check_seo(content, "getting-started")
        assert any("not HTTPS" in f.message for f in findings)
        assert any(f.severity == "high" for f in findings if "HTTPS" in f.message)

    def test_valid_canonical_no_findings(self):
        content = _make_content()
        findings = check_seo(content, "getting-started")
        canonical_findings = [f for f in findings if "canonical" in f.message.lower()]
        assert len(canonical_findings) == 0

    def test_index_page_skips_canonical(self):
        content = _make_content(canonical="", slug="_index")
        findings = check_seo(content, "_index")
        assert not any("canonical" in f.message.lower() for f in findings)


class TestRobotsCheck:
    def test_missing_robots(self):
        content = _make_content(robots="")
        findings = check_seo(content, "getting-started")
        assert any("Missing robots" in f.message for f in findings)

    def test_present_robots_no_findings(self):
        content = _make_content()
        findings = check_seo(content, "getting-started")
        assert not any("robots" in f.message.lower() for f in findings)


class TestKeywordChecks:
    def test_too_few_keywords(self):
        content = _make_content(keywords=["python"])
        findings = check_seo(content, "getting-started")
        assert any("Too few keywords" in f.message for f in findings)

    def test_enough_keywords_no_findings(self):
        content = _make_content()
        findings = check_seo(content, "getting-started")
        assert not any("Too few keywords" in f.message for f in findings)

    def test_index_page_skips_keyword_check(self):
        content = _make_content(keywords=[], slug="_index")
        findings = check_seo(content, "_index")
        assert not any("Too few keywords" in f.message for f in findings)


class TestTemplateDescriptionDetection:
    def test_template_description_detected(self):
        content = _make_content(
            title="Getting Started",
            description="Getting Started for Aspose.Cells for Python",
        )
        findings = check_seo(
            content, "getting-started",
            product_name="Aspose.Cells for Python",
        )
        assert any("template-generated" in f.message for f in findings)

    def test_real_description_not_flagged(self):
        content = _make_content()
        findings = check_seo(
            content, "getting-started",
            product_name="Aspose.Cells for Python",
        )
        assert not any("template-generated" in f.message for f in findings)


class TestHtmlEntityDetection:
    def test_entity_in_title(self):
        content = _make_content(title="Windows&reg; Spreadsheets")
        findings = check_seo(content, "getting-started")
        assert any("HTML entity in title" in f.message for f in findings)
        assert any(
            f.severity == "high"
            for f in findings
            if "HTML entity" in f.message
        )

    def test_entity_in_description(self):
        content = _make_content(
            description="Use &amp; to concatenate strings in your spreadsheet application processing workflow.",
        )
        findings = check_seo(content, "getting-started")
        assert any("HTML entity in description" in f.message for f in findings)

    def test_clean_fields_no_entity_findings(self):
        content = _make_content()
        findings = check_seo(content, "getting-started")
        assert not any("HTML entity" in f.message for f in findings)


class TestKeywordBodyPresence:
    def test_keyword_found_in_body_no_finding(self):
        content = _make_content(keywords=["overview", "spreadsheet"])
        # Body contains "Some content here" — no keyword match, but let's use "content"
        content2 = _make_content(keywords=["content"])
        findings = check_seo(content2, "getting-started")
        assert not any("No keywords found in page body" in f.message for f in findings)

    def test_keyword_missing_from_body(self):
        content = _make_content(keywords=["nonexistent", "missing", "absent"])
        findings = check_seo(content, "getting-started")
        assert any("No keywords found in page body" in f.message for f in findings)

    def test_keyword_check_skipped_for_index(self):
        content = _make_content(keywords=["nonexistent"], slug="_index")
        findings = check_seo(content, "_index")
        assert not any("No keywords found in page body" in f.message for f in findings)

    def test_keyword_check_case_insensitive(self):
        content = _make_content(keywords=["Overview"])
        findings = check_seo(content, "getting-started")
        # Body has "Overview" heading — case insensitive match should find it
        assert not any("No keywords found in page body" in f.message for f in findings)


class TestAnchorTextChecks:
    """SEO-19: anchor text optimization — generic anchors flagged."""

    def _content_with_body(self, body_line: str) -> str:
        fm = _make_content()
        return fm + f"\n{body_line}\n"

    def test_generic_anchor_click_here_flagged(self):
        content = self._content_with_body("[click here](https://example.com)")
        findings = check_seo(content, "getting-started")
        assert any("Generic anchor text" in f.message for f in findings)
        anchor_f = next(f for f in findings if "Generic anchor text" in f.message)
        assert anchor_f.severity == "medium"

    def test_generic_anchor_here_flagged(self):
        content = self._content_with_body("[here](https://example.com)")
        findings = check_seo(content, "getting-started")
        assert any("Generic anchor text" in f.message for f in findings)

    def test_descriptive_anchor_no_finding(self):
        content = self._content_with_body("[Install the Aspose.Cells SDK](https://example.com)")
        findings = check_seo(content, "getting-started")
        assert not any("Generic anchor text" in f.message for f in findings)

    def test_index_page_skips_anchor_check(self):
        content = self._content_with_body("[click here](https://example.com)")
        findings = check_seo(content, "_index")
        assert not any("Generic anchor text" in f.message for f in findings)

    def test_anchor_in_code_block_not_flagged(self):
        body = "```markdown\n[click here](https://example.com)\n```"
        content = _make_content() + f"\n{body}\n"
        findings = check_seo(content, "getting-started")
        assert not any("Generic anchor text" in f.message for f in findings)


class TestFullSeoCompliance:
    def test_fully_compliant_page(self):
        content = _make_content()
        findings = check_seo(
            content, "getting-started",
            product_name="Aspose.Cells for Python",
        )
        high = [f for f in findings if f.severity in ("critical", "high")]
        assert len(high) == 0
        medium = [f for f in findings if f.severity == "medium"]
        assert len(medium) == 0

"""Tests for deterministic dimension checkers (TC-2534).

Tests cover all 9 deterministic dimensions (RD-02 through RD-08, RD-10, RD-12)
with at least 2 tests per dimension: good content (high score) and bad content
(low score).
"""

from __future__ import annotations

import pytest

from launch.review.dimensions.deterministic import (
    check_claim_coverage,
    check_code_fence_integrity,
    check_contradiction,
    check_heading_hierarchy,
    check_link_integrity,
    check_prompt_leak,
    check_seo_meta,
    check_slug_quality,
    check_structure_compliance,
)
from launch.review.rubric import DimensionResult


# ── RD-02: Contradiction ──────────────────────────────────────────────────

class TestContradiction:
    """RD-02: Cross-page version/name mismatches."""

    def test_no_contradictions(self):
        pages = [
            {"path": "a.md", "content": "Use Python 3.10 for this."},
            {"path": "b.md", "content": "Requires Python 3.10 or later."},
        ]
        result = check_contradiction(pages)
        assert isinstance(result, DimensionResult)
        assert result.dimension_id == "RD-02"
        assert result.score >= 8

    def test_version_contradiction(self):
        pages = [
            {"path": "a.md", "content": "Use Python 3.10 for this."},
            {"path": "b.md", "content": "Requires Python 3.8 or later."},
        ]
        result = check_contradiction(pages)
        assert result.score < 10
        assert any("Python versions" in i.message for i in result.issues)

    def test_package_name_variants(self):
        pages = [
            {"path": "a.md", "content": "Run: pip install aspose-cells"},
            {"path": "b.md", "content": "Run: pip install aspose_cells"},
        ]
        result = check_contradiction(pages)
        assert result.score < 10
        assert any("Package name variants" in i.message for i in result.issues)

    def test_empty_pages(self):
        result = check_contradiction([])
        assert result.score == 10
        assert result.issues == []

    def test_shared_facts_contradiction(self):
        pages = [
            {"path": "a.md", "content": "Requires Python 3.6 minimum."},
        ]
        shared_facts = {"min_python_version": "3.8"}
        result = check_contradiction(pages, shared_facts)
        assert result.score < 10
        assert any("contradicts canonical" in i.message for i in result.issues)


# ── RD-03: Slug quality ──────────────────────────────────────────────────

class TestSlugQuality:
    """RD-03: SEO-friendliness checks."""

    def test_good_slug(self):
        result = check_slug_quality("convert-pdf-to-excel-python")
        assert result.dimension_id == "RD-03"
        assert result.score >= 8
        assert result.issues == []

    def test_empty_slug(self):
        result = check_slug_quality("")
        assert result.score == 0

    def test_uppercase_slug(self):
        result = check_slug_quality("Convert-PDF")
        assert result.score < 10
        assert any("uppercase" in i.message for i in result.issues)

    def test_consecutive_hyphens(self):
        result = check_slug_quality("convert--pdf--to")
        assert result.score < 10

    def test_too_short(self):
        result = check_slug_quality("ab")
        assert result.score < 10
        assert any("too short" in i.message for i in result.issues)

    def test_special_characters(self):
        result = check_slug_quality("convert pdf!")
        assert result.score < 10


# ── RD-04: Code fence integrity ──────────────────────────────────────────

class TestCodeFenceIntegrity:
    """RD-04: Code fence closure and language tags."""

    def test_good_fences(self):
        content = "# Title\n\n```python\nprint('hello')\n```\n\nText."
        result = check_code_fence_integrity(content)
        assert result.dimension_id == "RD-04"
        assert result.score == 10

    def test_unclosed_fence(self):
        content = "# Title\n\n```python\nprint('hello')\n\nText continues."
        result = check_code_fence_integrity(content)
        assert result.score < 10
        assert any("Unclosed" in i.message for i in result.issues)

    def test_missing_language_tag(self):
        content = "# Title\n\n```\nprint('hello')\n```\n"
        result = check_code_fence_integrity(content)
        assert result.score < 10
        assert any("language tag" in i.message for i in result.issues)

    def test_empty_code_block(self):
        content = "# Title\n\n```python\n```\n"
        result = check_code_fence_integrity(content)
        assert result.score < 10
        assert any("Empty" in i.message for i in result.issues)


# ── RD-05: Prompt leak ───────────────────────────────────────────────────

class TestPromptLeak:
    """RD-05: System prompt fragments in output."""

    def test_clean_content(self):
        content = "# Getting Started\n\nLearn how to use the library.\n"
        result = check_prompt_leak(content)
        assert result.dimension_id == "RD-05"
        assert result.score == 10

    def test_prompt_leak_you_are(self):
        content = "# Title\n\nYou are a helpful assistant. Here is the guide.\n"
        result = check_prompt_leak(content)
        assert result.score == 0
        assert any("Prompt leak" in i.message for i in result.issues)

    def test_prompt_leak_claim_marker(self):
        content = "# Title\n\nThis feature [[CLAIM_123]] is great.\n"
        result = check_prompt_leak(content)
        assert result.score == 0

    def test_prompt_leak_in_code_fence_ignored(self):
        content = "# Title\n\n```python\n# You are a developer\nprint('hello')\n```\n"
        result = check_prompt_leak(content)
        assert result.score == 10  # Should not flag inside code fences

    def test_prompt_leak_formatting_rules(self):
        content = "# Title\n\n## FORMATTING RULES\n\nDo this and that.\n"
        result = check_prompt_leak(content)
        assert result.score == 0


# ── RD-06: Structure compliance ──────────────────────────────────────────

class TestStructureCompliance:
    """RD-06: Required sections present."""

    def test_all_sections_present(self):
        content = (
            "# My Blog\n\n"
            "## Introduction\n\nHello.\n\n"
            "## Main Content\n\nBody text.\n\n"
            "## Conclusion\n\nGoodbye.\n"
        )
        result = check_structure_compliance(content, "blog")
        assert result.dimension_id == "RD-06"
        assert result.score >= 8

    def test_missing_sections(self):
        content = "# My Blog\n\n## Introduction\n\nHello.\n"
        result = check_structure_compliance(content, "blog")
        assert result.score < 10
        assert any("not found" in i.message for i in result.issues)

    def test_unknown_role_uses_default(self):
        content = "# Title\n\n## Introduction\n\n## Main Content\n"
        result = check_structure_compliance(content, "nonexistent_role")
        assert result.dimension_id == "RD-06"
        # Should use default template


# ── RD-07: Heading hierarchy ─────────────────────────────────────────────

class TestHeadingHierarchy:
    """RD-07: H1->H2->H3 monotonic descent."""

    def test_good_hierarchy(self):
        content = "# Title\n\n## Section\n\n### Subsection\n\n## Another\n"
        result = check_heading_hierarchy(content)
        assert result.dimension_id == "RD-07"
        assert result.score == 10

    def test_skipped_level(self):
        content = "# Title\n\n### Subsection\n\nSkipped H2.\n"
        result = check_heading_hierarchy(content)
        assert result.score < 10
        assert any("skip" in i.message.lower() for i in result.issues)

    def test_no_headings(self):
        content = "Just plain text here.\n"
        result = check_heading_hierarchy(content)
        assert result.score == 10

    def test_multiple_skips(self):
        content = "# Title\n\n#### Deep\n\n###### Very Deep\n"
        result = check_heading_hierarchy(content)
        assert result.score < 5  # Multiple skips should lower score significantly


# ── RD-08: Claim coverage ────────────────────────────────────────────────

class TestClaimCoverage:
    """RD-08: Percentage of assigned claims used."""

    def test_all_claims_present(self):
        content = "This page covers C-001 and C-002 and C-003.\n"
        result = check_claim_coverage(content, ["C-001", "C-002", "C-003"])
        assert result.dimension_id == "RD-08"
        assert result.score == 10

    def test_missing_claims(self):
        content = "This page only mentions C-001.\n"
        result = check_claim_coverage(content, ["C-001", "C-002", "C-003"])
        assert result.score < 10
        assert any("C-002" in i.message for i in result.issues)
        assert any("C-003" in i.message for i in result.issues)

    def test_no_assigned_claims(self):
        content = "Some content.\n"
        result = check_claim_coverage(content, [])
        assert result.score == 10

    def test_no_assigned_claims_none(self):
        content = "Some content.\n"
        result = check_claim_coverage(content, None)
        assert result.score == 10


# ── RD-10: SEO title/meta ────────────────────────────────────────────────

class TestSeoMeta:
    """RD-10: Frontmatter title/description/keywords."""

    def test_complete_frontmatter(self):
        content = (
            "---\n"
            "title: \"Convert PDF to Excel in Python - Complete Guide\"\n"
            "description: \"Learn how to convert PDF files to Excel spreadsheets using Python with this comprehensive step-by-step guide.\"\n"
            "keywords: \"python, pdf, excel, convert, aspose, spreadsheet\"\n"
            "---\n\n"
            "# Title\n"
        )
        result = check_seo_meta(content)
        assert result.dimension_id == "RD-10"
        assert result.score >= 8

    def test_missing_frontmatter(self):
        content = "# Title\n\nNo frontmatter here.\n"
        result = check_seo_meta(content)
        assert result.score < 5

    def test_title_too_short(self):
        content = (
            "---\n"
            "title: \"Short\"\n"
            "description: \"A decent description that is long enough to pass the minimum length check here.\"\n"
            "keywords: \"a, b, c\"\n"
            "---\n\n"
            "# Title\n"
        )
        result = check_seo_meta(content)
        assert result.score < 10  # Title too short


# ── RD-12: Link integrity ────────────────────────────────────────────────

class TestLinkIntegrity:
    """RD-12: No broken internal cross-references."""

    def test_all_links_valid(self):
        content = "See [Guide](getting-started) and [API](api-reference).\n"
        known = {"getting-started", "api-reference"}
        result = check_link_integrity(content, known)
        assert result.dimension_id == "RD-12"
        assert result.score == 10

    def test_broken_link(self):
        content = "See [Guide](missing-page).\n"
        known = {"getting-started", "api-reference"}
        result = check_link_integrity(content, known)
        assert result.score < 10
        assert any("Broken" in i.message for i in result.issues)

    def test_external_links_ignored(self):
        content = "See [Google](https://google.com) and [Mail](mailto:a@b.c).\n"
        known: set = set()
        result = check_link_integrity(content, known)
        assert result.score == 10

    def test_empty_known_pages(self):
        content = "See [Guide](some-page).\n"
        result = check_link_integrity(content, None)
        # With no known pages set, we can't verify links -- should not penalize
        assert result.score == 10

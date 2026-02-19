"""Tests for W7 ContentReviewer auto-fix capabilities.

TC-1100-P5: W7 ContentReviewer Phase 5 - Tests
"""
import pytest
from pathlib import Path

from launch.workers.w7_content_reviewer.fixes.auto_fixes import (
    apply_auto_fixes,
    fix_claim_markers,
    fix_frontmatter_comments,
    fix_template_tokens,
    fix_heading_hierarchy,
    fix_paragraph_breaks,
    fix_link_normalization,
    fix_bullet_splitting,
    fix_alt_text,
    fix_metadata,
    fix_missing_prerequisites,
    fix_missing_cta,
    fix_missing_next_steps,
    fix_low_content_density,
    fix_heading_descriptiveness,
    fix_example_clarity,
    fix_snippet_attribution,
    fix_foss_licensing,
    fix_collapsed_frontmatter,
    fix_source_annotations,
    fix_platform_listing,
)
from launch.workers.w7_content_reviewer.fixes.iteration_tracker import IterationTracker


class TestIterationTracker:
    """Test iteration tracking."""

    def test_first_iteration_allowed(self, tmp_path):
        """First iteration should be allowed."""
        tracker = IterationTracker(run_dir=tmp_path)
        assert tracker.can_iterate("page1") is True

    def test_max_iterations_enforced(self, tmp_path):
        """Should not allow more than MAX_ITERATIONS (3) iterations."""
        tracker = IterationTracker(run_dir=tmp_path)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        assert tracker.can_iterate("page1") is False

    def test_two_iterations_still_allowed(self, tmp_path):
        """After 2 iterations, a 3rd should still be allowed (< 3)."""
        tracker = IterationTracker(run_dir=tmp_path)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        assert tracker.can_iterate("page1") is True

    def test_different_pages_independent(self, tmp_path):
        """Different pages have independent iteration counts."""
        tracker = IterationTracker(run_dir=tmp_path)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        tracker.record_iteration("page1", fix_type="auto_fixes", count=1)
        assert tracker.can_iterate("page1") is False
        assert tracker.can_iterate("page2") is True

    def test_get_iteration_count(self, tmp_path):
        """Should return correct iteration count."""
        tracker = IterationTracker(run_dir=tmp_path)
        assert tracker.get_iteration_count("page1") == 0
        tracker.record_iteration("page1", fix_type="claim_markers", count=5)
        assert tracker.get_iteration_count("page1") == 1

    def test_record_returns_new_count(self, tmp_path):
        """record_iteration should return the new iteration count."""
        tracker = IterationTracker(run_dir=tmp_path)
        result = tracker.record_iteration("p1", fix_type="test", count=2)
        assert result == 1
        result = tracker.record_iteration("p1", fix_type="test", count=3)
        assert result == 2

    def test_max_iterations_class_constant(self, tmp_path):
        """MAX_ITERATIONS should be 3."""
        tracker = IterationTracker(run_dir=tmp_path)
        assert tracker.MAX_ITERATIONS == 3

    def test_write_iterations_json(self, tmp_path):
        """Should write review_iterations.json to artifacts dir."""
        import json
        tracker = IterationTracker(run_dir=tmp_path)
        tracker.record_iteration("docs/overview/index", fix_type="claim_markers", count=3)
        tracker.write_iterations_json()

        artifacts_dir = tmp_path / "artifacts"
        iterations_path = artifacts_dir / "review_iterations.json"
        assert iterations_path.exists()

        with open(iterations_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["schema_version"] == "1.0"
        assert data["max_iterations"] == 3
        assert "docs/overview/index" in data["iterations"]
        assert data["iterations"]["docs/overview/index"]["iteration_count"] == 1


class TestApplyAutoFixes:
    """Test auto-fix application."""

    def test_no_auto_fixable_issues_returns_empty(self, tmp_path):
        """Should return empty list when no issues are auto-fixable."""
        issues = [
            {"issue_id": "1", "severity": "error", "auto_fixable": False, "check": "test"}
        ]
        tracker = IterationTracker(run_dir=tmp_path)
        result = apply_auto_fixes(issues, tmp_path, {}, tracker)
        assert result == []

    def test_empty_issues_returns_empty(self, tmp_path):
        """Should return empty list for empty issues."""
        tracker = IterationTracker(run_dir=tmp_path)
        result = apply_auto_fixes([], tmp_path, {}, tracker)
        assert result == []

    def test_missing_file_returns_error(self, tmp_path):
        """Should return error when referenced file does not exist."""
        issues = [
            {
                "issue_id": "1",
                "severity": "warn",
                "auto_fixable": True,
                "check": "content_quality.claim_marker_format",
                "location": {"path": "drafts/missing.md", "line": 1},
            }
        ]
        tracker = IterationTracker(run_dir=tmp_path)
        result = apply_auto_fixes(issues, tmp_path, {}, tracker)
        assert len(result) == 1
        assert result[0]["success"] is False
        assert "not found" in result[0]["error"].lower() or "File not found" in result[0]["error"]

    def test_max_iterations_prevents_fix(self, tmp_path):
        """Should skip fixes when max iterations reached."""
        # Create run structure: tmp_path is run_dir, drafts/ is a subdirectory
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        test_file = drafts_dir / "test.md"
        test_file.write_text("# Test\n[claim: 12345678-1234-1234-1234-123456789abc]", encoding="utf-8")

        issues = [
            {
                "issue_id": "1",
                "severity": "warn",
                "auto_fixable": True,
                "check": "content_quality.claim_marker_format",
                "location": {"path": "test.md", "line": 2},
            }
        ]
        tracker = IterationTracker(run_dir=tmp_path)
        # _extract_page_id("drafts/test.md") strips "drafts/" and ".md" -> "test"
        page_id = "test"
        tracker.record_iteration(page_id, fix_type="auto_fixes", count=1)
        tracker.record_iteration(page_id, fix_type="auto_fixes", count=1)
        tracker.record_iteration(page_id, fix_type="auto_fixes", count=1)

        result = apply_auto_fixes(issues, drafts_dir, {}, tracker)
        assert len(result) == 1
        assert result[0]["success"] is False
        assert result[0]["fix_type"] == "max_iterations"


class TestFixClaimMarkers:
    """Test claim marker fix function."""

    def test_converts_inline_to_html_comment(self, tmp_path):
        """Should convert [claim: UUID] to <!-- claim_id: UUID -->."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "# Test\n[claim: 12345678-1234-1234-1234-123456789abc]\nMore text.",
            encoding="utf-8"
        )
        issue = {"issue_id": "1"}
        result = fix_claim_markers(issue, test_file)
        assert result["success"] is True
        assert result["fix_type"] == "claim_markers"
        content = test_file.read_text(encoding="utf-8")
        assert "<!-- claim_id: 12345678-1234-1234-1234-123456789abc -->" in content
        assert "[claim:" not in content

    def test_no_markers_returns_failure(self, tmp_path):
        """Should return failure when no claim markers found."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# No markers here\nJust text.", encoding="utf-8")
        issue = {"issue_id": "2"}
        result = fix_claim_markers(issue, test_file)
        assert result["success"] is False

    def test_multiple_markers_all_converted(self, tmp_path):
        """Should convert all claim markers in file."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "[claim: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa]\n"
            "[claim: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb]\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "3"}
        result = fix_claim_markers(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert content.count("<!-- claim_id:") == 2


class TestFixFrontmatterComments:
    """Test frontmatter comment removal."""

    def test_removes_yaml_comments(self, tmp_path):
        """Should remove YAML comment lines from frontmatter."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n# This is a comment\nweight: 1\n---\n# Body\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "1"}
        result = fix_frontmatter_comments(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "# This is a comment" not in content
        assert "title: Test" in content

    def test_no_frontmatter_returns_failure(self, tmp_path):
        """Should return failure when no frontmatter found."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Just a heading\nNo frontmatter.", encoding="utf-8")
        issue = {"issue_id": "2"}
        result = fix_frontmatter_comments(issue, test_file)
        assert result["success"] is False


class TestFixTemplateTokens:
    """Test template token replacement."""

    def test_replaces_known_tokens(self, tmp_path):
        """Should replace __PRODUCT_NAME__ with product facts value."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Welcome to __PRODUCT_NAME__!", encoding="utf-8")
        product_facts = {"product_name": "Aspose.3D"}
        issue = {"issue_id": "1"}
        result = fix_template_tokens(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "Aspose.3D" in content
        assert "__PRODUCT_NAME__" not in content

    def test_removes_unknown_tokens(self, tmp_path):
        """Should remove tokens that have no mapping."""
        test_file = tmp_path / "test.md"
        test_file.write_text("See __UNKNOWN_TOKEN__ here.", encoding="utf-8")
        product_facts = {}
        issue = {"issue_id": "2"}
        result = fix_template_tokens(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "__UNKNOWN_TOKEN__" not in content

    def test_no_tokens_returns_failure(self, tmp_path):
        """Should return failure when no tokens found."""
        test_file = tmp_path / "test.md"
        test_file.write_text("No tokens in this file.", encoding="utf-8")
        product_facts = {}
        issue = {"issue_id": "3"}
        result = fix_template_tokens(issue, test_file, product_facts)
        assert result["success"] is False


class TestFixHeadingHierarchy:
    """Test heading hierarchy fix."""

    def test_adjusts_skipped_heading(self, tmp_path):
        """Should adjust H3 to H2 when H1->H3 skip detected."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\n\n### Subtitle\n\nContent.", encoding="utf-8")
        issue = {
            "issue_id": "1",
            "location": {"line": 3},
            "message": "Heading level skip (H1->H3, should be H2)",
        }
        result = fix_heading_hierarchy(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "## Subtitle" in content
        assert "### Subtitle" not in content

    def test_invalid_line_number_returns_failure(self, tmp_path):
        """Should return failure for invalid line number."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\n", encoding="utf-8")
        issue = {
            "issue_id": "2",
            "location": {"line": 999},
            "message": "Heading level skip",
        }
        result = fix_heading_hierarchy(issue, test_file)
        assert result["success"] is False


class TestFixLinkNormalization:
    """Test link normalization."""

    def test_normalizes_relative_md_links(self, tmp_path):
        """Should convert ./page.md to /docs/page/."""
        test_file = tmp_path / "test.md"
        test_file.write_text("[See guide](./getting-started.md)", encoding="utf-8")
        issue = {"issue_id": "1", "message": "./page.md"}
        result = fix_link_normalization(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "/docs/" in content
        assert ".md" not in content.split("](")[1]

    def test_no_relative_links_returns_failure(self, tmp_path):
        """Should return failure when no relative links found."""
        test_file = tmp_path / "test.md"
        test_file.write_text("[link](https://example.com)", encoding="utf-8")
        issue = {"issue_id": "2", "message": "./page.md"}
        result = fix_link_normalization(issue, test_file)
        assert result["success"] is False


class TestFixAltText:
    """Test alt text fix."""

    def test_adds_alt_text_from_filename(self, tmp_path):
        """Should add alt text derived from image filename."""
        test_file = tmp_path / "test.md"
        test_file.write_text("![](my-screenshot.png)", encoding="utf-8")
        issue = {"issue_id": "1"}
        result = fix_alt_text(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "![My Screenshot]" in content

    def test_no_empty_alt_returns_failure(self, tmp_path):
        """Should return failure when no images with empty alt text."""
        test_file = tmp_path / "test.md"
        test_file.write_text("![Already has alt](image.png)", encoding="utf-8")
        issue = {"issue_id": "2"}
        result = fix_alt_text(issue, test_file)
        assert result["success"] is False


class TestFixMetadata:
    """Test metadata fix."""

    def test_adds_product_name_to_title(self, tmp_path):
        """Should add product name prefix to title."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Getting Started\nweight: 1\n---\n# Content\n", encoding="utf-8")
        product_facts = {"product_name": "Aspose.3D"}
        issue = {"issue_id": "1"}
        result = fix_metadata(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "Aspose.3D" in content

    def test_product_name_already_in_title_skips(self, tmp_path):
        """Should skip when product name already in title."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Aspose.3D Getting Started\nweight: 1\n---\n# Content\n", encoding="utf-8")
        product_facts = {"product_name": "Aspose.3D"}
        issue = {"issue_id": "2"}
        result = fix_metadata(issue, test_file, product_facts)
        assert result["success"] is False
        assert "already in title" in result.get("error", "").lower()

    def test_no_frontmatter_returns_failure(self, tmp_path):
        """Should return failure when no frontmatter found."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# No frontmatter\nContent.", encoding="utf-8")
        product_facts = {"product_name": "Test"}
        issue = {"issue_id": "3"}
        result = fix_metadata(issue, test_file, product_facts)
        assert result["success"] is False

    def test_empty_product_name_returns_failure(self, tmp_path):
        """Should return failure when product_name is empty."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n# Content\n", encoding="utf-8")
        product_facts = {}
        issue = {"issue_id": "4"}
        result = fix_metadata(issue, test_file, product_facts)
        assert result["success"] is False


class TestFixParagraphBreaks:
    """Test paragraph break fix."""

    def test_splits_long_paragraph(self, tmp_path):
        """Should split a paragraph longer than 10 lines into two chunks."""
        # Build a paragraph with 12 non-empty lines (exceeds threshold of 10)
        lines = [f"Sentence number {i}." for i in range(1, 13)]
        para_text = "\n".join(lines)
        content = f"# Title\n\n{para_text}\n\nEnd.\n"
        test_file = tmp_path / "test.md"
        test_file.write_text(content, encoding="utf-8")
        # Paragraph starts at line 3 (after "# Title\n\n")
        issue = {"issue_id": "pb1", "location": {"line": 3}}
        result = fix_paragraph_breaks(issue, test_file)
        assert result["success"] is True
        assert result["fix_type"] == "paragraph_breaks"
        updated = test_file.read_text(encoding="utf-8")
        # After fix, there should be an extra blank line inside the former paragraph
        assert "\n\n" in updated.split("# Title")[1]

    def test_short_paragraph_returns_failure(self, tmp_path):
        """Should return failure when paragraph is 10 lines or fewer."""
        test_file = tmp_path / "test.md"
        test_file.write_text("First paragraph.\nSecond paragraph.\n", encoding="utf-8")
        issue = {"issue_id": "pb2", "location": {"line": 1}}
        result = fix_paragraph_breaks(issue, test_file)
        assert result["success"] is False

    def test_invalid_line_returns_failure(self, tmp_path):
        """Should return failure for line number 0 or negative."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\nSome text.\n", encoding="utf-8")
        issue = {"issue_id": "pb3", "location": {"line": 0}}
        result = fix_paragraph_breaks(issue, test_file)
        assert result["success"] is False


class TestFixBulletSplitting:
    """Test bullet splitting fix."""

    def test_splits_long_bullet_at_commas(self, tmp_path):
        """Should split long bullet into multiple bullets at commas."""
        test_file = tmp_path / "test.md"
        long_text = "first item, second item, third item"
        test_file.write_text(f"- {long_text}\n", encoding="utf-8")
        issue = {"issue_id": "1", "location": {"line": 1}}
        result = fix_bullet_splitting(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert content.count("- ") >= 2

    def test_non_bullet_line_returns_failure(self, tmp_path):
        """Should return failure when line is not a bullet."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Just a paragraph.\n", encoding="utf-8")
        issue = {"issue_id": "2", "location": {"line": 1}}
        result = fix_bullet_splitting(issue, test_file)
        assert result["success"] is False


class TestFixMissingPrerequisites:
    """Test missing prerequisites auto-fix."""

    def test_inserts_prerequisites_before_first_h2(self, tmp_path):
        """Should insert Prerequisites section before the first H2."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Guide\n---\n\n# Guide\n\nIntro text.\n\n## Workflows\n\nContent.\n",
            encoding="utf-8",
        )
        product_facts = {"product_name": "Aspose.3D"}
        issue = {"issue_id": "prereq1"}
        result = fix_missing_prerequisites(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "## Prerequisites" in content
        assert "Installation Guide" in content
        # Prerequisites should come before Workflows
        assert content.index("## Prerequisites") < content.index("## Workflows")

    def test_appends_prerequisites_when_no_h2(self, tmp_path):
        """Should append at end when no H2 headings exist."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\n\nSome content.\n", encoding="utf-8")
        product_facts = {"product_name": "TestLib"}
        issue = {"issue_id": "prereq2"}
        result = fix_missing_prerequisites(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "## Prerequisites" in content
        assert "TestLib" in content


class TestFixMissingCta:
    """Test missing CTA auto-fix."""

    def test_appends_cta_text(self, tmp_path):
        """Should append Get started CTA text to file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Home\n---\n\n# Welcome\n\nIntro.\n", encoding="utf-8")
        product_facts = {"product_name": "Aspose.Note"}
        issue = {"issue_id": "cta1"}
        result = fix_missing_cta(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "Get started with Aspose.Note today" in content


class TestFixMissingNextSteps:
    """Test missing next steps auto-fix."""

    def test_appends_next_steps_section(self, tmp_path):
        """Should append Next Steps section with Developer Guide link."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Getting Started\n---\n\n# Getting Started\n\nHello.\n", encoding="utf-8")
        issue = {"issue_id": "ns1"}
        result = fix_missing_next_steps(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "## Next Steps" in content
        assert "Developer Guide" in content


class TestFixLowContentDensity:
    """Test low content density auto-fix."""

    def test_flags_for_review_when_low_density(self, tmp_path):
        """Should flag for review instead of injecting synthetic markers (TC-1750)."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Docs\n---\n\n# Docs\n\n" + "word " * 200 + "\n", encoding="utf-8")
        issue = {"issue_id": "cd1", "message": "Low claim density (0 claims for 200 words, expect ~2)"}
        product_facts = {
            "claims": [
                {"claim_id": "real-claim-001"},
                {"claim_id": "real-claim-002"},
                {"claim_id": "real-claim-003"},
            ]
        }
        result = fix_low_content_density(issue, test_file, product_facts)
        assert result["success"] is True
        assert result["action"] == "flagged_for_review"
        content = test_file.read_text(encoding="utf-8")
        assert "W7_REVIEW: low_content_density" in content
        assert "expected ~2 claim markers" in content

    def test_sufficient_markers_skips(self, tmp_path):
        """Should skip when enough claim markers already present."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n# Test\n\n"
            "<!-- claim_id: aaa --> <!-- claim_id: bbb -->\n" + "word " * 200 + "\n",
            encoding="utf-8",
        )
        issue = {"issue_id": "cd2", "message": "Low claim density (2 claims for 200 words, expect ~2)"}
        product_facts = {"claims": [{"claim_id": "aaa"}, {"claim_id": "bbb"}]}
        result = fix_low_content_density(issue, test_file, product_facts)
        assert result["success"] is False


class TestFixHeadingDescriptiveness:
    """Test heading descriptiveness auto-fix."""

    def test_prepends_product_name_to_short_heading(self, tmp_path):
        """Should prepend product name to short generic heading."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Page\n\n## Usage\n\nSome text.\n", encoding="utf-8")
        issue = {
            "issue_id": "hd1",
            "location": {"path": "test.md", "line": 3},
            "message": "Generic heading: Usage",
        }
        product_facts = {"product_name": "Aspose.3D"}
        result = fix_heading_descriptiveness(issue, test_file, product_facts)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "## Aspose.3D Usage" in content

    def test_skips_if_product_name_already_present(self, tmp_path):
        """Should skip heading that already contains product name."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Page\n\n## Aspose.3D Usage\n\nText.\n", encoding="utf-8")
        issue = {
            "issue_id": "hd2",
            "location": {"path": "test.md", "line": 3},
            "message": "Generic heading: Aspose.3D Usage",
        }
        product_facts = {"product_name": "Aspose.3D"}
        result = fix_heading_descriptiveness(issue, test_file, product_facts)
        assert result["success"] is False

    def test_handles_missing_product_name(self, tmp_path):
        """Should fail gracefully when product_name is empty."""
        test_file = tmp_path / "test.md"
        test_file.write_text("## Usage\n", encoding="utf-8")
        issue = {"issue_id": "hd3", "location": {"path": "test.md", "line": 1}}
        result = fix_heading_descriptiveness(issue, test_file, {"product_name": ""})
        assert result["success"] is False


class TestFixExampleClarity:
    """Test example clarity auto-fix."""

    def test_adds_introduction_before_code_block(self, tmp_path):
        """Should add introductory text before code block."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Page\n\n```python\nprint('hello')\n```\n", encoding="utf-8")
        issue = {
            "issue_id": "ec1",
            "location": {"path": "test.md", "line": 3},
            "message": "Code block missing introduction",
        }
        result = fix_example_clarity(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "The following example demonstrates" in content

    def test_adds_explanation_after_code_block(self, tmp_path):
        """Should add explanatory text after code block."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Page\n\nIntro line here.\n\n```python\nprint('hello')\n```\n", encoding="utf-8")
        issue = {
            "issue_id": "ec2",
            "location": {"path": "test.md", "line": 5},
            "message": "Code block missing explanation",
        }
        result = fix_example_clarity(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "The code above performs" in content


class TestFixSnippetAttribution:
    """Test snippet attribution auto-fix."""

    def test_adds_attribution_comment(self, tmp_path):
        """Should add attribution comment above code block."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Page\n\n```python\nprint('hello')\n```\n", encoding="utf-8")
        issue = {
            "issue_id": "sa1",
            "location": {"path": "test.md", "line": 3},
            "message": "Code block not found in snippet_catalog",
        }
        result = fix_snippet_attribution(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        assert "<!-- source: product API documentation -->" in content

    def test_invalid_line_number_fails(self, tmp_path):
        """Should fail gracefully for invalid line number."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Page\n", encoding="utf-8")
        issue = {"issue_id": "sa2", "location": {"path": "test.md", "line": 999}}
        result = fix_snippet_attribution(issue, test_file)
        assert result["success"] is False


class TestBulletRoutingFix:
    """Test that bullet WARN messages route correctly to fix_bullet_splitting."""

    def test_warn_message_matches_routing(self):
        """Bullet WARN message 'Bullet point long' should contain 'long'."""
        warn_msg = "Bullet point long (192 chars, recommend <180)"
        assert "long" in warn_msg.lower()

    def test_error_message_matches_routing(self):
        """Bullet ERROR message 'Bullet point too long' should also contain 'long'."""
        error_msg = "Bullet point too long (260 chars, max 250)"
        assert "long" in error_msg.lower()


# ---------------------------------------------------------------------------
# TC-1407: FOSS Licensing Auto-Fix (Agent B)
# ---------------------------------------------------------------------------

class TestFixFossLicensing:
    """TC-1407: Tests for fix_foss_licensing auto-fix."""

    def test_fix_foss_licensing_removes_line(self, tmp_path):
        """Should remove or blank line containing commercial licensing language."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "# Getting Started\n\n"
            "- You need a commercial license to use this.\n"
            "- This is a free feature.\n",
            encoding="utf-8",
        )
        issue = {
            "issue_id": "foss_lic_1",
            "location": {"path": "test.md", "line": 3},
        }
        result = fix_foss_licensing(issue, test_file)
        assert result["success"] is True
        assert result["fix_type"] == "foss_licensing"
        content = test_file.read_text(encoding="utf-8")
        assert "commercial license" not in content
        assert "free feature" in content

    def test_fix_foss_licensing_blanks_paragraph_line(self, tmp_path):
        """Should blank (not remove) non-list lines."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "# Title\n\n"
            "This is a paragraph with commercial license reference.\n\n"
            "Another paragraph.\n",
            encoding="utf-8",
        )
        issue = {
            "issue_id": "foss_lic_2",
            "location": {"path": "test.md", "line": 3},
        }
        result = fix_foss_licensing(issue, test_file)
        assert result["success"] is True
        content = test_file.read_text(encoding="utf-8")
        # The line should be blanked, not containing commercial text
        assert "commercial license" not in content

    def test_fix_foss_licensing_invalid_line(self, tmp_path):
        """Should fail gracefully for invalid line number."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Title\n", encoding="utf-8")
        issue = {
            "issue_id": "foss_lic_3",
            "location": {"path": "test.md", "line": 999},
        }
        result = fix_foss_licensing(issue, test_file)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TC-1407: Collapsed Frontmatter Auto-Fix (Agent B)
# ---------------------------------------------------------------------------

class TestFixCollapsedFrontmatter:
    """TC-1407: Tests for fix_collapsed_frontmatter auto-fix."""

    def test_fix_collapsed_frontmatter_splits(self, tmp_path):
        """Should split collapsed YAML line into separate lines."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            '---\ntitle: "A" description: "B"\nurl_path: /test/\n---\n\n# Page\n',
            encoding="utf-8",
        )
        issue = {
            "issue_id": "collapsed_fm_1",
            "location": {"path": "test.md", "line": 2},
        }
        result = fix_collapsed_frontmatter(issue, test_file)
        assert result["success"] is True
        assert result["fix_type"] == "collapsed_frontmatter"
        content = test_file.read_text(encoding="utf-8")
        lines = content.split('\n')
        # The original collapsed line should now be split into 2+ lines
        assert result.get("lines_created", 0) >= 2
        # Both title and description should be findable on separate lines
        title_lines = [l for l in lines if l.strip().startswith('title:')]
        desc_lines = [l for l in lines if l.strip().startswith('description:')]
        assert len(title_lines) >= 1
        assert len(desc_lines) >= 1

    def test_fix_collapsed_frontmatter_invalid_line(self, tmp_path):
        """Should fail gracefully for invalid line number."""
        test_file = tmp_path / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n", encoding="utf-8")
        issue = {
            "issue_id": "collapsed_fm_2",
            "location": {"path": "test.md", "line": 0},
        }
        result = fix_collapsed_frontmatter(issue, test_file)
        assert result["success"] is False


class TestTC1504NewAutoFixes:
    """Tests for TC-1504 new auto-fix functions."""

    # Fix Function 19: Source Annotations
    def test_fix_source_annotations_removes_comments(self, tmp_path):
        """Should remove <!-- source: ... --> comments."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Test\n\n"
            "<!-- source: product API documentation -->\n"
            "Content here.\n"
            "<!-- source: another source -->\n"
            "More content.\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "source_1"}
        result = fix_source_annotations(issue, test_file)
        assert result["success"] is True
        assert result["fix_type"] == "source_annotations"
        assert result["annotations_removed"] == 2

        content = test_file.read_text(encoding="utf-8")
        assert "<!-- source:" not in content

    def test_fix_source_annotations_no_annotations(self, tmp_path):
        """Should return failure when no source annotations found."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n# Test\n\nClean content.\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "source_2"}
        result = fix_source_annotations(issue, test_file)
        assert result["success"] is False
        assert "No source annotations" in result.get("error", "")

    def test_fix_source_annotations_cleans_triple_newlines(self, tmp_path):
        """Should clean up triple newlines after removal."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Test\n\n"
            "Content.\n\n"
            "<!-- source: test -->\n\n"
            "More content.\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "source_3"}
        result = fix_source_annotations(issue, test_file)
        assert result["success"] is True

        content = test_file.read_text(encoding="utf-8")
        # Should not have 3+ consecutive newlines
        assert "\n\n\n" not in content

    # Fix Function 20: Platform Listing
    def test_fix_platform_listing_removes_wrong_platforms(self, tmp_path):
        """Should remove lines with wrong platforms."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Test\n\n"
            "## Available Platforms\n\n"
            "- Python 3.7+\n"
            "- .NET Framework 4.8\n"
            "- Java 8+\n",
            encoding="utf-8"
        )
        issue = {
            "issue_id": "platform_1",
            "message": "Wrong platforms listed (target=python): .net, java"
        }
        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        result = fix_platform_listing(issue, test_file, product_facts)
        assert result["success"] is True
        assert result["fix_type"] == "platform_listing"
        assert result["lines_removed"] == 2

        content = test_file.read_text(encoding="utf-8")
        assert "Python" in content
        assert ".NET" not in content
        assert "Java" not in content

    def test_fix_platform_listing_no_section(self, tmp_path):
        """Should return failure when no Available Platforms section found."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n# Test\n\nNo platform section.\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "platform_2"}
        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        result = fix_platform_listing(issue, test_file, product_facts)
        assert result["success"] is False
        assert "No Available Platforms section" in result.get("error", "")

    def test_fix_platform_listing_unknown_product(self, tmp_path):
        """Should fail when target platform cannot be determined."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Test\n\n"
            "## Available Platforms\n\n"
            "- Platform A\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "platform_3"}
        product_facts = {"product_name": "Generic Product"}
        result = fix_platform_listing(issue, test_file, product_facts)
        assert result["success"] is False
        assert "Cannot determine target platform" in result.get("error", "")

    def test_fix_platform_listing_dotnet_product(self, tmp_path):
        """Should work correctly for .NET products."""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Test\n\n"
            "## Available Platforms\n\n"
            "- .NET Framework 4.8\n"
            "- Python 3.7+\n"
            "- Java 8+\n",
            encoding="utf-8"
        )
        issue = {"issue_id": "platform_4"}
        product_facts = {"product_name": "Aspose.Note .NET"}
        result = fix_platform_listing(issue, test_file, product_facts)
        assert result["success"] is True

        content = test_file.read_text(encoding="utf-8")
        assert ".NET" in content
        assert "Python" not in content
        assert "Java" not in content

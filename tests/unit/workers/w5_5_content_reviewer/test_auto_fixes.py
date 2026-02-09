"""Tests for W5.5 ContentReviewer auto-fix capabilities.

TC-1100-P5: W5.5 ContentReviewer Phase 5 - Tests
"""
import pytest
from pathlib import Path

from launch.workers.w5_5_content_reviewer.fixes.auto_fixes import (
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
)
from launch.workers.w5_5_content_reviewer.fixes.iteration_tracker import IterationTracker


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
                "location": {"path": "drafts/test.md", "line": 2},
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

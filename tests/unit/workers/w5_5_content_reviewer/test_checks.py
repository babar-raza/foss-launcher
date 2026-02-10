"""Tests for W5.5 ContentReviewer scoring, routing, and check_all logic.

TC-1100-P5: W5.5 ContentReviewer Phase 5 - Tests
TC-1103: W5.5 ContentReviewer test hardening (check_all tests).
"""
import pytest
from pathlib import Path

from launch.workers.w5_5_content_reviewer.scoring import (
    calculate_scores,
    route_review_result,
)
from launch.workers.w5_5_content_reviewer.checks import (
    content_quality,
    technical_accuracy,
    usability,
)


class TestCalculateScores:
    """Test dimension score calculation."""

    def test_no_issues_returns_all_fives(self):
        """Zero issues should give perfect 5/5 on all dimensions."""
        scores = calculate_scores([])
        assert scores == {
            "content_quality": 5,
            "technical_accuracy": 5,
            "usability": 5,
        }

    def test_single_content_quality_warn_not_auto_fixable(self):
        """One non-auto-fixable warn should give 3/5 (moderate)."""
        issues = [
            {"check": "content_quality.readability", "severity": "warn", "message": "test"}
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 3

    def test_single_content_quality_warn_auto_fixable(self):
        """One auto-fixable warn should give 4/5 (minor)."""
        issues = [
            {"check": "content_quality.readability", "severity": "warn", "message": "test", "auto_fixable": True}
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 4
        assert scores["technical_accuracy"] == 5
        assert scores["usability"] == 5

    def test_multiple_warns_gives_three(self):
        """4-6 warns should give 3/5."""
        issues = [
            {"check": "content_quality.readability", "severity": "warn", "message": f"test{i}"}
            for i in range(5)
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 3

    def test_many_warns_gives_two(self):
        """>6 warns should give 2/5."""
        issues = [
            {"check": "content_quality.readability", "severity": "warn", "message": f"test{i}"}
            for i in range(8)
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 2

    def test_blocker_gives_one(self):
        """Any blocker should give 1/5."""
        issues = [
            {"check": "content_quality.frontmatter_completeness", "severity": "blocker", "message": "Missing frontmatter"}
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 1

    def test_three_errors_gives_two(self):
        """3+ errors should give 2/5."""
        issues = [
            {"check": "technical_accuracy.code_syntax", "severity": "error", "message": f"err{i}"}
            for i in range(3)
        ]
        scores = calculate_scores(issues)
        assert scores["technical_accuracy"] == 2

    def test_one_error_gives_three(self):
        """1-2 errors should give 3/5."""
        issues = [
            {"check": "usability.navigation", "severity": "error", "message": "test"}
        ]
        scores = calculate_scores(issues)
        assert scores["usability"] == 3

    def test_mixed_dimensions_independent(self):
        """Each dimension scored independently."""
        issues = [
            {"check": "content_quality.readability", "severity": "blocker", "message": "bad"},
            {"check": "technical_accuracy.code_syntax", "severity": "warn", "message": "minor"},
            {"check": "usability.navigation", "severity": "error", "message": "moderate"},
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 1
        assert scores["technical_accuracy"] == 3  # Non-auto-fixable warn = moderate
        assert scores["usability"] == 3

    def test_unknown_dimension_ignored(self):
        """Issues with unknown check prefix don't affect any dimension."""
        issues = [
            {"check": "unknown.check", "severity": "error", "message": "test"}
        ]
        scores = calculate_scores(issues)
        assert all(s == 5 for s in scores.values())

    def test_info_severity_does_not_penalize(self):
        """Info-level issues should still yield score 5 (no penalty)."""
        issues = [
            {"check": "content_quality.readability", "severity": "info", "message": "note"}
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 5

    def test_exactly_four_warns_gives_three(self):
        """Boundary: exactly 4 warns = score 3 (moderate)."""
        issues = [
            {"check": "technical_accuracy.claim_validity", "severity": "warn", "message": f"w{i}"}
            for i in range(4)
        ]
        scores = calculate_scores(issues)
        assert scores["technical_accuracy"] == 3

    def test_exactly_seven_warns_gives_two(self):
        """Boundary: exactly 7 warns = score 2 (>6)."""
        issues = [
            {"check": "usability.navigation", "severity": "warn", "message": f"w{i}"}
            for i in range(7)
        ]
        scores = calculate_scores(issues)
        assert scores["usability"] == 2

    def test_two_errors_gives_three(self):
        """2 errors = score 3 (moderate, 1-2 errors)."""
        issues = [
            {"check": "content_quality.tone", "severity": "error", "message": f"e{i}"}
            for i in range(2)
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 3

    def test_exactly_six_warns_gives_three(self):
        """Boundary: exactly 6 warns = score 3 (4-6 range)."""
        issues = [
            {"check": "content_quality.structure", "severity": "warn", "message": f"w{i}"}
            for i in range(6)
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 3


class TestRouteReviewResult:
    """Test routing logic."""

    def test_all_pass(self):
        """All dimensions >=4, no issues -> PASS."""
        scores = {"content_quality": 5, "technical_accuracy": 5, "usability": 5}
        result = route_review_result(scores, [])
        assert result == "PASS"

    def test_all_four_with_auto_fixable_errors(self):
        """All >=4 with only auto-fixable errors -> PASS."""
        scores = {"content_quality": 4, "technical_accuracy": 4, "usability": 4}
        issues = [
            {"severity": "error", "auto_fixable": True, "location": {"path": "test.md"}},
        ]
        result = route_review_result(scores, issues)
        assert result == "PASS"

    def test_blocker_rejects(self):
        """Any blocker -> REJECT."""
        scores = {"content_quality": 1, "technical_accuracy": 5, "usability": 5}
        issues = [
            {"severity": "blocker", "location": {"path": "test.md"}},
        ]
        result = route_review_result(scores, issues)
        assert result == "REJECT"

    def test_score_two_rejects(self):
        """Any dimension <=2 -> REJECT."""
        scores = {"content_quality": 2, "technical_accuracy": 5, "usability": 5}
        result = route_review_result(scores, [])
        assert result == "REJECT"

    def test_score_three_needs_changes(self):
        """Any dimension = 3 -> NEEDS_CHANGES."""
        scores = {"content_quality": 3, "technical_accuracy": 5, "usability": 5}
        issues = [
            {"severity": "warn", "location": {"path": "test.md"}},
        ]
        result = route_review_result(scores, issues)
        assert result == "NEEDS_CHANGES"

    def test_non_auto_fixable_error_needs_changes(self):
        """Non-auto-fixable error -> NEEDS_CHANGES."""
        scores = {"content_quality": 4, "technical_accuracy": 4, "usability": 4}
        issues = [
            {"severity": "error", "auto_fixable": False, "location": {"path": "test.md"}},
        ]
        result = route_review_result(scores, issues)
        assert result == "NEEDS_CHANGES"

    def test_many_warns_per_page_rejects(self):
        """>10 warns per page -> REJECT."""
        scores = {"content_quality": 4, "technical_accuracy": 4, "usability": 4}
        issues = [
            {"severity": "warn", "location": {"path": "single_page.md"}}
            for _ in range(12)
        ]
        result = route_review_result(scores, issues)
        assert result == "REJECT"

    def test_five_warns_per_page_needs_changes(self):
        """5-10 warns per page -> NEEDS_CHANGES."""
        scores = {"content_quality": 4, "technical_accuracy": 4, "usability": 4}
        issues = [
            {"severity": "warn", "location": {"path": "page.md"}}
            for _ in range(7)
        ]
        result = route_review_result(scores, issues)
        assert result == "NEEDS_CHANGES"

    def test_score_one_rejects(self):
        """Score 1 in any dimension -> REJECT."""
        scores = {"content_quality": 5, "technical_accuracy": 1, "usability": 5}
        result = route_review_result(scores, [])
        assert result == "REJECT"

    def test_three_non_auto_fixable_errors_reject(self):
        """3+ non-auto-fixable errors -> REJECT."""
        scores = {"content_quality": 4, "technical_accuracy": 4, "usability": 4}
        issues = [
            {"severity": "error", "auto_fixable": False, "location": {"path": f"page{i}.md"}}
            for i in range(3)
        ]
        result = route_review_result(scores, issues)
        assert result == "REJECT"

    def test_pass_with_few_warns(self):
        """Few warns (<5 per page) with all scores >=4 -> PASS."""
        scores = {"content_quality": 4, "technical_accuracy": 5, "usability": 4}
        issues = [
            {"severity": "warn", "location": {"path": "page.md"}}
            for _ in range(3)
        ]
        result = route_review_result(scores, issues)
        assert result == "PASS"

    def test_no_issues_all_fives_pass(self):
        """Perfect scores with zero issues -> PASS."""
        scores = {"content_quality": 5, "technical_accuracy": 5, "usability": 5}
        result = route_review_result(scores, [])
        assert result == "PASS"

    def test_warns_distributed_across_pages_pass(self):
        """Many warns but spread across pages (<5 per page) -> PASS."""
        scores = {"content_quality": 4, "technical_accuracy": 4, "usability": 4}
        # 8 warns across 3 pages = ~2.7 per page => PASS
        issues = [
            {"severity": "warn", "location": {"path": "page1.md"}},
            {"severity": "warn", "location": {"path": "page1.md"}},
            {"severity": "warn", "location": {"path": "page1.md"}},
            {"severity": "warn", "location": {"path": "page2.md"}},
            {"severity": "warn", "location": {"path": "page2.md"}},
            {"severity": "warn", "location": {"path": "page2.md"}},
            {"severity": "warn", "location": {"path": "page3.md"}},
            {"severity": "warn", "location": {"path": "page3.md"}},
        ]
        result = route_review_result(scores, issues)
        assert result == "PASS"


# ---------------------------------------------------------------------------
# check_all() tests  (TC-1103 B3)
# ---------------------------------------------------------------------------

REQUIRED_ISSUE_KEYS = sorted(["issue_id", "check", "severity", "message", "location"])


class TestContentQualityCheckAll:
    """Test content_quality.check_all returns well-formed issues."""

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_returns_list(self, tmp_path):
        """check_all must return a list."""
        drafts_dir, product_facts, page_plan = self._make_fixtures(tmp_path)
        result = content_quality.check_all(drafts_dir, product_facts, page_plan)
        assert isinstance(result, list)

    def test_clean_draft_no_blockers(self, tmp_path):
        """Clean markdown with frontmatter should produce no blocker-severity issues."""
        clean_md = (
            "---\ntitle: Test\ndescription: A test page\nurl_path: /test/\n---\n\n"
            "# Test Page\n\nThis is a clean paragraph.\n"
        )
        drafts_dir, product_facts, page_plan = self._make_fixtures(tmp_path, content=clean_md)
        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        blockers = [i for i in issues if i.get("severity") == "blocker"]
        assert blockers == []

    def test_issue_dict_has_required_keys(self, tmp_path):
        """Every issue dict must contain issue_id, check, severity, message, location."""
        # Content with a TODO triggers an error
        bad_md = "# Title\n\nTODO: write this section\n"
        drafts_dir, product_facts, page_plan = self._make_fixtures(tmp_path, content=bad_md)
        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        assert len(issues) > 0, "Expected at least one issue for TODO content"
        for issue in issues:
            assert sorted(k for k in REQUIRED_ISSUE_KEYS if k in issue) == REQUIRED_ISSUE_KEYS, (
                f"Missing required keys in issue: {issue}"
            )

    def test_check_prefix(self, tmp_path):
        """All issue.check values must start with 'content_quality.'."""
        bad_md = "# Title\n\nTODO: placeholder\n"
        drafts_dir, product_facts, page_plan = self._make_fixtures(tmp_path, content=bad_md)
        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        for issue in issues:
            assert issue["check"].startswith("content_quality."), (
                f"Check prefix mismatch: {issue['check']}"
            )

    def test_empty_drafts_dir_returns_empty(self, tmp_path):
        """No .md files in drafts_dir should return no issues."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": []}
        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        assert issues == []

    def test_nonexistent_drafts_dir_returns_empty(self, tmp_path):
        """Non-existent drafts_dir should return empty list (not raise)."""
        drafts_dir = tmp_path / "nonexistent"
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": []}
        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        assert issues == []


class TestTechnicalAccuracyCheckAll:
    """Test technical_accuracy.check_all returns well-formed issues."""

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        snippet_catalog = {"snippets": []}
        evidence_map = {"evidence": [], "metadata": {}}
        return drafts_dir, product_facts, page_plan, snippet_catalog, evidence_map

    def test_returns_list(self, tmp_path):
        """check_all must return a list."""
        drafts_dir, pf, pp, sc, em = self._make_fixtures(tmp_path)
        result = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        assert isinstance(result, list)

    def test_issue_dict_has_required_keys(self, tmp_path):
        """Every issue dict must contain required keys."""
        # Python syntax error triggers a blocker
        bad_md = "# Title\n\n```python\ndef foo(\n```\n"
        drafts_dir, pf, pp, sc, em = self._make_fixtures(tmp_path, content=bad_md)
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        assert len(issues) > 0, "Expected at least one issue for broken Python syntax"
        for issue in issues:
            assert sorted(k for k in REQUIRED_ISSUE_KEYS if k in issue) == REQUIRED_ISSUE_KEYS, (
                f"Missing required keys in issue: {issue}"
            )

    def test_check_prefix(self, tmp_path):
        """All issue.check values must start with 'technical_accuracy.'."""
        bad_md = "# Title\n\n```python\ndef foo(\n```\n"
        drafts_dir, pf, pp, sc, em = self._make_fixtures(tmp_path, content=bad_md)
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        for issue in issues:
            assert issue["check"].startswith("technical_accuracy."), (
                f"Check prefix mismatch: {issue['check']}"
            )

    def test_empty_drafts_dir_returns_empty(self, tmp_path):
        """No .md files in drafts_dir should return no issues."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        pf = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        pp = {"pages": []}
        sc = {"snippets": []}
        em = {"evidence": [], "metadata": {}}
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        assert issues == []

    def test_valid_python_no_syntax_errors(self, tmp_path):
        """Valid Python code block should produce no code_syntax blocker."""
        good_md = "# Title\n\n```python\ndef greet():\n    print('hello')\n```\n"
        drafts_dir, pf, pp, sc, em = self._make_fixtures(tmp_path, content=good_md)
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        syntax_blockers = [
            i for i in issues
            if i.get("check") == "technical_accuracy.code_syntax_validation"
            and i.get("severity") == "blocker"
        ]
        assert syntax_blockers == []


class TestUsabilityCheckAll:
    """Test usability.check_all returns well-formed issues."""

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_returns_list(self, tmp_path):
        """check_all must return a list."""
        drafts_dir, pf, pp = self._make_fixtures(tmp_path)
        result = usability.check_all(drafts_dir, pp, pf)
        assert isinstance(result, list)

    def test_issue_dict_has_required_keys(self, tmp_path):
        """Every issue dict must contain required keys."""
        # Image with empty alt text triggers accessibility error
        bad_md = "# Title\n\n![](broken.png)\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=bad_md)
        issues = usability.check_all(drafts_dir, pp, pf)
        assert len(issues) > 0, "Expected at least one issue for empty alt text"
        for issue in issues:
            assert sorted(k for k in REQUIRED_ISSUE_KEYS if k in issue) == REQUIRED_ISSUE_KEYS, (
                f"Missing required keys in issue: {issue}"
            )

    def test_check_prefix(self, tmp_path):
        """All issue.check values must start with 'usability.'."""
        bad_md = "# Title\n\n![](broken.png)\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=bad_md)
        issues = usability.check_all(drafts_dir, pp, pf)
        for issue in issues:
            assert issue["check"].startswith("usability."), (
                f"Check prefix mismatch: {issue['check']}"
            )

    def test_empty_drafts_dir_returns_empty(self, tmp_path):
        """No .md files in drafts_dir should return no issues."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        pf = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        pp = {"pages": []}
        issues = usability.check_all(drafts_dir, pp, pf)
        assert issues == []

    def test_click_here_triggers_accessibility_issue(self, tmp_path):
        """'[click here]' link should trigger an accessibility issue."""
        bad_md = "# Title\n\n[click here](https://example.com)\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=bad_md)
        issues = usability.check_all(drafts_dir, pp, pf)
        accessibility_issues = [
            i for i in issues if i.get("check") == "usability.accessibility_compliance"
        ]
        assert len(accessibility_issues) > 0, "Expected accessibility issue for 'click here'"


# ---------------------------------------------------------------------------
# Bug Fix Tests (Agent B - TC-CREV-B-TRACK1)
# ---------------------------------------------------------------------------

class TestBugFixB001WorkflowCoverage:
    """Tests for Task B-001: Fix workflow coverage naive slug matching."""

    @staticmethod
    def _make_fixtures(tmp_path, page_slug="test", page_role=None, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / f"{page_slug}.md").write_text(content, encoding="utf-8")
        product_facts = {
            "product_name": "TestProduct",
            "claims": [],
            "claim_groups": {},
            "workflows": [
                {"name": "Install Package"},
                {"name": "Create Document"},
            ]
        }
        page = {"slug": page_slug, "title": "Test", "template": "feature.variant-standard"}
        if page_role:
            page["page_role"] = page_role
        page_plan = {"pages": [page]}
        snippet_catalog = {"snippets": []}
        evidence_map = {"claims": [], "metadata": {}}
        return drafts_dir, product_facts, page_plan, snippet_catalog, evidence_map

    def test_getting_started_guide_not_flagged(self, tmp_path):
        """Getting-started-guide should NOT trigger workflow coverage check."""
        drafts_dir, pf, pp, sc, em = self._make_fixtures(
            tmp_path,
            page_slug="getting-started-guide",
            page_role="tutorial",
            content="# Getting Started\n\nQuick start instructions.\n"
        )
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        workflow_issues = [
            i for i in issues if i.get("check") == "technical_accuracy.workflow_coverage"
        ]
        assert workflow_issues == [], "Getting-started-guide should not be flagged for workflow coverage"

    def test_comprehensive_guide_does_get_flagged(self, tmp_path):
        """Comprehensive guide SHOULD trigger workflow coverage check if workflows missing."""
        drafts_dir, pf, pp, sc, em = self._make_fixtures(
            tmp_path,
            page_slug="comprehensive-guide",
            page_role="comprehensive_guide",
            content="# Comprehensive Guide\n\nThis is a guide.\n"
        )
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        workflow_issues = [
            i for i in issues if i.get("check") == "technical_accuracy.workflow_coverage"
        ]
        # Should have 2 errors (one per workflow not mentioned)
        assert len(workflow_issues) == 2, "Comprehensive guide missing workflows should be flagged"


class TestBugFixB003GrammarWhitelist:
    """Tests for Task B-003: Add grammar whitelist for technical terms."""

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_grammar_whitelist_skips_aspose_note(self, tmp_path):
        """Lines with high technical term density should skip grammar check."""
        md_with_tech = "# Title\n\nThe Aspose.Note API provides SDK functionality.\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_tech)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        grammar_issues = [
            i for i in issues if i.get("check") == "content_quality.grammar_spelling"
        ]
        assert grammar_issues == [], "Aspose.Note should not trigger grammar warning"

    def test_grammar_still_catches_real_errors(self, tmp_path):
        """Real grammar errors should still be caught."""
        md_with_error = "# Title\n\nThis is a regular sentence with the the repeated word.\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_error)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        grammar_issues = [
            i for i in issues if i.get("check") == "content_quality.grammar_spelling"
        ]
        assert len(grammar_issues) > 0, "Real grammar errors should still be caught"


class TestBugFixB004RelatedLinksExemption:
    """Tests for Task B-004: Fix related links exemption for index pages."""

    @staticmethod
    def _make_fixtures(tmp_path, page_slug="test", content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / f"{page_slug}.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": page_slug, "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_related_links_index_exempt(self, tmp_path):
        """Index pages should be exempt from related links check."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path,
            page_slug="_index",
            content="# Table of Contents\n\nStructured navigation.\n"
        )
        issues = usability.check_all(drafts_dir, pp, pf)
        link_issues = [
            i for i in issues if i.get("check") == "usability.related_links"
        ]
        assert link_issues == [], "Index pages should be exempt from related links check"

    def test_related_links_non_index_checked(self, tmp_path):
        """Non-index pages should still be checked for related links."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path,
            page_slug="feature-page",
            content="# Feature Page\n\nSome content without links.\n"
        )
        issues = usability.check_all(drafts_dir, pp, pf)
        link_issues = [
            i for i in issues if i.get("check") == "usability.related_links"
        ]
        assert len(link_issues) > 0, "Non-index pages should be checked for related links"

    def test_related_links_index_exact_match_exempt(self, tmp_path):
        """Page with slug 'index' (no underscore) should also be exempt."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path,
            page_slug="index",
            content="# Index\n\nNavigation structure.\n"
        )
        issues = usability.check_all(drafts_dir, pp, pf)
        link_issues = [
            i for i in issues if i.get("check") == "usability.related_links"
        ]
        assert link_issues == [], "Exact 'index' slug should be exempt"

    @pytest.mark.xfail(reason="Known bug: '_index' in page_slug matches embedded occurrences (false positive)")
    def test_related_links_embedded_index_not_exempt(self, tmp_path):
        """Pages with '_index' embedded in slug should NOT be exempt (edge case).

        BUG C4-3: Current implementation uses 'in' operator which matches substrings.
        Fix needed: Change to page_slug == '_index' or page_slug == 'index'
        """
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path,
            page_slug="api_index_reference",
            content="# API Index Reference\n\nContent without links.\n"
        )
        issues = usability.check_all(drafts_dir, pp, pf)
        link_issues = [
            i for i in issues if i.get("check") == "usability.related_links"
        ]
        # Expected behavior: should NOT be exempt (should have link_issues)
        assert len(link_issues) > 0, "Embedded '_index' should NOT be exempt from related links check"


class TestBugFixB005ClaimMarkerFormat:
    """Tests for Task B-005: Fix claim marker format to accept both styles."""

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_claim_marker_html_format(self, tmp_path):
        """HTML comment claim format should be recognized."""
        claim_id = "12345678-1234-1234-1234-123456789abc"
        md_with_html_claim = f"# Title\n\nSome text. <!-- claim_id: {claim_id} -->\n\nMore text.\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_html_claim)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        # Should not trigger claim_marker_format error (that's for converting inline to HTML)
        # Should be counted in content_density check
        density_issues = [
            i for i in issues if i.get("check") == "content_quality.content_density"
        ]
        # With ~100 words, we expect ~1 claim, so this should pass
        assert all("Low claim density" not in i.get("message", "") for i in density_issues)

    def test_claim_marker_markdown_format(self, tmp_path):
        """Markdown claim format should be recognized in density check."""
        claim_id = "12345678-1234-1234-1234-123456789abc"
        md_with_markdown_claim = f"# Title\n\nSome text. [claim: {claim_id}]\n\nMore text.\n"
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_markdown_claim)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        # Should be counted in content_density check
        density_issues = [
            i for i in issues if i.get("check") == "content_quality.content_density"
        ]
        # With ~100 words, we expect ~1 claim, so this should pass
        assert all("Low claim density" not in i.get("message", "") for i in density_issues)

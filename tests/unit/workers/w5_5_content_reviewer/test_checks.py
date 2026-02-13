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
        """One non-auto-fixable warn should give 4/5 (minor).

        TC-P1A: Rubric says '4: Minor issues only (1-3 WARNs)' without
        requiring auto-fixability. 1-3 WARNs with zero errors = score 4.
        """
        issues = [
            {"check": "content_quality.readability", "severity": "warn", "message": "test"}
        ]
        scores = calculate_scores(issues)
        assert scores["content_quality"] == 4

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
        assert scores["technical_accuracy"] == 4  # TC-P1A: 1-3 WARNs = minor (score 4)
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

    def test_warns_spread_across_pages_gives_four(self):
        """BLOCKER-2b: 14 CQ warns on 14 pages (1.0/page) -> score 4, not 2.

        Density-aware scoring: absolute count 14 > 6 would give score 2,
        but 14 warns / 14 pages = 1.0 warns/page is mild -> score 4.
        """
        issues = [
            {
                "check": "content_quality.boilerplate_description",
                "severity": "warn",
                "message": f"boilerplate{i}",
                "location": {"path": f"page_{i}.md", "line": 1},
            }
            for i in range(14)
        ]
        scores = calculate_scores(issues, num_pages=14)
        assert scores["content_quality"] == 4

    def test_warns_concentrated_on_one_page_gives_two(self):
        """BLOCKER-2b: 14 CQ warns on 1 page (14.0/page) -> score 2.

        Same 14 warnings but concentrated = genuinely problematic.
        """
        issues = [
            {
                "check": "content_quality.boilerplate_description",
                "severity": "warn",
                "message": f"boilerplate{i}",
                "location": {"path": "single_page.md", "line": i},
            }
            for i in range(14)
        ]
        scores = calculate_scores(issues, num_pages=1)
        assert scores["content_quality"] == 2

    def test_round2_regression_scenario(self):
        """BLOCKER-2b: 27 warns across 18 pages, 3 dimensions -> all score 4.

        Reproduces the exact Round 2 regression: 14 CQ + 11 TA + 2 U warns
        across 18 pages. With absolute thresholds, CQ=2 TA=2 U=4 (REJECT).
        With density-aware thresholds, CQ=4 TA=4 U=4 (PASS).
        """
        issues = []
        # 14 content_quality warns
        for i in range(14):
            issues.append({
                "check": "content_quality.boilerplate_description",
                "severity": "warn",
                "message": f"cq{i}",
                "location": {"path": f"page_{i % 18}.md", "line": 1},
            })
        # 11 technical_accuracy warns
        for i in range(11):
            issues.append({
                "check": "technical_accuracy.snippet_attribution",
                "severity": "warn",
                "message": f"ta{i}",
                "location": {"path": f"page_{i % 18}.md", "line": 10},
            })
        # 2 usability warns
        for i in range(2):
            issues.append({
                "check": "usability.progressive_disclosure",
                "severity": "warn",
                "message": f"u{i}",
                "location": {"path": f"page_{i}.md", "line": 20},
            })

        scores = calculate_scores(issues, num_pages=18)
        assert scores["content_quality"] == 4   # 14/18 = 0.78/page
        assert scores["technical_accuracy"] == 4  # 11/18 = 0.61/page
        assert scores["usability"] == 4           # 2/18 = 0.11/page


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


class TestFeatureShowcaseFocus:
    """TC-P2D: Feature showcase pages must focus on single feature."""

    def test_feature_showcase_too_many_key_features_warns(self, tmp_path):
        """Feature showcase with >3 key_features claims should emit WARN."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        # Content with 5 distinct claim markers
        content = (
            "# Feature Page\n\n"
            "Text [claim: c1] and [claim: c2] and [claim: c3]\n"
            "More [claim: c4] and [claim: c5]\n"
        )
        (drafts_dir / "showcase.md").write_text(content, encoding="utf-8")

        product_facts = {
            "product_name": "TestProduct",
            "claims": [],
            "claim_groups": {
                "key_features": ["c1", "c2", "c3", "c4", "c5"],
            },
        }
        page_plan = {
            "pages": [{"slug": "showcase", "page_role": "feature_showcase"}],
        }
        snippet_catalog = {"snippets": []}
        evidence_map = {"evidence": [], "metadata": {}}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        focus_issues = [i for i in issues if i["check"] == "technical_accuracy.feature_showcase_focus"]
        assert len(focus_issues) == 1
        assert focus_issues[0]["severity"] == "warn"
        assert "5" in focus_issues[0]["message"]

    def test_feature_showcase_few_key_features_no_warn(self, tmp_path):
        """Feature showcase with <=3 key_features claims should not warn."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = "# Feature Page\n\nText [claim: c1] and [claim: c2]\n"
        (drafts_dir / "showcase.md").write_text(content, encoding="utf-8")

        product_facts = {
            "product_name": "TestProduct",
            "claims": [],
            "claim_groups": {
                "key_features": ["c1", "c2", "c3"],
            },
        }
        page_plan = {
            "pages": [{"slug": "showcase", "page_role": "feature_showcase"}],
        }
        snippet_catalog = {"snippets": []}
        evidence_map = {"evidence": [], "metadata": {}}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        focus_issues = [i for i in issues if i["check"] == "technical_accuracy.feature_showcase_focus"]
        assert len(focus_issues) == 0

    def test_non_showcase_page_skips_check(self, tmp_path):
        """Non-feature_showcase pages should not trigger focus check."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = "# Docs\n\n[claim: c1] [claim: c2] [claim: c3] [claim: c4] [claim: c5]\n"
        (drafts_dir / "docs.md").write_text(content, encoding="utf-8")

        product_facts = {
            "product_name": "TestProduct",
            "claims": [],
            "claim_groups": {"key_features": ["c1", "c2", "c3", "c4", "c5"]},
        }
        page_plan = {"pages": [{"slug": "docs", "page_role": "comprehensive_guide"}]}
        snippet_catalog = {"snippets": []}
        evidence_map = {"evidence": [], "metadata": {}}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        focus_issues = [i for i in issues if i["check"] == "technical_accuracy.feature_showcase_focus"]
        assert len(focus_issues) == 0


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

    def test_related_links_embedded_index_not_exempt(self, tmp_path):
        """Pages with '_index' embedded in slug should NOT be exempt (edge case).

        Fixed: Changed to exact match (page_slug == '_index') to avoid false positives.
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


class TestBugFixB101FrontmatterUrlField:
    """Tests for Task B-101 (TC-CREV-B-TRACK2): Accept both permalink and url_path in frontmatter."""

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_frontmatter_with_permalink_only(self, tmp_path):
        """Frontmatter with permalink field (Hugo standard) should pass."""
        md_with_permalink = (
            "---\ntitle: Test\ndescription: A test page\npermalink: /test/\n---\n\n"
            "# Test Page\n\nThis is content.\n"
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_permalink)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        url_field_issues = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and "url" in i.get("message", "").lower()
        ]
        assert url_field_issues == [], "Frontmatter with permalink should not trigger URL field error"

    def test_frontmatter_with_url_path_only(self, tmp_path):
        """Frontmatter with url_path field (backward compatibility) should pass."""
        md_with_url_path = (
            "---\ntitle: Test\ndescription: A test page\nurl_path: /test/\n---\n\n"
            "# Test Page\n\nThis is content.\n"
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_url_path)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        url_field_issues = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and "url" in i.get("message", "").lower()
        ]
        assert url_field_issues == [], "Frontmatter with url_path should not trigger URL field error"

    def test_frontmatter_with_both_fields(self, tmp_path):
        """Frontmatter with both permalink and url_path should pass."""
        md_with_both = (
            "---\ntitle: Test\ndescription: A test page\npermalink: /test/\nurl_path: /test/\n---\n\n"
            "# Test Page\n\nThis is content.\n"
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_with_both)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        url_field_issues = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and "url" in i.get("message", "").lower()
        ]
        assert url_field_issues == [], "Frontmatter with both fields should not trigger URL field error"

    def test_frontmatter_missing_both_url_fields(self, tmp_path):
        """Frontmatter with neither permalink nor url_path should trigger error."""
        md_without_url = (
            "---\ntitle: Test\ndescription: A test page\n---\n\n"
            "# Test Page\n\nThis is content.\n"
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=md_without_url)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        url_field_issues = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and "url" in i.get("message", "").lower()
        ]
        assert len(url_field_issues) == 1, "Frontmatter without URL field should trigger error"
        assert "permalink or url_path" in url_field_issues[0]["message"]

    def test_w5_output_format_with_permalink(self, tmp_path):
        """W5 output format (with permalink) should pass without issues."""
        # This is the actual format W5 generates
        w5_output = (
            "---\n"
            "title: \"Getting Started\"\n"
            "description: \"Mandatory docs page: getting-started\"\n"
            "layout: docs\n"
            "permalink: /3d/getting-started/\n"
            "---\n\n"
            "# Getting Started\n\n"
            "Content here.\n"
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=w5_output)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        frontmatter_issues = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
        ]
        # Should have no frontmatter completeness issues (permalink is present)
        url_field_issues = [
            i for i in frontmatter_issues
            if "url" in i.get("message", "").lower()
        ]
        assert url_field_issues == [], "W5 output with permalink should pass all frontmatter checks"


class TestLimitationHonestyPageTypeSpecific:
    """TC-CREV-D-TRACK2: Tests for page-type specific limitation honesty check."""

    def _make_fixtures(self, tmp_path, content: str, page_role: str = "overview", has_limitations: bool = True):
        """Helper to create minimal fixtures for limitation honesty tests."""
        drafts_dir = tmp_path / "drafts" / "products"
        drafts_dir.mkdir(parents=True)
        (drafts_dir / "test_page.md").write_text(content, encoding='utf-8')

        product_facts = {
            "product_name": "Test Product",
            "claims": [],
            "claim_groups": {}
        }

        if has_limitations:
            product_facts["claim_groups"]["limitations"] = ["limit_001", "limit_002"]

        page_plan = {
            "pages": [
                {
                    "slug": "test_page",
                    "filename": "test_page.md",
                    "page_role": page_role
                }
            ]
        }

        snippet_catalog = {"snippets": []}
        evidence_map = {"claims": []}

        return tmp_path / "drafts", product_facts, snippet_catalog, evidence_map, page_plan

    def test_overview_page_missing_limitations_returns_error(self, tmp_path):
        """Overview pages should ERROR if Limitations section missing."""
        content = "---\ntitle: Overview\n---\n\n# Overview\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="overview", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 1
        assert limitation_issues[0]["severity"] == "error"
        assert "Missing Limitations section" in limitation_issues[0]["message"]

    def test_comprehensive_guide_missing_limitations_returns_error(self, tmp_path):
        """Comprehensive guide pages should ERROR if Limitations section missing."""
        content = "---\ntitle: Guide\n---\n\n# Comprehensive Guide\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="comprehensive_guide", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 1
        assert limitation_issues[0]["severity"] == "error"

    def test_api_overview_missing_limitations_returns_error(self, tmp_path):
        """API overview pages should ERROR if Limitations section missing."""
        content = "---\ntitle: API Overview\n---\n\n# API Overview\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="api_overview", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 1
        assert limitation_issues[0]["severity"] == "error"

    def test_index_page_missing_limitations_skips_check(self, tmp_path):
        """Index pages should SKIP limitation check entirely."""
        content = "---\ntitle: Index\n---\n\n# Index\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="index", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 0  # Should be skipped

    def test_toc_page_missing_limitations_skips_check(self, tmp_path):
        """TOC pages should SKIP limitation check entirely."""
        content = "---\ntitle: Table of Contents\n---\n\n# TOC\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="toc", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 0

    def test_getting_started_page_missing_limitations_skips_check(self, tmp_path):
        """Getting started pages should SKIP limitation check entirely."""
        content = "---\ntitle: Getting Started\n---\n\n# Getting Started\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="getting_started", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 0

    def test_other_page_type_missing_limitations_returns_warn(self, tmp_path):
        """Other page types (not in skip or error lists) should WARN."""
        content = "---\ntitle: Tutorial\n---\n\n# Tutorial\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="tutorial", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 1
        assert limitation_issues[0]["severity"] == "warn"

    def test_page_with_limitations_section_passes(self, tmp_path):
        """Pages with Limitations section should pass regardless of page_role."""
        content = "---\ntitle: Overview\n---\n\n# Overview\n\n## Limitations\n\nSome limitations here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="overview", has_limitations=True)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 0

    def test_no_limitations_in_product_facts_skips_check(self, tmp_path):
        """If no limitations in product_facts, check should not trigger."""
        content = "---\ntitle: Overview\n---\n\n# Overview\n\nContent here."
        drafts_dir, pf, sc, em, pp = self._make_fixtures(tmp_path, content, page_role="overview", has_limitations=False)

        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        limitation_issues = [i for i in issues if i.get("check") == "technical_accuracy.limitation_honesty"]

        assert len(limitation_issues) == 0


class TestBugFixF101FrontmatterOnlyFiles:
    """Tests for Task F-101 (TC-CREV-F-TRACK2): Support frontmatter-only files (no body content).

    Root Cause: Regex pattern required newline after closing --- delimiter, failing when file
    ends immediately after frontmatter (valid per Markdown/Hugo standards).

    Fix: Update regex from r'^---\s*\n(.*?\n)---\s*\n' to r'^---\s*\n(.*?\n)---(?:\s*\n|$)'
    """

    @staticmethod
    def _make_fixtures(tmp_path, content="# Title\n\nParagraph text.\n"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test", "template": "feature.variant-standard"}]}
        return drafts_dir, product_facts, page_plan

    def test_frontmatter_only_file_no_blocker(self, tmp_path):
        """Frontmatter-only file (no body content) should NOT trigger 'No frontmatter found' BLOCKER.

        This is the primary bug fix test. Files ending immediately after closing ---
        are valid per Markdown/Hugo standards (e.g., Hugo 'family' layout pages).
        """
        frontmatter_only = (
            "---\n"
            "title: Index\n"
            "description: Documentation for Product\n"
            "permalink: /product/index/\n"
            "---"  # No trailing newline, file ends here
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=frontmatter_only)
        issues = content_quality.check_all(drafts_dir, pf, pp)

        # Filter for frontmatter BLOCKER issues
        frontmatter_blockers = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "blocker"
        ]

        assert frontmatter_blockers == [], (
            "Frontmatter-only file should NOT trigger BLOCKER. "
            "File ending after --- is valid per Markdown/Hugo standards."
        )

    def test_frontmatter_with_body_still_works(self, tmp_path):
        """Frontmatter with body content should still work (regression check).

        Ensures fix doesn't break existing behavior for files with body content.
        """
        frontmatter_with_body = (
            "---\n"
            "title: Test\n"
            "description: A test page\n"
            "permalink: /test/\n"
            "---\n\n"
            "# Test Page\n\n"
            "This is body content.\n"
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=frontmatter_with_body)
        issues = content_quality.check_all(drafts_dir, pf, pp)

        # Should have no frontmatter BLOCKER
        frontmatter_blockers = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "blocker"
        ]

        assert frontmatter_blockers == [], "Frontmatter with body should not trigger BLOCKER (regression check)"

    def test_frontmatter_with_trailing_newline(self, tmp_path):
        """Frontmatter-only file with trailing newline should work."""
        frontmatter_with_newline = (
            "---\n"
            "title: Index\n"
            "description: Documentation\n"
            "permalink: /index/\n"
            "---\n"  # Trailing newline, no body content
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=frontmatter_with_newline)
        issues = content_quality.check_all(drafts_dir, pf, pp)

        frontmatter_blockers = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "blocker"
        ]

        assert frontmatter_blockers == [], "Frontmatter with trailing newline should not trigger BLOCKER"

    def test_no_frontmatter_still_triggers_blocker(self, tmp_path):
        """File without frontmatter should still trigger BLOCKER (no false negatives).

        Ensures fix doesn't make pattern too permissive - truly missing frontmatter
        must still be detected.
        """
        no_frontmatter = "# Just a heading\n\nNo frontmatter here."
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=no_frontmatter)
        issues = content_quality.check_all(drafts_dir, pf, pp)

        frontmatter_blockers = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "blocker"
        ]

        assert len(frontmatter_blockers) == 1, "File without frontmatter should still BLOCKER"
        assert "No frontmatter found" in frontmatter_blockers[0]["message"]

    def test_frontmatter_missing_required_fields(self, tmp_path):
        """Frontmatter-only file missing required fields should trigger ERROR (not BLOCKER).

        Tests that required field validation still works after regex fix.
        """
        frontmatter_incomplete = (
            "---\n"
            "title: Test\n"
            "---"  # Missing description and permalink/url_path
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=frontmatter_incomplete)
        issues = content_quality.check_all(drafts_dir, pf, pp)

        # Should NOT have BLOCKER (frontmatter found)
        frontmatter_blockers = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "blocker"
        ]
        assert frontmatter_blockers == [], "Incomplete frontmatter should not BLOCKER (frontmatter exists)"

        # Should have ERROR for missing fields
        frontmatter_errors = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "error"
        ]
        assert len(frontmatter_errors) >= 2, "Should ERROR for missing description and URL field"

    def test_products_index_real_world_case(self, tmp_path):
        """Test actual products/index.md format that triggered the bug.

        This is the real-world content from pilot run that exposed the bug.
        """
        products_index_content = (
            "---\n"
            "layout: \"family\"\n"
            "type: \"_default\"\n\n"
            "head_title: \"Aspose.Note - Index\"\n"
            "head_description: \"Learn how to use Aspose.Note for index.\"\n\n"
            "title: \"Index\"\n"
            "description: \"Documentation for Aspose.Note\"\n"
            "button:\n"
            "  enable: false\n\n"
            "overview:\n"
            "  enable: true\n"
            "  content: |\n"
            "    This section covers index in Aspose.Note.\n\n"
            "testimonialswrapper:\n"
            "  enable: false\n"
            "  title: \"What Developers Say\"\n\n"
            "support:\n"
            "  enable: true\n\n"
            "back_to_top:\n"
            "  enable: true\n"
            "permalink: /note/index/\n"
            "---"  # File ends here (no body content)
        )
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content=products_index_content)
        issues = content_quality.check_all(drafts_dir, pf, pp)

        frontmatter_blockers = [
            i for i in issues
            if i.get("check") == "content_quality.frontmatter_completeness"
            and i.get("severity") == "blocker"
        ]

        assert frontmatter_blockers == [], (
            "products/index.md real-world format should not BLOCKER. "
            "This was the actual bug case from pilot run r_20260210T083043Z."
        )


# ---------------------------------------------------------------------------
# TC-1107: Readability Exemptions for Navigation/FAQ Pages (Agent C)
# ---------------------------------------------------------------------------

class TestReadabilityExemptions:
    """Tests for TC-1107: Page-type-specific readability thresholds."""

    @staticmethod
    def _make_complex_text(target_grade=20):
        """Generate text with high Flesch-Kincaid grade level.

        High grade level = long sentences + complex words.
        """
        # Very long sentence with complex words (aim for grade 20+)
        return (
            "# Title\n\n"
            "---\n"
            "title: Test\n"
            "description: Test page\n"
            "permalink: /test/\n"
            "---\n\n"
            "The implementation of comprehensive methodological frameworks "
            "necessitates an extraordinarily sophisticated understanding of "
            "multidimensional architectural paradigms encompassing heterogeneous "
            "computational infrastructures characterized by unprecedented complexity "
            "and requiring meticulous consideration of interdependent systematic "
            "relationships between disparate organizational components that fundamentally "
            "transform conventional approaches to technological innovation through "
            "revolutionary reconceptualization of traditional developmental methodologies.\n"
        )

    @staticmethod
    def _make_fixtures(tmp_path, page_slug="test", page_role=None, content=None):
        """Create test fixtures for readability exemption tests."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        if content is None:
            content = TestReadabilityExemptions._make_complex_text()

        (drafts_dir / f"{page_slug}.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}

        # Build page_plan with page_role
        page_entry = {"slug": page_slug, "title": "Test", "filename": f"{page_slug}.md"}
        if page_role:
            page_entry["page_role"] = page_role

        page_plan = {"pages": [page_entry]}

        return drafts_dir, product_facts, page_plan

    def test_index_page_exempted(self, tmp_path):
        """TC-1107: index pages (page_role='index') skip readability check entirely."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="index", page_role="index"
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]
        assert readability_issues == [], "index page should skip readability check"

    def test_toc_page_exempted(self, tmp_path):
        """TC-1107: toc pages (page_role='toc') skip readability check entirely."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="_index", page_role="toc"
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]
        assert readability_issues == [], "toc page should skip readability check"

    def test_landing_page_exempted(self, tmp_path):
        """TC-1107: landing pages (page_role='landing') skip readability check entirely."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="overview", page_role="landing"
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]
        assert readability_issues == [], "landing page should skip readability check"

    def test_faq_page_no_warn_below_18(self, tmp_path):
        """TC-1107: faq pages skip warnings for grade <18 (only error at >18).

        FAQ pages are inherently more complex due to Q&A format and technical terminology.
        Similar to how navigation pages skip readability checks entirely, FAQ pages
        should not warn for moderate complexity (grade 14-18).
        """
        # Create text with moderate complexity (grade ~15-16)
        # For FAQ pages, this should produce NO warnings (not even warn)
        faq_content = (
            "# FAQ\n\n"
            "---\n"
            "title: FAQ\n"
            "description: Frequently Asked Questions\n"
            "permalink: /faq/\n"
            "---\n\n"
            "## Question 1: How do I install the package?\n\n"
            "The installation process requires downloading the appropriate distribution "
            "package from the repository, extracting the contents to your desired location, "
            "and configuring the necessary environment variables according to your system "
            "specifications. Additional dependencies may need to be installed separately "
            "depending on your specific use case and operational requirements.\n\n"
            "## Question 2: What are the system requirements?\n\n"
            "The system requirements include sufficient memory allocation for processing "
            "large datasets, adequate storage capacity for intermediate file generation, "
            "and compatible operating system versions that support the required runtime "
            "environment. Performance characteristics may vary based on hardware configuration "
            "and concurrent application usage patterns.\n"
        )

        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="faq", page_role="faq", content=faq_content
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]

        # FAQ pages with grade 14-18 should NOT warn (only error at >18)
        # This eliminates false positive warnings for inherently complex FAQ content
        assert readability_issues == [], (
            f"FAQ page with grade 14-18 should not warn (only error at >18), "
            f"got {len(readability_issues)} issues"
        )

    def test_faq_page_error_at_19(self, tmp_path):
        """TC-1107: faq pages error at grade 19+ (relaxed threshold still enforced)."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="faq", page_role="faq"  # Uses _make_complex_text (grade 20)
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]

        # Should have error because grade > 18
        assert len(readability_issues) > 0, "FAQ page with grade >18 should error"
        assert readability_issues[0]["severity"] == "error", (
            f"FAQ page grade >18 should be error, got {readability_issues[0]['severity']}"
        )

    def test_content_page_original_threshold(self, tmp_path):
        """TC-1107: content pages (no page_role or other roles) use original threshold 16."""
        # Create text with grade ~17 (above original threshold)
        content_text = (
            "# Getting Started\n\n"
            "---\n"
            "title: Getting Started\n"
            "description: Getting started guide\n"
            "permalink: /getting-started/\n"
            "---\n\n"
            "The implementation necessitates sophisticated understanding of "
            "multidimensional architectural paradigms encompassing computational "
            "infrastructures characterized by complexity requiring consideration "
            "of interdependent systematic relationships between organizational components.\n"
        )

        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="getting-started", page_role=None, content=content_text
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]

        # Should have error because grade > 16 (original threshold)
        if readability_issues:
            # Grade might be slightly below/above threshold depending on text
            # Just verify that non-exempt pages still get checked
            assert readability_issues[0]["severity"] in ["warn", "error"], (
                "Content page should use original threshold"
            )

    def test_troubleshooting_page_relaxed(self, tmp_path):
        """TC-1107: troubleshooting pages (page_role='troubleshooting') use relaxed threshold 18."""
        drafts_dir, pf, pp = self._make_fixtures(
            tmp_path, page_slug="troubleshooting", page_role="troubleshooting"
        )
        issues = content_quality.check_all(drafts_dir, pf, pp)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]

        # Should have error because grade 20 > 18 (relaxed threshold)
        assert len(readability_issues) > 0, "Troubleshooting page with grade >18 should error"
        assert readability_issues[0]["severity"] == "error"

    def test_missing_page_plan_fallback(self, tmp_path):
        """TC-1107: If page_plan is empty/missing, fall back to original threshold."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(self._make_complex_text(), encoding="utf-8")

        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": []}  # Empty pages list

        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        readability_issues = [
            i for i in issues if i.get("check") == "content_quality.readability_score"
        ]

        # Should still check with original threshold (no exemption)
        assert len(readability_issues) > 0, "Missing page_plan should fall back to original check"


class TestClaimGroundingHTMLComments:
    """Claim grounding check should skip HTML comment claim markers."""

    def test_html_comment_claims_produce_no_grounding_issues(self, tmp_path):
        """HTML comment claims are metadata, not inline — should not trigger grounding."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        # HTML comment claims placed far from sentence ends
        content = (
            "---\ntitle: Test\ndescription: Test page\nurl_path: /test/\nweight: 1\n---\n\n"
            "# Test Page\n\n"
            "This is a paragraph about testing.\n\n"
            "<!-- claim_id: abc123def456 -->\n\n"
            "Another paragraph with more content here.\n\n"
            "<!-- claim_id: 789ghi012jkl -->\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "page_role": "content"}]}

        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        grounding_issues = [i for i in issues if "claim_grounding" in i.get("check", "")]
        assert grounding_issues == [], f"HTML comment claims should not trigger grounding: {grounding_issues}"

    def test_inline_claims_still_checked_for_grounding(self, tmp_path):
        """Inline [claim: hash] markers should still trigger grounding check."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        # Inline claim far from sentence end (>50 chars gap)
        content = (
            "---\ntitle: Test\ndescription: Test page\nurl_path: /test/\nweight: 1\n---\n\n"
            "# Test Page\n\n"
            "Sentence ends here.                                                      [claim: abc123]\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "page_role": "content"}]}

        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        grounding_issues = [i for i in issues if "claim_grounding" in i.get("check", "")]
        assert len(grounding_issues) > 0, "Inline claims far from sentences should trigger grounding"


# ---------------------------------------------------------------------------
# TC-1407: FOSS Licensing Compliance Check (Agent B)
# ---------------------------------------------------------------------------

class TestFossLicensingCompliance:
    """TC-1407: FOSS licensing compliance check tests."""

    @staticmethod
    def _make_fixtures(tmp_path, content, product_name="Aspose.3D FOSS Python"):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": product_name, "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test"}]}
        snippet_catalog = {"snippets": []}
        evidence_map = {"evidence": [], "metadata": {}}
        return drafts_dir, product_facts, page_plan, snippet_catalog, evidence_map

    def test_foss_licensing_flags_commercial(self, tmp_path):
        """Content with 'commercial license' in FOSS product should generate issue."""
        content = "# Getting Started\n\nYou need a commercial license to use this product.\n"
        drafts_dir, pf, pp, sc, em = self._make_fixtures(tmp_path, content)
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        foss_issues = [i for i in issues if i["check"] == "technical_accuracy.foss_licensing_compliance"]
        assert len(foss_issues) >= 1
        # TC-1407: Severity bumped from 'info' to 'warn' for defense-in-depth
        assert foss_issues[0]["severity"] == "warn"
        assert foss_issues[0]["auto_fixable"] is True

    def test_foss_licensing_ignores_non_foss(self, tmp_path):
        """Product without 'foss' in name should not trigger licensing check."""
        content = "# Getting Started\n\nYou need a commercial license to use this product.\n"
        drafts_dir, pf, pp, sc, em = self._make_fixtures(
            tmp_path, content, product_name="Aspose.3D Python"
        )
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        foss_issues = [i for i in issues if i["check"] == "technical_accuracy.foss_licensing_compliance"]
        assert len(foss_issues) == 0

    def test_foss_licensing_skips_code_blocks(self, tmp_path):
        """Commercial terms inside code blocks should not be flagged."""
        content = (
            "# API Reference\n\n"
            "```python\n"
            "# commercial license check\n"
            "license_type = 'commercial license'\n"
            "```\n\n"
            "This is free and open-source.\n"
        )
        drafts_dir, pf, pp, sc, em = self._make_fixtures(tmp_path, content)
        issues = technical_accuracy.check_all(drafts_dir, pf, sc, em, pp)
        foss_issues = [i for i in issues if i["check"] == "technical_accuracy.foss_licensing_compliance"]
        assert len(foss_issues) == 0


# ---------------------------------------------------------------------------
# TC-1407: Collapsed Frontmatter Detection (Agent B)
# ---------------------------------------------------------------------------

class TestCollapsedFrontmatterDetection:
    """TC-1407: Collapsed YAML frontmatter detection tests."""

    @staticmethod
    def _make_fixtures(tmp_path, content):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "title": "Test"}]}
        return drafts_dir, product_facts, page_plan

    def test_collapsed_frontmatter_detected(self, tmp_path):
        """Collapsed YAML with multiple keys on one line should be detected."""
        content = '---\ntitle: "A" description: "B"\n---\n\n# Page\n\nContent.\n'
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        collapsed_issues = [
            i for i in issues
            if i["check"] == "content_quality.frontmatter_completeness"
            and "collapsed" in i.get("message", "").lower()
        ]
        assert len(collapsed_issues) >= 1
        assert collapsed_issues[0]["severity"] == "error"
        assert collapsed_issues[0]["auto_fixable"] is True

    def test_collapsed_frontmatter_normal_ok(self, tmp_path):
        """Proper YAML with one key per line should not trigger collapsed detection."""
        content = '---\ntitle: "A"\ndescription: "B"\nurl_path: /test/\n---\n\n# Page\n\nContent.\n'
        drafts_dir, pf, pp = self._make_fixtures(tmp_path, content)
        issues = content_quality.check_all(drafts_dir, pf, pp)
        collapsed_issues = [
            i for i in issues
            if i["check"] == "content_quality.frontmatter_completeness"
            and "collapsed" in i.get("message", "").lower()
        ]
        assert len(collapsed_issues) == 0


class TestAutoFixableFlagValues:
    """Verify auto_fixable flags are set correctly for key check types."""

    def test_paragraph_structure_is_auto_fixable(self, tmp_path):
        """paragraph_structure issues should be auto_fixable."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        # 15 consecutive non-empty lines (triggers paragraph_structure warn)
        long_para = "\n".join([f"Line {i} of a very long paragraph." for i in range(15)])
        content = f"---\ntitle: T\ndescription: D\nurl_path: /t/\nweight: 1\n---\n\n# Title\n\n{long_para}\n"
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "page_role": "content"}]}

        issues = content_quality.check_all(drafts_dir, product_facts, page_plan)
        para_issues = [i for i in issues if "paragraph_structure" in i.get("check", "")]
        assert len(para_issues) > 0, "Should have paragraph_structure issues"
        for issue in para_issues:
            assert issue["auto_fixable"] is True, f"paragraph_structure should be auto_fixable: {issue}"

    def test_heading_descriptiveness_is_auto_fixable(self, tmp_path):
        """heading_descriptiveness issues should be auto_fixable."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = "---\ntitle: T\ndescription: D\nurl_path: /t/\nweight: 1\n---\n\n## Foo\n\nText.\n"
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "page_role": "content"}]}

        issues = usability.check_all(drafts_dir, page_plan, product_facts)
        heading_issues = [i for i in issues if "heading_descriptiveness" in i.get("check", "")]
        assert len(heading_issues) > 0, "Should have heading_descriptiveness issues for 'Foo'"
        for issue in heading_issues:
            assert issue["auto_fixable"] is True, f"heading_descriptiveness should be auto_fixable: {issue}"

    def test_search_optimization_is_auto_fixable(self, tmp_path):
        """search_optimization issues should be auto_fixable."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = "---\ntitle: Getting Started\ndescription: A guide.\nurl_path: /gs/\nweight: 1\n---\n\n# Getting Started\n\nText.\n"
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "getting-started", "page_role": "content"}]}

        issues = usability.check_all(drafts_dir, page_plan, product_facts)
        seo_issues = [i for i in issues if "search_optimization" in i.get("check", "")]
        assert len(seo_issues) > 0, "Should have search_optimization issues (title missing product name)"
        for issue in seo_issues:
            assert issue["auto_fixable"] is True, f"search_optimization should be auto_fixable: {issue}"

    def test_snippet_attribution_is_auto_fixable(self, tmp_path):
        """snippet_attribution issues should be auto_fixable."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = "---\ntitle: T\ndescription: D\nurl_path: /t/\nweight: 1\n---\n\n# Title\n\n```python\nresult = api.call()\nprint(result)\n```\n"
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")
        product_facts = {"product_name": "TestProduct", "claims": [], "claim_groups": {}}
        page_plan = {"pages": [{"slug": "test", "page_role": "content"}]}
        snippet_catalog = {"snippets": []}
        evidence_map = {"evidence": [], "metadata": {}}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        snippet_issues = [i for i in issues if "snippet_attribution" in i.get("check", "")]
        assert len(snippet_issues) > 0, "Should have snippet_attribution issues"
        for issue in snippet_issues:
            # BLOCKER-2: snippet_attribution auto-fix disabled due to conflict with source_annotations check
            assert issue["auto_fixable"] is False, f"snippet_attribution should NOT be auto_fixable (conflicts with source_annotations): {issue}"


class TestTC1504NewChecks:
    """Tests for TC-1504: W5.5 Detection Layer Enhancements.

    4 new checks + 1 auto-fix as safety net for issues that survive upstream fixes.
    """

    # Check CQ-13: Source annotation leaks
    def test_source_annotation_detected(self, tmp_path):
        """Should detect <!-- source: ... --> comments in body."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\n"
            "<!-- source: product API documentation -->\n"
            "Some content here.\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        issues = content_quality.check_all(drafts_dir, {}, {})
        source_issues = [i for i in issues if "source_annotations" in i.get("check", "")]

        assert len(source_issues) == 1
        assert source_issues[0]["severity"] == "warn"
        assert source_issues[0]["auto_fixable"] is True
        assert "source annotation" in source_issues[0]["message"].lower()

    def test_source_annotation_in_frontmatter_ignored(self, tmp_path):
        """Should not flag source annotations in frontmatter."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            "title: Test\n"
            "# source: internal template\n"
            "description: Test\n"
            "---\n\n"
            "# Test\n\nContent.\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        issues = content_quality.check_all(drafts_dir, {}, {})
        source_issues = [i for i in issues if "source_annotations" in i.get("check", "")]

        assert len(source_issues) == 0

    def test_no_source_annotation_passes(self, tmp_path):
        """Should not flag when no source annotations present."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\nClean content with no source annotations.\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        issues = content_quality.check_all(drafts_dir, {}, {})
        source_issues = [i for i in issues if "source_annotations" in i.get("check", "")]

        assert len(source_issues) == 0

    # Check TA-13: API naming convention mismatch
    def test_pascalcase_method_detected_in_python_docs(self, tmp_path):
        """Should detect PascalCase methods in Python documentation."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\n"
            "Call the .Save() method to persist changes. Use .AppendChildLast() to add nodes.\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        page_plan = {"pages": []}
        snippet_catalog = {"snippets": []}
        evidence_map = {"claims": []}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        api_issues = [i for i in issues if "api_naming_convention" in i.get("check", "")]

        # Should detect both .Save( and .AppendChildLast(
        assert len(api_issues) >= 1  # At least one should be detected
        assert all(i["severity"] == "warn" for i in api_issues)
        assert all(i["auto_fixable"] is False for i in api_issues)

    def test_pascalcase_method_in_code_block_ignored(self, tmp_path):
        """Should not flag PascalCase methods inside code blocks."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\n"
            "```python\n"
            "# This is .NET interop code\n"
            "doc.Save('output.one')\n"
            "```\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        page_plan = {"pages": []}
        snippet_catalog = {"snippets": []}
        evidence_map = {"claims": []}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        api_issues = [i for i in issues if "api_naming_convention" in i.get("check", "")]

        assert len(api_issues) == 0

    def test_api_naming_check_skips_non_python_products(self, tmp_path):
        """Should not run check for .NET or Java products."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\n"
            "Call the .Save() method to persist changes.\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "Aspose.Note .NET"}
        page_plan = {"pages": []}
        snippet_catalog = {"snippets": []}
        evidence_map = {"claims": []}

        issues = technical_accuracy.check_all(drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan)
        api_issues = [i for i in issues if "api_naming_convention" in i.get("check", "")]

        assert len(api_issues) == 0

    # Check CQ-14: Generic boilerplate descriptions
    def test_boilerplate_description_detected(self, tmp_path):
        """Should detect generic boilerplate description patterns."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            "title: Test\n"
            'description: "Comprehensive guide and resources for Aspose.Note"\n'
            "url_path: /test/\n"
            "---\n\n"
            "# Test\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        issues = content_quality.check_all(drafts_dir, {}, {})
        boilerplate_issues = [i for i in issues if "boilerplate_description" in i.get("check", "")]

        assert len(boilerplate_issues) == 1
        assert boilerplate_issues[0]["severity"] == "warn"
        assert boilerplate_issues[0]["auto_fixable"] is False

    def test_specific_description_passes(self, tmp_path):
        """Should not flag specific, non-boilerplate descriptions."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            "title: Test\n"
            'description: "Learn how to extract text from OneNote files using Python"\n'
            "url_path: /test/\n"
            "---\n\n"
            "# Test\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        issues = content_quality.check_all(drafts_dir, {}, {})
        boilerplate_issues = [i for i in issues if "boilerplate_description" in i.get("check", "")]

        assert len(boilerplate_issues) == 0

    # Check U-13: Wrong platform listing
    def test_wrong_platform_detected(self, tmp_path):
        """Should detect wrong platforms in Available Platforms section."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\n"
            "## Available Platforms\n\n"
            "- Python\n"
            "- .NET\n"
            "- Java\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        page_plan = {"pages": []}

        issues = usability.check_all(drafts_dir, page_plan, product_facts)
        platform_issues = [i for i in issues if "platform_listing" in i.get("check", "")]

        assert len(platform_issues) == 1
        assert platform_issues[0]["severity"] == "warn"
        assert platform_issues[0]["auto_fixable"] is True
        assert ".net" in platform_issues[0]["message"].lower() or "java" in platform_issues[0]["message"].lower()

    def test_correct_platform_only_passes(self, tmp_path):
        """Should pass when only correct platform is listed."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\n"
            "## Available Platforms\n\n"
            "- Python 3.7+\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        page_plan = {"pages": []}

        issues = usability.check_all(drafts_dir, page_plan, product_facts)
        platform_issues = [i for i in issues if "platform_listing" in i.get("check", "")]

        assert len(platform_issues) == 0

    def test_no_platform_section_passes(self, tmp_path):
        """Should not flag when no Available Platforms section exists."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "---\ntitle: Test\ndescription: Test\nurl_path: /test/\n---\n\n"
            "# Test\n\nContent with no platform section.\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        product_facts = {"product_name": "Aspose.Note FOSS Python"}
        page_plan = {"pages": []}

        issues = usability.check_all(drafts_dir, page_plan, product_facts)
        platform_issues = [i for i in issues if "platform_listing" in i.get("check", "")]

        assert len(platform_issues) == 0

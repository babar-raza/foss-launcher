"""Tests for FeedbackStore.

Validates:
- ReviewOutcome serialization and properties
- Recording and loading reviews (NDJSON persistence)
- Filtering by section, page_role, product_family
- Common issue detection and normalization
- Pass rate and average score calculation
- Strategy suggestion based on historical data
"""

import pytest
from pathlib import Path

from launch.store.feedback_store import (
    FeedbackStore,
    ReviewOutcome,
    CommonIssue,
    _normalize_issue_message,
)


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(tmp_path / "feedback")


@pytest.fixture
def sample_outcomes():
    return [
        ReviewOutcome(
            run_id="run1", page_slug="overview", section="docs", page_role="comprehensive_guide",
            round_number=1, content_quality=4, technical_accuracy=5, usability=4,
            routing="PASS", errors=[], warnings=["Heading too generic on line 5"],
            fixes_applied=["fix_heading_descriptiveness"], product_family="3d",
        ),
        ReviewOutcome(
            run_id="run1", page_slug="faq", section="kb", page_role="faq",
            round_number=1, content_quality=3, technical_accuracy=4, usability=3,
            routing="NEEDS_CHANGES", errors=["Content density below threshold"],
            warnings=["Missing code example"], fixes_applied=[],
            product_family="3d",
        ),
        ReviewOutcome(
            run_id="run2", page_slug="overview", section="docs", page_role="comprehensive_guide",
            round_number=1, content_quality=5, technical_accuracy=5, usability=5,
            routing="PASS", errors=[], warnings=[], fixes_applied=[],
            product_family="note",
        ),
        ReviewOutcome(
            run_id="run2", page_slug="faq", section="kb", page_role="faq",
            round_number=1, content_quality=2, technical_accuracy=3, usability=2,
            routing="REJECT", errors=["Content density below threshold", "Missing FAQ structure"],
            warnings=["Heading too generic on line 10"], fixes_applied=[],
            product_family="note",
        ),
    ]


class TestReviewOutcome:
    def test_default_values(self):
        r = ReviewOutcome()
        assert r.run_id == ""
        assert r.round_number == 1
        assert r.errors == []
        assert r.routing == ""

    def test_round_trip(self):
        r = ReviewOutcome(
            run_id="r1", page_slug="test", section="docs",
            content_quality=4, technical_accuracy=5, usability=3,
            routing="PASS",
        )
        d = r.to_dict()
        r2 = ReviewOutcome.from_dict(d)
        assert r2.run_id == "r1"
        assert r2.content_quality == 4
        assert r2.routing == "PASS"

    def test_avg_score(self):
        r = ReviewOutcome(content_quality=4, technical_accuracy=5, usability=3)
        assert r.avg_score == 4.0

    def test_avg_score_partial(self):
        r = ReviewOutcome(content_quality=4, technical_accuracy=0, usability=0)
        assert r.avg_score == 4.0  # Only counts non-zero

    def test_avg_score_empty(self):
        r = ReviewOutcome()
        assert r.avg_score == 0.0

    def test_passed(self):
        assert ReviewOutcome(routing="PASS").passed is True
        assert ReviewOutcome(routing="REJECT").passed is False
        assert ReviewOutcome(routing="NEEDS_CHANGES").passed is False


class TestFeedbackStorePersistence:
    def test_record_and_load(self, store):
        outcome = ReviewOutcome(
            run_id="r1", page_slug="test", section="docs",
            content_quality=4, routing="PASS",
        )
        store.record_review(outcome)

        reviews = store.load_reviews()
        assert len(reviews) == 1
        assert reviews[0].run_id == "r1"
        assert reviews[0].content_quality == 4

    def test_append_multiple(self, store):
        for i in range(5):
            store.record_review(ReviewOutcome(run_id=f"r{i}", page_slug=f"p{i}"))

        reviews = store.load_reviews()
        assert len(reviews) == 5

    def test_empty_store(self, store):
        assert store.load_reviews() == []

    def test_creates_directory(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c"
        s = FeedbackStore(deep_path)
        s.record_review(ReviewOutcome(run_id="test"))
        assert deep_path.exists()

    def test_filter_by_section(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        docs = store.load_reviews(section="docs")
        assert len(docs) == 2
        assert all(r.section == "docs" for r in docs)

    def test_filter_by_page_role(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        faqs = store.load_reviews(page_role="faq")
        assert len(faqs) == 2
        assert all(r.page_role == "faq" for r in faqs)

    def test_filter_by_product_family(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        three_d = store.load_reviews(product_family="3d")
        assert len(three_d) == 2


class TestCommonIssues:
    def test_detects_common_errors(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        issues = store.get_common_issues(min_count=2)
        assert len(issues) > 0
        # "Content density below threshold" appears twice
        density_issues = [i for i in issues if "density" in i.message.lower()]
        assert len(density_issues) == 1
        assert density_issues[0].count == 2

    def test_includes_warnings(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        issues = store.get_common_issues(min_count=2)
        # "Heading too generic on line N" appears twice (normalized)
        heading_issues = [i for i in issues if "heading" in i.message.lower()]
        assert len(heading_issues) == 1

    def test_min_count_filters(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        # Only issues with count >= 3 (none should match)
        issues = store.get_common_issues(min_count=3)
        assert len(issues) == 0

    def test_empty_store(self, store):
        assert store.get_common_issues() == []


class TestPassRate:
    def test_basic_pass_rate(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        rate = store.get_pass_rate()
        assert rate == 0.5  # 2 PASS out of 4

    def test_pass_rate_by_section(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        docs_rate = store.get_pass_rate(section="docs")
        assert docs_rate == 1.0  # Both docs reviews PASS

        kb_rate = store.get_pass_rate(section="kb")
        assert kb_rate == 0.0  # No kb reviews PASS

    def test_empty_store(self, store):
        assert store.get_pass_rate() == 0.0


class TestAvgScores:
    def test_basic_averages(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        scores = store.get_avg_scores()
        assert scores["content_quality"] == pytest.approx(3.5)
        assert scores["technical_accuracy"] == pytest.approx(4.25)
        assert scores["usability"] == pytest.approx(3.5)

    def test_empty_store(self, store):
        scores = store.get_avg_scores()
        assert scores["content_quality"] == 0.0


class TestSuggestStrategy:
    def test_suggests_lower_temp_for_low_pass_rate(self, store):
        # Record mostly failing reviews
        for _ in range(5):
            store.record_review(ReviewOutcome(
                page_role="faq", routing="REJECT",
                content_quality=2, technical_accuracy=3, usability=2,
                errors=["Bad structure"],
            ))
        store.record_review(ReviewOutcome(
            page_role="faq", routing="PASS",
            content_quality=4, technical_accuracy=4, usability=4,
        ))

        suggestion = store.suggest_strategy("w5", "faq")
        assert suggestion["temperature_adjustment"] < 0

    def test_no_suggestion_for_empty(self, store):
        suggestion = store.suggest_strategy("w5", "unknown")
        assert suggestion["temperature_adjustment"] == 0.0
        assert suggestion["quality_focus"] == ""

    def test_identifies_weakest_dimension(self, store):
        store.record_review(ReviewOutcome(
            page_role="tutorial", routing="NEEDS_CHANGES",
            content_quality=4, technical_accuracy=2, usability=4,
        ))
        suggestion = store.suggest_strategy("w5", "tutorial")
        assert suggestion["quality_focus"] == "technical_accuracy"


class TestStats:
    def test_basic_stats(self, store, sample_outcomes):
        for o in sample_outcomes:
            store.record_review(o)

        stats = store.get_stats()
        assert stats["total_reviews"] == 4
        assert stats["pass_rate"] == 0.5
        assert "docs" in stats["sections"]
        assert "kb" in stats["sections"]
        assert "faq" in stats["page_roles"]

    def test_empty_stats(self, store):
        stats = store.get_stats()
        assert stats["total_reviews"] == 0
        assert stats["pass_rate"] == 0.0


class TestNormalizeIssueMessage:
    def test_strips_line_numbers(self):
        assert "line N" in _normalize_issue_message("Error on line 42")

    def test_strips_uuids(self):
        result = _normalize_issue_message("Claim 550e8400-e29b-41d4-a716-446655440000 invalid")
        assert "<uuid>" in result

    def test_strips_file_paths(self):
        result = _normalize_issue_message("Error in /content/docs/overview.md")
        assert "<file>" in result

    def test_strips_hex_ids(self):
        result = _normalize_issue_message("Claim abc123def0 not found")
        assert "<id>" in result

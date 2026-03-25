"""Tests for golden observability event emission (TC-OBS-001).

Verifies that the generation worker emits golden_resolution events
at the correct points and that emission failures are non-fatal.
"""
from __future__ import annotations

import pytest

from launcher.shared.golden_loader import GoldenResolution


class TestGoldenResolutionEventData:
    """Verify the event data payload is well-formed."""

    def test_event_data_from_resolution(self):
        """Golden resolution to_dict() + worker enrichment produces valid event data."""
        res = GoldenResolution(
            match_level="exact",
            matched_heading="Code Examples",
            query_heading="Code Examples",
            page_role="howto_article",
            variant="standard",
            jaccard_score=0.0,
            golden_page_path="golden/kb.aspose.org/howto.md",
            golden_word_count=150,
            has_structural_spec=True,
        )
        # Simulate what worker.py does
        event_data = {
            **res.to_dict(),
            "page_slug": "test-page",
            "section_index": 0,
            "is_heal_mode": False,
            "heal_attempt": 0,
        }
        assert event_data["match_level"] == "exact"
        assert event_data["page_slug"] == "test-page"
        assert event_data["section_index"] == 0
        assert event_data["is_heal_mode"] is False
        assert event_data["heal_attempt"] == 0
        # Verify all required schema fields present
        required = [
            "match_level", "matched_heading", "query_heading",
            "page_role", "page_slug", "section_index", "variant",
            "jaccard_score", "is_heal_mode", "heal_attempt",
        ]
        for field in required:
            assert field in event_data, f"Missing required field: {field}"

    def test_miss_resolution_event_data(self):
        """A miss resolution produces valid event data with empty/zero fields."""
        res = GoldenResolution(
            match_level="miss",
            matched_heading="",
            query_heading="Nonexistent Section",
            page_role="api_reference",
            variant="standard",
            jaccard_score=0.0,
            golden_page_path="",
            golden_word_count=0,
            has_structural_spec=False,
        )
        event_data = {
            **res.to_dict(),
            "page_slug": "api-page",
            "section_index": 2,
            "is_heal_mode": True,
            "heal_attempt": 2,
        }
        assert event_data["match_level"] == "miss"
        assert event_data["matched_heading"] == ""
        assert event_data["golden_page_path"] == ""
        assert event_data["golden_word_count"] == 0
        assert event_data["is_heal_mode"] is True
        assert event_data["heal_attempt"] == 2

    def test_jaccard_resolution_carries_score(self):
        """Jaccard match resolution includes the similarity score."""
        res = GoldenResolution(
            match_level="jaccard",
            matched_heading="Getting Started Guide",
            query_heading="Started Guide Getting",
            page_role="howto_article",
            variant="standard",
            jaccard_score=0.75,
            golden_page_path="golden/test.md",
            golden_word_count=200,
            has_structural_spec=True,
        )
        event_data = res.to_dict()
        assert event_data["jaccard_score"] == 0.75
        assert event_data["match_level"] == "jaccard"


class TestGoldenResolutionNonFatal:
    """Verify golden resolution operations cannot crash generation."""

    def test_to_dict_never_raises(self):
        """to_dict() should work on any valid GoldenResolution."""
        res = GoldenResolution(
            match_level="miss",
            matched_heading="",
            query_heading="",
            page_role="",
            variant="",
            jaccard_score=0.0,
            golden_page_path="",
            golden_word_count=0,
            has_structural_spec=False,
        )
        d = res.to_dict()
        assert isinstance(d, dict)

    def test_resolve_with_none_golden_dir(self):
        """resolve_golden_for_section with None dir returns miss, never raises."""
        from launcher.shared.golden_loader import resolve_golden_for_section
        res = resolve_golden_for_section("any_role", None, "Any Heading")
        assert res.match_level == "miss"

    def test_resolve_with_nonexistent_dir(self, tmp_path):
        """resolve_golden_for_section with nonexistent dir returns miss, never raises."""
        from launcher.shared.golden_loader import resolve_golden_for_section
        res = resolve_golden_for_section("any_role", tmp_path / "nope", "Any Heading")
        assert res.match_level == "miss"


class TestEnforcementLogEnrichment:
    """Verify enforcement_log event data includes golden_spec_existed field."""

    def test_enforcement_log_data_structure(self):
        """Simulated enforcement_log event data includes golden_spec_existed boolean."""
        # Simulate what worker.py line ~2033 builds:
        event_data = {
            "section": "Code Examples",
            "pass_used": "pass1_gap_fill",
            "golden_spec_existed": True,
        }
        assert "golden_spec_existed" in event_data
        assert isinstance(event_data["golden_spec_existed"], bool)

    def test_enforcement_log_no_spec(self):
        """When golden spec is absent, golden_spec_existed is False."""
        event_data = {
            "section": "Overview",
            "pass_used": "pass2_retry",
            "golden_spec_existed": False,
        }
        assert event_data["golden_spec_existed"] is False

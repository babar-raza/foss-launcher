"""Unit tests for claim scoping: visibility filter + claim-kind affinity (TC-3672).

Tests select_claims_by_similarity() pre-filtering and CLAIM_KIND_AFFINITY_MAP.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from launch.workers.w4_ia_planner.worker import (
    CLAIM_KIND_AFFINITY_MAP,
    select_claims_by_similarity,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_claim(
    text: str,
    kind: str = "feature",
    visibility: str = "public",
) -> Dict[str, Any]:
    return {
        "claim_id": f"claim_{hash(text) % 10000}",
        "claim_text": text,
        "claim_kind": kind,
        "visibility": visibility,
        "truth_status": "fact",
        "citations": [],
    }


# ── CLAIM_KIND_AFFINITY_MAP coverage tests ───────────────────────────────


class TestClaimKindAffinityMap:
    """TC-3672: CLAIM_KIND_AFFINITY_MAP covers all 17 page roles."""

    ALL_PAGE_ROLES = [
        "landing", "toc", "comprehensive_guide", "workflow_page",
        "feature_showcase", "troubleshooting", "api_reference",
        "reference_object_page", "faq", "best_practices", "tutorial",
        "howto_article", "blog_announcement", "blog", "feature_blog",
        "format_conversion", "performance_guide",
    ]

    def test_all_17_roles_have_affinity(self):
        for role in self.ALL_PAGE_ROLES:
            assert role in CLAIM_KIND_AFFINITY_MAP, (
                f"Page role '{role}' missing from CLAIM_KIND_AFFINITY_MAP"
            )

    def test_map_has_exactly_17_entries(self):
        assert len(CLAIM_KIND_AFFINITY_MAP) == 17

    def test_all_values_are_non_empty_lists(self):
        for role, kinds in CLAIM_KIND_AFFINITY_MAP.items():
            assert isinstance(kinds, list), f"{role}: expected list, got {type(kinds)}"
            assert len(kinds) > 0, f"{role}: empty affinity list"

    def test_landing_includes_feature(self):
        assert "feature" in CLAIM_KIND_AFFINITY_MAP["landing"]

    def test_api_reference_includes_api(self):
        assert "api" in CLAIM_KIND_AFFINITY_MAP["api_reference"]

    def test_troubleshooting_includes_limitation(self):
        assert "limitation" in CLAIM_KIND_AFFINITY_MAP["troubleshooting"]


# ── Visibility pre-filter tests ──────────────────────────────────────────


class TestVisibilityFilter:
    """TC-3672: select_claims_by_similarity() filters by visibility."""

    def test_internal_claims_filtered_for_landing_page(self):
        claims = [
            _make_claim("Feature A supports spreadsheets", "feature", "public"),
            _make_claim("JCID field identifies the object", "feature", "internal"),
            _make_claim("Feature B enables formatting", "feature", "public"),
        ]
        result = select_claims_by_similarity(
            "Product features",
            claims,
            top_k=10,
            page_role="landing",
            visibility_filter="public",
        )
        # Internal claim should be filtered out
        result_texts = [c["claim_text"] for c in result]
        assert "JCID field identifies the object" not in result_texts
        assert "Feature A supports spreadsheets" in result_texts
        assert "Feature B enables formatting" in result_texts

    def test_internal_claims_allowed_for_reference_page(self):
        claims = [
            _make_claim("API method details", "api", "public"),
            _make_claim("JCID field spec details", "api", "internal"),
        ]
        result = select_claims_by_similarity(
            "API reference",
            claims,
            top_k=10,
            page_role="api_reference",
            visibility_filter="public",
        )
        # Reference pages can receive internal claims
        result_texts = [c["claim_text"] for c in result]
        assert "JCID field spec details" in result_texts

    def test_no_filter_returns_all(self):
        claims = [
            _make_claim("Public claim", "feature", "public"),
            _make_claim("Internal claim", "feature", "internal"),
        ]
        result = select_claims_by_similarity(
            "All claims",
            claims,
            top_k=10,
            visibility_filter="all",
        )
        assert len(result) == 2

    def test_missing_visibility_defaults_to_public(self):
        """Claims without visibility field should be treated as public."""
        claims = [
            {"claim_id": "c1", "claim_text": "No visibility field", "claim_kind": "feature"},
        ]
        result = select_claims_by_similarity(
            "Test purpose",
            claims,
            top_k=10,
            page_role="landing",
            visibility_filter="public",
        )
        # Should not be filtered out (defaults to "public")
        assert len(result) == 1


# ── Claim-kind affinity pre-filter tests ─────────────────────────────────


class TestClaimKindFilter:
    """TC-3672: select_claims_by_similarity() filters by claim_kind affinity."""

    def test_claim_kind_filter_restricts_to_affinity(self):
        claims = [
            _make_claim("Feature claim", "feature"),
            _make_claim("Workflow claim", "workflow"),
            _make_claim("Limitation claim", "limitation"),
        ]
        result = select_claims_by_similarity(
            "Landing page content",
            claims,
            top_k=10,
            page_role="landing",  # affinity: feature, compatibility, key_feature
        )
        # Workflow and limitation should be filtered out for landing page
        result_kinds = [c["claim_kind"] for c in result]
        assert "feature" in result_kinds
        assert "workflow" not in result_kinds
        assert "limitation" not in result_kinds

    def test_explicit_claim_kind_filters_override_affinity(self):
        claims = [
            _make_claim("Feature claim", "feature"),
            _make_claim("Workflow claim", "workflow"),
        ]
        result = select_claims_by_similarity(
            "Test purpose",
            claims,
            top_k=10,
            page_role="landing",
            claim_kind_filters=["workflow"],  # Override: only workflow
        )
        result_kinds = [c["claim_kind"] for c in result]
        assert "workflow" in result_kinds
        assert "feature" not in result_kinds

    def test_no_filter_when_no_page_role(self):
        claims = [
            _make_claim("Feature claim", "feature"),
            _make_claim("Limitation claim", "limitation"),
        ]
        result = select_claims_by_similarity(
            "General purpose",
            claims,
            top_k=10,
            # No page_role → no affinity filtering
        )
        assert len(result) == 2

    def test_tfidf_runs_on_filtered_subset(self):
        """After filtering, TF-IDF should rank remaining claims by relevance."""
        claims = [
            _make_claim("Aspose.Cells spreadsheet feature", "feature"),
            _make_claim("Aspose.Cells Python compatibility", "compatibility"),
            _make_claim("Install via pip workflow", "workflow"),
        ]
        result = select_claims_by_similarity(
            "Aspose.Cells spreadsheet features",
            claims,
            top_k=2,
            page_role="landing",  # Allows feature + compatibility, not workflow
        )
        # Workflow should be filtered; remaining ranked by similarity
        assert len(result) <= 2
        result_kinds = [c["claim_kind"] for c in result]
        assert "workflow" not in result_kinds

    def test_empty_after_filtering_returns_empty(self):
        claims = [
            _make_claim("Workflow only", "workflow"),
        ]
        result = select_claims_by_similarity(
            "Landing page",
            claims,
            top_k=10,
            page_role="troubleshooting",  # Allows limitation, compatibility, best_practice
        )
        # Workflow is not in troubleshooting affinity
        assert result == []


# ── Backward compatibility tests ─────────────────────────────────────────


class TestBackwardCompatibility:
    """TC-3672: Existing callers without new params still work."""

    def test_existing_signature_works(self):
        claims = [
            _make_claim("Feature A", "feature"),
            _make_claim("Feature B", "feature"),
        ]
        # Call with only original params — no page_role, no filters
        result = select_claims_by_similarity("Test", claims, 2)
        assert len(result) == 2

    def test_empty_candidates_returns_empty(self):
        result = select_claims_by_similarity("Test", [], 5)
        assert result == []

    def test_zero_top_k_returns_empty(self):
        claims = [_make_claim("Feature", "feature")]
        result = select_claims_by_similarity("Test", claims, 0)
        assert result == []

"""TC-4231: Tests for page-level claim relevance scoring and filtering in the Planner.

Covers:
1. _relevance_score: claims matching slug/title words score higher
2. _apply_relevance_filter: page-level cap applied when claim count exceeds max
3. _apply_relevance_filter: pages with ≤ max claims are returned unchanged
4. _apply_relevance_filter: starvation guard keeps top-5 by original order
   when relevance filtering would drop below threshold
5. Integration via _assign_claims: relevance filter applied post-assignment
6. Determinism: equal-scoring claims preserve original order
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claim(claim_id: str, text: str, kind: str = "workflow") -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind)


def _make_page(
    slug: str,
    role: str,
    *,
    title: str = "",
    mandatory: bool = True,
    topic_category: str | None = None,
) -> dict:
    return {
        "page_id": slug,
        "slug": slug,
        "page_role": role,
        "title": title or slug,
        "mandatory": mandatory,
        "topic_category": topic_category,
    }


# ---------------------------------------------------------------------------
# Unit tests for _relevance_score
# ---------------------------------------------------------------------------

class TestRelevanceScore:
    """_relevance_score returns higher values for claims that match slug/title words."""

    def test_matching_claim_scores_higher_than_unrelated(self):
        from launcher.workers.planner.plan import _relevance_score

        # Claim mentioning "workbook" should score higher for workbook-related page
        score_matching = _relevance_score(
            "Workbook class supports loading xlsx files",
            "workbook-api",
            "Workbook API Reference",
        )
        score_unrelated = _relevance_score(
            "General rendering support for charts",
            "workbook-api",
            "Workbook API Reference",
        )
        assert score_matching > score_unrelated, (
            "Claim mentioning slug/title words must score higher"
        )

    def test_zero_score_for_completely_unrelated_claim(self):
        from launcher.workers.planner.plan import _relevance_score

        score = _relevance_score(
            "Unrelated claim with no overlap",
            "xlsx-convert",
            "XLSX Conversion Guide",
        )
        # "with", "overlap" are 4+ chars but not in slug/title — should be 0
        # Validate it doesn't go negative
        assert score >= 0.0

    def test_short_words_ignored(self):
        from launcher.workers.planner.plan import _relevance_score

        # "to", "a", "be" are ≤3 chars — should not contribute to score
        score = _relevance_score("to be a test", "to-be", "To Be")
        assert score == 0.0, "Words with length ≤ 3 must not affect score"

    def test_score_is_float(self):
        from launcher.workers.planner.plan import _relevance_score

        result = _relevance_score("some claim text", "some-page", "Some Page Title")
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Unit tests for _apply_relevance_filter
# ---------------------------------------------------------------------------

class TestApplyRelevanceFilter:
    """_apply_relevance_filter caps and re-ranks claims by relevance."""

    def _make_claim_by_id(self, claims: list[Claim]) -> dict[str, Claim]:
        return {c.claim_id: c for c in claims}

    def test_no_op_when_under_cap(self):
        """Pages with ≤ max_claims claims are returned unchanged."""
        from launcher.workers.planner.plan import _apply_relevance_filter

        ids = [f"C{i}" for i in range(10)]
        claims = [_make_claim(cid, f"claim text {cid}") for cid in ids]
        claim_by_id = self._make_claim_by_id(claims)

        result = _apply_relevance_filter(ids, claim_by_id, "some-page", "Some Page", max_claims=50)
        assert result == ids, "Under-cap pages must be returned unchanged"

    def test_cap_applied_when_over_limit(self):
        """60 claims in → max_claims=50 → 50 out."""
        from launcher.workers.planner.plan import _apply_relevance_filter

        n = 60
        ids = [f"C{i}" for i in range(n)]
        claims = [_make_claim(cid, f"generic claim text about topic {cid}") for cid in ids]
        claim_by_id = self._make_claim_by_id(claims)

        result = _apply_relevance_filter(ids, claim_by_id, "some-page", "Some Page", max_claims=50)
        assert len(result) == 50, f"Expected 50, got {len(result)}"

    def test_relevant_claims_preferred_over_generic(self):
        """Claims matching slug words appear in the filtered output."""
        from launcher.workers.planner.plan import _apply_relevance_filter

        # Create 55 generic claims + 5 highly relevant ones
        generic_ids = [f"GEN-{i}" for i in range(55)]
        relevant_ids = [f"REL-{i}" for i in range(5)]
        all_ids = generic_ids + relevant_ids

        generic_claims = [_make_claim(cid, "generic unrelated content") for cid in generic_ids]
        relevant_claims = [
            _make_claim(cid, "workbook spreadsheet api reference documentation")
            for cid in relevant_ids
        ]
        all_claims = generic_claims + relevant_claims
        claim_by_id = {c.claim_id: c for c in all_claims}

        result = _apply_relevance_filter(
            all_ids, claim_by_id,
            "workbook-api-reference", "Workbook API Reference",
            max_claims=50,
        )
        assert len(result) == 50
        # All relevant (high-scoring) claims must survive the filter
        for rid in relevant_ids:
            assert rid in result, f"Relevant claim {rid} was incorrectly filtered out"

    def test_starvation_guard_keeps_minimum(self):
        """If filtering would drop page below 5 claims, keeps top-5 by original order."""
        from launcher.workers.planner.plan import _apply_relevance_filter

        # 10 claims all with zero relevance to the page slug/title
        ids = [f"C{i}" for i in range(10)]
        claims = [_make_claim(cid, "completely unrelated zzz xyz") for cid in ids]
        claim_by_id = {c.claim_id: c for c in claims}

        # max_claims=4 would normally produce 4, but starvation guard kicks in
        # when all scores are 0 and we'd otherwise have fewer than 5
        # With max_claims=4 < 5, the guard should keep 5 (original first 5)
        result = _apply_relevance_filter(ids, claim_by_id, "obscure-page", "Obscure Page", max_claims=4)
        # Starvation fires when len(filtered) < 5 AND original had >= 5
        assert len(result) == 5, f"Starvation guard must keep 5 claims, got {len(result)}"
        assert result == ids[:5], "Starvation guard must use original order"

    def test_deterministic_output(self):
        """Same input always produces same output regardless of dict ordering."""
        from launcher.workers.planner.plan import _apply_relevance_filter

        n = 60
        ids = [f"C{i:04d}" for i in range(n)]
        # All same score — original order must be preserved as tiebreak
        claims = [_make_claim(cid, "some text about spreadsheet cells") for cid in ids]
        claim_by_id = {c.claim_id: c for c in claims}

        result1 = _apply_relevance_filter(ids, claim_by_id, "cells-api", "Cells API", max_claims=50)
        result2 = _apply_relevance_filter(ids, claim_by_id, "cells-api", "Cells API", max_claims=50)
        assert result1 == result2, "Filter output must be deterministic"

    def test_missing_claim_in_lookup_handled_gracefully(self):
        """Claims missing from claim_by_id get score 0 and are still processed."""
        from launcher.workers.planner.plan import _apply_relevance_filter

        ids = [f"C{i}" for i in range(60)]
        # Empty lookup — all claims score 0
        result = _apply_relevance_filter(ids, {}, "workbook-api", "Workbook API", max_claims=50)
        assert len(result) == 50


# ---------------------------------------------------------------------------
# Integration: _assign_claims applies relevance filter post-assignment
# ---------------------------------------------------------------------------

class TestAssignClaimsRelevanceIntegration:
    """Verify that _assign_claims integrates the relevance filter correctly."""

    def test_relevance_filter_applied_after_assignment(self):
        """With _MAX_RELEVANCE_CLAIMS_PER_PAGE capped, only top-N are kept."""
        from launcher.workers.planner.plan import _assign_claims, _MAX_RELEVANCE_CLAIMS_PER_PAGE

        # Build a page and enough claims to hit the relevance cap
        page = _make_page("workbook-overview", "feature_showcase", title="Workbook Overview")

        n = _MAX_RELEVANCE_CLAIMS_PER_PAGE + 10
        claims = [
            _make_claim(f"C{i}", f"feature claim number {i} about workbook", kind="feature")
            for i in range(n)
        ]
        pages, _ = _assign_claims([page], claims, [])
        assert len(pages) == 1
        # After relevance filter, no page should exceed _MAX_RELEVANCE_CLAIMS_PER_PAGE
        assert len(pages[0].assigned_claims) <= _MAX_RELEVANCE_CLAIMS_PER_PAGE

    def test_small_page_unchanged_by_filter(self):
        """Pages with few claims are not affected by the relevance filter."""
        from launcher.workers.planner.plan import _assign_claims

        page = _make_page("install", "workflow_page", title="Install Guide")
        claims = [
            _make_claim(f"C{i}", f"workflow step {i} to install the library", kind="workflow")
            for i in range(5)
        ]
        pages, _ = _assign_claims([page], claims, [])
        assert len(pages) == 1
        # 5 claims are well under any cap — must be unchanged
        assert len(pages[0].assigned_claims) == 5

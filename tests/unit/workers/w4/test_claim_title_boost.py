"""Tests for TC-3686: W4 claim distribution title-keyword boost + usage cap."""

from __future__ import annotations

import pytest

from launch.workers.w4_ia_planner.worker import (
    _rerank_claims_by_title,
    MAX_PAGES_PER_CLAIM,
)


def _make_claim(cid: str, text: str) -> dict:
    return {"claim_id": cid, "claim_text": text}


# ── Title-keyword matching ────────────────────────────────────────────────────

class TestTitleKeywordMatch:
    """Verify claims matching page title are boosted."""

    def test_matching_claims_ranked_first(self):
        claims = [
            _make_claim("c1", "Supports CSV export and import operations"),
            _make_claim("c2", "Performance optimizations for large datasets"),
            _make_claim("c3", "Install via pip for Python development"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2", "c3"],
            claims,
            title="Python Installation Guide",
            purpose="How to install the library",
            usage_counts={},
        )
        # c3 mentions "install" and "python" — should rank first
        assert result[0] == "c3"

    def test_no_keywords_preserves_order(self):
        claims = [
            _make_claim("c1", "Feature A"),
            _make_claim("c2", "Feature B"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2"],
            claims,
            title="",  # No title
            purpose="",
            usage_counts={},
        )
        # Order preserved when no keywords
        assert result == ["c1", "c2"]

    def test_all_stopwords_title_preserves_order(self):
        claims = [
            _make_claim("c1", "Feature A"),
            _make_claim("c2", "Feature B"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2"],
            claims,
            title="The Guide For This",  # All stopwords
            purpose="",
            usage_counts={},
        )
        # All words are stopwords → no meaningful keywords → preserve order
        assert result == ["c1", "c2"]

    def test_stable_sort_preserves_tie_order(self):
        """Claims with same overlap count maintain original order."""
        claims = [
            _make_claim("c1", "Supports spreadsheet operations"),
            _make_claim("c2", "Handles spreadsheet processing"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2"],
            claims,
            title="Spreadsheet Operations",
            purpose="",
            usage_counts={},
        )
        # Both match "spreadsheet" (overlap=1) — c1 should stay first (stable sort)
        assert result[0] == "c1"
        assert result[1] == "c2"


# ── Usage cap ─────────────────────────────────────────────────────────────────

class TestUsageCap:
    """Verify claims at usage cap are excluded."""

    def test_capped_claims_excluded(self):
        claims = [
            _make_claim("c1", "Feature A"),
            _make_claim("c2", "Feature B"),
            _make_claim("c3", "Feature C"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2", "c3"],
            claims,
            title="Features",
            purpose="",
            usage_counts={"c2": MAX_PAGES_PER_CLAIM},  # c2 at cap
        )
        assert "c2" not in result
        assert "c1" in result
        assert "c3" in result

    def test_below_cap_included(self):
        claims = [
            _make_claim("c1", "Feature A"),
        ]
        result = _rerank_claims_by_title(
            ["c1"],
            claims,
            title="Features",
            purpose="",
            usage_counts={"c1": MAX_PAGES_PER_CLAIM - 1},  # Just below cap
        )
        assert "c1" in result

    def test_empty_usage_counts_all_included(self):
        claims = [
            _make_claim("c1", "Feature A"),
            _make_claim("c2", "Feature B"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2"],
            claims,
            title="Features",
            purpose="",
            usage_counts={},
        )
        assert len(result) == 2


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases for claim reranking."""

    def test_empty_claim_ids(self):
        result = _rerank_claims_by_title(
            [],
            [],
            title="Test",
            purpose="",
            usage_counts={},
        )
        assert result == []

    def test_missing_claim_text(self):
        """Claims without claim_text still work (zero overlap)."""
        claims = [
            {"claim_id": "c1"},  # No claim_text
            _make_claim("c2", "Matching text for test page"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2"],
            claims,
            title="Test Page",
            purpose="",
            usage_counts={},
        )
        # c2 should rank first (has overlap), c1 has zero overlap
        assert result[0] == "c2"

    def test_max_pages_per_claim_constant(self):
        """MAX_PAGES_PER_CLAIM is a reasonable default."""
        assert MAX_PAGES_PER_CLAIM == 3

    def test_purpose_words_also_counted(self):
        """Words from purpose contribute to keyword matching."""
        claims = [
            _make_claim("c1", "CSV data export functionality"),
            _make_claim("c2", "Memory management features"),
        ]
        result = _rerank_claims_by_title(
            ["c1", "c2"],
            claims,
            title="Data Guide",
            purpose="Export CSV files efficiently",
            usage_counts={},
        )
        # c1 matches "export", "csv", "data" — should rank first
        assert result[0] == "c1"

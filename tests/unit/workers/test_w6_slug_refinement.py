"""Tests for W6 slug refinement pipeline (TC-2609/2610/2611).

Validates:
- Schema-validated LLM response parsing
- Deterministic candidate selection (collision, format, identity checks)
- _pick_best_candidate logic
- _generate_seo_slug_via_llm schema enforcement
- End-to-end _refine_slugs_for_sections with mock LLM
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.launch.workers.w6_seo_optimizer.worker import (
    _generate_seo_slug_via_llm,
    _is_valid_slug,
    _pick_best_candidate,
    _validate_slug_formats,
)


# ---------------------------------------------------------------------------
# TC-2609: Schema-validated LLM response parsing
# ---------------------------------------------------------------------------


class TestGenerateSeoSlugViaLLM:
    """Tests for _generate_seo_slug_via_llm() schema validation."""

    def _mock_llm(self, content: str) -> MagicMock:
        client = MagicMock()
        client.chat_completion.return_value = {"content": content}
        return client

    def test_valid_single_candidate(self):
        """Valid single-candidate response is parsed correctly."""
        response = json.dumps({
            "candidates": [{"slug": "convert-3d-models", "rationale": "SEO-friendly"}]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Convert Formats", "convert-formats", [], "3d", "python", client
        )
        assert result is not None
        assert len(result) == 1
        assert result[0]["slug"] == "convert-3d-models"

    def test_valid_multiple_candidates(self):
        """Multiple candidates are all returned (up to 3)."""
        response = json.dumps({
            "candidates": [
                {"slug": "convert-3d-models", "rationale": "Primary keyword"},
                {"slug": "3d-format-converter", "rationale": "Action-oriented"},
                {"slug": "convert-fbx-obj", "rationale": "Format-specific"},
            ]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Convert Formats", "convert-formats", [], "3d", "python", client
        )
        assert result is not None
        assert len(result) == 3

    def test_invalid_json_returns_none(self):
        """Non-JSON response returns None."""
        client = self._mock_llm("not valid json")
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is None

    def test_empty_candidates_returns_none(self):
        """Empty candidates array returns None."""
        response = json.dumps({"candidates": []})
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is None

    def test_invalid_slug_pattern_filtered(self):
        """Candidates with invalid slug patterns are filtered out."""
        response = json.dumps({
            "candidates": [
                {"slug": "UPPERCASE-BAD", "rationale": "Invalid case"},
                {"slug": "valid-slug", "rationale": "Good one"},
            ]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is not None
        assert len(result) == 1
        assert result[0]["slug"] == "valid-slug"

    def test_slug_too_long_filtered(self):
        """Slugs exceeding 60 chars are filtered."""
        long_slug = "a" * 61
        response = json.dumps({
            "candidates": [
                {"slug": long_slug, "rationale": "Too long"},
                {"slug": "short-valid", "rationale": "Good"},
            ]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is not None
        assert len(result) == 1
        assert result[0]["slug"] == "short-valid"

    def test_all_candidates_invalid_returns_none(self):
        """When all candidates fail validation, returns None."""
        response = json.dumps({
            "candidates": [
                {"slug": "BAD!", "rationale": "Invalid"},
                {"slug": "-bad-start", "rationale": "Invalid"},
            ]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is None

    def test_llm_exception_returns_none(self):
        """LLM client exception returns None gracefully."""
        client = MagicMock()
        client.chat_completion.side_effect = RuntimeError("LLM down")
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is None

    def test_rationale_truncated_at_200(self):
        """Long rationale is truncated to 200 chars."""
        response = json.dumps({
            "candidates": [{"slug": "good-slug", "rationale": "x" * 300}]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is not None
        assert len(result[0]["rationale"]) == 200

    def test_candidates_capped_at_three(self):
        """More than 3 candidates returns only first 3."""
        response = json.dumps({
            "candidates": [
                {"slug": f"slug-{i}", "rationale": f"Reason {i}"}
                for i in range(5)
            ]
        })
        client = self._mock_llm(response)
        result = _generate_seo_slug_via_llm(
            "Title", "slug", [], "3d", "python", client
        )
        assert result is not None
        assert len(result) == 3


# ---------------------------------------------------------------------------
# TC-2610: Deterministic candidate selection
# ---------------------------------------------------------------------------


class TestPickBestCandidate:
    """Tests for _pick_best_candidate() deterministic validation."""

    def test_picks_first_valid(self):
        """First candidate passing all checks is selected."""
        candidates = [
            {"slug": "best-slug", "rationale": "Primary"},
            {"slug": "backup-slug", "rationale": "Fallback"},
        ]
        result = _pick_best_candidate(candidates, "old-slug", set(), None)
        assert result == "best-slug"

    def test_rejects_collision(self):
        """Candidate colliding with existing slug is skipped."""
        candidates = [
            {"slug": "taken-slug", "rationale": "Collides"},
            {"slug": "free-slug", "rationale": "Available"},
        ]
        existing = {"taken-slug", "another-slug"}
        result = _pick_best_candidate(candidates, "old-slug", existing, None)
        assert result == "free-slug"

    def test_rejects_same_as_current(self):
        """Candidate identical to current slug is skipped."""
        candidates = [
            {"slug": "current-slug", "rationale": "Same"},
            {"slug": "different-slug", "rationale": "New"},
        ]
        result = _pick_best_candidate(candidates, "current-slug", set(), None)
        assert result == "different-slug"

    def test_rejects_bad_format_tokens(self):
        """Candidate with unevidenced format tokens is rejected."""
        caps = {"supported_formats": ["FBX", "OBJ"]}
        candidates = [
            {"slug": "convert-xyz-to-abc", "rationale": "Bad formats"},
            {"slug": "convert-fbx-to-obj", "rationale": "Good formats"},
        ]
        result = _pick_best_candidate(candidates, "old-slug", set(), caps)
        assert result == "convert-fbx-to-obj"

    def test_all_rejected_returns_none(self):
        """When all candidates fail validation, returns None."""
        candidates = [
            {"slug": "current-slug", "rationale": "Same as current"},
        ]
        result = _pick_best_candidate(candidates, "current-slug", set(), None)
        assert result is None

    def test_no_registry_skips_format_check(self):
        """Without registry, format check is skipped."""
        candidates = [
            {"slug": "convert-xyz-to-abc", "rationale": "Unknown formats OK"},
        ]
        result = _pick_best_candidate(candidates, "old-slug", set(), None)
        assert result == "convert-xyz-to-abc"

    def test_empty_candidates_returns_none(self):
        """Empty candidates list returns None."""
        result = _pick_best_candidate([], "old-slug", set(), None)
        assert result is None

    def test_collision_plus_same_plus_valid(self):
        """Complex scenario: first collides, second same, third valid."""
        candidates = [
            {"slug": "taken", "rationale": "Collides"},
            {"slug": "current", "rationale": "Same"},
            {"slug": "winner", "rationale": "Valid"},
        ]
        existing = {"taken", "other"}
        result = _pick_best_candidate(candidates, "current", existing, None)
        assert result == "winner"


# ---------------------------------------------------------------------------
# TC-2611: Integration — _refine_slugs_for_sections with mocks
# ---------------------------------------------------------------------------


class TestRefineSlugsSections:
    """Integration tests for _refine_slugs_for_sections()."""

    def test_slug_rewrite_disabled_no_changes(self, tmp_path):
        """Without LLM client or PyTrends, no suggestions are produced."""
        from src.launch.workers.w6_seo_optimizer.worker import _refine_slugs_for_sections

        page_plan = {
            "pages": [
                {"slug": "old-slug", "section": "kb", "title": "Old Article"},
            ]
        }
        # No LLM client, no PyTrends → no suggestions (TC-3400: advisory-only)
        suggestions = _refine_slugs_for_sections(
            page_plan, tmp_path, {},
        )
        assert suggestions == []
        # page_plan must NOT be mutated
        assert page_plan["pages"][0]["slug"] == "old-slug"

    def test_docs_section_never_refined(self, tmp_path):
        """Docs section pages are never refined regardless of LLM."""
        from src.launch.workers.w6_seo_optimizer.worker import _refine_slugs_for_sections

        page_plan = {
            "pages": [
                {"slug": "getting-started", "section": "docs", "title": "Getting Started"},
            ]
        }
        suggestions = _refine_slugs_for_sections(
            page_plan, tmp_path, {},
        )
        assert page_plan["pages"][0]["slug"] == "getting-started"
        assert suggestions == []


# ---------------------------------------------------------------------------
# TC-2611: _is_valid_slug edge cases
# ---------------------------------------------------------------------------


class TestIsValidSlug:
    """Edge case tests for _is_valid_slug()."""

    def test_valid_simple(self):
        assert _is_valid_slug("getting-started") is True

    def test_valid_with_numbers(self):
        assert _is_valid_slug("convert-3d-models") is True

    def test_empty_invalid(self):
        assert _is_valid_slug("") is False

    def test_too_long_invalid(self):
        assert _is_valid_slug("a" * 41) is False

    def test_starts_with_hyphen_invalid(self):
        assert _is_valid_slug("-bad-start") is False

    def test_ends_with_hyphen_invalid(self):
        assert _is_valid_slug("bad-end-") is False

    def test_uppercase_invalid(self):
        assert _is_valid_slug("BAD-SLUG") is False

    def test_single_char_invalid(self):
        # Pattern requires at least 2 chars (start + end)
        assert _is_valid_slug("a") is False

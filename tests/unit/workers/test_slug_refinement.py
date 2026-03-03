"""Tests for LLM-powered slug refinement (TC-3651).

Covers:
- strip_leading_stop_words() algorithmic helper
- _refine_slugs() LLM path (mocked)
- _refine_slugs() fallback on LLM error / count mismatch / no LLM
- per_feature_blog semantic slug derivation
- SR-01: LLM slug sanitization guard
- SR-02: per_feature_blog slug length cap
- SR-03: slug refinement observability (summary logging)
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.launch.workers._shared.slug_constants import (
    SLUG_LEADING_STOP_WORDS,
    strip_leading_stop_words,
)
from src.launch.workers.w4_ia_planner.worker import (
    _detect_slug_collisions,
    _derive_page_title,
    _derive_semantic_slug,
    _refine_slugs,
)


# ---------------------------------------------------------------------------
# strip_leading_stop_words
# ---------------------------------------------------------------------------


class TestStripLeadingStopWords:
    """Unit tests for the algorithmic stop-word stripping helper."""

    def test_strips_single_leading_stop_word(self):
        assert strip_leading_stop_words("you-can-create-rules") == "create-rules"

    def test_strips_multiple_leading_stop_words(self):
        assert strip_leading_stop_words("you-can-also-create-rules") == "create-rules"

    def test_preserves_min_remaining(self):
        # All words are stop-words, but min_remaining=2 keeps last two
        assert strip_leading_stop_words("you-can") == "you-can"

    def test_no_stop_words_unchanged(self):
        assert strip_leading_stop_words("create-rules-python") == "create-rules-python"

    def test_empty_slug(self):
        assert strip_leading_stop_words("") == ""

    def test_single_word_non_stop(self):
        assert strip_leading_stop_words("convert") == "convert"

    def test_single_word_stop(self):
        # Single word that is a stop-word: min_remaining=2 won't strip (only 1 part)
        assert strip_leading_stop_words("the") == "the"

    def test_custom_min_remaining(self):
        result = strip_leading_stop_words("you-can-create-rules", min_remaining=3)
        assert result == "can-create-rules"

    def test_stop_words_frozenset_is_immutable(self):
        assert isinstance(SLUG_LEADING_STOP_WORDS, frozenset)


# ---------------------------------------------------------------------------
# _refine_slugs — LLM path
# ---------------------------------------------------------------------------


class TestRefineSlugsLLM:
    """Tests for _refine_slugs() when LLM client is available."""

    def test_llm_cleans_slugs(self):
        """LLM returns cleaned slugs → page slugs updated."""
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules-to-restrict"},
                {"slug": "convert-3d-models"},
            ],
        }
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = (
            "create-rules-restrict\nconvert-3d-models"
        )
        _refine_slugs(page_plan, mock_llm)
        assert page_plan["pages"][0]["slug"] == "create-rules-restrict"
        assert page_plan["pages"][1]["slug"] == "convert-3d-models"

    def test_llm_called_with_temperature_zero(self):
        """Verify LLM is called with temperature=0.0 for determinism."""
        page_plan = {"pages": [{"slug": "test-slug"}]}
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "test-slug"
        _refine_slugs(page_plan, mock_llm)
        _, kwargs = mock_llm.chat_completion.call_args
        assert kwargs.get("temperature") == 0.0

    def test_llm_count_mismatch_falls_back(self):
        """LLM returns wrong count → falls back to algorithmic strip."""
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules"},
                {"slug": "the-only-way-forward"},
            ],
        }
        mock_llm = MagicMock()
        # Return only 1 line instead of 2
        mock_llm.chat_completion.return_value = "create-rules"
        _refine_slugs(page_plan, mock_llm)
        # Algorithmic fallback applied
        assert page_plan["pages"][0]["slug"] == "create-rules"
        assert page_plan["pages"][1]["slug"] == "way-forward"

    def test_llm_error_falls_back(self):
        """LLM raises exception → falls back to algorithmic strip."""
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules"},
            ],
        }
        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = RuntimeError("timeout")
        _refine_slugs(page_plan, mock_llm)
        # Algorithmic fallback
        assert page_plan["pages"][0]["slug"] == "create-rules"

    def test_llm_empty_slug_not_applied(self):
        """LLM returns empty string → count mismatch → algorithmic fallback."""
        page_plan = {"pages": [{"slug": "you-can-create"}]}
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = ""
        # Count mismatch (0 lines vs 1) → fallback strips "you" but
        # min_remaining=2 keeps "can-create"
        _refine_slugs(page_plan, mock_llm)
        assert page_plan["pages"][0]["slug"] == "can-create"


# ---------------------------------------------------------------------------
# _refine_slugs — no LLM
# ---------------------------------------------------------------------------


class TestRefineSlugsNoLLM:
    """Tests for _refine_slugs() when llm_client is None."""

    def test_no_llm_strips_stop_words(self):
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules"},
                {"slug": "convert-formats"},
            ],
        }
        _refine_slugs(page_plan, None)
        assert page_plan["pages"][0]["slug"] == "create-rules"
        assert page_plan["pages"][1]["slug"] == "convert-formats"

    def test_empty_pages_no_error(self):
        page_plan = {"pages": []}
        _refine_slugs(page_plan, None)  # should not raise


# ---------------------------------------------------------------------------
# per_feature_blog semantic slug
# ---------------------------------------------------------------------------


class TestPerFeatureBlogSlug:
    """Verify per_feature_blog uses _derive_semantic_slug, not raw split."""

    def test_semantic_slug_strips_preamble(self):
        """_derive_semantic_slug strips filler preambles from claim text."""
        slug = _derive_semantic_slug("You can use this to create rules for 3D models")
        assert "you" not in slug.split("-")[:2]
        assert slug  # non-empty

    def test_semantic_slug_deterministic(self):
        """Same input → same output."""
        a = _derive_semantic_slug("Convert 3D models between formats")
        b = _derive_semantic_slug("Convert 3D models between formats")
        assert a == b


# ---------------------------------------------------------------------------
# SR-01: LLM slug sanitization guard
# ---------------------------------------------------------------------------


class TestLLMSlugSanitization:
    """SR-01: Verify LLM-returned slugs are sanitized before being applied."""

    def test_llm_returns_uppercase_sanitized(self):
        """LLM returns uppercase → lowercased before applying."""
        page_plan = {"pages": [{"slug": "old-slug"}]}
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "Create Rules"
        _refine_slugs(page_plan, mock_llm)
        slug = page_plan["pages"][0]["slug"]
        assert slug == "create-rules"

    def test_llm_returns_spaces_sanitized(self):
        """LLM returns spaces → converted to hyphens."""
        page_plan = {"pages": [{"slug": "old-slug"}]}
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "create rules python"
        _refine_slugs(page_plan, mock_llm)
        assert page_plan["pages"][0]["slug"] == "create-rules-python"

    def test_llm_returns_empty_line_skipped(self):
        """LLM returns empty line for one slug → original kept for that page."""
        page_plan = {
            "pages": [
                {"slug": "good-old"},
                {"slug": "keep-me"},
                {"slug": "also-good"},
            ],
        }
        mock_llm = MagicMock()
        # 3 lines, middle is empty → count matches, but empty line skipped
        mock_llm.chat_completion.return_value = "cleaned-first\n\ncleaned-third"
        _refine_slugs(page_plan, mock_llm)
        assert page_plan["pages"][0]["slug"] == "cleaned-first"
        assert page_plan["pages"][1]["slug"] == "keep-me"  # original kept
        assert page_plan["pages"][2]["slug"] == "cleaned-third"

    def test_llm_returns_special_chars_stripped(self):
        """LLM returns parens/brackets → stripped, hyphens collapsed."""
        page_plan = {"pages": [{"slug": "old-slug"}]}
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "slug (with parens)"
        _refine_slugs(page_plan, mock_llm)
        assert page_plan["pages"][0]["slug"] == "slug-with-parens"


# ---------------------------------------------------------------------------
# SR-02: per_feature_blog slug length cap
# ---------------------------------------------------------------------------


class TestPerFeatureBlogSlugLength:
    """SR-02: Verify per_feature_blog slug base is capped at 25 chars."""

    def test_per_feature_blog_slug_length_bounded(self):
        """Long claim text → slug_base ≤ 25 chars."""
        long_claim = (
            "This feature allows you to automatically convert "
            "multiple 3D model formats between FBX OBJ STL and GLTF "
            "with full material preservation and texture mapping support"
        )
        slug_base = _derive_semantic_slug(long_claim, max_length=25)
        assert len(slug_base) <= 25
        # Simulate total slug
        total = f"aspose-3d-foss-{slug_base}-python"
        assert len(total) <= 60

    def test_per_feature_blog_uses_semantic_not_raw_split(self):
        """With max_length=25 cap, slug differs from raw 4-word split."""
        claim = "You can use this to create advanced validation rules for 3D models"
        slug_base = _derive_semantic_slug(claim, max_length=25)
        # Old approach: raw 4-word split → "you-can-use-this" (16 chars)
        raw_split = "-".join(
            w for w in claim.lower().split()[:4]
            if w.isalnum()
        )
        # Semantic derivation strips the "You can use this to" preamble
        assert slug_base != raw_split
        assert len(slug_base) <= 25


# ---------------------------------------------------------------------------
# SR-03: Slug refinement observability (summary logging)
# ---------------------------------------------------------------------------


class TestSlugRefinementLogging:
    """SR-03: Verify summary log lines at both exit paths (structlog → stdout)."""

    def test_llm_path_logs_summary(self, capsys):
        """After LLM refinement, logs slug_refinement_complete method=llm."""
        page_plan = {
            "pages": [
                {"slug": "you-can-create"},
                {"slug": "convert-models"},
            ],
        }
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "create\nconvert-models"
        _refine_slugs(page_plan, mock_llm)
        captured = capsys.readouterr().out
        assert "slug_refinement_complete method=llm" in captured

    def test_fallback_path_logs_summary(self, capsys):
        """After fallback, logs slug_refinement_complete method=fallback."""
        page_plan = {"pages": [{"slug": "you-can-create-rules"}]}
        _refine_slugs(page_plan, None)
        captured = capsys.readouterr().out
        assert "slug_refinement_complete method=fallback" in captured

    def test_summary_log_changed_count_accurate(self, capsys):
        """Changed count in summary log matches actual changes."""
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules"},  # will change
                {"slug": "convert-formats"},  # won't change (no stop-words)
            ],
        }
        _refine_slugs(page_plan, None)
        captured = capsys.readouterr().out
        assert "slug_refinement_complete method=fallback changed=1 total=2" in captured


# ---------------------------------------------------------------------------
# SR-04: Integration + edge-case tests
# ---------------------------------------------------------------------------


class TestRefineSlugIntegration:
    """GAP-07: Verify _refine_slugs is wired into execute_ia_planner pipeline."""

    def test_refine_slugs_mutates_page_plan_before_collision_check(self):
        """_refine_slugs mutates page_plan in place → _detect_slug_collisions sees cleaned slugs.

        Production call site (worker.py:6101-6107):
            _refine_slugs(page_plan, llm_client)
            validate_page_plan(page_plan)
            slug_collisions = _detect_slug_collisions(page_plan)

        This test verifies the full in-place mutation contract that the wiring depends on.
        """
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules", "section": "kb", "title": "Page A"},
            ],
        }
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = "create-rules"
        _refine_slugs(page_plan, mock_llm)
        # Slug was mutated in place — same dict object
        assert page_plan["pages"][0]["slug"] == "create-rules"
        # Downstream _detect_slug_collisions sees the cleaned slug
        collisions = _detect_slug_collisions(page_plan)
        assert collisions == []


class TestPerFeatureBlogPath:
    """GAP-08: Verify per_feature_blog uses semantic helpers."""

    def test_blog_slug_uses_derive_semantic_slug(self):
        """Blog slug base comes from _derive_semantic_slug, not raw split."""
        claim = "You can use this to create advanced validation rules for 3D"
        slug_base = _derive_semantic_slug(claim, max_length=25)
        raw_split = "-".join(claim.lower().split()[:4])
        # Semantic derivation strips preamble → differs from raw split
        assert slug_base != raw_split
        # Simulated per_feature_blog slug construction (worker.py:2489-2490)
        full_slug = f"aspose-3d-foss-{slug_base}-python"
        assert "you-can" not in full_slug

    def test_blog_title_uses_derive_page_title(self):
        """Blog title comes from _derive_page_title, not raw truncation."""
        long_claim = (
            "You can use this to perform extremely complex transformations "
            "on documents with nested structures and embedded media content "
            "including images and hyperlinks"
        )
        title = _derive_page_title(long_claim)
        raw_truncated = long_claim[:50]
        # _derive_page_title strips "You can use" preamble and reformats
        assert title != raw_truncated
        # Title is not empty and has proper structure
        assert len(title) > 0
        assert len(title) <= 70


class TestRefinementCollisionInteraction:
    """GAP-09: Verify _detect_slug_collisions catches refinement-caused dupes."""

    def test_refinement_creating_duplicate_slug_detected(self):
        """If _refine_slugs creates a collision, _detect_slug_collisions catches it."""
        page_plan = {
            "pages": [
                {"slug": "you-can-create-rules", "section": "kb", "title": "Page A"},
                {"slug": "they-can-create-rules", "section": "kb", "title": "Page B"},
            ],
        }
        mock_llm = MagicMock()
        # LLM returns same cleaned slug for both → collision
        mock_llm.chat_completion.return_value = "create-rules\ncreate-rules"
        _refine_slugs(page_plan, mock_llm)

        # Both pages now have the same slug
        assert page_plan["pages"][0]["slug"] == "create-rules"
        assert page_plan["pages"][1]["slug"] == "create-rules"

        # _detect_slug_collisions should catch this
        collisions = _detect_slug_collisions(page_plan)
        assert len(collisions) == 1
        assert collisions[0]["slug"] == "create-rules"
        assert collisions[0]["section"] == "kb"
        assert len(collisions[0]["pages"]) == 2

"""Slug contract regression tests (Agent 47).

Verifies:
1. W4 generates deterministic, deduplicated slugs via _slugify().
2. W6 does NOT rewrite page_plan slugs/paths under default config
   (slug_rewrite_enabled defaults to False).
3. W6 CAN rewrite slugs for kb/blog when slug_rewrite_enabled=True,
   and leaves docs/reference unchanged.

Spec reference: specs/45_seo_slug_strategy.md
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w4_ia_planner.worker import _slugify
from launch.workers.w6_seo_optimizer.worker import (
    _is_valid_slug,
    _refine_slugs_for_sections,
    execute_seo_optimizer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_dir(tmp_path: Path, pages: list) -> tuple[Path, Path]:
    """Create a minimal run directory with artifacts and site/content dir.

    Returns (run_dir, page_plan_path).
    """
    run_dir = tmp_path / "run"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    page_plan = {"pages": pages}
    page_plan_path = artifacts_dir / "page_plan.json"
    page_plan_path.write_text(json.dumps(page_plan, indent=2), encoding="utf-8")

    product_facts = {
        "product_name": "Aspose.Cells",
        "product_family": "cells",
        "claims": [],
    }
    (artifacts_dir / "product_facts.json").write_text(
        json.dumps(product_facts), encoding="utf-8"
    )

    # Site content dir must exist or execute_seo_optimizer returns "skipped"
    (run_dir / "work" / "site" / "content").mkdir(parents=True)

    return run_dir, page_plan_path


def _make_page(section: str, slug: str) -> dict:
    return {
        "page_id": f"{section}-{slug}",
        "section": section,
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "output_path": f"content/docs.aspose.org/cells/en/{section}/{slug}.md",
        "url_path": f"/cells/{section}/{slug}/",
    }


# ---------------------------------------------------------------------------
# TestSlugContractW4 — W4 slugify and deduplication logic
# ---------------------------------------------------------------------------

class TestSlugContractW4:
    """Verifies W4 _slugify() produces correct URL-safe slugs."""

    def test_slugify_basic(self):
        assert _slugify("Getting Started") == "getting-started"

    def test_slugify_lowercase(self):
        assert _slugify("C++ Integration Guide") == "c-integration-guide"

    def test_slugify_strips_special_chars(self):
        assert _slugify("Hello, World!") == "hello-world"

    def test_slugify_collapse_consecutive_hyphens(self):
        # Multiple separators collapse to one hyphen
        assert _slugify("foo  --  bar") == "foo-bar"

    def test_slugify_strips_leading_trailing(self):
        assert _slugify("  hello  ") == "hello"

    def test_slugify_numbers_preserved(self):
        assert _slugify("API v2.0 Release") == "api-v2-0-release"

    def test_slugify_single_word(self):
        assert _slugify("Overview") == "overview"

    def test_slugify_already_slug(self):
        assert _slugify("already-a-slug") == "already-a-slug"


# ---------------------------------------------------------------------------
# TestSlugImmutabilityW6 — W6 must NOT rewrite slugs by default
# ---------------------------------------------------------------------------

class TestSlugImmutabilityW6:
    """Verifies _refine_slugs_for_sections does not run under default config."""

    def test_refine_not_called_when_slug_rewrite_disabled(self, tmp_path):
        """execute_seo_optimizer default: _refine_slugs_for_sections never called."""
        pages = [
            _make_page("kb", "install-python"),
            _make_page("docs", "overview"),
        ]
        run_dir, _ = _make_run_dir(tmp_path, pages)

        with patch(
            "launch.workers.w6_seo_optimizer.worker._refine_slugs_for_sections"
        ) as mock_refine, patch(
            "launch.workers.w6_seo_optimizer.worker.research_keywords"
        ) as mock_rk:
            mock_rk.return_value = {"primary_keywords": [], "long_tail": [], "per_page": {}}
            run_config = {}  # slug_rewrite_enabled absent → defaults to False
            execute_seo_optimizer(run_dir, run_config)

        mock_refine.assert_not_called()

    def test_refine_not_called_when_seo_enabled_only(self, tmp_path):
        """seo_enabled=True alone does NOT enable slug rewriting."""
        pages = [_make_page("kb", "install-python")]
        run_dir, _ = _make_run_dir(tmp_path, pages)

        with patch(
            "launch.workers.w6_seo_optimizer.worker._refine_slugs_for_sections"
        ) as mock_refine, patch(
            "launch.workers.w6_seo_optimizer.worker.research_keywords"
        ) as mock_rk:
            mock_rk.return_value = {"primary_keywords": [], "long_tail": [], "per_page": {}}
            run_config = {"seo_enabled": True}  # no slug_rewrite_enabled
            execute_seo_optimizer(run_dir, run_config)

        mock_refine.assert_not_called()

    def test_page_plan_slugs_unchanged_by_default(self, tmp_path):
        """After execute_seo_optimizer (default), page_plan slugs on disk are identical."""
        pages = [
            _make_page("kb", "install-python"),
            _make_page("blog", "why-aspose"),
            _make_page("docs", "overview"),
        ]
        run_dir, page_plan_path = _make_run_dir(tmp_path, pages)
        original_slugs = {p["page_id"]: p["slug"] for p in pages}

        with patch(
            "launch.workers.w6_seo_optimizer.worker.research_keywords"
        ) as mock_rk:
            mock_rk.return_value = {"primary_keywords": [], "long_tail": [], "per_page": {}}
            run_config = {}
            execute_seo_optimizer(run_dir, run_config)

        updated_plan = json.loads(page_plan_path.read_text(encoding="utf-8"))
        for page in updated_plan["pages"]:
            pid = page["page_id"]
            assert page["slug"] == original_slugs[pid], (
                f"Slug for {pid} changed from '{original_slugs[pid]}' to '{page['slug']}'"
            )

    def test_slug_changes_field_absent_by_default(self, tmp_path):
        """When slug rewriting is disabled, page_plan has no slug_changes key."""
        pages = [_make_page("kb", "install-python")]
        run_dir, page_plan_path = _make_run_dir(tmp_path, pages)

        with patch("launch.workers.w6_seo_optimizer.worker.research_keywords") as mock_rk:
            mock_rk.return_value = {"primary_keywords": [], "long_tail": [], "per_page": {}}
            execute_seo_optimizer(run_dir, {})

        updated_plan = json.loads(page_plan_path.read_text(encoding="utf-8"))
        assert "slug_changes" not in updated_plan


# ---------------------------------------------------------------------------
# TestSlugRewriteGated — slug rewriting when slug_rewrite_enabled=True
# ---------------------------------------------------------------------------

class TestSlugRewriteGated:
    """Verifies _refine_slugs_for_sections behaviour when explicitly enabled."""

    def _mock_llm(self, new_slug: str) -> MagicMock:
        """Mock LLM client that returns new_slug for any request."""
        llm = MagicMock()
        llm.chat_completion.return_value = {"content": new_slug}
        return llm

    def test_kb_slug_suggested_when_llm_returns_better_slug(self, tmp_path):
        """_refine_slugs_for_sections returns advisory suggestion for kb page (TC-3400)."""
        page = _make_page("kb", "install-python")
        page_plan = {"pages": [page]}

        # run_config must have llm.api_base_url so _refine_slugs_for_sections builds a client
        run_config = {"llm": {"api_base_url": "http://fake.local"}}

        with patch(
            "launch.workers.w6_seo_optimizer.worker._generate_seo_slug_via_llm",
            return_value=[{"slug": "python-installation-guide", "rationale": "SEO"}],
        ), patch(
            "launch.workers.w6_seo_optimizer.keyword_utils.SlugRefinementCache"
        ) as MockCache, patch(
            "launch.clients.llm_provider.create_llm_client_from_config",
            return_value=self._mock_llm("python-installation-guide"),
        ):
            # SlugRefinementCache returns None from .get() → forces LLM call
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache.pytrends_key.return_value = "pt_key"
            mock_cache.gemini_key.return_value = "gm_key"
            MockCache.return_value = mock_cache

            suggestions = _refine_slugs_for_sections(page_plan, tmp_path, run_config)

        # TC-3400: advisory-only — page_plan NOT mutated
        assert page_plan["pages"][0]["slug"] == "install-python"
        # Suggestion recorded
        assert len(suggestions) == 1
        assert suggestions[0]["suggested_slug"] == "python-installation-guide"

    def test_docs_slug_unchanged_even_when_rewrite_enabled(self, tmp_path):
        """Docs section is never touched by _refine_slugs_for_sections."""
        docs_page = _make_page("docs", "overview")
        page_plan = {"pages": [docs_page]}

        with patch(
            "launch.workers.w6_seo_optimizer.worker._generate_seo_slug_via_llm",
            return_value=[{"slug": "better-overview-slug", "rationale": "SEO"}],
        ), patch(
            "launch.workers.w6_seo_optimizer.keyword_utils.SlugRefinementCache"
        ) as MockCache:
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            MockCache.return_value = mock_cache

            suggestions = _refine_slugs_for_sections(page_plan, tmp_path, {})

        # Docs pages skip the loop entirely → slug unchanged, no suggestions
        assert page_plan["pages"][0]["slug"] == "overview"
        assert suggestions == []

    def test_reference_slug_unchanged_even_when_rewrite_enabled(self, tmp_path):
        """Reference section is never touched by _refine_slugs_for_sections."""
        ref_page = _make_page("reference", "workbook-class")
        page_plan = {"pages": [ref_page]}

        with patch(
            "launch.workers.w6_seo_optimizer.worker._generate_seo_slug_via_llm",
            return_value=[{"slug": "workbook-api-reference", "rationale": "SEO"}],
        ), patch(
            "launch.workers.w6_seo_optimizer.keyword_utils.SlugRefinementCache"
        ) as MockCache:
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            MockCache.return_value = mock_cache

            suggestions = _refine_slugs_for_sections(page_plan, tmp_path, {})

        assert page_plan["pages"][0]["slug"] == "workbook-class"
        assert suggestions == []

    def test_slug_changes_logged_for_mutated_pages(self, tmp_path):
        """slug_changes array records each mutation for audit purposes."""
        pages = [
            _make_page("kb", "install-python"),
            _make_page("blog", "getting-started"),
            _make_page("docs", "overview"),  # should not appear in slug_changes
        ]
        page_plan = {"pages": pages}

        call_count = 0
        new_slugs = ["python-install-guide", "start-your-journey"]

        def _fake_generate(title, current, trends, family, platform, llm_client):
            nonlocal call_count
            if call_count < len(new_slugs):
                slug = new_slugs[call_count]
                call_count += 1
                return [{"slug": slug, "rationale": "SEO"}]
            call_count += 1
            return None

        # run_config must have llm.api_base_url so _refine_slugs_for_sections builds a client
        run_config = {"llm": {"api_base_url": "http://fake.local"}}

        with patch(
            "launch.workers.w6_seo_optimizer.worker._generate_seo_slug_via_llm",
            side_effect=_fake_generate,
        ), patch(
            "launch.workers.w6_seo_optimizer.keyword_utils.SlugRefinementCache"
        ) as MockCache, patch(
            "launch.clients.llm_provider.create_llm_client_from_config",
            return_value=MagicMock(),
        ):
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_cache.pytrends_key.return_value = "pt"
            mock_cache.gemini_key.return_value = "gm"
            MockCache.return_value = mock_cache

            suggestions = _refine_slugs_for_sections(page_plan, tmp_path, run_config)

        # TC-3400: advisory-only — page_plan NOT mutated
        assert page_plan["pages"][0]["slug"] == "install-python"
        assert page_plan["pages"][1]["slug"] == "getting-started"
        assert page_plan["pages"][2]["slug"] == "overview"

        suggested_sections = {s["section"] for s in suggestions}
        # Only kb and blog should appear; docs must not
        assert "docs" not in suggested_sections
        assert len(suggestions) == 2

    def test_execute_seo_optimizer_calls_refine_when_enabled(self, tmp_path):
        """execute_seo_optimizer invokes _refine_slugs_for_sections when slug_rewrite_enabled=True."""
        pages = [_make_page("kb", "install-python")]
        run_dir, _ = _make_run_dir(tmp_path, pages)

        with patch(
            "launch.workers.w6_seo_optimizer.worker._refine_slugs_for_sections"
        ) as mock_refine, patch(
            "launch.workers.w6_seo_optimizer.worker.research_keywords"
        ) as mock_rk:
            mock_rk.return_value = {"primary_keywords": [], "long_tail": [], "per_page": {}}
            # TC-3400: _refine_slugs_for_sections now returns a list of suggestions
            mock_refine.return_value = []

            run_config = {"slug_rewrite_enabled": True}
            execute_seo_optimizer(run_dir, run_config)

        mock_refine.assert_called_once()


# ---------------------------------------------------------------------------
# TestSlugValidation — _is_valid_slug helper (used by W6)
# ---------------------------------------------------------------------------

class TestSlugValidation:
    """Verifies _is_valid_slug rejects invalid slugs before applying them."""

    def test_valid_slug(self):
        assert _is_valid_slug("getting-started") is True

    def test_too_long_slug(self):
        assert _is_valid_slug("a" * 41) is False

    def test_exactly_40_chars_valid(self):
        # 40-char slug is at the boundary and still valid
        assert _is_valid_slug("a" * 40) is True

    def test_41_chars_rejected(self):
        assert _is_valid_slug("a" * 41) is False

    def test_slug_with_underscore_rejected(self):
        # _is_valid_slug only allows [a-z0-9-]
        assert _is_valid_slug("hello_world") is False

    def test_slug_with_uppercase_rejected(self):
        assert _is_valid_slug("Getting-Started") is False

    def test_single_char_slug_rejected(self):
        # Pattern requires at least 2 chars: ^[a-z0-9][a-z0-9-]*[a-z0-9]$
        assert _is_valid_slug("a") is False

    def test_two_char_slug(self):
        assert _is_valid_slug("ab") is True

    def test_slug_starting_with_hyphen_rejected(self):
        assert _is_valid_slug("-bad-slug") is False

    def test_slug_ending_with_hyphen_rejected(self):
        assert _is_valid_slug("bad-slug-") is False

"""Unit tests for TC-REG-303: slug stability via prior_slugs pinning.

Tests verify that _refine_page_slugs respects prior_slugs and pins
existing slugs instead of sending them through LLM refinement.

REG-H-03: Also tests _load_prior_slugs for path resolution, error handling,
and graceful degradation on malformed input.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from launcher.models.plan import PlannedPage
from launcher.workers.planner.plan import _refine_page_slugs
from launcher.workers.planner.worker import _load_prior_slugs


def _make_page(page_id: str, slug: str, page_role: str = "feature_blog") -> PlannedPage:
    """Build a minimal PlannedPage with a slug in frontmatter."""
    return PlannedPage(
        page_id=page_id,
        page_role=page_role,
        title=f"Page {page_id}",
        frontmatter={"slug": slug, "url": f"/test/{slug}/"},
    )


class TestSlugPinning:
    """TC-REG-303: Prior slugs are pinned, new pages go through refinement."""

    def test_prior_slug_pinned(self):
        """A page with a matching page_id in prior_slugs should use the prior slug."""
        pages = [_make_page("kb/how-to-load", "how-to-load-files")]
        prior = {"kb/how-to-load": "loading-spreadsheets"}

        # No LLM client — refinement would return the slug as-is
        result = _refine_page_slugs(pages, prior_slugs=prior)

        assert result[0].frontmatter["slug"] == "loading-spreadsheets"
        assert "/loading-spreadsheets/" in result[0].frontmatter["url"]

    def test_prior_slug_same_as_current_no_change(self):
        """If prior slug matches current slug, no change needed."""
        pages = [_make_page("kb/how-to-load", "loading-spreadsheets")]
        prior = {"kb/how-to-load": "loading-spreadsheets"}

        result = _refine_page_slugs(pages, prior_slugs=prior)

        # Slug unchanged — page passes through to normal refinement path
        # (but with no LLM client, refine_slugs_batch returns as-is)
        assert result[0].frontmatter["slug"] == "loading-spreadsheets"

    def test_new_page_not_in_prior_goes_through_refinement(self):
        """Pages not in prior_slugs should go through normal refinement."""
        pages = [_make_page("kb/new-page", "new-topic")]
        prior = {"kb/how-to-load": "loading-spreadsheets"}

        # No LLM client — refine_slugs_batch returns slug as-is
        result = _refine_page_slugs(pages, prior_slugs=prior)

        assert result[0].frontmatter["slug"] == "new-topic"

    def test_empty_prior_slugs_no_change(self):
        """Empty prior_slugs should not change behavior."""
        pages = [_make_page("kb/how-to-load", "how-to-load-files")]

        result_without = _refine_page_slugs(pages, prior_slugs=None)
        result_with_empty = _refine_page_slugs(pages, prior_slugs={})

        assert result_without[0].frontmatter["slug"] == result_with_empty[0].frontmatter["slug"]

    def test_mixed_pinned_and_new(self):
        """Mix of pinned and new pages."""
        pages = [
            _make_page("kb/how-to-load", "how-to-load-files"),
            _make_page("kb/new-topic", "new-topic-slug"),
        ]
        prior = {"kb/how-to-load": "loading-spreadsheets"}

        result = _refine_page_slugs(pages, prior_slugs=prior)

        # First page pinned
        assert result[0].frontmatter["slug"] == "loading-spreadsheets"
        # Second page unchanged (no LLM client)
        assert result[1].frontmatter["slug"] == "new-topic-slug"

    def test_index_pages_not_refined(self):
        """Pages with slug='_index' should be skipped entirely."""
        pages = [_make_page("kb/_index", "_index")]
        prior = {"kb/_index": "some-other-slug"}

        result = _refine_page_slugs(pages, prior_slugs=prior)

        # _index pages are never refined — slug stays as-is
        assert result[0].frontmatter["slug"] == "_index"


# ---------------------------------------------------------------------------
# REG-H-03: _load_prior_slugs tests
# ---------------------------------------------------------------------------

def _make_context(tmp_path: Path, family: str = "cells", platform: str = "python") -> SimpleNamespace:
    """Build a minimal WorkerContext-like object for _load_prior_slugs testing."""
    # _load_prior_slugs expects: context.config.family, context.config.platform, context.run_dir
    # path resolution: run_dir.parent.parent / "phase_store" / family / platform / "plan.json"
    run_dir = tmp_path / "runs" / "run-001"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = SimpleNamespace(family=family, platform=platform)
    return SimpleNamespace(run_dir=run_dir, config=config)


class TestLoadPriorSlugs:
    """REG-H-03: _load_prior_slugs coverage."""

    def test_happy_path(self, tmp_path):
        """Valid plan.json with pages returns {page_id: slug} mapping."""
        ctx = _make_context(tmp_path)
        plan_dir = tmp_path / "phase_store" / "cells" / "python"
        plan_dir.mkdir(parents=True)
        plan_data = {
            "pages": [
                {"page_id": "kb/how-to-load", "frontmatter": {"slug": "loading-spreadsheets", "url": "/kb/loading-spreadsheets/"}},
                {"page_id": "kb/faq", "frontmatter": {"slug": "faq", "url": "/kb/faq/"}},
            ]
        }
        (plan_dir / "plan.json").write_text(json.dumps(plan_data), encoding="utf-8")
        result = _load_prior_slugs(ctx)
        assert result == {"kb/how-to-load": "loading-spreadsheets", "kb/faq": "faq"}

    def test_missing_file_returns_empty(self, tmp_path):
        """No plan.json returns {}."""
        ctx = _make_context(tmp_path)
        result = _load_prior_slugs(ctx)
        assert result == {}

    def test_malformed_json_returns_empty(self, tmp_path):
        """Invalid JSON returns {} without exception."""
        ctx = _make_context(tmp_path)
        plan_dir = tmp_path / "phase_store" / "cells" / "python"
        plan_dir.mkdir(parents=True)
        (plan_dir / "plan.json").write_text("{invalid json", encoding="utf-8")
        result = _load_prior_slugs(ctx)
        assert result == {}

    def test_missing_pages_key_returns_empty(self, tmp_path):
        """JSON without 'pages' key returns {}."""
        ctx = _make_context(tmp_path)
        plan_dir = tmp_path / "phase_store" / "cells" / "python"
        plan_dir.mkdir(parents=True)
        (plan_dir / "plan.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
        result = _load_prior_slugs(ctx)
        assert result == {}

    def test_page_without_slug_skipped(self, tmp_path):
        """Page entry missing frontmatter/slug is skipped gracefully."""
        ctx = _make_context(tmp_path)
        plan_dir = tmp_path / "phase_store" / "cells" / "python"
        plan_dir.mkdir(parents=True)
        plan_data = {
            "pages": [
                {"page_id": "kb/good", "frontmatter": {"slug": "good-slug"}},
                {"page_id": "kb/no-fm"},
                {"page_id": "kb/empty-fm", "frontmatter": {}},
                {"page_id": "kb/no-slug", "frontmatter": {"url": "/test/"}},
            ]
        }
        (plan_dir / "plan.json").write_text(json.dumps(plan_data), encoding="utf-8")
        result = _load_prior_slugs(ctx)
        assert result == {"kb/good": "good-slug"}

    def test_empty_pages_list_returns_empty(self, tmp_path):
        """Pages list is empty returns {}."""
        ctx = _make_context(tmp_path)
        plan_dir = tmp_path / "phase_store" / "cells" / "python"
        plan_dir.mkdir(parents=True)
        (plan_dir / "plan.json").write_text(json.dumps({"pages": []}), encoding="utf-8")
        result = _load_prior_slugs(ctx)
        assert result == {}

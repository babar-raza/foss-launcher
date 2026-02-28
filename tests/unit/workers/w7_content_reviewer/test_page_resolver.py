"""Tests for W7 PageResolver — correct slug resolution for index.md files.

TC-3500: Validates that PageResolver correctly derives slugs from parent
directory names for index.md files, resolves pages by output_path, slug+section,
and handles missing pages gracefully.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from launch.workers.w7_content_reviewer.page_resolver import (
    PageResolver,
    ResolvedPage,
)


class TestDeriveSlug:
    """PageResolver.derive_slug() tests."""

    def test_index_md_resolves_to_parent_dir_slug(self, tmp_path):
        """index.md files should derive slug from parent directory name."""
        d = tmp_path / "blog" / "python"
        d.mkdir(parents=True)
        md = d / "index.md"
        md.touch()
        assert PageResolver.derive_slug(md) == "python"

    def test_underscore_index_md_resolves_to_parent(self, tmp_path):
        """_index.md files (Hugo convention) also use parent directory."""
        d = tmp_path / "docs" / "tutorial"
        d.mkdir(parents=True)
        md = d / "_index.md"
        md.touch()
        assert PageResolver.derive_slug(md) == "tutorial"

    def test_non_index_md_resolves_to_stem(self, tmp_path):
        """Regular .md files should derive slug from filename stem."""
        d = tmp_path / "docs"
        d.mkdir(parents=True)
        md = d / "tutorial.md"
        md.touch()
        assert PageResolver.derive_slug(md) == "tutorial"


class TestPageResolverResolve:
    """PageResolver.resolve() tests."""

    def _make_resolver(self, tmp_path, pages):
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True)
        page_plan = {"pages": pages}
        return PageResolver(page_plan, drafts_dir), drafts_dir

    def test_output_path_match_priority(self, tmp_path):
        """output_path match takes priority over slug match."""
        pages = [
            {"slug": "wrong", "title": "Wrong", "output_path": "blog/python/index.md"},
            {"slug": "python", "title": "Python by slug"},
        ]
        resolver, drafts_dir = self._make_resolver(tmp_path, pages)
        d = drafts_dir / "blog" / "python"
        d.mkdir(parents=True)
        md = d / "index.md"
        md.touch()

        result = resolver.resolve(md)
        assert result is not None
        assert result.title == "Wrong"  # matched by output_path, not slug

    def test_section_disambiguation(self, tmp_path):
        """Two pages with same slug in different sections resolve independently."""
        pages = [
            {"slug": "overview", "section": "docs", "title": "Docs Overview"},
            {"slug": "overview", "section": "blog", "title": "Blog Overview"},
        ]
        resolver, drafts_dir = self._make_resolver(tmp_path, pages)

        docs_dir = drafts_dir / "docs"
        docs_dir.mkdir(parents=True)
        blog_dir = drafts_dir / "blog"
        blog_dir.mkdir(parents=True)

        md_docs = docs_dir / "overview.md"
        md_docs.touch()
        md_blog = blog_dir / "overview.md"
        md_blog.touch()

        r_docs = resolver.resolve(md_docs)
        r_blog = resolver.resolve(md_blog)
        assert r_docs is not None and r_docs.title == "Docs Overview"
        assert r_blog is not None and r_blog.title == "Blog Overview"

    def test_missing_page_returns_none(self, tmp_path):
        """File not in page_plan returns None."""
        resolver, drafts_dir = self._make_resolver(tmp_path, [])
        md = drafts_dir / "unknown.md"
        md.touch()

        result = resolver.resolve(md)
        assert result is None

    def test_resolve_all_populates_cache(self, tmp_path):
        """resolve_all() discovers all .md files and caches results."""
        pages = [
            {"slug": "a", "title": "Page A"},
            {"slug": "b", "title": "Page B"},
        ]
        resolver, drafts_dir = self._make_resolver(tmp_path, pages)
        (drafts_dir / "a.md").write_text("# A", encoding="utf-8")
        (drafts_dir / "b.md").write_text("# B", encoding="utf-8")
        (drafts_dir / "c.md").write_text("# C", encoding="utf-8")  # no page_plan entry

        resolved = resolver.resolve_all()
        # a and b should resolve, c should not (filtered from return)
        assert "a.md" in resolved
        assert "b.md" in resolved
        assert "c.md" not in resolved

    def test_claim_ids_populated(self, tmp_path):
        """ResolvedPage should carry claim_ids from page_plan entry."""
        pages = [
            {"slug": "feature", "title": "Feature", "claim_ids": ["c1", "c2"]},
        ]
        resolver, drafts_dir = self._make_resolver(tmp_path, pages)
        md = drafts_dir / "feature.md"
        md.write_text("# Feature", encoding="utf-8")

        result = resolver.resolve(md)
        assert result is not None
        assert result.claim_ids == ["c1", "c2"]

    def test_caching_same_file_twice(self, tmp_path):
        """Resolving the same file twice returns cached result."""
        pages = [{"slug": "cached", "title": "Cached"}]
        resolver, drafts_dir = self._make_resolver(tmp_path, pages)
        md = drafts_dir / "cached.md"
        md.write_text("# Cached", encoding="utf-8")

        r1 = resolver.resolve(md)
        r2 = resolver.resolve(md)
        assert r1 is r2  # Same object (cached)

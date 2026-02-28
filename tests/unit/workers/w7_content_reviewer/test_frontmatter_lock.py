"""Tests for W7 frontmatter invariant lock after LLM regen.

TC-3500: Validates that _enforce_frontmatter_lock() correctly restores
slug, permalink, and layout fields that LLM regen may corrupt.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from launch.workers.w7_content_reviewer.worker import _enforce_frontmatter_lock
from launch.workers.w7_content_reviewer.page_resolver import PageResolver


def _setup(tmp_path, page_entry, frontmatter_content):
    """Create a draft file with given frontmatter and return resolver."""
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir(parents=True)
    slug = page_entry.get("slug", "test")
    md = drafts_dir / f"{slug}.md"
    md.write_text(frontmatter_content, encoding="utf-8")
    resolver = PageResolver({"pages": [page_entry]}, drafts_dir)
    return drafts_dir, resolver, md


class TestEnforceFrontmatterLock:
    """_enforce_frontmatter_lock() tests."""

    def test_corrects_drifted_slug(self, tmp_path):
        """Slug field that differs from page_plan is restored."""
        page = {"slug": "tutorial", "permalink": "/tutorial/", "title": "Tutorial"}
        content = (
            "---\n"
            "title: Tutorial\n"
            "slug: wrong-slug\n"
            "permalink: /tutorial/\n"
            "---\n\n"
            "# Tutorial\n"
        )
        drafts_dir, resolver, md = _setup(tmp_path, page, content)
        corrected = _enforce_frontmatter_lock(drafts_dir, resolver)
        assert corrected == 1
        text = md.read_text(encoding="utf-8")
        assert "slug: tutorial" in text
        assert "wrong-slug" not in text

    def test_no_change_when_matching(self, tmp_path):
        """No correction when frontmatter already matches page_plan."""
        page = {"slug": "api", "permalink": "/api/"}
        content = (
            "---\n"
            "title: API\n"
            "slug: api\n"
            "permalink: /api/\n"
            "---\n\n"
            "# API Reference\n"
        )
        drafts_dir, resolver, md = _setup(tmp_path, page, content)
        corrected = _enforce_frontmatter_lock(drafts_dir, resolver)
        assert corrected == 0

    def test_adds_missing_field(self, tmp_path):
        """Missing locked field is appended to frontmatter."""
        page = {"slug": "guide", "layout": "single"}
        content = (
            "---\n"
            "title: Guide\n"
            "slug: guide\n"
            "---\n\n"
            "# Guide\n"
        )
        drafts_dir, resolver, md = _setup(tmp_path, page, content)
        corrected = _enforce_frontmatter_lock(drafts_dir, resolver)
        assert corrected == 1
        text = md.read_text(encoding="utf-8")
        assert "layout: single" in text

    def test_skips_unresolved_files(self, tmp_path):
        """Files not in page_plan are left untouched."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True)
        md = drafts_dir / "orphan.md"
        md.write_text("---\ntitle: Orphan\nslug: orphan\n---\n\n# Orphan\n", encoding="utf-8")
        resolver = PageResolver({"pages": []}, drafts_dir)
        corrected = _enforce_frontmatter_lock(drafts_dir, resolver)
        assert corrected == 0

    def test_preserves_non_locked_fields(self, tmp_path):
        """Non-locked fields (title, description) are untouched."""
        page = {"slug": "keep", "permalink": "/keep/"}
        content = (
            "---\n"
            "title: My Custom Title\n"
            "description: My custom description\n"
            "slug: wrong\n"
            "permalink: /keep/\n"
            "weight: 5\n"
            "---\n\n"
            "# Keep\n"
        )
        drafts_dir, resolver, md = _setup(tmp_path, page, content)
        _enforce_frontmatter_lock(drafts_dir, resolver)
        text = md.read_text(encoding="utf-8")
        assert "title: My Custom Title" in text
        assert "description: My custom description" in text
        assert "weight: 5" in text
        assert "slug: keep" in text

    def test_permalink_with_regex_special_chars(self, tmp_path):
        """SR-01: Permalink containing $1, braces, etc. must not crash or corrupt."""
        page = {"slug": "redir", "permalink": "/$1/redirect/{lang}/"}
        content = (
            "---\n"
            "title: Redirect\n"
            "slug: redir\n"
            "permalink: /old/path/\n"
            "---\n\n"
            "# Redirect\n"
        )
        drafts_dir, resolver, md = _setup(tmp_path, page, content)
        corrected = _enforce_frontmatter_lock(drafts_dir, resolver)
        assert corrected == 1
        text = md.read_text(encoding="utf-8")
        assert "permalink: /$1/redirect/{lang}/" in text
        # Ensure no regex back-reference corruption
        assert "\\g<1>" not in text
        assert "\\1" not in text

    def test_slug_with_regex_metacharacters(self, tmp_path):
        r"""SR-01: Slug containing regex metacharacters (e.g. \d, +, .) must survive."""
        # Use a file named "redir.md" but the page_plan expects a slug with
        # regex-special chars as the *permalink* (since slug is used as filename).
        page = {"slug": "redir", "permalink": r"/path\d+thing/[a-z]/"}
        content = (
            "---\n"
            "title: Test\n"
            "slug: redir\n"
            "permalink: /old/\n"
            "---\n\n"
            "# Test\n"
        )
        drafts_dir, resolver, md = _setup(tmp_path, page, content)
        corrected = _enforce_frontmatter_lock(drafts_dir, resolver)
        assert corrected == 1
        text = md.read_text(encoding="utf-8")
        assert r"permalink: /path\d+thing/[a-z]/" in text
        # Ensure no regex back-reference corruption
        assert "\\g<" not in text

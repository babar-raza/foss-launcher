"""Tests for TC-3625: W10 Malformed YAML Frontmatter Field-Preserving Fixer.

Tests fix_frontmatter_invalid_yaml() extension that extracts title/layout/permalink
from malformed content before falling back to synthetic defaults.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from launch.workers.w10_fixer.worker import (
    _extract_frontmatter_fields,
    _strip_trailing_yaml_lines,
    fix_frontmatter_invalid_yaml,
)


# ---------------------------------------------------------------------------
# _extract_frontmatter_fields helper tests
# ---------------------------------------------------------------------------


class TestExtractFrontmatterFields:
    def test_extracts_all_three_fields_unquoted(self):
        content = "---\ntitle: My Page\nlayout: docs\npermalink: /my-page/\n---\nBody"
        result = _extract_frontmatter_fields(content)
        assert result == {"title": "My Page", "layout": "docs", "permalink": "/my-page/"}

    def test_extracts_quoted_title_with_colon(self):
        content = 'title: "Page: Subtitle"\nlayout: docs\n'
        result = _extract_frontmatter_fields(content)
        assert result["title"] == "Page: Subtitle"

    def test_first_occurrence_wins(self):
        """Field appearing twice: first value kept."""
        content = "title: First Title\nSome prose\ntitle: Second Title\n"
        result = _extract_frontmatter_fields(content)
        assert result["title"] == "First Title"

    def test_returns_empty_dict_when_no_fields(self):
        content = "# Just a markdown heading\nSome body text with no YAML keys.\n"
        result = _extract_frontmatter_fields(content)
        assert result == {}

    def test_trailing_fields_after_body(self):
        """Handles the trailing-field pattern (YAML after body)."""
        content = (
            "---\nbad: yaml: content\n---\n"
            "# Body\n"
            "Some prose.\n"
            "title: Real Title\n"
            "layout: docs\n"
            "permalink: /real/\n"
        )
        result = _extract_frontmatter_fields(content)
        assert result["title"] == "Real Title"
        assert result["layout"] == "docs"
        assert result["permalink"] == "/real/"


# ---------------------------------------------------------------------------
# _strip_trailing_yaml_lines helper tests
# ---------------------------------------------------------------------------


class TestStripTrailingYamlLines:
    def test_strips_trailing_yaml_cluster(self):
        body = "# Body\n\nSome prose.\ntitle: Real Title\nlayout: docs\n"
        result = _strip_trailing_yaml_lines(body)
        assert "title:" not in result
        assert "layout:" not in result
        assert "# Body" in result
        assert "Some prose." in result

    def test_preserves_body_content_not_yaml(self):
        body = "# Heading\n\nNormal body text.\n"
        result = _strip_trailing_yaml_lines(body)
        assert result == body

    def test_strips_trailing_separator(self):
        body = "Body text.\n---\npermalink: /x/\n"
        result = _strip_trailing_yaml_lines(body)
        assert "---" not in result
        assert "permalink:" not in result
        assert "Body text." in result

    def test_empty_body_returns_empty(self):
        assert _strip_trailing_yaml_lines("") == ""


# ---------------------------------------------------------------------------
# fix_frontmatter_invalid_yaml end-to-end tests
# ---------------------------------------------------------------------------


class TestFixFrontmatterInvalidYaml:
    def _make_issue(self, path: str) -> dict:
        return {
            "error_code": "frontmatter_read_error_invalid_yaml",
            "location": {"path": path},
        }

    def test_trailing_fields_extracted(self, tmp_path):
        """File with title/layout/permalink after body → values preserved in fix."""
        md = tmp_path / "my-page.md"
        md.write_text(
            "---\nbad: yaml: colons\n---\n"
            "# Body heading\n\n"
            "Some prose content here.\n"
            "title: My Real Page\n"
            "layout: docs\n"
            "permalink: /my-real-page/\n",
            encoding="utf-8",
        )
        result = fix_frontmatter_invalid_yaml(self._make_issue(str(md)), tmp_path, None)
        assert result["fixed"] is True
        fixed = md.read_text(encoding="utf-8")
        assert "title: My Real Page" in fixed
        assert "layout: docs" in fixed
        assert "permalink: /my-real-page/" in fixed
        # Body prose preserved
        assert "Some prose content here." in fixed
        # Trailing YAML cluster stripped from body
        lines_after_fm = fixed.split("---\n", 2)[-1]
        assert "title: My Real Page\n" not in lines_after_fm or lines_after_fm.startswith("---\n")

    def test_minimal_fallback_when_no_fields(self, tmp_path):
        """No extractable fields → synthetic defaults used."""
        md = tmp_path / "some-doc.md"
        md.write_text(
            "---\n: bad yaml :\n---\n"
            "# Heading\n\nBody text only.\n",
            encoding="utf-8",
        )
        result = fix_frontmatter_invalid_yaml(self._make_issue(str(md)), tmp_path, None)
        assert result["fixed"] is True
        fixed = md.read_text(encoding="utf-8")
        # Synthetic title derived from stem
        assert "Some Doc" in fixed
        # layout and permalink synthesized
        assert "layout:" in fixed
        assert "permalink:" in fixed

    def test_title_with_colons_quoted(self, tmp_path):
        """title: "Page: Subtitle" extracted as 'Page: Subtitle'."""
        md = tmp_path / "page-subtitle.md"
        md.write_text(
            'title: "Page: Subtitle"\nlayout: docs\n\n# Body\nContent.\n',
            encoding="utf-8",
        )
        result = fix_frontmatter_invalid_yaml(self._make_issue(str(md)), tmp_path, None)
        assert result["fixed"] is True
        fixed = md.read_text(encoding="utf-8")
        assert "Page: Subtitle" in fixed

    def test_atomic_write_used(self, tmp_path):
        """Verify os.replace is called (atomic write path)."""
        md = tmp_path / "atomic-test.md"
        md.write_text(
            "---\nbad yaml\n---\n# Body\nContent.\ntitle: Atomic Page\n",
            encoding="utf-8",
        )
        replace_calls = []
        original_replace = os.replace

        def fake_replace(src, dst):
            replace_calls.append((src, dst))
            original_replace(src, dst)

        with patch("launch.workers.w10_fixer.worker.os.replace", side_effect=fake_replace):
            result = fix_frontmatter_invalid_yaml(
                self._make_issue(str(md)), tmp_path, None
            )

        assert result["fixed"] is True
        assert len(replace_calls) == 1, "os.replace should have been called exactly once"

    def test_no_file_returns_unfixed(self, tmp_path):
        """Missing file → returns fixed=False without raising."""
        result = fix_frontmatter_invalid_yaml(
            self._make_issue(str(tmp_path / "nonexistent.md")), tmp_path, None
        )
        assert result["fixed"] is False

    def test_body_content_not_stripped(self, tmp_path):
        """Markdown body is NOT accidentally stripped by trailing-yaml remover."""
        md = tmp_path / "preserve-body.md"
        body_text = (
            "# Introduction\n\n"
            "This is the main body paragraph.\n\n"
            "## Section Two\n\n"
            "More content here.\n"
        )
        md.write_text(
            "---\nbad: yaml\n---\n" + body_text,
            encoding="utf-8",
        )
        result = fix_frontmatter_invalid_yaml(self._make_issue(str(md)), tmp_path, None)
        assert result["fixed"] is True
        fixed = md.read_text(encoding="utf-8")
        assert "main body paragraph" in fixed
        assert "More content here." in fixed

    def test_idempotent_no_issue_is_noop(self, tmp_path):
        """File with no location path → fixed=False, not a crash."""
        result = fix_frontmatter_invalid_yaml(
            {"error_code": "frontmatter_read_error_invalid_yaml", "location": {}},
            tmp_path,
            None,
        )
        assert result["fixed"] is False

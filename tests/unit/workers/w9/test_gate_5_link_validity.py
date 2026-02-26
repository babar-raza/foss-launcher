"""TC-2830: Tests for Gate 5 link validation upgrade.

Covers:
- Placeholder URL detection (example.com, localhost)
- Doubled path segment detection (/python/python/)
- Absolute link validation against permalink index
- Existing relative link validation (backward compat)
- Code fence skipping
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_5_cross_page_link_validity import (
    execute_gate,
    _build_permalink_index,
    _check_external_link,
    _PLACEHOLDER_DOMAINS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


# ---------------------------------------------------------------------------
# Placeholder URL detection
# ---------------------------------------------------------------------------

class TestPlaceholderUrls:

    def test_example_com_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "See [API docs](https://example.com/api) for more.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "GATE_LINK_PLACEHOLDER_URL" for i in issues)

    def test_localhost_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "Visit [here](http://localhost:8080/docs)")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "GATE_LINK_PLACEHOLDER_URL" for i in issues)

    def test_todo_in_url_warns(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "See [docs](https://docs.aspose.com/TODO/page)")
        passed, issues = execute_gate(run_dir, "ci")
        warn_issues = [i for i in issues if i["error_code"] == "GATE_LINK_PLACEHOLDER_KEYWORD"]
        assert len(warn_issues) >= 1

    def test_real_external_link_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "See [docs](https://docs.aspose.com/3d/python/overview/)")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_local_profile_demotes_placeholder_to_warn(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "See [API](https://example.com/api)")
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True  # warn doesn't fail
        assert issues[0]["severity"] == "warn"


# ---------------------------------------------------------------------------
# Doubled path segments
# ---------------------------------------------------------------------------

class TestDoubledPathSegments:

    def test_doubled_python_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "See [page](/python/python/kb/open-file/)")
        passed, issues = execute_gate(run_dir, "ci")
        assert any(i["error_code"] == "GATE_LINK_DOUBLED_SEGMENT" for i in issues)

    def test_normal_absolute_link_no_double(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md",
            "See [page](/3d/python/kb/open-file/)")
        passed, issues = execute_gate(run_dir, "ci")
        doubled = [i for i in issues if i["error_code"] == "GATE_LINK_DOUBLED_SEGMENT"]
        assert len(doubled) == 0


# ---------------------------------------------------------------------------
# Permalink index
# ---------------------------------------------------------------------------

class TestBuildPermalinkIndex:

    def test_index_includes_filesystem_paths(self, tmp_path):
        site_dir = tmp_path / "site"
        content_dir = site_dir / "content" / "docs" / "3d" / "python"
        content_dir.mkdir(parents=True)
        md = content_dir / "overview.md"
        md.write_text("# Overview", encoding="utf-8")

        index = _build_permalink_index([md], site_dir)
        assert "/docs/3d/python/overview/" in index or "/content/docs/3d/python/overview/" in index

    def test_index_reads_frontmatter_url(self, tmp_path):
        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        md = site_dir / "content" / "page.md"
        md.write_text("---\nurl: /3d/python/kb/open-file/\n---\n# Content", encoding="utf-8")

        index = _build_permalink_index([md], site_dir)
        assert "/3d/python/kb/open-file/" in index


# ---------------------------------------------------------------------------
# Code fence skipping
# ---------------------------------------------------------------------------

class TestCodeFenceSkipping:

    def test_links_in_code_fences_ignored(self, tmp_path):
        run_dir = tmp_path / "run"
        content = (
            "Normal text.\n\n"
            "```python\n"
            "# See [fake](https://example.com/fake)\n"
            "```\n\n"
            "More text."
        )
        _write_md(run_dir, "page.md", content)
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True


# ---------------------------------------------------------------------------
# Backward compat: relative links
# ---------------------------------------------------------------------------

class TestRelativeLinks:

    def test_valid_relative_link_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "See [other](other.md)")
        _write_md(run_dir, "other.md", "# Other")
        passed, issues = execute_gate(run_dir, "ci")
        broken = [i for i in issues if i["error_code"] == "GATE_LINK_BROKEN_INTERNAL"]
        assert len(broken) == 0

    def test_broken_relative_link_fails(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "See [missing](nonexistent.md)")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

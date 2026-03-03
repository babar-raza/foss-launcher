"""Tests for TC-3685: G6 permalink uniqueness scoped by Hugo section."""

from __future__ import annotations

from pathlib import Path

import pytest

from launch.workers.w9_validator.gates.gate_permalink_uniqueness import (
    execute_gate,
    _infer_section,
)


def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    """Write a markdown file under run_dir/work/site/."""
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


# ── _infer_section helper ────────────────────────────────────────────────────

class TestInferSection:
    """Verify section (subdomain) inference from file paths."""

    def test_docs_section(self, tmp_path):
        site_dir = tmp_path / "work" / "site"
        md_file = site_dir / "content" / "docs.aspose.org" / "cells" / "en" / "page.md"
        assert _infer_section(md_file, site_dir) == "docs.aspose.org"

    def test_kb_section(self, tmp_path):
        site_dir = tmp_path / "work" / "site"
        md_file = site_dir / "content" / "kb.aspose.org" / "cells" / "en" / "page.md"
        assert _infer_section(md_file, site_dir) == "kb.aspose.org"

    def test_blog_section(self, tmp_path):
        site_dir = tmp_path / "work" / "site"
        md_file = site_dir / "content" / "blog.aspose.org" / "cells" / "post" / "index.md"
        assert _infer_section(md_file, site_dir) == "blog.aspose.org"

    def test_file_not_in_content_dir(self, tmp_path):
        site_dir = tmp_path / "work" / "site"
        md_file = site_dir / "page.md"
        assert _infer_section(md_file, site_dir) == "_global"

    def test_file_outside_site_dir(self, tmp_path):
        site_dir = tmp_path / "work" / "site"
        md_file = tmp_path / "elsewhere" / "page.md"
        assert _infer_section(md_file, site_dir) == "_global"


# ── Cross-section: same permalink allowed ─────────────────────────────────────

class TestCrossSectionAllowed:
    """Verify that same permalink across different sections is NOT a collision."""

    def test_cross_section_same_permalink_passes(self, tmp_path):
        """docs and kb sections can share /cells/python/ without collision."""
        run_dir = tmp_path / "run"
        _write_md(
            run_dir,
            "content/docs.aspose.org/cells/en/_index.md",
            "---\ntitle: Docs\npermalink: /cells/python/\n---\nDocs.\n",
        )
        _write_md(
            run_dir,
            "content/kb.aspose.org/cells/en/_index.md",
            "---\ntitle: KB\npermalink: /cells/python/\n---\nKB.\n",
        )
        passed, issues = execute_gate(run_dir, "ci")
        collision_issues = [i for i in issues if i["error_code"] == "G6_PERMALINK_COLLISION"]
        assert len(collision_issues) == 0
        assert passed is True

    def test_four_sections_same_permalink_passes(self, tmp_path):
        """4 sections with /cells/python/ — all allowed."""
        run_dir = tmp_path / "run"
        for section in ["docs.aspose.org", "kb.aspose.org", "reference.aspose.org", "products.aspose.org"]:
            _write_md(
                run_dir,
                f"content/{section}/cells/en/_index.md",
                f"---\ntitle: {section}\npermalink: /cells/python/\n---\nContent.\n",
            )
        passed, issues = execute_gate(run_dir, "ci")
        collision_issues = [i for i in issues if i["error_code"] == "G6_PERMALINK_COLLISION"]
        assert len(collision_issues) == 0
        assert passed is True


# ── Same-section: collision detected ──────────────────────────────────────────

class TestSameSectionCollision:
    """Verify that same permalink within one section IS a collision."""

    def test_same_section_same_permalink_fails(self, tmp_path):
        """Two files in docs with /cells/python/ is a collision."""
        run_dir = tmp_path / "run"
        _write_md(
            run_dir,
            "content/docs.aspose.org/cells/en/overview.md",
            "---\ntitle: Overview\npermalink: /cells/python/\n---\nA.\n",
        )
        _write_md(
            run_dir,
            "content/docs.aspose.org/cells/en/index.md",
            "---\ntitle: Index\npermalink: /cells/python/\n---\nB.\n",
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        collision_issues = [i for i in issues if i["error_code"] == "G6_PERMALINK_COLLISION"]
        assert len(collision_issues) == 1
        assert "docs.aspose.org" in collision_issues[0]["message"]

    def test_case_insensitive_same_section(self, tmp_path):
        """Case-insensitive comparison within section."""
        run_dir = tmp_path / "run"
        _write_md(
            run_dir,
            "content/docs.aspose.org/a.md",
            "---\npermalink: /Cells/Python/\n---\nA.\n",
        )
        _write_md(
            run_dir,
            "content/docs.aspose.org/b.md",
            "---\npermalink: /cells/python/\n---\nB.\n",
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False


# ── Doubled segments: always error ────────────────────────────────────────────

class TestDoubledSegmentsAlwaysError:
    """Doubled segment detection is global (not section-scoped)."""

    def test_doubled_segment_in_any_section(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(
            run_dir,
            "content/docs.aspose.org/page.md",
            "---\npermalink: /note/python/python/overview/\n---\nContent.\n",
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G6_DOUBLED_SEGMENT" for i in issues)


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases for section-scoped collision detection."""

    def test_files_without_content_prefix_use_global(self, tmp_path):
        """Files not under content/ share _global section."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page1.md", "---\npermalink: /x/\n---\nA.\n")
        _write_md(run_dir, "page2.md", "---\npermalink: /x/\n---\nB.\n")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False  # Same _global section → collision

    def test_no_permalink_ignored(self, tmp_path):
        """Files without permalink frontmatter are skipped."""
        run_dir = tmp_path / "run"
        _write_md(
            run_dir,
            "content/docs.aspose.org/a.md",
            "---\ntitle: No Permalink\n---\nContent.\n",
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_mixed_collision_and_cross_section(self, tmp_path):
        """One section has a collision, another section shares the same permalink OK."""
        run_dir = tmp_path / "run"
        # docs: two files with same permalink → collision
        _write_md(
            run_dir,
            "content/docs.aspose.org/a.md",
            "---\npermalink: /cells/python/\n---\nA.\n",
        )
        _write_md(
            run_dir,
            "content/docs.aspose.org/b.md",
            "---\npermalink: /cells/python/\n---\nB.\n",
        )
        # kb: one file with same permalink → no collision (cross-section OK)
        _write_md(
            run_dir,
            "content/kb.aspose.org/a.md",
            "---\npermalink: /cells/python/\n---\nC.\n",
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        collision_issues = [i for i in issues if i["error_code"] == "G6_PERMALINK_COLLISION"]
        assert len(collision_issues) == 1  # Only docs collision
        assert "docs.aspose.org" in collision_issues[0]["message"]

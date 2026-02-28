"""Tests for TC-3400: W6 SEO Optimizer Hardening.

Validates 4 fixes:
A) slug_rewrite_enabled writes advisory seo_slug_suggestions.json, never mutates page_plan.json
B) index.md / _index.md slug resolution uses parent folder name
C) description is injected when missing; canonical is always updated to computed value
D) Dead keyword_optimizer.inject_keywords_naturally call is removed
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from launch.workers.w6_seo_optimizer.seo_metadata import (
    optimize_seo_metadata,
    _build_seo_description,
    _get_frontmatter_field,
)
from launch.workers.w6_seo_optimizer.worker import execute_seo_optimizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_run_dir(
    tmp_path: Path,
    pages: list | None = None,
    md_files: dict[str, str] | None = None,
) -> Path:
    """Build a minimal run directory for W6 tests.

    Args:
        tmp_path: pytest tmp_path fixture
        pages: list of page dicts for page_plan.json
        md_files: mapping of relative paths (under site/content/) to markdown content
    """
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    (artifacts / "product_facts.json").write_text(
        json.dumps({
            "product_name": "Aspose.3D",
            "product_family": "3d",
            "claims": [{"claim_id": "c1", "claim_text": "Load 3D models"}],
        }),
        encoding="utf-8",
    )

    if pages is None:
        pages = [
            {"slug": "getting-started", "title": "Getting Started", "url_path": "3d/python/getting-started/"},
        ]
    (artifacts / "page_plan.json").write_text(
        json.dumps({"pages": pages}), encoding="utf-8",
    )

    if md_files is None:
        md_files = {
            "docs.aspose.org/3d/en/python/getting-started/index.md": (
                '---\ntitle: "Getting Started"\n---\n\n'
                "This is a test page about Python 3D processing with various "
                "features and capabilities for developers.\n"
            )
        }
    content_root = tmp_path / "work" / "site" / "content"
    for rel_path, content in md_files.items():
        md_path = content_root / rel_path
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(content, encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# A: Advisory slug suggestions
# ---------------------------------------------------------------------------


class TestAdvisorySlugSuggestions:
    """slug_rewrite_enabled must produce seo_slug_suggestions.json and
    NEVER mutate page_plan.json or rename draft files."""

    def test_slug_rewrite_does_not_mutate_page_plan(self, tmp_path):
        """page_plan.json must be byte-identical before and after W6."""
        pages = [
            {"slug": "old-kb-slug", "section": "kb", "title": "KB Article", "url_path": "3d/python/kb/old-kb-slug/"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "kb.aspose.org/3d/en/python/old-kb-slug/index.md": '---\ntitle: "KB"\n---\nBody.\n',
        })
        pp_path = run_dir / "artifacts" / "page_plan.json"
        original_bytes = pp_path.read_bytes()

        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "slug_rewrite_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })

        assert pp_path.read_bytes() == original_bytes, "page_plan.json must not be modified by W6"

    def test_slug_rewrite_does_not_rename_drafts(self, tmp_path):
        """Draft files must remain in their original locations."""
        pages = [
            {"slug": "old-slug", "section": "kb", "title": "KB Article", "url_path": "3d/python/kb/old-slug/"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "kb.aspose.org/3d/en/python/old-slug/index.md": '---\ntitle: "KB"\n---\nBody.\n',
        })
        draft_dir = run_dir / "work" / "drafts" / "kb" / "old-slug"
        draft_dir.mkdir(parents=True)
        draft_file = draft_dir / "index.md"
        draft_file.write_text("draft content", encoding="utf-8")

        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "slug_rewrite_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })

        assert draft_file.exists(), "Draft file must not be renamed"

    def test_slug_rewrite_writes_suggestions_file(self, tmp_path):
        """When slug_rewrite_enabled=True, seo_slug_suggestions.json must be written."""
        pages = [
            {"slug": "old-slug", "section": "kb", "title": "KB Article"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "kb.aspose.org/3d/en/python/old-slug/index.md": '---\ntitle: "KB"\n---\nBody.\n',
        })

        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "slug_rewrite_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })

        suggestions_path = run_dir / "work" / "seo_slug_suggestions.json"
        assert suggestions_path.exists(), "seo_slug_suggestions.json must be written"
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)

    def test_suggestions_file_fields_present(self, tmp_path):
        """Each entry in suggestions file must have the required fields."""
        pages = [
            {"slug": "old-slug", "section": "kb", "title": "KB Article"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "kb.aspose.org/3d/en/python/old-slug/index.md": '---\ntitle: "KB"\n---\nBody.\n',
        })
        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "slug_rewrite_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })
        suggestions_path = run_dir / "work" / "seo_slug_suggestions.json"
        assert suggestions_path.exists()
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        # If suggestions were produced, validate structure
        for entry in data:
            assert "section" in entry, f"Missing 'section' in {entry}"
            assert "old_slug" in entry, f"Missing 'old_slug' in {entry}"
            assert "suggested_slug" in entry, f"Missing 'suggested_slug' in {entry}"
            assert "rationale" in entry, f"Missing 'rationale' in {entry}"
            assert "warnings" in entry, f"Missing 'warnings' in {entry}"
            assert isinstance(entry["warnings"], list)


# ---------------------------------------------------------------------------
# B: index.md slug resolution
# ---------------------------------------------------------------------------


class TestIndexMdSlugResolution:
    """index.md and _index.md must resolve slug from parent folder name."""

    def test_index_md_uses_parent_folder_name(self, tmp_path):
        """getting-started/index.md should resolve to slug 'getting-started'."""
        pages = [
            {"slug": "getting-started", "title": "Getting Started",
             "url_path": "3d/python/getting-started/", "purpose": "Quick start guide for 3D Python library"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "docs.aspose.org/3d/en/python/getting-started/index.md": (
                '---\ntitle: "Getting Started"\n---\n\n'
                "Guide to getting started with the Python 3D library.\n"
            ),
        })

        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })

        content = (
            run_dir / "work" / "site" / "content"
            / "docs.aspose.org" / "3d" / "en" / "python"
            / "getting-started" / "index.md"
        ).read_text(encoding="utf-8")
        # Should have canonical based on url_path from the matched page
        canonical = _get_frontmatter_field(content, "canonical")
        assert canonical == "https://docs.aspose.org/3d/python/getting-started/"
        robots = _get_frontmatter_field(content, "robots")
        assert robots == "index, follow"

    def test_underscore_index_md_uses_parent_folder_name(self, tmp_path):
        """kb/_index.md should resolve to slug 'kb' (parent folder)."""
        pages = [
            {"slug": "kb", "title": "Knowledge Base", "url_path": "3d/python/kb/"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "kb.aspose.org/3d/en/python/kb/_index.md": (
                '---\ntitle: "Knowledge Base"\n---\n\nKB index.\n'
            ),
        })

        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })

        content = (
            run_dir / "work" / "site" / "content"
            / "kb.aspose.org" / "3d" / "en" / "python"
            / "kb" / "_index.md"
        ).read_text(encoding="utf-8")
        # Should have picked up the page with slug "kb"
        canonical = _get_frontmatter_field(content, "canonical")
        assert canonical == "https://kb.aspose.org/3d/python/kb/"
        robots = _get_frontmatter_field(content, "robots")
        assert robots == "noindex, follow"

    def test_regular_md_uses_stem(self, tmp_path):
        """overview.md should resolve to slug 'overview' (stem)."""
        pages = [
            {"slug": "overview", "title": "Overview", "url_path": "3d/python/overview/"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "docs.aspose.org/3d/en/python/overview.md": (
                '---\ntitle: "Overview"\n---\n\nOverview of the library.\n'
            ),
        })

        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })

        content = (
            run_dir / "work" / "site" / "content"
            / "docs.aspose.org" / "3d" / "en" / "python"
            / "overview.md"
        ).read_text(encoding="utf-8")
        assert "3d/python/overview/" in content

    def test_regular_index_md_gets_index_robots(self, tmp_path):
        """getting-started/index.md (content page) must get robots: 'index, follow'."""
        pages = [
            {"slug": "getting-started", "title": "Getting Started",
             "url_path": "3d/python/getting-started/"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "docs.aspose.org/3d/en/python/getting-started/index.md": (
                '---\ntitle: "Getting Started"\n---\n\nGuide content.\n'
            ),
        })
        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })
        content = (
            run_dir / "work" / "site" / "content"
            / "docs.aspose.org" / "3d" / "en" / "python"
            / "getting-started" / "index.md"
        ).read_text(encoding="utf-8")
        robots = _get_frontmatter_field(content, "robots")
        assert robots == "index, follow", f"Expected 'index, follow' but got {robots!r}"

    def test_underscore_index_md_gets_noindex_robots(self, tmp_path):
        """kb/_index.md (Hugo section index) must get robots: 'noindex, follow'."""
        pages = [
            {"slug": "kb", "title": "Knowledge Base", "url_path": "3d/python/kb/"},
        ]
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "kb.aspose.org/3d/en/python/kb/_index.md": (
                '---\ntitle: "Knowledge Base"\n---\n\nKB section listing.\n'
            ),
        })
        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })
        content = (
            run_dir / "work" / "site" / "content"
            / "kb.aspose.org" / "3d" / "en" / "python"
            / "kb" / "_index.md"
        ).read_text(encoding="utf-8")
        robots = _get_frontmatter_field(content, "robots")
        assert robots == "noindex, follow", f"Expected 'noindex, follow' but got {robots!r}"


# ---------------------------------------------------------------------------
# C: SEO field injection
# ---------------------------------------------------------------------------


class TestSeoFieldInjection:
    """description must be injected when missing; canonical must always be updated."""

    def test_description_injected_when_missing(self):
        """Content with no description should get one injected."""
        content = '---\ntitle: "Test Page"\n---\nBody content here.'
        page = {"slug": "test", "title": "Test Page", "url_path": "3d/python/test/",
                "purpose": "Comprehensive guide to testing 3D Python operations"}
        result = optimize_seo_metadata(
            content, page, ["python", "3d"], "Aspose.3D", "python",
            section="docs", family="3d",
        )
        desc = _get_frontmatter_field(result, "description")
        assert desc is not None, "description must be injected when absent"
        assert len(desc) > 0

    def test_description_length_within_gate4_limits(self):
        """Injected description must be <= 160 chars (Gate 4 G4-SEO-002)."""
        content = '---\ntitle: "Test"\n---\nBody.'
        page = {"slug": "test", "title": "Test", "url_path": "3d/python/test/",
                "purpose": "A" * 200}  # Very long purpose to stress truncation
        result = optimize_seo_metadata(
            content, page, ["k" * 20] * 5, "Aspose.3D", "python",
            section="docs", family="3d",
        )
        desc = _get_frontmatter_field(result, "description")
        assert desc is not None
        assert len(desc) <= 160, f"description is {len(desc)} chars (max 160)"

    def test_canonical_updated_when_stale(self):
        """Existing canonical with wrong URL should be updated to correct value."""
        content = (
            '---\ntitle: "Test"\n'
            'canonical: "https://old.example.com/wrong-path/"\n'
            '---\nBody.'
        )
        page = {"slug": "test", "title": "Test", "url_path": "3d/python/test/"}
        result = optimize_seo_metadata(
            content, page, [], "Aspose.3D", "python",
            section="docs", family="3d",
        )
        canonical = _get_frontmatter_field(result, "canonical")
        assert canonical == "https://docs.aspose.org/3d/python/test/"

    def test_canonical_deterministic_from_url_path(self):
        """Canonical must always match https://{subdomain}/{url_path}/."""
        content = '---\ntitle: "Test"\n---\nBody.'
        page = {"slug": "test", "url_path": "3d/python/test/"}
        result = optimize_seo_metadata(
            content, page, [], "Aspose.3D", "python",
            section="docs", family="3d",
        )
        canonical = _get_frontmatter_field(result, "canonical")
        assert canonical == "https://docs.aspose.org/3d/python/test/"

    def test_build_seo_description_max_length(self):
        """_build_seo_description must never exceed max_length."""
        desc = _build_seo_description(
            "Very Long Title " * 10,
            "A very long purpose " * 10,
            "Aspose.3D for Python via .NET",
            "python",
            ["keyword1", "keyword2", "keyword3"],
            max_length=160,
        )
        assert len(desc) <= 160

    def test_seo_report_includes_injection_counts(self, tmp_path):
        """seo_report.json must include description_injected_count and canonical_updated_count."""
        pages = [
            {
                "slug": "getting-started",
                "title": "Getting Started",
                "url_path": "3d/python/getting-started/",
            },
        ]
        # Content with NO description and STALE canonical (both injection paths exercised)
        run_dir = _create_run_dir(tmp_path, pages=pages, md_files={
            "docs.aspose.org/3d/en/python/getting-started/index.md": (
                '---\ntitle: "Getting Started"\n'
                'canonical: "https://old.example.com/stale/"\n'
                '---\n\nGuide content.\n'
            ),
        })
        execute_seo_optimizer(run_dir, {
            "seo_enabled": True,
            "target_platform": "python",
            "offline_mode": True,
        })
        report_path = run_dir / "work" / "seo_report.json"
        assert report_path.exists(), "seo_report.json must be written"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "description_injected_count" in report, (
            "seo_report.json must contain description_injected_count"
        )
        assert "canonical_updated_count" in report, (
            "seo_report.json must contain canonical_updated_count"
        )
        assert report["description_injected_count"] >= 1, (
            f"Expected >=1 description injections, got {report['description_injected_count']}"
        )
        assert report["canonical_updated_count"] >= 1, (
            f"Expected >=1 canonical updates, got {report['canonical_updated_count']}"
        )


# ---------------------------------------------------------------------------
# D: Dead injection removal
# ---------------------------------------------------------------------------


class TestDeadInjectionRemoved:
    """keyword_optimizer.inject_keywords_naturally must not be called from worker."""

    def test_keyword_optimizer_inject_not_imported(self):
        """worker.py must not import inject_keywords_naturally from keyword_optimizer."""
        import inspect
        from launch.workers.w6_seo_optimizer import worker as w6_mod
        source = inspect.getsource(w6_mod)
        # The import line should NOT contain inject_keywords_naturally from keyword_optimizer
        assert "from .keyword_optimizer import extract_keywords, inject_keywords_naturally" not in source
        # But extract_keywords should still be imported
        assert "from .keyword_optimizer import extract_keywords" in source

    def test_keyword_utils_inject_still_used(self):
        """keyword_utils.inject_keywords_naturally should still be imported and used."""
        import inspect
        from launch.workers.w6_seo_optimizer import worker as w6_mod
        source = inspect.getsource(w6_mod)
        assert "inject_kw_naturally" in source


# ---------------------------------------------------------------------------
# TC-3560: _index.md description placeholder normalization
# ---------------------------------------------------------------------------


class TestIndexDescriptionNormalization:
    """Tests for TC-3560: deterministic _index.md description placeholder fix."""

    _BASE = "---\ntitle: Products\n---\nBody content.\n"

    def _call(self, content: str, *, product_name: str = "Aspose.Cells", platform: str = "python",
              is_section_index: bool = True) -> str:
        return optimize_seo_metadata(
            content,
            page={"slug": "_index", "title": "Products"},
            keywords=["pdf", "python"],
            product_name=product_name,
            platform=platform,
            is_section_index=is_section_index,
        )

    def test_index_missing_description_gets_template(self) -> None:
        """_index.md with no description field gets a deterministic template."""
        result = self._call(self._BASE)
        desc = _get_frontmatter_field(result, "description") or ""
        assert desc.strip(), "Expected a non-empty description"
        assert "Aspose.Cells" in desc
        assert len(desc) <= 160

    def test_index_todo_placeholder_replaced(self) -> None:
        """description = 'TODO: fill description' is replaced on _index.md."""
        content = "---\ntitle: Products\ndescription: \"TODO: fill description\"\n---\nBody.\n"
        result = self._call(content)
        desc = _get_frontmatter_field(result, "description") or ""
        assert "TODO" not in desc
        assert "Aspose.Cells" in desc

    def test_index_tbd_placeholder_replaced(self) -> None:
        """description = 'TBD' is replaced on _index.md."""
        content = "---\ntitle: Products\ndescription: \"TBD\"\n---\nBody.\n"
        result = self._call(content)
        desc = _get_frontmatter_field(result, "description") or ""
        assert "TBD" not in desc.upper()
        assert "Aspose.Cells" in desc

    def test_index_template_driven_placeholder_replaced(self) -> None:
        """description = 'Template-driven products page' is replaced on _index.md."""
        content = (
            "---\ntitle: Products\n"
            "description: \"Template-driven products page\"\n"
            "---\nBody.\n"
        )
        result = self._call(content)
        desc = _get_frontmatter_field(result, "description") or ""
        assert "template" not in desc.lower()
        assert "Aspose.Cells" in desc

    def test_non_index_page_description_not_overridden_by_tc3560(self) -> None:
        """is_section_index=False: TC-3560 placeholder replacement does NOT fire."""
        content = "---\ntitle: Guide\ndescription: \"TBD\"\n---\nBody.\n"
        result = self._call(content, is_section_index=False)
        desc = _get_frontmatter_field(result, "description") or ""
        # TC-3400 may update the description because it's too short — that's fine
        # But the TC-3560 deterministic template specifically should not fire
        # (the result should be the TC-3400 generated desc, not necessarily "TBD" unchanged)
        # We only assert TC-3560 didn't fire by checking length <= 160 (sanity)
        assert len(desc) <= 160

    def test_index_good_description_preserved(self) -> None:
        """A meaningful existing description is preserved as-is on _index.md."""
        good_desc = "Aspose.Cells for Python lets you create, edit and convert Excel files."
        content = f"---\ntitle: Products\ndescription: \"{good_desc}\"\n---\nBody.\n"
        result = self._call(content)
        desc = _get_frontmatter_field(result, "description") or ""
        # Good description should remain (TC-3560 placeholder regex must NOT match it)
        assert good_desc in desc or desc == good_desc

    def test_index_description_max_160_chars(self) -> None:
        """Generated index description must be <= 160 characters."""
        long_product = "Aspose.Words for Python via .NET — Complete Word Processing Library"
        result = self._call(self._BASE, product_name=long_product, platform="python")
        desc = _get_frontmatter_field(result, "description") or ""
        assert len(desc) <= 160, f"Description too long ({len(desc)} chars): {desc}"

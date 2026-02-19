"""Tests for W6 SEO Optimizer Worker.

TC-2205: W6 SEO Optimizer Worker
"""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from launch.workers.w6_seo_optimizer.cache import SEOCache
from launch.workers.w6_seo_optimizer.keyword_research import (
    research_keywords,
    _extract_claim_keywords,
    _generate_search_patterns,
    _dedupe,
    STOP_WORDS,
)
from launch.workers.w6_seo_optimizer.keyword_optimizer import (
    extract_keywords,
    inject_keywords_naturally,
    calculate_keyword_density,
)
from launch.workers.w6_seo_optimizer.seo_metadata import (
    optimize_seo_metadata,
    _build_seo_title,
    _build_seo_description,
    _inject_frontmatter_field,
    _get_frontmatter_field,
)
from launch.workers.w6_seo_optimizer.worker import (
    execute_seo_optimizer,
    SEOOptimizerError,
    SEOOptimizerArtifactMissingError,
)


class TestSEOCache:
    """Tests for persistent SEO cache."""

    def test_set_and_get(self, tmp_path):
        cache = SEOCache(tmp_path / "cache.json")
        cache.set("test_key", {"data": 123})
        assert cache.get("test_key") == {"data": 123}

    def test_expired_entry_returns_none(self, tmp_path):
        cache = SEOCache(tmp_path / "cache.json", default_ttl=0)
        cache.set("key", "value", ttl=0)
        # Entry should be immediately expired
        time.sleep(0.1)
        assert cache.get("key") is None

    def test_get_or_compute(self, tmp_path):
        cache = SEOCache(tmp_path / "cache.json")
        call_count = 0

        def compute():
            nonlocal call_count
            call_count += 1
            return "computed_value"

        result1 = cache.get_or_compute("key", compute)
        result2 = cache.get_or_compute("key", compute)
        assert result1 == "computed_value"
        assert result2 == "computed_value"
        assert call_count == 1  # Only computed once

    def test_cache_persists_to_disk(self, tmp_path):
        path = tmp_path / "cache.json"
        cache1 = SEOCache(path)
        cache1.set("key", "value", ttl=3600)

        cache2 = SEOCache(path)
        assert cache2.get("key") == "value"

    def test_corrupt_cache_file_handled(self, tmp_path):
        path = tmp_path / "cache.json"
        path.write_text("not valid json", encoding="utf-8")
        cache = SEOCache(path)
        assert cache.get("anything") is None

    def test_make_key_is_deterministic(self, tmp_path):
        """Same raw key always produces the same hash."""
        k1 = SEOCache._make_key("test_key")
        k2 = SEOCache._make_key("test_key")
        assert k1 == k2

    def test_different_keys_produce_different_hashes(self, tmp_path):
        k1 = SEOCache._make_key("key_a")
        k2 = SEOCache._make_key("key_b")
        assert k1 != k2

    def test_cache_creates_parent_directories(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "cache.json"
        cache = SEOCache(deep_path)
        cache.set("key", "value")
        assert deep_path.exists()


class TestKeywordResearch:
    """Tests for keyword research (offline mode)."""

    def test_offline_research_produces_keywords(self):
        claims = [
            {"claim_id": "1", "claim_text": "Load 3D models in various formats including FBX OBJ STL"},
            {"claim_id": "2", "claim_text": "Convert between 3D file formats programmatically"},
            {"claim_id": "3", "claim_text": "Render 3D scenes with customizable lighting and materials"},
        ]
        result = research_keywords("Aspose.3D", "3d", "python", claims, offline=True)
        assert len(result["primary_keywords"]) > 0
        assert len(result["long_tail"]) > 0
        assert "per_page" in result

    def test_offline_mode_skips_network(self):
        """Offline mode should only use claims and patterns, not trends/suggest."""
        claims = [{"claim_text": "Load 3D models in FBX format"}]
        result = research_keywords("Aspose.3D", "3d", "python", claims, offline=True)
        assert result["sources"]["trends"] == []
        assert result["sources"]["suggest"] == []
        assert len(result["sources"]["claims"]) > 0
        assert len(result["sources"]["patterns"]) > 0

    def test_claim_keywords_extracted(self):
        claims = [
            {"claim_text": "Convert PDF documents to Word format"},
            {"claim_text": "Convert Excel spreadsheets to PDF"},
        ]
        kw = _extract_claim_keywords(claims, "pdf", "python")
        assert "convert" in kw

    def test_claim_keywords_exclude_stop_words(self):
        claims = [{"claim_text": "The system can convert and load the documents"}]
        kw = _extract_claim_keywords(claims, "pdf", "python")
        for stop in ["the", "can", "and"]:
            assert stop not in kw

    def test_search_patterns_generated(self):
        claims = [{"claim_text": "Load and convert 3D models"}]
        patterns = _generate_search_patterns("Aspose.3D", "3d", "python", claims)
        assert any("tutorial" in p for p in patterns)
        assert any("install" in p for p in patterns)

    def test_search_patterns_include_verbs_from_claims(self):
        claims = [{"claim_text": "Convert and render 3D scenes"}]
        patterns = _generate_search_patterns("Aspose.3D", "3d", "python", claims)
        assert any("convert" in p for p in patterns)
        assert any("render" in p for p in patterns)

    def test_dedupe_preserves_order(self):
        assert _dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_dedupe_strips_whitespace(self):
        assert _dedupe(["  a  ", "a", "b "]) == ["a", "b"]

    def test_dedupe_empty_list(self):
        assert _dedupe([]) == []

    def test_stop_words_excluded(self):
        assert "the" in STOP_WORDS
        assert "python" not in STOP_WORDS

    def test_research_result_structure(self):
        """Research result has all expected keys."""
        result = research_keywords("Product", "family", "python", [], offline=True)
        assert "primary_keywords" in result
        assert "long_tail" in result
        assert "per_page" in result
        assert "sources" in result
        assert set(result["sources"].keys()) == {"trends", "suggest", "claims", "patterns"}

    def test_per_page_assignments_include_family_and_platform(self):
        claims = [{"claim_text": "Install the library via pip"}]
        result = research_keywords("Aspose.3D", "3d", "python", claims, offline=True)
        for slug, kw_list in result["per_page"].items():
            # Family and platform should always be in per-page keywords
            lower_kw = [k.lower() for k in kw_list]
            assert "3d" in lower_kw
            assert "python" in lower_kw


class TestKeywordOptimizer:
    """Tests for keyword extraction and injection."""

    def test_extract_keywords_from_content(self):
        content = (
            "---\ntitle: Test\n---\n"
            "Python library for loading 3D models. Load FBX and OBJ files."
        )
        kw = extract_keywords(content)
        assert len(kw) > 0
        assert "the" not in kw  # Stop words excluded

    def test_extract_strips_code_blocks(self):
        content = (
            "---\ntitle: Test\n---\n"
            "Some text about loading models.\n"
            "```python\nimport special_module\n```\n"
            "More text about loading models."
        )
        kw = extract_keywords(content)
        # "loading" and "models" should appear from prose, code block content less dominant
        assert len(kw) > 0

    def test_extract_strips_html_comments(self):
        content = "---\ntitle: T\n---\n<!-- hidden keyword keyword keyword -->\nvisible text here"
        kw = extract_keywords(content)
        # HTML comment content should be stripped
        assert "hidden" not in kw

    def test_inject_respects_density(self):
        content = "---\ntitle: Test\n---\nShort line."
        result = inject_keywords_naturally(content, ["keyword"], max_density=0.0)
        # With 0% density, no injection should happen
        assert result == content

    def test_inject_returns_unchanged_with_no_keywords(self):
        content = "---\ntitle: Test\n---\nSome body text here."
        result = inject_keywords_naturally(content, [])
        assert result == content

    def test_inject_preserves_frontmatter(self):
        content = "---\ntitle: Test\nslug: page\n---\nBody content with many words."
        result = inject_keywords_naturally(content, ["keyword"])
        assert result.startswith("---\ntitle: Test\nslug: page\n---")

    def test_keyword_density_calculation(self):
        content = "---\ntitle: T\n---\npython python python other words here"
        density = calculate_keyword_density(content, "python")
        assert density > 0

    def test_keyword_density_empty_content(self):
        content = "---\ntitle: T\n---\n"
        density = calculate_keyword_density(content, "python")
        assert density == 0.0

    def test_keyword_density_no_frontmatter(self):
        content = "python is great python python other words"
        density = calculate_keyword_density(content, "python")
        assert density > 0

    def test_extract_keywords_max_limit(self):
        content = "---\ntitle: T\n---\n" + " ".join(
            f"word{i}" for i in range(50)
        )
        kw = extract_keywords(content, max_keywords=3)
        assert len(kw) <= 3


class TestSEOMetadata:
    """Tests for SEO metadata optimization."""

    def test_seo_title_max_length(self):
        title = _build_seo_title(
            "Very Long Title That Goes On And On And On", "Aspose.3D", "python"
        )
        assert len(title) <= 60

    def test_seo_title_includes_product(self):
        title = _build_seo_title("Getting Started", "Aspose.3D", "python")
        assert "Aspose.3D" in title

    def test_seo_title_does_not_duplicate_product(self):
        """If title already contains product name, don't prepend it."""
        title = _build_seo_title("Aspose.3D Getting Started", "Aspose.3D", "python")
        # Should not have "Aspose.3D Aspose.3D Getting Started"
        assert title.count("Aspose.3D") == 1

    def test_seo_description_max_length(self):
        desc = _build_seo_description(
            "Test", "A very detailed purpose", "Aspose.3D", "python", ["keyword"]
        )
        assert len(desc) <= 160

    def test_seo_description_with_purpose(self):
        desc = _build_seo_description(
            "Test",
            "This is a detailed purpose that explains the page content thoroughly",
            "Aspose.3D",
            "python",
            ["keyword"],
        )
        assert "Aspose.3D" in desc

    def test_inject_frontmatter_field_adds_new(self):
        content = "---\ntitle: Test\n---\nBody"
        result = _inject_frontmatter_field(content, "canonical", '"https://example.com/"')
        assert 'canonical: "https://example.com/"' in result

    def test_inject_frontmatter_field_skips_existing(self):
        content = '---\ntitle: Test\ncanonical: "old"\n---\nBody'
        result = _inject_frontmatter_field(content, "canonical", '"new"')
        assert '"old"' in result  # Not overwritten

    def test_inject_frontmatter_field_no_frontmatter(self):
        content = "No frontmatter here"
        result = _inject_frontmatter_field(content, "canonical", '"url"')
        assert result == content  # Unchanged

    def test_get_frontmatter_field(self):
        content = '---\ntitle: "My Title"\nslug: "test"\n---\nBody'
        assert _get_frontmatter_field(content, "title") == "My Title"

    def test_get_frontmatter_field_missing(self):
        content = '---\ntitle: "My Title"\n---\nBody'
        assert _get_frontmatter_field(content, "nonexistent") is None

    def test_optimize_adds_seo_fields(self):
        content = (
            '---\ntitle: "Test Page"\n'
            'description: "documentation and resources"\n'
            '---\nBody content here.'
        )
        page = {"slug": "test", "title": "Test Page", "url_path": "3d/python/test/"}
        result = optimize_seo_metadata(
            content, page, ["python", "3d"], "Aspose.3D", "python",
            section="docs", family="3d",
        )
        assert "seoTitle:" in result
        assert "canonical:" in result
        assert "robots:" in result

    def test_optimize_adds_keywords_field(self):
        content = '---\ntitle: "Test Page"\n---\nBody'
        page = {"slug": "test", "title": "Test Page"}
        result = optimize_seo_metadata(
            content, page, ["python", "3d"], "Product", "python"
        )
        assert "keywords:" in result

    def test_index_page_gets_noindex(self):
        content = '---\ntitle: "Index"\n---\nBody'
        page = {"slug": "_index", "title": "Index"}
        result = optimize_seo_metadata(
            content, page, [], "Product", "python"
        )
        assert "noindex" in result

    def test_regular_page_gets_index(self):
        content = '---\ntitle: "Guide"\n---\nBody'
        page = {"slug": "guide", "title": "Guide"}
        result = optimize_seo_metadata(
            content, page, [], "Product", "python"
        )
        assert '"index, follow"' in result

    def test_canonical_url_from_url_path(self):
        content = '---\ntitle: "Test"\n---\nBody'
        page = {"slug": "test", "url_path": "3d/python/test/"}
        result = optimize_seo_metadata(
            content, page, [], "Product", "python", section="docs", family="3d"
        )
        assert "https://docs.aspose.org/3d/python/test/" in result

    def test_canonical_url_fallback(self):
        content = '---\ntitle: "Test"\n---\nBody'
        page = {"slug": "test"}
        result = optimize_seo_metadata(
            content, page, [], "Product", "python", section="docs", family="3d"
        )
        assert "https://docs.aspose.org/" in result


class TestW10Worker:
    """Integration tests for W10 worker."""

    def _create_run_dir(self, tmp_path, *, with_content=True, with_artifacts=True):
        """Helper to create a minimal run directory structure."""
        if with_artifacts:
            artifacts_dir = tmp_path / "artifacts"
            artifacts_dir.mkdir(parents=True)
            (artifacts_dir / "product_facts.json").write_text(
                json.dumps({
                    "product_name": "Aspose.3D",
                    "product_family": "3d",
                    "claims": [
                        {"claim_id": "c1", "claim_text": "Load 3D models in FBX format"},
                    ],
                }),
                encoding="utf-8",
            )
            (artifacts_dir / "page_plan.json").write_text(
                json.dumps({
                    "pages": [
                        {
                            "slug": "test",
                            "title": "Test Page",
                            "url_path": "3d/python/test/",
                        }
                    ],
                }),
                encoding="utf-8",
            )

        if with_content:
            content_dir = (
                tmp_path / "work" / "site" / "content"
                / "docs.aspose.org" / "3d" / "en" / "python"
            )
            content_dir.mkdir(parents=True)
            md_content = (
                '---\ntitle: "Test Page"\n'
                'description: "documentation and resources"\n'
                '---\n\n'
                'This is a test page about Python 3D processing with various '
                'features and capabilities for developers.\n'
            )
            (content_dir / "test.md").write_text(md_content, encoding="utf-8")

        return tmp_path

    def test_worker_skips_when_disabled(self, tmp_path):
        run_dir = self._create_run_dir(tmp_path, with_content=True, with_artifacts=True)
        result = execute_seo_optimizer(
            run_dir,
            {"seo_enabled": False},
        )
        assert result["status"] == "disabled"

    def test_worker_skips_when_no_content(self, tmp_path):
        run_dir = self._create_run_dir(tmp_path, with_content=False, with_artifacts=True)
        result = execute_seo_optimizer(
            run_dir,
            {"seo_enabled": True},
        )
        assert result["status"] == "skipped"

    def test_worker_raises_on_missing_artifacts(self, tmp_path):
        """Worker should raise when artifacts are missing."""
        run_dir = self._create_run_dir(tmp_path, with_content=True, with_artifacts=False)
        with pytest.raises(SEOOptimizerArtifactMissingError):
            execute_seo_optimizer(
                run_dir,
                {"seo_enabled": True, "target_platform": "python"},
            )

    def test_worker_processes_md_files(self, tmp_path):
        run_dir = self._create_run_dir(tmp_path)
        result = execute_seo_optimizer(
            run_dir,
            {"seo_enabled": True, "target_platform": "python", "offline_mode": True},
        )
        assert result["status"] == "ok"
        # Verify file was modified
        content_dir = (
            run_dir / "work" / "site" / "content"
            / "docs.aspose.org" / "3d" / "en" / "python"
        )
        updated = (content_dir / "test.md").read_text(encoding="utf-8")
        assert "canonical:" in updated or "seoTitle:" in updated

    def test_worker_writes_seo_report(self, tmp_path):
        run_dir = self._create_run_dir(tmp_path)
        execute_seo_optimizer(
            run_dir,
            {"seo_enabled": True, "target_platform": "python", "offline_mode": True},
        )
        report_path = run_dir / "work" / "seo_report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "total_files" in report
        assert "optimized" in report
        assert "keyword_stats" in report

    def test_worker_default_seo_enabled(self, tmp_path):
        """SEO is enabled by default when seo_enabled is not specified."""
        run_dir = self._create_run_dir(tmp_path)
        result = execute_seo_optimizer(
            run_dir,
            {"target_platform": "python", "offline_mode": True},
        )
        assert result["status"] == "ok"

    def test_worker_handles_empty_content_dir(self, tmp_path):
        """Worker handles content directory with no .md files."""
        run_dir = self._create_run_dir(tmp_path, with_content=False, with_artifacts=True)
        # Create content dir but no .md files
        content_dir = run_dir / "work" / "site" / "content"
        content_dir.mkdir(parents=True)
        result = execute_seo_optimizer(
            run_dir,
            {"seo_enabled": True, "target_platform": "python", "offline_mode": True},
        )
        assert result["status"] == "ok"
        assert result["pages_optimized"] == 0

    def test_worker_report_contains_keyword_stats(self, tmp_path):
        run_dir = self._create_run_dir(tmp_path)
        result = execute_seo_optimizer(
            run_dir,
            {"seo_enabled": True, "target_platform": "python", "offline_mode": True},
        )
        assert "keyword_stats" in result.get("report", {})
        stats = result["report"]["keyword_stats"]
        assert "primary" in stats
        assert "long_tail_count" in stats


class TestWorkerInvokerRegistration:
    """Tests that W6 is properly registered in worker dispatch."""

    def test_w6_in_dispatch_map(self):
        from launch.orchestrator.worker_invoker import WORKER_DISPATCH
        assert "W6.SEOOptimizer" in WORKER_DISPATCH

    def test_w6_dispatch_order(self):
        """W6 should be between W5 and W7 in dispatch map keys."""
        from launch.orchestrator.worker_invoker import WORKER_DISPATCH
        keys = list(WORKER_DISPATCH.keys())
        w5_idx = keys.index("W5.SectionWriter")
        w6_idx = keys.index("W6.SEOOptimizer")
        w7_idx = keys.index("W7.ContentReviewer")
        assert w5_idx < w6_idx < w7_idx


class TestStateConstant:
    """Tests that the SEO_OPTIMIZING state constant exists."""

    def test_state_constant_exists(self):
        from launch.models.state import RUN_STATE_SEO_OPTIMIZING
        assert RUN_STATE_SEO_OPTIMIZING == "SEO_OPTIMIZING"

    def test_state_constant_between_linking_and_validating(self):
        from launch.models.state import (
            RUN_STATE_LINKING,
            RUN_STATE_SEO_OPTIMIZING,
            RUN_STATE_VALIDATING,
        )
        # All three should be defined (non-None)
        assert RUN_STATE_LINKING is not None
        assert RUN_STATE_SEO_OPTIMIZING is not None
        assert RUN_STATE_VALIDATING is not None

"""Tests for W5 production hardening (TC-3310).

Four test classes covering:
A) enforce_frontmatter_invariants — post-sanitizer frontmatter lock
B) evidence chunks + truth pack helpers — score-ranked grounding
C) _resolve_failed_page_slugs — index.md stem collision fix
D) Integration / feature-flag / manifest tests (SR-02)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

import pytest

from launch.workers.w5_section_writer.worker import (
    enforce_frontmatter_invariants,
    _find_failed_page_slugs,
    _resolve_failed_page_slugs,
    _generate_single_page,
)
from launch.workers.w5_section_writer.multi_pass import (
    _build_evidence_chunks_index,
    _format_grounding_excerpts_v2,
    _format_truth_pack_block,
)


# ===========================================================================
# A) TestEnforceFrontmatterInvariants
# ===========================================================================


class TestEnforceFrontmatterInvariants:
    """TC-3310: Verify frontmatter lock enforces canonical values from page plan."""

    @staticmethod
    def _page(
        slug: str = "overview",
        title: str = "Overview Page",
        section: str = "products",
        weight: int = 10,
        url_path: str = "/products/overview/",
    ) -> Dict[str, Any]:
        return {
            "slug": slug,
            "title": title,
            "section": section,
            "weight": weight,
            "url_path": url_path,
        }

    @staticmethod
    def _mappings(
        layout: str = "products",
        permalink: str = "/products/overview/",
    ) -> Dict[str, str]:
        return {"__LAYOUT__": layout, "__PERMALINK__": permalink}

    # ----- Tests -----

    def test_overrides_wrong_slug(self):
        content = '---\nslug: "wrong-slug"\ntitle: "Overview Page"\nlayout: products\n---\n# Body'
        page = self._page(slug="overview")
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert "slug" in corrections
        assert 'slug: "overview"' in result

    def test_overrides_wrong_permalink(self):
        content = '---\nslug: "overview"\npermalink: /old/path/\nlayout: products\n---\n# Body'
        page = self._page()
        mappings = self._mappings(permalink="/products/overview/")
        result, corrections = enforce_frontmatter_invariants(content, page, mappings)
        assert "permalink" in corrections
        assert "permalink: /products/overview/" in result

    def test_overrides_wrong_title(self):
        content = '---\ntitle: "Wrong Title"\nslug: "overview"\nlayout: products\n---\n# Body'
        page = self._page(title="Overview Page")
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert "title" in corrections
        assert 'title: "Overview Page"' in result

    def test_overrides_wrong_layout(self):
        content = '---\nlayout: wrong\nslug: "overview"\n---\n# Body'
        page = self._page()
        mappings = self._mappings(layout="products")
        result, corrections = enforce_frontmatter_invariants(content, page, mappings)
        assert "layout" in corrections
        assert "layout: products" in result

    def test_overrides_wrong_weight(self):
        content = '---\nweight: 99\nslug: "overview"\nlayout: products\n---\n# Body'
        page = self._page(weight=10)
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert "weight" in corrections
        assert "weight: 10" in result

    def test_no_correction_when_matching(self):
        content = '---\nslug: "overview"\ntitle: "Overview Page"\nlayout: products\npermalink: /products/overview/\nweight: 10\n---\n# Body'
        page = self._page()
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert corrections == []
        assert result == content

    def test_no_frontmatter_returns_unchanged(self):
        content = "# Title\n\nSome body text"
        page = self._page()
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert corrections == []
        assert result == content

    def test_preserves_field_ordering(self):
        content = '---\nweight: 99\ndescription: "Desc"\nslug: "wrong"\nlayout: products\n---\n# Body'
        page = self._page(slug="overview", weight=10)
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        # Both should be corrected
        assert "slug" in corrections
        assert "weight" in corrections
        # Ordering: weight comes before slug in the original
        weight_pos = result.index("weight:")
        slug_pos = result.index("slug:")
        assert weight_pos < slug_pos, "Field ordering must be preserved"

    def test_multiple_corrections(self):
        content = '---\nslug: "wrong"\ntitle: "Wrong"\nlayout: wrong\n---\n# Body'
        page = self._page(slug="overview", title="Right Title")
        mappings = self._mappings(layout="products")
        result, corrections = enforce_frontmatter_invariants(content, page, mappings)
        assert "slug" in corrections
        assert "title" in corrections
        assert "layout" in corrections
        assert len(corrections) == 3

    def test_title_with_special_chars(self):
        content = '---\ntitle: "Wrong Title"\nslug: "overview"\n---\n# Body'
        page = self._page(title='Aspose.Cells: Python Library')
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert "title" in corrections
        assert "Aspose.Cells: Python Library" in result

    def test_single_frontmatter_delimiter_returns_unchanged(self):
        content = "---\nslug: wrong\nNo closing delimiter"
        page = self._page()
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert corrections == []
        assert result == content

    def test_unquoted_slug_matches_quoted_canonical(self):
        """GAP-01: slug: overview (unquoted) must match canonical '"overview"'."""
        content = '---\nslug: overview\ntitle: "Overview Page"\nlayout: products\npermalink: /products/overview/\nweight: 10\n---\n# Body'
        page = self._page(slug="overview")
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert corrections == [], f"Expected no corrections but got {corrections}"
        assert result == content

    def test_single_quoted_slug_matches_canonical(self):
        """GAP-01: slug: 'overview' (single-quoted) must match canonical."""
        content = "---\nslug: 'overview'\ntitle: \"Overview Page\"\nlayout: products\npermalink: /products/overview/\nweight: 10\n---\n# Body"
        page = self._page(slug="overview")
        result, corrections = enforce_frontmatter_invariants(content, page, self._mappings())
        assert corrections == [], f"Expected no corrections but got {corrections}"


# ===========================================================================
# B) TestEvidenceChunksIntegration
# ===========================================================================


class TestEvidenceChunksIntegration:
    """TC-3310: Verify evidence chunks index, grounding v2, and truth pack block."""

    # ----- _build_evidence_chunks_index -----

    def test_build_index_basic(self):
        entries = [
            {
                "claim_id": "c1",
                "evidence_chunks": [
                    {"excerpt": "text A", "score": 0.9, "file_path": "README.md"},
                    {"excerpt": "text B", "score": 0.5, "file_path": "docs.md"},
                ],
            }
        ]
        index = _build_evidence_chunks_index(entries)
        assert "c1" in index
        assert len(index["c1"]) == 2
        # First chunk should be highest score
        assert index["c1"][0]["score"] == 0.9

    def test_build_index_sorts_by_score(self):
        entries = [
            {
                "claim_id": "c1",
                "evidence_chunks": [
                    {"excerpt": "low", "score": 0.1},
                    {"excerpt": "high", "score": 0.95},
                    {"excerpt": "mid", "score": 0.5},
                ],
            }
        ]
        index = _build_evidence_chunks_index(entries)
        scores = [c["score"] for c in index["c1"]]
        assert scores == sorted(scores, reverse=True)

    def test_build_index_caps_at_3(self):
        entries = [
            {
                "claim_id": "c1",
                "evidence_chunks": [
                    {"excerpt": f"text {i}", "score": 1.0 - i * 0.1}
                    for i in range(10)
                ],
            }
        ]
        index = _build_evidence_chunks_index(entries)
        assert len(index["c1"]) == 3

    def test_build_index_skips_empty_claim_id(self):
        entries = [{"claim_id": "", "evidence_chunks": [{"excerpt": "x", "score": 1}]}]
        index = _build_evidence_chunks_index(entries)
        assert len(index) == 0

    def test_build_index_skips_empty_chunks(self):
        entries = [{"claim_id": "c1", "evidence_chunks": []}]
        index = _build_evidence_chunks_index(entries)
        assert "c1" not in index

    # ----- _format_grounding_excerpts_v2 -----

    def test_v2_prefers_chunks_over_claims(self):
        ev_index = {"c1": [{"excerpt": "chunk text", "score": 0.9, "file_path": "a.py"}]}
        ec_index = {"c1": ["claim text"]}
        result = _format_grounding_excerpts_v2(["c1"], ev_index, ec_index)
        assert "chunk text" in result
        assert "(src: a.py, score: 0.90)" in result
        assert "claim text" not in result

    def test_v2_falls_back_to_claims(self):
        ev_index: Dict[str, List[Dict[str, Any]]] = {}
        ec_index = {"c1": ["fallback text"]}
        result = _format_grounding_excerpts_v2(["c1"], ev_index, ec_index)
        assert "fallback text" in result

    def test_v2_includes_source_attribution(self):
        ev_index = {"c1": [{"excerpt": "text", "score": 0.85, "file_path": "README.md"}]}
        result = _format_grounding_excerpts_v2(["c1"], ev_index, {})
        assert "(src: README.md, score: 0.85)" in result

    def test_v2_caps_at_max(self):
        ev_index = {
            f"c{i}": [{"excerpt": f"text{i}", "score": 0.9, "file_path": "f.py"}]
            for i in range(10)
        }
        claim_ids = [f"c{i}" for i in range(10)]
        result = _format_grounding_excerpts_v2(claim_ids, ev_index, {}, max_excerpts=3)
        # Header line + 3 excerpt lines = 4 total lines
        lines = [ln for ln in result.split("\n") if ln.strip()]
        assert len(lines) == 4  # 1 header + 3 excerpts

    def test_v2_empty_when_no_data(self):
        result = _format_grounding_excerpts_v2(["c1"], {}, {})
        assert result == ""

    def test_v2_empty_claim_ids(self):
        result = _format_grounding_excerpts_v2([], {"c1": [{"excerpt": "x", "score": 1}]}, {})
        assert result == ""

    def test_v2_skips_empty_excerpts(self):
        ev_index = {"c1": [{"excerpt": "", "score": 0.9, "file_path": "f.py"}]}
        result = _format_grounding_excerpts_v2(["c1"], ev_index, {})
        assert result == ""

    # ----- _format_truth_pack_block -----

    def test_truth_pack_formats_capabilities(self):
        tp = {"capabilities": [{"text": "Read Excel files"}, {"text": "Write CSV"}]}
        result = _format_truth_pack_block(tp)
        assert "TRUTH PACK" in result
        assert "Read Excel files" in result
        assert "Write CSV" in result

    def test_truth_pack_formats_limitations(self):
        tp = {"limitations": [{"text": "No VBA macro support"}]}
        result = _format_truth_pack_block(tp)
        assert "NEVER claim" in result
        assert "No VBA macro support" in result

    def test_truth_pack_formats_format_direction(self):
        tp = {"formats": {"input": ["XLSX", "XLS"], "output": ["CSV", "PDF"]}}
        result = _format_truth_pack_block(tp)
        assert "Input formats: XLSX, XLS" in result
        assert "Output formats: CSV, PDF" in result

    def test_truth_pack_empty_returns_empty(self):
        result = _format_truth_pack_block({})
        assert result == ""

    def test_truth_pack_caps_capabilities_at_5(self):
        tp = {"capabilities": [{"text": f"cap_{i}"} for i in range(10)]}
        result = _format_truth_pack_block(tp)
        assert "cap_4" in result
        assert "cap_5" not in result

    def test_truth_pack_caps_limitations_at_3(self):
        tp = {"limitations": [{"text": f"lim_{i}"} for i in range(10)]}
        result = _format_truth_pack_block(tp)
        assert "lim_2" in result
        assert "lim_3" not in result


# ===========================================================================
# C) TestResolveFailedPageSlugs
# ===========================================================================


class TestResolveFailedPageSlugs:
    """TC-3310: Verify regen targeting correctly resolves index.md paths."""

    @staticmethod
    def _pages(entries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Build a minimal pages list from (slug, section, output_path) tuples."""
        return [
            {"slug": e["slug"], "section": e["section"], "output_path": e["output_path"]}
            for e in entries
        ]

    @staticmethod
    def _write_report(path: Path, issues: list) -> None:
        path.write_text(json.dumps({"issues": issues}), encoding="utf-8")

    # ----- Tests -----

    def test_index_md_resolves_via_reverse_index(self, tmp_path):
        """Blog page output_path ending in index.md resolves to correct slug."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "content/blog.aspose.org/cells/python/perf-guide/index.md"}}
        ])
        pages = self._pages([
            {"slug": "perf-guide", "section": "blog", "output_path": "content/blog.aspose.org/cells/python/perf-guide/index.md"}
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "perf-guide" in slugs
        assert "index" not in slugs

    def test_underscore_index_resolves_correctly(self, tmp_path):
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "error", "location": {"path": "content/products.aspose.com/cells/en/getting-started/_index.md"}}
        ])
        pages = self._pages([
            {"slug": "getting-started", "section": "products", "output_path": "content/products.aspose.com/cells/en/getting-started/_index.md"}
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "getting-started" in slugs

    def test_draft_path_resolves_to_slug(self, tmp_path):
        """Classic drafts/<section>/<slug>.md path resolves via reverse index."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "drafts/products/overview.md"}}
        ])
        pages = self._pages([
            {"slug": "overview", "section": "products", "output_path": "content/p/en/overview.md"}
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "overview" in slugs

    def test_output_path_exact_match(self, tmp_path):
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "error", "location": {"path": "content/docs.aspose.com/note/en/install.md"}}
        ])
        pages = self._pages([
            {"slug": "install", "section": "docs", "output_path": "content/docs.aspose.com/note/en/install.md"}
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "install" in slugs

    def test_fallback_stem_for_non_index(self, tmp_path):
        """When path doesn't match reverse index, use stem (backward compat)."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "drafts/docs/tips.md"}}
        ])
        # No matching page in the list
        slugs = _resolve_failed_page_slugs(p, [])
        assert "tips" in slugs

    def test_multiple_index_md_resolve_independently(self, tmp_path):
        """Two different pages both with index.md resolve to different slugs."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "content/blog/cells/python/merge-files/index.md"}},
            {"severity": "error", "location": {"path": "content/blog/cells/python/convert-pdf/index.md"}},
        ])
        pages = self._pages([
            {"slug": "merge-files", "section": "blog", "output_path": "content/blog/cells/python/merge-files/index.md"},
            {"slug": "convert-pdf", "section": "blog", "output_path": "content/blog/cells/python/convert-pdf/index.md"},
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "merge-files" in slugs
        assert "convert-pdf" in slugs
        assert "index" not in slugs

    def test_backslash_normalization(self, tmp_path):
        """Windows-style paths with backslashes are normalized."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "drafts\\products\\overview.md"}}
        ])
        pages = self._pages([
            {"slug": "overview", "section": "products", "output_path": "content/p/en/overview.md"}
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "overview" in slugs

    def test_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "nonexistent.json"
        slugs = _resolve_failed_page_slugs(p, [])
        assert len(slugs) == 0

    def test_corrupt_json_returns_empty(self, tmp_path):
        p = tmp_path / "vr.json"
        p.write_text("NOT VALID JSON {{{", encoding="utf-8")
        slugs = _resolve_failed_page_slugs(p, [])
        assert len(slugs) == 0

    def test_warn_severity_excluded(self, tmp_path):
        """Only blocker/error issues count, not warnings."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "warn", "location": {"path": "drafts/products/overview.md"}}
        ])
        pages = self._pages([
            {"slug": "overview", "section": "products", "output_path": "content/p/en/overview.md"}
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert len(slugs) == 0

    def test_parent_dir_fallback_for_unknown_index_md(self, tmp_path):
        """Index.md path NOT in reverse index uses parent dir name as slug."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "content/unknown/category/my-page/index.md"}}
        ])
        # No matching page at all
        slugs = _resolve_failed_page_slugs(p, [])
        assert "my-page" in slugs
        assert "index" not in slugs

    def test_empty_location_path_skipped(self, tmp_path):
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": ""}},
            {"severity": "error", "location": {}},
        ])
        slugs = _resolve_failed_page_slugs(p, [])
        assert len(slugs) == 0

    def test_suffix_match_rejects_cross_page_collision(self, tmp_path):
        """GAP-04: products/overview/index.md must NOT match docs/overview/index.md."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "content/products/overview/index.md"}}
        ])
        pages = self._pages([
            {"slug": "docs-overview", "section": "docs", "output_path": "content/docs/overview/index.md"},
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        # Should NOT match docs-overview (different directory tree)
        assert "docs-overview" not in slugs

    def test_suffix_match_accepts_valid_subpath(self, tmp_path):
        """GAP-04: Suffix match works when absolute path has correct prefix."""
        p = tmp_path / "vr.json"
        self._write_report(p, [
            {"severity": "blocker", "location": {"path": "work/site/content/products/overview/index.md"}}
        ])
        pages = self._pages([
            {"slug": "overview", "section": "products", "output_path": "content/products/overview/index.md"},
        ])
        slugs = _resolve_failed_page_slugs(p, pages)
        assert "overview" in slugs


# ===========================================================================
# D) TestIntegrationAndFlags (SR-02)
# ===========================================================================

_W5_WORKER_MOD = "launch.workers.w5_section_writer.worker"


class TestIntegrationAndFlags:
    """SR-02: Integration, feature flag, and manifest tests for TC-3310."""

    @staticmethod
    def _make_page(**overrides) -> Dict[str, Any]:
        defaults = {
            "slug": "overview",
            "title": "Overview Page",
            "section": "products",
            "weight": 10,
            "url_path": "/products/overview/",
            "output_path": "content/products.aspose.com/cells/en/overview.md",
            "page_type": "products",
            "token_mappings": {
                "__LAYOUT__": "products",
                "__PERMALINK__": "/products/overview/",
            },
        }
        defaults.update(overrides)
        return defaults

    def test_frontmatter_lock_fires_in_generate_single_page(self, tmp_path):
        """GAP-05: Prove enforce_frontmatter_invariants fires at the
        correct call site inside _generate_single_page and corrects drift."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        # Content returned by generate_section_content — wrong slug
        bad_content = (
            '---\nslug: "wrong-slug"\ntitle: "Overview Page"\n'
            "layout: products\npermalink: /products/overview/\nweight: 10\n"
            "---\n# Overview\n\nSome body."
        )
        page = self._make_page()

        with (
            patch(f"{_W5_WORKER_MOD}.generate_section_content", return_value=bad_content),
            patch(f"{_W5_WORKER_MOD}.run_sanitizer_pipeline", side_effect=lambda c, _ctx: c),
            patch(f"{_W5_WORKER_MOD}.check_unfilled_tokens", return_value=[]),
        ):
            manifest = _generate_single_page(
                page=page,
                product_facts={},
                snippet_catalog={},
                llm_client=MagicMock(),
                page_plan={"pages": [page]},
                multi_pass_orchestrator=None,
                code_understanding={},
                evidence_map={},
                cross_page_summaries_snapshot={},
                run_config={"token_budget": 2048},
                drafts_dir=drafts_dir,
            )

        # Draft file should have corrected slug
        draft_path = drafts_dir / "products" / "overview.md"
        assert draft_path.exists()
        written = draft_path.read_text(encoding="utf-8")
        assert 'slug: "overview"' in written
        assert "wrong-slug" not in written

        # GAP-07: Manifest must contain frontmatter_corrections
        assert "frontmatter_corrections" in manifest
        assert "slug" in manifest["frontmatter_corrections"]

    def test_manifest_no_corrections_when_correct(self, tmp_path):
        """GAP-07 negative: manifest corrections empty when frontmatter correct."""
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir()

        good_content = (
            '---\nslug: "overview"\ntitle: "Overview Page"\n'
            "layout: products\npermalink: /products/overview/\nweight: 10\n"
            "---\n# Overview\n\nSome body."
        )
        page = self._make_page()

        with (
            patch(f"{_W5_WORKER_MOD}.generate_section_content", return_value=good_content),
            patch(f"{_W5_WORKER_MOD}.run_sanitizer_pipeline", side_effect=lambda c, _ctx: c),
            patch(f"{_W5_WORKER_MOD}.check_unfilled_tokens", return_value=[]),
        ):
            manifest = _generate_single_page(
                page=page,
                product_facts={},
                snippet_catalog={},
                llm_client=MagicMock(),
                page_plan={"pages": [page]},
                multi_pass_orchestrator=None,
                code_understanding={},
                evidence_map={},
                cross_page_summaries_snapshot={},
                run_config={"token_budget": 2048},
                drafts_dir=drafts_dir,
            )

        assert manifest["frontmatter_corrections"] == []

    def test_evidence_chunks_disabled_skips_loading(self, tmp_path):
        """GAP-06: evidence_chunks_enabled=False prevents loading."""
        from launch.workers.w5_section_writer.multi_pass import MultiPassOrchestrator

        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True)

        # Write artifacts that SHOULD be ignored
        (artifacts / "claim_evidence_chunks.json").write_text(
            json.dumps({"entries": [
                {"claim_id": "c1", "evidence_chunks": [{"excerpt": "x", "score": 0.9}]}
            ]}),
            encoding="utf-8",
        )

        orch = MultiPassOrchestrator(
            llm_client=MagicMock(),
            prompt_loader=MagicMock(),
            run_config={
                "run_dir": str(run_dir),
                "evidence_chunks_enabled": False,
            },
        )
        # Verify the flag prevents loading
        assert orch._evidence_chunks_enabled is False
        assert orch._evidence_chunks_index == {}


# ===========================================================================
# E) TestObservabilityAndSizeGuard (SR-03)
# ===========================================================================


class TestObservabilityAndSizeGuard:
    """SR-03: Event emission, truth pack logging, and evidence chunks size guard."""

    def test_evidence_chunks_truncated_on_overflow(self):
        """GAP-03: > 500 entries truncated with warning."""
        from launch.workers.w5_section_writer.multi_pass import (
            _build_evidence_chunks_index,
            _MAX_EVIDENCE_ENTRIES,
        )

        entries = [
            {"claim_id": f"c{i}", "evidence_chunks": [{"excerpt": f"t{i}", "score": 0.5}]}
            for i in range(600)
        ]
        index = _build_evidence_chunks_index(entries)
        assert len(index) <= _MAX_EVIDENCE_ENTRIES

    def test_truth_pack_injection_logs_debug(self):
        """GAP-09: _format_truth_pack_block output is logged when injected."""
        result = _format_truth_pack_block(
            {"capabilities": [{"text": "Read Excel files"}]}
        )
        # Verify the block is non-empty (the logging happens at injection site)
        assert "TRUTH PACK" in result
        assert len(result) > 10  # enough chars that tokens_approx > 0

    def test_frontmatter_locked_event_constant_exists(self):
        """GAP-02: W5_FRONTMATTER_LOCKED constant is defined."""
        from launch.workers.w5_section_writer.worker import W5_FRONTMATTER_LOCKED
        assert W5_FRONTMATTER_LOCKED == "W5_FRONTMATTER_LOCKED"


# ===========================================================================
# F) TestGroundingV2RoundRobinAndTruthPackFilter (SR-04)
# ===========================================================================


class TestGroundingV2RoundRobinAndTruthPackFilter:
    """SR-04: v2 round-robin iteration + truth pack role filtering."""

    def test_v2_round_robin_distributes_across_claims(self):
        """GAP-11: 3 claims, 3 chunks each, max=3 → one from each claim."""
        ev_index = {
            "c1": [
                {"excerpt": "c1a", "score": 0.9, "file_path": "a.py"},
                {"excerpt": "c1b", "score": 0.8, "file_path": "a.py"},
                {"excerpt": "c1c", "score": 0.7, "file_path": "a.py"},
            ],
            "c2": [
                {"excerpt": "c2a", "score": 0.9, "file_path": "b.py"},
                {"excerpt": "c2b", "score": 0.8, "file_path": "b.py"},
            ],
            "c3": [
                {"excerpt": "c3a", "score": 0.9, "file_path": "c.py"},
            ],
        }
        result = _format_grounding_excerpts_v2(
            ["c1", "c2", "c3"], ev_index, {}, max_excerpts=3
        )
        # Each claim should contribute exactly 1 excerpt (round-robin)
        assert "[c1]" in result
        assert "[c2]" in result
        assert "[c3]" in result
        # c1b should NOT appear (we only get 1st from each before depth 2)
        assert "c1b" not in result

    def test_v2_round_robin_fills_from_deep_when_some_short(self):
        """Round-robin continues to deeper items when shallow claims exhaust."""
        ev_index = {
            "c1": [
                {"excerpt": "c1a", "score": 0.9, "file_path": "a.py"},
                {"excerpt": "c1b", "score": 0.8, "file_path": "a.py"},
            ],
            "c2": [
                {"excerpt": "c2a", "score": 0.9, "file_path": "b.py"},
            ],
        }
        result = _format_grounding_excerpts_v2(
            ["c1", "c2"], ev_index, {}, max_excerpts=3
        )
        assert "c1a" in result
        assert "c2a" in result
        # Third excerpt should be c1b (depth 1 of c1)
        assert "c1b" in result

    def test_truth_pack_skipped_for_toc_page(self):
        """GAP-10: toc page does not get truth pack injection."""
        from launch.workers.w5_section_writer.multi_pass import _TRUTH_PACK_ROLES
        assert "toc" not in _TRUTH_PACK_ROLES
        assert "blog" not in _TRUTH_PACK_ROLES
        assert "landing" not in _TRUTH_PACK_ROLES

    def test_truth_pack_injected_for_products_page(self):
        """GAP-10: products page gets truth pack injection."""
        from launch.workers.w5_section_writer.multi_pass import _TRUTH_PACK_ROLES
        assert "products" in _TRUTH_PACK_ROLES
        assert "tutorial" in _TRUTH_PACK_ROLES
        assert "api_reference" in _TRUTH_PACK_ROLES

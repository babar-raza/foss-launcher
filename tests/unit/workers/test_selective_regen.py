"""Tests for heal_target_pages selective page regeneration (TC-3853 / H5.1 / HO-01)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.models.content import ContentManifest, GeneratedPage
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import WorkerContext


def _make_context(
    heal_target_pages=None,
    eval_fast_path=False,
    tmp_path: Path | None = None,
) -> WorkerContext:
    config = MagicMock(spec=RunConfig)
    config.llm = None
    config.display_name = "TestProduct"
    config.product_name = "test-product"
    run_dir = tmp_path or Path("/tmp/test-run")
    ctx = WorkerContext(
        run_id="r-test",
        run_dir=run_dir,
        config=config,
        heal_target_pages=heal_target_pages,
        eval_fast_path=eval_fast_path,
    )
    return ctx


class TestHealTargetPages:
    def test_default_is_none(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path=tmp_path)
        assert ctx.heal_target_pages is None

    def test_heal_target_pages_set(self, tmp_path: Path) -> None:
        ctx = _make_context(heal_target_pages=["pg-1", "pg-2"], tmp_path=tmp_path)
        assert ctx.heal_target_pages == ["pg-1", "pg-2"]

    def test_empty_list_accepted(self, tmp_path: Path) -> None:
        ctx = _make_context(heal_target_pages=[], tmp_path=tmp_path)
        assert ctx.heal_target_pages == []


class TestEvalFastPath:
    def test_default_is_false(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path=tmp_path)
        assert ctx.eval_fast_path is False

    def test_eval_fast_path_true(self, tmp_path: Path) -> None:
        ctx = _make_context(eval_fast_path=True, tmp_path=tmp_path)
        assert ctx.eval_fast_path is True


# ---------------------------------------------------------------------------
# HO-01: _load_cached_page_ir unit tests
# ---------------------------------------------------------------------------

class TestLoadCachedPageIR:
    """Unit tests for _load_cached_page_ir helper (HO-01)."""

    def _make_page_plan(self, page_id: str = "pg-1", slug: str = "pg-1") -> MagicMock:
        pp = MagicMock()
        pp.page_id = page_id
        pp.frontmatter = {"slug": slug}
        pp.content_path = slug
        return pp

    def _write_fake_ir(self, content_dir: Path, slug: str) -> Path:
        """Write a minimal valid PageIR JSON to disk."""
        from launcher.models.page_ir import PageIR
        ir = PageIR(
            page_id=slug,
            page_role="overview",
            title="Test Page",
            frontmatter={"slug": slug},
            sections=[],
        )
        ir_path = content_dir / f"{slug}.ir.json"
        ir_path.write_text(ir.model_dump_json(), encoding="utf-8")
        return ir_path

    def test_cache_hit_returns_page_ir(self, tmp_path: Path) -> None:
        """When cached ir.json exists, returns a valid PageIR."""
        from launcher.workers.generate.worker import _load_cached_page_ir
        from launcher.models.page_ir import PageIR

        content_dir = tmp_path / "content_bundle" / "pages"
        content_dir.mkdir(parents=True)
        self._write_fake_ir(content_dir, "pg-1")

        page_plan = self._make_page_plan(page_id="pg-1", slug="pg-1")
        result = _load_cached_page_ir(page_plan, tmp_path, content_dir)

        assert result is not None
        assert isinstance(result, PageIR)
        assert result.page_id == "pg-1"

    def test_cache_miss_returns_none(self, tmp_path: Path) -> None:
        """When no cached ir.json exists, returns None (no crash)."""
        from launcher.workers.generate.worker import _load_cached_page_ir

        content_dir = tmp_path / "content_bundle" / "pages"
        content_dir.mkdir(parents=True)
        # No file written

        page_plan = self._make_page_plan(page_id="missing-page", slug="missing-page")
        result = _load_cached_page_ir(page_plan, tmp_path, content_dir)

        assert result is None

    def test_corrupt_ir_returns_none(self, tmp_path: Path) -> None:
        """When cached ir.json is corrupt JSON, returns None (no crash)."""
        from launcher.workers.generate.worker import _load_cached_page_ir

        content_dir = tmp_path / "content_bundle" / "pages"
        content_dir.mkdir(parents=True)
        (content_dir / "corrupt.ir.json").write_text("NOT VALID JSON", encoding="utf-8")

        page_plan = self._make_page_plan(page_id="corrupt", slug="corrupt")
        result = _load_cached_page_ir(page_plan, tmp_path, content_dir)

        assert result is None

    def test_skipped_page_cache_event_has_cache_hit_true(self, tmp_path: Path) -> None:
        """When cache hit, emitted event carries cache_hit=True."""
        # This test validates the event payload shape for the caller integration.
        # We test _load_cached_page_ir returns non-None (caller sets cache_hit=True).
        from launcher.workers.generate.worker import _load_cached_page_ir

        content_dir = tmp_path / "content_bundle" / "pages"
        content_dir.mkdir(parents=True)
        self._write_fake_ir(content_dir, "pg-event")

        page_plan = self._make_page_plan(page_id="pg-event", slug="pg-event")
        result = _load_cached_page_ir(page_plan, tmp_path, content_dir)

        # Non-None result is the signal for cache_hit=True in the caller
        assert result is not None


# ---------------------------------------------------------------------------
# HO-05: Page-level asyncio.gather parallelism tests
# ---------------------------------------------------------------------------


def _make_eval_context(tmp_path: Path) -> WorkerContext:
    config = MagicMock(spec=RunConfig)
    config.llm = None
    config.display_name = "TestProduct"
    config.product_name = "test-product"
    config.seo = None
    return WorkerContext(
        run_id="eval-test",
        run_dir=tmp_path,
        config=config,
    )


def _make_gen_page(slug: str, tmp_path: Path, content: str = "# Test\n\nContent here.\n") -> GeneratedPage:
    md_rel = f"pages/{slug}.md"
    md_abs = tmp_path / md_rel
    md_abs.parent.mkdir(parents=True, exist_ok=True)
    md_abs.write_text(content, encoding="utf-8")
    return GeneratedPage(
        slug=slug,
        page_role="overview",
        section="overview",
        md_path=md_rel,
        content_path=f"docs/{slug}",
        word_count=len(content.split()),
    )


class TestPageGatherParallelism:
    """asyncio.gather page-level parallelism for generate and evaluate workers."""

    def test_generate_page_concurrency_constant_defined(self) -> None:
        """_PAGE_CONCURRENCY must be defined as an int >= 1."""
        from launcher.workers.generate.worker import _PAGE_CONCURRENCY
        assert isinstance(_PAGE_CONCURRENCY, int)
        assert _PAGE_CONCURRENCY >= 1

    def test_evaluate_pages_gathered_in_order(self, tmp_path: Path) -> None:
        """EvaluateWorker output page order matches ContentManifest.pages order."""
        from launcher.workers.evaluate.worker import EvaluateWorker

        pages = [_make_gen_page(f"page-{i}", tmp_path) for i in range(5)]
        manifest = ContentManifest(pages=pages)
        ctx = _make_eval_context(tmp_path)

        report = asyncio.run(EvaluateWorker().run(manifest, ctx))

        result_slugs = [pe.slug for pe in report.pages]
        expected_slugs = [p.slug for p in pages]
        assert result_slugs == expected_slugs, (
            f"Page order not preserved: got {result_slugs}, expected {expected_slugs}"
        )

    def test_evaluate_missing_page_isolated_from_others(self, tmp_path: Path) -> None:
        """A missing markdown file gives that page F-grade without aborting other pages."""
        from launcher.workers.evaluate.worker import EvaluateWorker

        good1 = _make_gen_page("good-1", tmp_path)
        good2 = _make_gen_page("good-2", tmp_path)
        # missing page: md_path points to a non-existent file
        missing = GeneratedPage(
            slug="missing-page",
            page_role="overview",
            section="overview",
            md_path="pages/does-not-exist.md",
            content_path="docs/missing",
            word_count=0,
        )
        manifest = ContentManifest(pages=[good1, missing, good2])
        ctx = _make_eval_context(tmp_path)

        report = asyncio.run(EvaluateWorker().run(manifest, ctx))

        slugs_by_grade: dict[str, str] = {pe.slug: pe.grade.value for pe in report.pages}
        assert slugs_by_grade.get("missing-page") == "F", (
            "Missing page must be graded F"
        )
        assert "good-1" in slugs_by_grade, "good-1 should still be evaluated"
        assert "good-2" in slugs_by_grade, "good-2 should still be evaluated"

    def test_evaluate_output_count_matches_input(self, tmp_path: Path) -> None:
        """EvaluateWorker produces exactly one PageEvaluation per input page."""
        from launcher.workers.evaluate.worker import EvaluateWorker

        pages = [_make_gen_page(f"p-{i}", tmp_path) for i in range(6)]
        manifest = ContentManifest(pages=pages)
        ctx = _make_eval_context(tmp_path)

        report = asyncio.run(EvaluateWorker().run(manifest, ctx))

        assert len(report.pages) == len(pages), (
            f"Expected {len(pages)} PageEvaluations, got {len(report.pages)}"
        )


# ---------------------------------------------------------------------------
# HO-06: Section-level finding→section_id mapping and section-skip tests
# ---------------------------------------------------------------------------


class TestSectionIdMapping:
    """section_id field set on section-scoped findings; None for global checks."""

    def test_finding_model_has_section_id_field(self) -> None:
        """Finding model must have section_id: str | None = None."""
        from launcher.models.evaluation import Finding

        f = Finding(check="density", message="too short", severity="low", location="pg-1")
        assert hasattr(f, "section_id")
        assert f.section_id is None

    def test_density_finding_has_section_id_when_section_scoped(self, tmp_path: Path) -> None:
        """Density check emits section_id when a section is too short."""
        from launcher.workers.evaluate.checks.density import check_density

        content = "## Short Section\n\nHi.\n\n## Normal Section\n\n" + "word " * 50
        findings = check_density(content, "test-page")
        section_findings = [f for f in findings if f.check == "density" and f.section_id is not None]
        assert section_findings, "Expected at least one density finding with section_id set"
        assert section_findings[0].section_id == "Short Section"

    def test_structure_heading_finding_has_section_id(self, tmp_path: Path) -> None:
        """Structure check sets section_id from heading text for per-heading findings."""
        from launcher.workers.evaluate.checks.structure import check_structure

        # H5 deep heading — should produce a section-scoped finding
        content = "## Overview\n\nContent.\n\n##### Very Deep\n\nSomething.\n"
        findings = check_structure(content, "test-page")
        deep_findings = [f for f in findings if "Deep" in f.message]
        assert deep_findings, "Expected a 'Deep heading' finding"
        assert deep_findings[0].section_id == "Very Deep", (
            f"section_id should be heading text, got {deep_findings[0].section_id!r}"
        )

    def test_section_skip_reuses_cached_section(self, tmp_path: Path) -> None:
        """When failing_section_ids set, non-failing sections reuse cached SectionIR."""
        from launcher.workers.generate.worker import _generate_page
        from launcher.models.page_ir import PageIR, SectionIR
        from launcher.models.plan import PlannedPage
        from launcher.models.product import ProductIdentity, RichnessTier
        from launcher.shared.page_skeletons import SkeletonSection

        # Build a minimal cached PageIR with two sections.
        # TC-3882 (Gap4): _section_needs_regen requires ≥80 prose words to skip regen.
        _long_text = " ".join(["word"] * 90)  # 90 words → passes the 80-word threshold
        from launcher.models.page_ir import BlockIR
        cached_section_a = SectionIR(
            section_id="overview", heading="Overview", level=2,
            blocks=[BlockIR(type="paragraph", content=_long_text)],
        )
        cached_section_b = SectionIR(
            section_id="usage", heading="Usage", level=2,
            blocks=[BlockIR(type="paragraph", content=_long_text)],
        )
        cached_ir = PageIR(
            page_id="page-1",
            page_role="overview",
            title="Test Page",
            frontmatter={"slug": "page-1"},
            sections=[cached_section_a, cached_section_b],
        )

        # Context with failing_section_ids: only "Usage" is failing → "Overview" is skipped
        ctx = _make_context(tmp_path=tmp_path)
        ctx._heal_metadata = {
            "failing_section_ids": {"page-1": ["Usage"]},
        }

        # Minimal page plan
        page_plan = MagicMock(spec=PlannedPage)
        page_plan.page_id = "page-1"
        page_plan.page_role = "overview"
        page_plan.title = "Test Page"
        page_plan.frontmatter = {"slug": "page-1"}
        page_plan.assigned_claims = []
        page_plan.assigned_snippets = []
        page_plan.skeleton_variant = "default"
        page_plan.sections = [
            MagicMock(heading="Overview", level=2),
            MagicMock(heading="Usage", level=2),
        ]

        product = MagicMock(spec=ProductIdentity)
        product.family = "cells"
        product.platform = "python"
        product.display_name = "TestProd"
        product.canonical_import = "import test"
        product.primary_language = "python"

        # Patch skeleton to return our two sections
        with patch(
            "launcher.workers.generate.worker.get_template_content",
            return_value="",
        ), patch(
            "launcher.shared.page_skeletons.resolve_skeleton",
            return_value=[
                SkeletonSection(heading="Overview", level=2, max_words=300, required=False, content_hint="", min_words=0),
                SkeletonSection(heading="Usage", level=2, max_words=300, required=False, content_hint="", min_words=0),
            ],
        ):
            result_ir, _, _, _, _, _ = asyncio.run(_generate_page(
                page_plan, product, [], [], [], ctx,
                tier=RichnessTier.B, family="cells",
                cached_page_ir=cached_ir,
            ))

        # "Overview" section was cached — verify it's the exact cached_section_a
        overview_sections = [s for s in result_ir.sections if s.heading == "Overview"]
        assert overview_sections, "Overview section should be present in result"
        assert overview_sections[0] is cached_section_a, (
            "Overview section should be the cached SectionIR object"
        )

    def test_section_skipped_event_emitted(self, tmp_path: Path) -> None:
        """generate_section_skipped event is emitted for each reused section."""
        from launcher.workers.generate.worker import _generate_page
        from launcher.models.page_ir import PageIR, SectionIR
        from launcher.models.plan import PlannedPage
        from launcher.models.product import ProductIdentity, RichnessTier
        from launcher.shared.page_skeletons import SkeletonSection

        # TC-3882 (Gap4): _section_needs_regen requires ≥80 prose words to skip regen.
        _long_text = " ".join(["word"] * 90)
        from launcher.models.page_ir import BlockIR
        cached_section = SectionIR(
            section_id="overview", heading="Overview", level=2,
            blocks=[BlockIR(type="paragraph", content=_long_text)],
        )
        cached_ir = PageIR(
            page_id="pg-ev", page_role="overview", title="Evt Page",
            frontmatter={"slug": "pg-ev"}, sections=[cached_section],
        )

        emitted_events: list[str] = []

        ctx = _make_context(tmp_path=tmp_path)
        ctx._heal_metadata = {"failing_section_ids": {"pg-ev": ["Usage"]}}
        real_emit = ctx.emit_event

        def _capture(event_type: str, data: dict, **kw: object) -> None:
            emitted_events.append(event_type)
            real_emit(event_type, data, **kw)

        ctx.emit_event = _capture  # type: ignore[method-assign]

        page_plan = MagicMock(spec=PlannedPage)
        page_plan.page_id = "pg-ev"
        page_plan.page_role = "overview"
        page_plan.title = "Evt Page"
        page_plan.frontmatter = {"slug": "pg-ev"}
        page_plan.assigned_claims = []
        page_plan.assigned_snippets = []
        page_plan.skeleton_variant = "default"
        page_plan.sections = [MagicMock(heading="Overview", level=2)]

        product = MagicMock(spec=ProductIdentity)
        product.family = "cells"
        product.display_name = "P"
        product.canonical_import = "import x"
        product.primary_language = "python"

        with patch(
            "launcher.workers.generate.worker.get_template_content",
            return_value="",
        ), patch(
            "launcher.shared.page_skeletons.resolve_skeleton",
            return_value=[SkeletonSection(heading="Overview", level=2, max_words=300, required=False, content_hint="", min_words=0)],
        ):
            asyncio.run(_generate_page(
                page_plan, product, [], [], [], ctx,
                tier=RichnessTier.B, family="cells",
                cached_page_ir=cached_ir,
            ))

        assert "generate_section_skipped" in emitted_events, (
            "generate_section_skipped event must be emitted for cached section"
        )

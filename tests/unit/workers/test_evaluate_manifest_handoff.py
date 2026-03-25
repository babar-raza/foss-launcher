"""Regression tests for TC-HO-09-R: Evaluate worker manifest-first handoff paths.

Tests:
- api_fact_member_names manifest-first path builds proxy extraction_db
- checkpoint_fallback events emitted when manifest fields are empty
- No checkpoint_fallback events when manifest is fully populated
- Backward compat: old manifests (no api_fact_member_names) trigger checkpoint fallback
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.models.content import ContentManifest, GeneratedPage, GenerationStats
from launcher.models.product import ApiSurface
from launcher.models.run_config import RunConfig
from launcher.models.understanding import ProductEvidence
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.evaluate.worker import EvaluateWorker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_CONTENT = """\
---
title: "Test Page"
slug: test-page
description: "A test page for evaluation."
---

## Overview

This page covers the main functionality of the library.

```python
from mylib import MyClass
obj = MyClass()
obj.save("output.xlsx")
```

The API provides comprehensive functionality for working with spreadsheets.
"""


def _make_context(tmp_path: Path) -> WorkerContext:
    run_dir = tmp_path / "runs" / "test-eval-handoff"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=None,
    )
    return WorkerContext(
        run_id="test-eval-handoff-001",
        run_dir=run_dir,
        config=config,
        llm_config=None,
    )


def _write_page(run_dir: Path, md_path: str, content: str) -> None:
    full = run_dir / md_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def _read_events(run_dir: Path) -> list[dict]:
    events_path = run_dir / "events.ndjson"
    if not events_path.exists():
        return []
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _checkpoint_fallback_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("event_type") == "checkpoint_fallback"]


# ---------------------------------------------------------------------------
# TC-HO-09-R: api_fact_member_names proxy construction
# ---------------------------------------------------------------------------


class TestApiFactMemberNamesManifestFirstPath:
    """Verify Evaluate uses manifest api_fact_member_names to build proxy extraction_db."""

    @pytest.mark.asyncio
    async def test_manifest_with_member_names_does_not_emit_extraction_db_fallback(
        self, tmp_path
    ):
        """When api_fact_member_names is populated, no checkpoint_fallback for extraction_db."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test-page.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="test-page",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            ],
            generation_stats=GenerationStats(total_pages=1),
            richness_tier="B",
            api_fact_member_names=["Workbook", "save", "load"],
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        db_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "extraction_db"
        ]
        assert len(db_fallbacks) == 0, (
            "No checkpoint_fallback for extraction_db when api_fact_member_names is populated"
        )

    @pytest.mark.asyncio
    async def test_manifest_without_member_names_emits_extraction_db_fallback(
        self, tmp_path
    ):
        """Empty api_fact_member_names emits checkpoint_fallback for extraction_db."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test-page.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        # No api_fact_member_names, no checkpoint on disk
        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="test-page",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            ],
            generation_stats=GenerationStats(total_pages=1),
            richness_tier="B",
            # api_fact_member_names defaults to []
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        db_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "extraction_db"
        ]
        assert len(db_fallbacks) == 1, (
            "Exactly one checkpoint_fallback event for extraction_db when api_fact_member_names empty"
        )
        assert db_fallbacks[0]["data"]["reason"] == "not_in_manifest"


# ---------------------------------------------------------------------------
# TC-HO-09-R: product_evidence checkpoint_fallback events
# ---------------------------------------------------------------------------


class TestProductEvidenceCheckpointFallbackEvent:
    """Verify checkpoint_fallback event is emitted when manifest product_evidence is empty."""

    @pytest.mark.asyncio
    async def test_empty_product_evidence_emits_checkpoint_fallback(self, tmp_path):
        """ContentManifest with default (empty) product_evidence emits checkpoint_fallback."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test-page.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="test-page",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            ],
            generation_stats=GenerationStats(total_pages=1),
            richness_tier="B",
            # product_evidence defaults to ProductEvidence() — empty
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        pe_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "product_evidence"
        ]
        assert len(pe_fallbacks) == 1, (
            "Exactly one checkpoint_fallback event for product_evidence when manifest is empty"
        )
        assert pe_fallbacks[0]["data"]["reason"] == "manifest_product_evidence_empty"

    @pytest.mark.asyncio
    async def test_populated_product_evidence_no_checkpoint_fallback(self, tmp_path):
        """Non-empty product_evidence in manifest suppresses checkpoint_fallback event."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test-page.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="test-page",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            ],
            generation_stats=GenerationStats(total_pages=1),
            richness_tier="B",
            product_evidence=ProductEvidence(
                supported_formats=["PDF", "XLSX"],
                input_formats=["PDF"],
                output_formats=["XLSX"],
            ),
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        pe_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "product_evidence"
        ]
        assert len(pe_fallbacks) == 0, (
            "No checkpoint_fallback for product_evidence when manifest has populated data"
        )


# ---------------------------------------------------------------------------
# TC-HO-09-R: api_surface checkpoint_fallback events
# ---------------------------------------------------------------------------


class TestApiSurfaceCheckpointFallbackEvent:
    """Verify checkpoint_fallback event for api_surface when manifest field is empty."""

    @pytest.mark.asyncio
    async def test_empty_api_surface_emits_checkpoint_fallback(self, tmp_path):
        """Default (low-confidence, empty) api_surface emits checkpoint_fallback."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test-page.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="test-page",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            ],
            generation_stats=GenerationStats(total_pages=1),
            richness_tier="B",
            # api_surface defaults to ApiSurface(public_classes=[], confidence="low")
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        api_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "api_surface"
        ]
        assert len(api_fallbacks) == 1, (
            "Exactly one checkpoint_fallback event for api_surface when manifest field is empty"
        )

    @pytest.mark.asyncio
    async def test_populated_api_surface_no_checkpoint_fallback(self, tmp_path):
        """Populated api_surface suppresses checkpoint_fallback event."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test-page.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        manifest = ContentManifest(
            pages=[
                GeneratedPage(
                    slug="test-page",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            ],
            generation_stats=GenerationStats(total_pages=1),
            richness_tier="B",
            api_surface=ApiSurface(
                public_classes=["Workbook"],
                import_allowlist=["import aspose_cells"],
                confidence="high",
                api_identifiers=["Workbook", "Workbook.save"],
            ),
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        api_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "api_surface"
        ]
        assert len(api_fallbacks) == 0, (
            "No checkpoint_fallback for api_surface when manifest field is populated"
        )


# ---------------------------------------------------------------------------
# TC-HO-09-R: checkpoint_fallback events emitted once (not per page)
# ---------------------------------------------------------------------------


class TestCheckpointFallbackEmittedOnce:
    """Verify checkpoint_fallback events are emitted exactly once per run, not per page."""

    @pytest.mark.asyncio
    async def test_checkpoint_fallback_emitted_once_for_multi_page_manifest(self, tmp_path):
        """With 3 pages and empty product_evidence, only 1 checkpoint_fallback event."""
        ctx = _make_context(tmp_path)
        pages = []
        for i in range(3):
            md_path = f"content_bundle/pages/page-{i}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(
                GeneratedPage(
                    slug=f"page-{i}",
                    page_role="overview",
                    section="docs",
                    md_path=md_path,
                    word_count=150,
                )
            )

        manifest = ContentManifest(
            pages=pages,
            generation_stats=GenerationStats(total_pages=3),
            richness_tier="B",
            # All manifest fields empty — triggers all 3 checkpoint_fallback events
        )

        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        events = _read_events(ctx.run_dir)
        pe_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "product_evidence"
        ]
        api_fallbacks = [
            e for e in _checkpoint_fallback_events(events)
            if e.get("data", {}).get("field") == "api_surface"
        ]
        # Each should appear exactly once, regardless of page count
        assert len(pe_fallbacks) == 1, (
            f"Expected 1 product_evidence fallback event, got {len(pe_fallbacks)}"
        )
        assert len(api_fallbacks) == 1, (
            f"Expected 1 api_surface fallback event, got {len(api_fallbacks)}"
        )


# ---------------------------------------------------------------------------
# TC-5163: page_evidence_index embedded in ContentManifest
# ---------------------------------------------------------------------------


class TestPageEvidenceIndexManifestField:
    """TC-5163: Verify page_evidence_index is correctly embedded in ContentManifest."""

    def test_page_evidence_index_defaults_to_empty_dict(self):
        """ContentManifest.page_evidence_index defaults to {} for backward compat."""
        manifest = ContentManifest(
            pages=[],
            generation_stats=GenerationStats(total_pages=0),
        )
        assert manifest.page_evidence_index == {}

    def test_page_evidence_index_accepts_evidence_score_dicts(self):
        """page_evidence_index can hold PageEvidenceScore-shaped dicts keyed by page_role."""
        pei = {
            "overview": {"evidence_sufficient": True, "verified_claim_count": 5, "missing": []},
            "reference": {"evidence_sufficient": False, "verified_claim_count": 1, "missing": ["no_snippets"]},
        }
        manifest = ContentManifest(
            pages=[],
            generation_stats=GenerationStats(total_pages=0),
            page_evidence_index=pei,
        )
        assert manifest.page_evidence_index["overview"]["evidence_sufficient"] is True
        assert manifest.page_evidence_index["reference"]["evidence_sufficient"] is False
        assert manifest.page_evidence_index["reference"]["missing"] == ["no_snippets"]

    def test_page_evidence_index_round_trips_through_json(self):
        """page_evidence_index survives model_dump/model_validate round-trip."""
        pei = {"faq": {"evidence_sufficient": False, "verified_claim_count": 0, "missing": ["no_claims"]}}
        manifest = ContentManifest(
            pages=[],
            generation_stats=GenerationStats(total_pages=0),
            page_evidence_index=pei,
        )
        dumped = manifest.model_dump(mode="json")
        restored = ContentManifest.model_validate(dumped)
        assert restored.page_evidence_index == pei

    def test_page_evidence_index_empty_old_manifest_no_keyerror(self):
        """Old manifests without page_evidence_index field deserialize without error."""
        # Simulate an old manifest JSON that has no page_evidence_index key
        old_manifest_data = {
            "pages": [],
            "cross_links": [],
            "generation_stats": {"total_pages": 0, "llm_calls": 0, "fallback_count": 0, "duration_seconds": 0.0},
        }
        manifest = ContentManifest.model_validate(old_manifest_data)
        assert manifest.page_evidence_index == {}

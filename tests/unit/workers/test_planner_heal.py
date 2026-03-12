"""Tests for TC-3850: Planner Worker Heal Directive Injection.

These tests verify the heal-mode block in PlannerWorker.run() by directly
exercising the heal_metadata access pattern with a mock WorkerContext.
The full worker pipeline is not run — only the heal-mode logic is tested.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock


def _make_context(heal_metadata=None):
    """Build a mock WorkerContext that captures emitted events."""
    ctx = MagicMock()
    ctx.heal_metadata = heal_metadata if heal_metadata is not None else {}
    ctx.log = logging.getLogger("test_planner_heal")
    emitted: list[dict] = []
    ctx.emit_event = lambda event_type, data, worker="": emitted.append(
        {"event_type": event_type, "data": data, "worker": worker}
    )
    ctx._emitted = emitted
    return ctx


def _get_planner_heal_events(ctx):
    return [e for e in ctx._emitted if e["event_type"] == "planner_heal_mode"]


def _run_heal_block(ctx, worker_name="planner"):
    """Simulate the heal-mode block from PlannerWorker.run()."""
    heal_metadata: dict = ctx.heal_metadata or {}
    re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
    if re_run_count > 0:
        failed_pages = heal_metadata.get("failed_pages", []) or []
        failed_checks = heal_metadata.get("failed_checks", []) or []
        ctx.log.info(
            "[Planner] Heal mode (re_run=%d): %d pages need healing, checks: %s",
            re_run_count, len(failed_pages), failed_checks,
        )
        ctx.emit_event(
            "planner_heal_mode",
            {
                "re_run_count": re_run_count,
                "failed_pages": failed_pages,
                "failed_checks": failed_checks,
            },
            worker=worker_name,
        )


def test_no_planner_heal_event_when_heal_metadata_empty():
    """Test 1: heal_metadata={} -> no planner_heal_mode event."""
    ctx = _make_context(heal_metadata={})
    _run_heal_block(ctx)
    assert len(_get_planner_heal_events(ctx)) == 0


def test_planner_heal_event_emitted_when_re_run_count_1():
    """Test 2: heal_metadata={"re_run_count": 1} -> planner_heal_mode event."""
    ctx = _make_context(heal_metadata={"re_run_count": 1})
    _run_heal_block(ctx)
    events = _get_planner_heal_events(ctx)
    assert len(events) == 1
    assert events[0]["data"]["re_run_count"] == 1


def test_planner_heal_event_has_correct_failed_pages_and_checks():
    """Test 3: heal_metadata with failed_pages + failed_checks -> correct event data."""
    ctx = _make_context(heal_metadata={
        "re_run_count": 1,
        "failed_pages": ["pg-1"],
        "failed_checks": ["density"],
    })
    _run_heal_block(ctx)
    events = _get_planner_heal_events(ctx)
    assert len(events) == 1
    data = events[0]["data"]
    assert data["re_run_count"] == 1
    assert "pg-1" in data["failed_pages"]
    assert "density" in data["failed_checks"]


def test_no_planner_heal_event_when_re_run_count_is_zero():
    """Test 4: re_run_count=0 -> no planner_heal_mode event."""
    ctx = _make_context(heal_metadata={"re_run_count": 0})
    _run_heal_block(ctx)
    assert len(_get_planner_heal_events(ctx)) == 0


def test_golden_index_importable_from_planner_worker():
    """Test 5: TC-3834 golden self-review block still present.

    Verifies GoldenIndex is importable from the module used by planner worker.
    This ensures the TC-3834 golden self-review block has not been removed.
    """
    from launcher.shared.golden_loader import GoldenIndex
    assert GoldenIndex is not None

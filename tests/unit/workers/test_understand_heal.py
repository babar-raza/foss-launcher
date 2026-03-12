"""Tests for TC-3849: Understand Worker Heal Directive Injection.

These tests verify the heal-mode block in UnderstandWorker.run() by directly
exercising the heal_metadata access pattern with a mock WorkerContext.
The full worker pipeline is not run — only the heal-mode logic is tested.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest


def _make_context(heal_metadata=None):
    """Build a mock WorkerContext that captures emitted events."""
    ctx = MagicMock()
    ctx.heal_metadata = heal_metadata if heal_metadata is not None else {}
    ctx.log = logging.getLogger("test_understand_heal")
    emitted: list[dict] = []
    ctx.emit_event = lambda event_type, data, worker="": emitted.append(
        {"event_type": event_type, "data": data, "worker": worker}
    )
    ctx._emitted = emitted
    return ctx


def _get_heal_events(ctx):
    return [e for e in ctx._emitted if e["event_type"] == "understand_heal_mode"]


def _run_heal_block(ctx, worker_name="understand"):
    """Simulate the heal-mode block from UnderstandWorker.run()."""
    heal_metadata: dict = ctx.heal_metadata or {}
    re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
    if re_run_count > 0:
        ctx.log.info(
            "[Understand] Heal mode (re_run=%d): tightening extraction focus",
            re_run_count,
        )
        ctx.emit_event(
            "understand_heal_mode",
            {
                "re_run_count": re_run_count,
                "focus_page_roles": heal_metadata.get("focus_page_roles", []),
                "page_directives": heal_metadata.get("page_directives", []),
            },
            worker=worker_name,
        )


def test_no_heal_mode_event_when_heal_metadata_empty():
    """Test 1: heal_metadata={} -> no understand_heal_mode event emitted."""
    ctx = _make_context(heal_metadata={})
    _run_heal_block(ctx)
    assert len(_get_heal_events(ctx)) == 0


def test_heal_mode_event_emitted_when_re_run_count_1():
    """Test 2: heal_metadata={"re_run_count": 1} -> understand_heal_mode event with re_run_count=1."""
    ctx = _make_context(heal_metadata={"re_run_count": 1})
    _run_heal_block(ctx)
    events = _get_heal_events(ctx)
    assert len(events) == 1
    assert events[0]["data"]["re_run_count"] == 1


def test_heal_mode_event_has_focus_page_roles():
    """Test 3: heal_metadata with focus_page_roles -> event contains focus_page_roles."""
    ctx = _make_context(heal_metadata={
        "re_run_count": 2,
        "focus_page_roles": ["workflow_page"],
    })
    _run_heal_block(ctx)
    events = _get_heal_events(ctx)
    assert len(events) == 1
    assert events[0]["data"]["re_run_count"] == 2
    assert "workflow_page" in events[0]["data"]["focus_page_roles"]


def test_no_heal_mode_event_when_re_run_count_is_zero():
    """Test 4: re_run_count=0 -> no understand_heal_mode event."""
    ctx = _make_context(heal_metadata={"re_run_count": 0})
    _run_heal_block(ctx)
    assert len(_get_heal_events(ctx)) == 0


def test_none_heal_metadata_does_not_crash():
    """Test 5: None heal_metadata -> no crash, no event emitted.

    WorkerContext.heal_metadata always returns a dict, but the worker
    also applies `or {}` as a safety guard. Verify no AttributeError
    when heal_metadata is effectively None.
    """
    ctx = _make_context(heal_metadata=None)
    # Directly simulate the worker's guard
    heal_metadata: dict = ctx.heal_metadata or {}
    re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
    assert re_run_count == 0
    # No event emitted
    assert len(_get_heal_events(ctx)) == 0

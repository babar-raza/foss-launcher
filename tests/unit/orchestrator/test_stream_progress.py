"""TC-3915 / TC-4064: Tests for _stream_execute and StreamEventHandler.

TC-4064: Streaming is always active — ainvoke() fallback removed.
         StreamEventHandler class extracted from inline loop.
         Custom events (page_generated, page_evaluated) displayed as sub-lines.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from launcher.orchestrator.run_loop import StreamEventHandler, _stream_execute


class _FakeGraph:
    """Minimal compiled graph stub (astream_events only — ainvoke removed)."""

    def __init__(self, state_out: dict[str, Any]) -> None:
        self._state_out = state_out

    async def astream_events(
        self, state: Any, *, version: str = "v2", config: dict | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        # Yield start + end events for one node, then final LangGraph end
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {"event": "on_chain_end", "name": "generate", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": self._state_out},
        }


class _FakeGraphWithCustomEvents:
    """Fake graph that also emits custom events (with total for N/T display)."""

    def __init__(self, state_out: dict[str, Any]) -> None:
        self._state_out = state_out

    async def astream_events(
        self, state: Any, *, version: str = "v2", config: dict | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {"event": "on_custom_event", "name": "page_generated", "data": {"slug": "install", "words": 450, "total": 2}}
        yield {"event": "on_custom_event", "name": "page_generated", "data": {"slug": "quickstart", "words": 300, "total": 2}}
        yield {"event": "on_chain_end", "name": "generate", "data": {}}
        yield {"event": "on_chain_start", "name": "evaluate", "data": {}}
        yield {"event": "on_custom_event", "name": "page_evaluated", "data": {"slug": "install", "grade": "B", "findings": 2}}
        yield {"event": "on_chain_end", "name": "evaluate", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": self._state_out},
        }


@pytest.mark.asyncio
async def test_stream_always_active_returns_correct_state() -> None:
    """Streaming is always active (no ainvoke fallback). Final state is captured."""
    expected: dict[str, Any] = {"worker_outputs": {"generate": {"pages": []}}}
    graph = _FakeGraph(expected)
    # stream_progress=False is kept for API compat but streaming is always on
    result = await _stream_execute(graph, {}, stream_progress=False)
    assert result == expected


@pytest.mark.asyncio
async def test_stream_emits_progress_lines(capsys: pytest.CaptureFixture[str]) -> None:
    expected: dict[str, Any] = {"worker_outputs": {}}
    graph = _FakeGraph(expected)
    await _stream_execute(graph, {})
    captured = capsys.readouterr()
    assert "starting..." in captured.err or "done" in captured.err


@pytest.mark.asyncio
async def test_stream_captures_final_state() -> None:
    expected: dict[str, Any] = {"worker_outputs": {"generate": {"pages": ["p1"]}}}
    graph = _FakeGraph(expected)
    result = await _stream_execute(graph, {})
    assert result == expected


@pytest.mark.asyncio
async def test_custom_events_displayed_as_sub_lines(capsys: pytest.CaptureFixture[str]) -> None:
    """Custom events (page_generated, page_evaluated) appear as indented sub-lines with N/T counter."""
    expected: dict[str, Any] = {"worker_outputs": {}}
    graph = _FakeGraphWithCustomEvents(expected)
    result = await _stream_execute(graph, {})
    assert result == expected
    captured = capsys.readouterr()
    assert "install" in captured.err          # page slug appears
    assert "1/2" in captured.err              # N/T position counter (first of two pages)
    assert "2/2" in captured.err              # N/T position counter (second page)
    assert "450 words" in captured.err        # page_generated words
    assert "grade=B" in captured.err          # page_evaluated grade
    assert "findings=2" in captured.err       # page_evaluated findings count


@pytest.mark.asyncio
async def test_page_generated_without_total_omits_fraction(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When total is absent from page_generated payload, format shows (N, K words) not (N/T, K words)."""

    async def _events_no_total() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {"event": "on_custom_event", "name": "page_generated", "data": {"slug": "index", "words": 200}}
        yield {"event": "on_chain_end", "name": "LangGraph", "data": {"output": {"worker_outputs": {}}}}

    handler = StreamEventHandler()
    await handler.consume(_events_no_total())
    captured = capsys.readouterr()
    assert "index" in captured.err
    assert "200 words" in captured.err
    assert "/" not in captured.err.split("index")[1].split("\n")[0]  # no fraction on that line


@pytest.mark.asyncio
async def test_stream_event_handler_direct() -> None:
    """StreamEventHandler can be used directly (for alternative frontends)."""

    async def _fake_events() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {"event": "on_chain_end", "name": "generate", "data": {}}
        yield {"event": "on_chain_end", "name": "LangGraph", "data": {"output": {"verdict": "GO"}}}

    handler = StreamEventHandler()
    state = await handler.consume(_fake_events())
    assert state == {"verdict": "GO"}


@pytest.mark.asyncio
async def test_custom_events_accumulated_in_final_state() -> None:
    """Custom events emitted during graph execution appear in final state stream_events."""

    async def _events_with_custom() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {
            "event": "on_custom_event",
            "name": "page_generated",
            "data": {"slug": "install", "words": 450},
        }
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"worker_outputs": {"generate": {}}}},
        }

    handler = StreamEventHandler()
    state = await handler.consume(_events_with_custom())
    events = state.get("stream_events", [])
    assert len(events) == 1
    assert events[0]["name"] == "page_generated"
    assert events[0]["data"]["slug"] == "install"
    assert "ts" in events[0]


@pytest.mark.asyncio
async def test_stream_events_empty_when_no_custom_events() -> None:
    """stream_events is absent or empty when no custom events were emitted."""

    async def _events_no_custom() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {"output": {"worker_outputs": {}}},
        }

    handler = StreamEventHandler()
    state = await handler.consume(_events_no_custom())
    assert state.get("stream_events", []) == []


@pytest.mark.asyncio
async def test_safe_stream_event_noop_outside_langgraph() -> None:
    """safe_stream_event must silently no-op when called outside a LangGraph context."""
    from launcher.orchestrator.stream_events import safe_stream_event

    # Should complete without raising even though there is no LangGraph context
    await safe_stream_event("page_generated", {"slug": "test", "words": 100})


@pytest.mark.asyncio
async def test_consume_raises_on_missing_final_state() -> None:
    """consume() must raise RuntimeError if graph never emits the LangGraph final state."""

    async def _incomplete_stream() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "on_chain_start", "name": "generate", "data": {}}
        yield {"event": "on_chain_start", "name": "evaluate", "data": {}}
        # Deliberately omit the LangGraph on_chain_end event

    handler = StreamEventHandler()
    with pytest.raises(RuntimeError, match="without emitting a final state"):
        await handler.consume(_incomplete_stream())

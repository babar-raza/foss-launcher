"""TC-3915: Tests for _stream_execute streaming helper."""
from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from launcher.orchestrator.run_loop import _stream_execute


class _FakeGraph:
    """Minimal compiled graph stub."""

    def __init__(self, state_out: dict[str, Any]) -> None:
        self._state_out = state_out

    async def ainvoke(self, state: Any, config: dict | None = None) -> dict[str, Any]:
        return self._state_out

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


@pytest.mark.asyncio
async def test_no_stream_returns_correct_state() -> None:
    expected: dict[str, Any] = {"worker_outputs": {"generate": {"pages": []}}}
    graph = _FakeGraph(expected)
    result = await _stream_execute(graph, {}, stream_progress=False)
    assert result == expected


@pytest.mark.asyncio
async def test_stream_emits_progress_lines(capsys: pytest.CaptureFixture[str]) -> None:
    expected: dict[str, Any] = {"worker_outputs": {}}
    graph = _FakeGraph(expected)
    await _stream_execute(graph, {}, stream_progress=True)
    captured = capsys.readouterr()
    assert "starting..." in captured.err or "done" in captured.err


@pytest.mark.asyncio
async def test_stream_captures_final_state() -> None:
    expected: dict[str, Any] = {"worker_outputs": {"generate": {"pages": ["p1"]}}}
    graph = _FakeGraph(expected)
    result = await _stream_execute(graph, {}, stream_progress=True)
    assert result == expected

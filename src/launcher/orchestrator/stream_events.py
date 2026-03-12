"""LangGraph custom event helpers for use in worker nodes.

Workers call ``safe_stream_event`` to emit structured progress events through the
LangGraph streaming protocol.  Outside a LangGraph execution context (e.g. unit
tests that call worker functions directly) the call is a silent no-op so that
test code does not need to mock the LangGraph runtime.
"""
from __future__ import annotations


async def safe_stream_event(name: str, data: dict) -> None:
    """Emit a LangGraph custom stream event; no-op outside graph execution context.

    Args:
        name: Event name (e.g. ``"page_generated"``, ``"page_evaluated"``).
        data: Arbitrary JSON-serialisable payload forwarded to the stream consumer.

    Raises:
        Nothing — all exceptions are suppressed so a broken LangGraph context
        does not crash a worker.
    """
    try:
        from langgraph.config import adispatch_custom_event  # type: ignore[import]

        await adispatch_custom_event(name, data)
    except Exception:  # noqa: BLE001
        pass

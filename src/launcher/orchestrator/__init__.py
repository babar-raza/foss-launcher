"""Orchestrator — config-driven pipeline engine for foss-launcher v2.

Public API:
    - ``execute_run``: Main entry point for running the full pipeline.
    - ``build_pipeline``: Build a LangGraph StateGraph from pipeline.yaml.
    - ``WorkerContract``: Abstract base class all workers implement.
    - ``WorkerContext``: Runtime context injected into each worker call.
    - ``SelfReviewResult``: Outcome of a worker's semantic self-review.
    - ``PipelineGraphState``: TypedDict flowing through the LangGraph nodes.
"""

from __future__ import annotations

from .graph_builder import build_pipeline, load_pipeline_config
from .run_loop import StreamEventHandler, execute_run
from .state import PipelineGraphState
from .stream_events import safe_stream_event
from .worker_contract import SelfReviewResult, WorkerContext, WorkerContract

__all__ = [
    "PipelineGraphState",
    "SelfReviewResult",
    "StreamEventHandler",
    "WorkerContext",
    "WorkerContract",
    "build_pipeline",
    "execute_run",
    "load_pipeline_config",
    "safe_stream_event",
]

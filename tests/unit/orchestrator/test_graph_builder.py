"""Unit tests for graph_builder checkpoint enrichment (TC-3839)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from launcher.models.base import LauncherBaseModel
from launcher.models.run_config import LLMConfig, LLMEndpoint, RunConfig
from launcher.orchestrator.state import PipelineGraphState
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext, WorkerContract


# ---------------------------------------------------------------------------
# Minimal pipeline.yaml fixture
# ---------------------------------------------------------------------------

_PIPELINE_YAML = """\
version: "2.0"
defaults:
  max_re_runs: 2
  schema_dir: "specs/schemas"
pipeline:
  - worker: dummy
    input_schema: "run_config.schema.json"
    output_schema: "run_config.schema.json"
    checkpoint: true
"""


# ---------------------------------------------------------------------------
# Minimal worker implementation
# ---------------------------------------------------------------------------


class _DummyOutput(LauncherBaseModel):
    status: str = "ok"


class _DummyWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "dummy"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> LauncherBaseModel:
        return _DummyOutput(status="ok")

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        return SelfReviewResult(passed=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_config() -> RunConfig:
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=LLMConfig(
            primary=LLMEndpoint(base_url="http://localhost:11434/v1", model="test-model"),
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCheckpointWrittenEventEnrichment:
    """checkpoint_written event must carry artifact_path, content_hash, checkpoint_id."""

    def test_checkpoint_event_has_required_keys(self, tmp_path: Path) -> None:
        """After a successful worker execution the checkpoint_written event must include
        artifact_path, content_hash, and checkpoint_id keys.
        """
        from launcher.orchestrator.graph_builder import (
            WorkerEntry,
            _make_worker_node,
        )

        entry = WorkerEntry(
            name="dummy",
            input_schema="run_config.schema.json",
            output_schema="run_config.schema.json",
            checkpoint=True,
        )
        run_config = _make_run_config()

        emitted: list[dict[str, Any]] = []

        # Patch WorkerContext so we can capture emitted events.
        original_init = WorkerContext.__init__

        def _patched_init(self_ctx, *args, **kwargs):
            original_init(self_ctx, *args, **kwargs)
            # Override emit_event to capture calls.
            real_emit = self_ctx.emit_event

            def _capturing_emit(event_type, data, **kw):
                emitted.append({"event_type": event_type, "data": data})
                real_emit(event_type, data, **kw)

            self_ctx.emit_event = _capturing_emit

        import unittest.mock as _mock

        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()

        worker = _DummyWorker()
        node_fn = _make_worker_node(
            entry, worker, schema_dir, ["dummy"],
        )

        state: PipelineGraphState = PipelineGraphState(
            run_id="test-run-01",
            run_dir=str(tmp_path),
            config=run_config.model_dump(mode="json"),
            current_worker="",
            worker_outputs={},
            re_run_count=0,
            max_re_runs=2,
            verdict="",
            errors=[],
        )

        with _mock.patch.object(WorkerContext, "__init__", _patched_init):
            result = asyncio.run(node_fn(state))

        checkpoint_events = [e for e in emitted if e["event_type"] == "checkpoint_written"]
        assert len(checkpoint_events) == 1, (
            f"Expected exactly one checkpoint_written event, got {len(checkpoint_events)}"
        )
        event_data = checkpoint_events[0]["data"]
        assert "artifact_path" in event_data, "checkpoint_written event missing 'artifact_path'"
        assert "content_hash" in event_data, "checkpoint_written event missing 'content_hash'"
        assert "checkpoint_id" in event_data, "checkpoint_written event missing 'checkpoint_id'"

    def test_checkpoint_event_artifact_path_ends_with_filename(self, tmp_path: Path) -> None:
        """artifact_path in checkpoint_written event must end with '<worker>_checkpoint.json'."""
        from launcher.orchestrator.graph_builder import WorkerEntry, _make_worker_node

        entry = WorkerEntry(
            name="dummy",
            input_schema="run_config.schema.json",
            output_schema="run_config.schema.json",
            checkpoint=True,
        )
        run_config = _make_run_config()
        emitted: list[dict[str, Any]] = []

        original_init = WorkerContext.__init__

        def _patched_init(self_ctx, *args, **kwargs):
            original_init(self_ctx, *args, **kwargs)
            real_emit = self_ctx.emit_event

            def _capturing_emit(event_type, data, **kw):
                emitted.append({"event_type": event_type, "data": data})
                real_emit(event_type, data, **kw)

            self_ctx.emit_event = _capturing_emit

        import unittest.mock as _mock

        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()

        worker = _DummyWorker()
        node_fn = _make_worker_node(entry, worker, schema_dir, ["dummy"])

        state: PipelineGraphState = PipelineGraphState(
            run_id="test-run-02",
            run_dir=str(tmp_path),
            config=run_config.model_dump(mode="json"),
            current_worker="",
            worker_outputs={},
            re_run_count=0,
            max_re_runs=2,
            verdict="",
            errors=[],
        )

        with _mock.patch.object(WorkerContext, "__init__", _patched_init):
            asyncio.run(node_fn(state))

        checkpoint_events = [e for e in emitted if e["event_type"] == "checkpoint_written"]
        assert checkpoint_events, "No checkpoint_written events emitted"
        artifact_path = checkpoint_events[0]["data"]["artifact_path"]
        assert artifact_path.endswith("dummy_checkpoint.json"), (
            f"artifact_path '{artifact_path}' does not end with 'dummy_checkpoint.json'"
        )

    def test_no_checkpoint_when_disabled(self, tmp_path: Path) -> None:
        """When checkpoint=False, no checkpoint_written event should be emitted."""
        from launcher.orchestrator.graph_builder import WorkerEntry, _make_worker_node

        entry = WorkerEntry(
            name="dummy",
            input_schema="run_config.schema.json",
            output_schema="run_config.schema.json",
            checkpoint=False,
        )
        run_config = _make_run_config()
        emitted: list[dict[str, Any]] = []

        original_init = WorkerContext.__init__

        def _patched_init(self_ctx, *args, **kwargs):
            original_init(self_ctx, *args, **kwargs)
            real_emit = self_ctx.emit_event

            def _capturing_emit(event_type, data, **kw):
                emitted.append({"event_type": event_type, "data": data})
                real_emit(event_type, data, **kw)

            self_ctx.emit_event = _capturing_emit

        import unittest.mock as _mock

        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()

        worker = _DummyWorker()
        node_fn = _make_worker_node(entry, worker, schema_dir, ["dummy"])

        state: PipelineGraphState = PipelineGraphState(
            run_id="test-run-03",
            run_dir=str(tmp_path),
            config=run_config.model_dump(mode="json"),
            current_worker="",
            worker_outputs={},
            re_run_count=0,
            max_re_runs=2,
            verdict="",
            errors=[],
        )

        with _mock.patch.object(WorkerContext, "__init__", _patched_init):
            asyncio.run(node_fn(state))

        checkpoint_events = [e for e in emitted if e["event_type"] == "checkpoint_written"]
        assert len(checkpoint_events) == 0, (
            f"Expected no checkpoint_written events when checkpoint=False, got {len(checkpoint_events)}"
        )


# ---------------------------------------------------------------------------
# TC-HO-02: Heal bypass routing (H5.2)
# ---------------------------------------------------------------------------

_HEAL_PIPELINE_YAML = """\
version: "2.0"
defaults:
  max_re_runs: 0
  schema_dir: "specs/schemas"
pipeline:
  - worker: understand
    input_schema: "run_config.schema.json"
    output_schema: "run_config.schema.json"
    checkpoint: true
  - worker: planner
    input_schema: "run_config.schema.json"
    output_schema: "run_config.schema.json"
    checkpoint: true
  - worker: generate
    input_schema: "run_config.schema.json"
    output_schema: "run_config.schema.json"
    checkpoint: true
"""


class _CallTrackingWorker(WorkerContract):
    """Worker that records whether it was invoked."""

    def __init__(self, worker_name: str) -> None:
        self._name = worker_name
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def run(self, input_data: Any, context: WorkerContext) -> Any:
        self.call_count += 1
        from launcher.orchestrator.graph_builder import _DictProxy
        return _DictProxy.model_validate({"status": "ok"})

    async def self_review(self, output: Any) -> SelfReviewResult:
        return SelfReviewResult(passed=True)


def _build_heal_graph(tmp_path: Path) -> tuple[Any, dict[str, "_CallTrackingWorker"]]:
    """Build pipeline with understand+planner+generate workers; return (graph, workers)."""
    import json as _json
    from launcher.orchestrator.graph_builder import build_pipeline

    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text(_HEAL_PIPELINE_YAML, encoding="utf-8")

    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(exist_ok=True)

    # Minimal schema that accepts any object.
    minimal_schema: dict[str, Any] = {"type": "object"}
    (schema_dir / "run_config.schema.json").write_text(
        _json.dumps(minimal_schema), encoding="utf-8"
    )

    worker_map: dict[str, _CallTrackingWorker] = {
        "understand": _CallTrackingWorker("understand"),
        "planner": _CallTrackingWorker("planner"),
        "generate": _CallTrackingWorker("generate"),
    }
    graph = build_pipeline(cfg_file, worker_map, schema_dir=schema_dir)  # type: ignore[arg-type]
    return graph, worker_map


def _make_heal_state(
    run_dir: Path,
    run_config: RunConfig,
    *,
    heal_metadata: dict[str, Any] | None = None,
) -> "PipelineGraphState":
    return PipelineGraphState(
        run_id="heal-test-run",
        run_dir=str(run_dir),
        config=run_config.model_dump(mode="json"),
        current_worker="",
        worker_outputs={},
        re_run_count=0,
        max_re_runs=0,
        verdict="",
        errors=[],
        heal_metadata=heal_metadata or {},
    )


def _write_fake_checkpoints(run_dir: Path, workers: list[str]) -> None:
    """Write minimal JSON checkpoint files for the listed workers."""
    import json as _json
    for w in workers:
        (run_dir / f"{w}_checkpoint.json").write_text(
            _json.dumps({"status": "ok"}), encoding="utf-8"
        )


class TestHealBypassRouting:
    """__heal_router__ routes past Understand+Planner when responsible_worker == 'generate'."""

    def test_heal_routes_past_understand_when_responsible_generate(self, tmp_path: Path) -> None:
        """Understand worker is never called when heal bypass is active with checkpoints."""
        graph, workers = _build_heal_graph(tmp_path)
        _write_fake_checkpoints(tmp_path, ["understand", "planner"])
        run_config = _make_run_config()
        state = _make_heal_state(
            tmp_path, run_config, heal_metadata={"responsible_worker": "generate"}
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 0, (
            "Understand should be bypassed when heal_metadata.responsible_worker == 'generate'"
        )

    def test_heal_routes_past_planner_when_responsible_generate(self, tmp_path: Path) -> None:
        """Planner worker is never called when heal bypass is active with checkpoints."""
        graph, workers = _build_heal_graph(tmp_path)
        _write_fake_checkpoints(tmp_path, ["understand", "planner"])
        run_config = _make_run_config()
        state = _make_heal_state(
            tmp_path, run_config, heal_metadata={"responsible_worker": "generate"}
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["planner"].call_count == 0, (
            "Planner should be bypassed when heal_metadata.responsible_worker == 'generate'"
        )

    def test_worker_skipped_event_emitted_for_each_bypassed_worker(self, tmp_path: Path) -> None:
        """A worker_skipped event is emitted for understand and planner when bypassed."""
        import unittest.mock as _mock
        graph, workers = _build_heal_graph(tmp_path)
        _write_fake_checkpoints(tmp_path, ["understand", "planner"])
        run_config = _make_run_config()
        state = _make_heal_state(
            tmp_path, run_config, heal_metadata={"responsible_worker": "generate"}
        )

        emitted: list[dict[str, Any]] = []
        original_init = WorkerContext.__init__

        def _patched_init(self_ctx: WorkerContext, *args: Any, **kwargs: Any) -> None:
            original_init(self_ctx, *args, **kwargs)
            real_emit = self_ctx.emit_event

            def _capture(event_type: str, data: dict[str, Any], **kw: Any) -> None:
                emitted.append({"event_type": event_type, "data": data})
                real_emit(event_type, data, **kw)

            self_ctx.emit_event = _capture  # type: ignore[method-assign]

        with _mock.patch.object(WorkerContext, "__init__", _patched_init):
            asyncio.run(graph.ainvoke(state))

        skipped = [e for e in emitted if e["event_type"] == "worker_skipped"]
        skipped_names = {e["data"]["worker"] for e in skipped}
        assert "understand" in skipped_names, "worker_skipped missing for understand"
        assert "planner" in skipped_names, "worker_skipped missing for planner"

    def test_normal_run_unaffected_when_no_heal_metadata(self, tmp_path: Path) -> None:
        """All workers run normally when heal_metadata is absent (no bypass)."""
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        state = _make_heal_state(tmp_path, run_config, heal_metadata={})
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 1, "Understand should run in normal mode"
        assert workers["planner"].call_count == 1, "Planner should run in normal mode"
        assert workers["generate"].call_count == 1, "Generate should run in normal mode"


# ---------------------------------------------------------------------------
# TC-3869: Resume skip guard — workers with cached outputs are skipped
# ---------------------------------------------------------------------------


def _make_resume_state(
    run_dir: Path,
    run_config: RunConfig,
    *,
    worker_outputs: dict[str, Any] | None = None,
    re_run_count: int = 0,
) -> "PipelineGraphState":
    """Build a PipelineGraphState with pre-populated worker_outputs for resume tests."""
    return PipelineGraphState(
        run_id="resume-test-run",
        run_dir=str(run_dir),
        config=run_config.model_dump(mode="json"),
        current_worker="",
        worker_outputs=worker_outputs or {},
        re_run_count=re_run_count,
        max_re_runs=0,
        verdict="",
        errors=[],
        heal_metadata={},
    )


class TestResumeSkipCachedWorkers:
    """Skip guard: workers whose output is in worker_outputs are skipped on first pass (re_run_count==0)."""

    def test_worker_skipped_when_output_cached(self, tmp_path: Path) -> None:
        """Worker.run is NOT called when worker_outputs already has its output (re_run_count=0)."""
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        # Pre-populate understand output — simulates _build_resume_state loading a checkpoint.
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"understand": {"status": "cached"}},
            re_run_count=0,
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 0, (
            "Understand should be skipped when output is already in worker_outputs"
        )

    def test_worker_skipped_event_emitted_for_cached_worker(self, tmp_path: Path) -> None:
        """worker_skipped event is emitted with reason='resume_checkpoint' for a cached worker."""
        import unittest.mock as _mock
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"understand": {"status": "cached"}},
            re_run_count=0,
        )

        emitted: list[dict[str, Any]] = []
        original_init = WorkerContext.__init__

        def _patched_init(self_ctx: WorkerContext, *args: Any, **kwargs: Any) -> None:
            original_init(self_ctx, *args, **kwargs)
            real_emit = self_ctx.emit_event

            def _capture(event_type: str, data: dict[str, Any], **kw: Any) -> None:
                emitted.append({"event_type": event_type, "data": data})
                real_emit(event_type, data, **kw)

            self_ctx.emit_event = _capture  # type: ignore[method-assign]

        with _mock.patch.object(WorkerContext, "__init__", _patched_init):
            asyncio.run(graph.ainvoke(state))

        resume_skipped = [
            e for e in emitted
            if e["event_type"] == "worker_skipped"
            and e["data"].get("reason") == "resume_checkpoint"
        ]
        assert len(resume_skipped) >= 1, "Expected at least one worker_skipped(resume_checkpoint) event"
        skipped_workers = {e["data"]["worker"] for e in resume_skipped}
        assert "understand" in skipped_workers, "worker_skipped event missing for 'understand'"

    def test_worker_runs_when_output_not_cached(self, tmp_path: Path) -> None:
        """Worker.run IS called when worker_outputs is empty."""
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        state = _make_resume_state(tmp_path, run_config, worker_outputs={}, re_run_count=0)
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 1, (
            "Understand should run when worker_outputs is empty"
        )

    def test_worker_runs_on_rerun_despite_cached_output(self, tmp_path: Path) -> None:
        """When re_run_count > 0, skip guard is disabled — workers must run even if output is cached.

        This prevents a stale first-pass output in worker_outputs from blocking the re-run target
        (e.g. generate) from producing fresh output when evaluate triggers a re-run loop.
        """
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        # Same setup as test_worker_skipped_when_output_cached but re_run_count=1.
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"understand": {"status": "stale-first-pass"}},
            re_run_count=1,
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 1, (
            "Understand must NOT be skipped when re_run_count > 0 — "
            "stale first-pass output in worker_outputs must not block re-runs"
        )

    def test_partial_resume_cached_first_downstream_runs(self, tmp_path: Path) -> None:
        """understand is skipped (cached), planner+generate run and complete normally."""
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        # Only understand is cached; planner and generate must run.
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"understand": {"status": "cached"}},
            re_run_count=0,
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 0, "Understand should be skipped (cached)"
        assert workers["planner"].call_count == 1, "Planner should run (not cached)"
        assert workers["generate"].call_count == 1, "Generate should run (not cached)"

    # -- TC-SR-01 regression: None-value must NOT trigger skip ----------------

    def test_none_value_in_worker_outputs_does_not_skip(self, tmp_path: Path) -> None:
        """A None value stored under a worker key must NOT trigger the skip guard.

        Regression for SR-01: key existence alone is insufficient — the checkpoint
        value must be non-None to be considered valid for skip.
        """
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"understand": None},
            re_run_count=0,
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 1, (
            "A None cached value must not skip the worker — only non-None outputs are trusted"
        )

    # -- TC-SR-02: all-cached and first-worker coverage -----------------------

    def test_all_workers_cached_none_run(self, tmp_path: Path) -> None:
        """When all workers have cached outputs, none of them call worker.run()."""
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={
                "understand": {"status": "cached"},
                "planner": {"status": "cached"},
                "generate": {"status": "cached"},
            },
            re_run_count=0,
        )
        asyncio.run(graph.ainvoke(state))
        assert workers["understand"].call_count == 0, "Understand should be skipped (all cached)"
        assert workers["planner"].call_count == 0, "Planner should be skipped (all cached)"
        assert workers["generate"].call_count == 0, "Generate should be skipped (all cached)"

    def test_first_worker_in_pipeline_skipped_when_cached(self, tmp_path: Path) -> None:
        """active_workers[0] is skipped when its output is in worker_outputs.

        Covers the path where the very first node (no __heal_router__) is the skip target,
        using the single-worker dummy pipeline.
        """
        import json as _json
        from launcher.orchestrator.graph_builder import build_pipeline

        _single_yaml = """\
version: "2.0"
defaults:
  max_re_runs: 0
  schema_dir: "specs/schemas"
pipeline:
  - worker: dummy
    input_schema: "run_config.schema.json"
    output_schema: "run_config.schema.json"
    checkpoint: true
"""
        cfg_file = tmp_path / "pipeline.yaml"
        cfg_file.write_text(_single_yaml, encoding="utf-8")
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir(exist_ok=True)
        (schema_dir / "run_config.schema.json").write_text(
            _json.dumps({"type": "object"}), encoding="utf-8"
        )
        dummy_worker = _CallTrackingWorker("dummy")
        graph = build_pipeline(cfg_file, {"dummy": dummy_worker}, schema_dir=schema_dir)

        run_config = _make_run_config()
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"dummy": {"status": "cached"}},
            re_run_count=0,
        )
        asyncio.run(graph.ainvoke(state))
        assert dummy_worker.call_count == 0, (
            "active_workers[0] must be skipped when its output is already cached"
        )

    # -- TC-SR-03: worker_skipped event must carry re_run_count ---------------

    def test_worker_skipped_event_carries_re_run_count(self, tmp_path: Path) -> None:
        """worker_skipped event payload must include re_run_count for telemetry correlation."""
        import unittest.mock as _mock
        graph, workers = _build_heal_graph(tmp_path)
        run_config = _make_run_config()
        state = _make_resume_state(
            tmp_path, run_config,
            worker_outputs={"understand": {"status": "cached"}},
            re_run_count=0,
        )

        emitted: list[dict[str, Any]] = []
        original_init = WorkerContext.__init__

        def _patched_init(self_ctx: WorkerContext, *args: Any, **kwargs: Any) -> None:
            original_init(self_ctx, *args, **kwargs)
            real_emit = self_ctx.emit_event

            def _capture(event_type: str, data: dict[str, Any], **kw: Any) -> None:
                emitted.append({"event_type": event_type, "data": data})
                real_emit(event_type, data, **kw)

            self_ctx.emit_event = _capture  # type: ignore[method-assign]

        with _mock.patch.object(WorkerContext, "__init__", _patched_init):
            asyncio.run(graph.ainvoke(state))

        resume_skipped = [
            e for e in emitted
            if e["event_type"] == "worker_skipped"
            and e["data"].get("reason") == "resume_checkpoint"
        ]
        assert resume_skipped, "Expected at least one resume_checkpoint worker_skipped event"
        event_data = resume_skipped[0]["data"]
        assert "re_run_count" in event_data, (
            "worker_skipped event must include re_run_count for telemetry correlation"
        )
        assert event_data["re_run_count"] == 0, (
            f"Expected re_run_count=0 in event, got {event_data['re_run_count']}"
        )

"""E2E tests for the pipeline graph builder and routing.

Tests the graph construction, verdict propagation, re-run routing,
and worker discovery without requiring network or LLM access.
Uses mock workers that implement WorkerContract.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from launcher.models.base import LauncherBaseModel
from launcher.models.run_config import RunConfig
from launcher.orchestrator.graph_builder import (
    PipelineTopology,
    WorkerEntry,
    _DictProxy,
    _make_should_re_run,
    _verdict_gate,
    build_pipeline,
    load_pipeline_config,
)

# Create a test-local _should_re_run with max_re_runs=2 (matching old default)
# to preserve existing test expectations.
_should_re_run = _make_should_re_run(max_re_runs=2)
from launcher.orchestrator.state import PipelineGraphState
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext, WorkerContract


# ---------------------------------------------------------------------------
# Mock workers
# ---------------------------------------------------------------------------


class MockWorker(WorkerContract):
    """A mock worker that returns configurable output."""

    def __init__(self, name: str, output: dict[str, Any] | None = None):
        self._name = name
        self._output = output or {}

    @property
    def name(self) -> str:
        return self._name

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> LauncherBaseModel:
        proxy = _DictProxy.model_validate(self._output)
        return proxy

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        return SelfReviewResult(passed=True)


class FailingWorker(WorkerContract):
    """A worker that always raises."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> LauncherBaseModel:
        raise RuntimeError(f"{self._name} failed")

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        return SelfReviewResult(passed=True)


# ---------------------------------------------------------------------------
# Pipeline config loading
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    def test_load_pipeline_config(self):
        config_path = Path("configs/pipeline.yaml")
        if not config_path.exists():
            pytest.skip("pipeline.yaml not found")
        topology = load_pipeline_config(config_path)
        assert topology.version == "2.0"
        assert len(topology.workers) == 6
        names = [w.name for w in topology.workers]
        assert names == ["intake", "understand", "planner", "generate", "evaluate", "publish"]

    def test_evaluate_has_rerun_targets(self):
        config_path = Path("configs/pipeline.yaml")
        if not config_path.exists():
            pytest.skip("pipeline.yaml not found")
        topology = load_pipeline_config(config_path)
        evaluate = next(w for w in topology.workers if w.name == "evaluate")
        assert evaluate.re_run_targets == ["generate"]  # TC-3919: understand removed, advisor handles routing
        assert evaluate.max_re_runs == 2  # TC-3919: enabled with __advisor__ node

    def test_publish_requires_verdict(self):
        config_path = Path("configs/pipeline.yaml")
        if not config_path.exists():
            pytest.skip("pipeline.yaml not found")
        topology = load_pipeline_config(config_path)
        publish = next(w for w in topology.workers if w.name == "publish")
        assert publish.requires_verdict == "GO"


# ---------------------------------------------------------------------------
# Conditional routing functions
# ---------------------------------------------------------------------------


class TestRouting:
    def _make_state(self, **overrides) -> PipelineGraphState:
        base: PipelineGraphState = {
            "run_id": "test-001",
            "run_dir": "/tmp/test",
            "config": {},
            "current_worker": "evaluate",
            "worker_outputs": {},
            "re_run_count": 0,
            "max_re_runs": 2,
            "verdict": "",
            "errors": [],
        }
        base.update(overrides)  # type: ignore[typeddict-item]
        return base

    def test_go_verdict_routes_to_publish(self):
        state = self._make_state(verdict="GO")
        assert _should_re_run(state) == "publish"

    def test_nogo_first_attempt_routes_to_rerun(self):
        state = self._make_state(verdict="NO_GO", re_run_count=0)
        assert _should_re_run(state) == "__re_run__"

    def test_nogo_exhausted_routes_to_end(self):
        from langgraph.graph import END
        state = self._make_state(verdict="NO_GO", re_run_count=2, max_re_runs=2)
        assert _should_re_run(state) == END

    def test_empty_verdict_routes_to_end(self):
        from langgraph.graph import END
        state = self._make_state(verdict="")
        assert _should_re_run(state) == END

    def test_verdict_gate_go(self):
        state = self._make_state(verdict="GO")
        assert _verdict_gate(state) == "publish"

    def test_verdict_gate_nogo(self):
        from langgraph.graph import END
        state = self._make_state(verdict="NO_GO")
        assert _verdict_gate(state) == END


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------


class TestGraphBuilding:
    def test_build_with_all_workers(self, tmp_path):
        """Build a graph with all 6 mandatory workers."""
        config_path = Path("configs/pipeline.yaml")
        if not config_path.exists():
            pytest.skip("pipeline.yaml not found")

        workers = {
            "intake": MockWorker("intake", {"family": "cells", "platform": "python"}),
            "understand": MockWorker("understand", {"claims": []}),
            "planner": MockWorker("planner", {"pages": [], "claim_assignment_index": {}}),
            "generate": MockWorker("generate", {"pages": []}),
            "evaluate": MockWorker("evaluate", {"verdict": "GO", "pages": []}),
            "publish": MockWorker("publish", {"patches": []}),
        }

        graph = build_pipeline(config_path, workers)
        assert graph is not None

    def test_missing_required_worker_raises(self, tmp_path):
        config_path = Path("configs/pipeline.yaml")
        if not config_path.exists():
            pytest.skip("pipeline.yaml not found")

        # Only provide intake — missing understand, generate, evaluate, publish
        workers = {
            "intake": MockWorker("intake"),
        }

        with pytest.raises(ValueError, match="requires worker"):
            build_pipeline(config_path, workers)


# ---------------------------------------------------------------------------
# stop_after support
# ---------------------------------------------------------------------------


def _all_mock_workers() -> dict[str, MockWorker]:
    """Return a full set of mock workers for all 6 pipeline stages."""
    return {
        "intake": MockWorker("intake", {"family": "cells", "platform": "python"}),
        "understand": MockWorker("understand", {"claims": [], "snippets": []}),
        "planner": MockWorker("planner", {"pages": [], "claim_assignment_index": {}}),
        "generate": MockWorker("generate", {"pages": []}),
        "evaluate": MockWorker("evaluate", {"verdict": "GO", "pages": []}),
        "publish": MockWorker("publish", {"patches": []}),
    }


class TestStopAfter:
    """Tests for build_pipeline stop_after parameter."""

    def _skip_if_no_config(self):
        config_path = Path("configs/pipeline.yaml")
        if not config_path.exists():
            pytest.skip("pipeline.yaml not found")
        return config_path

    def test_stop_after_understand_builds_graph(self):
        config_path = self._skip_if_no_config()
        workers = _all_mock_workers()
        graph = build_pipeline(config_path, workers, stop_after="understand")
        assert graph is not None

    def test_stop_after_intake_builds_graph(self):
        config_path = self._skip_if_no_config()
        workers = _all_mock_workers()
        graph = build_pipeline(config_path, workers, stop_after="intake")
        assert graph is not None

    def test_stop_after_none_builds_full_graph(self):
        """Regression: stop_after=None should build the complete pipeline."""
        config_path = self._skip_if_no_config()
        workers = _all_mock_workers()
        graph = build_pipeline(config_path, workers, stop_after=None)
        assert graph is not None

    def test_stop_after_invalid_raises(self):
        config_path = self._skip_if_no_config()
        workers = _all_mock_workers()
        with pytest.raises(ValueError, match="not a valid worker"):
            build_pipeline(config_path, workers, stop_after="nonexistent")

    def test_stop_after_truncates_topology(self):
        """Verify truncation produces correct worker count."""
        config_path = self._skip_if_no_config()
        topology = load_pipeline_config(config_path)
        # Full pipeline has 6 workers
        assert len(topology.workers) == 6

        # build_pipeline with stop_after="understand" should not require
        # workers beyond understand — only intake+understand needed
        workers = {
            "intake": MockWorker("intake"),
            "understand": MockWorker("understand"),
        }
        graph = build_pipeline(config_path, workers, stop_after="understand")
        assert graph is not None


# ---------------------------------------------------------------------------
# Worker discovery
# ---------------------------------------------------------------------------


class TestWorkerDiscovery:
    def test_all_workers_discoverable(self):
        """All 5 worker modules should be importable and produce workers."""
        from launcher.orchestrator.run_loop import _discover_workers
        workers = _discover_workers()
        # At minimum we should get understand, generate, evaluate, publish
        assert "understand" in workers
        assert "generate" in workers
        assert "evaluate" in workers
        assert "publish" in workers

    def test_workers_have_correct_names(self):
        from launcher.orchestrator.run_loop import _discover_workers
        workers = _discover_workers()
        for name, worker in workers.items():
            assert worker.name == name


# ---------------------------------------------------------------------------
# DictProxy
# ---------------------------------------------------------------------------


class TestDictProxy:
    def test_from_dict(self):
        data = {"foo": "bar", "count": 42}
        proxy = _DictProxy.model_validate(data)
        assert proxy.foo == "bar"  # type: ignore[attr-defined]
        assert proxy.count == 42  # type: ignore[attr-defined]

    def test_empty_dict(self):
        proxy = _DictProxy.model_validate({})
        assert isinstance(proxy, _DictProxy)


# ---------------------------------------------------------------------------
# Verdict propagation in graph node
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------


class TestRunResult:
    def test_run_result_with_none_report(self):
        from launcher.orchestrator.run_loop import RunResult
        result = RunResult(
            report=None,
            worker_outputs={"intake": {"family": "cells"}},
            stopped_after="intake",
            run_dir="/tmp/test",
        )
        assert result.report is None
        assert result.stopped_after == "intake"
        assert "intake" in result.worker_outputs

    def test_run_result_with_report(self):
        from launcher.models.evaluation import EvaluationReport, Verdict
        from launcher.orchestrator.run_loop import RunResult
        report = EvaluationReport(verdict=Verdict.GO)
        result = RunResult(report=report, worker_outputs={})
        assert result.report is not None
        assert result.report.verdict == Verdict.GO


# ---------------------------------------------------------------------------
# Worker summary display
# ---------------------------------------------------------------------------


class TestWorkerSummary:
    def test_intake_summary(self, capsys):
        from launcher.cli.main import _print_worker_summary
        _print_worker_summary("intake", {
            "family": "cells",
            "platform": "python",
            "display_name": "Aspose.Cells",
            "canonical_import": "aspose.cells",
            "launch_tier": "full",
            "repo_sha": "abc123def456",
        })
        out = capsys.readouterr().out
        assert "INTAKE" in out
        assert "cells" in out
        assert "abc123def456" in out

    def test_intake_summary_none_sha(self, capsys):
        """None repo_sha should not crash."""
        from launcher.cli.main import _print_worker_summary
        _print_worker_summary("intake", {
            "family": "cells",
            "platform": "python",
            "display_name": "X",
            "canonical_import": "x",
            "launch_tier": "core",
            "repo_sha": None,
        })
        out = capsys.readouterr().out
        assert "INTAKE" in out
        assert "?" in out

    def test_understand_summary(self, capsys):
        from launcher.cli.main import _print_worker_summary
        _print_worker_summary("understand", {
            "claims": [{"id": "c1"}],
            "snippets": [{"code": "x"}],
            "pages": [{"mandatory": True}, {"mandatory": False}],
            "richness_tier": {"tier": "A", "score": 85},
            "api_surface": {"public_classes": ["Foo", "Bar"]},
            "repo": {"content_files_read": 10, "content_budget_used": 2048},
        })
        out = capsys.readouterr().out
        assert "UNDERSTAND" in out
        assert "1" in out  # 1 claim
        assert "2 public classes" in out

    def test_generate_summary(self, capsys):
        from launcher.cli.main import _print_worker_summary
        _print_worker_summary("generate", {
            "pages": [{"slug": "a"}, {"slug": "b"}],
            "generation_stats": {"llm_calls": 5, "fallback_count": 1, "duration_seconds": 12.3},
        })
        out = capsys.readouterr().out
        assert "GENERATE" in out
        assert "LLM calls: 5" in out
        assert "Fallbacks: 1" in out
        assert "12.3s" in out

    def test_publish_summary(self, capsys):
        from launcher.cli.main import _print_worker_summary
        _print_worker_summary("publish", {
            "patches": [{"file_path": "a.md"}, {"file_path": "b.md"}],
            "pr": {"url": "https://github.com/x/y/pull/1", "state": "draft"},
        })
        out = capsys.readouterr().out
        assert "PUBLISH" in out
        assert "Patches:   2" in out
        assert "https://github.com/x/y/pull/1" in out

    def test_understand_summary_none_budget(self, capsys):
        """None content_budget_used should not crash."""
        from launcher.cli.main import _print_worker_summary
        _print_worker_summary("understand", {
            "claims": [], "snippets": [], "pages": [],
            "richness_tier": {}, "api_surface": {},
            "repo": {"content_files_read": 0, "content_budget_used": None},
        })
        out = capsys.readouterr().out
        assert "UNDERSTAND" in out
        assert "0.0 KB" in out


# ---------------------------------------------------------------------------
# Verdict propagation in graph node
# ---------------------------------------------------------------------------


class TestVerdictPropagation:
    def test_evaluate_output_contains_verdict(self):
        """Verify the evaluate worker output dict includes verdict."""
        from launcher.models.evaluation import EvaluationReport, Verdict
        report = EvaluationReport(verdict=Verdict.GO)
        output_dict = report.model_dump(mode="json")
        assert output_dict["verdict"] == "GO"

    def test_nogo_report_contains_verdict(self):
        from launcher.models.evaluation import EvaluationReport, Verdict
        report = EvaluationReport(verdict=Verdict.NO_GO)
        output_dict = report.model_dump(mode="json")
        assert output_dict["verdict"] == "NO_GO"


# ---------------------------------------------------------------------------
# TC-3774-H3: --resume-from + --stop-after conflict guard (CLI level)
# ---------------------------------------------------------------------------


class TestResumeStopConflict:
    """CLI-level tests for --resume-from / --stop-after ordering validation."""

    def test_resume_after_stop_rejected(self, tmp_path):
        """--resume-from after --stop-after in pipeline order should fail."""
        from typer.testing import CliRunner
        from launcher.cli.main import app

        config = tmp_path / "test.yaml"
        config.write_text(
            "family: cells\nplatform: python\nrepo_url: https://github.com/x/y\n"
        )

        runner = CliRunner()
        result = runner.invoke(app, [
            "run", str(config),
            "--resume-from", "generate",
            "--stop-after", "understand",
        ])
        assert result.exit_code == 1
        assert "must come before" in result.output

    def test_resume_equals_stop_rejected(self, tmp_path):
        """--resume-from same as --stop-after should fail."""
        from typer.testing import CliRunner
        from launcher.cli.main import app

        config = tmp_path / "test.yaml"
        config.write_text(
            "family: cells\nplatform: python\nrepo_url: https://github.com/x/y\n"
        )

        runner = CliRunner()
        result = runner.invoke(app, [
            "run", str(config),
            "--resume-from", "understand",
            "--stop-after", "understand",
        ])
        assert result.exit_code == 1
        assert "must come before" in result.output

    def test_invalid_stop_after_rejected(self, tmp_path):
        """Invalid --stop-after value should fail."""
        from typer.testing import CliRunner
        from launcher.cli.main import app

        config = tmp_path / "test.yaml"
        config.write_text(
            "family: cells\nplatform: python\nrepo_url: https://github.com/x/y\n"
        )

        runner = CliRunner()
        result = runner.invoke(app, [
            "run", str(config),
            "--stop-after", "nonexistent",
        ])
        assert result.exit_code == 1
        assert "must be one of" in result.output

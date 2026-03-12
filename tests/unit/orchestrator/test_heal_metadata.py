"""Unit tests for heal_metadata plumbing (TC-3841).

Verifies that heal directives flow from PipelineGraphState → WorkerContext
through the orchestrator boundary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from launcher.models.run_config import LLMConfig, LLMEndpoint, RunConfig
from launcher.orchestrator.state import PipelineGraphState
from launcher.orchestrator.worker_contract import WorkerContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_run_config() -> RunConfig:
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=LLMConfig(
            primary=LLMEndpoint(base_url="http://localhost:11434/v1", model="test-model"),
        ),
    )


def _make_context(tmp_path: Path, heal_metadata: dict[str, Any] | None = None) -> WorkerContext:
    config = _minimal_run_config()
    kwargs: dict[str, Any] = dict(
        run_id="test-run",
        run_dir=tmp_path,
        config=config,
    )
    if heal_metadata is not None:
        kwargs["heal_metadata"] = heal_metadata
    return WorkerContext(**kwargs)


# ---------------------------------------------------------------------------
# WorkerContext tests
# ---------------------------------------------------------------------------


class TestWorkerContextHealMetadata:
    def test_explicit_heal_metadata_stored(self, tmp_path: Path) -> None:
        """WorkerContext(heal_metadata={"x": 1}).heal_metadata must equal {"x": 1}."""
        ctx = _make_context(tmp_path, heal_metadata={"x": 1})
        assert ctx.heal_metadata == {"x": 1}

    def test_default_heal_metadata_is_empty_dict(self, tmp_path: Path) -> None:
        """WorkerContext() without heal_metadata must return {}."""
        ctx = _make_context(tmp_path)
        assert ctx.heal_metadata == {}

    def test_none_heal_metadata_coerced_to_empty(self, tmp_path: Path) -> None:
        """Passing heal_metadata=None must produce {} (not None)."""
        ctx = _make_context(tmp_path, heal_metadata=None)
        assert ctx.heal_metadata == {}
        assert isinstance(ctx.heal_metadata, dict)

    def test_heal_metadata_is_read_only_view(self, tmp_path: Path) -> None:
        """Mutating the returned dict must not affect the context's stored metadata."""
        original = {"worker": "generate", "re_run": 2}
        ctx = _make_context(tmp_path, heal_metadata=original)
        returned = ctx.heal_metadata
        assert returned == original

    def test_complex_heal_metadata_preserved(self, tmp_path: Path) -> None:
        """Nested JSON-serializable heal metadata must be preserved intact."""
        metadata = {
            "target_worker": "generate",
            "affected_pages": ["page-a", "page-b"],
            "instructions": {"tone": "technical", "max_words": 500},
        }
        ctx = _make_context(tmp_path, heal_metadata=metadata)
        assert ctx.heal_metadata == metadata


# ---------------------------------------------------------------------------
# PipelineGraphState tests
# ---------------------------------------------------------------------------


class TestPipelineGraphStateHealMetadata:
    def test_state_can_be_constructed_with_heal_metadata(self) -> None:
        """PipelineGraphState must accept heal_metadata={} without error."""
        state = PipelineGraphState(
            run_id="test-run",
            run_dir="/tmp/test-run",
            config={},
            current_worker="",
            worker_outputs={},
            re_run_count=0,
            max_re_runs=2,
            verdict="",
            errors=[],
            heal_metadata={},
        )
        assert state["heal_metadata"] == {}

    def test_state_heal_metadata_with_directives(self) -> None:
        """heal_metadata with actual directives must be stored and retrievable."""
        directives = {"target_worker": "generate", "re_run_id": "run-abc"}
        state = PipelineGraphState(
            run_id="test-run",
            run_dir="/tmp/test-run",
            config={},
            current_worker="",
            worker_outputs={},
            re_run_count=0,
            max_re_runs=2,
            verdict="",
            errors=[],
            heal_metadata=directives,
        )
        assert state["heal_metadata"] == directives


# ---------------------------------------------------------------------------
# _build_resume_state integration
# ---------------------------------------------------------------------------


class TestBuildResumeStateHealMetadata:
    def test_build_resume_state_base_fields_present(self, tmp_path: Path) -> None:
        """_build_resume_state() must return a valid state with all base fields."""
        from launcher.orchestrator.run_loop import _build_resume_state

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()
        config = _minimal_run_config()

        state = _build_resume_state(
            run_dir=run_dir,
            resume_from="intake",
            run_id="test-run",
            config=config,
        )

        # Base fields always present
        assert state["run_id"] == "test-run"
        assert state["run_dir"] == str(run_dir)
        assert state["worker_outputs"] == {}
        assert state["errors"] == []

    def test_heal_metadata_in_state_defaults_to_empty(self, tmp_path: Path) -> None:
        """heal_metadata in graph state defaults to empty dict when not in heal mode."""
        from launcher.orchestrator.run_loop import _build_resume_state

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()
        config = _minimal_run_config()

        state = _build_resume_state(
            run_dir=run_dir,
            resume_from="intake",
            run_id="test-run",
            config=config,
        )

        # heal_metadata should be present and empty (added in TC-3841)
        heal_meta = state.get("heal_metadata", {})
        assert heal_meta == {}, (
            f"Expected heal_metadata={{}}, got {heal_meta!r}"
        )

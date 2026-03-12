"""Unit tests for run_loop resume integrity check (TC-3840)."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import pytest

from launcher.models.run_config import LLMConfig, LLMEndpoint, RunConfig
from launcher.util.errors import WorkerError


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


def _write_checkpoint_json(run_dir: Path, worker: str, content: dict) -> Path:
    """Write a fake worker checkpoint JSON and return the path."""
    cp_file = run_dir / f"{worker}_checkpoint.json"
    cp_file.write_text(json.dumps(content), encoding="utf-8")
    return cp_file


def _write_worker_checkpoint_metadata(run_dir: Path, worker: str, artifact_path: Path) -> str:
    """Create a WorkerCheckpoint metadata file, return the checkpoint_id."""
    from launcher.resilience.checkpoint import write_worker_checkpoint
    wcp = write_worker_checkpoint(run_dir=run_dir, worker=worker, artifact_path=artifact_path)
    return wcp.checkpoint_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildResumeStateIntegrity:
    """_build_resume_state() must perform SHA-256 integrity check on artifacts."""

    def test_matching_hash_no_warning(self, tmp_path: Path, caplog) -> None:
        """When the stored hash matches the current artifact, no warning is emitted."""
        from launcher.orchestrator.run_loop import _build_resume_state

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()

        content = {"family": "cells", "platform": "python"}
        artifact_path = _write_checkpoint_json(run_dir, "intake", content)

        # Write matching WorkerCheckpoint metadata
        _write_worker_checkpoint_metadata(run_dir, "intake", artifact_path)

        config = _make_run_config()

        with caplog.at_level(logging.WARNING, logger="launcher.orchestrator.run_loop"):
            state = _build_resume_state(
                run_dir=run_dir,
                resume_from="understand",
                run_id="test-run",
                config=config,
            )

        # 'intake' should be loaded
        assert "intake" in state["worker_outputs"]
        # No warning about manual editing
        warning_msgs = [
            r.message for r in caplog.records
            if r.levelno == logging.WARNING and "manually edited" in r.message
        ]
        assert len(warning_msgs) == 0, (
            f"Unexpected warning(s) for matching hash: {warning_msgs}"
        )

    def test_mismatched_hash_emits_warning(self, tmp_path: Path, caplog) -> None:
        """When the artifact has been edited after checkpoint, a WARNING is logged."""
        from launcher.orchestrator.run_loop import _build_resume_state

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()

        original_content = {"family": "cells", "platform": "python"}
        artifact_path = _write_checkpoint_json(run_dir, "intake", original_content)

        # Write WorkerCheckpoint for the original content
        _write_worker_checkpoint_metadata(run_dir, "intake", artifact_path)

        # Now "manually edit" the artifact (change content after checkpoint was written)
        modified_content = {"family": "cells", "platform": "java", "EDITED": True}
        artifact_path.write_text(json.dumps(modified_content), encoding="utf-8")

        config = _make_run_config()

        with caplog.at_level(logging.WARNING, logger="launcher.orchestrator.run_loop"):
            state = _build_resume_state(
                run_dir=run_dir,
                resume_from="understand",
                run_id="test-run",
                config=config,
            )

        warning_msgs = [
            r.message for r in caplog.records
            if r.levelno == logging.WARNING and "manually edited" in r.message
        ]
        assert len(warning_msgs) == 1, (
            f"Expected 1 warning about manual edit, got {len(warning_msgs)}: {warning_msgs}"
        )
        assert "intake" in warning_msgs[0], (
            f"Warning should mention worker name 'intake': {warning_msgs[0]}"
        )

    def test_no_worker_checkpoint_file_no_crash(self, tmp_path: Path) -> None:
        """When no WorkerCheckpoint metadata exists, _build_resume_state must not crash."""
        from launcher.orchestrator.run_loop import _build_resume_state

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()

        # Write checkpoint JSON but NO WorkerCheckpoint metadata
        content = {"family": "cells", "platform": "python"}
        _write_checkpoint_json(run_dir, "intake", content)
        # worker_checkpoints/ dir does NOT exist

        config = _make_run_config()

        # Must not raise
        state = _build_resume_state(
            run_dir=run_dir,
            resume_from="understand",
            run_id="test-run",
            config=config,
        )

        assert "intake" in state["worker_outputs"]

    def test_resume_state_has_heal_metadata_field(self, tmp_path: Path) -> None:
        """_build_resume_state() result is a valid PipelineGraphState (no KeyError on known fields)."""
        from launcher.orchestrator.run_loop import _build_resume_state

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()

        config = _make_run_config()
        state = _build_resume_state(
            run_dir=run_dir,
            resume_from="intake",
            run_id="test-run",
            config=config,
        )

        # Basic fields must be present
        assert state["run_id"] == "test-run"
        assert state["run_dir"] == str(run_dir)
        assert state["worker_outputs"] == {}
        assert state["errors"] == []


# ---------------------------------------------------------------------------
# TC-SR-07 — resume_from validation in execute_run()
# ---------------------------------------------------------------------------


class TestResumeFromValidation:
    """execute_run() must raise ValueError for unknown resume_from values (TC-SR-07)."""

    def _minimal_execute_run_kwargs(self, tmp_path: Path) -> dict:
        """Minimal kwargs that satisfy execute_run() without starting a real pipeline."""
        from unittest.mock import MagicMock, patch, AsyncMock
        return dict(
            config=_make_run_config(),
            runs_root=tmp_path,
        )

    def test_invalid_resume_from_raises_value_error(self, tmp_path: Path) -> None:
        """resume_from='nonexistent' must raise ValueError with the invalid value in message."""
        from unittest.mock import patch, MagicMock, AsyncMock
        from launcher.orchestrator.run_loop import execute_run

        with patch("launcher.orchestrator.run_loop.build_pipeline") as mock_build, \
             patch("launcher.orchestrator.run_loop.discover_latest_run") as mock_discover:
            mock_build.return_value = MagicMock()
            mock_discover.return_value = None

            import pytest as _pytest
            with _pytest.raises(ValueError, match="nonexistent"):
                import asyncio
                asyncio.run(execute_run(
                    config=_make_run_config(),
                    runs_root=tmp_path,
                    resume_from="nonexistent",
                    run_id="test-run",
                ))

    def test_valid_resume_from_does_not_raise_at_validation(self, tmp_path: Path) -> None:
        """resume_from='generate' (a valid worker name) must pass the validation step."""
        from unittest.mock import patch, MagicMock, AsyncMock
        from launcher.orchestrator.run_loop import execute_run

        with patch("launcher.orchestrator.run_loop.build_pipeline") as mock_build, \
             patch("launcher.orchestrator.run_loop._build_resume_state") as mock_resume, \
             patch("launcher.orchestrator.run_loop.ArtifactStore"), \
             patch("launcher.orchestrator.run_loop.RunLayout"):
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={
                "worker_outputs": {},
                "errors": [],
                "current_worker": "",
                "run_id": "test-run",
                "run_dir": str(tmp_path),
                "config": _make_run_config().model_dump(mode="json"),
            })
            mock_build.return_value = mock_graph
            mock_resume.return_value = {
                "run_id": "test-run",
                "run_dir": str(tmp_path),
                "config": _make_run_config().model_dump(mode="json"),
                "worker_outputs": {},
                "errors": [],
                "current_worker": "",
                "re_run_count": 0,
                "heal_metadata": {},
            }

            # Should not raise ValueError at the validation step
            # (may fail later due to missing infrastructure, but not on validation)
            try:
                import asyncio
                asyncio.run(execute_run(
                    config=_make_run_config(),
                    runs_root=tmp_path,
                    resume_from="generate",
                    run_id="test-run",
                ))
            except ValueError as exc:
                # Fail only if the ValueError mentions validation (not other causes)
                assert "not a known pipeline worker" not in str(exc), (
                    f"Validation should not reject 'generate'; got: {exc}"
                )

    def test_wrong_case_resume_from_raises_value_error(self, tmp_path: Path) -> None:
        """resume_from='Generate' (wrong case) must raise ValueError — validation is case-sensitive."""
        from unittest.mock import patch, MagicMock, AsyncMock
        from launcher.orchestrator.run_loop import execute_run

        with patch("launcher.orchestrator.run_loop.build_pipeline") as mock_build, \
             patch("launcher.orchestrator.run_loop.discover_latest_run") as mock_discover:
            mock_build.return_value = MagicMock()
            mock_discover.return_value = None

            import pytest as _pytest
            with _pytest.raises(ValueError, match="Generate"):
                import asyncio
                asyncio.run(execute_run(
                    config=_make_run_config(),
                    runs_root=tmp_path,
                    resume_from="Generate",
                    run_id="test-run",
                ))


# ---------------------------------------------------------------------------
# TC-HO-10 — _assert_understand_checkpoint unit tests
# ---------------------------------------------------------------------------


class TestUnderstandCheckpointGuard:
    """_assert_understand_checkpoint() must fail fast when the checkpoint is missing."""

    def test_missing_checkpoint_raises_worker_error(self, tmp_path: Path) -> None:
        """Missing understand_checkpoint.json with active generate/evaluate workers raises."""
        from launcher.orchestrator.run_loop import _assert_understand_checkpoint

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()
        # No understand_checkpoint.json written

        workers = {"generate": object(), "evaluate": object()}
        with pytest.raises(WorkerError, match="understand_checkpoint"):
            _assert_understand_checkpoint(run_dir, workers)

    def test_valid_checkpoint_passes(self, tmp_path: Path) -> None:
        """When understand_checkpoint.json is valid JSON, no error is raised."""
        from launcher.orchestrator.run_loop import _assert_understand_checkpoint

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()
        (run_dir / "understand_checkpoint.json").write_text(
            '{"claims": [], "api_surface": {}}', encoding="utf-8"
        )

        workers = {"generate": object(), "evaluate": object()}
        # Must not raise
        _assert_understand_checkpoint(run_dir, workers)

    def test_no_generate_evaluate_skips_guard(self, tmp_path: Path) -> None:
        """Guard is a no-op when neither generate nor evaluate is in workers dict."""
        from launcher.orchestrator.run_loop import _assert_understand_checkpoint

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()
        # No checkpoint written — but guard should not apply

        workers = {"intake": object(), "understand": object()}
        # Must not raise even with missing checkpoint
        _assert_understand_checkpoint(run_dir, workers)

    def test_malformed_json_raises_worker_error(self, tmp_path: Path) -> None:
        """A checkpoint file with invalid JSON raises WorkerError."""
        from launcher.orchestrator.run_loop import _assert_understand_checkpoint

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()
        (run_dir / "understand_checkpoint.json").write_bytes(b"{not valid json")

        workers = {"generate": object(), "evaluate": object()}
        with pytest.raises(WorkerError, match="not valid JSON"):
            _assert_understand_checkpoint(run_dir, workers)

    def test_only_generate_worker_also_triggers_guard(self, tmp_path: Path) -> None:
        """Guard fires when only generate is present (no evaluate) and checkpoint is missing."""
        from launcher.orchestrator.run_loop import _assert_understand_checkpoint

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()

        workers = {"generate": object()}
        with pytest.raises(WorkerError, match="understand_checkpoint"):
            _assert_understand_checkpoint(run_dir, workers)

    def test_error_message_contains_path(self, tmp_path: Path) -> None:
        """The WorkerError message must contain the checkpoint path for actionable diagnostics."""
        from launcher.orchestrator.run_loop import _assert_understand_checkpoint

        run_dir = tmp_path / "test-run"
        run_dir.mkdir()

        workers = {"evaluate": object()}
        with pytest.raises(WorkerError) as exc_info:
            _assert_understand_checkpoint(run_dir, workers)

        assert "understand_checkpoint.json" in str(exc_info.value)

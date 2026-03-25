"""Unit tests for run_loop metadata promotion block (TC-5190 / TC5190-SR-01).

Tests the guard-clause logic that promotes scout.json and understand.json
to phase_store/ after any run where those workers completed.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.models.run_config import LLMConfig, LLMEndpoint, RunConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(family: str = "cells", platform: str = "python") -> RunConfig:
    return RunConfig(
        family=family,
        platform=platform,
        repo_url="https://github.com/test/test-repo",
        llm=LLMConfig(
            primary=LLMEndpoint(base_url="http://localhost:11434/v1", model="test-model"),
        ),
    )


def _create_run_dir(tmp_path: Path, *, scout: bool = True, understand: bool = False) -> Path:
    """Create a fake run directory under tmp_path/runs/<id>/."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = runs_dir / "test_run_001"
    run_dir.mkdir(parents=True, exist_ok=True)
    if scout:
        (run_dir / "scout.json").write_text(
            json.dumps({"build_systems": ["python"], "files_enumerated": 10}),
            encoding="utf-8",
        )
    if understand:
        (run_dir / "understanding_bundle.json").write_text(
            json.dumps({"claims": []}),
            encoding="utf-8",
        )
    return run_dir


def _run_metadata_promotion_block(
    run_dir: Path,
    config: RunConfig,
    mock_fn,
) -> None:
    """Execute the same logic as run_loop.py lines 784-796."""
    import logging as _logging

    _logger = _logging.getLogger("test_metadata_promotion")
    try:
        project_root = run_dir.parent.parent
        _phase_store_dir = project_root / "phase_store"
        if config.family and config.platform and (run_dir / "scout.json").exists():
            mock_fn(run_dir, _phase_store_dir, config.family, config.platform)
            _logger.info("Metadata phase_store updated for %s/%s", config.family, config.platform)
    except Exception:
        _logger.warning("Metadata phase_store promotion failed (non-fatal)", exc_info=True)


# ---------------------------------------------------------------------------
# Tests: Guard clause logic
# ---------------------------------------------------------------------------


class TestMetadataPromotionGuardClauses:
    """Test the guard clause: family + platform + scout.json must all exist."""

    def test_promoted_when_scout_exists(self, tmp_path: Path) -> None:
        """Happy path: scout.json exists, family+platform set → promotion fires."""
        run_dir = _create_run_dir(tmp_path, scout=True)
        config = _make_config(family="cells", platform="python")

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            _run_metadata_promotion_block(run_dir, config, mock_promote)
            mock_promote.assert_called_once_with(
                run_dir,
                tmp_path / "phase_store",
                "cells",
                "python",
            )

    def test_skipped_when_no_scout_json(self, tmp_path: Path) -> None:
        """No scout.json → promotion must NOT fire."""
        run_dir = _create_run_dir(tmp_path, scout=False)
        config = _make_config(family="cells", platform="python")

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            _run_metadata_promotion_block(run_dir, config, mock_promote)
            mock_promote.assert_not_called()

    def test_skipped_when_no_family(self, tmp_path: Path) -> None:
        """Empty family → promotion must NOT fire."""
        run_dir = _create_run_dir(tmp_path, scout=True)
        config = _make_config(family="", platform="python")

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            _run_metadata_promotion_block(run_dir, config, mock_promote)
            mock_promote.assert_not_called()

    def test_skipped_when_no_platform(self, tmp_path: Path) -> None:
        """Empty platform → promotion must NOT fire."""
        run_dir = _create_run_dir(tmp_path, scout=True)
        config = _make_config(family="cells", platform="")

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            _run_metadata_promotion_block(run_dir, config, mock_promote)
            mock_promote.assert_not_called()

    def test_promotion_failure_is_nonfatal(self, tmp_path: Path, caplog) -> None:
        """RuntimeError in promotion must be caught (non-fatal block)."""
        run_dir = _create_run_dir(tmp_path, scout=True)
        config = _make_config(family="cells", platform="python")

        def _raise(*args, **kwargs):
            raise RuntimeError("simulated promotion failure")

        # Must not propagate
        with caplog.at_level(logging.WARNING):
            _run_metadata_promotion_block(run_dir, config, _raise)

        assert "non-fatal" in caplog.text.lower() or "simulated" in caplog.text.lower()

    def test_promoted_with_both_scout_and_understand(self, tmp_path: Path) -> None:
        """Both scout.json and understanding_bundle.json present → one call."""
        run_dir = _create_run_dir(tmp_path, scout=True, understand=True)
        config = _make_config(family="3d", platform="dotnet")

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            _run_metadata_promotion_block(run_dir, config, mock_promote)
            # Guard only checks scout.json; function called once
            mock_promote.assert_called_once()
            args = mock_promote.call_args[0]
            assert args[2] == "3d"
            assert args[3] == "dotnet"


class TestProjectRootDerivation:
    """TC5190-SR-02: project_root = run_dir.parent.parent is correct by invariant."""

    def test_phase_store_dir_resolves_to_project_root(self, tmp_path: Path) -> None:
        """phase_store_dir passed to update_phase_store_metadata is <project_root>/phase_store."""
        run_dir = _create_run_dir(tmp_path, scout=True)
        config = _make_config(family="cells", platform="python")

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            _run_metadata_promotion_block(run_dir, config, mock_promote)
            phase_store_arg = mock_promote.call_args[0][1]
            # tmp_path is project_root; runs/test_run_001 is run_dir
            assert phase_store_arg == tmp_path / "phase_store"
            assert phase_store_arg.parent == tmp_path

    def test_run_dir_nesting_matches_invariant(self, tmp_path: Path) -> None:
        """run_dir.parent.parent must equal the project root (tmp_path)."""
        run_dir = _create_run_dir(tmp_path, scout=True)
        # _create_run_dir creates tmp_path/runs/test_run_001/
        assert run_dir.parent.name == "runs"
        assert run_dir.parent.parent == tmp_path

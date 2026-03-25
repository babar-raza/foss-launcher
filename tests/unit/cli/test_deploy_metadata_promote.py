"""Unit tests for CLI 'deploy metadata-promote' command (TC-5190 / TC5190-SR-01).

Tests the typer CLI command that promotes scout.json and understand.json
from a run directory to phase_store/.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from launcher.cli.deploy import deploy_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_run_dir(
    tmp_path: Path,
    *,
    scout: bool = True,
    understand: bool = False,
    run_config: dict | None = None,
) -> Path:
    """Create a fake run directory with optional artifacts."""
    run_dir = tmp_path / "test_run_001"
    run_dir.mkdir(parents=True, exist_ok=True)
    if scout:
        (run_dir / "scout.json").write_text(
            json.dumps({"build_systems": ["python"]}), encoding="utf-8"
        )
    if understand:
        (run_dir / "understanding_bundle.json").write_text(
            json.dumps({"claims": []}), encoding="utf-8"
        )
    if run_config is not None:
        (run_dir / "run_config.json").write_text(
            json.dumps(run_config), encoding="utf-8"
        )
    return run_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeployMetadataPromoteCLI:
    """Tests for the 'metadata-promote' CLI subcommand."""

    def test_auto_detects_family_platform(self, tmp_path: Path) -> None:
        """Family/platform auto-detected from run_config.json."""
        run_dir = _create_run_dir(
            tmp_path,
            scout=True,
            run_config={"family": "cells", "platform": "python"},
        )

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            result = runner.invoke(deploy_app, ["metadata-promote", str(run_dir)])

        assert result.exit_code == 0, result.output
        mock_promote.assert_called_once()
        args = mock_promote.call_args[0]
        assert args[2] == "cells"
        assert args[3] == "python"

    def test_explicit_family_platform(self, tmp_path: Path) -> None:
        """Explicit --family/--platform override auto-detection."""
        run_dir = _create_run_dir(
            tmp_path,
            scout=True,
            run_config={"family": "wrong", "platform": "wrong"},
        )

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            result = runner.invoke(
                deploy_app,
                [
                    "metadata-promote",
                    str(run_dir),
                    "--family", "3d",
                    "--platform", "dotnet",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_promote.assert_called_once()
        args = mock_promote.call_args[0]
        assert args[2] == "3d"
        assert args[3] == "dotnet"

    def test_missing_run_dir(self, tmp_path: Path) -> None:
        """Non-existent run directory → exit code 1."""
        fake_path = tmp_path / "nonexistent"
        result = runner.invoke(deploy_app, ["metadata-promote", str(fake_path)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_missing_family_platform_no_config(self, tmp_path: Path) -> None:
        """No run_config.json and no CLI flags → exit code 1."""
        run_dir = _create_run_dir(tmp_path, scout=True, run_config=None)

        result = runner.invoke(deploy_app, ["metadata-promote", str(run_dir)])
        assert result.exit_code == 1
        assert "required" in result.output.lower() or "family" in result.output.lower()

    def test_no_scout_no_understand(self, tmp_path: Path) -> None:
        """No scout.json or understanding_bundle.json → exit 0, nothing to promote."""
        run_dir = _create_run_dir(
            tmp_path,
            scout=False,
            understand=False,
            run_config={"family": "cells", "platform": "python"},
        )

        with patch(
            "launcher.deploy.phase_promoter.update_phase_store_metadata"
        ) as mock_promote:
            result = runner.invoke(deploy_app, ["metadata-promote", str(run_dir)])

        assert result.exit_code == 0
        assert "nothing to promote" in result.output.lower()
        mock_promote.assert_not_called()

    def test_malformed_run_config(self, tmp_path: Path) -> None:
        """Invalid JSON in run_config.json → falls through to requiring CLI flags."""
        run_dir = _create_run_dir(tmp_path, scout=True, run_config=None)
        (run_dir / "run_config.json").write_text("NOT VALID JSON", encoding="utf-8")

        result = runner.invoke(deploy_app, ["metadata-promote", str(run_dir)])
        # Should fail because family/platform couldn't be parsed
        assert result.exit_code == 1
        assert "required" in result.output.lower() or "family" in result.output.lower()

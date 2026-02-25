"""Tests for ``launch phase`` CLI subcommand (TC-2502).

Covers argument validation, verify-only mode, and default values.
Heavy integration (actual pipeline execution) is out of scope — these tests
exercise the CLI layer with mocks for the underlying orchestrator functions.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer import Exit
from typer.testing import CliRunner

from launch.cli.main import app
from launch.orchestrator.phase_verifier import PhaseVerificationResult, ArtifactCheck

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_dir(tmp_path: Path) -> Path:
    """Create a minimal run_dir inside a ``runs/`` parent (satisfies path validation)."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    run_dir = runs_dir / "r_test_phase"
    run_dir.mkdir()
    (run_dir / "artifacts").mkdir()
    # run_config.yaml is expected by the phase subcommand
    (run_dir / "run_config.yaml").write_text(
        textwrap.dedent("""\
            product_slug: test-product
            github_ref: main
            site_ref: default_branch
        """),
        encoding="utf-8",
    )
    return run_dir


def _make_dummy_config(tmp_path: Path) -> Path:
    """Create a minimal YAML config file that exists on disk (for --config)."""
    cfg = tmp_path / "run_config.pinned.yaml"
    cfg.write_text(
        textwrap.dedent("""\
            product_slug: test-product
            github_ref: main
            site_ref: default_branch
        """),
        encoding="utf-8",
    )
    return cfg


def _all_ok_verification(phase_id: str) -> PhaseVerificationResult:
    """Return a PhaseVerificationResult where everything passes."""
    return PhaseVerificationResult(
        phase_id=phase_id,
        ok=True,
        checks=[
            ArtifactCheck(path="artifacts/dummy.json", exists=True, valid_json=True, schema_valid=True),
        ],
        missing=[],
        schema_errors=[],
    )


def _missing_artifact_verification(phase_id: str) -> PhaseVerificationResult:
    """Return a PhaseVerificationResult with a missing artifact."""
    return PhaseVerificationResult(
        phase_id=phase_id,
        ok=False,
        checks=[
            ArtifactCheck(
                path="artifacts/product_facts.json",
                exists=False,
                valid_json=False,
                error="Artifact not found: artifacts/product_facts.json",
            ),
        ],
        missing=["artifacts/product_facts.json"],
        schema_errors=[],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPhaseSubcommandVerifyOnly:
    """--verify-only mode tests."""

    def test_verify_only_all_present(self, tmp_path: Path) -> None:
        """verify-only with all artifacts present exits 0."""
        run_dir = _make_run_dir(tmp_path)
        cfg = _make_dummy_config(tmp_path)

        ok_results = [_all_ok_verification("P1"), _all_ok_verification("P2")]

        with patch(
            "launch.orchestrator.phase_verifier.verify_phase_range",
            return_value=ok_results,
        ):
            result = runner.invoke(
                app,
                [
                    "phase",
                    "--config", str(cfg),
                    "--verify-only",
                    "--run-dir", str(run_dir),
                    "--phase-start", "P1",
                    "--phase-end", "P2",
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        assert "Verifying" in result.stdout

    def test_verify_only_missing_artifact(self, tmp_path: Path) -> None:
        """verify-only with missing artifacts exits 1."""
        run_dir = _make_run_dir(tmp_path)
        cfg = _make_dummy_config(tmp_path)

        fail_results = [_missing_artifact_verification("P1")]

        with patch(
            "launch.orchestrator.phase_verifier.verify_phase_range",
            return_value=fail_results,
        ):
            result = runner.invoke(
                app,
                [
                    "phase",
                    "--config", str(cfg),
                    "--verify-only",
                    "--run-dir", str(run_dir),
                    "--phase-start", "P1",
                    "--phase-end", "P1",
                ],
            )

        assert result.exit_code == 1, f"stdout: {result.stdout}"
        assert "FAIL" in result.stdout or "missing" in result.stdout.lower()


class TestPhaseSubcommandValidation:
    """Argument validation tests."""

    def test_invalid_phase_id(self, tmp_path: Path) -> None:
        """Invalid phase identifier (e.g. P99) exits 1 with clear error."""
        run_dir = _make_run_dir(tmp_path)
        cfg = _make_dummy_config(tmp_path)

        result = runner.invoke(
            app,
            [
                "phase",
                "--config", str(cfg),
                "--run-dir", str(run_dir),
                "--phase-start", "P99",
            ],
        )

        assert result.exit_code == 1, f"stdout: {result.stdout}"
        assert "Invalid phase identifier" in result.stdout or "P99" in result.stdout

    def test_end_before_start(self, tmp_path: Path) -> None:
        """--phase-end before --phase-start exits 1 with clear error."""
        run_dir = _make_run_dir(tmp_path)
        cfg = _make_dummy_config(tmp_path)

        result = runner.invoke(
            app,
            [
                "phase",
                "--config", str(cfg),
                "--run-dir", str(run_dir),
                "--phase-start", "P4",
                "--phase-end", "P2",
            ],
        )

        assert result.exit_code == 1, f"stdout: {result.stdout}"
        assert "precedes" in result.stdout

    def test_verify_only_requires_run_dir(self, tmp_path: Path) -> None:
        """--verify-only without --run-dir exits 1."""
        cfg = _make_dummy_config(tmp_path)

        result = runner.invoke(
            app,
            [
                "phase",
                "--config", str(cfg),
                "--verify-only",
            ],
        )

        assert result.exit_code == 1, f"stdout: {result.stdout}"
        assert "--run-dir" in result.stdout


class TestPhaseSubcommandDefaults:
    """Default argument value tests."""

    def test_defaults_p1_to_p6(self, tmp_path: Path) -> None:
        """Without explicit --phase-start/--phase-end, defaults are P1..P6.

        We verify this by checking that verify_phase_range is called with
        start_phase='P1' and end_phase='P6' in --verify-only mode.
        """
        run_dir = _make_run_dir(tmp_path)
        cfg = _make_dummy_config(tmp_path)

        ok_results = [_all_ok_verification(f"P{i}") for i in range(1, 7)]

        with patch(
            "launch.orchestrator.phase_verifier.verify_phase_range",
            return_value=ok_results,
        ) as mock_verify:
            result = runner.invoke(
                app,
                [
                    "phase",
                    "--config", str(cfg),
                    "--verify-only",
                    "--run-dir", str(run_dir),
                    # No --phase-start or --phase-end → should default to P1..P6
                ],
            )

        assert result.exit_code == 0, f"stdout: {result.stdout}"
        # Verify that verify_phase_range was called with P1, P6
        mock_verify.assert_called_once()
        call_args = mock_verify.call_args
        # positional args: (run_dir, start_phase, end_phase)
        assert call_args[0][1] == "P1"
        assert call_args[0][2] == "P6"

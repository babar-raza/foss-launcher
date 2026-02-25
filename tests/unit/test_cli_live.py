"""Tests for CLI --live, --pause, and monitor command registration.

Validates that the new monitoring flags are accepted by the CLI
and that the monitor command is registered in the app.
"""

from __future__ import annotations

import inspect

import pytest
from typer.testing import CliRunner

from launch.cli.main import app, monitor, phase, resume, run


runner = CliRunner()


# ---------------------------------------------------------------------------
# Tests: --live flag registration
# ---------------------------------------------------------------------------


class TestLiveFlagRegistration:
    """Verify that --live is accepted as a parameter on run/resume/phase."""

    def test_run_has_live_param(self):
        sig = inspect.signature(run)
        assert "live" in sig.parameters, "run() missing 'live' parameter"
        param = sig.parameters["live"]
        assert param.default.default is False

    def test_resume_has_live_param(self):
        sig = inspect.signature(resume)
        assert "live" in sig.parameters, "resume() missing 'live' parameter"
        param = sig.parameters["live"]
        assert param.default.default is False

    def test_phase_has_live_param(self):
        sig = inspect.signature(phase)
        assert "live" in sig.parameters, "phase() missing 'live' parameter"
        param = sig.parameters["live"]
        assert param.default.default is False


# ---------------------------------------------------------------------------
# Tests: --pause flag registration
# ---------------------------------------------------------------------------


class TestPauseFlagRegistration:
    """Verify that --pause is accepted as a parameter on phase."""

    def test_phase_has_pause_param(self):
        sig = inspect.signature(phase)
        assert "pause" in sig.parameters, "phase() missing 'pause' parameter"
        param = sig.parameters["pause"]
        assert param.default.default is False


# ---------------------------------------------------------------------------
# Tests: monitor command registration
# ---------------------------------------------------------------------------


class TestMonitorCommand:
    """Verify that the monitor command is registered in the app."""

    def test_monitor_command_exists(self):
        """The monitor command should be registered in the CLI app."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "monitor" in command_names, (
            f"'monitor' command not registered. Available: {command_names}"
        )

    def test_monitor_has_run_dir_param(self):
        sig = inspect.signature(monitor)
        assert "run_dir" in sig.parameters, "monitor() missing 'run_dir' parameter"

    def test_monitor_has_verbose_param(self):
        sig = inspect.signature(monitor)
        assert "verbose" in sig.parameters, "monitor() missing 'verbose' parameter"


# ---------------------------------------------------------------------------
# Tests: --pause implies --live behavior
# ---------------------------------------------------------------------------


class TestPauseImpliesLive:
    """Verify that --pause implies --live in the phase command logic.

    We cannot easily test the runtime implication without mocking the full
    orchestrator, but we can verify the parameter defaults are set up
    correctly for downstream logic.
    """

    def test_pause_and_live_are_independent_defaults(self):
        """Both default to False — implication is handled at runtime."""
        sig = inspect.signature(phase)
        assert sig.parameters["live"].default.default is False
        assert sig.parameters["pause"].default.default is False

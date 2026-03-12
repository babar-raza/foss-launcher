"""Tests for _VALID_WORKERS completeness and CLI guard behavior — TC-4221."""
from __future__ import annotations

from launcher.cli.main import _VALID_WORKERS


class TestValidWorkers:
    def test_scout_in_valid_workers(self):
        assert "scout" in _VALID_WORKERS

    def test_scout_order_after_intake(self):
        intake_idx = _VALID_WORKERS.index("intake")
        scout_idx = _VALID_WORKERS.index("scout")
        assert scout_idx == intake_idx + 1

    def test_pipeline_order_complete(self):
        expected = ["intake", "scout", "understand", "planner", "generate", "evaluate", "publish"]
        assert _VALID_WORKERS == expected

    def test_stop_after_scout_not_rejected_by_guard(self, tmp_path):
        from typer.testing import CliRunner
        from launcher.cli.main import app

        config = tmp_path / "c.yaml"
        config.write_text("family: cells\nplatform: python\nrepo_url: https://github.com/x/y\n")
        result = CliRunner().invoke(app, ["run", str(config), "--stop-after", "scout"])
        # Guard must not reject "scout" as an invalid worker value
        assert "--stop-after must be one of" not in (result.output or "")

    def test_resume_from_scout_not_rejected_by_run_loop(self, tmp_path):
        """resume_from=scout must not raise ValueError in execute_run guard."""
        from typer.testing import CliRunner
        from launcher.cli.main import app

        config = tmp_path / "c.yaml"
        config.write_text("family: cells\nplatform: python\nrepo_url: https://github.com/x/y\n")
        result = CliRunner().invoke(app, [
            "run", str(config),
            "--resume-from", "scout",
            "--stop-after", "understand",
        ])
        # Should not contain run_loop's "not a known pipeline worker" error
        assert "not a known pipeline worker" not in (result.output or "")

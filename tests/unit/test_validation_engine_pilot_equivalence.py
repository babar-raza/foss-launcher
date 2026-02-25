"""TC-2432: Env-gated equivalence test against a real pilot run directory.

This module is skipped unless LAUNCH_TEST_PILOT_RUN_DIR is set to the path
of an actual pilot run directory (e.g. from a recent FOSS-Launcher pilot run).

Usage:
    LAUNCH_TEST_PILOT_RUN_DIR=/path/to/run_dir pytest tests/unit/test_validation_engine_pilot_equivalence.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PILOT_RUN_DIR = os.environ.get("LAUNCH_TEST_PILOT_RUN_DIR")


def _run_engine(run_dir: Path, engine: str, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Run execute_validator with the given engine and return the report."""
    monkeypatch.setenv("LAUNCH_VALIDATION_ENGINE", engine)

    try:
        from launch.validation_engine.context import GateContext
        monkeypatch.setattr(GateContext, "get_llm_client", lambda self: None)
    except Exception:
        pass

    (run_dir / "events.ndjson").write_text("", encoding="utf-8")

    from launch.workers.w9_validator.worker import execute_validator
    return execute_validator(run_dir, {"validation_profile": "local"})


@pytest.mark.skipif(
    not PILOT_RUN_DIR,
    reason="LAUNCH_TEST_PILOT_RUN_DIR not set — set to real pilot run dir to run",
)
class TestPilotEquivalence:
    """Legacy vs registry engine equivalence on a real pilot run directory."""

    def test_legacy_equals_registry_gate_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_dir = Path(PILOT_RUN_DIR)
        legacy   = _run_engine(run_dir, "legacy",   monkeypatch)
        registry = _run_engine(run_dir, "registry", monkeypatch)
        assert [g["name"] for g in legacy["gates"]] == [g["name"] for g in registry["gates"]]

    def test_legacy_equals_registry_ok_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_dir = Path(PILOT_RUN_DIR)
        legacy   = _run_engine(run_dir, "legacy",   monkeypatch)
        registry = _run_engine(run_dir, "registry", monkeypatch)
        for lg, rg in zip(legacy["gates"], registry["gates"]):
            assert lg["ok"] == rg["ok"]

    def test_legacy_equals_registry_overall_ok(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_dir = Path(PILOT_RUN_DIR)
        legacy   = _run_engine(run_dir, "legacy",   monkeypatch)
        registry = _run_engine(run_dir, "registry", monkeypatch)
        assert legacy["ok"] == registry["ok"]

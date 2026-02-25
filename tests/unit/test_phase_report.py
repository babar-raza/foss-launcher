"""Tests for write_phase_report() — TC-2504.

Validates that phase_report.json is written correctly with proper
aggregation of phase execution and verification results.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.orchestrator.phase_executor import PhaseResult, write_phase_report
from launch.orchestrator.phase_verifier import (
    ArtifactCheck,
    PhaseVerificationResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_phase_result(
    phase_id: str = "P1",
    workers: list | None = None,
    ok: bool = True,
    error: str | None = None,
) -> PhaseResult:
    """Create a PhaseResult with sensible defaults."""
    return PhaseResult(
        phase_id=phase_id,
        workers=workers or ["W1", "W2"],
        ok=ok,
        error=error,
        started_at_utc="2026-02-25T10:00:00+00:00",
        finished_at_utc="2026-02-25T10:05:00+00:00",
    )


def _make_verification_result(
    phase_id: str = "P1",
    ok: bool = True,
    missing: list | None = None,
    schema_errors: list | None = None,
) -> PhaseVerificationResult:
    """Create a PhaseVerificationResult with sensible defaults."""
    checks = [
        ArtifactCheck(
            path="artifacts/repo_inventory.json",
            exists=True,
            valid_json=True,
            schema_valid=True,
        ),
    ]
    return PhaseVerificationResult(
        phase_id=phase_id,
        ok=ok,
        checks=checks,
        missing=missing or [],
        schema_errors=schema_errors or [],
    )


STARTED = "2026-02-25T10:00:00+00:00"
FINISHED = "2026-02-25T10:30:00+00:00"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWritePhaseReport:
    """Tests for write_phase_report()."""

    def test_write_phase_report_all_ok(self, tmp_path: Path) -> None:
        """When all phases and verifications pass, overall_ok is True."""
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        phase_results = [
            _make_phase_result("P1", ["W1", "W2"], ok=True),
            _make_phase_result("P2", ["W3", "W4"], ok=True),
        ]
        verification_results = [
            _make_verification_result("P1", ok=True),
            _make_verification_result("P2", ok=True),
        ]

        result_path = write_phase_report(
            run_dir=run_dir,
            run_id="r_test",
            phase_results=phase_results,
            verification_results=verification_results,
            started_at_utc=STARTED,
            finished_at_utc=FINISHED,
        )

        assert result_path.exists()
        report = json.loads(result_path.read_text(encoding="utf-8"))

        assert report["overall_ok"] is True
        assert report["run_id"] == "r_test"
        assert report["run_dir"] == str(run_dir)
        assert report["started_at_utc"] == STARTED
        assert report["finished_at_utc"] == FINISHED
        assert len(report["phases_executed"]) == 2
        assert len(report["verifications"]) == 2

    def test_write_phase_report_phase_failure(self, tmp_path: Path) -> None:
        """When one phase fails, overall_ok is False."""
        run_dir = tmp_path / "runs" / "r_fail"
        run_dir.mkdir(parents=True)

        phase_results = [
            _make_phase_result("P1", ok=True),
            _make_phase_result("P2", ok=False, error="RuntimeError: boom"),
        ]
        verification_results = [
            _make_verification_result("P1", ok=True),
        ]

        result_path = write_phase_report(
            run_dir=run_dir,
            run_id="r_fail",
            phase_results=phase_results,
            verification_results=verification_results,
            started_at_utc=STARTED,
            finished_at_utc=FINISHED,
        )

        report = json.loads(result_path.read_text(encoding="utf-8"))

        assert report["overall_ok"] is False
        assert report["phases_executed"][1]["ok"] is False
        assert report["phases_executed"][1]["error"] == "RuntimeError: boom"

    def test_write_phase_report_verification_failure(
        self, tmp_path: Path
    ) -> None:
        """When phases pass but verification fails, overall_ok is False."""
        run_dir = tmp_path / "runs" / "r_vfail"
        run_dir.mkdir(parents=True)

        phase_results = [
            _make_phase_result("P1", ok=True),
        ]
        verification_results = [
            _make_verification_result(
                "P1",
                ok=False,
                missing=["artifacts/repo_inventory.json"],
            ),
        ]

        result_path = write_phase_report(
            run_dir=run_dir,
            run_id="r_vfail",
            phase_results=phase_results,
            verification_results=verification_results,
            started_at_utc=STARTED,
            finished_at_utc=FINISHED,
        )

        report = json.loads(result_path.read_text(encoding="utf-8"))

        assert report["overall_ok"] is False
        assert report["verifications"][0]["ok"] is False
        assert "artifacts/repo_inventory.json" in report["verifications"][0]["missing"]

    def test_write_phase_report_schema_valid(self, tmp_path: Path) -> None:
        """Output validates against phase_report.schema.json."""
        run_dir = tmp_path / "runs" / "r_schema"
        run_dir.mkdir(parents=True)

        phase_results = [_make_phase_result("P1", ok=True)]
        verification_results = [_make_verification_result("P1", ok=True)]

        result_path = write_phase_report(
            run_dir=run_dir,
            run_id="r_schema",
            phase_results=phase_results,
            verification_results=verification_results,
            started_at_utc=STARTED,
            finished_at_utc=FINISHED,
        )

        report = json.loads(result_path.read_text(encoding="utf-8"))

        # Locate the schema relative to the repo root
        schema_path = (
            Path(__file__).resolve().parents[2]
            / "specs"
            / "schemas"
            / "phase_report.schema.json"
        )
        assert schema_path.exists(), f"Schema not found at {schema_path}"

        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        # Use jsonschema if available; fall back to manual structural checks
        try:
            import jsonschema

            jsonschema.validate(instance=report, schema=schema)
        except ImportError:
            # Manual validation: required keys present, correct types
            for key in schema["required"]:
                assert key in report, f"Missing required key: {key}"
            assert isinstance(report["run_id"], str)
            assert isinstance(report["overall_ok"], bool)
            assert isinstance(report["phases_executed"], list)
            assert isinstance(report["verifications"], list)
            for phase in report["phases_executed"]:
                assert "phase_id" in phase
                assert "ok" in phase
            for verif in report["verifications"]:
                assert "phase_id" in verif
                assert "ok" in verif

    def test_write_phase_report_deterministic_output(
        self, tmp_path: Path
    ) -> None:
        """Same inputs produce byte-identical output (sorted keys)."""
        phase_results = [
            _make_phase_result("P1", ["W1", "W2"], ok=True),
            _make_phase_result("P2", ["W3", "W4"], ok=True),
        ]
        verification_results = [
            _make_verification_result("P1", ok=True),
            _make_verification_result("P2", ok=True),
        ]

        # Use the SAME run_dir for both writes so the run_dir field
        # in the serialized report is identical.
        run_dir = tmp_path / "run_det"
        run_dir.mkdir(parents=True)

        outputs = []
        for _ in range(2):
            result_path = write_phase_report(
                run_dir=run_dir,
                run_id="r_det",
                phase_results=phase_results,
                verification_results=verification_results,
                started_at_utc=STARTED,
                finished_at_utc=FINISHED,
            )
            outputs.append(result_path.read_text(encoding="utf-8"))

        assert outputs[0] == outputs[1], (
            "write_phase_report must produce deterministic output"
        )

        # Verify keys are sorted (atomic_write_json uses sort_keys=True)
        report = json.loads(outputs[0])
        keys = list(report.keys())
        assert keys == sorted(keys), "Top-level keys must be sorted"

    def test_write_phase_report_creates_artifacts_dir(
        self, tmp_path: Path
    ) -> None:
        """Creates artifacts/ subdirectory if it does not exist."""
        run_dir = tmp_path / "runs" / "r_noart"
        run_dir.mkdir(parents=True)

        # Ensure artifacts dir does NOT exist before the call
        assert not (run_dir / "artifacts").exists()

        result_path = write_phase_report(
            run_dir=run_dir,
            run_id="r_noart",
            phase_results=[_make_phase_result("P1", ok=True)],
            verification_results=[_make_verification_result("P1", ok=True)],
            started_at_utc=STARTED,
            finished_at_utc=FINISHED,
        )

        assert result_path.exists()
        assert (run_dir / "artifacts").is_dir()
        assert result_path == run_dir / "artifacts" / "phase_report.json"

    def test_write_phase_report_empty_lists(self, tmp_path: Path) -> None:
        """Empty phase and verification lists produce overall_ok=True."""
        run_dir = tmp_path / "runs" / "r_empty"
        run_dir.mkdir(parents=True)

        result_path = write_phase_report(
            run_dir=run_dir,
            run_id="r_empty",
            phase_results=[],
            verification_results=[],
            started_at_utc=STARTED,
            finished_at_utc=FINISHED,
        )

        report = json.loads(result_path.read_text(encoding="utf-8"))
        # all() on empty iterable returns True
        assert report["overall_ok"] is True
        assert report["phases_executed"] == []
        assert report["verifications"] == []

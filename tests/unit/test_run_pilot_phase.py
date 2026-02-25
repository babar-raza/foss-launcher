"""TC-2503: Tests for --phase-start / --phase-end CLI flags in run_pilot.py.

Validates argument parsing, mutual exclusivity, defaults, and phase-bounded
execution plumbing.  These tests are fast and hermetic (no subprocess or
network calls).
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Optional
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Import helpers from the scripts/ directory
# ---------------------------------------------------------------------------
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root / "scripts"))

import run_pilot  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Run the run_pilot argument parser on *argv* and return the Namespace.

    Mirrors the parser definition in ``run_pilot.main()``.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--export-content", type=Path, default=None)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--from-worker", default=None, metavar="ALIAS")
    parser.add_argument("--phase-start", default=None, metavar="PHASE")
    parser.add_argument("--phase-end", default=None, metavar="PHASE")
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Test: argument parsing
# ---------------------------------------------------------------------------


class TestPhaseArgsParsed:
    """Verify --phase-start and --phase-end are parsed correctly."""

    def test_both_flags_present(self) -> None:
        ns = _parse_args(["--pilot", "test", "--phase-start", "P2", "--phase-end", "P4"])
        assert ns.phase_start == "P2"
        assert ns.phase_end == "P4"

    def test_only_phase_start(self) -> None:
        ns = _parse_args(["--pilot", "test", "--phase-start", "P3"])
        assert ns.phase_start == "P3"
        assert ns.phase_end is None

    def test_only_phase_end(self) -> None:
        ns = _parse_args(["--pilot", "test", "--phase-end", "P5"])
        assert ns.phase_start is None
        assert ns.phase_end == "P5"

    def test_no_phase_flags(self) -> None:
        ns = _parse_args(["--pilot", "test"])
        assert ns.phase_start is None
        assert ns.phase_end is None


# ---------------------------------------------------------------------------
# Test: mutual exclusivity with --from-worker
# ---------------------------------------------------------------------------


class TestPhaseMutuallyExclusiveWithFromWorker:
    """--phase-start / --phase-end and --from-worker cannot coexist."""

    def test_phase_start_with_from_worker_returns_1(self) -> None:
        """main() should return 1 when both --phase-start and --from-worker are given."""
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-start", "P2",
            "--from-worker", "W5",
        ]
        with mock.patch("sys.argv", test_args):
            rc = run_pilot.main()
        assert rc == 1

    def test_phase_end_with_from_worker_returns_1(self) -> None:
        """main() should return 1 when both --phase-end and --from-worker are given."""
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-end", "P4",
            "--from-worker", "W5",
        ]
        with mock.patch("sys.argv", test_args):
            rc = run_pilot.main()
        assert rc == 1


# ---------------------------------------------------------------------------
# Test: defaults
# ---------------------------------------------------------------------------


class TestPhaseDefaults:
    """When only one flag is provided the other defaults to P1 or P6."""

    @mock.patch("run_pilot._run_pilot_phased")
    def test_phase_start_only_defaults_end_to_P6(self, mock_phased: mock.Mock) -> None:
        mock_phased.return_value = 0
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-start", "P3",
        ]
        with mock.patch("sys.argv", test_args):
            run_pilot.main()

        mock_phased.assert_called_once_with("pilot-aspose-3d-foss-python", "P3", "P6")

    @mock.patch("run_pilot._run_pilot_phased")
    def test_phase_end_only_defaults_start_to_P1(self, mock_phased: mock.Mock) -> None:
        mock_phased.return_value = 0
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-end", "P4",
        ]
        with mock.patch("sys.argv", test_args):
            run_pilot.main()

        mock_phased.assert_called_once_with("pilot-aspose-3d-foss-python", "P1", "P4")

    @mock.patch("run_pilot._run_pilot_phased")
    def test_both_flags_passed_through(self, mock_phased: mock.Mock) -> None:
        mock_phased.return_value = 0
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-start", "P2",
            "--phase-end", "P5",
        ]
        with mock.patch("sys.argv", test_args):
            run_pilot.main()

        mock_phased.assert_called_once_with("pilot-aspose-3d-foss-python", "P2", "P5")


# ---------------------------------------------------------------------------
# Test: invalid phase identifiers
# ---------------------------------------------------------------------------


class TestPhaseInvalidId:
    """Invalid phase IDs produce a helpful error message (return code 1)."""

    def test_invalid_phase_start(self) -> None:
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-start", "PX",
        ]
        with mock.patch("sys.argv", test_args):
            rc = run_pilot.main()
        assert rc == 1

    def test_invalid_phase_end(self) -> None:
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-end", "P99",
        ]
        with mock.patch("sys.argv", test_args):
            rc = run_pilot.main()
        assert rc == 1

    def test_invalid_both(self) -> None:
        test_args = [
            "run_pilot.py",
            "--pilot", "pilot-aspose-3d-foss-python",
            "--phase-start", "BAD",
            "--phase-end", "WORSE",
        ]
        with mock.patch("sys.argv", test_args):
            rc = run_pilot.main()
        assert rc == 1


# ---------------------------------------------------------------------------
# Test: reversed range
# ---------------------------------------------------------------------------


class TestPhaseReversedRange:
    """--phase-end before --phase-start is an error."""

    def test_reversed_range_returns_1(self) -> None:
        """_run_pilot_phased should return 1 for reversed range."""
        rc = run_pilot._run_pilot_phased(
            "pilot-aspose-3d-foss-python", "P5", "P2"
        )
        assert rc == 1


# ---------------------------------------------------------------------------
# Test: constants consistency
# ---------------------------------------------------------------------------


class TestPhaseConstants:
    """Verify module-level constants are well-formed."""

    def test_valid_phase_ids_length(self) -> None:
        assert len(run_pilot._VALID_PHASE_IDS) == 6

    def test_valid_phase_ids_content(self) -> None:
        assert run_pilot._VALID_PHASE_IDS == ("P1", "P2", "P3", "P4", "P5", "P6")

    def test_entry_workers_keys_match_phase_ids(self) -> None:
        assert set(run_pilot._PHASE_ENTRY_WORKERS.keys()) == set(run_pilot._VALID_PHASE_IDS)

    def test_entry_workers_values_are_worker_aliases(self) -> None:
        for phase_id, worker in run_pilot._PHASE_ENTRY_WORKERS.items():
            assert worker.startswith("W"), (
                f"Entry worker for {phase_id} should be a W-alias, got {worker!r}"
            )


# ---------------------------------------------------------------------------
# Test: _find_latest_run_dir
# ---------------------------------------------------------------------------


class TestFindLatestRunDir:
    """Test manifest lookup in _find_latest_run_dir."""

    def test_no_manifest_returns_none(self, tmp_path: Path) -> None:
        """No manifest.jsonl means no run directory."""
        with mock.patch("run_pilot.get_repo_root", return_value=tmp_path):
            result = run_pilot._find_latest_run_dir("pilot-aspose-3d-foss-python")
        assert result is None

    def test_no_matching_pilot_returns_none(self, tmp_path: Path) -> None:
        """Manifest exists but no entry for this pilot."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        manifest = runs_dir / "manifest.jsonl"
        manifest.write_text(
            json.dumps({"pilot": "other-pilot", "output_dir": str(tmp_path / "runs" / "r1")}) + "\n",
            encoding="utf-8",
        )

        with mock.patch("run_pilot.get_repo_root", return_value=tmp_path):
            result = run_pilot._find_latest_run_dir("pilot-aspose-3d-foss-python")
        assert result is None

    def test_matching_pilot_returns_path(self, tmp_path: Path) -> None:
        """Manifest has a matching entry with existing directory."""
        runs_dir = tmp_path / "runs"
        run_dir = runs_dir / "r_20260225T000000Z"
        run_dir.mkdir(parents=True)
        manifest = runs_dir / "manifest.jsonl"
        manifest.write_text(
            json.dumps({"pilot": "pilot-aspose-3d-foss-python", "output_dir": str(run_dir)}) + "\n",
            encoding="utf-8",
        )

        with mock.patch("run_pilot.get_repo_root", return_value=tmp_path):
            result = run_pilot._find_latest_run_dir("pilot-aspose-3d-foss-python")
        assert result == run_dir

    def test_nonexistent_run_dir_returns_none(self, tmp_path: Path) -> None:
        """Manifest points to a directory that no longer exists."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        manifest = runs_dir / "manifest.jsonl"
        manifest.write_text(
            json.dumps({
                "pilot": "pilot-aspose-3d-foss-python",
                "output_dir": str(tmp_path / "runs" / "deleted_run"),
            }) + "\n",
            encoding="utf-8",
        )

        with mock.patch("run_pilot.get_repo_root", return_value=tmp_path):
            result = run_pilot._find_latest_run_dir("pilot-aspose-3d-foss-python")
        assert result is None

    def test_last_matching_entry_wins(self, tmp_path: Path) -> None:
        """When multiple entries match, the last one wins."""
        runs_dir = tmp_path / "runs"
        old_dir = runs_dir / "r_old"
        new_dir = runs_dir / "r_new"
        old_dir.mkdir(parents=True)
        new_dir.mkdir(parents=True)
        manifest = runs_dir / "manifest.jsonl"
        lines = [
            json.dumps({"pilot": "pilot-aspose-3d-foss-python", "output_dir": str(old_dir)}),
            json.dumps({"pilot": "pilot-aspose-3d-foss-python", "output_dir": str(new_dir)}),
        ]
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with mock.patch("run_pilot.get_repo_root", return_value=tmp_path):
            result = run_pilot._find_latest_run_dir("pilot-aspose-3d-foss-python")
        assert result == new_dir


# ---------------------------------------------------------------------------
# Test: _print_phase_summary (output formatting)
# ---------------------------------------------------------------------------


class TestPrintPhaseSummary:
    """Verify human-readable output from _print_phase_summary."""

    def test_all_pass(self, capsys: pytest.CaptureFixture) -> None:
        """All phases pass -- should print 'All N phases verified OK.'"""
        # Minimal duck-typed objects
        v1 = mock.Mock(phase_id="P1", ok=True, checks=[1, 2, 3], missing=[], schema_errors=[])
        v2 = mock.Mock(phase_id="P2", ok=True, checks=[1], missing=[], schema_errors=[])

        run_pilot._print_phase_summary([v1, v2])

        out = capsys.readouterr().out
        assert "P1: PASS" in out
        assert "P2: PASS" in out
        assert "All 2 phases verified OK." in out

    def test_with_failures(self, capsys: pytest.CaptureFixture) -> None:
        """Mixed pass/fail -- should report failures."""
        v1 = mock.Mock(
            phase_id="P1", ok=True, checks=[1, 2], missing=[], schema_errors=[]
        )
        v2 = mock.Mock(
            phase_id="P2",
            ok=False,
            checks=[1],
            missing=["artifacts/page_plan.json"],
            schema_errors=[],
        )

        run_pilot._print_phase_summary([v1, v2])

        out = capsys.readouterr().out
        assert "P1: PASS" in out
        assert "P2: FAIL" in out
        assert "MISSING: artifacts/page_plan.json" in out
        assert "1/2 phases verified OK. 1 failed." in out

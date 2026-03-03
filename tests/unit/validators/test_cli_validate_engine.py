"""Tests for TC-3616: validators/cli.py canonical engine delegation.

Verifies that ``launch validate`` (validators/cli.validate) delegates to
validation_engine.run_gates() and writes the canonical validation_report.json
instead of the old scaffold 4-gate report at validation_report.site.json.

Binding spec: specs/29_project_repo_structure.md §Binding-rules Rule 3
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_gate(name: str, ok: bool = True) -> Dict[str, Any]:
    return {"name": name, "ok": ok}


def _make_issue(gate: str, message: str = "test issue") -> Dict[str, Any]:
    return {
        "issue_id": f"iss_{gate}",
        "gate": gate,
        "severity": "error",
        "message": message,
        "status": "OPEN",
    }


def _run_validate(run_dir: Path, profile: str = "local") -> int:
    """Call validate() and return the exit code.

    typer.Exit / click.Exit are not SystemExit, so we catch BaseException.
    """
    from launch.validators.cli import validate

    try:
        validate(run_dir, profile=profile)
        return 0
    except BaseException as exc:
        # click.exceptions.Exit uses 'exit_code' in newer click versions;
        # SystemExit uses 'code'.
        for attr in ("exit_code", "code"):
            val = getattr(exc, attr, None)
            if isinstance(val, int):
                return val
        return 0


def _make_run_dir(tmp_path: Path, *, with_run_config: bool = True) -> Path:
    """Create a minimal run directory structure for validate() tests."""
    run_dir = tmp_path / "runs" / "test-run-01"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    if with_run_config:
        (run_dir / "run_config.yaml").write_text(
            "product_slug: test-product\nrun_id: test-run-01\n",
            encoding="utf-8",
        )
    return run_dir


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestValidateCallsEngine:
    """TC-3616: validate() must delegate to validation_engine.run_gates()."""

    def test_validate_calls_run_gates_with_correct_args(self, tmp_path: Path) -> None:
        """run_gates() is called with (run_dir, run_config, profile)."""
        run_dir = _make_run_dir(tmp_path)
        gate_results = [_make_gate("gate_1_schema_validation", ok=True)]
        all_issues: List[Dict[str, Any]] = []

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=(gate_results, all_issues),
        ) as mock_run_gates:
            exit_code = _run_validate(run_dir, profile="local")

        mock_run_gates.assert_called_once()
        call_args = mock_run_gates.call_args
        assert call_args[0][0] == run_dir  # run_dir
        assert call_args[0][2] == "local"  # profile
        assert exit_code == 0

    def test_validate_writes_canonical_report(self, tmp_path: Path) -> None:
        """validation_report.json is written (not validation_report.site.json)."""
        run_dir = _make_run_dir(tmp_path)
        gate_results = [_make_gate("gate_truth_layer_completeness", ok=True)]

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=(gate_results, []),
        ):
            _run_validate(run_dir, profile="local")

        canonical = run_dir / "artifacts" / "validation_report.json"
        assert canonical.exists(), "validation_report.json must be written"

    def test_validate_does_not_write_site_json(self, tmp_path: Path) -> None:
        """validation_report.site.json must NOT be written (TC-3616 supersedes TC-3580)."""
        run_dir = _make_run_dir(tmp_path)

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=([_make_gate("g", ok=True)], []),
        ):
            _run_validate(run_dir, profile="local")

        site_json = run_dir / "artifacts" / "validation_report.site.json"
        assert not site_json.exists(), "validation_report.site.json must NOT be written"

    def test_validate_report_has_required_schema_fields(self, tmp_path: Path) -> None:
        """Written report contains all required validation_report.schema.json fields."""
        run_dir = _make_run_dir(tmp_path)
        gate_results = [_make_gate("gate_1", ok=True), _make_gate("gate_2", ok=True)]
        issues = [_make_issue("gate_3")]

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=(gate_results, issues),
        ):
            _run_validate(run_dir, profile="ci")

        report_path = run_dir / "artifacts" / "validation_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))

        # Required fields per specs/schemas/validation_report.schema.json
        assert report["schema_version"] == "1.0"
        assert isinstance(report["ok"], bool)
        assert report["profile"] == "ci"
        assert isinstance(report["gates"], list)
        assert isinstance(report["issues"], list)
        # TC-3616 adds these for W9 schema compatibility
        assert "generation_id" in report
        assert "content_hash" in report

    def test_validate_content_hash_is_deterministic(self, tmp_path: Path) -> None:
        """content_hash is SHA-256 of sorted gates+issues — deterministic."""
        run_dir = _make_run_dir(tmp_path)
        gate_results = [_make_gate("gate_a", ok=True)]
        all_issues: List[Dict[str, Any]] = []

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=(gate_results, all_issues),
        ):
            _run_validate(run_dir, profile="local")

        report = json.loads(
            (run_dir / "artifacts" / "validation_report.json").read_text(encoding="utf-8")
        )
        expected_hash = hashlib.sha256(
            json.dumps(
                {"gates": gate_results, "issues": all_issues}, sort_keys=True
            ).encode()
        ).hexdigest()
        assert report["content_hash"] == expected_hash

    def test_validate_exit_0_when_all_gates_ok(self, tmp_path: Path) -> None:
        """Exit code 0 when all gates return ok=True."""
        run_dir = _make_run_dir(tmp_path)

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=([_make_gate("g", ok=True)], []),
        ):
            code = _run_validate(run_dir, profile="local")

        assert code == 0

    def test_validate_exit_2_when_any_gate_fails(self, tmp_path: Path) -> None:
        """Exit code 2 when at least one gate returns ok=False."""
        run_dir = _make_run_dir(tmp_path)

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch(
            "launch.validation_engine.run_gates",
            return_value=(
                [_make_gate("g_ok", ok=True), _make_gate("g_fail", ok=False)],
                [_make_issue("g_fail")],
            ),
        ):
            code = _run_validate(run_dir, profile="local")

        assert code == 2

    def test_validate_profile_from_run_config_takes_precedence(
        self, tmp_path: Path
    ) -> None:
        """run_config.validation_profile overrides --profile CLI arg."""
        run_dir = _make_run_dir(tmp_path)
        # Override run_config with validation_profile: prod
        (run_dir / "run_config.yaml").write_text(
            "product_slug: test\nvalidation_profile: prod\n", encoding="utf-8"
        )

        captured_profile: List[str] = []

        def fake_run_gates(rd: Path, rc: dict, profile: str):  # type: ignore[return]
            captured_profile.append(profile)
            return ([_make_gate("g", ok=True)], [])

        with patch(
            "launch.validators.cli.validate_run_dir_under_runs",
            side_effect=lambda p: p,
        ), patch("launch.validation_engine.run_gates", side_effect=fake_run_gates):
            _run_validate(run_dir, profile="local")  # CLI says local, config says prod

        assert captured_profile == ["prod"], (
            "run_config.validation_profile should override --profile"
        )

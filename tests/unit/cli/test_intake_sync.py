"""Tests for TC-5172: intake sync command.

Covers:
- test_sync_generates_missing_config: repo in scan_state with no config → config created
- test_sync_skips_existing_config: repo with existing config → no overwrite
- test_sync_reports_needs_review: classification=needs_review → reported, not crashed
- test_sync_dry_run: dry_run=True → nothing written, output shows what would happen
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from launcher.cli.intake import intake_app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_REPO: Dict[str, Any] = {
    "name": "Aspose.Cells-FOSS-for-Python",
    "full_name": "aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    "html_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    "description": "Aspose.Cells FOSS for Python",
    "stargazers_count": 10,
    "topics": ["cells"],
    "owner": {"login": "aspose-cells-foss"},
    "default_branch": "main",
    "language": "Python",
}

_ELIGIBLE_CLASSIFICATION = MagicMock(
    decision="eligible",
    reasons=[],
    full_name="aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
)
_ELIGIBLE_CLASSIFICATION.to_dict.return_value = {"decision": "eligible", "reasons": []}

_NEEDS_REVIEW_CLASSIFICATION = MagicMock(
    decision="needs_review",
    reasons=["no known manifest file"],
    full_name="aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
)
_NEEDS_REVIEW_CLASSIFICATION.to_dict.return_value = {
    "decision": "needs_review",
    "reasons": ["no known manifest file"],
}


def _make_scan_state(tmp_path: Path, slugs: list) -> Path:
    p = tmp_path / "scan_state.json"
    p.write_text(
        json.dumps({"last_scan_ts": "2026-03-22T00:00:00+00:00", "seen_repos": slugs, "total_discovered": len(slugs)}),
        encoding="utf-8",
    )
    return p


def _make_output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "configs" / "pilots"
    d.mkdir(parents=True)
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sync_generates_missing_config(tmp_path: Path) -> None:
    """Repo in scan_state with no existing config → config file written."""
    ss = _make_scan_state(tmp_path, ["aspose-cells-foss/Aspose.Cells-FOSS-for-Python"])
    out_dir = _make_output_dir(tmp_path)
    work_dir = tmp_path / "intake"
    work_dir.mkdir()

    inspection_mock = MagicMock()
    generated_path = out_dir / "aspose-cells-foss-python.yaml"

    with (
        patch("launcher.cli.intake._repo_root", return_value=tmp_path),
        patch("launcher.phase1.config_generator.check_dedup", return_value=False),
        patch("launcher.intake.org_scanner.scan_org", return_value=[_MINIMAL_REPO]),
        patch("launcher.phase1.inspection.inspect_repo", return_value=inspection_mock),
        patch("launcher.phase1.classification.classify_inspection", return_value=_ELIGIBLE_CLASSIFICATION),
        patch("launcher.phase1.inspection.write_inspection_artifact"),
        patch("launcher.phase1.config_generator.write_config", return_value=generated_path) as mock_write,
    ):
        result = runner.invoke(
            intake_app,
            ["sync", "--scan-state", str(ss), "--output", str(out_dir)],
        )

    assert result.exit_code == 0, result.output
    mock_write.assert_called_once()
    assert "generated" in result.output.lower()
    assert "aspose-cells-foss/Aspose.Cells-FOSS-for-Python" in result.output


def test_sync_skips_existing_config(tmp_path: Path) -> None:
    """Repo with existing config → check_dedup returns True → no write call."""
    ss = _make_scan_state(tmp_path, ["aspose-cells-foss/Aspose.Cells-FOSS-for-Python"])
    out_dir = _make_output_dir(tmp_path)

    with (
        patch("launcher.cli.intake._repo_root", return_value=tmp_path),
        patch("launcher.phase1.config_generator.check_dedup", return_value=True),
        patch("launcher.phase1.config_generator.write_config") as mock_write,
    ):
        result = runner.invoke(
            intake_app,
            ["sync", "--scan-state", str(ss), "--output", str(out_dir)],
        )

    assert result.exit_code == 0, result.output
    mock_write.assert_not_called()
    assert "[exists]" in result.output
    assert "aspose-cells-foss/Aspose.Cells-FOSS-for-Python" in result.output


def test_sync_reports_needs_review(tmp_path: Path) -> None:
    """Repo classified as needs_review → reported with reason, not crashed."""
    ss = _make_scan_state(tmp_path, ["aspose-cells-foss/Aspose.Cells-FOSS-for-Python"])
    out_dir = _make_output_dir(tmp_path)

    inspection_mock = MagicMock()

    with (
        patch("launcher.cli.intake._repo_root", return_value=tmp_path),
        patch("launcher.phase1.config_generator.check_dedup", return_value=False),
        patch("launcher.intake.org_scanner.scan_org", return_value=[_MINIMAL_REPO]),
        patch("launcher.phase1.inspection.inspect_repo", return_value=inspection_mock),
        patch("launcher.phase1.classification.classify_inspection", return_value=_NEEDS_REVIEW_CLASSIFICATION),
        patch("launcher.phase1.inspection.write_inspection_artifact"),
        patch("launcher.phase1.config_generator.write_config") as mock_write,
    ):
        result = runner.invoke(
            intake_app,
            ["sync", "--scan-state", str(ss), "--output", str(out_dir)],
        )

    assert result.exit_code == 0, result.output
    mock_write.assert_not_called()
    assert "needs_review" in result.output
    assert "no known manifest file" in result.output


def test_sync_dry_run(tmp_path: Path) -> None:
    """dry_run=True → classification runs, but write_config never called."""
    ss = _make_scan_state(tmp_path, ["aspose-cells-foss/Aspose.Cells-FOSS-for-Python"])
    out_dir = _make_output_dir(tmp_path)

    inspection_mock = MagicMock()

    with (
        patch("launcher.cli.intake._repo_root", return_value=tmp_path),
        patch("launcher.phase1.config_generator.check_dedup", return_value=False),
        patch("launcher.intake.org_scanner.scan_org", return_value=[_MINIMAL_REPO]),
        patch("launcher.phase1.inspection.inspect_repo", return_value=inspection_mock),
        patch("launcher.phase1.classification.classify_inspection", return_value=_ELIGIBLE_CLASSIFICATION),
        patch("launcher.phase1.inspection.write_inspection_artifact"),
        patch("launcher.phase1.config_generator.write_config") as mock_write,
    ):
        result = runner.invoke(
            intake_app,
            ["sync", "--scan-state", str(ss), "--output", str(out_dir), "--dry-run"],
        )

    assert result.exit_code == 0, result.output
    mock_write.assert_not_called()
    assert "would generate" in result.output
    assert "Dry-run mode" in result.output

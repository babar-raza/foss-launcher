"""
TC-520: Test run_pilot.py in dry-run mode.

These tests are hermetic and fast - they validate config only, no network/execution.
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "scripts"))

from run_pilot import run_pilot


def test_run_pilot_dry_run_aspose_3d():
    """
    Test dry-run mode for pilot-aspose-3d-foss-python.

    Should validate config without network or execution.
    """
    report = run_pilot(
        pilot_id="pilot-aspose-3d-foss-python",
        dry_run=True,
        output_path=None
    )

    # Should return a report
    assert isinstance(report, dict), "run_pilot should return a dictionary"

    # Should indicate dry-run mode
    assert report["dry_run"] is True, "Report should indicate dry-run mode"

    # Should validate config
    assert "validation_passed" in report, "Report should include validation_passed"

    # Config may or may not be valid (placeholders might cause schema failures)
    # But the validation process should complete without exceptions
    assert report["pilot_id"] == "pilot-aspose-3d-foss-python"

    # Should not have execution results in dry-run
    assert "exit_code" not in report, "Dry-run should not execute pilot"
    assert "run_dir" not in report, "Dry-run should not create run directory"


def test_run_pilot_dry_run_invalid_pilot():
    """Test that invalid pilot ID raises appropriate error."""
    with pytest.raises(ValueError, match="not found"):
        run_pilot(
            pilot_id="nonexistent-pilot",
            dry_run=True,
            output_path=None
        )


def test_run_pilot_dry_run_no_network():
    """
    Test that dry-run mode does not make network calls.

    This is a smoke test - we can't guarantee no network without mocking,
    but we can verify it completes quickly (< 5 seconds) which suggests
    no large downloads or network operations.
    """
    import time

    start = time.time()
    report = run_pilot(
        pilot_id="pilot-aspose-3d-foss-python",
        dry_run=True,
        output_path=None
    )
    elapsed = time.time() - start

    # Should complete quickly (no cloning, no network)
    assert elapsed < 5.0, f"Dry-run took {elapsed:.2f}s, expected < 5s (suggests network activity)"


def test_run_pilot_output_json():
    """Test that --output writes valid JSON report."""
    import json
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        output_path = Path(f.name)

    try:
        report = run_pilot(
            pilot_id="pilot-aspose-3d-foss-python",
            dry_run=True,
            output_path=output_path
        )

        # Output file should exist
        assert output_path.exists(), "Output file should be created"

        # Should contain valid JSON
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should match returned report
        assert data["pilot_id"] == report["pilot_id"]
        assert data["dry_run"] == report["dry_run"]

    finally:
        # Cleanup
        if output_path.exists():
            output_path.unlink()

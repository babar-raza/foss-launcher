"""Unit tests for TC-935: Validation report determinism.

Tests that validation_report.json is deterministic across runs with different
run_dir values (different timestamps/run IDs).

Per TC-935 acceptance criteria:
- validation_report.json contains no run-specific absolute paths
- Two runs with different run_dir produce identical canonical JSON SHA256
"""

import hashlib
import json
from pathlib import Path

import pytest

from src.launch.workers.w7_validator.worker import normalize_report


def test_normalize_report_makes_paths_relative():
    """Test that absolute paths are normalized to relative paths."""
    run_dir1 = Path("C:/Users/test/foss-launcher/runs/r_20260203T010000Z_test_abc123")
    run_dir2 = Path("C:/Users/test/foss-launcher/runs/r_20260203T020000Z_test_def456")

    # Build a sample report with absolute paths
    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "default",
        "gates": [{"name": "gate_1", "ok": False}],
        "issues": [
            {
                "error_code": "TEST_ERROR",
                "gate": "gate_1",
                "issue_id": "test_issue_1",
                "location": {
                    "path": str(run_dir1 / "artifacts" / "page_plan.json")
                },
                "message": "Test error",
                "severity": "error",
                "status": "OPEN",
            },
            {
                "error_code": "TEST_ERROR_2",
                "gate": "gate_1",
                "issue_id": "test_issue_2",
                "location": {
                    "path": str(run_dir1 / "artifacts" / "validation_report.json")
                },
                "message": "Test error 2",
                "severity": "warn",
                "status": "OPEN",
            },
        ],
    }

    # Normalize with first run_dir
    normalized1 = normalize_report(report, run_dir1)

    # Build same report but with second run_dir paths
    report2 = json.loads(json.dumps(report))
    report2["issues"][0]["location"]["path"] = str(run_dir2 / "artifacts" / "page_plan.json")
    report2["issues"][1]["location"]["path"] = str(
        run_dir2 / "artifacts" / "validation_report.json"
    )

    # Normalize with second run_dir
    normalized2 = normalize_report(report2, run_dir2)

    # Check that paths are now relative
    assert normalized1["issues"][0]["location"]["path"] == "artifacts/page_plan.json"
    assert normalized1["issues"][1]["location"]["path"] == "artifacts/validation_report.json"
    assert normalized2["issues"][0]["location"]["path"] == "artifacts/page_plan.json"
    assert normalized2["issues"][1]["location"]["path"] == "artifacts/validation_report.json"

    # Check that canonical JSON hashes match (determinism proof)
    canonical1 = json.dumps(normalized1, sort_keys=True, indent=2)
    canonical2 = json.dumps(normalized2, sort_keys=True, indent=2)

    hash1 = hashlib.sha256(canonical1.encode("utf-8")).hexdigest()
    hash2 = hashlib.sha256(canonical2.encode("utf-8")).hexdigest()

    assert hash1 == hash2, "Canonical JSON hashes must match for determinism"


def test_normalize_report_preserves_non_run_dir_paths():
    """Test that paths outside run_dir are preserved as-is."""
    run_dir = Path("C:/Users/test/foss-launcher/runs/r_20260203T010000Z_test_abc123")

    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "default",
        "gates": [{"name": "gate_1", "ok": False}],
        "issues": [
            {
                "error_code": "TEST_ERROR",
                "gate": "gate_1",
                "issue_id": "test_issue",
                "location": {"path": "C:/external/file.txt"},
                "message": "Test error",
                "severity": "error",
                "status": "OPEN",
            }
        ],
    }

    normalized = normalize_report(report, run_dir)

    # External path should remain unchanged
    assert normalized["issues"][0]["location"]["path"] == "C:/external/file.txt"


def test_normalize_report_handles_missing_location():
    """Test that issues without location field are handled gracefully."""
    run_dir = Path("C:/Users/test/foss-launcher/runs/r_20260203T010000Z_test_abc123")

    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "default",
        "gates": [{"name": "gate_1", "ok": False}],
        "issues": [
            {
                "error_code": "TEST_ERROR",
                "gate": "gate_1",
                "issue_id": "test_issue",
                "message": "Test error without location",
                "severity": "error",
                "status": "OPEN",
            }
        ],
    }

    normalized = normalize_report(report, run_dir)

    # Should not raise exception, issue should be unchanged
    assert "location" not in normalized["issues"][0]


def test_normalize_report_handles_empty_issues():
    """Test that reports with no issues are handled correctly."""
    run_dir = Path("C:/Users/test/foss-launcher/runs/r_20260203T010000Z_test_abc123")

    report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "default",
        "gates": [{"name": "gate_1", "ok": True}],
        "issues": [],
    }

    normalized = normalize_report(report, run_dir)

    assert normalized["issues"] == []
    assert normalized["ok"] is True


def test_normalize_report_determinism_with_windows_paths():
    """Test determinism with Windows-style backslash paths."""
    run_dir1 = Path(r"C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\r_20260203T025743Z_launch_pilot_abc")
    run_dir2 = Path(r"C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\r_20260203T030007Z_launch_pilot_def")

    report1 = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "default",
        "gates": [{"name": "gate_1", "ok": False}],
        "issues": [
            {
                "error_code": "GATE_SCHEMA_VALIDATION_FAILED",
                "gate": "gate_1_schema_validation",
                "issue_id": "schema_validation_evidence_map.json",
                "location": {
                    "path": str(run_dir1 / "artifacts" / "evidence_map.json")
                },
                "message": "Schema validation error",
                "severity": "blocker",
                "status": "OPEN",
            }
        ],
    }

    report2 = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "default",
        "gates": [{"name": "gate_1", "ok": False}],
        "issues": [
            {
                "error_code": "GATE_SCHEMA_VALIDATION_FAILED",
                "gate": "gate_1_schema_validation",
                "issue_id": "schema_validation_evidence_map.json",
                "location": {
                    "path": str(run_dir2 / "artifacts" / "evidence_map.json")
                },
                "message": "Schema validation error",
                "severity": "blocker",
                "status": "OPEN",
            }
        ],
    }

    normalized1 = normalize_report(report1, run_dir1)
    normalized2 = normalize_report(report2, run_dir2)

    # Paths should be normalized to forward slashes
    assert normalized1["issues"][0]["location"]["path"] == "artifacts/evidence_map.json"
    assert normalized2["issues"][0]["location"]["path"] == "artifacts/evidence_map.json"

    # Canonical JSON should match
    canonical1 = json.dumps(normalized1, sort_keys=True, indent=2)
    canonical2 = json.dumps(normalized2, sort_keys=True, indent=2)

    hash1 = hashlib.sha256(canonical1.encode("utf-8")).hexdigest()
    hash2 = hashlib.sha256(canonical2.encode("utf-8")).hexdigest()

    assert hash1 == hash2

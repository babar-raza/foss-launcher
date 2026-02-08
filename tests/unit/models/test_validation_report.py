"""Tests for ValidationReport model.

Validates:
- ValidationReport serialization (to_dict/from_dict)
- Round-trip consistency
- Optional fields handling
- Validation logic
- Sub-component models (GateResult, Issue, IssueLocation)

TC-1031: Typed Artifact Models -- Worker Models
"""

import pytest

from src.launch.models.validation_report import (
    GateResult,
    Issue,
    IssueLocation,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_issue_data() -> dict:
    """Create minimal Issue dict for testing."""
    return {
        "issue_id": "test_issue_001",
        "gate": "gate_1_schema_validation",
        "severity": "error",
        "message": "Invalid JSON in artifact.json",
        "status": "OPEN",
        "error_code": "GATE_SCHEMA_VALIDATION_FAILED",
    }


def _minimal_gate_result_data() -> dict:
    """Create minimal GateResult dict for testing."""
    return {
        "name": "gate_1_schema_validation",
        "ok": True,
    }


def _minimal_report_data() -> dict:
    """Create minimal ValidationReport dict for testing."""
    return {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [_minimal_gate_result_data()],
        "issues": [],
    }


# ---------------------------------------------------------------------------
# IssueLocation tests
# ---------------------------------------------------------------------------

def test_issue_location_minimal():
    """Test IssueLocation with no fields."""
    loc = IssueLocation()
    data = loc.to_dict()
    assert data == {}


def test_issue_location_full():
    """Test IssueLocation with all fields."""
    loc = IssueLocation(path="content/docs/test.md", line=42)
    data = loc.to_dict()
    assert data["path"] == "content/docs/test.md"
    assert data["line"] == 42


def test_issue_location_round_trip():
    """Test IssueLocation round-trip."""
    original = IssueLocation(path="test.md", line=10)
    data = original.to_dict()
    restored = IssueLocation.from_dict(data)
    assert restored.path == original.path
    assert restored.line == original.line


# ---------------------------------------------------------------------------
# Issue tests
# ---------------------------------------------------------------------------

def test_issue_minimal():
    """Test Issue with required fields only."""
    issue = Issue(
        issue_id="test_001",
        gate="gate_1",
        severity="warn",
        message="Warning message",
        status="OPEN",
    )
    data = issue.to_dict()
    assert data["issue_id"] == "test_001"
    assert data["gate"] == "gate_1"
    assert data["severity"] == "warn"
    assert data["message"] == "Warning message"
    assert data["status"] == "OPEN"
    assert "error_code" not in data
    assert "location" not in data
    assert "files" not in data


def test_issue_full():
    """Test Issue with all fields."""
    issue = Issue(
        issue_id="test_002",
        gate="gate_2_claim_marker_validity",
        severity="blocker",
        message="Missing claim marker",
        status="OPEN",
        error_code="GATE_CLAIM_MARKER_MISSING",
        code=201,
        files=["page_b.md", "page_a.md"],
        location=IssueLocation(path="content/test.md", line=5),
        suggested_fix="Add [claim: claim_001] marker",
    )
    data = issue.to_dict()
    assert data["error_code"] == "GATE_CLAIM_MARKER_MISSING"
    assert data["code"] == 201
    assert data["files"] == ["page_a.md", "page_b.md"]  # sorted
    assert data["location"]["path"] == "content/test.md"
    assert data["location"]["line"] == 5
    assert data["suggested_fix"] == "Add [claim: claim_001] marker"


def test_issue_from_dict():
    """Test Issue.from_dict."""
    data = _minimal_issue_data()
    issue = Issue.from_dict(data)
    assert issue.issue_id == "test_issue_001"
    assert issue.gate == "gate_1_schema_validation"
    assert issue.severity == "error"
    assert issue.error_code == "GATE_SCHEMA_VALIDATION_FAILED"


def test_issue_round_trip():
    """Test Issue round-trip."""
    data = _minimal_issue_data()
    data["location"] = {"path": "test.md", "line": 10}
    data["suggested_fix"] = "Fix the JSON"
    original = Issue.from_dict(data)
    serialized = original.to_dict()
    restored = Issue.from_dict(serialized)
    assert restored.issue_id == original.issue_id
    assert restored.severity == original.severity
    assert restored.location.path == original.location.path
    assert restored.suggested_fix == original.suggested_fix


# ---------------------------------------------------------------------------
# GateResult tests
# ---------------------------------------------------------------------------

def test_gate_result_minimal():
    """Test GateResult with required fields only."""
    gate = GateResult(name="gate_1", ok=True)
    data = gate.to_dict()
    assert data["name"] == "gate_1"
    assert data["ok"] is True
    assert "log_path" not in data


def test_gate_result_with_log_path():
    """Test GateResult with log_path."""
    gate = GateResult(name="gate_13_hugo_build", ok=False, log_path="logs/hugo.log")
    data = gate.to_dict()
    assert data["log_path"] == "logs/hugo.log"
    assert data["ok"] is False


def test_gate_result_round_trip():
    """Test GateResult round-trip."""
    original = GateResult(name="gate_t_test_determinism", ok=True)
    data = original.to_dict()
    restored = GateResult.from_dict(data)
    assert restored.name == original.name
    assert restored.ok == original.ok


# ---------------------------------------------------------------------------
# ValidationReport tests
# ---------------------------------------------------------------------------

def test_validation_report_minimal():
    """Test ValidationReport with minimal required fields."""
    report = ValidationReport(
        schema_version="1.0",
        ok=True,
        profile="local",
    )
    data = report.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["ok"] is True
    assert data["profile"] == "local"
    assert data["gates"] == []
    assert data["issues"] == []
    assert "manual_edits" not in data
    assert "manual_edited_files" not in data


def test_validation_report_with_gates_and_issues():
    """Test ValidationReport with gates and issues."""
    report = ValidationReport(
        schema_version="1.0",
        ok=False,
        profile="ci",
        gates=[
            GateResult(name="gate_1", ok=True),
            GateResult(name="gate_2", ok=False),
        ],
        issues=[
            Issue(
                issue_id="issue_001",
                gate="gate_2",
                severity="error",
                message="Test error",
                status="OPEN",
                error_code="TEST_ERROR",
            ),
        ],
    )
    data = report.to_dict()
    assert data["ok"] is False
    assert len(data["gates"]) == 2
    assert len(data["issues"]) == 1
    assert data["issues"][0]["issue_id"] == "issue_001"


def test_validation_report_with_manual_edits():
    """Test ValidationReport with manual edits fields."""
    report = ValidationReport(
        schema_version="1.0",
        ok=True,
        profile="local",
        manual_edits=True,
        manual_edited_files=["file_b.md", "file_a.md"],
    )
    data = report.to_dict()
    assert data["manual_edits"] is True
    assert data["manual_edited_files"] == ["file_a.md", "file_b.md"]  # sorted


def test_validation_report_from_dict():
    """Test ValidationReport.from_dict."""
    data = _minimal_report_data()
    report = ValidationReport.from_dict(data)
    assert report.ok is True
    assert report.profile == "local"
    assert len(report.gates) == 1
    assert report.gates[0].name == "gate_1_schema_validation"


def test_validation_report_round_trip():
    """Test ValidationReport round-trip."""
    data = _minimal_report_data()
    data["issues"] = [_minimal_issue_data()]
    data["ok"] = False

    original = ValidationReport.from_dict(data)
    serialized = original.to_dict()
    restored = ValidationReport.from_dict(serialized)
    assert restored.ok == original.ok
    assert restored.profile == original.profile
    assert len(restored.gates) == len(original.gates)
    assert len(restored.issues) == len(original.issues)
    assert restored.issues[0].issue_id == original.issues[0].issue_id


def test_validation_report_validate_valid():
    """Test validate() on valid report."""
    data = _minimal_report_data()
    report = ValidationReport.from_dict(data)
    assert report.validate() is True


def test_validation_report_validate_invalid_profile():
    """Test validate() rejects invalid profile."""
    report = ValidationReport(
        schema_version="1.0",
        ok=True,
        profile="invalid_profile",
    )
    with pytest.raises(ValueError, match="profile"):
        report.validate()


def test_validation_report_validate_invalid_severity():
    """Test validate() rejects invalid issue severity."""
    report = ValidationReport(
        schema_version="1.0",
        ok=True,
        profile="local",
        issues=[
            Issue(
                issue_id="bad",
                gate="test",
                severity="invalid_severity",
                message="Bad issue",
                status="OPEN",
            ),
        ],
    )
    with pytest.raises(ValueError, match="severity"):
        report.validate()


def test_validation_report_validate_invalid_status():
    """Test validate() rejects invalid issue status."""
    report = ValidationReport(
        schema_version="1.0",
        ok=True,
        profile="local",
        issues=[
            Issue(
                issue_id="bad",
                gate="test",
                severity="warn",
                message="Bad issue",
                status="INVALID_STATUS",
            ),
        ],
    )
    with pytest.raises(ValueError, match="status"):
        report.validate()


def test_validation_report_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_report_data()
    report = ValidationReport.from_dict(data)
    json_str = report.to_json()
    restored = ValidationReport.from_json(json_str)
    assert restored.ok == report.ok
    assert restored.profile == report.profile
    assert len(restored.gates) == len(report.gates)

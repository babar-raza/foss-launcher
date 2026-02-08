"""Tests for TruthLockReport model.

Validates:
- TruthLockReport serialization (to_dict/from_dict)
- Round-trip consistency
- Sub-component models (TruthLockPage, Issue)
- Validation logic

TC-1030: Typed Artifact Models -- Foundation
"""

import pytest

from src.launch.models.truth_lock import Issue, TruthLockPage, TruthLockReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_truth_lock_data() -> dict:
    """Create minimal TruthLockReport dict for testing."""
    return {
        "schema_version": "1.0",
        "ok": True,
        "pages": [],
        "unresolved_claim_ids": [],
        "issues": [],
    }


# ---------------------------------------------------------------------------
# TruthLockPage tests
# ---------------------------------------------------------------------------

def test_truth_lock_page():
    """Test TruthLockPage serialization."""
    page = TruthLockPage(
        path="content/en/python/getting-started.md",
        claim_ids=["c3", "c1", "c2"],
    )
    data = page.to_dict()
    assert data["path"] == "content/en/python/getting-started.md"
    assert data["claim_ids"] == ["c1", "c2", "c3"]  # sorted


def test_truth_lock_page_round_trip():
    """Test TruthLockPage round-trip."""
    original = TruthLockPage(
        path="content/en/python/overview.md",
        claim_ids=["c2", "c1"],
    )
    data = original.to_dict()
    restored = TruthLockPage.from_dict(data)
    assert restored.path == original.path
    assert sorted(restored.claim_ids) == sorted(original.claim_ids)


# ---------------------------------------------------------------------------
# Issue tests
# ---------------------------------------------------------------------------

def test_issue_minimal():
    """Test Issue with required fields only."""
    issue = Issue(
        issue_id="ISS-001",
        gate="gate_8",
        severity="warn",
        message="Missing claim coverage",
        status="OPEN",
    )
    data = issue.to_dict()
    assert data["issue_id"] == "ISS-001"
    assert data["gate"] == "gate_8"
    assert data["severity"] == "warn"
    assert data["message"] == "Missing claim coverage"
    assert data["status"] == "OPEN"
    assert "error_code" not in data
    assert "files" not in data
    assert "location" not in data
    assert "suggested_fix" not in data


def test_issue_full():
    """Test Issue with all fields."""
    issue = Issue(
        issue_id="ISS-002",
        gate="gate_4",
        severity="error",
        message="Missing required frontmatter field 'title'",
        status="OPEN",
        error_code="FRONTMATTER_MISSING_FIELD",
        files=["content/en/getting-started.md", "content/en/overview.md"],
        location={"path": "content/en/getting-started.md", "line": 1},
        suggested_fix="Add 'title' field to frontmatter",
    )
    data = issue.to_dict()
    assert data["error_code"] == "FRONTMATTER_MISSING_FIELD"
    assert data["files"] == ["content/en/getting-started.md", "content/en/overview.md"]  # sorted
    assert data["location"]["path"] == "content/en/getting-started.md"
    assert data["suggested_fix"] == "Add 'title' field to frontmatter"


def test_issue_round_trip():
    """Test Issue round-trip."""
    original = Issue(
        issue_id="ISS-003",
        gate="gate_5",
        severity="info",
        message="Cross-link target exists",
        status="RESOLVED",
        files=["content/en/a.md"],
    )
    data = original.to_dict()
    restored = Issue.from_dict(data)
    assert restored.issue_id == original.issue_id
    assert restored.gate == original.gate
    assert restored.severity == original.severity
    assert restored.status == original.status
    assert restored.files == original.files


# ---------------------------------------------------------------------------
# TruthLockReport tests
# ---------------------------------------------------------------------------

def test_truth_lock_report_minimal():
    """Test TruthLockReport with minimal data."""
    data = _minimal_truth_lock_data()
    report = TruthLockReport.from_dict(data)
    assert report.ok is True
    assert report.pages == []
    assert report.unresolved_claim_ids == []
    assert report.issues == []
    assert report.inferred_claim_ids is None
    assert report.forbidden_inferred_claim_ids is None


def test_truth_lock_report_full():
    """Test TruthLockReport with all fields."""
    report = TruthLockReport(
        schema_version="1.0",
        ok=False,
        pages=[
            TruthLockPage(path="page1.md", claim_ids=["c1", "c2"]),
            TruthLockPage(path="page2.md", claim_ids=["c3"]),
        ],
        unresolved_claim_ids=["c4", "c5"],
        issues=[
            Issue(
                issue_id="ISS-001",
                gate="gate_8",
                severity="error",
                message="Unresolved claims",
                status="OPEN",
                error_code="UNRESOLVED_CLAIMS",
            ),
        ],
        inferred_claim_ids=["c6"],
        forbidden_inferred_claim_ids=["c7"],
    )
    data = report.to_dict()
    assert data["ok"] is False
    assert len(data["pages"]) == 2
    assert data["unresolved_claim_ids"] == ["c4", "c5"]  # sorted
    assert len(data["issues"]) == 1
    assert data["inferred_claim_ids"] == ["c6"]
    assert data["forbidden_inferred_claim_ids"] == ["c7"]


def test_truth_lock_report_round_trip():
    """Test TruthLockReport serialization round-trip."""
    data = {
        "schema_version": "1.0",
        "ok": False,
        "pages": [
            {"path": "page1.md", "claim_ids": ["c2", "c1"]},
            {"path": "page2.md", "claim_ids": ["c3"]},
        ],
        "unresolved_claim_ids": ["c5", "c4"],
        "issues": [
            {
                "issue_id": "ISS-001",
                "gate": "gate_8",
                "severity": "warn",
                "message": "Coverage gap",
                "status": "OPEN",
            },
        ],
        "inferred_claim_ids": ["c6", "c7"],
        "forbidden_inferred_claim_ids": ["c8"],
    }
    original = TruthLockReport.from_dict(data)
    serialized = original.to_dict()
    restored = TruthLockReport.from_dict(serialized)

    assert restored.ok == original.ok
    assert len(restored.pages) == len(original.pages)
    assert sorted(restored.unresolved_claim_ids) == sorted(original.unresolved_claim_ids)
    assert len(restored.issues) == len(original.issues)
    assert sorted(restored.inferred_claim_ids) == sorted(original.inferred_claim_ids)


def test_truth_lock_report_validate_valid():
    """Test validate() on valid TruthLockReport."""
    report = TruthLockReport(
        schema_version="1.0",
        ok=True,
        pages=[],
        unresolved_claim_ids=[],
        issues=[],
    )
    assert report.validate() is True


def test_truth_lock_report_validate_valid_with_issues():
    """Test validate() with properly structured issues."""
    report = TruthLockReport(
        schema_version="1.0",
        ok=False,
        pages=[],
        unresolved_claim_ids=["c1"],
        issues=[
            Issue(
                issue_id="ISS-001",
                gate="gate_8",
                severity="error",
                message="Unresolved",
                status="OPEN",
                error_code="UNRESOLVED_CLAIMS",
            ),
        ],
    )
    assert report.validate() is True


def test_truth_lock_report_validate_invalid_severity():
    """Test validate() rejects invalid issue severity."""
    report = TruthLockReport(
        schema_version="1.0",
        ok=True,
        pages=[],
        unresolved_claim_ids=[],
        issues=[
            Issue(
                issue_id="ISS-001",
                gate="gate_1",
                severity="critical",  # Invalid
                message="Bad",
                status="OPEN",
            ),
        ],
    )
    with pytest.raises(ValueError, match="invalid severity"):
        report.validate()


def test_truth_lock_report_validate_invalid_status():
    """Test validate() rejects invalid issue status."""
    report = TruthLockReport(
        schema_version="1.0",
        ok=True,
        pages=[],
        unresolved_claim_ids=[],
        issues=[
            Issue(
                issue_id="ISS-001",
                gate="gate_1",
                severity="info",
                message="Something",
                status="CLOSED",  # Invalid
            ),
        ],
    )
    with pytest.raises(ValueError, match="invalid status"):
        report.validate()


def test_truth_lock_report_validate_error_requires_code():
    """Test validate() requires error_code for error/blocker severity."""
    report = TruthLockReport(
        schema_version="1.0",
        ok=False,
        pages=[],
        unresolved_claim_ids=[],
        issues=[
            Issue(
                issue_id="ISS-001",
                gate="gate_8",
                severity="error",
                message="Missing code",
                status="OPEN",
                # No error_code!
            ),
        ],
    )
    with pytest.raises(ValueError, match="error_code"):
        report.validate()


def test_truth_lock_report_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_truth_lock_data()
    report = TruthLockReport.from_dict(data)
    json_str = report.to_json()
    restored = TruthLockReport.from_json(json_str)
    assert restored.ok == report.ok
    assert restored.pages == []

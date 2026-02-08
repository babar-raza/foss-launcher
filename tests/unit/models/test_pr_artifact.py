"""Tests for PRResult model.

Validates:
- PRResult serialization (to_dict/from_dict)
- Round-trip consistency
- Optional fields handling
- Validation logic
- Sub-component models (ValidationSummary)

TC-1031: Typed Artifact Models -- Worker Models
"""

import pytest

from src.launch.models.pr_artifact import (
    PRResult,
    ValidationSummary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_pr_data() -> dict:
    """Create minimal PRResult dict for testing."""
    return {
        "schema_version": "1.0",
        "run_id": "RUN-20260207-120000Z-abc123",
        "base_ref": "a" * 40,
        "rollback_steps": [
            "git fetch origin",
            "git revert --no-commit abc123",
            "git commit -m 'Rollback'",
            "git push origin main",
        ],
        "affected_paths": [
            "content/docs/python/overview/_index.md",
            "content/docs/python/install/_index.md",
        ],
    }


# ---------------------------------------------------------------------------
# ValidationSummary tests
# ---------------------------------------------------------------------------

def test_validation_summary_minimal():
    """Test ValidationSummary with no fields."""
    summary = ValidationSummary()
    data = summary.to_dict()
    assert data == {}


def test_validation_summary_full():
    """Test ValidationSummary with all fields."""
    summary = ValidationSummary(
        ok=True,
        profile="local",
        gates_passed=15,
        gates_failed=0,
    )
    data = summary.to_dict()
    assert data["ok"] is True
    assert data["profile"] == "local"
    assert data["gates_passed"] == 15
    assert data["gates_failed"] == 0


def test_validation_summary_round_trip():
    """Test ValidationSummary round-trip."""
    original = ValidationSummary(ok=False, profile="ci", gates_passed=10, gates_failed=2)
    data = original.to_dict()
    restored = ValidationSummary.from_dict(data)
    assert restored.ok == original.ok
    assert restored.profile == original.profile
    assert restored.gates_passed == original.gates_passed
    assert restored.gates_failed == original.gates_failed


# ---------------------------------------------------------------------------
# PRResult tests
# ---------------------------------------------------------------------------

def test_pr_result_minimal():
    """Test PRResult with minimal required fields."""
    pr = PRResult(
        schema_version="1.0",
        run_id="RUN-001",
        base_ref="a" * 40,
        rollback_steps=["git revert HEAD"],
        affected_paths=["content/test.md"],
    )
    data = pr.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["run_id"] == "RUN-001"
    assert data["base_ref"] == "a" * 40
    assert data["rollback_steps"] == ["git revert HEAD"]
    assert data["affected_paths"] == ["content/test.md"]
    assert "pr_number" not in data
    assert "pr_url" not in data
    assert "branch_name" not in data
    assert "commit_shas" not in data
    assert "pr_body" not in data
    assert "validation_summary" not in data


def test_pr_result_with_optional():
    """Test PRResult with all optional fields."""
    pr = PRResult(
        schema_version="1.0",
        run_id="RUN-001",
        base_ref="b" * 40,
        rollback_steps=["git fetch origin", "git revert HEAD"],
        affected_paths=["content/b.md", "content/a.md"],
        pr_number=42,
        pr_url="https://github.com/Aspose/repo/pull/42",
        branch_name="launch/aspose-3d/main/abc123",
        commit_shas=["c" * 40],
        pr_body="## Summary\nAutomated launch",
        validation_summary=ValidationSummary(ok=True, profile="local", gates_passed=15, gates_failed=0),
    )
    data = pr.to_dict()
    assert data["pr_number"] == 42
    assert data["pr_url"] == "https://github.com/Aspose/repo/pull/42"
    assert data["branch_name"] == "launch/aspose-3d/main/abc123"
    assert data["commit_shas"] == ["c" * 40]
    assert data["pr_body"] == "## Summary\nAutomated launch"
    assert data["validation_summary"]["ok"] is True
    # affected_paths should be sorted
    assert data["affected_paths"] == ["content/a.md", "content/b.md"]


def test_pr_result_from_dict():
    """Test PRResult.from_dict."""
    data = _minimal_pr_data()
    pr = PRResult.from_dict(data)
    assert pr.run_id == "RUN-20260207-120000Z-abc123"
    assert pr.base_ref == "a" * 40
    assert len(pr.rollback_steps) == 4
    assert len(pr.affected_paths) == 2


def test_pr_result_from_dict_with_optional():
    """Test PRResult.from_dict with optional fields."""
    data = _minimal_pr_data()
    data["pr_number"] = 100
    data["pr_url"] = "https://github.com/test/repo/pull/100"
    data["validation_summary"] = {
        "ok": True,
        "profile": "ci",
        "gates_passed": 12,
        "gates_failed": 1,
    }
    pr = PRResult.from_dict(data)
    assert pr.pr_number == 100
    assert pr.pr_url == "https://github.com/test/repo/pull/100"
    assert pr.validation_summary.ok is True
    assert pr.validation_summary.gates_passed == 12


def test_pr_result_round_trip():
    """Test PRResult round-trip."""
    data = _minimal_pr_data()
    data["pr_number"] = 55
    data["pr_url"] = "https://github.com/test/repo/pull/55"
    data["branch_name"] = "launch/test/main/abc"
    data["commit_shas"] = ["d" * 40]
    data["validation_summary"] = {
        "ok": False,
        "profile": "prod",
        "gates_passed": 10,
        "gates_failed": 3,
    }

    original = PRResult.from_dict(data)
    serialized = original.to_dict()
    restored = PRResult.from_dict(serialized)
    assert restored.run_id == original.run_id
    assert restored.base_ref == original.base_ref
    assert restored.pr_number == original.pr_number
    assert restored.pr_url == original.pr_url
    assert restored.branch_name == original.branch_name
    assert restored.commit_shas == original.commit_shas
    assert restored.validation_summary.ok == original.validation_summary.ok
    assert restored.validation_summary.gates_failed == original.validation_summary.gates_failed


def test_pr_result_validate_valid():
    """Test validate() on valid PR result."""
    data = _minimal_pr_data()
    pr = PRResult.from_dict(data)
    assert pr.validate() is True


def test_pr_result_validate_empty_run_id():
    """Test validate() rejects empty run_id."""
    pr = PRResult(
        schema_version="1.0",
        run_id="",
        base_ref="a" * 40,
        rollback_steps=["git revert HEAD"],
        affected_paths=["test.md"],
    )
    with pytest.raises(ValueError, match="run_id"):
        pr.validate()


def test_pr_result_validate_empty_base_ref():
    """Test validate() rejects empty base_ref."""
    pr = PRResult(
        schema_version="1.0",
        run_id="RUN-001",
        base_ref="",
        rollback_steps=["git revert HEAD"],
        affected_paths=["test.md"],
    )
    with pytest.raises(ValueError, match="base_ref"):
        pr.validate()


def test_pr_result_validate_empty_rollback_steps():
    """Test validate() rejects empty rollback_steps."""
    pr = PRResult(
        schema_version="1.0",
        run_id="RUN-001",
        base_ref="a" * 40,
        rollback_steps=[],
        affected_paths=["test.md"],
    )
    with pytest.raises(ValueError, match="rollback_steps"):
        pr.validate()


def test_pr_result_validate_empty_affected_paths():
    """Test validate() rejects empty affected_paths."""
    pr = PRResult(
        schema_version="1.0",
        run_id="RUN-001",
        base_ref="a" * 40,
        rollback_steps=["git revert HEAD"],
        affected_paths=[],
    )
    with pytest.raises(ValueError, match="affected_paths"):
        pr.validate()


def test_pr_result_validate_invalid_pr_number():
    """Test validate() rejects pr_number < 1."""
    pr = PRResult(
        schema_version="1.0",
        run_id="RUN-001",
        base_ref="a" * 40,
        rollback_steps=["git revert HEAD"],
        affected_paths=["test.md"],
        pr_number=0,
    )
    with pytest.raises(ValueError, match="pr_number"):
        pr.validate()


def test_pr_result_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_pr_data()
    pr = PRResult.from_dict(data)
    json_str = pr.to_json()
    restored = PRResult.from_json(json_str)
    assert restored.run_id == pr.run_id
    assert restored.base_ref == pr.base_ref
    assert len(restored.rollback_steps) == len(pr.rollback_steps)

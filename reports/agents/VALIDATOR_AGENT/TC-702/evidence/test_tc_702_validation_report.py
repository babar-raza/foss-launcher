"""Unit tests for TC-702: Validation Report Deterministic Generation.

Tests validate that validation_report.json is deterministic across runs by:
- Normalizing paths with <RUN_DIR> and <REPO_ROOT> tokens
- Removing timestamps
- Stable sorting issues and gates
- Proving bit-for-bit identical output with canonical hashes
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w7_validator.worker import (
    compute_canonical_hash,
    normalize_validation_report,
)


def test_validation_report_normalization_basic():
    """Test basic path normalization in validation report."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [],
        "issues": [],
    }

    normalized = normalize_validation_report(report, run_dir)

    # Basic structure preserved
    assert normalized["schema_version"] == "1.0"
    assert normalized["ok"] is True
    assert normalized["profile"] == "local"


def test_path_normalization_run_dir():
    """Absolute run_dir paths must be replaced with <RUN_DIR> token."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "test_issue",
                "gate": "gate_1_schema_validation",
                "severity": "error",
                "message": "Issue in /tmp/runs/run_001/artifacts/foo.json",
                "location": {
                    "path": "/tmp/runs/run_001/work/site/content/test.md",
                    "line": 42
                },
                "status": "OPEN",
            }
        ],
    }

    normalized = normalize_validation_report(report, run_dir)

    # Check replacement in location path
    issue = normalized["issues"][0]
    assert "<RUN_DIR>" in issue["location"]["path"]
    assert "/tmp/runs/run_001" not in issue["location"]["path"]

    # Check replacement in message
    assert "<RUN_DIR>" in issue["message"]
    assert "/tmp/runs/run_001" not in issue["message"]


def test_path_normalization_repo_root():
    """Absolute repo root paths must be replaced with <REPO_ROOT> token."""
    run_dir = Path("/home/user/foss-launcher/runs/run_001")
    repo_root = run_dir.parent.parent

    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "test_issue",
                "gate": "gate_1_schema_validation",
                "severity": "error",
                "message": f"Schema file at {repo_root}/specs/schemas/test.schema.json",
                "location": {
                    "path": str(repo_root / "specs" / "schemas" / "test.schema.json"),
                    "line": 1
                },
                "status": "OPEN",
            }
        ],
    }

    normalized = normalize_validation_report(report, run_dir)

    issue = normalized["issues"][0]
    # Check replacement in location path
    assert "<REPO_ROOT>" in issue["location"]["path"]
    assert str(repo_root) not in issue["location"]["path"]

    # Check replacement in message
    assert "<REPO_ROOT>" in issue["message"]


def test_path_separator_normalization():
    """Windows backslashes must be normalized to forward slashes."""
    run_dir = Path(r"C:\Users\test\foss-launcher\runs\run_001")
    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "test_issue",
                "gate": "gate_1_schema_validation",
                "severity": "error",
                "message": r"Issue in C:\Users\test\foss-launcher\runs\run_001\work\site\test.md",
                "location": {
                    "path": r"C:\Users\test\foss-launcher\runs\run_001\work\site\test.md",
                    "line": 10
                },
                "status": "OPEN",
            }
        ],
    }

    normalized = normalize_validation_report(report, run_dir)

    issue = normalized["issues"][0]
    # Check forward slashes
    assert "\\" not in issue["location"]["path"]
    assert "/" in issue["location"]["path"]


def test_timestamp_removal():
    """Timestamps must be removed from report body."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [],
        "issues": [],
        "generated_at": "2026-01-30T12:34:56Z",
        "timestamp": "2026-01-30T12:34:56.123456",
    }

    normalized = normalize_validation_report(report, run_dir)

    # Timestamps removed
    assert "generated_at" not in normalized
    assert "timestamp" not in normalized


def test_stable_sorting_gates():
    """Gates must be sorted deterministically by name."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [
            {"name": "gate_z_last", "ok": True},
            {"name": "gate_a_first", "ok": False},
            {"name": "gate_m_middle", "ok": True},
        ],
        "issues": [],
    }

    normalized = normalize_validation_report(report, run_dir)

    # Gates sorted by name
    assert normalized["gates"][0]["name"] == "gate_a_first"
    assert normalized["gates"][1]["name"] == "gate_m_middle"
    assert normalized["gates"][2]["name"] == "gate_z_last"


def test_stable_sorting_issues():
    """Issues must be sorted deterministically by (path, line, message)."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "issue_3",
                "message": "Message B",
                "location": {"path": "b.md", "line": 10},
            },
            {
                "issue_id": "issue_1",
                "message": "Message A",
                "location": {"path": "a.md", "line": 5},
            },
            {
                "issue_id": "issue_2",
                "message": "Message C",
                "location": {"path": "b.md", "line": 5},
            },
        ],
    }

    normalized = normalize_validation_report(report, run_dir)

    # Issues sorted by (file, line, message)
    assert normalized["issues"][0]["location"]["path"] == "a.md"
    assert normalized["issues"][1]["location"]["path"] == "b.md"
    assert normalized["issues"][1]["location"]["line"] == 5
    assert normalized["issues"][2]["location"]["path"] == "b.md"
    assert normalized["issues"][2]["location"]["line"] == 10


def test_determinism_across_different_run_dirs():
    """Two runs with different run_dir must produce identical canonical JSON.

    This is the critical test for TC-702: proving bit-for-bit determinism.
    """
    # Setup two temporary run directories
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        run_dir1 = Path(tmp1) / "runs" / "run_001"
        run_dir2 = Path(tmp2) / "runs" / "run_002"
        run_dir1.mkdir(parents=True)
        run_dir2.mkdir(parents=True)

        # Create identical reports with different absolute paths
        report1 = {
            "schema_version": "1.0",
            "ok": False,
            "profile": "local",
            "gates": [
                {"name": "gate_1_schema_validation", "ok": True},
                {"name": "gate_11_template_token_lint", "ok": False},
            ],
            "issues": [
                {
                    "issue_id": "template_token_issue",
                    "gate": "gate_11_template_token_lint",
                    "severity": "blocker",
                    "message": f"Unresolved token in {run_dir1}/work/site/test.md",
                    "location": {
                        "path": f"{run_dir1}/work/site/test.md",
                        "line": 42
                    },
                    "status": "OPEN",
                }
            ],
            "generated_at": "2026-01-30T12:00:00Z",
        }

        report2 = {
            "schema_version": "1.0",
            "ok": False,
            "profile": "local",
            "gates": [
                {"name": "gate_1_schema_validation", "ok": True},
                {"name": "gate_11_template_token_lint", "ok": False},
            ],
            "issues": [
                {
                    "issue_id": "template_token_issue",
                    "gate": "gate_11_template_token_lint",
                    "severity": "blocker",
                    "message": f"Unresolved token in {run_dir2}/work/site/test.md",
                    "location": {
                        "path": f"{run_dir2}/work/site/test.md",
                        "line": 42
                    },
                    "status": "OPEN",
                }
            ],
            "generated_at": "2026-01-30T13:00:00Z",  # Different timestamp
        }

        # Normalize both
        norm1 = normalize_validation_report(report1, run_dir1)
        norm2 = normalize_validation_report(report2, run_dir2)

        # Write to files
        artifacts1 = run_dir1 / "artifacts"
        artifacts2 = run_dir2 / "artifacts"
        artifacts1.mkdir(parents=True, exist_ok=True)
        artifacts2.mkdir(parents=True, exist_ok=True)

        path1 = artifacts1 / "validation_report.json"
        path2 = artifacts2 / "validation_report.json"

        with path1.open("w") as f:
            json.dump(norm1, f, indent=2, sort_keys=True)
        with path2.open("w") as f:
            json.dump(norm2, f, indent=2, sort_keys=True)

        # Compute canonical hashes
        hash1 = compute_canonical_hash(path1)
        hash2 = compute_canonical_hash(path2)

        # MUST match - this proves bit-for-bit determinism
        assert hash1 == hash2, f"Hashes differ: {hash1} != {hash2}"


def test_canonical_hash_computation():
    """Test that compute_canonical_hash produces stable SHA256."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "test.json"

        # Write test JSON
        test_data = {
            "z_field": "value",
            "a_field": "value",
            "nested": {"b": 2, "a": 1},
        }

        with json_path.open("w") as f:
            json.dump(test_data, f, indent=2, sort_keys=True)

        # Compute hash
        hash1 = compute_canonical_hash(json_path)

        # Verify hash format (64 hex chars)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)

        # Recompute - should be identical
        hash2 = compute_canonical_hash(json_path)
        assert hash1 == hash2


def test_deep_nested_path_normalization():
    """Test path normalization works on deeply nested structures."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "nested_issue",
                "details": {
                    "context": {
                        "file_path": "/tmp/runs/run_001/work/site/nested/deep/file.md",
                        "references": [
                            "/tmp/runs/run_001/artifacts/ref1.json",
                            "/tmp/runs/run_001/artifacts/ref2.json",
                        ]
                    }
                },
                "location": {
                    "path": "/tmp/runs/run_001/work/site/test.md",
                    "line": 10
                },
            }
        ],
    }

    normalized = normalize_validation_report(report, run_dir)

    issue = normalized["issues"][0]
    # Check nested paths are normalized
    assert "<RUN_DIR>" in issue["details"]["context"]["file_path"]
    assert "/tmp/runs/run_001" not in issue["details"]["context"]["file_path"]

    # Check array of paths
    for ref in issue["details"]["context"]["references"]:
        assert "<RUN_DIR>" in ref
        assert "/tmp/runs/run_001" not in ref


def test_normalization_preserves_schema_compliance():
    """Normalized report must still comply with validation_report.schema.json."""
    run_dir = Path("/tmp/runs/run_001")
    report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [
            {"name": "gate_1_schema_validation", "ok": True},
        ],
        "issues": [],
    }

    normalized = normalize_validation_report(report, run_dir)

    # Check required fields present
    assert "schema_version" in normalized
    assert "ok" in normalized
    assert "profile" in normalized
    assert "gates" in normalized
    assert "issues" in normalized

    # Check types
    assert isinstance(normalized["ok"], bool)
    assert isinstance(normalized["gates"], list)
    assert isinstance(normalized["issues"], list)
    assert normalized["profile"] in ["local", "ci", "prod"]

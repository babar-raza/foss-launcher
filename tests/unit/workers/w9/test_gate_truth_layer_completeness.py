"""Phase 2: Tests for Gate — Truth Layer Completeness.

Covers:
- All required artifacts present → pass
- Missing artifacts → error in ci, blocker in prod, warn in local
- Corrupt JSON → error/blocker in ci/prod, warn in local
- Non-object JSON → error/blocker in ci/prod, warn in local
- Partial presence (2 of 3) → fail on missing artifact
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_truth_layer_completeness import (
    execute_gate,
    _REQUIRED_ARTIFACTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_artifact(run_dir: Path, filename: str, data: dict) -> None:
    """Write a valid JSON artifact."""
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / filename).write_text(json.dumps(data), encoding="utf-8")


def _write_all_artifacts(run_dir: Path) -> None:
    """Write all required truth artifacts with minimal valid content."""
    _write_artifact(run_dir, "api_inventory.json", {
        "package_name": "test", "classes": [], "functions": [], "modules": [],
    })
    _write_artifact(run_dir, "repo_truth.json", {
        "schema_version": "1.0",
        "license": {"spdx_id": "", "name": "", "source": ""},
        "python_requires": {"min": "", "spec": "", "source": ""},
        "package_name": {"value": "test", "source": "manifest"},
    })
    _write_artifact(run_dir, "shared_facts.json", {
        "schema_version": "1.1", "package_name": "test",
    })
    _write_artifact(run_dir, "page_plan.json", {
        "pages": [],
    })


# ---------------------------------------------------------------------------
# All artifacts present
# ---------------------------------------------------------------------------

class TestAllPresent:
    """Gate passes when all required artifacts are present and valid."""

    def test_all_present_local(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True
        assert issues == []

    def test_all_present_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_all_present_prod(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        passed, issues = execute_gate(tmp_path, "prod")
        assert passed is True
        assert issues == []


# ---------------------------------------------------------------------------
# Missing artifacts
# ---------------------------------------------------------------------------

class TestMissingArtifacts:
    """Gate behaviour when truth artifacts are absent."""

    def test_all_missing_local_warns(self, tmp_path: Path) -> None:
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True  # warns don't fail
        assert len(issues) == 4
        assert all(i["severity"] == "warn" for i in issues)

    def test_all_missing_ci_fails(self, tmp_path: Path) -> None:
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 4
        assert all(i["severity"] == "error" for i in issues)

    def test_all_missing_prod_blocks(self, tmp_path: Path) -> None:
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        passed, issues = execute_gate(tmp_path, "prod")
        assert passed is False
        assert len(issues) == 4
        assert all(i["severity"] == "blocker" for i in issues)

    def test_single_missing_api_inventory_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "api_inventory.json").unlink()
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["error_code"] == "TRUTH_MISSING_API_INVENTORY"

    def test_single_missing_shared_facts_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "shared_facts.json").unlink()
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["error_code"] == "TRUTH_MISSING_SHARED_FACTS"

    def test_single_missing_page_plan_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "page_plan.json").unlink()
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["error_code"] == "TRUTH_MISSING_PAGE_PLAN"

    def test_no_artifacts_dir(self, tmp_path: Path) -> None:
        """Even if artifacts/ doesn't exist, gate reports missing."""
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 4


# ---------------------------------------------------------------------------
# Corrupt artifacts
# ---------------------------------------------------------------------------

class TestCorruptArtifacts:
    """Gate detects corrupted/invalid JSON artifacts."""

    def test_invalid_json_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "api_inventory.json").write_text(
            "NOT_JSON{", encoding="utf-8"
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert any("TRUTH_CORRUPT_API_INVENTORY" in i.get("error_code", "") for i in issues)

    def test_non_object_json_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "shared_facts.json").write_text(
            "[]", encoding="utf-8"
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert any("CORRUPT" in i.get("error_code", "") for i in issues)

    def test_empty_file_ci(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "page_plan.json").write_text("", encoding="utf-8")
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False

    def test_corrupt_local_warns(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "api_inventory.json").write_text(
            "BROKEN", encoding="utf-8"
        )
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True  # warn-level doesn't fail
        assert any(i["severity"] == "warn" for i in issues)


# ---------------------------------------------------------------------------
# Mixed state
# ---------------------------------------------------------------------------

class TestMixedState:
    """Partial artifact presence and mixed valid/corrupt."""

    def test_two_present_one_missing(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "shared_facts.json").unlink()
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1

    def test_all_present_one_corrupt(self, tmp_path: Path) -> None:
        _write_all_artifacts(tmp_path)
        (tmp_path / "artifacts" / "page_plan.json").write_text("{bad", encoding="utf-8")
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert len(issues) == 1

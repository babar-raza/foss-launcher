"""Tests for Gate — Truth Facts Completeness.

Covers:
- Graceful skip when repo_truth.json absent
- Graceful skip when repo_truth.json is corrupt
- All facts populated → pass
- Unrecognized license → profile-aware severity
- Missing package_name → profile-aware severity
- Missing python_requires → info only (does not fail)
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_truth_facts_completeness import (
    execute_gate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_repo_truth(run_dir: Path, data: dict) -> None:
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "repo_truth.json").write_text(json.dumps(data), encoding="utf-8")


def _full_repo_truth() -> dict:
    return {
        "schema_version": "1.0",
        "license": {"spdx_id": "MIT", "name": "MIT License", "source": "LICENSE file (LICENSE)"},
        "python_requires": {"min": "3.8", "spec": ">=3.8", "source": "setup.py"},
        "package_name": {"value": "aspose-3d", "source": "manifest"},
        "import_roots": {"values": ["src/"], "source": "code_analysis"},
    }


# ---------------------------------------------------------------------------
# Graceful skips
# ---------------------------------------------------------------------------

class TestGracefulSkips:
    """Gate passes gracefully when repo_truth.json is absent or corrupt."""

    def test_no_repo_truth(self, tmp_path: Path) -> None:
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_corrupt_repo_truth(self, tmp_path: Path) -> None:
        arts = tmp_path / "artifacts"
        arts.mkdir(parents=True, exist_ok=True)
        (arts / "repo_truth.json").write_text("BROKEN{", encoding="utf-8")
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_non_dict_json(self, tmp_path: Path) -> None:
        arts = tmp_path / "artifacts"
        arts.mkdir(parents=True, exist_ok=True)
        (arts / "repo_truth.json").write_text("[]", encoding="utf-8")
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True


# ---------------------------------------------------------------------------
# All facts populated → pass
# ---------------------------------------------------------------------------

class TestAllPopulated:
    """Gate passes when all canonical facts are present."""

    def test_full_facts_local(self, tmp_path: Path) -> None:
        _write_repo_truth(tmp_path, _full_repo_truth())
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True
        assert issues == []

    def test_full_facts_ci(self, tmp_path: Path) -> None:
        _write_repo_truth(tmp_path, _full_repo_truth())
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_full_facts_prod(self, tmp_path: Path) -> None:
        _write_repo_truth(tmp_path, _full_repo_truth())
        passed, issues = execute_gate(tmp_path, "prod")
        assert passed is True
        assert issues == []


# ---------------------------------------------------------------------------
# Unrecognized license
# ---------------------------------------------------------------------------

class TestUnrecognizedLicense:
    """LICENSE file found but spdx_id could not be determined."""

    def test_unrecognized_license_warn_local(self, tmp_path: Path) -> None:
        rt = _full_repo_truth()
        rt["license"] = {"spdx_id": "", "name": "", "source": "LICENSE file (LICENSE) — unrecognized"}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True  # warn doesn't fail
        assert len(issues) == 1
        assert issues[0]["severity"] == "warn"
        assert issues[0]["error_code"] == "TRUTH_FACTS_LICENSE_UNRECOGNIZED"

    def test_unrecognized_license_error_ci(self, tmp_path: Path) -> None:
        rt = _full_repo_truth()
        rt["license"] = {"spdx_id": "", "name": "", "source": "LICENSE file (LICENSE) — unrecognized"}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert issues[0]["severity"] == "error"

    def test_unrecognized_license_blocker_prod(self, tmp_path: Path) -> None:
        rt = _full_repo_truth()
        rt["license"] = {"spdx_id": "", "name": "", "source": "LICENSE file (LICENSE) — unrecognized"}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "prod")
        assert passed is False
        assert issues[0]["severity"] == "blocker"

    def test_no_license_file_no_issue(self, tmp_path: Path) -> None:
        """No LICENSE file at all → no issue (source is empty)."""
        rt = _full_repo_truth()
        rt["license"] = {"spdx_id": "", "name": "", "source": ""}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        # Only python_requires missing or package_name could trigger, not license
        assert not any(i["error_code"] == "TRUTH_FACTS_LICENSE_UNRECOGNIZED" for i in issues)


# ---------------------------------------------------------------------------
# Missing package_name
# ---------------------------------------------------------------------------

class TestMissingPackageName:
    """Missing package_name produces profile-aware issues."""

    def test_missing_package_name_ci(self, tmp_path: Path) -> None:
        rt = _full_repo_truth()
        rt["package_name"] = {"value": "", "source": ""}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is False
        assert any(i["error_code"] == "TRUTH_FACTS_PACKAGE_NAME_MISSING" for i in issues)

    def test_missing_package_name_local(self, tmp_path: Path) -> None:
        rt = _full_repo_truth()
        rt["package_name"] = {"value": "", "source": ""}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "local")
        assert passed is True  # warn


# ---------------------------------------------------------------------------
# Missing python_requires (info only)
# ---------------------------------------------------------------------------

class TestMissingPythonRequires:
    """Missing python_requires produces info severity (never fails gate)."""

    def test_missing_python_requires_info(self, tmp_path: Path) -> None:
        rt = _full_repo_truth()
        rt["python_requires"] = {"min": "", "spec": "", "source": ""}
        _write_repo_truth(tmp_path, rt)
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True  # info doesn't fail
        assert any(i["error_code"] == "TRUTH_FACTS_PYTHON_REQUIRES_MISSING" for i in issues)
        assert all(
            i["severity"] == "info"
            for i in issues
            if i["error_code"] == "TRUTH_FACTS_PYTHON_REQUIRES_MISSING"
        )

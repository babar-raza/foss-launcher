"""TC-2870 + Phase 2: Tests for gate_license_consistency.

Covers:
- No shared_facts.json → graceful skip (local), error (ci), blocker (prod)
- No license in shared_facts → pass (local), warn (ci/prod)
- Correct license mentioned → pass
- Contradicting license → error in CI, blocker in prod, warn in local
- "Free/open-source" claim on commercial license → error
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_license_consistency import (
    execute_gate,
    _is_license_match,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_shared_facts(run_dir: Path, facts: dict) -> None:
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "shared_facts.json").write_text(
        json.dumps(facts), encoding="utf-8",
    )


def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


def _shared_facts_with_license(spdx_id: str, name: str = "") -> dict:
    return {
        "schema_version": "1.1",
        "license": {
            "spdx_id": spdx_id,
            "name": name or spdx_id,
        },
        "package_name": "test-pkg",
        "runtime_versions": {"python": {"minimum": "3.8", "all_mentioned": ["3.8"]}},
    }


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:

    def test_no_shared_facts_graceful_skip_local(self, tmp_path):
        """Local profile: missing shared_facts → pass with info."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True
        assert len(issues) == 1
        assert issues[0]["error_code"] == "LICENSE_SHARED_FACTS_MISSING"
        assert issues[0]["severity"] == "info"

    def test_no_shared_facts_fails_ci(self, tmp_path):
        """Phase 2: CI profile → missing shared_facts is an error."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["error_code"] == "LICENSE_SHARED_FACTS_MISSING"
        assert issues[0]["severity"] == "error"

    def test_no_shared_facts_blocks_prod(self, tmp_path):
        """Phase 2: prod profile → missing shared_facts is a blocker."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "prod")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"

    def test_corrupt_shared_facts_fails_ci(self, tmp_path):
        """Phase 2: CI profile → corrupted shared_facts is an error."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True, exist_ok=True)
        (arts / "shared_facts.json").write_text("NOT_JSON", encoding="utf-8")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert issues[0]["error_code"] == "LICENSE_SHARED_FACTS_ERROR"

    def test_no_license_in_shared_facts_warns_ci(self, tmp_path):
        """Phase 2: CI/prod → missing license field produces warn."""
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {
            "schema_version": "1.0",
            "package_name": "test-pkg",
        })
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 1
        assert issues[0]["error_code"] == "LICENSE_NO_CANONICAL"
        assert issues[0]["severity"] == "warn"

    def test_no_license_in_shared_facts_passes_local(self, tmp_path):
        """Local profile: missing license field → pass, no issues."""
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {
            "schema_version": "1.0",
            "package_name": "test-pkg",
        })
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True
        assert len(issues) == 0

    def test_empty_license_warns_ci(self, tmp_path):
        """Phase 2: CI → empty license fields produce warn."""
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {
            "license": {"spdx_id": "", "name": ""},
        })
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 1
        assert issues[0]["error_code"] == "LICENSE_NO_CANONICAL"

    def test_empty_license_passes_local(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, {
            "license": {"spdx_id": "", "name": ""},
        })
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True
        assert len(issues) == 0

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True


# ---------------------------------------------------------------------------
# License consistency checks
# ---------------------------------------------------------------------------

class TestLicenseConsistency:

    def test_correct_license_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        _write_md(run_dir, "page.md", "This library is released under the MIT license.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        # No contradiction issues
        contradiction_issues = [i for i in issues if i["error_code"] == "LICENSE_CONTRADICTION"]
        assert len(contradiction_issues) == 0

    def test_contradicting_license_fails_ci(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        _write_md(run_dir, "page.md", "This library uses the Apache license.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        contradiction = [i for i in issues if i["error_code"] == "LICENSE_CONTRADICTION"]
        assert len(contradiction) >= 1
        assert contradiction[0]["severity"] == "error"

    def test_contradicting_license_blocker_in_prod(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        _write_md(run_dir, "page.md", "Licensed under GPL.")
        passed, issues = execute_gate(run_dir, "prod")
        assert passed is False
        contradiction = [i for i in issues if i["error_code"] == "LICENSE_CONTRADICTION"]
        assert contradiction[0]["severity"] == "blocker"

    def test_contradicting_license_warns_in_local(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        _write_md(run_dir, "page.md", "Licensed under Apache 2.0.")
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True  # warn doesn't fail gate
        contradiction = [i for i in issues if i["error_code"] == "LICENSE_CONTRADICTION"]
        assert len(contradiction) >= 1
        assert contradiction[0]["severity"] == "warn"

    def test_no_license_mention_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        _write_md(run_dir, "page.md", "This is a great library for 3D processing.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True


# ---------------------------------------------------------------------------
# Commercial license + free claims
# ---------------------------------------------------------------------------

class TestCommercialFreeClaim:

    def test_free_claim_with_commercial_license(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("Freemium"))
        _write_md(run_dir, "page.md", "This is a free open-source library.")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        free_issues = [i for i in issues if i["error_code"] == "LICENSE_FREE_CLAIM_COMMERCIAL"]
        assert len(free_issues) >= 1

    def test_free_claim_with_open_source_license_ok(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_shared_facts(run_dir, _shared_facts_with_license("MIT"))
        _write_md(run_dir, "page.md", "This is a free open-source library.")
        passed, issues = execute_gate(run_dir, "ci")
        # MIT is open-source — "free open-source" claim is fine
        free_issues = [i for i in issues if i["error_code"] == "LICENSE_FREE_CLAIM_COMMERCIAL"]
        assert len(free_issues) == 0


# ---------------------------------------------------------------------------
# _is_license_match
# ---------------------------------------------------------------------------

class TestIsLicenseMatch:

    def test_exact_match(self):
        assert _is_license_match("MIT", "MIT", "MIT License")

    def test_case_insensitive(self):
        assert _is_license_match("mit", "MIT", "MIT License")

    def test_apache_variant(self):
        assert _is_license_match("Apache 2.0", "Apache-2.0", "Apache License 2.0")

    def test_gpl_variant(self):
        assert _is_license_match("GPLv3", "GPL-3.0", "")

    def test_mismatch(self):
        assert not _is_license_match("BSD", "MIT", "MIT License")

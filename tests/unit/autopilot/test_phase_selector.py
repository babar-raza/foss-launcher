"""Tests for PhaseSelector baseline (TC-3020).

Tests use tmp_path with minimal inline JSON stubs. Each test creates only
the artifacts needed to pass prior checkpoints, then omits/corrupts the target.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.autopilot.phase_selector import PhaseDecision, select_phase


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _setup_w1(run_dir: Path, repo_sha: str = "abc123") -> None:
    """Create minimal W1 artifacts (repo dir with .git + repo_inventory)."""
    (run_dir / "work" / "repo").mkdir(parents=True, exist_ok=True)
    # TC-3642: .git dir proves actual clone (not empty skeleton)
    (run_dir / "work" / "repo" / ".git").mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "artifacts" / "repo_inventory.json",
        {"repo_sha": repo_sha, "schema_version": "1.0"},
    )


def _setup_w3(run_dir: Path) -> None:
    """Create minimal W3 artifacts (product_facts + snippet_catalog)."""
    _write_json(run_dir / "artifacts" / "product_facts.json", {"schema_version": "1.0"})
    _write_json(run_dir / "artifacts" / "snippet_catalog.json", {"schema_version": "1.0"})


def _setup_w4(run_dir: Path) -> None:
    """Create minimal W4 artifacts (page_plan + shared_facts)."""
    _write_json(run_dir / "artifacts" / "page_plan.json", {"schema_version": "1.0"})
    _write_json(run_dir / "artifacts" / "shared_facts.json", {"schema_version": "1.0"})


def _setup_w5(run_dir: Path) -> None:
    """Create minimal W5 artifacts (draft_manifest + a draft .md file)."""
    _write_json(run_dir / "artifacts" / "draft_manifest.json", {"pages": []})
    drafts = run_dir / "drafts" / "products"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "landing.md").write_text("# Landing", encoding="utf-8")


def _setup_w8(run_dir: Path) -> None:
    """Create minimal W8 artifacts (patch_bundle)."""
    _write_json(run_dir / "artifacts" / "patch_bundle.json", {"schema_version": "1.0"})


def _setup_w9(run_dir: Path) -> None:
    """Create minimal W9 artifacts (validation_report)."""
    _write_json(
        run_dir / "artifacts" / "validation_report.json",
        {"schema_version": "1.0", "gates": [], "issues": []},
    )


def _setup_all(run_dir: Path, repo_sha: str = "abc123") -> None:
    """Create all artifacts through W9."""
    _setup_w1(run_dir, repo_sha)
    _setup_w3(run_dir)
    _setup_w4(run_dir)
    _setup_w5(run_dir)
    _setup_w8(run_dir)
    _setup_w9(run_dir)


class TestCheckpoint1_W1:
    """Checkpoint 1: repo dir + repo_inventory + SHA match."""

    def test_empty_run_dir_returns_w1(self, tmp_path: Path) -> None:
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W1"
        assert "REPO_DIR_MISSING" in decision.reasons

    def test_missing_repo_inventory_returns_w1(self, tmp_path: Path) -> None:
        (tmp_path / "work" / "repo" / ".git").mkdir(parents=True)
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W1"
        assert any("ARTIFACT_MISSING" in r for r in decision.reasons)

    def test_repo_sha_mismatch_returns_w1(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path, repo_sha="old_sha")
        decision = select_phase(tmp_path, "new_sha")
        assert decision.start_worker == "W1"
        assert "REPO_SHA_MISMATCH" in decision.reasons

    def test_corrupt_repo_inventory_returns_w1(self, tmp_path: Path) -> None:
        (tmp_path / "work" / "repo" / ".git").mkdir(parents=True)
        inv_path = tmp_path / "artifacts" / "repo_inventory.json"
        inv_path.parent.mkdir(parents=True, exist_ok=True)
        inv_path.write_text("NOT VALID JSON{{{", encoding="utf-8")
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W1"
        assert any("ARTIFACT_INVALID_JSON" in r for r in decision.reasons)


class TestCheckpoint2_W3:
    """Checkpoint 2: product_facts + snippet_catalog."""

    def test_missing_product_facts_returns_w3(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W3"
        assert any("ARTIFACT_MISSING:product_facts" in r for r in decision.reasons)

    def test_missing_snippet_catalog_returns_w3(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        _write_json(tmp_path / "artifacts" / "product_facts.json", {"schema_version": "1.0"})
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W3"
        assert any("snippet_catalog" in r for r in decision.reasons)


class TestCheckpoint3_W4:
    """Checkpoint 3: page_plan + shared_facts."""

    def test_missing_page_plan_returns_w4(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        _setup_w3(tmp_path)
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W4"
        assert any("page_plan" in r for r in decision.reasons)


class TestCheckpoint4_W5:
    """Checkpoint 4: draft_manifest + markdown files."""

    def test_missing_draft_manifest_returns_w5(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        _setup_w3(tmp_path)
        _setup_w4(tmp_path)
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W5"
        assert any("draft_manifest" in r for r in decision.reasons)

    def test_empty_drafts_dir_returns_w5(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        _setup_w3(tmp_path)
        _setup_w4(tmp_path)
        _write_json(tmp_path / "artifacts" / "draft_manifest.json", {"pages": []})
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W5"
        assert "DRAFTS_EMPTY" in decision.reasons


class TestCheckpoint5_W8:
    """Checkpoint 5: patch_bundle."""

    def test_missing_patch_bundle_returns_w8(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        _setup_w3(tmp_path)
        _setup_w4(tmp_path)
        _setup_w5(tmp_path)
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W8"
        assert any("patch_bundle" in r for r in decision.reasons)


class TestCheckpoint6_W9:
    """Checkpoint 6: validation_report."""

    def test_missing_validation_report_returns_w9(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        _setup_w3(tmp_path)
        _setup_w4(tmp_path)
        _setup_w5(tmp_path)
        _setup_w8(tmp_path)
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W9"
        assert any("validation_report" in r for r in decision.reasons)


class TestPostValidation:
    """Post-validation decisions: W10, W11, DONE."""

    def test_fixable_validation_returns_w10(self, tmp_path: Path) -> None:
        _setup_all(tmp_path)
        decision = select_phase(
            tmp_path, "abc123",
            validation_summary={"fixable_count": 3, "blocker_count": 0},
        )
        assert decision.start_worker == "W10"
        assert "VALIDATION_HAS_FIXABLE" in decision.reasons

    def test_all_passed_goal_pr_returns_w11(self, tmp_path: Path) -> None:
        _setup_all(tmp_path)
        decision = select_phase(tmp_path, "abc123", goal="pr")
        assert decision.start_worker == "W11"
        assert "ALL_PASSED" in decision.reasons

    def test_all_passed_goal_draft_returns_done(self, tmp_path: Path) -> None:
        _setup_all(tmp_path)
        decision = select_phase(tmp_path, "abc123", goal="draft")
        assert decision.start_worker == "DONE"
        assert "DONE" in decision.reasons


def _setup_w9_with_issues(run_dir: Path, issues: list) -> None:
    """Create W9 artifacts with the given issues list in validation_report.json."""
    _write_json(
        run_dir / "artifacts" / "validation_report.json",
        {"schema_version": "1.0", "gates": [], "issues": issues},
    )


class TestSelfDerivedValidation:
    """PhaseSelector auto-derives fixable summary from validation_report.json.

    TC-3080: When validation_summary is not provided, PhaseSelector reads
    validation_report.json issues and auto-computes blocker_count + error_count.
    """

    def test_blockers_in_report_returns_w10(self, tmp_path: Path) -> None:
        """2 blockers in report → W10 (auto-derived)."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [
            {"severity": "blocker", "issue_id": "b1", "gate": "g1", "message": "m1", "status": "OPEN", "error_code": "E1"},
            {"severity": "blocker", "issue_id": "b2", "gate": "g1", "message": "m2", "status": "OPEN", "error_code": "E2"},
        ])
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W10"
        assert "VALIDATION_HAS_FIXABLE" in decision.reasons

    def test_errors_in_report_returns_w10(self, tmp_path: Path) -> None:
        """1 error in report → W10 (auto-derived)."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [
            {"severity": "error", "issue_id": "e1", "gate": "g2", "message": "m1", "status": "OPEN", "error_code": "E3"},
        ])
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W10"
        assert "VALIDATION_HAS_FIXABLE" in decision.reasons

    def test_mixed_severities_returns_w10(self, tmp_path: Path) -> None:
        """1 blocker + 1 error + 1 warn → W10; fixable=2, blocker=1 in details."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [
            {"severity": "blocker", "issue_id": "b1", "gate": "g1", "message": "m1", "status": "OPEN", "error_code": "E1"},
            {"severity": "error", "issue_id": "e1", "gate": "g2", "message": "m2", "status": "OPEN", "error_code": "E2"},
            {"severity": "warn", "issue_id": "w1", "gate": "g3", "message": "m3", "status": "OPEN"},
        ])
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W10"
        assert "VALIDATION_HAS_FIXABLE" in decision.reasons
        assert "2 fixable" in decision.details.get("VALIDATION_HAS_FIXABLE", "")
        assert "1 blocker" in decision.details.get("VALIDATION_HAS_FIXABLE", "")

    def test_only_warnings_returns_done(self, tmp_path: Path) -> None:
        """2 warnings → DONE (warnings are not fixable by W10 routing logic)."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [
            {"severity": "warn", "issue_id": "w1", "gate": "g1", "message": "m1", "status": "OPEN"},
            {"severity": "warn", "issue_id": "w2", "gate": "g1", "message": "m2", "status": "OPEN"},
        ])
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "DONE"

    def test_only_info_returns_done(self, tmp_path: Path) -> None:
        """1 info issue → DONE."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [
            {"severity": "info", "issue_id": "i1", "gate": "g1", "message": "m1", "status": "OPEN"},
        ])
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "DONE"

    def test_empty_issues_returns_done(self, tmp_path: Path) -> None:
        """Empty issues list → DONE."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [])
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "DONE"

    def test_explicit_summary_takes_precedence(self, tmp_path: Path) -> None:
        """Caller-provided validation_summary overrides auto-derive (backward compat).

        Even if validation_report has no issues, an explicit fixable_count=1 routes to W10.
        """
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [])  # no issues in report
        decision = select_phase(
            tmp_path, "abc123",
            validation_summary={"fixable_count": 1, "blocker_count": 0},
        )
        assert decision.start_worker == "W10"
        assert "VALIDATION_HAS_FIXABLE" in decision.reasons

    def test_warnings_goal_pr_returns_w11(self, tmp_path: Path) -> None:
        """Warnings only + goal=pr → W11 (warnings don't trigger W10)."""
        _setup_all(tmp_path)
        _setup_w9_with_issues(tmp_path, [
            {"severity": "warn", "issue_id": "w1", "gate": "g1", "message": "m1", "status": "OPEN"},
        ])
        decision = select_phase(tmp_path, "abc123", goal="pr")
        assert decision.start_worker == "W11"
        assert "ALL_PASSED" in decision.reasons


class TestDeterminism:
    """PhaseSelector must be deterministic."""

    def test_same_inputs_same_decision(self, tmp_path: Path) -> None:
        _setup_w1(tmp_path)
        d1 = select_phase(tmp_path, "abc123")
        d2 = select_phase(tmp_path, "abc123")
        assert d1.start_worker == d2.start_worker
        assert d1.reasons == d2.reasons

    def test_reason_codes_populated(self, tmp_path: Path) -> None:
        decision = select_phase(tmp_path, "abc123")
        assert len(decision.reasons) > 0
        assert len(decision.details) > 0


# ═══════════════════════════════════════════════════════════════════════
# TC-3642: .git Hardening
# ═══════════════════════════════════════════════════════════════════════


class TestGitHardening:
    """Verify that an empty work/repo/ without .git returns W1.

    Spec: specs/48_autopilot_phase_selection.md §Baseline Algorithm.
    """

    def test_repo_dir_exists_but_no_git_returns_w1(self, tmp_path: Path) -> None:
        """Empty work/repo/ without .git → W1 (REPO_NOT_CLONED)."""
        (tmp_path / "work" / "repo").mkdir(parents=True, exist_ok=True)
        _write_json(
            tmp_path / "artifacts" / "repo_inventory.json",
            {"repo_sha": "abc123", "schema_version": "1.0"},
        )
        decision = select_phase(tmp_path, "abc123")
        assert decision.start_worker == "W1"
        assert "REPO_NOT_CLONED" in decision.reasons

    def test_repo_dir_with_git_passes_checkpoint(self, tmp_path: Path) -> None:
        """work/repo/ with .git present → proceeds past checkpoint 1."""
        _setup_w1(tmp_path)
        decision = select_phase(tmp_path, "abc123")
        # Should NOT be W1 for REPO_NOT_CLONED (may be W3 due to missing W3 artifacts)
        assert "REPO_NOT_CLONED" not in decision.reasons

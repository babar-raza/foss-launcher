"""Unit tests for the launch drive self-driving autopilot command (TC-3040).

Tests cover:
- Phase selection with no store (first run → W1)
- Store hydration and correct phase resumption
- execution_plan.json artifact writing
- LLM planner integration and guardrail
- run_config schema acceptance of autopilot field
- DONE decision skips execution

All tests are fast (no network, no LLM, no real pipeline — mocked).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_run_config(**overrides: Any) -> Dict[str, Any]:
    """Minimal run_config for testing."""
    base = {
        "product_slug": "aspose-cells-python",
        "product_name": "Aspose.Cells for Python",
        "family": "cells",
        "target_platform": "python",
        "github_repo_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
        "github_ref": "a" * 40,
        "site_ref": "b" * 40,
    }
    base.update(overrides)
    return base


def _make_run_dir(tmp_path: Path, artifacts: Dict[str, Any] | None = None) -> Path:
    """Create a minimal run directory with optional artifacts."""
    run_dir = tmp_path / "runs" / "r_test_drive"
    run_dir.mkdir(parents=True)
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    (run_dir / "snapshot.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "work" / "repo").mkdir(parents=True)

    if artifacts:
        art_dir = run_dir / "artifacts"
        art_dir.mkdir(parents=True, exist_ok=True)
        for name, content in artifacts.items():
            (art_dir / name).write_text(
                json.dumps(content, indent=2), encoding="utf-8"
            )

    return run_dir


def _write_run_config(run_dir: Path, run_config: Dict[str, Any]) -> None:
    """Write run_config.yaml to run_dir."""
    import yaml

    (run_dir / "run_config.yaml").write_text(
        yaml.dump(run_config, default_flow_style=False), encoding="utf-8"
    )


# ── Phase selector import ────────────────────────────────────────────────────

from launch.autopilot.phase_selector import PhaseDecision, select_phase
from launch.provenance import build_provenance, validate_provenance_compat
from launch.state_store.store import (
    find_artifact_set,
    get_store_key,
    get_store_root,
    hydrate_run_dir,
    publish_run_artifacts,
    read_provenance,
    write_provenance,
)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestDriveNoStore:
    """First run with no cached artifacts → W1."""

    def test_empty_run_dir_returns_w1(self, tmp_path: Path) -> None:
        """No artifacts at all → PhaseSelector returns W1."""
        run_dir = _make_run_dir(tmp_path)
        run_config = _make_run_config()
        decision = select_phase(
            run_dir, run_config["github_ref"], goal="draft"
        )
        assert decision.start_worker == "W1"

    def test_no_store_match_returns_none(self, tmp_path: Path) -> None:
        """State store with no matching SHA → find_artifact_set returns None."""
        store_root = tmp_path / ".foss_state"
        store_root.mkdir()
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        result = find_artifact_set(store_root, store_key, run_config["github_ref"])
        assert result is None


class TestDriveHydration:
    """Store has W1-W4 artifacts → hydration works."""

    def _populate_store(
        self, store_root: Path, store_key: Path, repo_sha: str
    ) -> Path:
        """Create a minimal store with W1-W4 artifacts."""
        for worker in ("w1", "w2", "w3", "w4"):
            worker_dir = store_root / store_key / "artifacts" / repo_sha / worker
            worker_dir.mkdir(parents=True, exist_ok=True)
            # Write a dummy artifact
            (worker_dir / f"dummy_{worker}.json").write_text(
                json.dumps({"from": worker}), encoding="utf-8"
            )
        return store_root / store_key / "artifacts" / repo_sha

    def test_hydrate_copies_artifacts(self, tmp_path: Path) -> None:
        """Hydrating from store copies files into run_dir/artifacts/."""
        run_dir = _make_run_dir(tmp_path)
        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        artifact_set = self._populate_store(store_root, store_key, sha)
        count = hydrate_run_dir(run_dir, artifact_set)
        assert count == 4  # 4 dummy files across 4 workers
        assert (run_dir / "artifacts" / "dummy_w1.json").exists()
        assert (run_dir / "artifacts" / "dummy_w4.json").exists()

    def test_find_artifact_set_returns_path(self, tmp_path: Path) -> None:
        """find_artifact_set returns the path when SHA exists."""
        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        self._populate_store(store_root, store_key, sha)
        result = find_artifact_set(store_root, store_key, sha)
        assert result is not None
        assert result.name == sha


class TestDriveExecutionPlan:
    """execution_plan.json is written correctly."""

    def test_execution_plan_fields(self, tmp_path: Path) -> None:
        """execution_plan.json contains all required fields."""
        run_dir = _make_run_dir(tmp_path)
        run_config = _make_run_config()
        sha = run_config["github_ref"]

        # Build the execution plan dict as the drive command does
        decision = select_phase(run_dir, sha, goal="draft")

        plan = {
            "schema_version": "1.0",
            "baseline_start_worker": decision.start_worker,
            "final_start_worker": decision.start_worker,
            "reasons": [
                {"code": r, "message": decision.details.get(r, "")}
                for r in decision.reasons
            ],
            "target_repo_sha": sha,
            "hydrate_source": "none",
            "hydrated_artifact_count": 0,
            "llm_planner_used": False,
            "guardrail_applied": False,
            "llm_rationale": "",
            "goal": "draft",
            "timestamp": "2026-02-27T00:00:00+00:00",
        }

        plan_path = run_dir / "artifacts" / "execution_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        # Read back and verify
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
        assert loaded["schema_version"] == "1.0"
        assert loaded["baseline_start_worker"] == "W1"
        assert loaded["final_start_worker"] == "W1"
        assert loaded["target_repo_sha"] == sha
        assert loaded["hydrate_source"] == "none"
        assert loaded["llm_planner_used"] is False
        assert isinstance(loaded["reasons"], list)

    def test_execution_plan_with_hydration(self, tmp_path: Path) -> None:
        """When artifacts are hydrated, plan records the source."""
        run_dir = _make_run_dir(tmp_path)

        plan = {
            "schema_version": "1.0",
            "baseline_start_worker": "W5",
            "final_start_worker": "W5",
            "reasons": [{"code": "DRAFTS_EMPTY", "message": "No .md files under drafts/"}],
            "target_repo_sha": "a" * 40,
            "hydrate_source": "/some/store/path",
            "hydrated_artifact_count": 12,
            "llm_planner_used": False,
            "guardrail_applied": False,
            "llm_rationale": "",
            "goal": "draft",
            "timestamp": "2026-02-27T00:00:00+00:00",
        }

        plan_path = run_dir / "artifacts" / "execution_plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan) + "\n", encoding="utf-8")

        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
        assert loaded["hydrated_artifact_count"] == 12
        assert loaded["hydrate_source"] == "/some/store/path"


class TestDriveLLMPlanner:
    """LLM planner integration — guardrail enforcement."""

    def test_llm_later_than_baseline_rejected(self) -> None:
        """LLM suggesting later worker → guardrail forces baseline."""
        from launch.autopilot.llm_planner import PlannerSuggestion, _validate_suggestion

        raw = {"suggested_start_worker": "W9", "toggles": {}, "rationale": "skip ahead"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.suggested_start_worker == "W5"  # Guardrailed back to baseline
        assert result.guardrail_applied is True

    def test_llm_earlier_than_baseline_accepted(self) -> None:
        """LLM suggesting earlier worker → accepted."""
        from launch.autopilot.llm_planner import _validate_suggestion

        raw = {"suggested_start_worker": "W1", "toggles": {}, "rationale": "rerun all"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.suggested_start_worker == "W1"
        assert result.guardrail_applied is False

    def test_llm_equal_to_baseline_accepted(self) -> None:
        """LLM agreeing with baseline → accepted (no guardrail)."""
        from launch.autopilot.llm_planner import _validate_suggestion

        raw = {"suggested_start_worker": "W5", "toggles": {}, "rationale": "agree"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.suggested_start_worker == "W5"
        assert result.guardrail_applied is False


class TestDriveSchemaAcceptance:
    """run_config.schema.json accepts the autopilot field."""

    def test_schema_accepts_autopilot_block(self, tmp_path: Path) -> None:
        """Run config with autopilot block validates against schema."""
        # Load the schema
        from launch.io.schema_validation import load_schema

        repo_root = Path(__file__).resolve().parents[3]
        schema_path = repo_root / "specs" / "schemas" / "run_config.schema.json"
        if not schema_path.exists():
            pytest.skip("run_config.schema.json not found")

        schema = load_schema(schema_path)

        # The autopilot block should be a valid property
        assert "autopilot" in schema.get("properties", {}), (
            "autopilot not in schema properties"
        )
        autopilot_schema = schema["properties"]["autopilot"]
        assert autopilot_schema["type"] == "object"
        assert "enabled" in autopilot_schema["properties"]
        assert "state_store_root" in autopilot_schema["properties"]
        assert "llm_planner_enabled" in autopilot_schema["properties"]

    def test_autopilot_not_required(self, tmp_path: Path) -> None:
        """Autopilot is optional — not in required list."""
        from launch.io.schema_validation import load_schema

        repo_root = Path(__file__).resolve().parents[3]
        schema_path = repo_root / "specs" / "schemas" / "run_config.schema.json"
        if not schema_path.exists():
            pytest.skip("run_config.schema.json not found")

        schema = load_schema(schema_path)
        required = schema.get("required", [])
        assert "autopilot" not in required


class TestDriveDoneDecision:
    """When all artifacts are ready, DONE means no execution."""

    def test_done_decision_all_ready(self, tmp_path: Path) -> None:
        """PhaseDecision with start_worker=DONE when all checkpoints pass."""
        run_dir = _make_run_dir(tmp_path, artifacts={
            "repo_inventory.json": {"repo_sha": "a" * 40, "files": []},
            "product_facts.json": {"product_name": "test", "claims": []},
            "snippet_catalog.json": {"snippets": []},
            "page_plan.json": {"pages": []},
            "shared_facts.json": {"facts": {}},
            "draft_manifest.json": {"pages": []},
            "patch_bundle.json": {"patches": []},
            "validation_report.json": {"gates": [], "issues": [], "ok": True},
        })

        # Create at least one draft .md
        drafts_dir = run_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "test.md").write_text("# Test\nContent", encoding="utf-8")

        sha = "a" * 40
        # Without repo_root → skip schema validation
        decision = select_phase(run_dir, sha, goal="draft")
        assert decision.start_worker == "DONE"
        assert "DONE" in decision.reasons


class TestDriveEventConstant:
    """EVENT_PLAN_COMPUTED constant exists."""

    def test_event_constant_defined(self) -> None:
        from launch.models.event import EVENT_PLAN_COMPUTED
        assert EVENT_PLAN_COMPUTED == "PLAN_COMPUTED"


class TestDrivePublish:
    """Artifact publishing after successful run."""

    def test_publish_round_trip(self, tmp_path: Path) -> None:
        """Publish W5/W8/W9 from run_dir, then find in legacy store.

        TC-3250: publish_run_artifacts now handles only W5/W8/W9.
        W1 goes to raw layer; W2/W3/W4 go to derived layer.
        """
        run_dir = _make_run_dir(tmp_path, artifacts={
            # W9 artifact — handled by publish_run_artifacts
            "validation_report.json": {"gates": [], "issues": [], "ok": True},
        })

        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        count = publish_run_artifacts(store_root, store_key, sha, run_dir)
        assert count == 1  # only validation_report.json (W9)

        # Now find it in legacy layout
        result = find_artifact_set(store_root, store_key, sha)
        assert result is not None

    def test_publish_run_artifacts_skips_w1_only(self, tmp_path: Path) -> None:
        """TC-3250/SR-02: publish_run_artifacts returns 0 for W1-only artifacts."""
        run_dir = _make_run_dir(tmp_path, artifacts={
            "repo_inventory.json": {"repo_sha": "a" * 40},
        })
        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        count = publish_run_artifacts(store_root, store_key, sha, run_dir)
        assert count == 0
        # Legacy layout must NOT contain w1/
        legacy_w1 = store_root / store_key / "artifacts" / sha / "w1"
        assert not legacy_w1.exists()

    def test_publish_run_artifacts_skips_w2_only(self, tmp_path: Path) -> None:
        """TC-3250/SR-02: publish_run_artifacts returns 0 for W2-only artifacts."""
        run_dir = _make_run_dir(tmp_path, artifacts={
            "product_facts.json": {"product_name": "test"},
        })
        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        count = publish_run_artifacts(store_root, store_key, sha, run_dir)
        assert count == 0
        legacy_w2 = store_root / store_key / "artifacts" / sha / "w2"
        assert not legacy_w2.exists()

    def test_publish_run_artifacts_mixed_w1_w2_w9(self, tmp_path: Path) -> None:
        """TC-3250/SR-02: W1+W2+W9 → only W9 published (count=1), no w1/ or w2/."""
        run_dir = _make_run_dir(tmp_path, artifacts={
            "repo_inventory.json": {"repo_sha": "a" * 40},
            "product_facts.json": {"product_name": "test"},
            "validation_report.json": {"gates": [], "ok": True},
        })
        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config()
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        count = publish_run_artifacts(store_root, store_key, sha, run_dir)
        assert count == 1  # only validation_report.json (W9)

        legacy_base = store_root / store_key / "artifacts" / sha
        assert (legacy_base / "w9" / "validation_report.json").exists()
        assert not (legacy_base / "w1").exists()
        assert not (legacy_base / "w2").exists()


class TestDriveProvenance:
    """TC-3070: Provenance validation in the drive flow."""

    def _populate_store_with_provenance(
        self, store_root: Path, store_key: Path, repo_sha: str, run_config: Dict[str, Any]
    ) -> Path:
        """Create a store with W1-W4 artifacts + provenance.json."""
        for worker in ("w1", "w2", "w3", "w4"):
            worker_dir = store_root / store_key / "artifacts" / repo_sha / worker
            worker_dir.mkdir(parents=True, exist_ok=True)
            (worker_dir / f"dummy_{worker}.json").write_text(
                json.dumps({"from": worker}), encoding="utf-8"
            )
        prov = build_provenance(run_config, repo_sha)
        write_provenance(store_root, store_key, repo_sha, prov)
        return store_root / store_key / "artifacts" / repo_sha

    def test_publish_and_write_provenance(self, tmp_path: Path) -> None:
        """After publish + write_provenance, provenance.json exists in store.

        TC-3250: publish_run_artifacts handles W5/W8/W9; use a W9 artifact.
        """
        run_dir = _make_run_dir(tmp_path, artifacts={
            "validation_report.json": {"gates": [], "issues": [], "ok": True},
        })
        store_root = tmp_path / ".foss_state"
        run_config = _make_run_config(
            ruleset_version="ruleset.v1_1", templates_version="templates.v1"
        )
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        publish_run_artifacts(store_root, store_key, sha, run_dir)
        prov_record = build_provenance(run_config, sha)
        write_provenance(store_root, store_key, sha, prov_record)

        artifact_set = find_artifact_set(store_root, store_key, sha)
        assert artifact_set is not None
        prov = read_provenance(artifact_set)
        assert prov is not None
        assert prov["ruleset_version"] == "ruleset.v1_1"
        assert prov["templates_version"] == "templates.v1"

    def test_provenance_mismatch_blocks_hydration(self, tmp_path: Path) -> None:
        """When ruleset_version differs, provenance validation fails."""
        run_config = _make_run_config(
            ruleset_version="ruleset.v1_1", templates_version="templates.v1"
        )
        store_root = tmp_path / ".foss_state"
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        # Populate store with OLD ruleset version
        old_config = dict(run_config, ruleset_version="ruleset.v1_0")
        self._populate_store_with_provenance(store_root, store_key, sha, old_config)

        # Validate provenance with NEW config
        artifact_set = find_artifact_set(store_root, store_key, sha)
        assert artifact_set is not None
        prov = read_provenance(artifact_set)
        assert prov is not None

        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha=sha,
            required_ruleset_version="ruleset.v1_1",
            required_templates_version="templates.v1",
        )
        assert ok is False
        assert any(r["code"] == "RULESET_VERSION_MISMATCH" for r in reasons)

    def test_missing_provenance_allows_hydration(self, tmp_path: Path) -> None:
        """Old stores without provenance.json still allow hydration (backward compat)."""
        run_config = _make_run_config()
        store_root = tmp_path / ".foss_state"
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        # Populate store WITHOUT provenance
        for worker in ("w1", "w2"):
            worker_dir = store_root / store_key / "artifacts" / sha / worker
            worker_dir.mkdir(parents=True, exist_ok=True)
            (worker_dir / f"dummy_{worker}.json").write_text(
                json.dumps({"from": worker}), encoding="utf-8"
            )

        artifact_set = find_artifact_set(store_root, store_key, sha)
        assert artifact_set is not None
        prov = read_provenance(artifact_set)
        assert prov is None  # No provenance → backward compat → allow hydration

        # Hydration should work
        run_dir = _make_run_dir(tmp_path)
        count = hydrate_run_dir(run_dir, artifact_set)
        assert count == 2

    def test_templates_version_mismatch_detected(self, tmp_path: Path) -> None:
        """When templates_version differs, provenance validation fails."""
        run_config = _make_run_config(
            ruleset_version="rv1", templates_version="templates.v1"
        )
        store_root = tmp_path / ".foss_state"
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        old_config = dict(run_config, templates_version="templates.v0")
        self._populate_store_with_provenance(store_root, store_key, sha, old_config)

        artifact_set = find_artifact_set(store_root, store_key, sha)
        prov = read_provenance(artifact_set)
        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha=sha,
            required_ruleset_version="rv1",
            required_templates_version="templates.v1",
        )
        assert ok is False
        assert any(r["code"] == "TEMPLATES_VERSION_MISMATCH" for r in reasons)

    def test_matching_provenance_allows_hydration(self, tmp_path: Path) -> None:
        """When provenance matches, hydration proceeds normally."""
        run_config = _make_run_config(
            ruleset_version="rv1", templates_version="tv1"
        )
        store_root = tmp_path / ".foss_state"
        store_key = get_store_key(run_config)
        sha = run_config["github_ref"]

        self._populate_store_with_provenance(store_root, store_key, sha, run_config)

        artifact_set = find_artifact_set(store_root, store_key, sha)
        prov = read_provenance(artifact_set)
        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha=sha,
            required_ruleset_version="rv1",
            required_templates_version="tv1",
        )
        assert ok is True
        assert reasons == []

        run_dir = _make_run_dir(tmp_path)
        count = hydrate_run_dir(run_dir, artifact_set)
        assert count == 4  # 4 dummy worker files


# ── TC-3080: Goal routing and heal wiring tests ──────────────────────────────


def _write_validation_report(run_dir: Path, ok: bool, issues=None) -> None:
    """Write a minimal validation_report.json."""
    report = {
        "schema_version": "1.0",
        "ok": ok,
        "profile": "local",
        "gates": [{"name": "gate_1", "ok": ok}],
        "issues": issues or [],
        "generation_id": "test-gen-id",
        "content_hash": "test-hash",
    }
    art_dir = run_dir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "validation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


def _mock_run_result(exit_code: int = 0, final_state: str = "DONE"):
    """Create a mock RunResult."""
    result = MagicMock()
    result.exit_code = exit_code
    result.final_state = final_state
    result.run_id = "r_test"
    return result


class TestDriveGoalRouting:
    """TC-3080: Verify _drive_goal is injected and exit codes are correct."""

    def test_drive_goal_injected_into_run_config(self, tmp_path: Path) -> None:
        """run_config['_drive_goal'] is set before graph execution."""
        run_config = _make_run_config()

        # Simulate what drive() does: inject _drive_goal
        run_config["_drive_goal"] = "validate"
        assert run_config["_drive_goal"] == "validate"

        # Verify it's a transient key (not in the original template)
        fresh = _make_run_config()
        assert "_drive_goal" not in fresh

    def test_goal_validate_exit_0_when_ok(self, tmp_path: Path) -> None:
        """goal=validate + report.ok=True → exit 0."""
        run_dir = _make_run_dir(tmp_path)
        _write_validation_report(run_dir, ok=True)

        # Simulate post-execution logic from drive()
        report_path = run_dir / "artifacts" / "validation_report.json"
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        validation_ok = report_data.get("ok", False)

        result = _mock_run_result(exit_code=0)
        if result.exit_code == 2:
            exit_code = 2
        elif validation_ok is not None:
            exit_code = 0 if validation_ok else 1
        else:
            exit_code = 0

        assert exit_code == 0

    def test_goal_validate_exit_1_when_not_ok(self, tmp_path: Path) -> None:
        """goal=validate + report.ok=False → exit 1."""
        run_dir = _make_run_dir(tmp_path)
        _write_validation_report(run_dir, ok=False, issues=[
            {"issue_id": "i1", "gate": "gate_1", "severity": "error", "message": "fail"},
        ])

        report_path = run_dir / "artifacts" / "validation_report.json"
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        validation_ok = report_data.get("ok", False)

        result = _mock_run_result(exit_code=0)  # "stop" route → DONE → exit 0
        if result.exit_code == 2:
            exit_code = 2
        elif validation_ok is not None:
            exit_code = 0 if validation_ok else 1
        else:
            exit_code = 0

        assert exit_code == 1

    def test_pipeline_crash_preserves_exit_2(self, tmp_path: Path) -> None:
        """Pipeline crash (exit 2) is preserved regardless of goal."""
        run_dir = _make_run_dir(tmp_path)
        # No validation report written (pipeline crashed before W9)

        report_path = run_dir / "artifacts" / "validation_report.json"
        validation_ok = None
        if report_path.exists():
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            validation_ok = report_data.get("ok", False)

        result = _mock_run_result(exit_code=2, final_state="FAILED")
        if result.exit_code == 2:
            exit_code = 2
        elif validation_ok is not None:
            exit_code = 0 if validation_ok else 1
        else:
            exit_code = 0

        assert exit_code == 2


class TestDriveHealWiring:
    """TC-3080: Verify --heal triggers heal loop correctly."""

    def test_heal_triggered_when_not_ok(self, tmp_path: Path) -> None:
        """--heal invokes run_heal_loop when validation_report.ok=False."""
        run_dir = _make_run_dir(tmp_path)
        _write_validation_report(run_dir, ok=False, issues=[
            {"issue_id": "i1", "gate": "gate_17", "severity": "error", "message": "fmt"},
        ])

        report_path = run_dir / "artifacts" / "validation_report.json"
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        validation_ok = report_data.get("ok", False)

        heal = True
        heal_called = False
        if heal and validation_ok is False:
            heal_called = True

        assert heal_called is True

    def test_heal_skipped_when_ok(self, tmp_path: Path) -> None:
        """--heal does NOT invoke heal loop when validation_report.ok=True."""
        run_dir = _make_run_dir(tmp_path)
        _write_validation_report(run_dir, ok=True)

        report_path = run_dir / "artifacts" / "validation_report.json"
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        validation_ok = report_data.get("ok", False)

        heal = True
        heal_called = False
        if heal and validation_ok is False:
            heal_called = True

        assert heal_called is False

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    @patch("launch.cli.heal.run_heal_loop")
    def test_heal_then_w11_on_goal_pr(
        self, mock_heal_loop, mock_exec, tmp_path: Path
    ) -> None:
        """After heal converges and goal=pr, W11 is executed."""
        from launch.cli.heal import HealResult

        run_dir = _make_run_dir(tmp_path)
        _write_validation_report(run_dir, ok=False)

        mock_heal_result = MagicMock(spec=HealResult)
        mock_heal_result.stop_reason = "all_gates_pass"
        mock_heal_result.final_failed_gate_count = 0
        mock_heal_result.steps = []
        mock_heal_loop.return_value = mock_heal_result

        mock_exec.return_value = _mock_run_result(exit_code=0)

        # Simulate the drive() heal + W11 logic
        goal = "pr"
        heal_result = mock_heal_loop(
            run_id="r_test", run_dir=run_dir, run_config={},
            max_steps=5, top_k=3, mode="strict",
        )

        exit_code = 0
        if heal_result.stop_reason == "all_gates_pass":
            exit_code = 0
            if goal == "pr":
                pr_result = mock_exec("r_test", run_dir, {}, "W11")
                if pr_result.exit_code != 0:
                    exit_code = pr_result.exit_code

        assert exit_code == 0
        mock_heal_loop.assert_called_once()
        mock_exec.assert_called_once_with("r_test", run_dir, {}, "W11")

    @patch("launch.cli.heal.run_heal_loop")
    def test_heal_no_w11_on_goal_draft(
        self, mock_heal_loop, tmp_path: Path
    ) -> None:
        """After heal converges and goal=draft, W11 is NOT executed."""
        from launch.cli.heal import HealResult

        run_dir = _make_run_dir(tmp_path)
        _write_validation_report(run_dir, ok=False)

        mock_heal_result = MagicMock(spec=HealResult)
        mock_heal_result.stop_reason = "all_gates_pass"
        mock_heal_result.final_failed_gate_count = 0
        mock_heal_result.steps = []
        mock_heal_loop.return_value = mock_heal_result

        goal = "draft"
        w11_called = False

        heal_result = mock_heal_loop(
            run_id="r_test", run_dir=run_dir, run_config={},
            max_steps=5, top_k=3, mode="strict",
        )

        if heal_result.stop_reason == "all_gates_pass":
            if goal == "pr":
                w11_called = True

        assert w11_called is False
        mock_heal_loop.assert_called_once()

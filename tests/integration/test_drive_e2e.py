"""Integration test for the launch drive autopilot E2E flow (TC-3040).

Tests the full hydrate -> select -> plan -> execute cycle with mocked
pipeline execution (no real LLM, no real pipeline).

Verifies:
- Store hydration populates run_dir/artifacts/
- PhaseSelector computes correct start worker after hydration
- execution_plan.json is written with all required fields
- Store publish after 'execution' round-trips artifacts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from launch.autopilot.phase_selector import select_phase
from launch.provenance import compute_interpretation_signature
from launch.state_store.store import (
    find_artifact_set,
    find_derived_artifact_set,
    find_raw_artifact_set,
    get_store_key,
    hydrate_from_derived,
    hydrate_from_raw,
    hydrate_run_dir,
    publish_derived_artifacts,
    publish_raw_artifacts,
    publish_run_artifacts,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_run_config() -> Dict[str, Any]:
    """Minimal run_config for integration testing."""
    return {
        "product_slug": "aspose-cells-python",
        "product_name": "Aspose.Cells for Python",
        "family": "cells",
        "target_platform": "python",
        "github_repo_url": "https://github.com/test/test",
        "github_ref": "c" * 40,
        "site_ref": "d" * 40,
    }


def _make_run_dir(base: Path, with_drafts: bool = False) -> Path:
    """Create a minimal run directory."""
    run_dir = base / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    (run_dir / "snapshot.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "work" / "repo").mkdir(parents=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

    if with_drafts:
        drafts_dir = run_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "landing.md").write_text("# Landing\nContent here", encoding="utf-8")

    return run_dir


def _populate_store(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    artifacts: Dict[str, Dict[str, Any]],
) -> Path:
    """Create a store with artifacts assigned to known workers."""
    worker_map = {
        "repo_inventory.json": "w1",
        "product_facts.json": "w2",
        "snippet_catalog.json": "w3",
        "page_plan.json": "w4",
        "shared_facts.json": "w4",
    }
    for name, content in artifacts.items():
        worker = worker_map.get(name, "w1")
        worker_dir = store_root / store_key / "artifacts" / repo_sha / worker
        worker_dir.mkdir(parents=True, exist_ok=True)
        (worker_dir / name).write_text(
            json.dumps(content, indent=2), encoding="utf-8"
        )
    return store_root / store_key / "artifacts" / repo_sha


# ── Tests ────────────────────────────────────────────────────────────────────


class TestDriveE2E:
    """Full hydrate → select → plan → (mock) execute → publish cycle."""

    def test_first_run_no_store_starts_w1(self, tmp_path: Path) -> None:
        """First run with empty store → PhaseSelector picks W1."""
        run_dir = _make_run_dir(tmp_path)
        run_config = _make_run_config()
        sha = run_config["github_ref"]

        # No store exists
        decision = select_phase(run_dir, sha, goal="draft")
        assert decision.start_worker == "W1"

    def test_hydrate_then_select_skips_to_w5(self, tmp_path: Path) -> None:
        """Store has W1-W4 artifacts → hydrate → select picks W5 (drafts missing)."""
        run_dir = _make_run_dir(tmp_path)
        run_config = _make_run_config()
        sha = run_config["github_ref"]
        store_root = tmp_path / ".foss_state"
        store_key = get_store_key(run_config)

        # Populate store with W1-W4 artifacts
        store_artifacts = {
            "repo_inventory.json": {"repo_sha": sha, "files": []},
            "product_facts.json": {"product_name": "test", "claims": []},
            "snippet_catalog.json": {"snippets": []},
            "page_plan.json": {"pages": []},
            "shared_facts.json": {"facts": {}},
        }
        artifact_set = _populate_store(store_root, store_key, sha, store_artifacts)

        # Hydrate
        count = hydrate_run_dir(run_dir, artifact_set)
        assert count == 5  # 5 artifact files

        # Verify files landed in run_dir/artifacts/
        for name in store_artifacts:
            assert (run_dir / "artifacts" / name).exists(), f"Missing: {name}"

        # Select phase — W1-W4 artifacts present, but no drafts
        decision = select_phase(run_dir, sha, goal="draft")
        assert decision.start_worker == "W5"
        assert "DRAFTS_EMPTY" in decision.reasons or any(
            "draft_manifest" in r for r in decision.reasons
        )

    def test_execution_plan_written_before_pipeline(self, tmp_path: Path) -> None:
        """execution_plan.json is written with all required fields."""
        from datetime import datetime, timezone

        run_dir = _make_run_dir(tmp_path)
        run_config = _make_run_config()
        sha = run_config["github_ref"]

        decision = select_phase(run_dir, sha, goal="draft")

        # Simulate what drive command does: write execution_plan.json
        execution_plan = {
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        plan_path = run_dir / "artifacts" / "execution_plan.json"
        plan_path.write_text(
            json.dumps(execution_plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Verify
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
        assert loaded["schema_version"] == "1.0"
        assert loaded["baseline_start_worker"] == "W1"
        assert loaded["final_start_worker"] == "W1"
        assert loaded["goal"] == "draft"
        assert isinstance(loaded["reasons"], list)
        assert "timestamp" in loaded

    def test_publish_after_run_round_trips(self, tmp_path: Path) -> None:
        """After a run, two-layer publish stores W1-W4; second run hydrates them (TC-3250).

        W1 → publish_raw_artifacts → raw/<sha>/w1/
        W2/W3/W4 → publish_derived_artifacts → derived/<sha>/<sig>/
        Second run hydrates via hydrate_from_raw + hydrate_from_derived.
        """
        # Simulate a completed run with artifacts
        run_dir_1 = _make_run_dir(tmp_path / "first")
        run_config = _make_run_config()
        sha = run_config["github_ref"]
        sig = compute_interpretation_signature(run_config)

        # Write W1-W4 artifacts as if the pipeline produced them
        art_dir = run_dir_1 / "artifacts"
        for name, content in {
            "repo_inventory.json": {"repo_sha": sha, "files": []},
            "product_facts.json": {"product_name": "test"},
            "snippet_catalog.json": {"snippets": []},
            "page_plan.json": {"pages": []},
            "shared_facts.json": {"facts": {}},
        }.items():
            (art_dir / name).write_text(json.dumps(content), encoding="utf-8")

        # Publish to store via two-layer functions (TC-3250)
        store_root = tmp_path / ".foss_state"
        store_key = get_store_key(run_config)
        raw_published = publish_raw_artifacts(store_root, store_key, sha, run_dir_1)
        derived_published = publish_derived_artifacts(store_root, store_key, sha, sig, run_dir_1)
        assert raw_published == 1   # repo_inventory.json (W1)
        assert derived_published == 4  # product_facts + snippet_catalog + page_plan + shared_facts

        # Second run: find and hydrate via new two-layer functions
        run_dir_2 = _make_run_dir(tmp_path / "second")
        raw_set = find_raw_artifact_set(store_root, store_key, sha)
        derived_set = find_derived_artifact_set(store_root, store_key, sha, sig)
        assert raw_set is not None
        assert derived_set is not None

        raw_hydrated = hydrate_from_raw(run_dir_2, raw_set)
        derived_hydrated = hydrate_from_derived(run_dir_2, derived_set)
        assert raw_hydrated == 1
        assert derived_hydrated == 4

        # Phase selector sees W1-W4 artifacts → picks W5
        decision = select_phase(run_dir_2, sha, goal="draft")
        assert decision.start_worker == "W5"

    def test_done_state_with_all_artifacts(self, tmp_path: Path) -> None:
        """All artifacts present + drafts → DONE."""
        run_dir = _make_run_dir(tmp_path, with_drafts=True)
        run_config = _make_run_config()
        sha = run_config["github_ref"]

        # Write ALL artifacts
        art_dir = run_dir / "artifacts"
        for name, content in {
            "repo_inventory.json": {"repo_sha": sha, "files": []},
            "product_facts.json": {"product_name": "test", "claims": []},
            "snippet_catalog.json": {"snippets": []},
            "page_plan.json": {"pages": []},
            "shared_facts.json": {"facts": {}},
            "draft_manifest.json": {"pages": []},
            "patch_bundle.json": {"patches": []},
            "validation_report.json": {"gates": [], "issues": [], "ok": True},
        }.items():
            (art_dir / name).write_text(json.dumps(content), encoding="utf-8")

        decision = select_phase(run_dir, sha, goal="draft")
        assert decision.start_worker == "DONE"

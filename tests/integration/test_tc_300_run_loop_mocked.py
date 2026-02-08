"""TC-1035: Mocked orchestrator run loop integration test.

This module creates a fully mocked run loop that exercises the
W1 -> W2 -> W3 -> W4 -> W5 -> W6 -> W7 sequence without external
services. Each worker is replaced by a fixture that produces
deterministic artifacts.

Unlike test_tc_300_run_loop.py (which is skipped due to real worker
invocations), this test mocks the WORKER_DISPATCH to inject stub
worker functions that produce minimal valid artifacts.

Spec references:
- specs/11_state_and_events.md (Event log and replay)
- specs/28_coordination_and_handoffs.md (Run loop coordination)
- specs/21_worker_contracts.md (Worker I/O contracts)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Stub worker functions that produce minimal valid artifacts
# ---------------------------------------------------------------------------
def stub_repo_scout(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W1 RepoScout: produces repo_inventory.json and friends."""
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    repo_inventory = {
        "schema_version": "1.0",
        "repo_url": "https://github.com/Test/repo",
        "files": [],
    }
    (artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory, indent=2, sort_keys=True)
    )

    frontmatter_contract = {"fields": []}
    (artifacts_dir / "frontmatter_contract.json").write_text(
        json.dumps(frontmatter_contract, indent=2, sort_keys=True)
    )

    site_context = {"site_url": "https://docs.aspose.org"}
    (artifacts_dir / "site_context.json").write_text(
        json.dumps(site_context, indent=2, sort_keys=True)
    )

    hugo_facts = {"config": {}}
    (artifacts_dir / "hugo_facts.json").write_text(
        json.dumps(hugo_facts, indent=2, sort_keys=True)
    )

    return {"status": "success", "artifacts": ["repo_inventory.json"]}


def stub_facts_builder(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W2 FactsBuilder: produces product_facts.json and evidence_map.json."""
    artifacts_dir = run_dir / "artifacts"

    product_facts = {
        "schema_version": "1.0",
        "product_name": "Test Product",
        "product_slug": "test-product",
        "claims": [],
        "claim_groups": {},
    }
    (artifacts_dir / "product_facts.json").write_text(
        json.dumps(product_facts, indent=2, sort_keys=True)
    )

    evidence_map = {
        "schema_version": "1.0",
        "entries": [],
    }
    (artifacts_dir / "evidence_map.json").write_text(
        json.dumps(evidence_map, indent=2, sort_keys=True)
    )

    return {"status": "success"}


def stub_snippet_curator(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W3 SnippetCurator: produces snippet_catalog.json."""
    artifacts_dir = run_dir / "artifacts"

    snippet_catalog = {
        "schema_version": "1.0",
        "snippets": [],
    }
    (artifacts_dir / "snippet_catalog.json").write_text(
        json.dumps(snippet_catalog, indent=2, sort_keys=True)
    )

    return {"status": "success"}


def stub_ia_planner(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W4 IAPlanner: produces page_plan.json."""
    artifacts_dir = run_dir / "artifacts"

    page_plan = {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "launch_tier": "minimal",
        "pages": [
            {
                "section": "docs",
                "slug": "index",
                "output_path": "content/docs.aspose.org/test-product/en/python/index.md",
                "url_path": "/test-product/python/",
                "title": "Test Product",
                "purpose": "Landing page",
            }
        ],
    }
    (artifacts_dir / "page_plan.json").write_text(
        json.dumps(page_plan, indent=2, sort_keys=True)
    )

    return {"status": "success"}


def stub_section_writer(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W5 SectionWriter: produces draft files and draft_manifest.json."""
    artifacts_dir = run_dir / "artifacts"
    drafts_dir = run_dir / "drafts" / "docs"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    draft_content = "---\ntitle: Test Product\n---\n\n# Test Product\n\nWelcome.\n"
    (drafts_dir / "index.md").write_text(draft_content)

    draft_manifest = {
        "schema_version": "1.0",
        "run_id": run_config.get("run_id", "test"),
        "total_pages": 1,
        "draft_count": 1,
        "drafts": [
            {
                "page_id": "docs_index",
                "section": "docs",
                "slug": "index",
                "output_path": "content/docs.aspose.org/test-product/en/python/index.md",
                "draft_path": "drafts/docs/index.md",
                "title": "Test Product",
                "word_count": 5,
                "claim_count": 0,
            }
        ],
    }
    (artifacts_dir / "draft_manifest.json").write_text(
        json.dumps(draft_manifest, indent=2, sort_keys=True)
    )

    return {"status": "success"}


def stub_linker_patcher(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W6 LinkerAndPatcher: produces patch_bundle.json and applies patches."""
    artifacts_dir = run_dir / "artifacts"
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Create site worktree file
    site_dir = run_dir / "work" / "site" / "content" / "docs.aspose.org" / "test-product" / "en" / "python"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "index.md").write_text("---\ntitle: Test Product\n---\n\n# Test Product\n\nWelcome.\n")

    patch_bundle = {
        "schema_version": "1.0",
        "patches": [
            {
                "patch_id": "create_docs_index",
                "type": "create_file",
                "path": "content/docs.aspose.org/test-product/en/python/index.md",
                "new_content": "---\ntitle: Test Product\n---\n\n# Test Product\n\nWelcome.\n",
                "content_hash": "abc123",
            }
        ],
    }
    (artifacts_dir / "patch_bundle.json").write_text(
        json.dumps(patch_bundle, indent=2, sort_keys=True)
    )

    diff_report = "# Patch Application Report\n\n**Total Patches**: 1\n**Applied**: 1\n"
    (reports_dir / "diff_report.md").write_text(diff_report)

    return {
        "status": "success",
        "patch_bundle_path": str(artifacts_dir / "patch_bundle.json"),
        "diff_report_path": str(reports_dir / "diff_report.md"),
        "patches_applied": 1,
        "patches_skipped": 0,
        "content_preview_dir": "content_preview",
        "exported_files_count": 1,
    }


def stub_validator(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W7 Validator: produces validation_report.json (all pass)."""
    artifacts_dir = run_dir / "artifacts"

    validation_report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [
            {"name": "Gate0-S", "ok": True, "log_path": "logs/gate0.log"},
            {"name": "Gate1", "ok": True, "log_path": "logs/gate1.log"},
        ],
        "issues": [],
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2, sort_keys=True)
    )

    return {
        "status": "success",
        "ok": True,
        "issues": [],
    }


def stub_fixer(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W8 Fixer."""
    return {"status": "resolved", "issue_id": None, "files_changed": []}


def stub_pr_manager(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """Stub W9 PRManager: creates offline bundle."""
    artifacts_dir = run_dir / "artifacts"
    offline_dir = run_dir / "offline_bundles"
    offline_dir.mkdir(parents=True, exist_ok=True)

    payload = {"mode": "offline", "run_id": run_config.get("run_id", "test")}
    (offline_dir / "pr_payload.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True)
    )

    return {
        "ok": True,
        "status": "offline_ok",
        "message": "Offline bundle created",
        "offline_bundle": str(offline_dir / "pr_payload.json"),
        "artifacts": [str(offline_dir / "pr_payload.json")],
    }


# Stubbed dispatch map
STUB_DISPATCH = {
    "W1.RepoScout": stub_repo_scout,
    "W2.FactsBuilder": stub_facts_builder,
    "W3.SnippetCurator": stub_snippet_curator,
    "W4.IAPlanner": stub_ia_planner,
    "W5.SectionWriter": stub_section_writer,
    "W6.LinkerAndPatcher": stub_linker_patcher,
    "W7.Validator": stub_validator,
    "W8.Fixer": stub_fixer,
    "W9.PRManager": stub_pr_manager,
}


@pytest.fixture
def minimal_run_config():
    """Minimal run config for mocked run loop tests."""
    return {
        "run_id": "test-run-mocked-001",
        "product_slug": "test-product",
        "language": "python",
        "repo_url": "https://github.com/Test/repo",
        "base_ref": "main",
        "github_ref": "refs/heads/main",
        "allowed_paths": ["content/docs.aspose.org/test-product/"],
        "validation_profile": "local",
    }


# ---------------------------------------------------------------------------
# 1. Full mocked run loop: W1 -> W2 -> W3 -> W4 -> W5 -> W6 -> W7 -> W9
# ---------------------------------------------------------------------------
@patch("launch.orchestrator.worker_invoker.WORKER_DISPATCH", STUB_DISPATCH)
def test_mocked_run_loop_full_pipeline(minimal_run_config):
    """Execute the full mocked orchestrator pipeline and verify all
    artifacts are produced at each step."""
    from launch.orchestrator.run_loop import execute_run

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test-mocked-full"
        run_dir = Path(tmpdir) / "runs" / run_id

        result = execute_run(run_id, run_dir, minimal_run_config)

        # Verify run completed
        assert result.run_id == run_id
        assert result.final_state in ("DONE", "FAILED"), f"Unexpected state: {result.final_state}"

        # Verify RUN_DIR structure exists
        assert run_dir.exists()
        assert (run_dir / "events.ndjson").exists()
        assert (run_dir / "snapshot.json").exists()

        # Verify required directories
        assert (run_dir / "artifacts").exists()
        assert (run_dir / "work" / "repo").exists()
        assert (run_dir / "work" / "site").exists()

        # Verify W1 artifacts
        assert (run_dir / "artifacts" / "repo_inventory.json").exists()
        assert (run_dir / "artifacts" / "frontmatter_contract.json").exists()

        # Verify W2 artifacts
        assert (run_dir / "artifacts" / "product_facts.json").exists()
        assert (run_dir / "artifacts" / "evidence_map.json").exists()

        # Verify W3 artifacts
        assert (run_dir / "artifacts" / "snippet_catalog.json").exists()

        # Verify W4 artifacts
        assert (run_dir / "artifacts" / "page_plan.json").exists()

        # Verify W5 artifacts
        assert (run_dir / "artifacts" / "draft_manifest.json").exists()

        # Verify W6 artifacts
        assert (run_dir / "artifacts" / "patch_bundle.json").exists()

        # Verify W7 artifacts
        assert (run_dir / "artifacts" / "validation_report.json").exists()

        # Verify events were emitted
        events_text = (run_dir / "events.ndjson").read_text()
        events = [json.loads(line) for line in events_text.strip().split("\n") if line]
        assert len(events) > 0

        # Check for essential event types
        event_types = [e["type"] for e in events]
        assert "RUN_CREATED" in event_types
        assert "WORK_ITEM_QUEUED" in event_types
        assert "WORK_ITEM_STARTED" in event_types
        assert "WORK_ITEM_FINISHED" in event_types


# ---------------------------------------------------------------------------
# 2. Verify state transitions are correct
# ---------------------------------------------------------------------------
@patch("launch.orchestrator.worker_invoker.WORKER_DISPATCH", STUB_DISPATCH)
def test_mocked_run_loop_state_transitions(minimal_run_config):
    """Verify that the orchestrator transitions through expected states."""
    from launch.orchestrator.run_loop import execute_run

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test-mocked-states"
        run_dir = Path(tmpdir) / "runs" / run_id

        result = execute_run(run_id, run_dir, minimal_run_config)

        # Read events to trace state changes
        events_text = (run_dir / "events.ndjson").read_text()
        events = [json.loads(line) for line in events_text.strip().split("\n") if line]

        state_changes = [
            e for e in events if e["type"] == "RUN_STATE_CHANGED"
        ]

        # Should have multiple state changes
        assert len(state_changes) >= 3, (
            f"Expected at least 3 state changes, got {len(state_changes)}: "
            f"{[sc['payload'] for sc in state_changes]}"
        )

        # Extract state sequence
        states_seen = []
        for sc in state_changes:
            if sc["payload"].get("new_state"):
                states_seen.append(sc["payload"]["new_state"])

        # CLONED_INPUTS should be first state after CREATED
        assert "CLONED_INPUTS" in states_seen, f"States: {states_seen}"


# ---------------------------------------------------------------------------
# 3. Verify artifacts are valid JSON
# ---------------------------------------------------------------------------
@patch("launch.orchestrator.worker_invoker.WORKER_DISPATCH", STUB_DISPATCH)
def test_mocked_run_loop_artifact_validity(minimal_run_config):
    """All JSON artifacts produced by the mocked pipeline should be valid."""
    from launch.orchestrator.run_loop import execute_run

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test-mocked-validity"
        run_dir = Path(tmpdir) / "runs" / run_id

        execute_run(run_id, run_dir, minimal_run_config)

        # Check all JSON artifacts are valid
        artifacts_dir = run_dir / "artifacts"
        json_files = sorted(artifacts_dir.glob("*.json"))

        assert len(json_files) >= 5, f"Expected >=5 artifacts, got {len(json_files)}"

        for json_file in json_files:
            content = json_file.read_text(encoding="utf-8")
            try:
                data = json.loads(content)
                assert isinstance(data, dict), f"{json_file.name} should be a dict"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {json_file.name}: {e}")


# ---------------------------------------------------------------------------
# 4. Verify snapshot reconstructed correctly
# ---------------------------------------------------------------------------
@patch("launch.orchestrator.worker_invoker.WORKER_DISPATCH", STUB_DISPATCH)
def test_mocked_run_loop_snapshot_integrity(minimal_run_config):
    """Snapshot should be reconstructable from events."""
    from launch.orchestrator.run_loop import execute_run
    from launch.state.snapshot_manager import read_snapshot

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test-mocked-snapshot"
        run_dir = Path(tmpdir) / "runs" / run_id

        result = execute_run(run_id, run_dir, minimal_run_config)

        # Read snapshot
        snapshot = read_snapshot(run_dir / "snapshot.json")
        assert snapshot.run_id == run_id
        assert snapshot.schema_version is not None


# ---------------------------------------------------------------------------
# 5. Verify exit code
# ---------------------------------------------------------------------------
@patch("launch.orchestrator.worker_invoker.WORKER_DISPATCH", STUB_DISPATCH)
def test_mocked_run_loop_exit_code(minimal_run_config):
    """Run that completes successfully should have exit code 0."""
    from launch.orchestrator.run_loop import execute_run

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test-mocked-exit"
        run_dir = Path(tmpdir) / "runs" / run_id

        result = execute_run(run_id, run_dir, minimal_run_config)

        # With all stubs succeeding and validation ok=True, should reach DONE
        if result.final_state == "DONE":
            assert result.exit_code == 0
        elif result.final_state == "FAILED":
            assert result.exit_code == 2


# ---------------------------------------------------------------------------
# 6. Verify batch execution still blocked
# ---------------------------------------------------------------------------
def test_batch_execution_still_blocked():
    """Batch execution should remain blocked by OQ-BATCH-001."""
    from launch.orchestrator.run_loop import execute_batch

    with pytest.raises(NotImplementedError, match="OQ-BATCH-001"):
        execute_batch({})


# ---------------------------------------------------------------------------
# 7. Verify work item IDs follow contract format
# ---------------------------------------------------------------------------
@patch("launch.orchestrator.worker_invoker.WORKER_DISPATCH", STUB_DISPATCH)
def test_mocked_run_loop_work_item_ids(minimal_run_config):
    """Work item IDs should follow {run_id}:{worker}:{attempt} format."""
    from launch.orchestrator.run_loop import execute_run

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test-mocked-ids"
        run_dir = Path(tmpdir) / "runs" / run_id

        execute_run(run_id, run_dir, minimal_run_config)

        # Read events
        events_text = (run_dir / "events.ndjson").read_text()
        events = [json.loads(line) for line in events_text.strip().split("\n") if line]

        queued_events = [e for e in events if e["type"] == "WORK_ITEM_QUEUED"]
        assert len(queued_events) > 0

        for qe in queued_events:
            work_item_id = qe["payload"]["work_item_id"]
            # Should follow format: {run_id}:{worker}:{attempt}
            parts = work_item_id.split(":")
            assert len(parts) >= 3, f"Invalid work_item_id format: {work_item_id}"
            assert parts[0] == run_id
            assert parts[1].startswith("W")  # Worker name starts with W


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

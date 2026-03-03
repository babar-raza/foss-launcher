"""Tests for ARTIFACT_WRITTEN reducer normalization in snapshot_manager.

Verifies that the reducer correctly handles all four emitter payload patterns
found across workers W1-W11, per specs/21_worker_contracts.md:38-39.

TC-3632: Snapshot ARTIFACT_WRITTEN reducer normalization.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import pytest

from launch.models.event import EVENT_ARTIFACT_WRITTEN, Event
from launch.models.state import Snapshot
from launch.state.snapshot_manager import (
    SNAPSHOT_SCHEMA_VERSION,
    _resolve_artifact_name,
    _resolve_artifact_path,
    _resolve_writer_worker,
    apply_event_reducer,
)


def _make_snapshot() -> Snapshot:
    """Create a minimal empty snapshot for testing."""
    return Snapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        run_id="test-run",
        run_state="CREATED",
        artifacts_index={},
        work_items=[],
        issues=[],
        section_states={},
    )


def _make_event(payload: Dict[str, Any], event_id: str = "evt-001") -> Event:
    """Create an ARTIFACT_WRITTEN event with the given payload."""
    return Event(
        event_id=event_id,
        run_id="test-run",
        ts="2026-03-02T00:00:00Z",
        type=EVENT_ARTIFACT_WRITTEN,
        payload=payload,
        trace_id="trace-001",
        span_id="span-001",
    )


# ---------------------------------------------------------------------------
# Pattern 1: Spec-compliant (W1, W2, W3) — uses "name" key
# ---------------------------------------------------------------------------
class TestPattern1SpecCompliant:
    """W1/W2/W3 use the canonical {name, path, sha256, schema_id} payload."""

    def test_name_key_produces_index_entry(self):
        snapshot = _make_snapshot()
        event = _make_event({
            "name": "repo_inventory.json",
            "path": "artifacts/repo_inventory.json",
            "sha256": "a" * 64,
            "schema_id": "repo_inventory.schema.json",
        })
        result = apply_event_reducer(snapshot, event)
        assert "repo_inventory.json" in result.artifacts_index
        entry = result.artifacts_index["repo_inventory.json"]
        assert entry.path == "artifacts/repo_inventory.json"
        assert entry.sha256 == "a" * 64
        assert entry.schema_id == "repo_inventory.schema.json"
        assert entry.ts == "2026-03-02T00:00:00Z"
        assert entry.event_id == "evt-001"


# ---------------------------------------------------------------------------
# Pattern 2: W4, W5, W8 — uses "artifact" key
# ---------------------------------------------------------------------------
class TestPattern2ArtifactKey:
    """W4/W5/W8 emit {artifact: ..., path: ...} instead of {name: ...}."""

    def test_w4_page_plan_indexed(self):
        """W4 pattern: {artifact, path, page_count, launch_tier}."""
        snapshot = _make_snapshot()
        event = _make_event({
            "artifact": "page_plan.json",
            "path": "artifacts/page_plan.json",
            "page_count": 12,
            "launch_tier": "standard",
        })
        result = apply_event_reducer(snapshot, event)
        assert "page_plan.json" in result.artifacts_index
        entry = result.artifacts_index["page_plan.json"]
        assert entry.path == "artifacts/page_plan.json"
        assert entry.sha256 == ""
        assert entry.schema_id == ""

    def test_w5_draft_manifest_indexed(self):
        """W5 pattern for manifest: {artifact, path, draft_count}."""
        snapshot = _make_snapshot()
        event = _make_event({
            "artifact": "draft_manifest.json",
            "path": "artifacts/draft_manifest.json",
            "draft_count": 5,
        })
        result = apply_event_reducer(snapshot, event)
        assert "draft_manifest.json" in result.artifacts_index
        assert result.artifacts_index["draft_manifest.json"].path == "artifacts/draft_manifest.json"

    def test_w5_draft_page_indexed(self):
        """W5 pattern for individual draft: {artifact: "draft", page_id, path}."""
        snapshot = _make_snapshot()
        event = _make_event({
            "artifact": "draft",
            "page_id": "getting-started",
            "path": "drafts/quickstart/getting-started.md",
        })
        result = apply_event_reducer(snapshot, event)
        assert "draft" in result.artifacts_index
        assert result.artifacts_index["draft"].path == "drafts/quickstart/getting-started.md"

    def test_w8_patch_bundle_indexed(self):
        """W8 pattern: {artifact, path, patch_count}."""
        snapshot = _make_snapshot()
        event = _make_event({
            "artifact": "patch_bundle.json",
            "path": "artifacts/patch_bundle.json",
            "patch_count": 8,
        })
        result = apply_event_reducer(snapshot, event)
        assert "patch_bundle.json" in result.artifacts_index
        assert result.artifacts_index["patch_bundle.json"].path == "artifacts/patch_bundle.json"


# ---------------------------------------------------------------------------
# Pattern 3: W9 — uses "artifact_name" / "artifact_path" keys
# ---------------------------------------------------------------------------
class TestPattern3W9:
    """W9 emits {artifact_name, artifact_path} instead of {name, path}."""

    def test_w9_validation_report_indexed(self):
        """Exact W9 payload from w9_validator/worker.py:1632."""
        snapshot = _make_snapshot()
        event = _make_event({
            "artifact_name": "validation_report.json",
            "artifact_path": "artifacts/validation_report.json",
        })
        result = apply_event_reducer(snapshot, event)
        assert "validation_report.json" in result.artifacts_index
        entry = result.artifacts_index["validation_report.json"]
        assert entry.path == "artifacts/validation_report.json"
        assert entry.sha256 == ""
        assert entry.schema_id == ""

    def test_artifact_path_resolved_when_path_missing(self):
        """artifact_path is used when 'path' key is absent."""
        snapshot = _make_snapshot()
        event = _make_event({
            "name": "some_artifact.json",
            "artifact_path": "artifacts/some_artifact.json",
        })
        result = apply_event_reducer(snapshot, event)
        assert result.artifacts_index["some_artifact.json"].path == "artifacts/some_artifact.json"


# ---------------------------------------------------------------------------
# Pattern 4: W11 — uses "artifact_type" key
# ---------------------------------------------------------------------------
class TestPattern4W11:
    """W11 emits {worker, artifact_type, path}."""

    def test_w11_pr_metadata_indexed(self):
        """Exact W11 payload from w11_pr_manager/worker.py:750."""
        snapshot = _make_snapshot()
        event = _make_event({
            "worker": "W9_PRManager",
            "artifact_type": "pr_metadata",
            "path": "artifacts/pr_metadata.json",
        })
        result = apply_event_reducer(snapshot, event)
        assert "pr_metadata" in result.artifacts_index
        entry = result.artifacts_index["pr_metadata"]
        assert entry.path == "artifacts/pr_metadata.json"
        assert entry.writer_worker == "W9_PRManager"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """Edge cases and priority resolution."""

    def test_empty_payload_no_crash(self):
        """Empty payload must not crash; no entry created."""
        snapshot = _make_snapshot()
        event = _make_event({})
        result = apply_event_reducer(snapshot, event)
        assert len(result.artifacts_index) == 0

    def test_empty_payload_logs_warning(self, caplog):
        """Empty payload emits a warning via logger."""
        snapshot = _make_snapshot()
        event = _make_event({})
        with caplog.at_level(logging.WARNING, logger="launch.state.snapshot_manager"):
            apply_event_reducer(snapshot, event)
        assert "no resolvable artifact name" in caplog.text

    def test_name_takes_priority_over_artifact(self):
        """When both 'name' and 'artifact' are present, 'name' wins."""
        snapshot = _make_snapshot()
        event = _make_event({
            "name": "canonical_name.json",
            "artifact": "alt_name.json",
            "path": "artifacts/file.json",
        })
        result = apply_event_reducer(snapshot, event)
        assert "canonical_name.json" in result.artifacts_index
        assert "alt_name.json" not in result.artifacts_index

    def test_path_takes_priority_over_artifact_path(self):
        """When both 'path' and 'artifact_path' are present, 'path' wins."""
        snapshot = _make_snapshot()
        event = _make_event({
            "name": "test.json",
            "path": "artifacts/canonical.json",
            "artifact_path": "artifacts/alt.json",
        })
        result = apply_event_reducer(snapshot, event)
        assert result.artifacts_index["test.json"].path == "artifacts/canonical.json"

    def test_last_writer_wins_for_same_name(self):
        """Two events with the same artifact name: second overwrites first."""
        snapshot = _make_snapshot()
        e1 = _make_event(
            {"name": "repo_inventory.json", "path": "old_path", "sha256": "a" * 64},
            event_id="evt-001",
        )
        e2 = _make_event(
            {"name": "repo_inventory.json", "path": "new_path", "sha256": "b" * 64},
            event_id="evt-002",
        )
        snapshot = apply_event_reducer(snapshot, e1)
        snapshot = apply_event_reducer(snapshot, e2)
        assert snapshot.artifacts_index["repo_inventory.json"].path == "new_path"
        assert snapshot.artifacts_index["repo_inventory.json"].sha256 == "b" * 64


# ---------------------------------------------------------------------------
# Helper unit tests: _resolve_artifact_name
# ---------------------------------------------------------------------------
class TestResolveArtifactName:
    """Unit tests for _resolve_artifact_name() priority chain."""

    def test_name_key(self):
        assert _resolve_artifact_name({"name": "a.json"}) == "a.json"

    def test_artifact_name_key(self):
        assert _resolve_artifact_name({"artifact_name": "b.json"}) == "b.json"

    def test_artifact_key(self):
        assert _resolve_artifact_name({"artifact": "c.json"}) == "c.json"

    def test_artifact_type_key(self):
        assert _resolve_artifact_name({"artifact_type": "pr_metadata"}) == "pr_metadata"

    def test_empty_dict(self):
        assert _resolve_artifact_name({}) == ""

    def test_priority_name_over_artifact(self):
        assert _resolve_artifact_name({"name": "a", "artifact": "b"}) == "a"

    def test_priority_artifact_name_over_artifact(self):
        assert _resolve_artifact_name({"artifact_name": "a", "artifact": "b"}) == "a"


# ---------------------------------------------------------------------------
# Helper unit tests: _resolve_artifact_path
# ---------------------------------------------------------------------------
class TestResolveArtifactPath:
    """Unit tests for _resolve_artifact_path() priority chain."""

    def test_path_key(self):
        assert _resolve_artifact_path({"path": "/x"}) == "/x"

    def test_artifact_path_key(self):
        assert _resolve_artifact_path({"artifact_path": "/y"}) == "/y"

    def test_path_over_artifact_path(self):
        assert _resolve_artifact_path({"path": "/x", "artifact_path": "/y"}) == "/x"

    def test_empty(self):
        assert _resolve_artifact_path({}) == ""


# ---------------------------------------------------------------------------
# Helper unit tests: _resolve_writer_worker
# ---------------------------------------------------------------------------
class TestResolveWriterWorker:
    """Unit tests for _resolve_writer_worker() priority chain."""

    def test_writer_worker_key(self):
        assert _resolve_writer_worker({"writer_worker": "W1"}) == "W1"

    def test_worker_key_fallback(self):
        assert _resolve_writer_worker({"worker": "W9_PRManager"}) == "W9_PRManager"

    def test_writer_worker_over_worker(self):
        assert _resolve_writer_worker({"writer_worker": "W1", "worker": "W11"}) == "W1"

    def test_empty(self):
        assert _resolve_writer_worker({}) == ""

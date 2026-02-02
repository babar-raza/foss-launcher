"""Unit tests for TC-400: W1 RepoScout integrator.

Tests cover:
- Full pipeline integration (TC-401 → TC-402 → TC-403 → TC-404)
- Error handling and rollback
- Artifact validation (all expected artifacts present)
- Event sequence validation
- Idempotency (can re-run safely)
- Sub-worker coordination

Spec references:
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (Event emission)

TC-400: W1 RepoScout integrator
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from launch.workers.w1_repo_scout import (
    execute_repo_scout,
    RepoScoutError,
    RepoScoutCloneError,
    RepoScoutFingerprintError,
    RepoScoutDiscoveryError,
)
from launch.workers.w1_repo_scout.worker import (
    emit_event,
    emit_artifact_written_event,
)
from launch.io.run_layout import RunLayout
from launch.models.run_config import RunConfig


def create_minimal_run_config(**overrides):
    """Create minimal run_config for testing."""
    config = {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "product_name": "Test Product",
        "family": "test",
        "github_repo_url": "https://github.com/aspose-cells/aspose-cells-foss-python",
        "github_ref": "main",
        "required_sections": ["overview", "features"],
        "site_layout": {"content_dir": "content", "output_dir": "public"},
        "allowed_paths": ["content/", "data/"],
        "llm": {"provider": "test", "model": "test-model"},
        "mcp": {"enabled": False},
        "telemetry": {"enabled": False},
        "commit_service": {"mode": "test"},
        "templates_version": "1.0",
        "ruleset_version": "1.0",
        "allow_inference": False,
        "max_fix_attempts": 3,
        "budgets": {"max_tokens": 10000},
    }
    config.update(overrides)
    return config


class TestRepoScoutIntegration:
    """Test W1 RepoScout full pipeline integration."""

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_full_pipeline_success(self, mock_clone):
        """Test successful execution of full RepoScout pipeline."""
        # Mock clone_and_resolve to avoid actual git operations
        from launch.workers._git.clone_helpers import ResolvedRepo

        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-cells/aspose-cells-foss-python",
            requested_ref="main",
            resolved_sha="a" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create mock repo directory with some files
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)

            # Create sample files
            (repo_dir / "README.md").write_text("# Test Repo\n\n## Features\n")
            (repo_dir / "setup.py").write_text("from setuptools import setup\n")
            (repo_dir / "src").mkdir()
            (repo_dir / "src" / "main.py").write_text("def hello():\n    pass\n")

            # Create docs directory with doc files
            docs_dir = repo_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "intro.md").write_text("# Introduction\n")

            # Create examples directory with example files
            examples_dir = repo_dir / "examples"
            examples_dir.mkdir()
            (examples_dir / "example_basic.py").write_text("# Example\nprint('hello')\n")

            # Create run_config
            run_config = create_minimal_run_config()

            # Execute RepoScout
            result = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
                run_id="test_run_001",
                trace_id="trace_001",
                span_id="span_001",
            )

            # Verify result structure
            assert result["status"] == "success"
            assert result["error"] is None
            assert "artifacts" in result
            assert "metadata" in result

            # Verify all artifacts were created
            assert "resolved_refs" in result["artifacts"]
            assert "repo_inventory" in result["artifacts"]
            assert "discovered_docs" in result["artifacts"]
            assert "discovered_examples" in result["artifacts"]

            # Verify artifacts exist on disk
            assert (run_layout.artifacts_dir / "resolved_refs.json").exists()
            assert (run_layout.artifacts_dir / "repo_inventory.json").exists()
            assert (run_layout.artifacts_dir / "discovered_docs.json").exists()
            assert (run_layout.artifacts_dir / "discovered_examples.json").exists()

            # Verify metadata
            assert result["metadata"]["repo_sha"] == "a" * 40
            assert result["metadata"]["file_count"] > 0
            assert result["metadata"]["docs_found"] > 0
            assert result["metadata"]["examples_found"] > 0

            # Verify events.ndjson was created and contains events
            events_file = run_dir / "events.ndjson"
            assert events_file.exists()

            events = []
            with events_file.open("r") as f:
                for line in f:
                    events.append(json.loads(line))

            # Verify event sequence
            event_types = [e["type"] for e in events]
            assert "WORK_ITEM_STARTED" in event_types
            assert "WORK_ITEM_FINISHED" in event_types
            assert event_types.count("ARTIFACT_WRITTEN") >= 4  # At least 4 artifacts

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_idempotency(self, mock_clone):
        """Test that RepoScout can be re-run safely (idempotent)."""
        from launch.workers._git.clone_helpers import ResolvedRepo

        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-cells/aspose-cells-foss-python",
            requested_ref="main",
            resolved_sha="b" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create mock repo directory
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "README.md").write_text("# Test\n")

            run_config = create_minimal_run_config()

            # Run once
            result1 = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
                run_id="test_run_001",
            )

            assert result1["status"] == "success"

            # Capture first inventory
            inventory1_path = run_layout.artifacts_dir / "repo_inventory.json"
            inventory1 = json.loads(inventory1_path.read_text())

            # Run again (idempotent re-run)
            result2 = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
                run_id="test_run_002",
            )

            assert result2["status"] == "success"

            # Capture second inventory
            inventory2 = json.loads(inventory1_path.read_text())

            # Verify deterministic output (same fingerprint)
            assert inventory1["repo_fingerprint"] == inventory2["repo_fingerprint"]
            assert inventory1["file_count"] == inventory2["file_count"]

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_artifact_validation(self, mock_clone):
        """Test that all artifacts are valid JSON and contain required fields."""
        from launch.workers._git.clone_helpers import ResolvedRepo

        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-cells/aspose-cells-foss-python",
            requested_ref="main",
            resolved_sha="c" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create mock repo directory
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "README.md").write_text("# Test\n")
            (repo_dir / "docs").mkdir()
            (repo_dir / "docs" / "guide.md").write_text("# Guide\n")

            run_config = create_minimal_run_config()

            result = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
            )

            assert result["status"] == "success"

            # Validate resolved_refs.json
            resolved_refs = json.loads(
                (run_layout.artifacts_dir / "resolved_refs.json").read_text()
            )
            assert "repo" in resolved_refs
            assert resolved_refs["repo"]["resolved_sha"] == "c" * 40
            assert resolved_refs["repo"]["repo_url"] == "https://github.com/aspose-cells/aspose-cells-foss-python"

            # Validate repo_inventory.json
            inventory = json.loads(
                (run_layout.artifacts_dir / "repo_inventory.json").read_text()
            )
            assert "repo_fingerprint" in inventory
            assert "file_count" in inventory
            assert "paths" in inventory
            assert "doc_roots" in inventory
            assert "example_roots" in inventory
            assert inventory["repo_sha"] == "c" * 40

            # Validate discovered_docs.json
            docs = json.loads(
                (run_layout.artifacts_dir / "discovered_docs.json").read_text()
            )
            assert "doc_roots" in docs
            assert "doc_entrypoints" in docs
            assert "discovery_summary" in docs
            assert docs["discovery_summary"]["total_docs_found"] >= 0

            # Validate discovered_examples.json
            examples = json.loads(
                (run_layout.artifacts_dir / "discovered_examples.json").read_text()
            )
            assert "example_roots" in examples
            assert "example_paths" in examples
            assert "discovery_summary" in examples
            assert examples["discovery_summary"]["total_examples_found"] >= 0

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_error_handling_clone_failure(self, mock_clone):
        """Test error handling when clone fails."""
        from launch.workers._git.clone_helpers import GitCloneError

        # Mock clone failure
        mock_clone.side_effect = GitCloneError("Network error (RETRYABLE)")

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)

            run_config = create_minimal_run_config()

            # Execute should raise RepoScoutCloneError
            with pytest.raises(RepoScoutCloneError, match="Clone failed"):
                execute_repo_scout(
                    run_dir=run_dir,
                    run_config=run_config,
                )

            # Verify WORK_ITEM_FAILED event was emitted
            events_file = run_dir / "events.ndjson"
            if events_file.exists():
                events = []
                with events_file.open("r") as f:
                    for line in f:
                        events.append(json.loads(line))

                event_types = [e["type"] for e in events]
                assert "WORK_ITEM_FAILED" in event_types

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_error_handling_missing_repo_dir(self, mock_clone):
        """Test error handling when repo directory is missing (TC-402 fails)."""
        from launch.workers._git.clone_helpers import ResolvedRepo

        # Mock successful clone but don't create the directory
        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-cells/aspose-cells-foss-python",
            requested_ref="main",
            resolved_sha="d" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Don't create repo directory - this will cause TC-402 to fail
            run_config = create_minimal_run_config()

            # This should fail because repo directory doesn't exist
            with pytest.raises(RepoScoutFingerprintError, match="not found"):
                execute_repo_scout(
                    run_dir=run_dir,
                    run_config=run_config,
                )

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_event_sequence_validation(self, mock_clone):
        """Test that events are emitted in correct order."""
        from launch.workers._git.clone_helpers import ResolvedRepo

        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-cells/aspose-cells-foss-python",
            requested_ref="main",
            resolved_sha="e" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create mock repo
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "README.md").write_text("# Test\n")

            run_config = create_minimal_run_config()

            result = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
            )

            assert result["status"] == "success"

            # Load events
            events_file = run_dir / "events.ndjson"
            events = []
            with events_file.open("r") as f:
                for line in f:
                    events.append(json.loads(line))

            event_types = [e["type"] for e in events]

            # Verify sequence:
            # 1. WORK_ITEM_STARTED (W1 RepoScout)
            # 2. REPO_SCOUT_STEP_STARTED (TC-401)
            # 3. ARTIFACT_WRITTEN (resolved_refs.json)
            # 4. REPO_SCOUT_STEP_COMPLETED (TC-401)
            # 5. REPO_SCOUT_STEP_STARTED (TC-402)
            # 6. ARTIFACT_WRITTEN (repo_inventory.json)
            # 7. REPO_SCOUT_STEP_COMPLETED (TC-402)
            # ... etc for TC-403, TC-404
            # N. WORK_ITEM_FINISHED (W1 RepoScout)

            assert event_types[0] == "WORK_ITEM_STARTED"
            assert event_types[-1] == "WORK_ITEM_FINISHED"

            # Verify step events
            step_started_count = event_types.count("REPO_SCOUT_STEP_STARTED")
            step_completed_count = event_types.count("REPO_SCOUT_STEP_COMPLETED")
            assert step_started_count == 4  # TC-401, TC-402, TC-403, TC-404
            assert step_completed_count == 4

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_empty_repository_edge_case(self, mock_clone):
        """Test handling of empty repository (no files)."""
        from launch.workers._git.clone_helpers import ResolvedRepo

        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-pdf/aspose-pdf-foss-java",
            requested_ref="main",
            resolved_sha="f" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create empty repo directory
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)

            run_config = create_minimal_run_config(
                github_repo_url="https://github.com/aspose-pdf/aspose-pdf-foss-java",
                github_ref="main",
            )

            result = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
            )

            # Should succeed but with zero files
            assert result["status"] == "success"
            assert result["metadata"]["file_count"] == 0
            assert result["metadata"]["docs_found"] == 0
            assert result["metadata"]["examples_found"] == 0

            # Verify repo_inventory has zero fingerprint
            inventory = json.loads(
                (run_layout.artifacts_dir / "repo_inventory.json").read_text()
            )
            assert inventory["repo_fingerprint"] == "0" * 64
            assert inventory["file_count"] == 0

    @patch("launch.workers.w1_repo_scout.clone.clone_and_resolve")
    def test_no_docs_no_examples(self, mock_clone):
        """Test repository with code but no docs or examples."""
        from launch.workers._git.clone_helpers import ResolvedRepo

        mock_clone.return_value = ResolvedRepo(
            repo_url="https://github.com/aspose-words/aspose-words-foss-python",
            requested_ref="main",
            resolved_sha="0" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create repo with only code files
            repo_dir = run_layout.work_dir / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "src").mkdir()
            (repo_dir / "src" / "main.py").write_text("def main():\n    pass\n")
            (repo_dir / "setup.py").write_text("from setuptools import setup\n")

            run_config = create_minimal_run_config(
                github_repo_url="https://github.com/aspose-words/aspose-words-foss-python",
                github_ref="main",
            )

            result = execute_repo_scout(
                run_dir=run_dir,
                run_config=run_config,
            )

            # Should succeed
            assert result["status"] == "success"
            assert result["metadata"]["file_count"] == 2
            assert result["metadata"]["docs_found"] == 0
            assert result["metadata"]["examples_found"] == 0

            # Verify empty discovery results
            docs = json.loads(
                (run_layout.artifacts_dir / "discovered_docs.json").read_text()
            )
            assert docs["discovery_summary"]["total_docs_found"] == 0

            examples = json.loads(
                (run_layout.artifacts_dir / "discovered_examples.json").read_text()
            )
            assert examples["discovery_summary"]["total_examples_found"] == 0


class TestEventEmissionHelpers:
    """Test event emission helper functions."""

    def test_emit_event(self):
        """Test emit_event helper function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            emit_event(
                run_layout,
                run_id="test_run",
                trace_id="trace_123",
                span_id="span_456",
                event_type="TEST_EVENT",
                payload={"key": "value"},
            )

            events_file = run_dir / "events.ndjson"
            assert events_file.exists()

            with events_file.open("r") as f:
                event = json.loads(f.readline())

            assert event["type"] == "TEST_EVENT"
            assert event["run_id"] == "test_run"
            assert event["trace_id"] == "trace_123"
            assert event["span_id"] == "span_456"
            assert event["payload"]["key"] == "value"

    def test_emit_artifact_written_event(self):
        """Test emit_artifact_written_event helper function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            run_layout = RunLayout(run_dir=run_dir)

            # Create a dummy artifact
            run_layout.artifacts_dir.mkdir(parents=True)
            artifact_path = run_layout.artifacts_dir / "test_artifact.json"
            artifact_path.write_text('{"test": true}\n')

            emit_artifact_written_event(
                run_layout,
                run_id="test_run",
                trace_id="trace_123",
                span_id="span_456",
                artifact_name="test_artifact.json",
                schema_id="test_artifact.schema.json",
            )

            events_file = run_dir / "events.ndjson"
            assert events_file.exists()

            with events_file.open("r") as f:
                event = json.loads(f.readline())

            assert event["type"] == "ARTIFACT_WRITTEN"
            assert event["payload"]["name"] == "test_artifact.json"
            assert event["payload"]["schema_id"] == "test_artifact.schema.json"
            assert "sha256" in event["payload"]
            assert len(event["payload"]["sha256"]) == 64  # SHA-256 hex


class TestExceptionHierarchy:
    """Test RepoScout exception hierarchy."""

    def test_exception_inheritance(self):
        """Test that exceptions inherit correctly."""
        assert issubclass(RepoScoutCloneError, RepoScoutError)
        assert issubclass(RepoScoutFingerprintError, RepoScoutError)
        assert issubclass(RepoScoutDiscoveryError, RepoScoutError)

        # Verify they can be caught by base exception
        try:
            raise RepoScoutCloneError("test")
        except RepoScoutError:
            pass  # Should catch

    def test_exception_messages(self):
        """Test exception message propagation."""
        msg = "Test error message"

        try:
            raise RepoScoutCloneError(msg)
        except RepoScoutCloneError as e:
            assert str(e) == msg

        try:
            raise RepoScoutFingerprintError(msg)
        except RepoScoutFingerprintError as e:
            assert str(e) == msg

        try:
            raise RepoScoutDiscoveryError(msg)
        except RepoScoutDiscoveryError as e:
            assert str(e) == msg

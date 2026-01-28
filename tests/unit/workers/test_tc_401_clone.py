"""Unit tests for TC-401: Clone inputs and resolve SHAs deterministically.

Tests cover:
- Git clone and SHA resolution helpers
- Deterministic output verification
- Error handling (network failures, invalid refs)
- Event emission
- Artifact creation

Spec references:
- specs/02_repo_ingestion.md (Clone and fingerprint)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md (W1 binding requirements)

TC-401: W1.1 Clone inputs and resolve SHAs deterministically
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from launch.workers._git.clone_helpers import (
    clone_and_resolve,
    resolve_remote_ref,
    GitCloneError,
    GitResolveError,
    ResolvedRepo,
)
from launch.workers.w1_repo_scout.clone import (
    clone_inputs,
    write_resolved_refs_artifact,
    emit_clone_events,
)
from launch.io.run_layout import RunLayout
from launch.models.run_config import RunConfig


class TestCloneHelpers:
    """Test git clone and SHA resolution helpers."""

    def test_resolved_repo_dataclass(self):
        """Test ResolvedRepo dataclass structure."""
        repo = ResolvedRepo(
            repo_url="https://github.com/example/repo.git",
            requested_ref="main",
            resolved_sha="a" * 40,
            default_branch="main",
            clone_path="/tmp/repo",
        )

        assert repo.repo_url == "https://github.com/example/repo.git"
        assert repo.requested_ref == "main"
        assert repo.resolved_sha == "a" * 40
        assert repo.default_branch == "main"
        assert repo.clone_path == "/tmp/repo"

    @patch("subprocess.run")
    def test_clone_and_resolve_success(self, mock_run):
        """Test successful clone and SHA resolution."""
        # Mock git clone success
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        # Mock git rev-parse (resolve SHA)
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "rev-parse" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="abcdef1234567890abcdef1234567890abcdef12\n",
                    stderr="",
                )
            elif "symbolic-ref" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="refs/remotes/origin/main\n",
                    stderr="",
                )
            else:
                return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "repo"
            result = clone_and_resolve(
                repo_url="https://github.com/example/repo.git",
                ref="main",
                target_dir=target_dir,
                shallow=False,
            )

            assert result.repo_url == "https://github.com/example/repo.git"
            assert result.requested_ref == "main"
            assert result.resolved_sha == "abcdef1234567890abcdef1234567890abcdef12"
            assert result.default_branch == "main"
            assert str(target_dir.absolute()) in result.clone_path

    @patch("subprocess.run")
    def test_clone_and_resolve_shallow(self, mock_run):
        """Test shallow clone operation."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            # Verify --depth 1 is included for shallow clone
            if "clone" in cmd:
                assert "--depth" in cmd
                assert "1" in cmd
                return MagicMock(returncode=0, stdout="", stderr="")
            elif "rev-parse" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="1234567890abcdef1234567890abcdef12345678\n",
                    stderr="",
                )
            elif "symbolic-ref" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="refs/remotes/origin/develop\n",
                    stderr="",
                )
            else:
                return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "repo"
            result = clone_and_resolve(
                repo_url="https://github.com/example/repo.git",
                ref="develop",
                target_dir=target_dir,
                shallow=True,
            )

            assert result.resolved_sha == "1234567890abcdef1234567890abcdef12345678"
            assert result.default_branch == "develop"

    @patch("subprocess.run")
    def test_clone_failure_network_error(self, mock_run):
        """Test clone failure with network error (retryable)."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: unable to access 'https://github.com/example/repo.git/': Connection timeout",
            stdout="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "repo"
            with pytest.raises(GitCloneError) as exc_info:
                clone_and_resolve(
                    repo_url="https://github.com/example/repo.git",
                    ref="main",
                    target_dir=target_dir,
                )

            assert "RETRYABLE" in str(exc_info.value)
            assert "timeout" in str(exc_info.value).lower()

    @patch("subprocess.run")
    def test_clone_failure_invalid_ref(self, mock_run):
        """Test clone failure with invalid ref (not retryable)."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: Remote branch nonexistent not found in upstream origin",
            stdout="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "repo"
            with pytest.raises(GitCloneError) as exc_info:
                clone_and_resolve(
                    repo_url="https://github.com/example/repo.git",
                    ref="nonexistent",
                    target_dir=target_dir,
                )

            # Should NOT be retryable
            assert "RETRYABLE" not in str(exc_info.value)

    @patch("subprocess.run")
    def test_sha_resolution_invalid_format(self, mock_run):
        """Test SHA resolution with invalid SHA format."""

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "clone" in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif "rev-parse" in cmd:
                # Return invalid SHA (too short)
                return MagicMock(returncode=0, stdout="abc123\n", stderr="")
            else:
                return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "repo"
            with pytest.raises(GitResolveError) as exc_info:
                clone_and_resolve(
                    repo_url="https://github.com/example/repo.git",
                    ref="main",
                    target_dir=target_dir,
                )

            assert "Invalid SHA format" in str(exc_info.value)

    @patch("subprocess.run")
    def test_resolve_remote_ref_success(self, mock_run):
        """Test remote ref resolution without clone."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="fedcba9876543210fedcba9876543210fedcba98\trefs/heads/main\n",
            stderr="",
        )

        sha = resolve_remote_ref(
            repo_url="https://github.com/example/repo.git",
            ref="main",
        )

        assert sha == "fedcba9876543210fedcba9876543210fedcba98"

    @patch("subprocess.run")
    def test_resolve_remote_ref_network_error(self, mock_run):
        """Test remote ref resolution with network error."""
        mock_run.side_effect = Exception("Connection timeout")

        with pytest.raises(Exception):
            resolve_remote_ref(
                repo_url="https://github.com/example/repo.git",
                ref="main",
            )


class TestCloneWorker:
    """Test clone worker functions."""

    def test_write_resolved_refs_artifact(self):
        """Test artifact writing with deterministic JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            resolved_metadata = {
                "repo": {
                    "repo_url": "https://github.com/example/repo.git",
                    "requested_ref": "main",
                    "resolved_sha": "a" * 40,
                    "default_branch": "main",
                    "clone_path": "/tmp/repo",
                },
                "site": {
                    "repo_url": "https://github.com/example/site.git",
                    "requested_ref": "main",
                    "resolved_sha": "b" * 40,
                    "default_branch": "main",
                    "clone_path": "/tmp/site",
                },
            }

            write_resolved_refs_artifact(run_layout, resolved_metadata)

            artifact_path = artifacts_dir / "resolved_refs.json"
            assert artifact_path.exists()

            # Verify JSON is valid and deterministic
            content = json.loads(artifact_path.read_text())
            assert content["repo"]["resolved_sha"] == "a" * 40
            assert content["site"]["resolved_sha"] == "b" * 40

            # Verify keys are sorted (determinism)
            json_text = artifact_path.read_text()
            assert json_text.index('"repo"') < json_text.index('"site"')

    def test_emit_clone_events(self):
        """Test event emission for clone operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()
            events_file = run_dir / "events.ndjson"
            events_file.write_text("")  # Initialize empty file

            run_layout = RunLayout(run_dir=run_dir)

            resolved_metadata = {
                "repo": {
                    "repo_url": "https://github.com/example/repo.git",
                    "requested_ref": "main",
                    "resolved_sha": "a" * 40,
                    "default_branch": "main",
                    "clone_path": str(run_dir / "work" / "repo"),
                }
            }

            # Write artifact first so ARTIFACT_WRITTEN event can be emitted
            write_resolved_refs_artifact(run_layout, resolved_metadata)

            emit_clone_events(
                run_layout=run_layout,
                run_id="test-run-123",
                trace_id="trace-456",
                span_id="span-789",
                resolved_metadata=resolved_metadata,
            )

            # Verify events were written
            events_content = events_file.read_text()
            assert events_content  # Not empty

            # Parse events
            events = [json.loads(line) for line in events_content.strip().split("\n")]

            # Verify event types in order
            event_types = [e["type"] for e in events]
            assert "WORK_ITEM_STARTED" in event_types
            assert "INPUTS_CLONED" in event_types
            assert "ARTIFACT_WRITTEN" in event_types
            assert "WORK_ITEM_FINISHED" in event_types

            # Verify INPUTS_CLONED payload
            inputs_cloned_event = next(e for e in events if e["type"] == "INPUTS_CLONED")
            assert inputs_cloned_event["payload"]["repo_sha"] == "a" * 40

    def test_clone_inputs_minimal_config(self):
        """Test clone_inputs with minimal configuration (repo only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "work").mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            # Create minimal RunConfig (repo only, no site/workflows)
            run_config = RunConfig(
                schema_version="1.0",
                product_slug="test-product",
                product_name="Test Product",
                family="test",
                github_repo_url="https://github.com/example/repo.git",
                github_ref="main",
                required_sections=["products"],
                site_layout={},
                allowed_paths=[],
                llm={},
                mcp={},
                telemetry={},
                commit_service={},
                templates_version="v1",
                ruleset_version="v1",
                allow_inference=False,
                max_fix_attempts=3,
                budgets={},
            )

            with patch("launch.workers.w1_repo_scout.clone.clone_and_resolve") as mock_clone:
                mock_clone.return_value = ResolvedRepo(
                    repo_url="https://github.com/example/repo.git",
                    requested_ref="main",
                    resolved_sha="c" * 40,
                    default_branch="main",
                    clone_path=str(run_dir / "work" / "repo"),
                )

                result = clone_inputs(run_layout, run_config)

                # Verify only repo was cloned
                assert "repo" in result
                assert "site" not in result
                assert "workflows" not in result
                assert result["repo"]["resolved_sha"] == "c" * 40

    def test_clone_inputs_full_config(self):
        """Test clone_inputs with full configuration (repo + site + workflows)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "work").mkdir()

            run_layout = RunLayout(run_dir=run_dir)

            # Create full RunConfig
            run_config = RunConfig(
                schema_version="1.0",
                product_slug="test-product",
                product_name="Test Product",
                family="test",
                github_repo_url="https://github.com/example/repo.git",
                github_ref="main",
                site_repo_url="https://github.com/example/site.git",
                site_ref="main",
                workflows_repo_url="https://github.com/example/workflows.git",
                workflows_ref="main",
                required_sections=["products"],
                site_layout={},
                allowed_paths=[],
                llm={},
                mcp={},
                telemetry={},
                commit_service={},
                templates_version="v1",
                ruleset_version="v1",
                allow_inference=False,
                max_fix_attempts=3,
                budgets={},
            )

            with patch("launch.workers.w1_repo_scout.clone.clone_and_resolve") as mock_clone:

                def clone_side_effect(repo_url, ref, target_dir, shallow):
                    if "repo.git" in repo_url:
                        sha = "r" * 40
                    elif "site.git" in repo_url:
                        sha = "s" * 40
                    elif "workflows.git" in repo_url:
                        sha = "w" * 40
                    else:
                        sha = "x" * 40

                    return ResolvedRepo(
                        repo_url=repo_url,
                        requested_ref=ref,
                        resolved_sha=sha,
                        default_branch="main",
                        clone_path=str(target_dir),
                    )

                mock_clone.side_effect = clone_side_effect

                result = clone_inputs(run_layout, run_config)

                # Verify all three were cloned
                assert "repo" in result
                assert "site" in result
                assert "workflows" in result

                assert result["repo"]["resolved_sha"] == "r" * 40
                assert result["site"]["resolved_sha"] == "s" * 40
                assert result["workflows"]["resolved_sha"] == "w" * 40


class TestDeterminism:
    """Test deterministic behavior per specs/10_determinism_and_caching.md."""

    def test_resolved_refs_artifact_deterministic(self):
        """Test that resolved_refs.json is byte-identical across runs."""
        resolved_metadata = {
            "repo": {
                "clone_path": "/tmp/repo",
                "default_branch": "main",
                "repo_url": "https://github.com/example/repo.git",
                "requested_ref": "main",
                "resolved_sha": "a" * 40,
            },
            "site": {
                "clone_path": "/tmp/site",
                "default_branch": "main",
                "repo_url": "https://github.com/example/site.git",
                "requested_ref": "main",
                "resolved_sha": "b" * 40,
            },
        }

        outputs = []
        for _ in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                run_dir = Path(tmpdir)
                artifacts_dir = run_dir / "artifacts"
                artifacts_dir.mkdir()

                run_layout = RunLayout(run_dir=run_dir)
                write_resolved_refs_artifact(run_layout, resolved_metadata)

                artifact_path = artifacts_dir / "resolved_refs.json"
                outputs.append(artifact_path.read_bytes())

        # All outputs should be byte-identical
        assert outputs[0] == outputs[1] == outputs[2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

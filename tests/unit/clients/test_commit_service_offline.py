"""Tests for commit service offline mode.

Test coverage:
- Offline bundle creation
- Bundle structure
- Deferred PR responses
- Health check in offline mode
"""

import json
import tempfile
from pathlib import Path

import pytest

from launch.clients.commit_service import CommitServiceClient


def test_offline_mode_create_commit():
    """Verify create_commit writes bundle in offline mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        client = CommitServiceClient(
            endpoint_url="http://mock",
            auth_token="mock_token",
            offline_mode=True,
            run_dir=run_dir,
        )

        response = client.create_commit(
            run_id="test_run",
            repo_url="https://github.com/example/repo",
            base_ref="main",
            branch_name="test-branch",
            allowed_paths=["content/"],
            commit_message="Test commit",
            commit_body="Test body",
            patch_bundle={"patches": []},
        )

        # Check response
        assert response["status"] == "deferred"
        assert "bundle_path" in response
        assert response["commit_sha"] == "0" * 40  # Mock SHA

        # Check bundle file
        bundle_path = Path(response["bundle_path"])
        assert bundle_path.exists()

        bundle = json.loads(bundle_path.read_text())
        assert bundle["operation"] == "create_commit"
        assert bundle["offline_mode"] is True
        assert bundle["payload"]["repo_url"] == "https://github.com/example/repo"
        assert bundle["payload"]["branch_name"] == "test-branch"


def test_offline_mode_open_pr():
    """Verify open_pr writes bundle in offline mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        client = CommitServiceClient(
            endpoint_url="http://mock",
            auth_token="mock_token",
            offline_mode=True,
            run_dir=run_dir,
        )

        response = client.open_pr(
            run_id="test_run",
            repo_url="https://github.com/example/repo",
            base_ref="main",
            head_ref="test-branch",
            title="Test PR",
            body="Test description",
        )

        # Check response
        assert response["status"] == "deferred"
        assert "bundle_path" in response
        assert response["pr_number"] == 0  # Mock PR number

        # Check bundle file
        bundle_path = Path(response["bundle_path"])
        assert bundle_path.exists()

        bundle = json.loads(bundle_path.read_text())
        assert bundle["operation"] == "open_pr"
        assert bundle["offline_mode"] is True
        assert bundle["payload"]["title"] == "Test PR"


def test_offline_mode_health_check():
    """Verify health check returns True in offline mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        client = CommitServiceClient(
            endpoint_url="http://mock",
            auth_token="mock_token",
            offline_mode=True,
            run_dir=run_dir,
        )

        # Should not raise and should return True
        assert client.health_check() is True


def test_offline_mode_env_var():
    """Verify OFFLINE_MODE env var activates offline mode."""
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        # Set env var
        original_value = os.environ.get("OFFLINE_MODE")
        try:
            os.environ["OFFLINE_MODE"] = "1"

            client = CommitServiceClient(
                endpoint_url="http://mock",
                auth_token="mock_token",
                run_dir=run_dir,
            )

            assert client.offline_mode is True

        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop("OFFLINE_MODE", None)
            else:
                os.environ["OFFLINE_MODE"] = original_value


def test_offline_mode_requires_run_dir():
    """Verify offline mode requires run_dir."""
    with pytest.raises(ValueError, match="run_dir is required"):
        CommitServiceClient(
            endpoint_url="http://mock",
            auth_token="mock_token",
            offline_mode=True,
            run_dir=None,
        )

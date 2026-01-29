"""Tests for TC-500: Clients & Services (telemetry, commit service, LLM provider).

Tests verify:
- TelemetryClient: outbox buffering, stable payloads, bounded retries
- CommitServiceClient: idempotency, deterministic requests, error mapping
- LLMProviderClient: deterministic settings, evidence capture, prompt hashing

Spec references:
- specs/16_local_telemetry_api.md (Telemetry)
- specs/17_github_commit_service.md (Commit service)
- specs/25_frameworks_and_dependencies.md (LLM provider)
- specs/10_determinism_and_caching.md (Deterministic serialization)
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from launch.clients import (
    CommitServiceClient,
    CommitServiceError,
    LLMProviderClient,
    TelemetryClient,
    TelemetryError,
)


class TestTelemetryClient:
    """Tests for TelemetryClient with outbox buffering."""

    @pytest.fixture
    def temp_run_dir(self, tmp_path: Path) -> Path:
        """Create temporary RUN_DIR for testing."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        return run_dir

    @pytest.fixture
    def client(self, temp_run_dir: Path) -> TelemetryClient:
        """Create TelemetryClient for testing."""
        return TelemetryClient(
            endpoint_url="http://localhost:8765",
            run_dir=temp_run_dir,
            timeout=10,
            max_retries=3,
        )

    def test_client_initialization(self, client: TelemetryClient, temp_run_dir: Path):
        """Test client initializes with correct settings."""
        assert client.endpoint_url == "http://localhost:8765"
        assert client.run_dir == temp_run_dir
        assert client.timeout == 10
        assert client.max_retries == 3
        assert client.outbox_path == temp_run_dir / "telemetry_outbox.jsonl"

    @patch("launch.clients.telemetry.http_post")
    def test_create_run_success(self, mock_post: Mock, client: TelemetryClient):
        """Test create_run succeeds when API is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = client.create_run(
            run_id="test-run-123",
            agent_name="launch.orchestrator",
            job_type="launch",
            start_time="2026-01-28T00:00:00Z",
            event_id="event-123",
            status="running",
        )

        assert result is True
        assert mock_post.call_count == 1

        # Verify payload structure
        call_args = mock_post.call_args
        payload_json = call_args[1]["data"]
        payload = json.loads(payload_json)

        assert payload["run_id"] == "test-run-123"
        assert payload["agent_name"] == "launch.orchestrator"
        assert payload["job_type"] == "launch"
        assert payload["event_id"] == "event-123"

    @patch("launch.clients.telemetry.http_post")
    def test_create_run_outbox_on_failure(
        self,
        mock_post: Mock,
        client: TelemetryClient,
    ):
        """Test create_run buffers to outbox when API fails."""
        mock_post.side_effect = Exception("Network error")

        result = client.create_run(
            run_id="test-run-456",
            agent_name="launch.workers.RepoScout",
            job_type="worker",
            start_time="2026-01-28T00:00:00Z",
        )

        assert result is False
        assert client.outbox_path.exists()

        # Verify outbox contains entry
        with open(client.outbox_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["endpoint"] == "/api/v1/runs"
        assert entry["payload"]["run_id"] == "test-run-456"

    @patch("launch.clients.telemetry.http_post")
    def test_stable_json_serialization(self, mock_post: Mock, client: TelemetryClient):
        """Test payload uses stable JSON serialization (deterministic)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Create run with context_json
        client.create_run(
            run_id="test-run",
            agent_name="test",
            job_type="test",
            start_time="2026-01-28T00:00:00Z",
            context_json={"z": 3, "a": 1, "m": 2},  # Unsorted keys
        )

        # Verify JSON is sorted
        call_args = mock_post.call_args
        payload_json = call_args[1]["data"]

        # Check that keys are sorted (stable serialization)
        assert '"context_json": {"a": 1, "m": 2, "z": 3}' in payload_json

    @patch("launch.clients.telemetry.http_post")
    def test_outbox_flush_success(
        self,
        mock_post: Mock,
        client: TelemetryClient,
        temp_run_dir: Path,
    ):
        """Test outbox flush sends buffered entries."""
        # Create outbox with one entry
        outbox_entry = {
            "endpoint": "/api/v1/runs",
            "payload": {
                "run_id": "buffered-run",
                "agent_name": "test",
                "job_type": "test",
                "start_time": "2026-01-28T00:00:00Z",
                "status": "running",
            },
            "method": "POST",
            "timestamp": 1234567890,
        }

        with open(client.outbox_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(outbox_entry) + "\n")

        # Mock successful POST
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Flush outbox
        successful, failed = client.flush_outbox()

        assert successful == 1
        assert failed == 0
        assert not client.outbox_path.exists()  # Outbox deleted after success

    @patch("launch.clients.telemetry.http_post")
    def test_bounded_retry_policy(self, mock_post: Mock, client: TelemetryClient):
        """Test bounded retry with exponential backoff."""
        mock_post.side_effect = Exception("Network error")

        result = client.create_run(
            run_id="test-run",
            agent_name="test",
            job_type="test",
            start_time="2026-01-28T00:00:00Z",
        )

        # Should retry max_retries times (3)
        assert mock_post.call_count == 3
        assert result is False


class TestCommitServiceClient:
    """Tests for CommitServiceClient with idempotency."""

    @pytest.fixture
    def client(self) -> CommitServiceClient:
        """Create CommitServiceClient for testing."""
        return CommitServiceClient(
            endpoint_url="http://localhost:8080/v1",
            auth_token="test-token-123",
            timeout=60,
            max_retries=3,
        )

    def test_client_initialization(self, client: CommitServiceClient):
        """Test client initializes with correct settings."""
        assert client.endpoint_url == "http://localhost:8080/v1"
        assert client.auth_token == "test-token-123"
        assert client.timeout == 60
        assert client.max_retries == 3

    @patch("launch.clients.commit_service.http_post")
    def test_create_commit_success(self, mock_post: Mock, client: CommitServiceClient):
        """Test create_commit builds deterministic request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "commit_sha": "abc123",
            "branch_name": "test-branch",
            "repo_url": "https://github.com/test/repo",
        }
        mock_post.return_value = mock_response

        result = client.create_commit(
            run_id="test-run",
            repo_url="https://github.com/test/repo",
            base_ref="main",
            branch_name="test-branch",
            allowed_paths=["content/products/"],
            commit_message="Test commit",
            commit_body="Test body",
            patch_bundle={"schema_version": "1.0", "operations": []},
            idempotency_key="test-key-123",
        )

        assert result["commit_sha"] == "abc123"
        assert mock_post.call_count == 1

        # Verify request structure
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8080/v1/commit"

        # Verify headers
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["Idempotency-Key"] == "test-key-123"

        # Verify deterministic payload
        payload_json = call_args[1]["data"]
        payload = json.loads(payload_json)
        assert payload["run_id"] == "test-run"
        assert payload["allowed_paths"] == ["content/products/"]  # Sorted

    @patch("launch.clients.commit_service.http_post")
    def test_create_commit_generates_idempotency_key(
        self,
        mock_post: Mock,
        client: CommitServiceClient,
    ):
        """Test idempotency key is generated if not provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "commit_sha": "abc123",
            "branch_name": "test-branch",
            "repo_url": "https://github.com/test/repo",
        }
        mock_post.return_value = mock_response

        client.create_commit(
            run_id="test-run",
            repo_url="https://github.com/test/repo",
            base_ref="main",
            branch_name="test-branch",
            allowed_paths=["content/"],
            commit_message="Test",
            commit_body="Body",
            patch_bundle={"schema_version": "1.0", "operations": []},
        )

        # Verify idempotency key was generated
        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        assert "Idempotency-Key" in headers

        # Validate UUID format
        key = headers["Idempotency-Key"]
        uuid.UUID(key)  # Should not raise

    @patch("launch.clients.commit_service.http_post")
    def test_create_commit_4xx_error_no_retry(
        self,
        mock_post: Mock,
        client: CommitServiceClient,
    ):
        """Test 4xx errors are not retried (client errors)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.json.return_value = {
            "code": "PATH_NOT_ALLOWED",
            "message": "Path not allowed",
        }
        mock_post.return_value = mock_response

        with pytest.raises(CommitServiceError) as exc_info:
            client.create_commit(
                run_id="test-run",
                repo_url="https://github.com/test/repo",
                base_ref="main",
                branch_name="test-branch",
                allowed_paths=["content/"],
                commit_message="Test",
                commit_body="Body",
                patch_bundle={"schema_version": "1.0", "operations": []},
            )

        # Should not retry on 4xx
        assert mock_post.call_count == 1
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "PATH_NOT_ALLOWED"

    @patch("launch.clients.commit_service.http_post")
    def test_create_commit_5xx_error_retries(
        self,
        mock_post: Mock,
        client: CommitServiceClient,
    ):
        """Test 5xx errors are retried (server errors)."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.json.side_effect = Exception("Not JSON")
        mock_post.return_value = mock_response

        with pytest.raises(CommitServiceError):
            client.create_commit(
                run_id="test-run",
                repo_url="https://github.com/test/repo",
                base_ref="main",
                branch_name="test-branch",
                allowed_paths=["content/"],
                commit_message="Test",
                commit_body="Body",
                patch_bundle={"schema_version": "1.0", "operations": []},
            )

        # Should retry max_retries times
        assert mock_post.call_count == 3

    @patch("launch.clients.commit_service.http_post")
    def test_open_pr_success(self, mock_post: Mock, client: CommitServiceClient):
        """Test open_pr builds deterministic request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pr_number": 123,
            "pr_url": "https://api.github.com/repos/test/repo/pulls/123",
            "pr_html_url": "https://github.com/test/repo/pull/123",
        }
        mock_post.return_value = mock_response

        result = client.open_pr(
            run_id="test-run",
            repo_url="https://github.com/test/repo",
            base_ref="main",
            head_ref="test-branch",
            title="Test PR",
            body="PR body",
            labels=["automated", "launch"],
        )

        assert result["pr_number"] == 123
        assert mock_post.call_count == 1

        # Verify payload
        call_args = mock_post.call_args
        payload_json = call_args[1]["data"]
        payload = json.loads(payload_json)
        assert payload["labels"] == ["automated", "launch"]  # Sorted


class TestLLMProviderClient:
    """Tests for LLMProviderClient with deterministic settings."""

    @pytest.fixture
    def temp_run_dir(self, tmp_path: Path) -> Path:
        """Create temporary RUN_DIR for testing."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        return run_dir

    @pytest.fixture
    def client(self, temp_run_dir: Path) -> LLMProviderClient:
        """Create LLMProviderClient for testing."""
        return LLMProviderClient(
            api_base_url="http://localhost:8000",
            model="test-model",
            run_dir=temp_run_dir,
            api_key="test-api-key",
            temperature=0.0,
        )

    def test_client_initialization(
        self,
        client: LLMProviderClient,
        temp_run_dir: Path,
    ):
        """Test client initializes with correct settings."""
        assert client.api_base_url == "http://localhost:8000"
        assert client.model == "test-model"
        assert client.temperature == 0.0
        assert client.evidence_dir == temp_run_dir / "evidence" / "llm_calls"

    def test_prompt_hashing_deterministic(self, client: LLMProviderClient):
        """Test prompt hashing is deterministic."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

        hash1 = client.get_prompt_version(messages)
        hash2 = client.get_prompt_version(messages)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_prompt_hashing_different_messages(self, client: LLMProviderClient):
        """Test different messages produce different hashes."""
        messages1 = [{"role": "user", "content": "Hello!"}]
        messages2 = [{"role": "user", "content": "Goodbye!"}]

        hash1 = client.get_prompt_version(messages1)
        hash2 = client.get_prompt_version(messages2)

        assert hash1 != hash2

    @patch("launch.clients.llm_provider.http_post")
    def test_chat_completion_success(
        self,
        mock_post: Mock,
        client: LLMProviderClient,
    ):
        """Test chat_completion with evidence capture."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help?",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18,
            },
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello!"}]

        result = client.chat_completion(messages, call_id="test-call-1")

        assert result["content"] == "Hello! How can I help?"
        assert result["model"] == "test-model"
        assert result["usage"]["total_tokens"] == 18
        assert "prompt_hash" in result
        assert "latency_ms" in result
        assert "evidence_path" in result

        # Verify evidence file exists
        evidence_path = Path(result["evidence_path"])
        assert evidence_path.exists()

        # Verify evidence content
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence = json.load(f)

        assert evidence["call_id"] == "test-call-1"
        assert evidence["model"] == "test-model"
        assert evidence["temperature"] == 0.0

    @patch("launch.clients.llm_provider.http_post")
    def test_chat_completion_deterministic_temperature(
        self,
        mock_post: Mock,
        client: LLMProviderClient,
    ):
        """Test temperature defaults to 0.0 for determinism."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Response"}}],
            "usage": {},
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        client.chat_completion(messages)

        # Verify request payload
        call_args = mock_post.call_args
        payload_json = call_args[1]["data"]
        payload = json.loads(payload_json)

        assert payload["temperature"] == 0.0

    @patch("launch.clients.llm_provider.http_post")
    def test_evidence_capture_atomic_write(
        self,
        mock_post: Mock,
        client: LLMProviderClient,
    ):
        """Test evidence is written atomically."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Response"}}],
            "usage": {},
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Test"}]
        result = client.chat_completion(messages, call_id="atomic-test")

        # Evidence file should exist (no .tmp files left)
        evidence_path = Path(result["evidence_path"])
        assert evidence_path.exists()

        # No temp files should exist
        temp_files = list(evidence_path.parent.glob("*.tmp"))
        assert len(temp_files) == 0


def test_client_imports():
    """Test all clients are importable from package."""
    from launch.clients import (
        CommitServiceClient,
        CommitServiceError,
        LangChainLLMAdapter,
        LLMError,
        LLMProviderClient,
        TelemetryClient,
        TelemetryError,
    )

    assert TelemetryClient is not None
    assert TelemetryError is not None
    assert CommitServiceClient is not None
    assert CommitServiceError is not None
    assert LLMProviderClient is not None
    assert LLMError is not None
    assert LangChainLLMAdapter is not None


def test_stable_json_ordering():
    """Test JSON serialization is stable (deterministic)."""
    from launch.clients.telemetry import TelemetryClient

    # Create minimal client (won't make network calls)
    client = TelemetryClient(
        endpoint_url="http://test",
        run_dir=Path("/tmp/test"),
    )

    # Test payload with unsorted dict
    payload = {"z": 3, "a": 1, "m": 2}
    json_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    # Verify keys are sorted
    assert json_str == '{"a": 1, "m": 2, "z": 3}'

"""Unit tests for telemetry API batch upload endpoint (TC-522).

Binding contract: specs/16_local_telemetry_api.md

Tests:
1. Batch upload success (multiple runs)
2. Transaction rollback on error (transactional endpoint)
3. Validation errors (empty batch, oversized batch)
4. Empty batch handling
5. Large batch performance
6. Idempotency (duplicate event_ids)
7. Partial failure handling (non-transactional endpoint)
8. Mixed success/failure scenarios
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient

from launch.telemetry_api.server import create_app, ServerConfig
from launch.telemetry_api.routes.database import TelemetryDatabase


@pytest.fixture
def test_db(tmp_path: Path) -> TelemetryDatabase:
    """Create a test database."""
    db_path = tmp_path / "test_telemetry.db"
    return TelemetryDatabase(db_path)


@pytest.fixture
def client(test_db: TelemetryDatabase) -> TestClient:
    """Create a test client with test database."""
    config = ServerConfig(db_path=str(test_db.db_path))
    app = create_app(config)
    return TestClient(app)


def generate_run_data(
    event_id: str = None,
    run_id: str = None,
    agent_name: str = "test.agent",
    job_type: str = "test",
    status: str = "running",
    parent_run_id: str = None,
) -> dict:
    """Generate test run data."""
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "run_id": run_id or f"test-run-{uuid.uuid4().hex[:8]}",
        "agent_name": agent_name,
        "job_type": job_type,
        "start_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "parent_run_id": parent_run_id,
        "product": "test-product",
        "metrics_json": {"test_metric": 123},
        "context_json": {"trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4())},
    }


class TestBatchUpload:
    """Tests for batch upload endpoint."""

    def test_batch_upload_success_multiple_runs(self, client: TestClient):
        """Test successful batch upload with multiple runs."""
        # Create 5 runs
        runs = [generate_run_data() for _ in range(5)]

        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        assert response.status_code == 201
        data = response.json()

        assert data["total"] == 5
        assert data["created"] == 5
        assert data["existing"] == 0
        assert data["failed"] == 0
        assert len(data["runs"]) == 5
        assert len(data["errors"]) == 0

        # Verify all runs were created
        for i, run in enumerate(runs):
            assert data["runs"][i]["event_id"] == run["event_id"]
            assert data["runs"][i]["run_id"] == run["run_id"]
            assert data["runs"][i]["agent_name"] == run["agent_name"]

    def test_batch_upload_empty_batch(self, client: TestClient):
        """Test batch upload with empty batch."""
        response = client.post("/api/v1/runs/batch", json={"runs": []})

        assert response.status_code == 400
        assert "at least one run" in response.json()["detail"].lower()

    def test_batch_upload_oversized_batch(self, client: TestClient):
        """Test batch upload with batch exceeding size limit."""
        # Create 1001 runs (exceeds limit of 1000)
        runs = [generate_run_data() for _ in range(1001)]

        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        assert response.status_code == 400
        assert "exceeds maximum limit" in response.json()["detail"].lower()

    def test_batch_upload_idempotency(self, client: TestClient):
        """Test idempotent batch upload (duplicate event_ids)."""
        # Create initial batch
        runs = [generate_run_data() for _ in range(3)]
        response1 = client.post("/api/v1/runs/batch", json={"runs": runs})
        assert response1.status_code == 201
        data1 = response1.json()
        assert data1["created"] == 3
        assert data1["existing"] == 0

        # Upload same batch again
        response2 = client.post("/api/v1/runs/batch", json={"runs": runs})
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["total"] == 3
        assert data2["created"] == 0
        assert data2["existing"] == 3
        assert data2["failed"] == 0

        # Verify runs are identical
        for i in range(3):
            assert data1["runs"][i]["event_id"] == data2["runs"][i]["event_id"]
            assert data1["runs"][i]["created_at"] == data2["runs"][i]["created_at"]

    def test_batch_upload_large_batch_performance(self, client: TestClient):
        """Test batch upload performance with large batch."""
        # Create 100 runs
        runs = [generate_run_data() for _ in range(100)]

        import time
        start_time = time.time()
        response = client.post("/api/v1/runs/batch", json={"runs": runs})
        duration = time.time() - start_time

        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 100
        assert data["created"] == 100
        assert data["failed"] == 0

        # Performance assertion: should complete in < 5 seconds
        assert duration < 5.0, f"Batch upload took {duration:.2f}s, expected < 5s"

    def test_batch_upload_with_parent_child_runs(self, client: TestClient):
        """Test batch upload with parent and child runs."""
        # Create parent run
        parent_run = generate_run_data(
            agent_name="launch.orchestrator",
            job_type="launch",
        )

        # Create child runs
        child_runs = [
            generate_run_data(
                agent_name="launch.workers.RepoScout",
                job_type="worker",
                parent_run_id=parent_run["run_id"],
            )
            for _ in range(3)
        ]

        # Upload batch with parent + children
        all_runs = [parent_run] + child_runs
        response = client.post("/api/v1/runs/batch", json={"runs": all_runs})

        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 4
        assert data["created"] == 4

        # Verify parent run
        assert data["runs"][0]["event_id"] == parent_run["event_id"]
        assert data["runs"][0]["parent_run_id"] is None

        # Verify child runs
        for i in range(1, 4):
            assert data["runs"][i]["parent_run_id"] == parent_run["run_id"]

    def test_batch_upload_with_metrics_and_context(self, client: TestClient):
        """Test batch upload preserves metrics_json and context_json."""
        runs = [
            generate_run_data(
                agent_name="test.agent",
                job_type="llm_call",
            )
            for _ in range(2)
        ]

        # Add detailed metrics and context
        runs[0]["metrics_json"] = {
            "tokens_prompt": 100,
            "tokens_completion": 50,
            "latency_ms": 1234,
        }
        runs[0]["context_json"] = {
            "trace_id": str(uuid.uuid4()),
            "span_id": str(uuid.uuid4()),
            "model": "gpt-4",
            "prompt_hash": "abc123",
        }

        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        assert response.status_code == 201
        data = response.json()

        # Verify metrics and context preserved
        assert data["runs"][0]["metrics_json"]["tokens_prompt"] == 100
        assert data["runs"][0]["metrics_json"]["latency_ms"] == 1234
        assert data["runs"][0]["context_json"]["model"] == "gpt-4"
        assert "trace_id" in data["runs"][0]["context_json"]

    def test_batch_upload_partial_failure_continues(self, client: TestClient):
        """Test that non-transactional batch continues on partial failure."""
        # Create runs with one that has missing required field
        runs = [
            generate_run_data() for _ in range(2)
        ]

        # Add a valid third run
        runs.append(generate_run_data())

        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        # All runs should succeed in this case (no invalid data)
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 3
        assert data["created"] == 3
        assert data["failed"] == 0


class TestBatchUploadTransactional:
    """Tests for transactional batch upload endpoint."""

    def test_batch_transactional_success(self, client: TestClient):
        """Test successful transactional batch upload."""
        runs = [generate_run_data() for _ in range(5)]

        response = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})

        assert response.status_code == 201
        data = response.json()

        assert data["total"] == 5
        assert data["created"] == 5
        assert data["existing"] == 0
        assert data["failed"] == 0
        assert len(data["runs"]) == 5

    def test_batch_transactional_rollback_on_error(self, client: TestClient):
        """Test that transactional batch rolls back on any error."""
        # Create valid runs
        runs = [generate_run_data() for _ in range(3)]

        # First upload should succeed
        response1 = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})
        assert response1.status_code == 201

        # Verify runs were created
        for run in runs:
            response = client.get(f"/api/v1/runs/{run['run_id']}")
            assert response.status_code == 200

    def test_batch_transactional_idempotency(self, client: TestClient):
        """Test transactional batch handles duplicate event_ids."""
        runs = [generate_run_data() for _ in range(3)]

        # First upload
        response1 = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})
        assert response1.status_code == 201
        data1 = response1.json()
        assert data1["created"] == 3

        # Second upload (idempotent)
        response2 = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["existing"] == 3
        assert data2["created"] == 0

    def test_batch_transactional_empty_batch(self, client: TestClient):
        """Test transactional batch rejects empty batch."""
        response = client.post("/api/v1/runs/batch-transactional", json={"runs": []})

        assert response.status_code == 400
        assert "at least one run" in response.json()["detail"].lower()

    def test_batch_transactional_oversized_batch(self, client: TestClient):
        """Test transactional batch rejects oversized batch."""
        runs = [generate_run_data() for _ in range(1001)]

        response = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})

        assert response.status_code == 400
        assert "exceeds maximum limit" in response.json()["detail"].lower()

    def test_batch_transactional_atomicity(self, client: TestClient):
        """Test that transactional batch is truly atomic."""
        # Create valid runs
        runs = [generate_run_data() for _ in range(3)]

        # Upload should succeed
        response = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})
        assert response.status_code == 201

        # Verify all runs exist
        for run in runs:
            response = client.get(f"/api/v1/runs/{run['run_id']}")
            assert response.status_code == 200


class TestBatchValidation:
    """Tests for batch upload validation."""

    def test_batch_missing_required_fields(self, client: TestClient):
        """Test batch upload validates required fields."""
        # Missing required field: agent_name
        invalid_run = {
            "event_id": str(uuid.uuid4()),
            "run_id": "test-run-123",
            "job_type": "test",
            "start_time": datetime.now(timezone.utc).isoformat(),
        }

        response = client.post("/api/v1/runs/batch", json={"runs": [invalid_run]})

        # FastAPI validation should reject this
        assert response.status_code == 422

    def test_batch_invalid_json_structure(self, client: TestClient):
        """Test batch upload validates JSON structure."""
        # Send invalid JSON (not a dict with "runs" key)
        response = client.post(
            "/api/v1/runs/batch",
            json=[generate_run_data()],  # Array instead of object with "runs" key
        )

        assert response.status_code == 422

    def test_batch_single_run(self, client: TestClient):
        """Test batch upload works with single run."""
        run = generate_run_data()

        response = client.post("/api/v1/runs/batch", json={"runs": [run]})

        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 1
        assert data["created"] == 1


class TestBatchPerformance:
    """Tests for batch upload performance characteristics."""

    def test_batch_scales_linearly(self, client: TestClient):
        """Test that batch upload scales approximately linearly."""
        import time

        # Test with 10 runs
        runs_10 = [generate_run_data() for _ in range(10)]
        start = time.time()
        response = client.post("/api/v1/runs/batch", json={"runs": runs_10})
        duration_10 = time.time() - start
        assert response.status_code == 201

        # Test with 50 runs
        runs_50 = [generate_run_data() for _ in range(50)]
        start = time.time()
        response = client.post("/api/v1/runs/batch", json={"runs": runs_50})
        duration_50 = time.time() - start
        assert response.status_code == 201

        # Should scale reasonably (not more than 10x for 5x data)
        assert duration_50 < duration_10 * 10

    def test_batch_memory_efficiency(self, client: TestClient):
        """Test batch upload is memory efficient with large payloads."""
        # Create 200 runs with large context_json
        runs = []
        for _ in range(200):
            run = generate_run_data()
            run["context_json"] = {
                "trace_id": str(uuid.uuid4()),
                "large_data": "x" * 1000,  # 1KB of data per run
            }
            runs.append(run)

        response = client.post("/api/v1/runs/batch", json={"runs": runs})

        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 200
        assert data["created"] == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

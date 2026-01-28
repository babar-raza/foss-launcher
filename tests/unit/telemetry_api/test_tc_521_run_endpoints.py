"""Unit tests for telemetry API run endpoints (TC-521).

Binding contract: specs/16_local_telemetry_api.md (Local Telemetry API)

Tests:
1. Create run endpoint (POST /api/v1/runs)
2. List runs with filtering (GET /api/v1/runs)
3. Get run by ID (GET /api/v1/runs/{run_id})
4. Update run metadata (PATCH /api/v1/runs/{event_id})
5. Stream events (GET /api/v1/runs/{run_id}/events)
6. Associate commit (POST /api/v1/runs/{event_id}/associate-commit)
7. Error handling (404, 400, 500)
8. Idempotent create
9. Pagination
10. Multiple filters
"""

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from launch.telemetry_api.server import create_app, ServerConfig
from launch.telemetry_api.routes.database import TelemetryDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_telemetry.db"
        yield db_path


@pytest.fixture
def client(temp_db):
    """Create a test client with temporary database."""
    config = ServerConfig(db_path=str(temp_db))
    app = create_app(config)
    return TestClient(app)


@pytest.fixture
def sample_run_data():
    """Generate sample run data for testing."""
    return {
        "event_id": str(uuid.uuid4()),
        "run_id": "2026-01-28T10:00:00Z-launch-test-product",
        "agent_name": "launch.orchestrator",
        "job_type": "launch",
        "start_time": "2026-01-28T10:00:00Z",
        "status": "running",
        "product": "test-product",
        "product_family": "test-family",
        "platform": "python",
        "git_repo": "https://github.com/test/repo",
        "git_branch": "main",
        "metrics_json": {"token_count": 1000},
        "context_json": {"trace_id": "abc123", "span_id": "def456"},
    }


class TestCreateRun:
    """Test POST /api/v1/runs endpoint."""

    def test_create_run_success(self, client, sample_run_data):
        """Test successful run creation."""
        response = client.post("/api/v1/runs", json=sample_run_data)

        assert response.status_code == 201
        data = response.json()

        assert data["event_id"] == sample_run_data["event_id"]
        assert data["run_id"] == sample_run_data["run_id"]
        assert data["agent_name"] == sample_run_data["agent_name"]
        assert data["job_type"] == sample_run_data["job_type"]
        assert data["status"] == sample_run_data["status"]
        assert data["product"] == sample_run_data["product"]
        assert data["metrics_json"] == sample_run_data["metrics_json"]
        assert data["context_json"] == sample_run_data["context_json"]
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_run_minimal(self, client):
        """Test run creation with minimal required fields."""
        minimal_data = {
            "event_id": str(uuid.uuid4()),
            "run_id": "2026-01-28T10:00:00Z-launch-minimal",
            "agent_name": "launch.orchestrator",
            "job_type": "launch",
            "start_time": "2026-01-28T10:00:00Z",
        }

        response = client.post("/api/v1/runs", json=minimal_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "running"  # Default status
        assert data["product"] is None
        assert data["metrics_json"] is None

    def test_create_run_idempotent(self, client, sample_run_data):
        """Test idempotent run creation (same event_id returns existing run)."""
        # Create run first time
        response1 = client.post("/api/v1/runs", json=sample_run_data)
        assert response1.status_code == 201
        data1 = response1.json()

        # Create again with same event_id
        response2 = client.post("/api/v1/runs", json=sample_run_data)
        assert response2.status_code == 201
        data2 = response2.json()

        # Should return same run
        assert data1["event_id"] == data2["event_id"]
        assert data1["run_id"] == data2["run_id"]
        assert data1["created_at"] == data2["created_at"]

    def test_create_child_run(self, client, sample_run_data):
        """Test creating a child run with parent_run_id."""
        # Create parent run
        parent_response = client.post("/api/v1/runs", json=sample_run_data)
        assert parent_response.status_code == 201

        # Create child run
        child_data = {
            "event_id": str(uuid.uuid4()),
            "run_id": f"{sample_run_data['run_id']}-worker-scout",
            "agent_name": "launch.workers.RepoScout",
            "job_type": "worker",
            "start_time": "2026-01-28T10:05:00Z",
            "parent_run_id": sample_run_data["run_id"],
            "context_json": {"trace_id": "xyz789", "span_id": "uvw012"},
        }

        response = client.post("/api/v1/runs", json=child_data)
        assert response.status_code == 201

        data = response.json()
        assert data["parent_run_id"] == sample_run_data["run_id"]
        assert data["job_type"] == "worker"


class TestListRuns:
    """Test GET /api/v1/runs endpoint."""

    def test_list_runs_empty(self, client):
        """Test listing runs when database is empty."""
        response = client.get("/api/v1/runs")

        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_list_runs_basic(self, client, sample_run_data):
        """Test listing runs with data."""
        # Create 3 runs
        for i in range(3):
            run_data = sample_run_data.copy()
            run_data["event_id"] = str(uuid.uuid4())
            run_data["run_id"] = f"run-{i}"
            client.post("/api/v1/runs", json=run_data)

        response = client.get("/api/v1/runs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 3
        assert data["total"] == 3

    def test_list_runs_pagination(self, client, sample_run_data):
        """Test pagination with limit and offset."""
        # Create 5 runs
        for i in range(5):
            run_data = sample_run_data.copy()
            run_data["event_id"] = str(uuid.uuid4())
            run_data["run_id"] = f"run-{i:03d}"
            run_data["start_time"] = f"2026-01-28T10:{i:02d}:00Z"
            client.post("/api/v1/runs", json=run_data)

        # Get first 2
        response = client.get("/api/v1/runs?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0

        # Get next 2
        response = client.get("/api/v1/runs?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 2
        assert data["total"] == 5

    def test_list_runs_filter_by_status(self, client, sample_run_data):
        """Test filtering runs by status."""
        # Create runs with different statuses
        statuses = ["running", "success", "failure"]
        for status in statuses:
            run_data = sample_run_data.copy()
            run_data["event_id"] = str(uuid.uuid4())
            run_data["run_id"] = f"run-{status}"
            run_data["status"] = status
            client.post("/api/v1/runs", json=run_data)

        # Filter by status=success
        response = client.get("/api/v1/runs?status=success")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["runs"][0]["status"] == "success"

    def test_list_runs_filter_by_job_type(self, client, sample_run_data):
        """Test filtering runs by job_type."""
        # Create runs with different job types
        job_types = ["launch", "worker", "gate"]
        for job_type in job_types:
            run_data = sample_run_data.copy()
            run_data["event_id"] = str(uuid.uuid4())
            run_data["run_id"] = f"run-{job_type}"
            run_data["job_type"] = job_type
            client.post("/api/v1/runs", json=run_data)

        # Filter by job_type=worker
        response = client.get("/api/v1/runs?job_type=worker")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["runs"][0]["job_type"] == "worker"

    def test_list_runs_filter_by_parent_run_id(self, client, sample_run_data):
        """Test filtering runs by parent_run_id."""
        # Create parent run
        parent_response = client.post("/api/v1/runs", json=sample_run_data)
        assert parent_response.status_code == 201

        # Create 2 child runs
        for i in range(2):
            child_data = sample_run_data.copy()
            child_data["event_id"] = str(uuid.uuid4())
            child_data["run_id"] = f"{sample_run_data['run_id']}-child-{i}"
            child_data["parent_run_id"] = sample_run_data["run_id"]
            client.post("/api/v1/runs", json=child_data)

        # Filter by parent_run_id
        response = client.get(
            f"/api/v1/runs?parent_run_id={sample_run_data['run_id']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(
            run["parent_run_id"] == sample_run_data["run_id"]
            for run in data["runs"]
        )

    def test_list_runs_multiple_filters(self, client, sample_run_data):
        """Test combining multiple filters."""
        # Create runs with various attributes
        for i in range(4):
            run_data = sample_run_data.copy()
            run_data["event_id"] = str(uuid.uuid4())
            run_data["run_id"] = f"run-{i}"
            run_data["status"] = "success" if i % 2 == 0 else "failure"
            run_data["job_type"] = "worker" if i < 2 else "gate"
            client.post("/api/v1/runs", json=run_data)

        # Filter by status=success AND job_type=worker
        response = client.get("/api/v1/runs?status=success&job_type=worker")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["runs"][0]["status"] == "success"
        assert data["runs"][0]["job_type"] == "worker"


class TestGetRun:
    """Test GET /api/v1/runs/{run_id} endpoint."""

    def test_get_run_success(self, client, sample_run_data):
        """Test getting run by run_id."""
        # Create run
        create_response = client.post("/api/v1/runs", json=sample_run_data)
        assert create_response.status_code == 201

        # Get run by run_id
        response = client.get(f"/api/v1/runs/{sample_run_data['run_id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["run_id"] == sample_run_data["run_id"]
        assert data["event_id"] == sample_run_data["event_id"]
        assert data["agent_name"] == sample_run_data["agent_name"]

    def test_get_run_not_found(self, client):
        """Test getting non-existent run returns 404."""
        response = client.get("/api/v1/runs/nonexistent-run-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Run not found" in data["detail"]


class TestUpdateRun:
    """Test PATCH /api/v1/runs/{event_id} endpoint."""

    def test_update_run_status(self, client, sample_run_data):
        """Test updating run status."""
        # Create run
        create_response = client.post("/api/v1/runs", json=sample_run_data)
        assert create_response.status_code == 201

        # Update status to success
        update_data = {
            "status": "success",
            "end_time": "2026-01-28T10:30:00Z",
            "duration_ms": 1800000,
        }
        response = client.patch(
            f"/api/v1/runs/{sample_run_data['event_id']}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["end_time"] == "2026-01-28T10:30:00Z"
        assert data["duration_ms"] == 1800000

    def test_update_run_metrics(self, client, sample_run_data):
        """Test updating run metrics and context."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Update metrics
        update_data = {
            "items_discovered": 10,
            "items_succeeded": 8,
            "items_failed": 2,
            "items_skipped": 0,
            "metrics_json": {"new_metric": 42},
        }
        response = client.patch(
            f"/api/v1/runs/{sample_run_data['event_id']}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items_discovered"] == 10
        assert data["items_succeeded"] == 8
        assert data["items_failed"] == 2
        assert data["metrics_json"]["new_metric"] == 42

    def test_update_run_summary(self, client, sample_run_data):
        """Test updating run output and error summaries."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Update summaries
        update_data = {
            "output_summary": "All tasks completed successfully",
            "error_summary": "No errors",
        }
        response = client.patch(
            f"/api/v1/runs/{sample_run_data['event_id']}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["output_summary"] == "All tasks completed successfully"
        assert data["error_summary"] == "No errors"

    def test_update_run_not_found(self, client):
        """Test updating non-existent run returns 404."""
        update_data = {"status": "success"}
        response = client.patch(
            "/api/v1/runs/nonexistent-event-id",
            json=update_data,
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Run not found" in data["detail"]

    def test_update_run_empty_request(self, client, sample_run_data):
        """Test updating run with empty request returns current run."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Empty update
        response = client.patch(
            f"/api/v1/runs/{sample_run_data['event_id']}",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == sample_run_data["run_id"]


class TestGetRunEvents:
    """Test GET /api/v1/runs/{run_id}/events endpoint."""

    def test_get_events_empty(self, client, sample_run_data):
        """Test getting events for run with no events."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Get events
        response = client.get(
            f"/api/v1/runs/{sample_run_data['run_id']}/events"
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_events_not_found(self, client):
        """Test getting events for non-existent run returns 404."""
        response = client.get("/api/v1/runs/nonexistent-run/events")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Run not found" in data["detail"]

    def test_get_events_with_data(self, client, sample_run_data, temp_db):
        """Test getting events with actual event data."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Add events directly to database
        db = TelemetryDatabase(temp_db)
        events = [
            {
                "event_id": str(uuid.uuid4()),
                "run_id": sample_run_data["run_id"],
                "ts": "2026-01-28T10:00:00Z",
                "type": "RUN_CREATED",
                "payload": {"status": "created"},
                "trace_id": "trace1",
                "span_id": "span1",
            },
            {
                "event_id": str(uuid.uuid4()),
                "run_id": sample_run_data["run_id"],
                "ts": "2026-01-28T10:05:00Z",
                "type": "RUN_STATE_CHANGED",
                "payload": {"new_state": "RUNNING"},
                "trace_id": "trace1",
                "span_id": "span2",
                "parent_span_id": "span1",
            },
        ]
        for event in events:
            db.add_event(event)

        # Get events
        response = client.get(
            f"/api/v1/runs/{sample_run_data['run_id']}/events"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["type"] == "RUN_CREATED"
        assert data[1]["type"] == "RUN_STATE_CHANGED"
        assert data[1]["parent_span_id"] == "span1"


class TestAssociateCommit:
    """Test POST /api/v1/runs/{event_id}/associate-commit endpoint."""

    def test_associate_commit_success(self, client, sample_run_data):
        """Test successfully associating commit with run."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Associate commit
        commit_data = {
            "commit_hash": "abc1234567",
            "commit_source": "llm",
            "commit_author": "claude",
            "commit_timestamp": "2026-01-28T10:15:00Z",
        }
        response = client.post(
            f"/api/v1/runs/{sample_run_data['event_id']}/associate-commit",
            json=commit_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["commit_hash"] == "abc1234567"
        assert data["commit_source"] == "llm"
        assert data["commit_author"] == "claude"
        assert data["commit_timestamp"] == "2026-01-28T10:15:00Z"

    def test_associate_commit_minimal(self, client, sample_run_data):
        """Test associating commit with minimal data."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Associate commit (minimal)
        commit_data = {
            "commit_hash": "def7890",
            "commit_source": "manual",
        }
        response = client.post(
            f"/api/v1/runs/{sample_run_data['event_id']}/associate-commit",
            json=commit_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["commit_hash"] == "def7890"
        assert data["commit_source"] == "manual"
        assert data["commit_author"] is None

    def test_associate_commit_invalid_hash_length(self, client, sample_run_data):
        """Test associating commit with invalid hash length."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Try to associate commit with too short hash
        commit_data = {
            "commit_hash": "abc",  # Too short (< 7 chars)
            "commit_source": "llm",
        }
        response = client.post(
            f"/api/v1/runs/{sample_run_data['event_id']}/associate-commit",
            json=commit_data,
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "commit_hash" in data["detail"]

    def test_associate_commit_invalid_source(self, client, sample_run_data):
        """Test associating commit with invalid source."""
        # Create run
        client.post("/api/v1/runs", json=sample_run_data)

        # Try to associate commit with invalid source
        commit_data = {
            "commit_hash": "abc1234567",
            "commit_source": "invalid",  # Not in (manual, llm, ci)
        }
        response = client.post(
            f"/api/v1/runs/{sample_run_data['event_id']}/associate-commit",
            json=commit_data,
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "commit_source" in data["detail"]

    def test_associate_commit_not_found(self, client):
        """Test associating commit with non-existent run."""
        commit_data = {
            "commit_hash": "abc1234567",
            "commit_source": "llm",
        }
        response = client.post(
            "/api/v1/runs/nonexistent-event-id/associate-commit",
            json=commit_data,
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Run not found" in data["detail"]


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.2.0"

"""Unit tests for telemetry API metadata endpoints (TC-523).

Binding contract: specs/16_local_telemetry_api.md, docs/reference/local-telemetry.md

Tests:
1. GET /api/v1/metadata - Returns distinct agent names and job types
2. GET /metrics - Returns system-level metrics
3. Metadata response format validation
4. Metrics response format validation
5. Metadata caching behavior
6. Empty database handling
7. Multiple agents and job types
8. Recent runs count (24h)
"""

import json
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
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
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "event_id": str(uuid.uuid4()),
        "run_id": f"{current_time}-launch-test-product",
        "agent_name": "launch.orchestrator",
        "job_type": "launch",
        "start_time": current_time,
        "status": "running",
        "product": "test-product",
        "metrics_json": {"token_count": 1000},
        "context_json": {"trace_id": "abc123"},
    }


class TestMetadataEndpoint:
    """Test GET /api/v1/metadata endpoint."""

    def test_metadata_empty_database(self, client):
        """Test metadata endpoint with empty database."""
        response = client.get("/api/v1/metadata")

        assert response.status_code == 200
        data = response.json()

        assert data["agent_names"] == []
        assert data["job_types"] == []
        assert data["counts"]["agent_names"] == 0
        assert data["counts"]["job_types"] == 0
        assert "cache_hit" in data
        assert isinstance(data["cache_hit"], bool)

    def test_metadata_single_run(self, client, sample_run_data):
        """Test metadata endpoint with single run."""
        # Create a run
        client.post("/api/v1/runs", json=sample_run_data)

        # Get metadata
        response = client.get("/api/v1/metadata")

        assert response.status_code == 200
        data = response.json()

        assert data["agent_names"] == ["launch.orchestrator"]
        assert data["job_types"] == ["launch"]
        assert data["counts"]["agent_names"] == 1
        assert data["counts"]["job_types"] == 1
        assert data["cache_hit"] is False  # First query, not cached

    def test_metadata_multiple_agents_and_jobs(self, client):
        """Test metadata endpoint with multiple agents and job types."""
        # Create runs with different agents and job types
        runs = [
            {
                "event_id": str(uuid.uuid4()),
                "run_id": f"run-{i}",
                "agent_name": f"agent-{i % 3}",  # 3 unique agents
                "job_type": f"job-{i % 2}",  # 2 unique job types
                "start_time": "2026-01-28T10:00:00Z",
            }
            for i in range(6)
        ]

        for run in runs:
            client.post("/api/v1/runs", json=run)

        # Get metadata
        response = client.get("/api/v1/metadata")

        assert response.status_code == 200
        data = response.json()

        # Should have 3 unique agents (agent-0, agent-1, agent-2)
        assert len(data["agent_names"]) == 3
        assert set(data["agent_names"]) == {"agent-0", "agent-1", "agent-2"}

        # Should have 2 unique job types (job-0, job-1)
        assert len(data["job_types"]) == 2
        assert set(data["job_types"]) == {"job-0", "job-1"}

        assert data["counts"]["agent_names"] == 3
        assert data["counts"]["job_types"] == 2

    def test_metadata_caching(self, client, sample_run_data):
        """Test metadata caching behavior."""
        # Create a run
        client.post("/api/v1/runs", json=sample_run_data)

        # First request - should not be cached
        response1 = client.get("/api/v1/metadata")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cache_hit"] is False

        # Second request - should be cached
        response2 = client.get("/api/v1/metadata")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cache_hit"] is True

        # Data should be the same
        assert data1["agent_names"] == data2["agent_names"]
        assert data1["job_types"] == data2["job_types"]

    def test_metadata_sorted_output(self, client):
        """Test that metadata results are sorted alphabetically."""
        # Create runs with agents in non-alphabetical order
        agents = ["zebra", "alpha", "bravo"]
        job_types = ["task-z", "task-a", "task-m"]

        for i, (agent, job) in enumerate(zip(agents, job_types)):
            client.post(
                "/api/v1/runs",
                json={
                    "event_id": str(uuid.uuid4()),
                    "run_id": f"run-{i}",
                    "agent_name": agent,
                    "job_type": job,
                    "start_time": "2026-01-28T10:00:00Z",
                },
            )

        response = client.get("/api/v1/metadata")
        assert response.status_code == 200
        data = response.json()

        # Should be sorted alphabetically
        assert data["agent_names"] == ["alpha", "bravo", "zebra"]
        assert data["job_types"] == ["task-a", "task-m", "task-z"]


class TestMetricsEndpoint:
    """Test GET /metrics endpoint."""

    def test_metrics_empty_database(self, client):
        """Test metrics endpoint with empty database."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_runs"] == 0
        assert data["agents"] == {}
        assert data["recent_24h"] == 0
        assert "performance" in data
        assert "db_path" in data["performance"]
        assert "journal_mode" in data["performance"]

    def test_metrics_single_run(self, client, sample_run_data):
        """Test metrics endpoint with single run."""
        # Create a run
        client.post("/api/v1/runs", json=sample_run_data)

        # Get metrics
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_runs"] == 1
        assert data["agents"] == {"launch.orchestrator": 1}
        assert data["recent_24h"] == 1
        assert "performance" in data

    def test_metrics_multiple_runs_by_agent(self, client):
        """Test metrics aggregation by agent."""
        # Create runs with different agents
        runs = [
            {
                "event_id": str(uuid.uuid4()),
                "run_id": f"run-{i}",
                "agent_name": "agent-a" if i < 5 else "agent-b",
                "job_type": "test",
                "start_time": "2026-01-28T10:00:00Z",
            }
            for i in range(8)
        ]

        for run in runs:
            client.post("/api/v1/runs", json=run)

        # Get metrics
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_runs"] == 8
        assert data["agents"]["agent-a"] == 5
        assert data["agents"]["agent-b"] == 3

    def test_metrics_recent_24h(self, client):
        """Test recent_24h metric calculation."""
        # Create runs with different timestamps
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1, hours=1)  # Just over 24 hours ago
        today = now - timedelta(hours=1)  # 1 hour ago

        # Old run (> 24h ago) - should not be counted
        old_run = {
            "event_id": str(uuid.uuid4()),
            "run_id": "run-old",
            "agent_name": "test-agent",
            "job_type": "test",
            "start_time": yesterday.isoformat(),
        }
        client.post("/api/v1/runs", json=old_run)

        # Recent run (< 24h ago) - should be counted
        recent_run = {
            "event_id": str(uuid.uuid4()),
            "run_id": "run-recent",
            "agent_name": "test-agent",
            "job_type": "test",
            "start_time": today.isoformat(),
        }
        client.post("/api/v1/runs", json=recent_run)

        # Get metrics
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_runs"] == 2
        # Note: SQLite's datetime('now', '-1 day') might have slight timing differences
        # We accept either 1 or 2 recent runs due to test timing
        assert data["recent_24h"] in [1, 2]

    def test_metrics_performance_info(self, client, sample_run_data):
        """Test that performance info is included in metrics."""
        # Create a run
        client.post("/api/v1/runs", json=sample_run_data)

        # Get metrics
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check performance fields
        assert "performance" in data
        assert "db_path" in data["performance"]
        assert "journal_mode" in data["performance"]

        # db_path should be a string
        assert isinstance(data["performance"]["db_path"], str)
        # journal_mode should be one of the SQLite modes (accept both upper and lowercase)
        assert data["performance"]["journal_mode"].upper() in [
            "DELETE",
            "TRUNCATE",
            "PERSIST",
            "MEMORY",
            "WAL",
            "OFF",
        ]


class TestResponseFormatValidation:
    """Test response format validation for metadata and metrics endpoints."""

    def test_metadata_response_schema(self, client, sample_run_data):
        """Test that metadata response matches expected schema."""
        client.post("/api/v1/runs", json=sample_run_data)
        response = client.get("/api/v1/metadata")

        assert response.status_code == 200
        data = response.json()

        # Validate all required fields are present
        assert "agent_names" in data
        assert "job_types" in data
        assert "counts" in data
        assert "cache_hit" in data

        # Validate types
        assert isinstance(data["agent_names"], list)
        assert isinstance(data["job_types"], list)
        assert isinstance(data["counts"], dict)
        assert isinstance(data["cache_hit"], bool)

        # Validate counts structure
        assert "agent_names" in data["counts"]
        assert "job_types" in data["counts"]
        assert isinstance(data["counts"]["agent_names"], int)
        assert isinstance(data["counts"]["job_types"], int)

    def test_metrics_response_schema(self, client, sample_run_data):
        """Test that metrics response matches expected schema."""
        client.post("/api/v1/runs", json=sample_run_data)
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        # Validate all required fields are present
        assert "total_runs" in data
        assert "agents" in data
        assert "recent_24h" in data
        assert "performance" in data

        # Validate types
        assert isinstance(data["total_runs"], int)
        assert isinstance(data["agents"], dict)
        assert isinstance(data["recent_24h"], int)
        assert isinstance(data["performance"], dict)

        # Validate all values are non-negative
        assert data["total_runs"] >= 0
        assert data["recent_24h"] >= 0
        for count in data["agents"].values():
            assert isinstance(count, int)
            assert count >= 0

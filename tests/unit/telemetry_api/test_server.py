"""Tests for telemetry API server endpoints (TC-3796)."""

import pytest
import uuid

# Skip entire module if fastapi or httpx not available
fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from launcher.telemetry_api.server import create_app, ServerConfig, _API_VERSION
from launcher.telemetry_api.routes.database import TelemetryDatabase


@pytest.fixture()
def client(tmp_path):
    """Create test client with temporary database."""
    config = ServerConfig(db_path=str(tmp_path / "test_telemetry.db"))
    app = create_app(config)
    return TestClient(app)


def _make_run_payload(**overrides):
    """Create a valid run payload with optional overrides."""
    data = {
        "event_id": str(uuid.uuid4()),
        "run_id": f"run-{uuid.uuid4().hex[:8]}",
        "agent_name": "launcher.orchestrator",
        "job_type": "launch",
        "start_time": "2026-03-07T10:00:00Z",
        "status": "running",
    }
    data.update(overrides)
    return data


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_contains_status_ok(self, client):
        resp = client.get("/health")
        body = resp.json()
        assert body["status"] == "ok"

    def test_health_contains_version(self, client):
        resp = client.get("/health")
        body = resp.json()
        assert body["version"] == _API_VERSION


class TestRunsCRUD:
    """Tests for /api/v1/runs endpoints."""

    def test_create_run(self, client):
        payload = _make_run_payload()
        resp = client.post("/api/v1/runs", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["event_id"] == payload["event_id"]
        assert body["run_id"] == payload["run_id"]
        assert body["status"] == "running"

    def test_create_run_idempotent(self, client):
        payload = _make_run_payload()
        resp1 = client.post("/api/v1/runs", json=payload)
        resp2 = client.post("/api/v1/runs", json=payload)
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["event_id"] == resp2.json()["event_id"]

    def test_list_runs_empty(self, client):
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["runs"] == []
        assert body["total"] == 0

    def test_list_runs_after_create(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["runs"][0]["run_id"] == payload["run_id"]

    def test_get_run_by_id(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.get(f"/api/v1/runs/{payload['run_id']}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == payload["run_id"]

    def test_get_run_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent")
        assert resp.status_code == 404

    def test_update_run(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.patch(
            f"/api/v1/runs/{payload['event_id']}",
            json={"status": "success", "duration_ms": 1234},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["duration_ms"] == 1234

    def test_update_run_not_found(self, client):
        resp = client.patch(
            "/api/v1/runs/nonexistent",
            json={"status": "success"},
        )
        assert resp.status_code == 404


class TestRunEvents:
    """Tests for /api/v1/runs/{run_id}/events."""

    def test_get_events_empty(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.get(f"/api/v1/runs/{payload['run_id']}/events")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_events_run_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent/events")
        assert resp.status_code == 404


class TestAssociateCommit:
    """Tests for POST /api/v1/runs/{event_id}/associate-commit."""

    def test_associate_commit(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.post(
            f"/api/v1/runs/{payload['event_id']}/associate-commit",
            json={
                "commit_hash": "abc1234",
                "commit_source": "manual",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["commit_hash"] == "abc1234"
        assert body["commit_source"] == "manual"

    def test_associate_commit_invalid_hash(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.post(
            f"/api/v1/runs/{payload['event_id']}/associate-commit",
            json={
                "commit_hash": "abc",
                "commit_source": "manual",
            },
        )
        assert resp.status_code == 400

    def test_associate_commit_invalid_source(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.post(
            f"/api/v1/runs/{payload['event_id']}/associate-commit",
            json={
                "commit_hash": "abc1234",
                "commit_source": "invalid",
            },
        )
        assert resp.status_code == 400


class TestBatchEndpoints:
    """Tests for batch upload endpoints."""

    def test_batch_upload(self, client):
        runs = [_make_run_payload() for _ in range(3)]
        resp = client.post("/api/v1/runs/batch", json={"runs": runs})
        assert resp.status_code == 201
        body = resp.json()
        assert body["total"] == 3
        assert body["created"] == 3
        assert body["failed"] == 0

    def test_batch_upload_idempotent(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.post("/api/v1/runs/batch", json={"runs": [payload]})
        assert resp.status_code == 201
        body = resp.json()
        assert body["existing"] == 1
        assert body["created"] == 0


class TestMetadataEndpoints:
    """Tests for metadata and metrics endpoints."""

    def test_metadata_empty(self, client):
        resp = client.get("/api/v1/metadata")
        assert resp.status_code == 200
        body = resp.json()
        assert body["agent_names"] == []
        assert body["job_types"] == []

    def test_metadata_after_runs(self, client):
        client.post("/api/v1/runs", json=_make_run_payload(agent_name="test-agent"))
        resp = client.get("/api/v1/metadata")
        assert resp.status_code == 200
        body = resp.json()
        assert "test-agent" in body["agent_names"]

    def test_metrics(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_runs"] == 0

    def test_metrics_after_runs(self, client):
        client.post("/api/v1/runs", json=_make_run_payload())
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert resp.json()["total_runs"] == 1


class TestSQLFieldAllowlist:
    """Tests for TM-02: SQL field allowlist in update_run."""

    def test_update_with_unknown_field_ignored(self, client):
        """Unknown fields in PATCH should be silently skipped, not injected into SQL."""
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.patch(
            f"/api/v1/runs/{payload['event_id']}",
            json={"status": "success", "evil_field": "drop table"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_update_only_known_fields_applied(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.patch(
            f"/api/v1/runs/{payload['event_id']}",
            json={"duration_ms": 500, "output_summary": "done"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["duration_ms"] == 500
        assert body["output_summary"] == "done"


class TestBatchTransactional:
    """Tests for batch-transactional endpoint (TM-02/TM-03)."""

    def test_batch_transactional_create(self, client):
        runs = [_make_run_payload() for _ in range(3)]
        resp = client.post("/api/v1/runs/batch-transactional", json={"runs": runs})
        assert resp.status_code == 201
        body = resp.json()
        assert body["total"] == 3
        assert body["created"] == 3
        assert body["failed"] == 0

    def test_batch_transactional_idempotent(self, client):
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        resp = client.post("/api/v1/runs/batch-transactional", json={"runs": [payload]})
        assert resp.status_code == 201
        body = resp.json()
        assert body["existing"] == 1
        assert body["created"] == 0


class TestVersionAlignment:
    """Tests for TM-01: version sourced from ENGINE_VERSION."""

    def test_openapi_version_matches(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert resp.json()["info"]["version"] == _API_VERSION

    def test_api_version_is_engine_version(self):
        from launcher.provenance import ENGINE_VERSION
        assert _API_VERSION == ENGINE_VERSION


@pytest.fixture()
def client_db(tmp_path):
    """Create test client with direct database access for event roundtrip tests."""
    db_path = tmp_path / "test_telemetry.db"
    config = ServerConfig(db_path=str(db_path))
    app = create_app(config)
    db = TelemetryDatabase(db_path)
    return TestClient(app), db


class TestListRunsFilters:
    """Tests for GET /api/v1/runs filter params (G-TM-07)."""

    def test_filter_by_status(self, client):
        """Filter by status returns only matching runs."""
        client.post("/api/v1/runs", json=_make_run_payload(status="running"))
        client.post("/api/v1/runs", json=_make_run_payload(status="success"))
        resp = client.get("/api/v1/runs?status=running")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert all(r["status"] == "running" for r in body["runs"])

    def test_filter_by_job_type(self, client):
        """Filter by job_type returns only matching runs."""
        client.post("/api/v1/runs", json=_make_run_payload(job_type="launch"))
        client.post("/api/v1/runs", json=_make_run_payload(job_type="heal"))
        resp = client.get("/api/v1/runs?job_type=heal")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["runs"][0]["job_type"] == "heal"

    def test_filter_by_product(self, client):
        """Filter by product returns only matching runs."""
        client.post("/api/v1/runs", json=_make_run_payload(product="aspose.cells"))
        client.post("/api/v1/runs", json=_make_run_payload(product="aspose.words"))
        resp = client.get("/api/v1/runs?product=aspose.cells")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["runs"][0]["product"] == "aspose.cells"

    def test_filter_by_parent_run_id(self, client):
        """Filter by parent_run_id returns only child runs."""
        parent_id = "parent-run-001"
        client.post("/api/v1/runs", json=_make_run_payload(parent_run_id=parent_id))
        client.post("/api/v1/runs", json=_make_run_payload())
        resp = client.get(f"/api/v1/runs?parent_run_id={parent_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["runs"][0]["parent_run_id"] == parent_id

    def test_combined_filters_status_and_job_type(self, client):
        """Combined status + job_type filters apply as AND logic."""
        client.post("/api/v1/runs", json=_make_run_payload(status="running", job_type="launch"))
        client.post("/api/v1/runs", json=_make_run_payload(status="success", job_type="launch"))
        client.post("/api/v1/runs", json=_make_run_payload(status="running", job_type="heal"))
        resp = client.get("/api/v1/runs?status=running&job_type=launch")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["runs"][0]["status"] == "running"
        assert body["runs"][0]["job_type"] == "launch"


class TestPagination:
    """Tests for limit/offset pagination (G-TM-08)."""

    def test_limit_one_returns_one_result(self, client):
        """limit=1 returns exactly one run while total reflects all runs."""
        for _ in range(3):
            client.post("/api/v1/runs", json=_make_run_payload())
        resp = client.get("/api/v1/runs?limit=1&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["runs"]) == 1
        assert body["total"] == 3

    def test_offset_skips_results_total_unchanged(self, client):
        """offset skips leading results but total always reflects the full filtered count."""
        for _ in range(3):
            client.post("/api/v1/runs", json=_make_run_payload())
        resp = client.get("/api/v1/runs?limit=2&offset=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["runs"]) == 1
        assert body["total"] == 3


class TestEventRoundtrip:
    """Tests for event storage and retrieval roundtrip (G-TM-09)."""

    def test_event_storage_and_retrieval(self, client_db):
        """Events inserted via database.add_event() are returned by GET /runs/{run_id}/events."""
        client, db = client_db
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        run_id = payload["run_id"]

        db.add_event({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "ts": "2026-03-07T10:01:00Z",
            "type": "worker_started",
            "payload": {"worker": "generate"},
        })

        resp = client.get(f"/api/v1/runs/{run_id}/events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 1
        assert events[0]["type"] == "worker_started"
        assert events[0]["payload"]["worker"] == "generate"

    def test_events_ordered_by_timestamp(self, client_db):
        """Events are returned in ascending timestamp order."""
        client, db = client_db
        payload = _make_run_payload()
        client.post("/api/v1/runs", json=payload)
        run_id = payload["run_id"]

        db.add_event({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "ts": "2026-03-07T10:02:00Z",
            "type": "step_two",
            "payload": {},
        })
        db.add_event({
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "ts": "2026-03-07T10:01:00Z",
            "type": "step_one",
            "payload": {},
        })

        resp = client.get(f"/api/v1/runs/{run_id}/events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) == 2
        assert events[0]["type"] == "step_one"
        assert events[1]["type"] == "step_two"


class TestMetadataCache:
    """Tests for metadata cache miss/hit/invalidation behavior (G-TM-10)."""

    def test_cache_miss_then_hit(self, client):
        """First request is a cache miss; second request is a cache hit."""
        from launcher.telemetry_api.routes import metadata as metadata_mod
        metadata_mod.invalidate_metadata_cache()

        resp1 = client.get("/api/v1/metadata")
        assert resp1.status_code == 200
        assert resp1.json()["cache_hit"] is False

        resp2 = client.get("/api/v1/metadata")
        assert resp2.status_code == 200
        assert resp2.json()["cache_hit"] is True

    def test_cache_invalidated_on_run_create(self, client):
        """Creating a run via POST invalidates the metadata cache."""
        from launcher.telemetry_api.routes import metadata as metadata_mod
        metadata_mod.invalidate_metadata_cache()

        client.get("/api/v1/metadata")
        assert client.get("/api/v1/metadata").json()["cache_hit"] is True

        client.post("/api/v1/runs", json=_make_run_payload())
        resp = client.get("/api/v1/metadata")
        assert resp.json()["cache_hit"] is False

    def test_cache_reflects_new_data_after_invalidation(self, client):
        """After cache invalidation, metadata reflects the newly created run's agent_name."""
        from launcher.telemetry_api.routes import metadata as metadata_mod
        metadata_mod.invalidate_metadata_cache()

        resp1 = client.get("/api/v1/metadata")
        assert "unique-agent-xyz" not in resp1.json()["agent_names"]

        client.post("/api/v1/runs", json=_make_run_payload(agent_name="unique-agent-xyz"))

        resp2 = client.get("/api/v1/metadata")
        assert "unique-agent-xyz" in resp2.json()["agent_names"]


class TestNegativeInputs:
    """Tests for validation of malformed or incomplete requests (G-TM-11)."""

    def test_missing_event_id_returns_422(self, client):
        """POST /api/v1/runs without event_id returns 422."""
        payload = _make_run_payload()
        del payload["event_id"]
        resp = client.post("/api/v1/runs", json=payload)
        assert resp.status_code == 422

    def test_missing_run_id_returns_422(self, client):
        """POST /api/v1/runs without run_id returns 422."""
        payload = _make_run_payload()
        del payload["run_id"]
        resp = client.post("/api/v1/runs", json=payload)
        assert resp.status_code == 422

    def test_missing_agent_name_returns_422(self, client):
        """POST /api/v1/runs without agent_name returns 422."""
        payload = _make_run_payload()
        del payload["agent_name"]
        resp = client.post("/api/v1/runs", json=payload)
        assert resp.status_code == 422

    def test_invalid_json_body_returns_422(self, client):
        """POST /api/v1/runs with invalid JSON body returns 422."""
        resp = client.post(
            "/api/v1/runs",
            content=b"not valid json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422


class TestServerConfig:
    """Tests for get_server_config_from_env() (G-TM-12)."""

    def test_config_from_env_custom_values(self, monkeypatch):
        """Custom env vars are reflected in the returned ServerConfig."""
        from launcher.telemetry_api.server import get_server_config_from_env
        monkeypatch.setenv("TELEMETRY_API_HOST", "0.0.0.0")
        monkeypatch.setenv("TELEMETRY_API_PORT", "9000")
        monkeypatch.setenv("TELEMETRY_LOG_LEVEL", "debug")
        monkeypatch.setenv("TELEMETRY_DB_PATH", "/tmp/custom.db")

        config = get_server_config_from_env()
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.log_level == "debug"
        assert config.db_path == "/tmp/custom.db"

    def test_config_from_env_defaults(self, monkeypatch):
        """Default values are used when env vars are absent."""
        from launcher.telemetry_api.server import get_server_config_from_env
        monkeypatch.delenv("TELEMETRY_API_HOST", raising=False)
        monkeypatch.delenv("TELEMETRY_API_PORT", raising=False)
        monkeypatch.delenv("TELEMETRY_LOG_LEVEL", raising=False)
        monkeypatch.delenv("TELEMETRY_DB_PATH", raising=False)

        config = get_server_config_from_env()
        assert config.host == "127.0.0.1"
        assert config.port == 8765
        assert config.log_level == "info"
        assert config.db_path == "./telemetry.db"

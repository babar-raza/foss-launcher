"""Tests for ArtifactStore (TC-1032).

Validates:
- load_artifact: happy path, file not found, invalid JSON
- load_artifact_or_default: exists, does not exist
- write_artifact: writes valid JSON, returns entry with sha256
- emit_event: appends to events.ndjson
- artifact_path: correct path construction
- exists: true/false cases
- Deterministic output: same input produces identical JSON bytes
- Schema validation integration (optional)

Spec references:
- specs/10_determinism_and_caching.md (Deterministic output)
- specs/11_state_and_events.md (Event log format)
- specs/21_worker_contracts.md (Artifact contracts)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.io.artifact_store import ArtifactStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """Create a minimal run directory structure."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    return tmp_path


@pytest.fixture
def store(run_dir: Path) -> ArtifactStore:
    """Create an ArtifactStore with a temporary run directory."""
    return ArtifactStore(run_dir=run_dir)


@pytest.fixture
def sample_artifact_data() -> dict:
    """Sample artifact data for testing."""
    return {
        "schema_version": "1.0",
        "items": [
            {"id": "item_001", "name": "Alpha"},
            {"id": "item_002", "name": "Beta"},
        ],
        "metadata": {
            "count": 2,
            "generated_by": "test",
        },
    }


# ---------------------------------------------------------------------------
# artifact_path
# ---------------------------------------------------------------------------

class TestArtifactPath:
    """Tests for artifact_path() method."""

    def test_returns_path_under_artifacts_dir(self, store: ArtifactStore, run_dir: Path) -> None:
        """artifact_path returns run_dir/artifacts/<name>."""
        result = store.artifact_path("repo_inventory.json")
        assert result == run_dir / "artifacts" / "repo_inventory.json"

    def test_different_names_produce_different_paths(self, store: ArtifactStore) -> None:
        """Different artifact names produce different paths."""
        path_a = store.artifact_path("product_facts.json")
        path_b = store.artifact_path("page_plan.json")
        assert path_a != path_b


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------

class TestExists:
    """Tests for exists() method."""

    def test_false_when_missing(self, store: ArtifactStore) -> None:
        """exists() returns False for non-existent artifacts."""
        assert store.exists("nonexistent.json") is False

    def test_true_when_present(self, store: ArtifactStore, run_dir: Path) -> None:
        """exists() returns True when artifact file is on disk."""
        artifact_path = run_dir / "artifacts" / "test.json"
        artifact_path.write_text("{}", encoding="utf-8")
        assert store.exists("test.json") is True

    def test_false_for_directory(self, store: ArtifactStore, run_dir: Path) -> None:
        """exists() returns False if name matches a directory, not a file."""
        (run_dir / "artifacts" / "subdir").mkdir()
        assert store.exists("subdir") is False


# ---------------------------------------------------------------------------
# load_artifact
# ---------------------------------------------------------------------------

class TestLoadArtifact:
    """Tests for load_artifact() method."""

    def test_happy_path(
        self,
        store: ArtifactStore,
        run_dir: Path,
        sample_artifact_data: dict,
    ) -> None:
        """load_artifact reads and parses a valid JSON file."""
        artifact_path = run_dir / "artifacts" / "product_facts.json"
        artifact_path.write_text(
            json.dumps(sample_artifact_data, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        result = store.load_artifact("product_facts.json", validate_schema=False)
        assert result == sample_artifact_data

    def test_file_not_found(self, store: ArtifactStore) -> None:
        """load_artifact raises FileNotFoundError for missing artifacts."""
        with pytest.raises(FileNotFoundError, match="Required artifact not found"):
            store.load_artifact("missing.json")

    def test_invalid_json(self, store: ArtifactStore, run_dir: Path) -> None:
        """load_artifact raises JSONDecodeError for malformed JSON."""
        artifact_path = run_dir / "artifacts" / "bad.json"
        artifact_path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            store.load_artifact("bad.json", validate_schema=False)

    def test_returns_dict(self, store: ArtifactStore, run_dir: Path) -> None:
        """load_artifact returns the parsed dict, not a string."""
        artifact_path = run_dir / "artifacts" / "simple.json"
        artifact_path.write_text('{"key": "value"}', encoding="utf-8")

        result = store.load_artifact("simple.json", validate_schema=False)
        assert isinstance(result, dict)
        assert result["key"] == "value"


# ---------------------------------------------------------------------------
# load_artifact_or_default
# ---------------------------------------------------------------------------

class TestLoadArtifactOrDefault:
    """Tests for load_artifact_or_default() method."""

    def test_returns_data_when_exists(
        self,
        store: ArtifactStore,
        run_dir: Path,
        sample_artifact_data: dict,
    ) -> None:
        """Returns loaded data when artifact exists."""
        artifact_path = run_dir / "artifacts" / "facts.json"
        artifact_path.write_text(
            json.dumps(sample_artifact_data), encoding="utf-8"
        )

        result = store.load_artifact_or_default(
            "facts.json", default={"empty": True}, validate_schema=False
        )
        assert result == sample_artifact_data

    def test_returns_default_when_missing(self, store: ArtifactStore) -> None:
        """Returns default value when artifact does not exist."""
        default = {"claims": []}
        result = store.load_artifact_or_default(
            "evidence_map.json", default=default
        )
        assert result is default

    def test_returns_none_default(self, store: ArtifactStore) -> None:
        """Returns None when that is the default."""
        result = store.load_artifact_or_default("nope.json", default=None)
        assert result is None

    def test_invalid_json_still_raises(self, store: ArtifactStore, run_dir: Path) -> None:
        """JSONDecodeError is NOT caught -- only FileNotFoundError is."""
        artifact_path = run_dir / "artifacts" / "bad.json"
        artifact_path.write_text("NOT JSON", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            store.load_artifact_or_default(
                "bad.json", default={}, validate_schema=False
            )


# ---------------------------------------------------------------------------
# write_artifact
# ---------------------------------------------------------------------------

class TestWriteArtifact:
    """Tests for write_artifact() method."""

    def test_writes_valid_json(
        self,
        store: ArtifactStore,
        run_dir: Path,
        sample_artifact_data: dict,
    ) -> None:
        """write_artifact creates a JSON file that can be loaded back."""
        store.write_artifact("output.json", sample_artifact_data)

        written = json.loads(
            (run_dir / "artifacts" / "output.json").read_text(encoding="utf-8")
        )
        assert written == sample_artifact_data

    def test_returns_entry_with_sha256(
        self,
        store: ArtifactStore,
        sample_artifact_data: dict,
    ) -> None:
        """write_artifact returns an entry dict with path, sha256, size."""
        entry = store.write_artifact("output.json", sample_artifact_data)

        assert "path" in entry
        assert "sha256" in entry
        assert "size" in entry
        assert isinstance(entry["sha256"], str)
        assert len(entry["sha256"]) == 64  # SHA-256 hex digest length
        assert isinstance(entry["size"], int)
        assert entry["size"] > 0

    def test_entry_path_is_relative(
        self,
        store: ArtifactStore,
        sample_artifact_data: dict,
    ) -> None:
        """Returned path is relative to run_dir, using forward slashes."""
        entry = store.write_artifact("page_plan.json", sample_artifact_data)
        assert entry["path"] == "artifacts/page_plan.json"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """write_artifact creates artifacts/ directory if missing."""
        run_dir = tmp_path / "fresh_run"
        run_dir.mkdir()
        # NOTE: We do NOT create run_dir/artifacts/ ourselves
        fresh_store = ArtifactStore(run_dir=run_dir)

        entry = fresh_store.write_artifact("test.json", {"key": "val"})
        assert (run_dir / "artifacts" / "test.json").exists()
        assert entry["size"] > 0

    def test_overwrites_existing(
        self,
        store: ArtifactStore,
        run_dir: Path,
    ) -> None:
        """write_artifact overwrites an existing artifact file."""
        store.write_artifact("data.json", {"version": 1})
        store.write_artifact("data.json", {"version": 2})

        loaded = json.loads(
            (run_dir / "artifacts" / "data.json").read_text(encoding="utf-8")
        )
        assert loaded["version"] == 2


# ---------------------------------------------------------------------------
# Deterministic output
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Tests for deterministic JSON output."""

    def test_same_input_same_bytes(self, store: ArtifactStore, run_dir: Path) -> None:
        """Identical data produces byte-for-byte identical output."""
        data = {"z_field": 1, "a_field": 2, "m_field": 3}

        store.write_artifact("first.json", data)
        store.write_artifact("second.json", data)

        bytes_a = (run_dir / "artifacts" / "first.json").read_bytes()
        bytes_b = (run_dir / "artifacts" / "second.json").read_bytes()
        assert bytes_a == bytes_b

    def test_keys_sorted(self, store: ArtifactStore, run_dir: Path) -> None:
        """Output JSON has keys in sorted order."""
        data = {"zebra": 1, "alpha": 2, "middle": 3}
        store.write_artifact("sorted.json", data)

        text = (run_dir / "artifacts" / "sorted.json").read_text(encoding="utf-8")
        keys = [
            line.strip().split('"')[1]
            for line in text.strip().splitlines()
            if line.strip().startswith('"')
        ]
        assert keys == sorted(keys)

    def test_trailing_newline(self, store: ArtifactStore, run_dir: Path) -> None:
        """Output JSON ends with a trailing newline (POSIX convention)."""
        store.write_artifact("nl.json", {"k": "v"})
        raw = (run_dir / "artifacts" / "nl.json").read_text(encoding="utf-8")
        assert raw.endswith("\n")

    def test_sha256_consistent(self, store: ArtifactStore) -> None:
        """SHA-256 in entry matches actual file hash."""
        data = {"test": True}
        entry = store.write_artifact("check.json", data)

        from launch.io.hashing import sha256_bytes
        actual_bytes = store.artifact_path("check.json").read_bytes()
        expected_sha = sha256_bytes(actual_bytes)
        assert entry["sha256"] == expected_sha


# ---------------------------------------------------------------------------
# emit_event
# ---------------------------------------------------------------------------

class TestEmitEvent:
    """Tests for emit_event() method."""

    def test_appends_to_events_ndjson(self, store: ArtifactStore, run_dir: Path) -> None:
        """emit_event appends a line to events.ndjson."""
        store.emit_event("TEST_EVENT", {"key": "value"})

        events_file = run_dir / "events.ndjson"
        assert events_file.exists()

        lines = events_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

        event = json.loads(lines[0])
        assert event["type"] == "TEST_EVENT"
        assert event["payload"]["key"] == "value"

    def test_multiple_events_append(self, store: ArtifactStore, run_dir: Path) -> None:
        """Multiple emit_event calls produce multiple lines."""
        store.emit_event("EVENT_A", {"seq": 1})
        store.emit_event("EVENT_B", {"seq": 2})
        store.emit_event("EVENT_C", {"seq": 3})

        events_file = run_dir / "events.ndjson"
        lines = events_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

        types = [json.loads(line)["type"] for line in lines]
        assert types == ["EVENT_A", "EVENT_B", "EVENT_C"]

    def test_event_has_required_fields(self, store: ArtifactStore, run_dir: Path) -> None:
        """Emitted events have all required fields per event schema."""
        store.emit_event(
            "WORK_ITEM_STARTED",
            {"worker": "W4"},
            run_id="run_test",
            trace_id="trace_abc",
            span_id="span_def",
        )

        events_file = run_dir / "events.ndjson"
        event = json.loads(events_file.read_text(encoding="utf-8").strip())

        assert "event_id" in event
        assert event["run_id"] == "run_test"
        assert "ts" in event
        assert event["type"] == "WORK_ITEM_STARTED"
        assert event["payload"] == {"worker": "W4"}
        assert event["trace_id"] == "trace_abc"
        assert event["span_id"] == "span_def"

    def test_generates_default_ids(self, store: ArtifactStore, run_dir: Path) -> None:
        """When run_id/trace_id/span_id are not given, defaults are generated."""
        store.emit_event("SOME_EVENT", {})

        events_file = run_dir / "events.ndjson"
        event = json.loads(events_file.read_text(encoding="utf-8").strip())

        assert event["run_id"] == run_dir.name
        assert len(event["trace_id"]) > 0
        assert len(event["span_id"]) > 0

    def test_creates_events_file_if_missing(self, tmp_path: Path) -> None:
        """emit_event creates events.ndjson if it does not exist."""
        run_dir = tmp_path / "new_run"
        run_dir.mkdir()
        new_store = ArtifactStore(run_dir=run_dir)

        new_store.emit_event("INIT", {"msg": "hello"})

        assert (run_dir / "events.ndjson").exists()


# ---------------------------------------------------------------------------
# Schema validation (optional)
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Tests for optional schema validation during load and write."""

    @pytest.fixture
    def schemas_dir(self, tmp_path: Path) -> Path:
        """Create a schemas directory with a simple test schema."""
        sdir = tmp_path / "schemas"
        sdir.mkdir()

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
            },
        }
        (sdir / "test_artifact.schema.json").write_text(
            json.dumps(schema, indent=2), encoding="utf-8"
        )
        return sdir

    def test_load_validates_against_schema(
        self, run_dir: Path, schemas_dir: Path
    ) -> None:
        """load_artifact validates against matching schema when present."""
        store = ArtifactStore(run_dir=run_dir, schemas_dir=schemas_dir)

        # Write valid artifact
        artifact_path = run_dir / "artifacts" / "test_artifact.json"
        artifact_path.write_text('{"name": "ok"}', encoding="utf-8")

        # Should succeed
        result = store.load_artifact("test_artifact.json")
        assert result["name"] == "ok"

    def test_load_fails_on_schema_violation(
        self, run_dir: Path, schemas_dir: Path
    ) -> None:
        """load_artifact raises ValueError when schema validation fails."""
        store = ArtifactStore(run_dir=run_dir, schemas_dir=schemas_dir)

        # Write invalid artifact (missing required 'name')
        artifact_path = run_dir / "artifacts" / "test_artifact.json"
        artifact_path.write_text('{"other": "field"}', encoding="utf-8")

        with pytest.raises(ValueError, match="Schema validation failed"):
            store.load_artifact("test_artifact.json")

    def test_write_validates_with_schema_id(
        self, run_dir: Path, schemas_dir: Path
    ) -> None:
        """write_artifact validates against schema_id before writing."""
        store = ArtifactStore(run_dir=run_dir, schemas_dir=schemas_dir)

        # Valid data
        store.write_artifact(
            "output.json",
            {"name": "valid"},
            schema_id="test_artifact.schema.json",
        )
        assert store.exists("output.json")

    def test_write_rejects_invalid_data(
        self, run_dir: Path, schemas_dir: Path
    ) -> None:
        """write_artifact raises ValueError for invalid data with schema_id."""
        store = ArtifactStore(run_dir=run_dir, schemas_dir=schemas_dir)

        with pytest.raises(ValueError, match="Schema validation failed"):
            store.write_artifact(
                "output.json",
                {"invalid": True},
                schema_id="test_artifact.schema.json",
            )

    def test_no_schema_dir_skips_validation(self, store: ArtifactStore, run_dir: Path) -> None:
        """When schemas_dir is None, schema validation is silently skipped."""
        artifact_path = run_dir / "artifacts" / "any.json"
        artifact_path.write_text('{"anything": true}', encoding="utf-8")

        # Should not raise even though no schema exists
        result = store.load_artifact("any.json", validate_schema=True)
        assert result == {"anything": True}

    def test_missing_schema_file_skips_validation(
        self, run_dir: Path, schemas_dir: Path
    ) -> None:
        """When schema file for artifact doesn't exist, validation is skipped."""
        store = ArtifactStore(run_dir=run_dir, schemas_dir=schemas_dir)

        # no_schema.json has no matching no_schema.schema.json
        artifact_path = run_dir / "artifacts" / "no_schema.json"
        artifact_path.write_text('{"any": "data"}', encoding="utf-8")

        result = store.load_artifact("no_schema.json")
        assert result["any"] == "data"

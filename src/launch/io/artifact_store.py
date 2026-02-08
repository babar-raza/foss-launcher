"""TC-1032: Centralized ArtifactStore for unified artifact I/O and event emission.

Eliminates duplicated load/write/emit patterns found across 9+ workers.
Each worker currently has its own emit_event(), load_<artifact>() functions
with identical logic. This module provides a single, tested ArtifactStore
class that all workers can use.

Design decisions:
- Reuses atomic.py for writes (atomic_write_json, atomic_write_text)
- Reuses hashing.py for SHA-256 (sha256_bytes)
- Reuses schema_validation.py for optional schema validation
- Event emission follows the events.ndjson append-only pattern
- All JSON output is deterministic: indent=2, sort_keys=True, ensure_ascii=False

Spec references:
- specs/11_state_and_events.md (Event log format)
- specs/10_determinism_and_caching.md (Deterministic output)
- specs/21_worker_contracts.md (Artifact contracts)
- specs/29_project_repo_structure.md (Run directory layout)
"""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .atomic import atomic_write_json, atomic_write_text
from .hashing import sha256_bytes
from .schema_validation import load_schema, validate


class ArtifactStore:
    """Centralized artifact loading, writing, and event emission.

    Provides a unified interface that eliminates the 14+ duplicated
    load_<artifact>() functions and 9+ duplicated emit_event() calls
    scattered across worker modules.

    Usage:
        store = ArtifactStore(run_dir=Path("/path/to/run"))
        facts = store.load_artifact("product_facts.json")
        entry = store.write_artifact("page_plan.json", plan_data)
        store.emit_event("WORK_ITEM_STARTED", {"worker": "W4"})

    All writes go through atomic_write_json/atomic_write_text from
    src/launch/io/atomic.py, preserving existing Guarantee B enforcement.
    """

    def __init__(
        self,
        run_dir: Path,
        *,
        schemas_dir: Optional[Path] = None,
    ) -> None:
        """Initialize with the run output directory.

        Args:
            run_dir: Path to the run directory (e.g., output/run_xxx).
                     Artifacts are stored under run_dir/artifacts/.
            schemas_dir: Optional path to schema directory for validation.
                         If None, schema validation is skipped.
        """
        self.run_dir = run_dir
        self.schemas_dir = schemas_dir

    @property
    def artifacts_dir(self) -> Path:
        """Path to the artifacts subdirectory."""
        return self.run_dir / "artifacts"

    def artifact_path(self, name: str) -> Path:
        """Get the full path for an artifact name.

        Args:
            name: Artifact filename (e.g., 'repo_inventory.json')

        Returns:
            Absolute path under run_dir/artifacts/
        """
        return self.artifacts_dir / name

    def exists(self, name: str) -> bool:
        """Check if an artifact exists.

        Args:
            name: Artifact filename

        Returns:
            True if the artifact file exists on disk
        """
        return self.artifact_path(name).is_file()

    def load_artifact(self, name: str, *, validate_schema: bool = True) -> dict:
        """Load a JSON artifact by name from run_dir/artifacts/.

        Args:
            name: Artifact filename (e.g., 'repo_inventory.json',
                  'product_facts.json')
            validate_schema: If True and a matching schema exists in
                           schemas_dir, validate the artifact against it.

        Returns:
            Parsed dict from the JSON file.

        Raises:
            FileNotFoundError: If the artifact file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If schema validation fails.
        """
        artifact_path = self.artifact_path(name)
        if not artifact_path.is_file():
            raise FileNotFoundError(
                f"Required artifact not found: {name} "
                f"(expected at {artifact_path})"
            )

        data = json.loads(artifact_path.read_text(encoding="utf-8"))

        if validate_schema:
            self._validate_if_schema_exists(name, data)

        return data

    def load_artifact_or_default(
        self,
        name: str,
        default: Any,
        *,
        validate_schema: bool = True,
    ) -> Any:
        """Load artifact or return default if not found.

        This is the safe counterpart to load_artifact() for optional
        artifacts like evidence_map.json that may not exist yet.

        Args:
            name: Artifact filename
            default: Value to return if artifact does not exist
            validate_schema: If True and schema exists, validate loaded data

        Returns:
            Parsed dict if artifact exists, otherwise default value.

        Raises:
            json.JSONDecodeError: If file exists but contains invalid JSON.
            ValueError: If schema validation fails on existing file.
        """
        try:
            return self.load_artifact(name, validate_schema=validate_schema)
        except FileNotFoundError:
            return default

    def write_artifact(
        self,
        name: str,
        data: dict,
        *,
        schema_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write a JSON artifact atomically.

        Uses atomic_write_json from src/launch/io/atomic.py to ensure
        writes are crash-safe (write to temp file, then rename).

        JSON output is deterministic per specs/10_determinism_and_caching.md:
        indent=2, sort_keys=True, ensure_ascii=False.

        Args:
            name: Output filename (written to run_dir/artifacts/)
            data: Dict to serialize as JSON
            schema_id: Optional schema filename to validate against
                      before writing (e.g., 'page_plan.schema.json')

        Returns:
            ArtifactIndexEntry-like dict with:
            - path: str (relative path from run_dir)
            - sha256: str (hex digest of written bytes)
            - size: int (byte count of written file)

        Raises:
            ValueError: If schema validation fails (when schema_id given).
        """
        # Validate against schema before writing if requested
        if schema_id and self.schemas_dir:
            schema_path = self.schemas_dir / schema_id
            if schema_path.is_file():
                schema = load_schema(schema_path)
                validate(data, schema, context=name)

        artifact_path = self.artifact_path(name)

        # Use atomic_write_json which handles:
        # - mkdir -p for parent dirs
        # - temp file + os.replace for atomicity
        # - deterministic JSON serialization
        # - Guarantee B path validation
        atomic_write_json(artifact_path, data)

        # Compute metadata from the written file for the index entry
        written_bytes = artifact_path.read_bytes()
        sha256 = sha256_bytes(written_bytes)
        size = len(written_bytes)

        # Return path relative to run_dir for the artifact index
        rel_path = str(artifact_path.relative_to(self.run_dir))
        # Normalize to forward slashes for cross-platform consistency
        rel_path = rel_path.replace("\\", "/")

        return {
            "path": rel_path,
            "sha256": sha256,
            "size": size,
        }

    def emit_event(
        self,
        event_type: str,
        payload: dict,
        *,
        run_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """Emit a telemetry event to the run's event log.

        Appends a single NDJSON line to run_dir/events.ndjson following
        the format defined in specs/11_state_and_events.md.

        If run_id, trace_id, or span_id are not provided, reasonable
        defaults are generated (run_dir name and new UUIDs).

        Args:
            event_type: Event type string (e.g., 'WORK_ITEM_STARTED',
                       'ARTIFACT_WRITTEN')
            payload: Event payload dictionary
            run_id: Run identifier (defaults to run_dir.name)
            trace_id: Trace ID for telemetry (defaults to new UUID)
            span_id: Span ID for telemetry (defaults to new UUID)
        """
        # Import here to avoid circular dependency at module level.
        # The Event model is in models/ which may import from io/.
        from ..models.event import Event

        event = Event(
            event_id=str(uuid.uuid4()),
            run_id=run_id or self.run_dir.name,
            ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            type=event_type,
            payload=payload,
            trace_id=trace_id or str(uuid.uuid4()),
            span_id=span_id or str(uuid.uuid4()),
        )

        events_file = self.run_dir / "events.ndjson"

        # Ensure parent directory exists
        events_file.parent.mkdir(parents=True, exist_ok=True)

        # Append to events.ndjson (append-only log)
        event_line = json.dumps(
            event.to_dict(), ensure_ascii=False, sort_keys=True
        ) + "\n"
        with events_file.open("a", encoding="utf-8") as f:
            f.write(event_line)

    def _validate_if_schema_exists(self, artifact_name: str, data: Any) -> None:
        """Validate artifact data against schema if one exists.

        Schema filenames are derived from artifact names by replacing
        '.json' with '.schema.json'. For example:
        - 'page_plan.json' -> 'page_plan.schema.json'
        - 'product_facts.json' -> 'product_facts.schema.json'

        Args:
            artifact_name: Artifact filename
            data: Parsed artifact data to validate

        Raises:
            ValueError: If schema validation fails.
        """
        if not self.schemas_dir:
            return

        # Derive schema filename from artifact name
        if artifact_name.endswith(".json"):
            schema_name = artifact_name.replace(".json", ".schema.json")
        else:
            return

        schema_path = self.schemas_dir / schema_name
        if not schema_path.is_file():
            return

        schema = load_schema(schema_path)
        validate(data, schema, context=artifact_name)

"""Centralized ArtifactStore for unified artifact I/O and event emission.

Eliminates duplicated load/write/emit patterns across workers.
Each worker uses a single ArtifactStore instance for all artifact
and event operations within a run directory.

Design decisions:
- Reuses atomic.py for writes (atomic_write_json, atomic_write_text)
- Reuses hashing.py for SHA-256 (sha256_bytes)
- Reuses schema_validation.py for optional schema validation
- Event emission follows the events.ndjson append-only pattern
- All JSON output is deterministic: indent=2, sort_keys=True, ensure_ascii=False
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .atomic import atomic_write_json
from .hashing import sha256_bytes
from .schema_validation import load_schema, validate

logger = logging.getLogger(__name__)


class ArtifactStore:
    """Centralized artifact loading, writing, and event emission.

    Usage:
        store = ArtifactStore(run_dir=Path("runs/r_xxx"))
        bundle = store.load_json("understanding_bundle.json")
        entry = store.write_json("evaluation_report.json", report_data)
        store.emit_event("worker_started", {"worker": "Understand"})
    """

    def __init__(
        self,
        run_dir: Path,
        *,
        schemas_dir: Optional[Path] = None,
    ) -> None:
        self.run_dir = run_dir
        self.schemas_dir = schemas_dir

    def file_path(self, name: str) -> Path:
        """Get the full path for a file name relative to run_dir."""
        return self.run_dir / name

    def exists(self, name: str) -> bool:
        """Check if a file exists in the run directory."""
        return self.file_path(name).is_file()

    def load_json(self, name: str, *, validate_schema: bool = True) -> dict:
        """Load a JSON file by name from run_dir.

        Args:
            name: Filename relative to run_dir (e.g., 'understanding_bundle.json').
            validate_schema: If True and a matching schema exists, validate.

        Returns:
            Parsed dict from the JSON file.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ValueError: If schema validation fails.
        """
        fpath = self.file_path(name)
        if not fpath.is_file():
            raise FileNotFoundError(
                f"Required file not found: {name} (expected at {fpath})"
            )

        data = json.loads(fpath.read_text(encoding="utf-8"))

        if validate_schema:
            self._validate_if_schema_exists(name, data)

        return data

    def load_json_or_default(
        self,
        name: str,
        default: Any,
        *,
        validate_schema: bool = True,
    ) -> Any:
        """Load JSON file or return default if not found."""
        try:
            return self.load_json(name, validate_schema=validate_schema)
        except FileNotFoundError:
            return default

    def write_json(
        self,
        name: str,
        data: dict,
        *,
        schema_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write a JSON file atomically to run_dir.

        Args:
            name: Output filename relative to run_dir.
            data: Dict to serialize as JSON.
            schema_id: Optional schema filename to validate against.

        Returns:
            Dict with path (relative), sha256, and size.
        """
        if schema_id and self.schemas_dir:
            schema_path = self.schemas_dir / schema_id
            if schema_path.is_file():
                schema = load_schema(schema_path)
                validate(data, schema, context=name)

        fpath = self.file_path(name)
        atomic_write_json(fpath, data)

        written_bytes = fpath.read_bytes()
        sha256 = sha256_bytes(written_bytes)
        size = len(written_bytes)

        rel_path = str(fpath.relative_to(self.run_dir)).replace("\\", "/")

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
        worker: str = "",
    ) -> None:
        """Emit a telemetry event to run_dir/events.ndjson.

        Uses the Event model and append_event() for a single serialization
        path shared with llm_telemetry.

        Args:
            event_type: Event type string (e.g., 'worker_started').
            payload: Event payload dictionary.
            run_id: Run identifier (defaults to run_dir.name).
            worker: Worker name for the event.
        """
        from launcher.models.event import Event
        from launcher.state.event_log import append_event

        events_file = self.run_dir / "events.ndjson"
        events_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                run_id=run_id or self.run_dir.name,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                worker=worker,
                data=payload,
            )
            append_event(events_file, event)
        except Exception:
            logger.warning(
                "Failed to emit event %s; falling back to raw write",
                event_type,
                exc_info=True,
            )
            # Fallback: raw dict append (never lose events)
            event_record = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "run_id": run_id or self.run_dir.name,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "worker": worker,
                "data": payload,
            }
            line = json.dumps(event_record, ensure_ascii=False, sort_keys=True) + "\n"
            with open(events_file, "a", encoding="utf-8") as f:
                f.write(line)

    def _validate_if_schema_exists(self, name: str, data: Any) -> None:
        """Validate data against schema if one exists."""
        if not self.schemas_dir:
            return

        if name.endswith(".json"):
            schema_name = name.replace(".json", ".schema.json")
        else:
            return

        schema_path = self.schemas_dir / schema_name
        if not schema_path.is_file():
            return

        schema = load_schema(schema_path)
        validate(data, schema, context=name)

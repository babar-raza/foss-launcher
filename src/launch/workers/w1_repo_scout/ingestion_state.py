"""Ingestion state manager — tracks file hashes for incremental processing.

Reference: content-generator kb_ingestion.py IngestionStateManager (TC-2397).
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class IngestionStateManager:
    """Tracks file content hashes to skip unchanged files on subsequent runs.

    State is persisted to a JSON file so it survives between runs.
    """

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self._state: Dict[str, str] = {}
        if state_file.exists():
            try:
                self._state = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("ingestion_state_load_failed path=%s error=%s", state_file, e)

    def needs_ingestion(self, file_path: Path) -> bool:
        """Return True if file has changed since last ingestion (or never ingested)."""
        key = str(file_path)
        stored_hash = self._state.get(key)
        try:
            current_hash = self._file_hash(file_path)
        except OSError:
            return True  # Can't read → treat as changed
        return stored_hash != current_hash

    def mark_ingested(self, file_path: Path) -> None:
        """Record that file was successfully ingested at current content."""
        try:
            self._state[str(file_path)] = self._file_hash(file_path)
            self._persist()
        except Exception as e:
            logger.warning("ingestion_state_mark_failed path=%s error=%s", file_path, e)

    def mark_ingested_many(self, file_paths: list) -> None:
        """Batch mark multiple files as ingested (one persist at the end)."""
        for fp in file_paths:
            try:
                self._state[str(fp)] = self._file_hash(fp)
            except Exception:
                pass
        self._persist()

    def get_changed_files(self, file_paths: list) -> list:
        """Return subset of file_paths that need re-ingestion."""
        return [fp for fp in file_paths if self.needs_ingestion(fp)]

    def clear(self) -> None:
        """Clear all state (force full re-ingestion on next run)."""
        self._state = {}
        self._persist()

    @property
    def tracked_file_count(self) -> int:
        """Return number of files currently tracked in state."""
        return len(self._state)

    def _file_hash(self, path: Path) -> str:
        """SHA-256 of file contents, first 16 hex chars."""
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    def _persist(self) -> None:
        """Write state to disk (best-effort)."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(self._state, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("ingestion_state_persist_failed path=%s error=%s", self.state_file, e)

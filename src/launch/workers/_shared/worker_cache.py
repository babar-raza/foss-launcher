"""Hash-based worker skip cache for incremental pipeline execution.

DISABLED by default (caching.enabled=false in run_config).
Zero behavior change when disabled.

Cache file: run_dir/artifacts/run_cache.json
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkerCache:
    """Per-run artifact hash cache. Safe to use even when disabled."""

    def __init__(self, run_dir: Path, enabled: bool = False) -> None:
        self.run_dir = run_dir
        self.enabled = enabled
        self._cache_path = run_dir / "artifacts" / "run_cache.json"
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load existing cache. Returns {} on missing/corrupt file."""
        if self._cache_path.exists():
            try:
                return json.loads(self._cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def compute_input_hash(self, artifact_paths: List[Path]) -> str:
        """SHA256 over sorted artifact path+content. Deterministic."""
        h = hashlib.sha256()
        for path in sorted(artifact_paths, key=lambda p: str(p)):
            if path.exists():
                h.update(str(path).encode("utf-8"))
                h.update(b"|")
                h.update(path.read_bytes())
        return h.hexdigest()

    def is_hit(self, worker_id: str, input_hash: str) -> bool:
        """True iff cache enabled AND recorded hash matches input_hash."""
        if not self.enabled:
            return False
        recorded = self._data.get("workers", {}).get(worker_id, {}).get("input_hash")
        return recorded == input_hash

    def record(self, worker_id: str, input_hash: str, output_hash: str) -> None:
        """Record worker's input/output hash pair. No-op when disabled."""
        if not self.enabled:
            return
        workers = self._data.setdefault("workers", {})
        workers[worker_id] = {"input_hash": input_hash, "output_hash": output_hash}
        self._persist()

    def _persist(self) -> None:
        """Persist cache atomically to run_cache.json."""
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to temp then rename for atomicity
        tmp = self._cache_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self._cache_path)

    def to_artifact(self) -> Dict[str, Any]:
        """Serialize to run_cache.json format."""
        return {
            "schema_version": "1.0",
            "enabled": self.enabled,
            "workers": self._data.get("workers", {}),
            "pages": self._data.get("pages", {}),
        }

    def is_page_hit(self, page_key: str, input_hash: str = "") -> Optional[str]:
        """Returns cached draft file path if hit, None on miss.

        Hash validation rules (TC-2450):
        - If input_hash provided AND stored entry has a non-empty input_hash:
          validate they match. Mismatch → miss.
        - If either is empty (old entries / callers without hash): skip validation
          (backward-compatible with pre-TC-2450 callers).
        """
        if not self.enabled:
            return None
        entry = self._data.get("pages", {}).get(page_key)
        if entry is None:
            return None
        stored_hash = entry.get("input_hash", "")
        if input_hash and stored_hash and stored_hash != input_hash:
            return None  # Hash mismatch → cache miss
        return entry.get("draft_path")

    def record_page(self, page_key: str, draft_path: str, input_hash: str = "") -> None:
        """Record a page's draft path (and optional input hash) in the cache.

        TC-2450: input_hash="" is accepted for backward compat with existing callers.
        No-op when disabled.
        """
        if not self.enabled:
            return
        pages = self._data.setdefault("pages", {})
        pages[page_key] = {"draft_path": draft_path, "input_hash": input_hash}
        self._persist()


def load_cache_config(run_dir: Path, run_config: Dict[str, Any]) -> WorkerCache:
    """Load WorkerCache from run_config. Returns disabled cache if not configured."""
    caching = run_config.get("caching", {})
    enabled = bool(caching.get("enabled", False))
    return WorkerCache(run_dir, enabled=enabled)

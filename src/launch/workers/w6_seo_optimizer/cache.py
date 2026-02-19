"""Persistent cache for SEO operations with TTL support."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

from ...util.logging import get_logger

logger = get_logger()


class SEOCache:
    """Persistent JSON cache with per-key TTL.

    Storage: {run_dir}/work/seo_cache.json
    Thread-safe: single-writer model (adequate for sequential worker)
    Cross-run reuse: loads existing cache, prunes expired entries on load
    """

    def __init__(self, cache_path: Path, default_ttl: int = 3600):
        self._path = cache_path
        self._default_ttl = default_ttl
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load cache from disk, prune expired entries."""
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                now = time.time()
                self._data = {
                    k: v for k, v in raw.items()
                    if v.get("expires_at", 0) > now
                }
                pruned = len(raw) - len(self._data)
                if pruned > 0:
                    logger.info(
                        "[W10 Cache] Loaded entries, pruned expired",
                        loaded=len(self._data),
                        pruned=pruned,
                    )
            except (json.JSONDecodeError, KeyError):
                logger.warning("[W10 Cache] Corrupt cache file, starting fresh")
                self._data = {}
        else:
            logger.info("[W10 Cache] No existing cache, starting fresh")

    def _save(self) -> None:
        """Persist cache to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    @staticmethod
    def _make_key(raw_key: str) -> str:
        """Hash raw key for consistent storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        hashed = self._make_key(key)
        entry = self._data.get(hashed)
        if entry and entry.get("expires_at", 0) > time.time():
            return entry.get("value")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value with TTL (defaults to self._default_ttl)."""
        hashed = self._make_key(key)
        self._data[hashed] = {
            "key_hint": key[:100],  # For debugging
            "value": value,
            "expires_at": time.time() + (ttl or self._default_ttl),
            "created_at": time.time(),
        }
        self._save()

    def get_or_compute(
        self, key: str, compute_fn: Callable[[], Any], ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or compute and store."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute_fn()
        self.set(key, value, ttl)
        return value

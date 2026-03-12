"""Cross-run, per-family/platform SEO cache with TTL management.

Stores keyword research, Gemini responses, and other SEO data on disk
so that repeated runs for the same product family/platform reuse
previously fetched external API results.

Cache layout::

    <cache_root>/<family>/<platform>/
        trends.json
        suggest.json
        gemini_keywords.json
        ...

Each JSON file holds a dict of cache entries keyed by SHA-256 hash.

TC-3806: Created for v2 SEO module.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Default TTLs in seconds.
TTL_EXTERNAL_API = 7 * 24 * 3600  # 7 days for Trends/Suggest/Gemini
TTL_LOCAL = 24 * 3600  # 24 hours for claim-derived/patterns


class SEOCache:
    """Disk-backed cache with per-entry TTL.

    Parameters
    ----------
    cache_dir:
        Directory where cache files are stored.  Created on first write.
    default_ttl:
        Default time-to-live in seconds for entries without explicit TTL.
    """

    def __init__(self, cache_dir: Path, default_ttl: int = TTL_EXTERNAL_API) -> None:
        self._cache_dir = cache_dir
        self._default_ttl = default_ttl
        self._stores: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, store_name: str, key: str) -> Any | None:
        """Return cached value or ``None`` if missing/expired.

        Parameters
        ----------
        store_name:
            Logical store name (e.g. ``"trends"``, ``"gemini_keywords"``).
            Maps to ``<cache_dir>/<store_name>.json``.
        key:
            Raw cache key (will be hashed internally).
        """
        hashed = _make_key(key)
        store = self._load_store(store_name)
        entry = store.get(hashed)
        if entry is None:
            return None
        if time.time() > entry.get("expires_at", 0):
            # Expired — remove lazily.
            store.pop(hashed, None)
            return None
        return entry.get("value")

    def set(
        self,
        store_name: str,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Store a value with TTL.

        Parameters
        ----------
        store_name:
            Logical store name.
        key:
            Raw cache key.
        value:
            JSON-serialisable value.
        ttl:
            Time-to-live in seconds.  Falls back to ``default_ttl``.
        """
        hashed = _make_key(key)
        store = self._load_store(store_name)
        now = time.time()
        store[hashed] = {
            "key_hint": key[:100],
            "value": value,
            "created_at": now,
            "expires_at": now + (ttl if ttl is not None else self._default_ttl),
            "cache_version": 1,
        }
        self._save_store(store_name, store)

    def get_or_compute(
        self,
        store_name: str,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: int | None = None,
    ) -> Any:
        """Return cached value or compute, cache, and return.

        Parameters
        ----------
        store_name:
            Logical store name.
        key:
            Raw cache key.
        compute_fn:
            Zero-arg callable that produces the value on cache miss.
        ttl:
            Time-to-live in seconds.
        """
        cached = self.get(store_name, key)
        if cached is not None:
            logger.debug("SEO cache HIT: store=%s key_hint=%s", store_name, key[:60])
            return cached
        logger.debug("SEO cache MISS: store=%s key_hint=%s", store_name, key[:60])
        value = compute_fn()
        self.set(store_name, key, value, ttl=ttl)
        return value

    def clear_store(self, store_name: str) -> None:
        """Delete all entries in a store."""
        self._stores.pop(store_name, None)
        path = self._store_path(store_name)
        if path.exists():
            path.unlink()

    def prune_expired(self, store_name: str) -> int:
        """Remove expired entries from a store.  Returns count removed."""
        store = self._load_store(store_name)
        now = time.time()
        expired_keys = [k for k, v in store.items() if now > v.get("expires_at", 0)]
        for k in expired_keys:
            del store[k]
        if expired_keys:
            self._save_store(store_name, store)
        return len(expired_keys)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _store_path(self, store_name: str) -> Path:
        return self._cache_dir / f"{store_name}.json"

    def _load_store(self, store_name: str) -> dict[str, Any]:
        if store_name in self._stores:
            return self._stores[store_name]

        path = self._store_path(store_name)
        store: dict[str, Any] = {}
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, dict):
                    store = data
                else:
                    logger.warning(
                        "SEO cache store %s has non-dict root; resetting", store_name,
                    )
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "SEO cache store %s corrupted (%s); resetting", store_name, exc,
                )

        self._stores[store_name] = store
        return store

    def _save_store(self, store_name: str, store: dict[str, Any]) -> None:
        self._stores[store_name] = store
        path = self._store_path(store_name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp file in same directory, then replace.
            fd, tmp_path = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".seo_cache_",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(store, f, indent=2, sort_keys=True)
                os.replace(tmp_path, str(path))
            except BaseException:
                # Clean up temp file on any error.
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as exc:
            logger.warning("SEO cache write failed for %s: %s", store_name, exc)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _make_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key, truncated to 16 hex chars."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def make_cache_key(
    family: str,
    platform: str,
    source: str,
    content_hash: str = "",
) -> str:
    """Build a canonical raw cache key for SEO data.

    Parameters
    ----------
    family:
        Product family (e.g. ``"cells"``).
    platform:
        Platform (e.g. ``"python"``).
    source:
        Data source name (e.g. ``"trends"``, ``"suggest"``).
    content_hash:
        Optional content-dependent hash (e.g. hash of claim texts).
    """
    parts = [family.lower(), platform.lower(), source]
    if content_hash:
        parts.append(content_hash)
    return ":".join(parts)


def build_cache_dir(cache_root: Path, family: str, platform: str) -> Path:
    """Return the cache directory for a specific family/platform pair."""
    return cache_root / family.lower() / platform.lower()

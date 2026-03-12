"""Disk-backed LLM response cache (opt-in).

Purpose
-------
Speed up reruns, restarts, and iterative gate-fix cycles by returning prior
LLM responses from disk instead of making network calls for identical requests.
The cache is **opt-in** and has zero effect when disabled (the default).

Environment variables
---------------------
FOSS_LAUNCHER_LLM_CACHE
    Set to ``"1"`` to enable the disk cache.  Default: ``"0"`` (disabled).
FOSS_LAUNCHER_LLM_CACHE_DIR
    Override the cache directory path.
    Default: ``<run_dir>/cache/llm``.
FOSS_LAUNCHER_LLM_CACHE_ALLOW_NONDET
    Set to ``"1"`` to cache responses for requests with ``temperature > 0``
    (non-deterministic sampling).  Default: ``"0"`` -- only temperature == 0.0
    requests are cached.
FOSS_LAUNCHER_LLM_CACHE_FALLBACK
    Set to ``"1"`` to also cache responses from the fallback endpoint.
    Default: ``"0"`` -- only primary-endpoint responses are cached.

Cache key
---------
SHA-256 of the canonical JSON serialisation (``sort_keys=True``, compact
separators) of the full ``request_payload`` dict passed to the provider.
That dict always contains: ``model``, ``messages`` (including any
``output_schema`` injection), ``temperature``, and optionally
``max_tokens``, ``response_format``, ``tools``.  All fields that affect
LLM output are therefore covered.

Storage format
--------------
One JSON file per key: ``<cache_dir>/<sha256>.json``::

    {
      "meta": {
        "key_prefix": "<first 8 chars>",
        "saved_at": <unix timestamp>,
        "model": "<model name>",
        "endpoint_used": "primary"
      },
      "response": { <full result dict from LLMProviderClient> }
    }

Writes are atomic (temp-file + ``os.replace``).  Corrupted or incomplete
entries are silently treated as cache misses.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def cache_enabled() -> bool:
    """Return ``True`` when ``FOSS_LAUNCHER_LLM_CACHE=1`` is set."""
    return os.environ.get("FOSS_LAUNCHER_LLM_CACHE", "0") == "1"


def cache_dir(run_dir: Optional[Path] = None) -> Path:
    """Return the effective cache directory.

    Priority order:

    1. ``FOSS_LAUNCHER_LLM_CACHE_DIR`` env var (explicit override).
    2. ``<run_dir>/cache/llm`` when *run_dir* is provided.
    3. ``.cache/llm`` relative to the current working directory (safe
       fallback when no run context is available).

    Args:
        run_dir: Optional run directory (``LLMProviderClient.run_dir``).

    Returns:
        Resolved ``Path`` for cache files.  The directory is **not** created
        here; callers must call ``.mkdir(parents=True, exist_ok=True)`` before
        writing.
    """
    env_override = os.environ.get("FOSS_LAUNCHER_LLM_CACHE_DIR")
    if env_override:
        return Path(env_override)
    if run_dir is not None:
        return Path(run_dir) / "cache" / "llm"
    return Path(".cache") / "llm"


def make_cache_key(request_sig: Dict[str, Any]) -> str:
    """Return the SHA-256 hex digest of *request_sig*.

    Uses ``sort_keys=True`` and compact separators so the key is
    deterministic across Python versions and dict-insertion orders.

    Args:
        request_sig: Dict containing all fields that affect LLM output:
            ``model``, ``messages``, ``temperature``, ``max_tokens``
            (optional), ``response_format`` (optional), ``tools``
            (optional).

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    canonical = json.dumps(
        request_sig,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load(key: str, dir_: Path) -> Optional[Dict[str, Any]]:
    """Load the cached response for *key* from *dir_*.

    Args:
        key: 64-char SHA-256 hex key (from :func:`make_cache_key`).
        dir_: Cache directory to search.

    Returns:
        The stored ``response`` dict on a cache hit, or ``None`` on:

        - cache miss (file not found),
        - parse error (invalid JSON),
        - structural corruption (missing ``"response"`` key),
        - any other I/O exception.

        Callers should treat ``None`` as an ordinary cache miss.
    """
    cache_file = dir_ / f"{key}.json"
    if not cache_file.exists():
        return None
    try:
        raw = cache_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict) or "response" not in data:
            return None
        return data["response"]
    except Exception:  # noqa: BLE001 -- corruption-tolerant by design
        return None


def save(key: str, response: Dict[str, Any], dir_: Path) -> None:
    """Persist *response* for *key* atomically.

    Writes to a ``.tmp`` file first then calls ``os.replace`` so readers
    never observe a partial write, even on process crash mid-write.

    Args:
        key: 64-char SHA-256 hex key (from :func:`make_cache_key`).
        response: Full result dict returned by ``LLMProviderClient``.
        dir_: Cache directory (created if absent).
    """
    dir_.mkdir(parents=True, exist_ok=True)
    cache_file = dir_ / f"{key}.json"
    tmp_file = dir_ / f"{key}.json.tmp"
    data: Dict[str, Any] = {
        "meta": {
            "key_prefix": key[:8],
            "saved_at": time.time(),
            "model": response.get("model"),
            "endpoint_used": response.get("endpoint_used"),
        },
        "response": response,
    }
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    tmp_file.write_text(payload, encoding="utf-8")
    os.replace(tmp_file, cache_file)

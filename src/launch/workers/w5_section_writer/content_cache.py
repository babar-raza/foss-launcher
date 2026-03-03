"""TC-3675: Content cache for W5 section-level caching.

Provides deterministic caching of LLM-generated content keyed by input signature.
Cache is run-local (stored under run_dir/cache/w5_content/).

Spec: specs/28_coordination_and_handoffs.md
      section: W5 Content Cache and Section-Level Regeneration (TC-3675)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContentCacheKey:
    """Deterministic cache key for a single content section.

    All fields contribute to the final hash.  Claims are pre-hashed externally
    (facts_hash) so the key itself is lightweight and serialisable.
    """

    page_path: str
    section_heading: str
    facts_hash: str
    outline_hash: str
    prompt_version: str = ""
    model_id: str = ""
    canonical_import: str = ""


def compute_cache_key(
    page_path: str,
    section_heading: str,
    claims: List[Dict[str, Any]],
    outline: str = "",
    prompt_version: str = "",
    model_id: str = "",
    canonical_import: str = "",
) -> str:
    """Compute a deterministic SHA-256 cache key from inputs.

    Claims are sorted by ``claim_id`` before hashing for determinism
    (specs/10_determinism_and_caching.md).  All JSON serialisation uses
    ``sort_keys=True, ensure_ascii=True`` per the binding contract in
    specs/28_coordination_and_handoffs.md §Cache key contract.
    """
    sorted_claims = sorted(claims, key=lambda c: c.get("claim_id", ""))
    claims_json = json.dumps(sorted_claims, sort_keys=True, ensure_ascii=True)
    facts_hash = hashlib.sha256(claims_json.encode()).hexdigest()[:16]
    outline_hash = hashlib.sha256(outline.encode()).hexdigest()[:16]

    key = ContentCacheKey(
        page_path=page_path,
        section_heading=section_heading,
        facts_hash=facts_hash,
        outline_hash=outline_hash,
        prompt_version=prompt_version,
        model_id=model_id,
        canonical_import=canonical_import,
    )

    key_json = json.dumps(asdict(key), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(key_json.encode()).hexdigest()


class ContentCache:
    """Run-local content cache stored under ``run_dir/cache/w5_content/``.

    Each cached entry is a JSON file named by its cache key hash.  The cache
    directory is created lazily on the first ``put()`` call.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._hits: int = 0
        self._misses: int = 0
        self._puts: int = 0

    @property
    def cache_dir(self) -> Path:
        """Return the cache directory path."""
        return self._cache_dir

    def get(self, key: str) -> Optional[str]:
        """Retrieve cached content by key hash.  Returns ``None`` on miss."""
        path = self._cache_dir / f"{key}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._hits += 1
                return data.get("content", "")
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Cache read failed for %s: %s", key[:12], exc)
        self._misses += 1
        return None

    def put(self, key: str, content: str, page_path: str = "") -> None:
        """Store content in cache.  Creates ``cache_dir`` if needed.

        ``page_path`` is stored alongside the content so that
        ``invalidate(page_path)`` can selectively remove entries.
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_dir / f"{key}.json"
        data = {"key": key, "content": content, "page_path": page_path}
        path.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        self._puts += 1

    def invalidate(self, page_path: str) -> int:
        """Invalidate all cache entries for a specific *page_path*.

        Returns the count of invalidated entries.
        """
        if not self._cache_dir.exists():
            return 0
        count = 0
        for path in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("page_path") == page_path:
                    path.unlink()
                    count += 1
            except (json.JSONDecodeError, OSError):
                continue
        return count

    def clear(self) -> int:
        """Remove all cache entries.  Returns the count of removed entries."""
        if not self._cache_dir.exists():
            return 0
        count = 0
        for path in self._cache_dir.glob("*.json"):
            try:
                path.unlink()
                count += 1
            except OSError:
                continue
        return count

    def stats(self) -> Dict[str, int]:
        """Return cache statistics.

        ``entries`` is the current on-disk count; ``hits``, ``misses``, and
        ``puts`` are session-scoped counters.
        """
        entry_count = 0
        if self._cache_dir.exists():
            entry_count = sum(1 for _ in self._cache_dir.glob("*.json"))
        return {
            "entries": entry_count,
            "hits": self._hits,
            "misses": self._misses,
            "puts": self._puts,
        }

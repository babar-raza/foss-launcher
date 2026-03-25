"""Re-export module for runtime acquisition logic.

All clone functionality lives in ``launcher.workers.intake.acquisition``.
This module re-exports the public surface so that:
  - Workers import from ``launcher.workers.intake.clone``
  - Tests can mock at ``launcher.workers.intake.clone.<name>``

No wrapper functions, no runtime module mutation.
"""

from launcher.workers.intake.acquisition import (
    _CLONE_SHA_MARKER,
    _CLONE_TIMESTAMP_MARKER,
    _CLONE_URL_MARKER,
    _check_url_collision,
    _extract_brand_from_org,
    _extract_brand_from_url,
    _get_cache_dir,
    _get_repo_sha,
    _log_cache_age,
    _normalize_slug,
    _write_cache_timestamp,
    check_remote_sha,
    clone_repo_cached,
)

__all__ = [
    "_CLONE_SHA_MARKER",
    "_CLONE_TIMESTAMP_MARKER",
    "_CLONE_URL_MARKER",
    "_check_url_collision",
    "_extract_brand_from_org",
    "_extract_brand_from_url",
    "_get_cache_dir",
    "_get_repo_sha",
    "_log_cache_age",
    "_normalize_slug",
    "_write_cache_timestamp",
    "check_remote_sha",
    "clone_repo_cached",
]

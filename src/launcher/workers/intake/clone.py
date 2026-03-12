"""Compatibility wrapper for shared Phase 1 acquisition logic."""

import subprocess

from launcher.phase1 import acquisition as _impl

_CLONE_SHA_MARKER = _impl._CLONE_SHA_MARKER
_CLONE_TIMESTAMP_MARKER = _impl._CLONE_TIMESTAMP_MARKER
_CLONE_URL_MARKER = _impl._CLONE_URL_MARKER
_log_cache_age = _impl._log_cache_age
_get_cache_dir = _impl._get_cache_dir
_get_repo_sha = _impl._get_repo_sha


def check_remote_sha(repo_url: str):
    return _impl.check_remote_sha(repo_url)


def clone_repo_cached(*args, **kwargs):
    _impl.subprocess = subprocess
    _impl.check_remote_sha = check_remote_sha
    _impl._get_cache_dir = _get_cache_dir
    _impl._get_repo_sha = _get_repo_sha
    _impl._log_cache_age = _log_cache_age
    return _impl.clone_repo_cached(*args, **kwargs)

__all__ = [
    "_CLONE_SHA_MARKER",
    "_CLONE_TIMESTAMP_MARKER",
    "_CLONE_URL_MARKER",
    "_get_cache_dir",
    "_get_repo_sha",
    "_log_cache_age",
    "check_remote_sha",
    "clone_repo_cached",
]

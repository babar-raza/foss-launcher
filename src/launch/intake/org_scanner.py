"""GitHub organization repository scanner.

Discovers public repositories from configured GitHub organizations using the
GitHub REST API v3.  Supports pagination, rate limiting, activity filtering,
and state persistence.

All target repos are assumed to be public.  A GitHub token is optional —
unauthenticated access allows 60 requests/hour, while an authenticated
token increases the limit to 5000 requests/hour.

Spec reference: specs/49_github_intake.md  Section 4
TC: TC-2540
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"

# Repo fields we persist in scan state (subset of GitHub API response)
_REPO_KEYS = frozenset({
    "id", "full_name", "name", "html_url", "description", "fork",
    "archived", "is_template", "size", "stargazers_count", "language",
    "license", "pushed_at", "created_at", "updated_at", "default_branch",
    "topics", "owner",
})


class ScannerError(Exception):
    """Raised on unrecoverable scanner errors."""


class RateLimitError(ScannerError):
    """Raised when GitHub rate limit is exhausted and cannot be waited out."""


def _default_rate_limiter(delay_s: float) -> None:
    """Default rate limiter using time.sleep."""
    if delay_s > 0:
        time.sleep(delay_s)


def _parse_link_header(link_header: str) -> Dict[str, str]:
    """Parse GitHub ``Link`` header into {rel: url} mapping."""
    links: Dict[str, str] = {}
    for part in link_header.split(","):
        part = part.strip()
        match = re.match(r'<([^>]+)>;\s*rel="([^"]+)"', part)
        if match:
            links[match.group(2)] = match.group(1)
    return links


def _slim_repo(repo: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only the fields we persist from a GitHub repo response."""
    slim: Dict[str, Any] = {}
    for key in _REPO_KEYS:
        if key in repo:
            val = repo[key]
            # Flatten nested objects for deterministic serialization
            if key == "license" and isinstance(val, dict):
                slim["license"] = {"spdx_id": val.get("spdx_id"), "name": val.get("name")}
            elif key == "owner" and isinstance(val, dict):
                slim["owner"] = {"login": val.get("login"), "type": val.get("type")}
            else:
                slim[key] = val
    return slim


def scan_org(
    org: str,
    *,
    token: Optional[str] = None,
    per_page: int = 100,
    max_pages: int = 10,
    activity_months: int = 12,
    rate_limit_delay_s: float = 1.0,
    rate_limiter: Callable[[float], None] = _default_rate_limiter,
    seen_repos: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Scan a single GitHub organization for public repositories.

    Args:
        org: GitHub organization login name.
        token: GitHub API token (optional, increases rate limits).
        per_page: Repos per page (1-100).
        max_pages: Maximum pages to fetch.
        activity_months: Only include repos pushed within this many months.
        rate_limit_delay_s: Delay between paginated requests.
        rate_limiter: Callable for inter-request delay (mockable).
        seen_repos: Set of repo full_names already scanned (skipped).

    Returns:
        List of slim repo dicts for repos passing the activity filter.

    Raises:
        ScannerError: On unrecoverable API errors.
        RateLimitError: When rate limit is exhausted.
    """
    if seen_repos is None:
        seen_repos = set()

    cutoff = datetime.now(timezone.utc) - timedelta(days=activity_months * 30)
    headers = _build_headers(token)
    url: Optional[str] = (
        f"{GITHUB_API_BASE}/orgs/{org}/repos?type=public&per_page={per_page}"
    )

    discovered: List[Dict[str, Any]] = []
    pages_fetched = 0

    while url and pages_fetched < max_pages:
        logger.info("Fetching %s (page %d)", url, pages_fetched + 1)
        resp = requests.get(url, headers=headers, timeout=30)

        # Handle rate limiting
        _check_rate_limit(resp, rate_limiter)

        if resp.status_code == 404:
            logger.warning("Organization not found: %s", org)
            return []

        if resp.status_code != 200:
            raise ScannerError(
                f"GitHub API error {resp.status_code} for org '{org}': {resp.text[:200]}"
            )

        repos = resp.json()
        if not isinstance(repos, list):
            raise ScannerError(f"Unexpected response type for org '{org}': {type(repos)}")

        for repo in repos:
            full_name = repo.get("full_name", "")
            if full_name in seen_repos:
                logger.debug("Skipping already-seen repo: %s", full_name)
                continue

            # Skip archived, forks, empty repos
            if repo.get("archived", False):
                logger.debug("Skipping archived repo: %s", full_name)
                continue
            if repo.get("fork", False):
                logger.debug("Skipping fork: %s", full_name)
                continue
            if repo.get("size", 0) == 0:
                logger.debug("Skipping empty repo: %s", full_name)
                continue

            # Activity filter
            pushed_at_str = repo.get("pushed_at")
            if pushed_at_str:
                pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                if pushed_at < cutoff:
                    logger.debug("Skipping inactive repo: %s (pushed %s)", full_name, pushed_at_str)
                    continue

            discovered.append(_slim_repo(repo))

        # Follow pagination
        link_header = resp.headers.get("Link", "")
        links = _parse_link_header(link_header) if link_header else {}
        url = links.get("next")
        pages_fetched += 1

        if url:
            rate_limiter(rate_limit_delay_s)

    logger.info("Discovered %d repos from org '%s' (%d pages)", len(discovered), org, pages_fetched)
    return discovered


def scan_orgs(
    orgs: Sequence[str],
    *,
    token: Optional[str] = None,
    per_page: int = 100,
    max_pages: int = 10,
    activity_months: int = 12,
    rate_limit_delay_s: float = 1.0,
    rate_limiter: Callable[[float], None] = _default_rate_limiter,
    state_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Scan multiple GitHub organizations and persist state.

    Args:
        orgs: List of organization login names.
        token: GitHub API token.
        per_page: Repos per page.
        max_pages: Max pages per org.
        activity_months: Activity cutoff in months.
        rate_limit_delay_s: Delay between requests.
        rate_limiter: Mockable delay callable.
        state_dir: Directory for scan_state.json persistence.

    Returns:
        List of all discovered repo dicts across all orgs.
    """
    # Load existing state
    seen_repos: set = set()
    state_path: Optional[Path] = None
    if state_dir is not None:
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        state_path = state_dir / "scan_state.json"
        if state_path.exists():
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            seen_repos = set(state.get("seen_repos", []))
            logger.info("Loaded %d seen repos from state", len(seen_repos))

    all_repos: List[Dict[str, Any]] = []
    for org in orgs:
        repos = scan_org(
            org,
            token=token,
            per_page=per_page,
            max_pages=max_pages,
            activity_months=activity_months,
            rate_limit_delay_s=rate_limit_delay_s,
            rate_limiter=rate_limiter,
            seen_repos=seen_repos,
        )
        for r in repos:
            seen_repos.add(r["full_name"])
        all_repos.extend(repos)

    # Persist state
    if state_path is not None:
        state_data = {
            "seen_repos": sorted(seen_repos),
            "last_scan_ts": datetime.now(timezone.utc).isoformat(),
            "total_discovered": len(all_repos),
        }
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, sort_keys=True)
        logger.info("Persisted scan state to %s", state_path)

    return all_repos


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_headers(token: Optional[str]) -> Dict[str, str]:
    """Build HTTP headers for GitHub API requests."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _check_rate_limit(
    resp: requests.Response,
    rate_limiter: Callable[[float], None],
) -> None:
    """Check rate limit headers and handle 403 rate limit responses.

    If remaining requests are low (< 10), sleeps until the reset time.
    On 403 with rate limit indication, raises RateLimitError.
    """
    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset_at = resp.headers.get("X-RateLimit-Reset")

    if resp.status_code == 403:
        body_lower = resp.text.lower()
        if "rate limit" in body_lower or "api rate" in body_lower:
            if reset_at:
                wait_s = max(0, int(reset_at) - int(time.time())) + 1
                if wait_s <= 300:  # Only auto-wait up to 5 minutes
                    logger.warning("Rate limited. Waiting %d seconds.", wait_s)
                    rate_limiter(wait_s)
                    return
            raise RateLimitError(
                f"GitHub API rate limit exceeded. Reset at: {reset_at}"
            )

    if remaining is not None and int(remaining) < 10 and reset_at:
        wait_s = max(0, int(reset_at) - int(time.time())) + 1
        if wait_s <= 60:
            logger.info("Rate limit low (%s remaining). Sleeping %ds.", remaining, wait_s)
            rate_limiter(wait_s)

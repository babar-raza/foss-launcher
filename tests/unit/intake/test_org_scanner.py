"""Tests for the GitHub organization scanner.

Covers pagination, rate limiting, activity filtering, state persistence,
and error handling with fully mocked GitHub API responses.

TC: TC-2540, TC-2545
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.intake.org_scanner import (
    GITHUB_API_BASE,
    RateLimitError,
    ScannerError,
    _parse_link_header,
    _slim_repo,
    scan_org,
    scan_orgs,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic GitHub API v3 response payloads
# ---------------------------------------------------------------------------

def _make_repo(
    name: str = "MyRepo",
    full_name: str = "myorg/MyRepo",
    html_url: str = "https://github.com/myorg/MyRepo",
    stars: int = 10,
    language: str = "Python",
    archived: bool = False,
    fork: bool = False,
    is_template: bool = False,
    size: int = 500,
    pushed_at: str | None = None,
    license_spdx: str | None = "MIT",
    description: str = "A cool repo",
    topics: list | None = None,
) -> dict:
    """Build a realistic GitHub repo API response dict."""
    if pushed_at is None:
        pushed_at = datetime.now(timezone.utc).isoformat()
    license_obj = {"spdx_id": license_spdx, "name": license_spdx} if license_spdx else None
    return {
        "id": hash(full_name) % 10**8,
        "name": name,
        "full_name": full_name,
        "html_url": html_url,
        "description": description,
        "fork": fork,
        "archived": archived,
        "is_template": is_template,
        "size": size,
        "stargazers_count": stars,
        "language": language,
        "license": license_obj,
        "pushed_at": pushed_at,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": pushed_at,
        "default_branch": "main",
        "topics": topics or [],
        "owner": {"login": "myorg", "type": "Organization"},
    }


def _mock_response(
    json_data=None,
    status_code: int = 200,
    headers: dict | None = None,
    text: str = "",
):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.headers = headers or {}
    resp.text = text or json.dumps(json_data or [])
    return resp


# ---------------------------------------------------------------------------
# Tests: _parse_link_header
# ---------------------------------------------------------------------------


class TestParseLinkHeader:
    def test_single_next(self):
        header = '<https://api.github.com/orgs/foo/repos?page=2>; rel="next"'
        links = _parse_link_header(header)
        assert links == {"next": "https://api.github.com/orgs/foo/repos?page=2"}

    def test_multiple_links(self):
        header = (
            '<https://api.github.com/orgs/foo/repos?page=2>; rel="next", '
            '<https://api.github.com/orgs/foo/repos?page=5>; rel="last"'
        )
        links = _parse_link_header(header)
        assert links["next"] == "https://api.github.com/orgs/foo/repos?page=2"
        assert links["last"] == "https://api.github.com/orgs/foo/repos?page=5"

    def test_empty_header(self):
        assert _parse_link_header("") == {}


# ---------------------------------------------------------------------------
# Tests: _slim_repo
# ---------------------------------------------------------------------------


class TestSlimRepo:
    def test_extracts_expected_keys(self):
        repo = _make_repo()
        slim = _slim_repo(repo)
        assert slim["full_name"] == "myorg/MyRepo"
        assert slim["stargazers_count"] == 10
        assert slim["license"]["spdx_id"] == "MIT"
        assert slim["owner"]["login"] == "myorg"
        # Extra keys are dropped
        assert "clone_url" not in slim

    def test_flattens_license(self):
        repo = _make_repo(license_spdx="Apache-2.0")
        slim = _slim_repo(repo)
        assert slim["license"] == {"spdx_id": "Apache-2.0", "name": "Apache-2.0"}

    def test_no_license(self):
        repo = _make_repo(license_spdx=None)
        repo["license"] = None
        slim = _slim_repo(repo)
        assert slim.get("license") is None


# ---------------------------------------------------------------------------
# Tests: scan_org
# ---------------------------------------------------------------------------


class TestScanOrg:
    @patch("launch.intake.org_scanner.requests.get")
    def test_basic_scan(self, mock_get):
        repos = [_make_repo(name="RepoA", full_name="org1/RepoA")]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_org("org1", rate_limiter=lambda _: None)
        assert len(result) == 1
        assert result[0]["full_name"] == "org1/RepoA"

    @patch("launch.intake.org_scanner.requests.get")
    def test_skips_archived(self, mock_get):
        repos = [_make_repo(archived=True)]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_org("org1", rate_limiter=lambda _: None)
        assert len(result) == 0

    @patch("launch.intake.org_scanner.requests.get")
    def test_skips_forks(self, mock_get):
        repos = [_make_repo(fork=True)]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_org("org1", rate_limiter=lambda _: None)
        assert len(result) == 0

    @patch("launch.intake.org_scanner.requests.get")
    def test_skips_empty_repos(self, mock_get):
        repos = [_make_repo(size=0)]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_org("org1", rate_limiter=lambda _: None)
        assert len(result) == 0

    @patch("launch.intake.org_scanner.requests.get")
    def test_skips_inactive_repos(self, mock_get):
        old_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        repos = [_make_repo(pushed_at=old_date)]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_org("org1", activity_months=12, rate_limiter=lambda _: None)
        assert len(result) == 0

    @patch("launch.intake.org_scanner.requests.get")
    def test_skips_seen_repos(self, mock_get):
        repos = [_make_repo(full_name="org1/Seen")]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_org("org1", seen_repos={"org1/Seen"}, rate_limiter=lambda _: None)
        assert len(result) == 0

    @patch("launch.intake.org_scanner.requests.get")
    def test_pagination(self, mock_get):
        page1_repos = [_make_repo(name="A", full_name="org1/A")]
        page2_repos = [_make_repo(name="B", full_name="org1/B")]

        resp1 = _mock_response(
            json_data=page1_repos,
            headers={"Link": '<https://api.github.com/orgs/org1/repos?page=2>; rel="next"'},
        )
        resp2 = _mock_response(json_data=page2_repos)
        mock_get.side_effect = [resp1, resp2]

        result = scan_org("org1", rate_limiter=lambda _: None)
        assert len(result) == 2
        names = {r["full_name"] for r in result}
        assert names == {"org1/A", "org1/B"}

    @patch("launch.intake.org_scanner.requests.get")
    def test_max_pages_limit(self, mock_get):
        repos = [_make_repo(name="A", full_name="org1/A")]
        resp = _mock_response(
            json_data=repos,
            headers={"Link": '<https://api.github.com/orgs/org1/repos?page=2>; rel="next"'},
        )
        mock_get.return_value = resp

        result = scan_org("org1", max_pages=1, rate_limiter=lambda _: None)
        assert len(result) == 1
        assert mock_get.call_count == 1

    @patch("launch.intake.org_scanner.requests.get")
    def test_org_not_found(self, mock_get):
        mock_get.return_value = _mock_response(status_code=404)

        result = scan_org("nonexistent", rate_limiter=lambda _: None)
        assert result == []

    @patch("launch.intake.org_scanner.requests.get")
    def test_api_error_raises(self, mock_get):
        mock_get.return_value = _mock_response(
            status_code=500, text="Internal Server Error"
        )

        with pytest.raises(ScannerError, match="GitHub API error 500"):
            scan_org("org1", rate_limiter=lambda _: None)

    @patch("launch.intake.org_scanner.requests.get")
    def test_rate_limit_403_raises(self, mock_get):
        mock_get.return_value = _mock_response(
            status_code=403,
            text="API rate limit exceeded",
            headers={"X-RateLimit-Remaining": "0"},
        )

        with pytest.raises(RateLimitError):
            scan_org("org1", rate_limiter=lambda _: None)


# ---------------------------------------------------------------------------
# Tests: scan_orgs (state persistence)
# ---------------------------------------------------------------------------


class TestScanOrgs:
    @patch("launch.intake.org_scanner.requests.get")
    def test_persists_state(self, mock_get, tmp_path):
        repos = [_make_repo(name="R1", full_name="org1/R1")]
        mock_get.return_value = _mock_response(json_data=repos)

        result = scan_orgs(
            ["org1"],
            state_dir=tmp_path / "intake",
            rate_limiter=lambda _: None,
        )

        assert len(result) == 1
        state_path = tmp_path / "intake" / "scan_state.json"
        assert state_path.exists()
        with open(state_path) as f:
            state = json.load(f)
        assert "org1/R1" in state["seen_repos"]
        assert "last_scan_ts" in state

    @patch("launch.intake.org_scanner.requests.get")
    def test_incremental_scan_skips_seen(self, mock_get, tmp_path):
        # First scan
        repos = [_make_repo(name="R1", full_name="org1/R1")]
        mock_get.return_value = _mock_response(json_data=repos)
        scan_orgs(["org1"], state_dir=tmp_path / "intake", rate_limiter=lambda _: None)

        # Second scan -- same repos, should be skipped
        mock_get.return_value = _mock_response(json_data=repos)
        result = scan_orgs(["org1"], state_dir=tmp_path / "intake", rate_limiter=lambda _: None)
        assert len(result) == 0

    @patch("launch.intake.org_scanner.requests.get")
    def test_multiple_orgs(self, mock_get, tmp_path):
        repos1 = [_make_repo(name="A", full_name="org1/A")]
        repos2 = [_make_repo(name="B", full_name="org2/B")]
        mock_get.side_effect = [
            _mock_response(json_data=repos1),
            _mock_response(json_data=repos2),
        ]

        result = scan_orgs(
            ["org1", "org2"],
            state_dir=tmp_path / "intake",
            rate_limiter=lambda _: None,
        )
        assert len(result) == 2

"""Tests for HTTP client with network allowlist enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.clients.http import (
    NetworkBlockedError,
    _is_host_allowed,
    _load_allowlist,
    _validate_url,
)


@pytest.fixture
def allowlist_file(tmp_path: Path) -> Path:
    f = tmp_path / "allowlist.yaml"
    f.write_text(
        "allowed_hosts:\n"
        "  - localhost\n"
        "  - 127.0.0.1\n"
        "  - api.github.com\n"
        "  - '*.aspose.com'\n"
        "  - 'localhost:11434'\n",
        encoding="utf-8",
    )
    return f


class TestLoadAllowlist:
    def test_load_custom_allowlist(self, allowlist_file: Path) -> None:
        allowlist = _load_allowlist(allowlist_file)
        assert isinstance(allowlist, list)
        assert "localhost" in allowlist
        assert "api.github.com" in allowlist

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Network allowlist not found"):
            _load_allowlist(tmp_path / "nonexistent.yaml")


class TestIsHostAllowed:
    def test_exact_match(self) -> None:
        assert _is_host_allowed("localhost", ["localhost", "example.com"])

    def test_no_match(self) -> None:
        assert not _is_host_allowed("evil.com", ["localhost", "example.com"])

    def test_wildcard_match(self) -> None:
        assert _is_host_allowed("api.aspose.com", ["*.aspose.com"])
        assert _is_host_allowed("docs.aspose.com", ["*.aspose.com"])

    def test_wildcard_no_match(self) -> None:
        assert not _is_host_allowed("evil.com", ["*.aspose.com"])

    def test_host_port_exact(self) -> None:
        assert _is_host_allowed("localhost:11434", ["localhost:11434"])

    def test_host_port_hostname_only(self) -> None:
        assert _is_host_allowed("localhost:11434", ["localhost"])


class TestValidateUrl:
    def test_allowed_url(self, allowlist_file: Path) -> None:
        _validate_url("https://api.github.com/repos/test", allowlist_file)

    def test_blocked_url(self, allowlist_file: Path) -> None:
        with pytest.raises(NetworkBlockedError, match="Network request blocked"):
            _validate_url("https://evil.com/exfiltrate", allowlist_file)

    def test_blocked_has_host_attr(self, allowlist_file: Path) -> None:
        with pytest.raises(NetworkBlockedError) as exc_info:
            _validate_url("https://bad.example.org/data", allowlist_file)
        assert exc_info.value.host == "bad.example.org"

    def test_empty_url_raises(self, allowlist_file: Path) -> None:
        with pytest.raises(ValueError, match="Invalid URL"):
            _validate_url("", allowlist_file)

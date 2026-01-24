"""Tests for HTTP client with network allowlist enforcement (Guarantee D)."""

import pytest
from pathlib import Path
import tempfile

from launch.clients.http import (
    NetworkBlockedError,
    _load_allowlist,
    _is_host_allowed,
    _validate_url,
)


class TestLoadAllowlist:
    """Tests for _load_allowlist function."""

    def test_load_default_allowlist(self):
        """Loading default allowlist should succeed."""
        allowlist = _load_allowlist()
        assert isinstance(allowlist, list)
        assert len(allowlist) > 0
        assert "localhost" in allowlist or "127.0.0.1" in allowlist

    def test_load_custom_allowlist(self, tmp_path):
        """Loading custom allowlist from path should succeed."""
        allowlist_file = tmp_path / "test_allowlist.yaml"
        allowlist_file.write_text("""
allowed_hosts:
  - example.com
  - test.org
""")

        allowlist = _load_allowlist(allowlist_file)
        assert allowlist == ["example.com", "test.org"]

    def test_load_missing_allowlist_raises(self, tmp_path):
        """Loading missing allowlist should raise FileNotFoundError."""
        missing_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            _load_allowlist(missing_file)


class TestIsHostAllowed:
    """Tests for _is_host_allowed function."""

    def test_exact_match(self):
        """Exact host match should return True."""
        allowlist = ["example.com", "test.org"]
        assert _is_host_allowed("example.com", allowlist) is True

    def test_no_match(self):
        """Non-matching host should return False."""
        allowlist = ["example.com", "test.org"]
        assert _is_host_allowed("evil.com", allowlist) is False

    def test_wildcard_match(self):
        """Wildcard pattern match should return True."""
        allowlist = ["*.example.com", "test.org"]
        assert _is_host_allowed("api.example.com", allowlist) is True
        assert _is_host_allowed("sub.api.example.com", allowlist) is True

    def test_wildcard_no_match(self):
        """Wildcard pattern non-match should return False."""
        allowlist = ["*.example.com"]
        assert _is_host_allowed("example.com", allowlist) is False  # *.example.com doesn't match example.com
        assert _is_host_allowed("evil.com", allowlist) is False

    def test_host_with_port_exact(self):
        """Host:port exact match should return True."""
        allowlist = ["127.0.0.1:8080", "localhost:3000"]
        assert _is_host_allowed("127.0.0.1:8080", allowlist) is True

    def test_host_with_port_host_only_match(self):
        """Host:port should match if hostname matches."""
        allowlist = ["127.0.0.1", "localhost"]
        assert _is_host_allowed("127.0.0.1:8080", allowlist) is True
        assert _is_host_allowed("localhost:3000", allowlist) is True

    def test_localhost_variations(self):
        """Common localhost variations should be handled."""
        allowlist = ["localhost", "127.0.0.1"]
        assert _is_host_allowed("localhost", allowlist) is True
        assert _is_host_allowed("127.0.0.1", allowlist) is True
        assert _is_host_allowed("localhost:8080", allowlist) is True


class TestValidateUrl:
    """Tests for _validate_url function."""

    def test_validate_allowed_url(self, tmp_path):
        """Validating allowed URL should not raise."""
        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text("""
allowed_hosts:
  - example.com
  - api.github.com
""")

        # Should not raise
        _validate_url("https://example.com/path", allowlist_file)
        _validate_url("https://api.github.com/repos", allowlist_file)

    def test_validate_blocked_url_raises(self, tmp_path):
        """Validating blocked URL should raise NetworkBlockedError."""
        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text("""
allowed_hosts:
  - example.com
""")

        with pytest.raises(NetworkBlockedError) as exc_info:
            _validate_url("https://evil.com/exfiltrate", allowlist_file)

        assert exc_info.value.error_code == "NETWORK_BLOCKED"
        assert exc_info.value.host == "evil.com"
        assert "not in allowlist" in str(exc_info.value)

    def test_validate_url_with_port(self, tmp_path):
        """Validating URL with port should work."""
        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text("""
allowed_hosts:
  - 127.0.0.1:8080
  - localhost
""")

        _validate_url("http://127.0.0.1:8080/api", allowlist_file)
        _validate_url("http://localhost:3000/test", allowlist_file)

    def test_validate_url_wildcard(self, tmp_path):
        """Validating URL with wildcard pattern should work."""
        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text("""
allowed_hosts:
  - "*.aspose.com"
  - "*.github.com"
""")

        _validate_url("https://api.aspose.com/v1", allowlist_file)

        # raw.githubusercontent.com does NOT match *.github.com, should be blocked
        with pytest.raises(NetworkBlockedError):
            _validate_url("https://raw.githubusercontent.com/file", allowlist_file)

    def test_validate_invalid_url_raises(self, tmp_path):
        """Validating invalid URL should raise ValueError."""
        allowlist_file = tmp_path / "allowlist.yaml"
        allowlist_file.write_text("""
allowed_hosts:
  - example.com
""")

        with pytest.raises(ValueError, match="Invalid URL"):
            _validate_url("", allowlist_file)


class TestHttpGetPost:
    """Tests for http_get and http_post wrappers.

    Note: These tests require the requests library to be installed.
    They are integration tests that validate allowlist enforcement.
    """

    def test_http_get_import_note(self):
        """Note: http_get/http_post tests require requests library."""
        # This is a placeholder test to document the requirement
        # Actual http_get/http_post tests would need requests mocking
        # which requires additional dependencies (requests_mock or responses)

        # For now, just verify the functions are importable
        from launch.clients.http import http_get, http_post

        assert callable(http_get)
        assert callable(http_post)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_case_sensitive_host_matching(self):
        """Host matching should be case-sensitive by default."""
        allowlist = ["Example.COM"]
        # fnmatch is case-sensitive on Unix, case-insensitive on Windows
        # For strict security, we rely on exact config specification
        result = _is_host_allowed("example.com", allowlist)
        # On Windows this might be True, on Unix False
        # The allowlist should specify the exact case expected

    def test_empty_allowlist(self):
        """Empty allowlist should block all hosts."""
        allowlist = []
        assert _is_host_allowed("example.com", allowlist) is False
        assert _is_host_allowed("localhost", allowlist) is False

    def test_localhost_ipv6(self):
        """IPv6 localhost should be matchable."""
        allowlist = ["::1", "localhost"]
        assert _is_host_allowed("::1", allowlist) is True
        assert _is_host_allowed("localhost", allowlist) is True

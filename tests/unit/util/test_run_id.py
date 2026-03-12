"""Tests for launcher.util.run_id — format, uniqueness, and sanitization."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from launcher.util.run_id import generate_run_id, _sanitize_slug

# Format: YYMMDD_HHMMSS_{family}_{platform}_{hex4}
_RUN_ID_RE = re.compile(r"^\d{6}_\d{6}_[a-z0-9-]+_[a-z0-9-]+_[0-9a-f]{4}$")


class TestSanitizeSlug:
    def test_lowercase(self) -> None:
        assert _sanitize_slug("Cells") == "cells"

    def test_strips_aspose_prefix(self) -> None:
        assert _sanitize_slug("aspose-cells") == "cells"
        assert _sanitize_slug("Aspose-Note") == "note"

    def test_replaces_non_alnum(self) -> None:
        assert _sanitize_slug("foo.bar") == "foo-bar"

    def test_truncates(self) -> None:
        assert len(_sanitize_slug("a" * 30)) == 16

    def test_strips_leading_trailing_dashes(self) -> None:
        assert _sanitize_slug("-foo-") == "foo"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            _sanitize_slug("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            _sanitize_slug("   ")

    def test_special_chars_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            _sanitize_slug("---")

    def test_all_digits_valid(self) -> None:
        assert _sanitize_slug("12345") == "12345"

    def test_mixed_special(self) -> None:
        assert _sanitize_slug("foo.bar_baz") == "foo-bar-baz"


class TestGenerateRunIdFormat:
    def test_matches_regex(self) -> None:
        rid = generate_run_id("cells", "python")
        assert _RUN_ID_RE.match(rid), f"Unexpected format: {rid}"

    def test_contains_family_and_platform(self) -> None:
        rid = generate_run_id("cells", "python")
        assert "_cells_python_" in rid

    def test_date_component_matches_utc(self) -> None:
        frozen = datetime(2026, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        with patch("launcher.util.run_id.datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            rid = generate_run_id("cells", "python")
        assert rid.startswith("260115_235959_")

    def test_aspose_prefix_stripped(self) -> None:
        rid = generate_run_id("aspose-cells", "python")
        assert "_cells_" in rid
        assert "aspose" not in rid

    def test_two_calls_same_second_differ(self) -> None:
        """Hex suffix makes same-second calls very likely unique."""
        frozen = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        with patch("launcher.util.run_id.datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            ids = {generate_run_id("cells", "python") for _ in range(20)}
        # 20 draws from 65K space: collision prob < 0.3%
        assert len(ids) == 20, f"Only {len(ids)} unique out of 20 same-second calls"

    def test_uniqueness_across_families(self) -> None:
        frozen = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        with patch("launcher.util.run_id.datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            a = generate_run_id("cells", "python")
            b = generate_run_id("note", "python")
        assert a != b


class TestInputValidation:
    def test_empty_family_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            generate_run_id("", "python")

    def test_empty_platform_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            generate_run_id("cells", "")

    def test_whitespace_family_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            generate_run_id("  ", "python")

    def test_special_only_family_raises(self) -> None:
        with pytest.raises(ValueError, match="empty string"):
            generate_run_id("---", "python")

    def test_long_family_truncated_but_valid(self) -> None:
        rid = generate_run_id("a" * 30, "python")
        # Family slug truncated to 16 chars
        parts = rid.split("_")
        # parts: [date, time, family, platform, hex]
        assert len(parts[2]) == 16


class TestCollisionGuard:
    """Verify that call sites retry on directory collision."""

    def test_retry_skips_existing_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()

        first_id = generate_run_id("cells", "python")
        (runs / first_id).mkdir()

        call_count = 0
        original = generate_run_id

        def mock_generate(family: str, platform: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return first_id
            return original(family, platform)

        with patch("launcher.util.run_id.generate_run_id", side_effect=mock_generate):
            for _attempt in range(3):
                run_id = mock_generate("cells", "python")
                run_dir = runs / run_id
                if not run_dir.exists():
                    break
            else:
                pytest.fail("Retry loop exhausted")

        assert call_count == 2
        assert run_id != first_id

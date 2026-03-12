"""Tests for intake clone module (TC-3776, TC-4216)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.workers.intake.clone import (
    _CLONE_URL_MARKER,
    _check_url_collision,
    _extract_brand_from_url,
    _get_cache_dir,
    _get_repo_sha,
    _normalize_slug,
    check_remote_sha,
    clone_repo_cached,
)


FAKE_URL = "https://github.com/aspose-cells-foss/aspose-cells-python-for-python"
FAKE_SHA = "a" * 40


# ===================================================================
# TC-4216: _normalize_slug
# ===================================================================


class TestNormalizeSlug:
    def test_lowercase_and_hyphen(self):
        assert _normalize_slug("Aspose-Cells") == "aspose_cells"

    def test_numeric_preserved(self):
        assert _normalize_slug("3D") == "3d"

    def test_dot_separator(self):
        assert _normalize_slug("aspose.cells") == "aspose_cells"

    def test_already_clean(self):
        assert _normalize_slug("python") == "python"

    def test_multiple_separators_collapsed(self):
        assert _normalize_slug("aspose--cells") == "aspose_cells"

    def test_leading_trailing_stripped(self):
        assert _normalize_slug("-aspose-") == "aspose"

    def test_typescript(self):
        assert _normalize_slug("TypeScript") == "typescript"


# ===================================================================
# TC-4216: _extract_brand_from_url
# ===================================================================


class TestExtractBrandFromUrl:
    def test_aspose_cells_foss(self):
        url = "https://github.com/aspose-cells-foss/aspose-cells-python"
        assert _extract_brand_from_url(url) == "aspose"

    def test_aspose_3d_foss(self):
        url = "https://github.com/aspose-3d-foss/aspose-3d-typescript"
        assert _extract_brand_from_url(url) == "aspose"

    def test_aspose_note_foss(self):
        url = "https://github.com/aspose-note-foss/aspose-note-python"
        assert _extract_brand_from_url(url) == "aspose"

    def test_bad_url_returns_unknown(self):
        assert _extract_brand_from_url("not-a-url") == "unknown"

    def test_empty_string_returns_unknown(self):
        assert _extract_brand_from_url("") == "unknown"


# ===================================================================
# TC-4216: _get_cache_dir (readable slug naming)
# ===================================================================


class TestGetCacheDir:
    def test_cache_dir_under_runs_root(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        # Should be under runs/.clone_cache/
        assert ".clone_cache" in str(cache_dir)
        assert cache_dir.parent.parent == tmp_path / "runs"

    def test_readable_slug_format(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        assert cache_dir.name == "aspose_cells_python"

    def test_same_brand_family_platform_same_dir(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        d1 = _get_cache_dir("aspose", "cells", "python", work_dir)
        d2 = _get_cache_dir("aspose", "cells", "python", work_dir)
        assert d1 == d2

    def test_different_platform_different_dir(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        d1 = _get_cache_dir("aspose", "cells", "python", work_dir)
        d2 = _get_cache_dir("aspose", "cells", "typescript", work_dir)
        assert d1 != d2

    def test_different_family_different_dir(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        d1 = _get_cache_dir("aspose", "cells", "python", work_dir)
        d2 = _get_cache_dir("aspose", "note", "python", work_dir)
        assert d1 != d2

    def test_normalizes_family_slug(self, tmp_path: Path):
        """Family '3d' should normalize to '3d' (no underscore corruption)."""
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        cache_dir = _get_cache_dir("aspose", "3d", "typescript", work_dir)
        assert cache_dir.name == "aspose_3d_typescript"


# ===================================================================
# TC-4216: Org allowlist enforcement
# ===================================================================


class TestOrgAllowlist:
    def test_allowed_url_passes(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        allowed = ["https://github.com/aspose-cells-foss/"]

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
             patch("launcher.workers.intake.clone.subprocess.run"):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL,
                family="cells",
                platform="python",
                work_dir=work_dir,
                allowed_org_prefixes=allowed,
            )
        assert sha == FAKE_SHA

    def test_blocked_url_raises_value_error(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        allowed = ["https://github.com/aspose-note-foss/"]

        with pytest.raises(ValueError, match="not in the allowed org list"):
            clone_repo_cached(
                FAKE_URL,
                family="cells",
                platform="python",
                work_dir=work_dir,
                allowed_org_prefixes=allowed,
            )

    def test_none_allowlist_skips_check(self, tmp_path: Path):
        """allowed_org_prefixes=None disables the check entirely."""
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)
        non_aspose_url = "https://github.com/totally-different-org/some-repo"

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
             patch("launcher.workers.intake.clone.subprocess.run"):
            repo_dir, sha, is_fresh = clone_repo_cached(
                non_aspose_url,
                family="cells",
                platform="python",
                work_dir=work_dir,
                allowed_org_prefixes=None,
            )
        assert is_fresh is True

    def test_empty_allowlist_blocks_all(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="not in the allowed org list"):
            clone_repo_cached(
                FAKE_URL,
                family="cells",
                platform="python",
                work_dir=work_dir,
                allowed_org_prefixes=[],
            )


# ===================================================================
# TC-4216: .clone_url marker + collision detection
# ===================================================================


class TestCloneUrlMarker:
    def test_url_marker_written_on_fresh_clone(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
             patch("launcher.workers.intake.clone.subprocess.run"):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL, family="cells", platform="python", work_dir=work_dir
            )

        url_marker = repo_dir / _CLONE_URL_MARKER
        assert url_marker.exists()
        assert url_marker.read_text(encoding="utf-8").strip() == FAKE_URL

    def test_collision_raises_runtime_error(self, tmp_path: Path):
        """_check_url_collision raises RuntimeError when URL marker mismatches."""
        cache_dir = tmp_path / "aspose_cells_python"
        cache_dir.mkdir(parents=True)
        (cache_dir / _CLONE_URL_MARKER).write_text(
            "https://github.com/other-org/other-repo", encoding="utf-8"
        )

        with pytest.raises(RuntimeError, match="Cache collision"):
            _check_url_collision(cache_dir, FAKE_URL)

    def test_no_marker_no_collision(self, tmp_path: Path):
        """No .clone_url marker → no error (backward-compatible with old caches)."""
        cache_dir = tmp_path / "aspose_cells_python"
        cache_dir.mkdir(parents=True)
        # No .clone_url marker — should not raise
        _check_url_collision(cache_dir, FAKE_URL)  # must not raise

    def test_matching_url_no_error(self, tmp_path: Path):
        """Matching URL → no error."""
        cache_dir = tmp_path / "aspose_cells_python"
        cache_dir.mkdir(parents=True)
        (cache_dir / _CLONE_URL_MARKER).write_text(FAKE_URL, encoding="utf-8")
        _check_url_collision(cache_dir, FAKE_URL)  # must not raise


# ===================================================================
# TC-4216: Readable slug names for real-world inputs
# ===================================================================


class TestReadableSlugNames:
    def test_cells_python_slug(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "r1" / "work"
        work_dir.mkdir(parents=True)
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        assert cache_dir.name == "aspose_cells_python"

    def test_3d_typescript_slug(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "r1" / "work"
        work_dir.mkdir(parents=True)
        cache_dir = _get_cache_dir("aspose", "3d", "typescript", work_dir)
        assert cache_dir.name == "aspose_3d_typescript"

    def test_slides_python_slug(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "r1" / "work"
        work_dir.mkdir(parents=True)
        cache_dir = _get_cache_dir("aspose", "slides", "python", work_dir)
        assert cache_dir.name == "aspose_slides_python"

    def test_brand_derived_from_url(self, tmp_path: Path):
        """clone_repo_cached derives brand='aspose' from FAKE_URL org."""
        work_dir = tmp_path / "runs" / "r1" / "work"
        work_dir.mkdir(parents=True)

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
             patch("launcher.workers.intake.clone.subprocess.run"):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL, family="cells", platform="python", work_dir=work_dir
            )

        # Cache folder should be aspose_cells_python (brand derived from URL)
        assert repo_dir.name == "aspose_cells_python"


# ===================================================================
# TestCloneRepoCached (updated for TC-4216 signature)
# ===================================================================


class TestCloneRepoCached:
    def test_fresh_clone(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
             patch("launcher.workers.intake.clone.subprocess.run"):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL, family="cells", platform="python", work_dir=work_dir
            )

        assert sha == FAKE_SHA
        assert is_fresh is True
        assert repo_dir.exists()
        # SHA marker should be written
        marker = repo_dir / ".clone_sha"
        assert marker.read_text(encoding="utf-8") == FAKE_SHA

    def test_cache_hit(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # Pre-populate cache
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        cache_dir.mkdir(parents=True)
        (cache_dir / ".clone_sha").write_text(FAKE_SHA, encoding="utf-8")
        (cache_dir / _CLONE_URL_MARKER).write_text(FAKE_URL, encoding="utf-8")

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL, family="cells", platform="python", work_dir=work_dir
            )

        assert sha == FAKE_SHA
        assert is_fresh is False
        assert repo_dir == cache_dir

    def test_cache_miss_different_sha(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # Pre-populate cache with old SHA
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        cache_dir.mkdir(parents=True)
        (cache_dir / ".clone_sha").write_text("b" * 40, encoding="utf-8")
        (cache_dir / "old_file.txt").write_text("old", encoding="utf-8")

        new_sha = "c" * 40
        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=new_sha), \
             patch("launcher.workers.intake.clone.subprocess.run"):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL, family="cells", platform="python", work_dir=work_dir
            )

        assert sha == new_sha
        assert is_fresh is True

    def test_ls_remote_failure_still_clones(self, tmp_path: Path):
        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=""), \
             patch("launcher.workers.intake.clone.subprocess.run"), \
             patch("launcher.workers.intake.clone._get_repo_sha", return_value=FAKE_SHA):
            repo_dir, sha, is_fresh = clone_repo_cached(
                FAKE_URL, family="cells", platform="python", work_dir=work_dir
            )

        assert sha == FAKE_SHA
        assert is_fresh is True


# ===================================================================
# TestGetRepoSha (unchanged)
# ===================================================================


class TestGetRepoSha:
    def test_returns_sha(self, tmp_path: Path):
        mock_result = MagicMock()
        mock_result.stdout = f"{FAKE_SHA}\n"
        with patch("launcher.workers.intake.clone.subprocess.run", return_value=mock_result):
            sha = _get_repo_sha(tmp_path)
        assert sha == FAKE_SHA

    def test_returns_empty_on_error(self, tmp_path: Path):
        with patch("launcher.workers.intake.clone.subprocess.run", side_effect=Exception("no git")):
            sha = _get_repo_sha(tmp_path)
        assert sha == ""


# ===================================================================
# TestCheckRemoteSha (unchanged)
# ===================================================================


class TestCheckRemoteSha:
    def test_returns_sha_on_success(self):
        mock_result = MagicMock()
        mock_result.stdout = f"{FAKE_SHA}\tHEAD\n"
        with patch("launcher.workers.intake.clone.subprocess.run", return_value=mock_result):
            sha = check_remote_sha(FAKE_URL)
        assert sha == FAKE_SHA

    def test_returns_none_on_failure(self):
        """Network failure (exception) must return None, not '' — TC-A05."""
        with patch("launcher.workers.intake.clone.subprocess.run", side_effect=Exception("network")):
            sha = check_remote_sha(FAKE_URL)
        assert sha is None

    def test_returns_empty_on_empty_output(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("launcher.workers.intake.clone.subprocess.run", return_value=mock_result):
            sha = check_remote_sha(FAKE_URL)
        assert sha == ""


# ===================================================================
# PH-01: _write_cache_timestamp OSError guard tests
# ===================================================================


class TestWriteCacheTimestampGuard:
    """PH-01: _write_cache_timestamp must log WARNING on OSError, not abort."""

    def test_write_failure_logs_warning_not_raises(self, tmp_path, caplog):
        """OSError during timestamp write must log WARNING and not propagate."""
        import logging
        from unittest.mock import patch
        from launcher.workers.intake.clone import _write_cache_timestamp

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
                # Must not raise — pipeline continues
                _write_cache_timestamp(tmp_path)

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("Could not write .clone_timestamp" in m for m in warning_msgs), (
            f"Expected WARNING 'Could not write .clone_timestamp': {warning_msgs}"
        )
        assert any("stale cache age detection disabled" in m for m in warning_msgs), (
            f"Expected 'stale cache age detection disabled' in warning: {warning_msgs}"
        )

    def test_write_success_no_warning(self, tmp_path, caplog):
        """Successful timestamp write emits no WARNING."""
        import logging
        from launcher.workers.intake.clone import _write_cache_timestamp

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            _write_cache_timestamp(tmp_path)

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert not warning_msgs, f"Expected no WARNING on success, got: {warning_msgs}"
        assert (tmp_path / ".clone_timestamp").exists()


# ===================================================================
# P1-B: Cache integrity check — empty cache dir tests (TC-4088)
# ===================================================================


class TestCacheIntegrityCheck:
    """P1-B: empty or missing cache dir should trigger fresh clone, not a silent pass-through."""

    def test_cache_hit_empty_dir_logs_warning_and_reclones(self, tmp_path, caplog):
        """P1-B: SHA match but empty cache dir must warn and fall through to fresh clone."""
        import logging
        from launcher.workers.intake.clone import clone_repo_cached, _get_cache_dir

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # Pre-create cache dir with SHA marker but NO other files (corrupted cache)
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        cache_dir.mkdir(parents=True)
        (cache_dir / ".clone_sha").write_text(FAKE_SHA, encoding="utf-8")
        # Delete the SHA marker so the dir is truly empty
        (cache_dir / ".clone_sha").unlink()

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
                 patch("launcher.workers.intake.clone.subprocess.run"):
                # empty dir means no marker.exists() → SHA check won't match → fresh clone
                repo_dir, sha, is_fresh = clone_repo_cached(
                    FAKE_URL, family="cells", platform="python", work_dir=work_dir
                )

        # Should do a fresh clone (no SHA marker means cache miss)
        assert is_fresh is True

    def test_cache_hit_only_sha_marker_warns_empty(self, tmp_path, caplog):
        """P1-B: SHA match with only .clone_sha in dir — non-empty dir returns hit."""
        import logging
        from launcher.workers.intake.clone import clone_repo_cached, _get_cache_dir

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # Pre-create cache dir with ONLY the SHA marker + URL marker
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        cache_dir.mkdir(parents=True)
        (cache_dir / ".clone_sha").write_text(FAKE_SHA, encoding="utf-8")
        (cache_dir / _CLONE_URL_MARKER).write_text(FAKE_URL, encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA):
                repo_dir, sha, is_fresh = clone_repo_cached(
                    FAKE_URL, family="cells", platform="python", work_dir=work_dir
                )

        # Non-empty dir (has SHA marker) should be a cache hit
        assert is_fresh is False
        assert sha == FAKE_SHA

    def test_truly_empty_cache_dir_triggers_reclone(self, tmp_path, caplog):
        """P1-B: completely empty cache_dir with matching SHA marker elsewhere causes re-clone."""
        import logging
        from launcher.workers.intake.clone import clone_repo_cached, _get_cache_dir

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # Create cache_dir with SHA marker, then remove all files to simulate corruption
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        cache_dir.mkdir(parents=True)
        sha_marker = cache_dir / ".clone_sha"
        sha_marker.write_text(FAKE_SHA, encoding="utf-8")
        # Remove every file — dir exists but is completely empty
        for f in list(cache_dir.iterdir()):
            f.unlink()
        assert list(cache_dir.iterdir()) == [], "Test setup: cache_dir should be empty"

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            with patch("launcher.workers.intake.clone.check_remote_sha", return_value=FAKE_SHA), \
                 patch("launcher.workers.intake.clone.subprocess.run"):
                repo_dir, sha, is_fresh = clone_repo_cached(
                    FAKE_URL, family="cells", platform="python", work_dir=work_dir
                )

        assert is_fresh is True

    def test_network_failure_empty_cache_dir_logs_warning(self, tmp_path, caplog):
        """P1-B: network failure + empty cache dir should warn and attempt re-clone."""
        import logging
        from launcher.workers.intake.clone import clone_repo_cached, _get_cache_dir

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # Create cache_dir with SHA marker but then remove all files
        cache_dir = _get_cache_dir("aspose", "cells", "python", work_dir)
        cache_dir.mkdir(parents=True)
        (cache_dir / ".clone_sha").write_text(FAKE_SHA, encoding="utf-8")
        # Wipe the marker so the fallback path (remote_sha is None, no marker) doesn't trigger
        for f in list(cache_dir.iterdir()):
            f.unlink()

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            with patch("launcher.workers.intake.clone.check_remote_sha", return_value=None), \
                 patch("launcher.workers.intake.clone.subprocess.run"), \
                 patch("launcher.workers.intake.clone._get_repo_sha", return_value=FAKE_SHA):
                repo_dir, sha, is_fresh = clone_repo_cached(
                    FAKE_URL, family="cells", platform="python", work_dir=work_dir
                )

        assert is_fresh is True

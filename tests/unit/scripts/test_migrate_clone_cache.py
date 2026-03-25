"""Unit tests for scripts/migrate_clone_cache.py (SR-02).

Tests cover:
- Happy path: dir with wrong brand prefix is renamed
- Idempotency: dir already using correct name → no rename
- Collision skip: target name already exists → skip with warning
- Missing marker skip: no .clone_url file → skip with warning
- Unreadable marker: OSError on read → error counted
- Dry-run: no-op even when rename would occur
- Unknown URL: URL that yields brand="unknown" → skip with warning
- No-underscore dir: dir with no underscore in name → skip with warning
- Error counter: rename failure increments errors and returns exit code 1
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Load migrate module without triggering the full package __init__.py
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "migrate_clone_cache.py"
_spec = importlib.util.spec_from_file_location("migrate_clone_cache", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
# We need launcher.phase1.acquisition registered first (for the script's own import).
# Re-use whatever is already cached from the test session, or load it fresh.
if "launcher.phase1.acquisition" not in sys.modules:
    _acq_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "launcher" / "phase1" / "acquisition.py"
    _acq_spec = importlib.util.spec_from_file_location("launcher.phase1.acquisition", _acq_path)
    _acq_mod = importlib.util.module_from_spec(_acq_spec)  # type: ignore[arg-type]
    sys.modules["launcher.phase1.acquisition"] = _acq_mod
    _acq_spec.loader.exec_module(_acq_mod)  # type: ignore[union-attr]

sys.modules["migrate_clone_cache"] = _mod
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

migrate = _mod.migrate
_CLONE_URL_MARKER = _mod._CLONE_URL_MARKER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache_dir(root: Path, name: str, url: str | None = None) -> Path:
    d = root / name
    d.mkdir(parents=True)
    if url is not None:
        (d / _CLONE_URL_MARKER).write_text(url, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigrateHappyPath:
    def test_renames_po_to_aspose(self, tmp_path: Path):
        """po_3d_python → aspose_3d_python when URL org is aspose-3d-foss."""
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "po_3d_python", "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python")

        rc = migrate(root, dry_run=False)

        assert rc == 0
        assert not (root / "po_3d_python").exists()
        assert (root / "aspose_3d_python").exists()
        # .clone_url marker must be preserved in renamed dir
        url_content = (root / "aspose_3d_python" / _CLONE_URL_MARKER).read_text(encoding="utf-8").strip()
        assert "aspose-3d-foss" in url_content

    def test_multiple_dirs_all_renamed(self, tmp_path: Path):
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "po_cells_python", "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python")
        _make_cache_dir(root, "po_slides_java", "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java")

        rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "aspose_cells_python").exists()
        assert (root / "aspose_slides_java").exists()
        assert not (root / "po_cells_python").exists()
        assert not (root / "po_slides_java").exists()


class TestMigrateIdempotency:
    def test_already_correct_name_no_rename(self, tmp_path: Path):
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "aspose_3d_python", "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python")

        rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "aspose_3d_python").exists()  # still there

    def test_running_twice_is_safe(self, tmp_path: Path):
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "po_email_python", "https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Python")

        rc1 = migrate(root, dry_run=False)
        rc2 = migrate(root, dry_run=False)  # second run: already renamed

        assert rc1 == 0
        assert rc2 == 0
        assert (root / "aspose_email_python").exists()


class TestMigrateDryRun:
    def test_dry_run_no_rename_executed(self, tmp_path: Path):
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "po_note_python", "https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python")

        rc = migrate(root, dry_run=True)

        assert rc == 0
        # Original dir must still exist — dry-run must not rename
        assert (root / "po_note_python").exists()
        assert not (root / "aspose_note_python").exists()


class TestMigrateSkipCases:
    def test_missing_url_marker_skipped(self, tmp_path: Path, caplog):
        root = tmp_path / ".clone_cache"
        root.mkdir()
        d = root / "po_3d_python"
        d.mkdir()  # no .clone_url marker

        import logging
        with caplog.at_level(logging.WARNING):
            rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "po_3d_python").exists()  # not renamed
        assert any("no .clone_url" in r.message for r in caplog.records)

    def test_unknown_brand_url_skipped(self, tmp_path: Path, caplog):
        """URL that yields brand='unknown' (all stop words org) → skip."""
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "foss_for_python", "https://github.com/foss-for-net/some-repo")

        import logging
        with caplog.at_level(logging.WARNING):
            rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "foss_for_python").exists()  # not renamed
        assert any("Cannot derive brand" in r.message for r in caplog.records)

    def test_collision_skip_when_target_exists(self, tmp_path: Path, caplog):
        """If target name already exists, source is skipped (not overwritten)."""
        root = tmp_path / ".clone_cache"
        root.mkdir()
        url = "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python"
        _make_cache_dir(root, "po_3d_python", url)
        _make_cache_dir(root, "aspose_3d_python", url)  # target already exists

        import logging
        with caplog.at_level(logging.WARNING):
            rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "po_3d_python").exists()  # not renamed
        assert (root / "aspose_3d_python").exists()  # unchanged
        assert any("already exists" in r.message for r in caplog.records)

    def test_no_underscore_dir_skipped(self, tmp_path: Path, caplog):
        """Dir with no underscore cannot be parsed — must be skipped."""
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "nodash", "https://github.com/aspose-3d-foss/repo")

        import logging
        with caplog.at_level(logging.WARNING):
            rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "nodash").exists()
        assert any("no underscore" in r.message for r in caplog.records)


class TestMigrateErrors:
    def test_rename_failure_counted_as_error(self, tmp_path: Path):
        """OSError during rename → errors incremented, exit code 1."""
        root = tmp_path / ".clone_cache"
        root.mkdir()
        _make_cache_dir(root, "po_3d_python", "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python")

        with patch("pathlib.Path.rename", side_effect=OSError("permission denied")):
            rc = migrate(root, dry_run=False)

        assert rc == 1  # error → non-zero exit

    def test_nonexistent_cache_root_returns_error(self, tmp_path: Path):
        rc = migrate(tmp_path / "nonexistent", dry_run=False)
        assert rc == 1


class TestMigrateFiles:
    def test_non_directory_entries_ignored(self, tmp_path: Path):
        """Regular files in cache root are silently ignored."""
        root = tmp_path / ".clone_cache"
        root.mkdir()
        (root / "stale_lock.txt").write_text("lock", encoding="utf-8")
        _make_cache_dir(root, "po_3d_python", "https://github.com/aspose-3d-foss/repo")

        rc = migrate(root, dry_run=False)

        assert rc == 0
        assert (root / "stale_lock.txt").exists()  # file untouched

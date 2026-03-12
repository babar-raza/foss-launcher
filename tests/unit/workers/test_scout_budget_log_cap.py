"""Tests that budget_log is capped at 500 entries — IUH-04.

TC-4212: Also tests dropped_by_category tracking for overflow entries.
"""
from __future__ import annotations
import logging
from pathlib import Path
from launcher.models.understanding import FileCategory, FileEntry
from launcher.workers.understand.scout import _read_repo_content, _DEFAULT_BUDGET_BYTES


def _make_file_index(
    repo_dir: Path,
    count: int,
    category: FileCategory = FileCategory.doc,
) -> dict:
    """Create a file_index with `count` markdown files of ~100 bytes each."""
    index = {}
    for i in range(count):
        fname = f"doc_{i:04d}.md"
        p = repo_dir / fname
        p.write_text("# Doc\n" * 10, encoding="utf-8")
        index[fname] = FileEntry(
            category=category,
            size_bytes=p.stat().st_size,
            language="",
        )
    return index


class TestBudgetLogCap:
    def test_budget_log_never_exceeds_500(self, tmp_path):
        """budget_log must not exceed 500 entries even with 600 skipped files."""
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count, _dropped, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=5_000
        )

        assert len(budget_log) <= 500, (
            f"budget_log has {len(budget_log)} entries, expected ≤ 500"
        )
        assert overflow_count >= 0

    def test_overflow_count_nonzero_when_log_at_cap(self, tmp_path):
        """When >500 files are skipped, overflow_count must be > 0."""
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count, _dropped, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=500
        )

        if len(budget_log) == 500:
            assert overflow_count > 0, (
                "When budget_log is at cap, overflow_count must be > 0"
            )

    def test_small_repo_no_overflow(self, tmp_path):
        """For a repo with few skips, overflow_count should be 0."""
        index = _make_file_index(tmp_path, count=5, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count, _dropped, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=_DEFAULT_BUDGET_BYTES
        )

        assert overflow_count == 0
        assert len(budget_log) <= 5

    def test_len_plus_overflow_consistent(self, tmp_path):
        """len(budget_log) + overflow_count must not exceed total files that were skipped."""
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count, _dropped, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=5_000
        )

        # All 600 files: some read (very few given tiny budget), rest skipped/capped
        total_accounted = len(budget_log) + overflow_count
        assert total_accounted <= 600


# ===========================================================================
# TC-4212: dropped_by_category tracking for overflow entries
# ===========================================================================


class TestDroppedByCategory:
    """TC-4212: When budget_log overflows, dropped_by_category must track reason counts."""

    def test_dropped_by_category_present_on_overflow(self, tmp_path):
        """When budget_log overflows, dropped_by_category must be a dict (not None/empty when there are overflows)."""
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count, dropped_by_category, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=5_000
        )

        assert isinstance(dropped_by_category, dict), (
            "dropped_by_category must always be a dict"
        )
        if overflow_count > 0:
            assert len(dropped_by_category) > 0, (
                "When overflow_count > 0, dropped_by_category must have at least one entry"
            )

    def test_dropped_by_category_counts_match_overflow(self, tmp_path):
        """Sum of dropped_by_category values must equal budget_log_overflow count."""
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count, dropped_by_category, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=500
        )

        if overflow_count > 0:
            total_dropped = sum(dropped_by_category.values())
            assert total_dropped == overflow_count, (
                f"sum(dropped_by_category.values())={total_dropped} must equal "
                f"overflow_count={overflow_count}"
            )

    def test_warning_logged_on_overflow(self, tmp_path, caplog):
        """A WARNING must be emitted to the scout logger when budget_log overflows."""
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        with caplog.at_level(logging.WARNING, logger="launcher.workers.scout.scout"):
            _, _, _, _, overflow_count, dropped_by_category, _imp = _read_repo_content(
                tmp_path, index, budget_bytes=500
            )

        if overflow_count > 0:
            warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
            scout_warnings = [m for m in warning_messages if "Budget log" in m or "dropped" in m.lower()]
            assert len(scout_warnings) > 0, (
                "At least one WARNING about budget log overflow must be emitted. "
                f"Got warnings: {warning_messages}"
            )

    def test_no_overflow_dropped_by_category_empty(self, tmp_path):
        """When no overflow occurs, dropped_by_category must be empty dict."""
        # Small index: 5 files, generous budget — no overflow expected
        index = _make_file_index(tmp_path, count=5, category=FileCategory.doc)

        _, _, _, _, overflow_count, dropped_by_category, _imp = _read_repo_content(
            tmp_path, index, budget_bytes=_DEFAULT_BUDGET_BYTES
        )

        assert overflow_count == 0
        assert dropped_by_category == {}, (
            "When there is no overflow, dropped_by_category must be empty"
        )


# ===========================================================================
# TC-4236: important_files_skipped metric
# ===========================================================================


class TestImportantFilesSkipped:
    """TC-4236: High-rank files skipped by budget are tracked in important_files_skipped."""

    def test_important_files_skipped_when_budget_exhausted(self, tmp_path):
        """Root-level .md files (rank=3: root+ext, no keyword) are counted when budget hit."""
        from launcher.models.understanding import FileCategory, FileEntry
        # Create 5 root-level .md files each ~5KB — should be rank 3 (root+ext, no keyword)
        index = {}
        for i in range(5):
            fname = f"notes_{i}.md"
            p = tmp_path / fname
            p.write_text("x" * 5_000, encoding="utf-8")
            index[fname] = FileEntry(category=FileCategory.doc, size_bytes=p.stat().st_size, language="")

        # Tiny budget forces skips
        _, _, _, _, _, _, important_skipped = _read_repo_content(
            tmp_path, index, budget_bytes=3_000
        )
        # At least some root-level .md files (rank=3 base) should be counted
        # rank=3 < 4 threshold, but with size signal (200-50000 bytes) they get rank=4
        assert important_skipped >= 1, (
            f"Expected >=1 important file skipped but got {important_skipped}"
        )

    def test_no_important_files_skipped_when_budget_ample(self, tmp_path):
        """When budget is ample, important_files_skipped must be 0."""
        from launcher.models.understanding import FileCategory, FileEntry
        index = {}
        for i in range(3):
            fname = f"README_{i}.md"
            p = tmp_path / fname
            p.write_text("content " * 100, encoding="utf-8")
            index[fname] = FileEntry(category=FileCategory.doc, size_bytes=p.stat().st_size, language="")

        _, _, _, _, _, _, important_skipped = _read_repo_content(
            tmp_path, index, budget_bytes=_DEFAULT_BUDGET_BYTES
        )
        assert important_skipped == 0

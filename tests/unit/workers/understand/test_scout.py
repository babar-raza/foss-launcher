"""IU-02 / IU-03 — TC-4056 Fix 6 (importance sort) and Fix 7 (skipped_paths).

IU-02: Verify that within a budget tier, files with known-important stems
(readme, api, __init__) are read before unknown-named files even when the
unknown file is smaller. Tests _file_importance_rank directly and via
_read_repo_content with a constrained budget.

IU-03: Verify that files excluded due to budget exhaustion appear in
RepoInfo.skipped_paths, and that files merely truncated (per_file_cap)
do NOT appear in skipped_paths.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from launcher.models.understanding import FileCategory, FileEntry, RepoInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file_index(
    repo_dir: Path,
    specs: list[tuple[str, str, FileCategory]],
) -> dict[str, FileEntry]:
    """Write test files to disk and return a file_index dict.

    Args:
        repo_dir:  Root directory for the repo.
        specs:     List of (rel_path, content, category) tuples.
    """
    file_index: dict[str, FileEntry] = {}
    for rel_path, content, category in specs:
        p = repo_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        file_index[rel_path] = FileEntry(
            category=category,
            size_bytes=len(content.encode("utf-8")),
            language="",
        )
    return file_index


# ===========================================================================
# IU-02a — Direct tests for _file_importance_rank
# ===========================================================================


class TestImportanceRankHelper:
    """Unit tests for _file_importance_rank — the sort-key helper added by TC-4056 Fix 6.

    TC-4234: _file_importance_rank now returns int 0-6 via three additive factors:
      +3 stem keyword match, +2 root-level file, +1 standard extension for category.

    These tests catch any future change to _DOC_IMPORTANCE_STEMS or
    _SOURCE_IMPORTANCE_STEMS that would silently break priority logic.
    """

    def test_readme_doc_rank_is_6(self):
        # root(+2) + keyword(+3) + .md ext(+1) = 6
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("readme.md", FileCategory.doc) == 6

    def test_readme_nested_path_rank_is_4(self):
        # nested(0) + keyword(+3) + .md ext(+1) = 4
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("docs/readme.md", FileCategory.doc) == 4

    def test_api_doc_rank_is_6(self):
        # root(+2) + keyword(+3) + .md ext(+1) = 6
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("api.md", FileCategory.doc) == 6

    def test_guide_doc_rank_is_6(self):
        # root(+2) + keyword(+3) + .md ext(+1) = 6
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("guide.md", FileCategory.doc) == 6

    def test_getting_started_hyphenated_rank_is_6(self):
        """'getting-started' → strip hyphens → 'gettingstarted' which is in the stem set.
        root(+2) + keyword(+3) + .md ext(+1) = 6
        """
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("getting-started.md", FileCategory.doc) == 6

    def test_installation_underscore_rank_is_6(self):
        """'installation' after underscore strip is 'installation' — in stem set.
        root(+2) + keyword(+3) + .md ext(+1) = 6
        """
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("installation.md", FileCategory.doc) == 6

    def test_unknown_doc_stem_root_rank_is_3(self):
        # root(+2) + no keyword(0) + .md ext(+1) = 3
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("zzz_noise.md", FileCategory.doc) == 3

    def test_random_doc_name_root_rank_is_3(self):
        # root(+2) + no keyword(0) + .md ext(+1) = 3
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("misc_notes.md", FileCategory.doc) == 3

    def test_init_source_rank_is_6(self):
        """IU-07: '__init__' stem normalizes to 'init' (underscores stripped).
        _SOURCE_IMPORTANCE_STEMS contains 'init'. root(+2) + keyword(+3) + .py ext(+1) = 6
        """
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("__init__.py", FileCategory.source) == 6

    def test_init_nested_source_rank_is_4(self):
        # nested(0) + keyword(+3) + .py ext(+1) = 4
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("pkg/subpkg/__init__.py", FileCategory.source) == 4

    def test_main_source_rank_is_6(self):
        # root(+2) + keyword(+3) + .py ext(+1) = 6
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("main.py", FileCategory.source) == 6

    def test_core_source_rank_is_6(self):
        # root(+2) + keyword(+3) + .py ext(+1) = 6
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("core.py", FileCategory.source) == 6

    def test_unknown_source_root_rank_is_3(self):
        # root(+2) + no keyword(0) + .py ext(+1) = 3
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("utils_helper.py", FileCategory.source) == 3

    def test_source_name_in_wrong_category_rank_is_2(self):
        """main.py misclassified as doc: root(+2) + no doc keyword(0) + .py not a doc ext(0) = 2"""
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("main.py", FileCategory.doc) == 2

    def test_doc_name_in_wrong_category_rank_is_2(self):
        """readme.md misclassified as source: root(+2) + no source keyword(0) + .md not a source ext(0) = 2"""
        from launcher.workers.understand.scout import _file_importance_rank
        assert _file_importance_rank("readme.md", FileCategory.source) == 2


# ===========================================================================
# IU-02b — Sort behaviour via _read_repo_content with constrained budget
# ===========================================================================


class TestFileImportanceSort:
    """Verify important files are read before unimportant ones when budget is tight.

    All tests call _read_repo_content directly with a small budget_bytes so that
    only the highest-priority file(s) fit. If the sort key were reverted to
    ascending-size-only, the important-but-large file would NOT be read first,
    and the assertions would fail.
    """

    def test_important_doc_read_before_small_junk_doc(self, tmp_path):
        """api.md (3000 B, rank=1) must be read before zzz_noise.md (500 B, rank=0).

        Budget=3200: api.md fits (3000B used), remaining=200 which is < 500B → zzz_noise skipped.
        Under old ascending-size sort: zzz_noise (500B) would be read first (smaller),
        leaving only 2700B for api.md — api.md would actually still fit in that case.
        So we use budget=3100 to force the distinction:
          - importance sort: api.md (3000B) read first → remaining 100B < 500B → zzz_noise skipped
          - size-only sort: zzz_noise (500B) read first → remaining 2600B → api.md also fits
            (both read — test would pass both sorts). Instead we set budget=3100:
          Budget=3100 with importance: api.md(3000) read → used=3000, remaining=100 < 500 → skip noise
          Budget=3100 with size-only:  zzz_noise(500) read → used=500, remaining=2600 → api.md(3000) > 2600 → skip!
        So budget=3100 distinguishes the two sort orders decisively.
        """
        from launcher.workers.understand.scout import _read_repo_content

        file_index = _make_file_index(tmp_path, [
            ("docs/api.md",       "A" * 3000, FileCategory.doc),
            ("docs/zzz_noise.md", "B" * 500,  FileCategory.doc),
        ])

        content, _red, _trunc, budget_log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=3100,
        )

        assert "docs/api.md" in content, (
            "api.md (rank=4, 3000B) must be read first when budget=3100. "
            "If zzz_noise.md (rank=0, 500B) were read first, api.md would be skipped."
        )
        assert "docs/zzz_noise.md" not in content, (
            "zzz_noise.md must be excluded: after api.md consumes 3000B, only 100B remain."
        )

    def test_readme_read_before_unknown_doc_same_size(self, tmp_path):
        """readme.md (rank=1, 1500 B) must be read before other_doc.md (rank=0, 1500 B).

        Budget=1600: only one 1500B file fits. importance sort picks readme.md.
        """
        from launcher.workers.understand.scout import _read_repo_content

        file_index = _make_file_index(tmp_path, [
            ("other_doc.md", "X" * 1500, FileCategory.doc),
            ("readme.md",    "Y" * 1500, FileCategory.doc),
        ])

        content, _red, _trunc, _log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=1600,
        )

        assert "readme.md" in content, "readme.md (rank=6) must win at equal size"
        assert "other_doc.md" not in content, "Unknown doc must be deferred after readme.md"

    def test_init_read_before_unknown_source_same_size(self, tmp_path):
        """__init__.py (rank=1, 2000 B) must be read before utils_extra.py (rank=0, 2000 B).

        IU-07 fixed: 'init' is now in _SOURCE_IMPORTANCE_STEMS so __init__.py gets rank 1.
        Budget=2100: only one 2000B file fits.
        """
        from launcher.workers.understand.scout import _read_repo_content

        file_index = _make_file_index(tmp_path, [
            ("utils_extra.py", "X" * 2000, FileCategory.source),
            ("__init__.py",    "Y" * 2000, FileCategory.source),
        ])

        content, _red, _trunc, _log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=2100,
        )

        assert "__init__.py" in content, "__init__.py (rank=6 source) must beat utils_extra.py"
        assert "utils_extra.py" not in content, "Unknown source file must be deferred"

    def test_main_read_before_unknown_source_same_size(self, tmp_path):
        """main.py (rank=1, 2000 B) must be read before utils_extra.py (rank=0, 2000 B).

        Budget=2100: only one 2000B file fits.
        """
        from launcher.workers.understand.scout import _read_repo_content

        file_index = _make_file_index(tmp_path, [
            ("utils_extra.py", "X" * 2000, FileCategory.source),
            ("main.py",        "Y" * 2000, FileCategory.source),
        ])

        content, _red, _trunc, _log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=2100,
        )

        assert "main.py" in content, "main.py (rank=6 source) must beat utils_extra.py"
        assert "utils_extra.py" not in content, "Unknown source file must be deferred"

    def test_regression_guard_sort_key_not_size_alone(self, tmp_path):
        """Explicit regression guard: the sort key MUST factor in importance rank.

        If someone reverts the sort to ascending-size-only:
          zzz_noise.md (500B) would be chosen first, leaving api.md (3000B) skipped.
        With importance sort:
          api.md (rank=1, 3000B) is chosen first regardless of size.
        Budget=3000: api.md barely fits; zzz_noise.md does not.
        """
        from launcher.workers.understand.scout import _read_repo_content, _file_importance_rank

        # Confirm ranks — this makes the regression explicit in the failure message
        # TC-4234: nested files: api.md = nested(0)+keyword(+3)+.md(+1)=4; zzz_noise.md = nested(0)+.md(+1)=1
        assert _file_importance_rank("docs/api.md", FileCategory.doc) == 4, \
            "_file_importance_rank must return 4 for nested 'api.md' (keyword+ext)"
        assert _file_importance_rank("docs/zzz_noise.md", FileCategory.doc) == 1, \
            "_file_importance_rank must return 1 for nested 'zzz_noise.md' (.md ext only)"

        file_index = _make_file_index(tmp_path, [
            ("docs/api.md",       "A" * 3000, FileCategory.doc),
            ("docs/zzz_noise.md", "B" * 500,  FileCategory.doc),
        ])

        content, _red, _trunc, budget_log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=3000,
        )

        assert "docs/api.md" in content, (
            "REGRESSION: api.md must be chosen when budget=3000. "
            "If sort is size-only, zzz_noise.md (500B) is read first, "
            "leaving only 2500B which cannot fit api.md (3000B)."
        )


# ===========================================================================
# IU-03a — skipped_paths logic via _read_repo_content
# ===========================================================================


class TestSkippedPathsPopulation:
    """IU-G3: Verify that budget-skipped files appear in skipped_paths but
    truncated-only files do NOT.

    Tests _read_repo_content directly to control budget_bytes precisely,
    plus one integration test via run_scout to verify the wiring.
    """

    _SKIP_REASONS = frozenset({
        "budget_exceeded", "doc_cap_reached", "source_reserve",
        "file_too_large_for_remaining_budget",
    })

    def test_budget_exceeded_files_in_skipped(self, tmp_path):
        """Files excluded because budget is 0 must appear in skipped entries."""
        from launcher.workers.understand.scout import _read_repo_content

        file_index = _make_file_index(tmp_path, [
            ("docs/doc_a.md", "A" * 400, FileCategory.doc),
            ("docs/doc_b.md", "B" * 400, FileCategory.doc),
            ("docs/doc_c.md", "C" * 400, FileCategory.doc),
        ])

        # Budget=700: doc_a.md (400B) fits; remaining=300B < 400B → doc_b and doc_c skipped
        content, _red, _trunc, budget_log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=700,
        )

        skipped = [e["path"] for e in budget_log if e.get("reason") in self._SKIP_REASONS]

        assert len(skipped) >= 1, "At least one file must be skipped when budget is tight"
        for path in skipped:
            assert path not in content, (
                f"Skipped path {path!r} must NOT appear in repo_content — "
                "it was excluded, not truncated."
            )

    def test_truncated_files_not_in_skipped(self, tmp_path):
        """Files truncated by per_file_cap must be in repo_content but NOT in skipped.

        A file of 150_000 chars is truncated by sanitize_input(max_chars=100_000).
        Its budget_log entry has reason='per_file_cap', not a skip reason.
        """
        from launcher.workers.understand.scout import _read_repo_content

        file_index = _make_file_index(tmp_path, [
            ("big.md", "X" * 150_000, FileCategory.doc),
        ])

        content, _red, trunc_count, budget_log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=2_000_000,  # generous budget
        )

        skipped = [e["path"] for e in budget_log if e.get("reason") in self._SKIP_REASONS]
        per_file_cap_entries = [e for e in budget_log if e.get("reason") == "per_file_cap"]

        assert "big.md" in content, "Truncated file must be present in repo_content"
        assert "big.md" not in skipped, (
            "Truncated file must NOT appear in skipped_paths — it was read (just shortened)."
        )
        assert any(e["path"] == "big.md" for e in per_file_cap_entries), (
            "Truncated file must appear in budget_log with reason='per_file_cap'"
        )
        assert trunc_count >= 1, "files_truncated count must reflect at least one truncation"

    def test_file_too_large_for_remaining_budget_in_skipped(self, tmp_path):
        """A file that would push past total budget gets reason='file_too_large_for_remaining_budget'."""
        from launcher.workers.understand.scout import _read_repo_content

        # After reading doc_a (400B), remaining = 200B. doc_b (500B) > 200B → skipped.
        file_index = _make_file_index(tmp_path, [
            ("docs/doc_a.md", "A" * 400, FileCategory.doc),
            ("docs/doc_b.md", "B" * 500, FileCategory.doc),
        ])

        content, _red, _trunc, budget_log, _overflow, _dropped, _imp = _read_repo_content(
            tmp_path, file_index, budget_bytes=600,
        )

        skipped = [e["path"] for e in budget_log if e.get("reason") in self._SKIP_REASONS]

        assert "docs/doc_b.md" in skipped, (
            "doc_b.md (500B) must be in skipped when only 200B remain after doc_a."
        )
        assert "docs/doc_b.md" not in content, "Skipped file must not appear in content"

    @pytest.mark.asyncio
    async def test_run_scout_wires_skipped_paths_to_repo_info(self, tmp_path):
        """Integration: run_scout must populate RepoInfo.skipped_paths when doc_cap is reached.

        Strategy: write 8 doc files of 110_000 chars each.
        - per_file_cap (100_000 chars) truncates each to ~100KB in budget accounting.
        - doc_cap = 60% of 1MB = 600KB.
        - After 6 files: category_bytes[doc] = 600KB = doc_cap threshold.
        - Files 7 and 8: trigger doc_cap_reached → in budget_log with a skip reason.
        - run_scout must wire those to repo_info.skipped_paths.
        """
        from launcher.workers.understand.scout import run_scout

        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "main.py").write_text("# main\n", encoding="utf-8")

        docs = tmp_path / "docs"
        docs.mkdir()
        # 8 files × 110K chars each. First 6 fit under doc_cap (600KB); files 7-8 are skipped.
        for i in range(8):
            (docs / f"doc_{i:02d}.md").write_text("D" * 110_000, encoding="utf-8")

        repo_info, repo_content, _budget_log, _overflow = await run_scout(tmp_path)

        assert len(repo_info.skipped_paths) > 0, (
            "run_scout must set RepoInfo.skipped_paths when doc_cap is exceeded. "
            f"Budget log had {len(_budget_log)} entries; skipped_paths={repo_info.skipped_paths!r}"
        )
        for path in repo_info.skipped_paths:
            assert path not in repo_content, (
                f"Skipped path {path!r} must NOT be present in repo_content."
            )


# ===================================================================
# SR-06: Scout integration tests on real temp fixture repos
# ===================================================================


class TestScoutOnFixtureRepo:
    """SR-06: run_scout() on a real temp directory — no mocks, no network."""

    def test_scout_on_python_fixture(self, tmp_path):
        """SR-06: Python fixture produces primary_language=python + correct file counts."""
        import asyncio
        from launcher.workers.understand.scout import run_scout

        # Create minimal Python repo structure
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test-pkg"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        (tmp_path / "README.md").write_text(
            "# Test Package\nA test fixture.\n", encoding="utf-8"
        )
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "core.py").write_text(
            "class Processor:\n    def run(self): pass\n", encoding="utf-8"
        )

        repo_info, repo_content, budget_log, budget_log_overflow = asyncio.run(
            run_scout(tmp_path)
        )

        assert repo_info.shared_facts.primary_language == "python", (
            f"Expected primary_language='python', got {repo_info.shared_facts.primary_language!r}"
        )
        assert len(repo_info.file_tree) >= 2, (
            f"Expected ≥2 files in file_tree, got {len(repo_info.file_tree)}"
        )
        assert isinstance(budget_log, list), "budget_log must be a list"
        assert isinstance(budget_log_overflow, int), "budget_log_overflow must be an int"
        assert repo_info.content_files_read >= 1, "Expected at least 1 file to be read"

    def test_scout_on_js_fixture(self, tmp_path):
        """SR-06: JavaScript fixture produces primary_language=javascript."""
        import asyncio
        from launcher.workers.understand.scout import run_scout

        # Create minimal JavaScript repo structure
        (tmp_path / "package.json").write_text(
            '{"name": "test-js", "version": "1.0.0"}\n', encoding="utf-8"
        )
        (tmp_path / "index.js").write_text(
            "function main() { return 42; }\nmodule.exports = { main };\n",
            encoding="utf-8",
        )

        repo_info, repo_content, budget_log, budget_log_overflow = asyncio.run(
            run_scout(tmp_path)
        )

        assert repo_info.shared_facts.primary_language == "javascript", (
            f"Expected primary_language='javascript', got {repo_info.shared_facts.primary_language!r}"
        )
        assert len(repo_info.file_tree) >= 1

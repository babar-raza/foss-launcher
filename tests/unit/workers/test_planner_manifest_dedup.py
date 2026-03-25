"""Tests for TC-5152 planner manifest deduplication logic (SR-03).

Tests the deploy_manifest_pages dedup block in run_plan() by replicating
the filtering logic in isolation. The full run_plan() has ~15 required
parameters and heavy side effects, so we test the dedup logic directly.
"""
from __future__ import annotations

import pytest


# Replicate the exact dedup logic from plan.py lines 731-750
def _dedup_pages(
    pages: list[dict],
    deploy_manifest_pages: "dict[str, str] | None",
) -> list[dict]:
    """Replica of the TC-5152 dedup block from run_plan()."""
    if not deploy_manifest_pages:
        return list(pages)
    _grade_rank = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
    _deduped = []
    for _page in pages:
        _cp = _page.get("content_path", "")
        _mandatory = _page.get("mandatory", False)
        if not _mandatory and _cp and _cp in deploy_manifest_pages:
            _existing_grade = deploy_manifest_pages[_cp]
            if _grade_rank.get(_existing_grade, 0) >= _grade_rank["B"]:
                continue
        _deduped.append(_page)
    return _deduped


class TestDedupNoneManifest:
    """When deploy_manifest_pages is None, no dedup occurs."""

    def test_none_manifest_passes_all(self):
        pages = [
            {"content_path": "docs/page1", "mandatory": False},
            {"content_path": "docs/page2", "mandatory": False},
        ]
        result = _dedup_pages(pages, None)
        assert len(result) == 2

    def test_empty_dict_manifest_passes_all(self):
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        result = _dedup_pages(pages, {})
        assert len(result) == 1


class TestDedupGradeThreshold:
    """Pages in manifest with grade B+ are skipped; C/D/F are kept."""

    def test_grade_a_skipped(self):
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        manifest = {"docs/page1": "A"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 0

    def test_grade_b_skipped(self):
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        manifest = {"docs/page1": "B"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 0

    def test_grade_c_not_skipped(self):
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        manifest = {"docs/page1": "C"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 1

    def test_grade_d_not_skipped(self):
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        manifest = {"docs/page1": "D"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 1

    def test_grade_f_not_skipped(self):
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        manifest = {"docs/page1": "F"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 1


class TestDedupMandatoryBypass:
    """Mandatory pages are never skipped, even with grade A in manifest."""

    def test_mandatory_page_kept_despite_grade_a(self):
        pages = [{"content_path": "docs/page1", "mandatory": True}]
        manifest = {"docs/page1": "A"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 1


class TestDedupNotInManifest:
    """Pages not in manifest are always kept."""

    def test_page_not_in_manifest_kept(self):
        pages = [{"content_path": "docs/new-page", "mandatory": False}]
        manifest = {"docs/other-page": "A"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 1


class TestDedupEdgeCases:
    """Edge cases and boundary conditions."""

    def test_unknown_grade_string_not_skipped(self):
        # Unknown grade has rank 0 < B's rank 4 → not skipped
        pages = [{"content_path": "docs/page1", "mandatory": False}]
        manifest = {"docs/page1": "X"}
        result = _dedup_pages(pages, manifest)
        assert len(result) == 1

    def test_empty_content_path_not_matched(self):
        pages = [{"content_path": "", "mandatory": False}]
        manifest = {"": "A"}
        result = _dedup_pages(pages, manifest)
        # Empty content_path → the `_cp and _cp in manifest` check fails on `_cp`
        assert len(result) == 1

    def test_mixed_pages(self):
        pages = [
            {"content_path": "docs/existing-a", "mandatory": False},  # A → skip
            {"content_path": "docs/existing-c", "mandatory": False},  # C → keep
            {"content_path": "docs/new-page", "mandatory": False},    # not in manifest → keep
            {"content_path": "docs/mandatory-a", "mandatory": True},  # A but mandatory → keep
        ]
        manifest = {
            "docs/existing-a": "A",
            "docs/existing-c": "C",
            "docs/mandatory-a": "A",
        }
        result = _dedup_pages(pages, manifest)
        assert len(result) == 3
        paths = [p["content_path"] for p in result]
        assert "docs/existing-a" not in paths
        assert "docs/existing-c" in paths
        assert "docs/new-page" in paths
        assert "docs/mandatory-a" in paths

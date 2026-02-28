"""Tests for TC-3520: W8 patch ordering + line range OOB resilience."""

from __future__ import annotations

import pytest

from launch.workers.w8_linker_and_patcher.worker import (
    LinkerPatchConflictError,
    _apply_update_file_range_patch,
    _patch_type_priority,
)


# ── Patch type priority tests ──────────────────────────────────────────────────

class TestPatchTypePriority:
    def test_create_file_first(self):
        p = {"type": "create_file", "patch_id": "create_foo"}
        assert _patch_type_priority(p) == 0

    def test_update_frontmatter_second(self):
        p = {"type": "update_frontmatter_keys", "patch_id": "update_fm_foo"}
        assert _patch_type_priority(p) == 1

    def test_append_update_file_range_third(self):
        p = {"type": "update_file_range", "patch_id": "append_foo_bar"}
        assert _patch_type_priority(p) == 2

    def test_update_by_anchor_fourth(self):
        p = {"type": "update_by_anchor", "patch_id": "update_anchor_foo"}
        assert _patch_type_priority(p) == 3

    def test_update_range_file_range_fifth(self):
        p = {"type": "update_file_range", "patch_id": "update_range_foo"}
        assert _patch_type_priority(p) == 4

    def test_delete_file_sixth(self):
        p = {"type": "delete_file", "patch_id": "delete_foo"}
        assert _patch_type_priority(p) == 5

    def test_unknown_type_last(self):
        p = {"type": "unknown_op", "patch_id": "foo"}
        assert _patch_type_priority(p) == 99

    def test_sorting_produces_correct_order(self):
        patches = [
            {"type": "update_by_anchor", "patch_id": "update_anchor_x"},
            {"type": "update_file_range", "patch_id": "update_range_x"},
            {"type": "create_file", "patch_id": "create_x"},
            {"type": "update_file_range", "patch_id": "append_x"},
            {"type": "update_frontmatter_keys", "patch_id": "update_fm_x"},
        ]
        sorted_patches = sorted(patches, key=_patch_type_priority)
        # create → update (fm) → append → update (anchor) → update (range)
        assert sorted_patches[0]["patch_id"] == "create_x"
        assert sorted_patches[1]["patch_id"] == "update_fm_x"
        assert sorted_patches[2]["patch_id"] == "append_x"
        assert sorted_patches[3]["patch_id"] == "update_anchor_x"
        assert sorted_patches[4]["patch_id"] == "update_range_x"

    def test_empty_patch_returns_unknown(self):
        p = {}
        assert _patch_type_priority(p) == 99

    def test_append_prefix_required_for_priority_2(self):
        """A patch_id that does NOT start with 'append_' gets priority 4 (not 2)."""
        p = {"type": "update_file_range", "patch_id": "my_append_section"}
        # patch_id starts with 'my_append_' not 'append_'
        assert _patch_type_priority(p) == 4

    def test_append_prefix_case_sensitive(self):
        """Priority check is case-sensitive — 'Append_' is not 'append_'."""
        p = {"type": "update_file_range", "patch_id": "Append_foo"}
        assert _patch_type_priority(p) == 4


# ── Line range OOB / clamping tests ───────────────────────────────────────────

class TestAppendClamp:
    def test_append_patch_clamps_when_oob(self, tmp_path):
        """Append patch with end_line > file length should clamp to EOF."""
        target = tmp_path / "page.md"
        target.write_text("# Title\n\nSome content.\n", encoding="utf-8")

        # File has 3 lines. Patch was computed with old line count of 10.
        patch = {
            "type": "update_file_range",
            "patch_id": "append_page_new_section",
            "path": str(target),
            "start_line": 8,
            "end_line": 10,
            "new_content": "## New Section\n\nAppended content.",
            "content_hash": "abc123",
        }

        result = _apply_update_file_range_patch(patch, target)

        assert result["status"] == "applied"
        content = target.read_text(encoding="utf-8")
        assert "New Section" in content
        assert "Appended content." in content

    def test_non_append_patch_still_raises_oob(self, tmp_path):
        """Non-append update_file_range with OOB should still raise."""
        target = tmp_path / "page.md"
        target.write_text("# Title\n\nShort.\n", encoding="utf-8")

        patch = {
            "type": "update_file_range",
            "patch_id": "update_range_foo",
            "path": str(target),
            "start_line": 5,
            "end_line": 10,
            "new_content": "Replacement.",
            "content_hash": "abc123",
        }

        with pytest.raises(LinkerPatchConflictError, match="out of bounds"):
            _apply_update_file_range_patch(patch, target)

    def test_anchor_shrink_then_append_succeeds(self, tmp_path):
        """Simulate: update_by_anchor shrinks content, append patch runs after with clamping."""
        target = tmp_path / "page.md"
        # Start with 20 lines
        original_lines = ["# Title\n"] + [f"Line {i}.\n" for i in range(19)]
        target.write_text("".join(original_lines), encoding="utf-8")

        # Simulate update_by_anchor having already shrunk to 5 lines
        target.write_text("# Title\n\nShort content.\n\nEnd.\n", encoding="utf-8")

        # Append patch computed with original 20 lines
        patch = {
            "type": "update_file_range",
            "patch_id": "append_page_conclusion",
            "path": str(target),
            "start_line": 18,
            "end_line": 20,
            "new_content": "## Conclusion\n\nDone.",
            "content_hash": "abc",
        }

        result = _apply_update_file_range_patch(patch, target)
        assert result["status"] == "applied"
        content = target.read_text(encoding="utf-8")
        assert "Conclusion" in content

    def test_append_patch_preserves_existing_content(self, tmp_path):
        """Clamped append patch should NOT lose existing file content."""
        target = tmp_path / "page.md"
        target.write_text("# Title\n\nExisting line.\n", encoding="utf-8")

        patch = {
            "type": "update_file_range",
            "patch_id": "append_page_extra",
            "path": str(target),
            "start_line": 50,
            "end_line": 60,
            "new_content": "## Extra",
            "content_hash": "xyz",
        }

        _apply_update_file_range_patch(patch, target)
        content = target.read_text(encoding="utf-8")
        assert "# Title" in content
        assert "Existing line." in content
        assert "## Extra" in content

    def test_append_patch_not_oob_uses_normal_path(self, tmp_path):
        """Append patch within file bounds goes through normal replacement path."""
        target = tmp_path / "page.md"
        target.write_text("# Title\nLine 2\nLine 3\n", encoding="utf-8")

        # end_line=3 == len(lines)=3, so NOT OOB — normal path applies
        patch = {
            "type": "update_file_range",
            "patch_id": "append_page_section",
            "path": str(target),
            "start_line": 3,
            "end_line": 3,
            "new_content": "Replaced line 3.",
            "content_hash": "def",
        }

        result = _apply_update_file_range_patch(patch, target)
        assert result["status"] == "applied"
        content = target.read_text(encoding="utf-8")
        assert "Replaced line 3." in content


class TestPatchOrdering:
    def test_patches_sorted_before_apply(self):
        """Verify patches list sorted by priority gives correct relative ordering."""
        patches = [
            {"type": "update_by_anchor", "patch_id": "update_anchor_a"},
            {"type": "create_file", "patch_id": "create_a"},
            {"type": "update_file_range", "patch_id": "append_a"},
        ]
        sorted_p = sorted(patches, key=_patch_type_priority)
        assert sorted_p[0]["patch_id"] == "create_a"
        assert sorted_p[1]["patch_id"] == "append_a"
        assert sorted_p[2]["patch_id"] == "update_anchor_a"

    def test_full_priority_order_with_all_types(self):
        """All six patch types sort in the correct priority order."""
        patches = [
            {"type": "delete_file", "patch_id": "delete_z"},
            {"type": "update_file_range", "patch_id": "update_range_z"},
            {"type": "update_by_anchor", "patch_id": "update_anchor_z"},
            {"type": "update_file_range", "patch_id": "append_z"},
            {"type": "update_frontmatter_keys", "patch_id": "update_fm_z"},
            {"type": "create_file", "patch_id": "create_z"},
        ]
        sorted_p = sorted(patches, key=_patch_type_priority)
        expected_order = [
            "create_z",
            "update_fm_z",
            "append_z",
            "update_anchor_z",
            "update_range_z",
            "delete_z",
        ]
        assert [p["patch_id"] for p in sorted_p] == expected_order

    def test_sort_is_stable_for_equal_priorities(self):
        """Python sort is stable — equal-priority patches keep their original order."""
        patches = [
            {"type": "update_by_anchor", "patch_id": "update_anchor_first"},
            {"type": "update_by_anchor", "patch_id": "update_anchor_second"},
        ]
        sorted_p = sorted(patches, key=_patch_type_priority)
        assert sorted_p[0]["patch_id"] == "update_anchor_first"
        assert sorted_p[1]["patch_id"] == "update_anchor_second"

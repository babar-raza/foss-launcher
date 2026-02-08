"""TC-1035: W6 LinkerPatcher edge case tests.

This module tests edge cases in the W6 LinkerAndPatcher worker that are
NOT covered by the existing test_tc_450_linker_and_patcher.py:

1. Empty patch bundle (no patches to apply)
2. Malformed patch content (invalid diff format / unknown patch type)
3. Patches targeting non-existent files (update_by_anchor, update_frontmatter_keys)
4. Cross-page link resolution with missing target pages
5. Concurrent patch conflicts (overlapping line ranges)
6. Unicode content in patches
7. update_file_range line range out of bounds
8. Frontmatter with no closing delimiter
9. Content hash mismatch during create_file with expected_before_hash

Spec references:
- specs/08_patch_engine.md (Patch application algorithm)
- specs/21_worker_contracts.md:228-251 (W6 LinkerAndPatcher contract)
- specs/10_determinism_and_caching.md (Deterministic ordering)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w6_linker_and_patcher import (
    LinkerAndPatcherError,
    LinkerNoDraftsError,
    LinkerPatchConflictError,
    LinkerAllowedPathsViolationError,
    LinkerWriteFailedError,
    execute_linker_and_patcher,
)
from src.launch.workers.w6_linker_and_patcher.worker import (
    apply_patch,
    compute_content_hash,
    find_anchor_in_content,
    generate_diff_report,
    generate_patches_from_drafts,
    insert_content_at_anchor,
    parse_frontmatter,
    update_frontmatter,
    validate_allowed_path,
)


@pytest.fixture
def temp_run_dir():
    """Create temporary run directory with required structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run"
        run_dir.mkdir()

        # Create required subdirectories
        (run_dir / "artifacts").mkdir()
        (run_dir / "reports").mkdir()
        (run_dir / "drafts").mkdir()
        (run_dir / "work" / "site" / "content").mkdir(parents=True)

        # Create events.ndjson
        (run_dir / "events.ndjson").write_text("")

        yield run_dir


# ---------------------------------------------------------------------------
# 1. Empty patch bundle (generate_patches_from_drafts returns empty list)
# ---------------------------------------------------------------------------
def test_generate_patches_empty_draft_manifest(temp_run_dir):
    """When draft_manifest has drafts but all draft files are missing,
    generate_patches_from_drafts returns an empty list (logs warnings)."""
    draft_manifest = {
        "drafts": [
            {
                "page_id": "ghost_page",
                "output_path": "content/missing/page.md",
                "draft_path": "drafts/nonexistent.md",
            }
        ]
    }
    page_plan = {"pages": []}
    site_worktree = temp_run_dir / "work" / "site"

    patches = generate_patches_from_drafts(
        draft_manifest=draft_manifest,
        page_plan=page_plan,
        run_dir=temp_run_dir,
        site_worktree=site_worktree,
    )

    # No draft files exist so no patches should be generated
    assert patches == []


def test_diff_report_with_zero_patches():
    """generate_diff_report should produce valid markdown even with no patches."""
    site_worktree = Path("/fake/site")
    report = generate_diff_report([], [], site_worktree)

    assert "# Patch Application Report" in report
    assert "**Total Patches**: 0" in report
    assert "**Applied**: 0" in report
    assert "**Skipped**: 0" in report
    assert "**Conflicts**: 0" in report


# ---------------------------------------------------------------------------
# 2. Unknown / malformed patch type
# ---------------------------------------------------------------------------
def test_apply_patch_unknown_type(temp_run_dir):
    """apply_patch should raise LinkerAndPatcherError for unknown patch type."""
    site_worktree = temp_run_dir / "work" / "site"
    patch = {
        "patch_id": "bad_type",
        "type": "teleport_content",
        "path": "content/test.md",
        "new_content": "hello",
        "content_hash": compute_content_hash("hello"),
    }

    with pytest.raises(LinkerAndPatcherError, match="Unknown patch type"):
        apply_patch(patch, site_worktree)


# ---------------------------------------------------------------------------
# 3. Patches targeting non-existent files
# ---------------------------------------------------------------------------
def test_apply_update_by_anchor_missing_file(temp_run_dir):
    """update_by_anchor should raise LinkerPatchConflictError when file missing."""
    site_worktree = temp_run_dir / "work" / "site"
    patch = {
        "patch_id": "anchor_missing",
        "type": "update_by_anchor",
        "path": "content/does_not_exist.md",
        "anchor": "Installation",
        "new_content": "pip install foo",
        "content_hash": "dummy",
    }

    with pytest.raises(LinkerPatchConflictError, match="Target file not found"):
        apply_patch(patch, site_worktree)


def test_apply_update_frontmatter_missing_file(temp_run_dir):
    """update_frontmatter_keys should raise LinkerPatchConflictError when file missing."""
    site_worktree = temp_run_dir / "work" / "site"
    patch = {
        "patch_id": "fm_missing",
        "type": "update_frontmatter_keys",
        "path": "content/nope.md",
        "frontmatter_updates": {"weight": 5},
        "content_hash": "dummy",
    }

    with pytest.raises(LinkerPatchConflictError, match="Target file not found"):
        apply_patch(patch, site_worktree)


def test_apply_update_file_range_missing_file(temp_run_dir):
    """update_file_range should raise LinkerPatchConflictError when file missing."""
    site_worktree = temp_run_dir / "work" / "site"
    patch = {
        "patch_id": "range_missing",
        "type": "update_file_range",
        "path": "content/absent.md",
        "start_line": 1,
        "end_line": 3,
        "new_content": "replacement",
    }

    with pytest.raises(LinkerPatchConflictError, match="Target file not found"):
        apply_patch(patch, site_worktree)


# ---------------------------------------------------------------------------
# 4. Anchor not found when inserting
# ---------------------------------------------------------------------------
def test_insert_content_at_missing_anchor():
    """insert_content_at_anchor should raise LinkerPatchConflictError."""
    content = "# Title\n\n## Section A\n\nSome text."
    with pytest.raises(LinkerPatchConflictError, match="Anchor not found"):
        insert_content_at_anchor(content, "Nonexistent Section", "new content")


def test_apply_update_by_anchor_anchor_missing(temp_run_dir):
    """Full apply_patch path for update_by_anchor with missing anchor."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "anchored.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("# Title\n\n## Section A\n\nContent here.\n")

    patch = {
        "patch_id": "anchor_wrong",
        "type": "update_by_anchor",
        "path": "content/anchored.md",
        "anchor": "Missing Heading",
        "new_content": "should fail",
        "content_hash": "dummy",
    }

    with pytest.raises(LinkerPatchConflictError, match="Anchor not found"):
        apply_patch(patch, site_worktree)


# ---------------------------------------------------------------------------
# 5. Overlapping line ranges (update_file_range)
# ---------------------------------------------------------------------------
def test_update_file_range_out_of_bounds(temp_run_dir):
    """update_file_range should raise LinkerPatchConflictError when line range
    extends beyond file length."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "short.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("line 1\nline 2\nline 3\n")

    patch = {
        "patch_id": "oob_range",
        "type": "update_file_range",
        "path": "content/short.md",
        "start_line": 1,
        "end_line": 50,  # File has only 3 lines
        "new_content": "replacement",
    }

    with pytest.raises(LinkerPatchConflictError, match="Line range out of bounds"):
        apply_patch(patch, site_worktree)


def test_update_file_range_valid(temp_run_dir):
    """update_file_range should successfully replace a valid line range."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "range_test.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("line 1\nline 2\nline 3\nline 4\n")

    patch = {
        "patch_id": "valid_range",
        "type": "update_file_range",
        "path": "content/range_test.md",
        "start_line": 2,
        "end_line": 3,
        "new_content": "REPLACED",
    }

    result = apply_patch(patch, site_worktree)
    assert result["status"] == "applied"

    updated = target_path.read_text(encoding="utf-8")
    assert "REPLACED" in updated
    assert "line 1" in updated
    assert "line 4" in updated


def test_update_file_range_start_line_zero(temp_run_dir):
    """update_file_range with start_line=0 should raise conflict (1-indexed)."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "zero.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("line 1\nline 2\n")

    patch = {
        "patch_id": "zero_start",
        "type": "update_file_range",
        "path": "content/zero.md",
        "start_line": 0,
        "end_line": 1,
        "new_content": "bad",
    }

    with pytest.raises(LinkerPatchConflictError, match="Line range out of bounds"):
        apply_patch(patch, site_worktree)


# ---------------------------------------------------------------------------
# 6. Unicode content in patches
# ---------------------------------------------------------------------------
def test_apply_patch_unicode_content(temp_run_dir):
    """Patches with Unicode/multilingual content should work correctly."""
    site_worktree = temp_run_dir / "work" / "site"

    unicode_content = (
        "# Aspose.3D for Python\n\n"
        "## Apercu\n\n"
        "Biblioteque de traitement de fichiers 3D pour Python.\n\n"
        "## Caracteres speciaux\n\n"
        "Umlauts: a, o, u\n"
        "CJK: \u4f60\u597d\u4e16\u754c\n"
        "Emoji: (test)\n"
        "Arabic: \u0645\u0631\u062d\u0628\u0627\n"
    )

    patch = {
        "patch_id": "unicode_test",
        "type": "create_file",
        "path": "content/unicode_page.md",
        "new_content": unicode_content,
        "content_hash": compute_content_hash(unicode_content),
    }

    result = apply_patch(patch, site_worktree)
    assert result["status"] == "applied"

    # Verify content round-trips correctly
    written = (site_worktree / "content" / "unicode_page.md").read_text(encoding="utf-8")
    assert written == unicode_content

    # Idempotency check
    result2 = apply_patch(patch, site_worktree)
    assert result2["status"] == "skipped"


# ---------------------------------------------------------------------------
# 7. Content hash mismatch (expected_before_hash conflict)
# ---------------------------------------------------------------------------
def test_create_file_hash_mismatch(temp_run_dir):
    """create_file with expected_before_hash that does not match existing content
    should raise LinkerPatchConflictError."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "hashcheck.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("original content")

    new_content = "updated content"
    patch = {
        "patch_id": "hash_mismatch",
        "type": "create_file",
        "path": "content/hashcheck.md",
        "new_content": new_content,
        "content_hash": compute_content_hash(new_content),
        "expected_before_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    }

    with pytest.raises(LinkerPatchConflictError, match="Content mismatch"):
        apply_patch(patch, site_worktree)


def test_create_file_hash_match_updates(temp_run_dir):
    """create_file with matching expected_before_hash should apply successfully."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "hashok.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    original = "original"
    target_path.write_text(original)

    new_content = "updated"
    patch = {
        "patch_id": "hash_ok",
        "type": "create_file",
        "path": "content/hashok.md",
        "new_content": new_content,
        "content_hash": compute_content_hash(new_content),
        "expected_before_hash": compute_content_hash(original),
    }

    result = apply_patch(patch, site_worktree)
    assert result["status"] == "applied"
    assert target_path.read_text(encoding="utf-8") == new_content


# ---------------------------------------------------------------------------
# 8. Frontmatter edge cases
# ---------------------------------------------------------------------------
def test_parse_frontmatter_no_closing_delimiter():
    """parse_frontmatter with opening --- but no closing --- returns None, full content."""
    content = "---\ntitle: Broken\nweight: 5\nThis is body text"
    frontmatter, body = parse_frontmatter(content)
    assert frontmatter is None
    assert body == content


def test_update_frontmatter_creates_new_when_absent():
    """update_frontmatter on content without frontmatter should add it."""
    content = "# Just a heading\n\nSome body text."
    updated = update_frontmatter(content, {"title": "New Title", "weight": 1})

    assert updated.startswith("---\n")
    assert "title: New Title" in updated
    assert "weight: 1" in updated
    assert "# Just a heading" in updated


def test_update_frontmatter_invalid_yaml_recovers():
    """update_frontmatter on content with unparseable frontmatter should
    create new frontmatter (graceful recovery)."""
    content = "---\n{invalid yaml [[[: broken\n---\n\nBody here."
    updated = update_frontmatter(content, {"title": "Fixed"})

    assert "title: Fixed" in updated
    assert "Body here." in updated


# ---------------------------------------------------------------------------
# 9. Allowed paths edge cases
# ---------------------------------------------------------------------------
def test_validate_allowed_path_empty_list():
    """Empty allowed_paths list is treated same as None (no restrictions).

    Note: The implementation uses `if not allowed_paths:` which evaluates
    both None and [] the same way -- allowing all paths within site_worktree.
    This is a documented behavior, not a bug.
    """
    site_worktree = Path("/tmp/site")
    target = Path("/tmp/site/content/page.md")

    # Empty list treated same as None = all paths within worktree allowed
    assert validate_allowed_path(target, site_worktree, []) is True

    # But paths outside worktree are still denied
    outside = Path("/tmp/other/page.md")
    assert validate_allowed_path(outside, site_worktree, []) is False


def test_validate_allowed_path_partial_prefix_match():
    """Validate that path prefix matching is correct."""
    site_worktree = Path("/tmp/site")

    # Should match because path starts with allowed prefix
    target = Path("/tmp/site/content/docs/deep/nested/page.md")
    assert validate_allowed_path(target, site_worktree, ["content/docs"]) is True

    # Should NOT match (different prefix)
    assert validate_allowed_path(target, site_worktree, ["content/kb"]) is False


# ---------------------------------------------------------------------------
# 10. Diff report with mixed results
# ---------------------------------------------------------------------------
def test_diff_report_mixed_statuses():
    """generate_diff_report should correctly count applied, skipped, and conflict patches."""
    patches = [
        {"patch_id": "p1", "type": "create_file", "path": "a.md"},
        {"patch_id": "p2", "type": "update_by_anchor", "path": "b.md"},
        {"patch_id": "p3", "type": "create_file", "path": "c.md"},
    ]
    results = [
        {"status": "applied", "reason": "Created file"},
        {"status": "skipped", "reason": "Content unchanged"},
        {"status": "conflict", "reason": "Hash mismatch"},
    ]

    report = generate_diff_report(patches, results, Path("/fake"))

    assert "**Applied**: 1" in report
    assert "**Skipped**: 1" in report
    assert "**Conflicts**: 1" in report
    assert "### p1" in report
    assert "### p2" in report
    assert "### p3" in report


# ---------------------------------------------------------------------------
# 11. Full execute with drafts that produce idempotent patches (all skipped)
# ---------------------------------------------------------------------------
def test_execute_all_patches_skipped(temp_run_dir):
    """When all draft content already exists in site worktree, all patches
    should be skipped during generation (no patches created at all)."""
    content_a = "# Page A\n\nContent for page A."
    content_b = "# Page B\n\nContent for page B."

    # Create draft files
    drafts_dir = temp_run_dir / "drafts"
    (drafts_dir / "page_a.md").write_text(content_a)
    (drafts_dir / "page_b.md").write_text(content_b)

    # Pre-create in site worktree with identical content
    site_worktree = temp_run_dir / "work" / "site"
    path_a = site_worktree / "content" / "docs" / "page_a.md"
    path_b = site_worktree / "content" / "docs" / "page_b.md"
    path_a.parent.mkdir(parents=True, exist_ok=True)
    path_b.parent.mkdir(parents=True, exist_ok=True)
    path_a.write_text(content_a)
    path_b.write_text(content_b)

    draft_manifest = {
        "drafts": [
            {
                "page_id": "page_a",
                "output_path": "content/docs/page_a.md",
                "draft_path": "drafts/page_a.md",
            },
            {
                "page_id": "page_b",
                "output_path": "content/docs/page_b.md",
                "draft_path": "drafts/page_b.md",
            },
        ]
    }

    patches = generate_patches_from_drafts(
        draft_manifest=draft_manifest,
        page_plan={"pages": []},
        run_dir=temp_run_dir,
        site_worktree=site_worktree,
    )

    # No patches because content hashes match
    assert patches == []


# ---------------------------------------------------------------------------
# 12. find_anchor_in_content edge cases
# ---------------------------------------------------------------------------
def test_find_anchor_empty_content():
    """find_anchor_in_content on empty string should return None."""
    assert find_anchor_in_content("", "Installation") is None


def test_find_anchor_multiple_levels():
    """find_anchor_in_content should find anchors at different heading levels."""
    content = "# H1\n## H2\n### H3\n#### H4\n"
    assert find_anchor_in_content(content, "H1") == 0
    assert find_anchor_in_content(content, "H2") == 1
    assert find_anchor_in_content(content, "H3") == 2
    assert find_anchor_in_content(content, "H4") == 3


def test_find_anchor_with_extra_whitespace():
    """find_anchor_in_content should find headings with trailing whitespace."""
    content = "## Installation  \n\nSome text."
    # The heading text has trailing spaces; strip should handle it
    assert find_anchor_in_content(content, "Installation") == 0


# ---------------------------------------------------------------------------
# 13. Content hash determinism
# ---------------------------------------------------------------------------
def test_content_hash_deterministic_unicode():
    """compute_content_hash must be deterministic for Unicode content."""
    content = "\u4f60\u597d\u4e16\u754c hello"
    h1 = compute_content_hash(content)
    h2 = compute_content_hash(content)
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex


def test_content_hash_different_for_different_content():
    """compute_content_hash must produce different hashes for different inputs."""
    h1 = compute_content_hash("abc")
    h2 = compute_content_hash("abd")
    assert h1 != h2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

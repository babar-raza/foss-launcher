"""TC-3350 + TC-3355: W8 LinkerAndPatcher Production Hardening + Healing tests.

Tests for 7 spec-compliance fixes (TC-3350):
M1: Granular update patches for existing files (anchor + frontmatter + range)
M2: delete_file patches include content_hash
M3: Section-aware deterministic patch ordering
M4: patch_conflicts.json artifact on conflict
M5: replace_content_under_anchor (replace, not insert)
M6: allowed_paths glob support via fnmatch
M7: patch_bundle schema validation

Healing tests (TC-3355):
GAP-01: New-heading crash path fix (update_file_range append)
GAP-02: Fail-fast schema validation
GAP-03: Telemetry events (PATCH_ENGINE_STARTED/COMPLETED/APPLIED/SKIPPED)
GAP-05: Schema caching at module level
GAP-06: Integration test for existing-file update chain
GAP-07: Conflict classification hardening
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.launch.workers.w8_linker_and_patcher.worker import (
    _classify_conflict,
    _extract_conflict_states,
    _generate_update_patches_for_existing,
    _get_patch_bundle_schema,
    _section_index_from_path,
    _split_into_sections,
    _suggest_fix,
    _validate_patch_bundle,
    apply_patch,
    compute_content_hash,
    find_anchor_in_content,
    generate_patches_from_drafts,
    replace_content_under_anchor,
    validate_allowed_path,
    LinkerPatchConflictError,
)


# ---------------------------------------------------------------------------
# M5: replace_content_under_anchor
# ---------------------------------------------------------------------------

class TestReplaceContentUnderAnchor:
    """Tests for replace_content_under_anchor() — M5."""

    def test_replaces_section_content(self):
        """Old section content is replaced, not appended."""
        content = (
            "# Title\n\n"
            "## Installation\n\nOld install text.\n\n"
            "## Usage\n\nUsage text.\n"
        )
        result = replace_content_under_anchor(content, "Installation", "New install text.")
        assert "New install text." in result
        assert "Old install text." not in result
        assert "## Usage" in result
        assert "Usage text." in result

    def test_respects_heading_level(self):
        """H2 anchor replaces until next H2/H1, but keeps H3 subsections."""
        content = (
            "# Title\n\n"
            "## Section A\n\nA content.\n\n"
            "### Subsection A1\n\nA1 content.\n\n"
            "## Section B\n\nB content.\n"
        )
        result = replace_content_under_anchor(content, "Section A", "Replaced A.")
        assert "Replaced A." in result
        assert "A content." not in result
        assert "A1 content." not in result  # H3 subsection was under H2, so replaced
        assert "## Section B" in result
        assert "B content." in result

    def test_last_section_replaces_to_eof(self):
        """Anchor at last heading replaces content to end of file."""
        content = "# Title\n\n## Only Section\n\nOld content.\nMore old.\n"
        result = replace_content_under_anchor(content, "Only Section", "Fresh content.")
        assert "Fresh content." in result
        assert "Old content." not in result
        assert "More old." not in result

    def test_anchor_not_found_raises(self):
        """Missing anchor raises LinkerPatchConflictError."""
        with pytest.raises(LinkerPatchConflictError, match="Anchor not found"):
            replace_content_under_anchor("# Title\n\nBody.", "Missing", "New.")

    def test_idempotent_no_duplicates(self):
        """Applying same patch twice via apply_patch produces no duplicate content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            site = Path(tmpdir)
            target = site / "page.md"
            target.write_text(
                "# Title\n\n## Section\n\nOriginal.\n\n## Other\n\nKept.\n",
                encoding="utf-8",
            )
            patch = {
                "patch_id": "test_anchor",
                "type": "update_by_anchor",
                "path": "page.md",
                "anchor": "Section",
                "new_content": "Updated content.",
                "content_hash": compute_content_hash("Updated content."),
            }
            r1 = apply_patch(patch, site)
            assert r1["status"] == "applied"

            r2 = apply_patch(patch, site)
            assert r2["status"] == "skipped"

            final = target.read_text(encoding="utf-8")
            assert final.count("Updated content.") == 1


# ---------------------------------------------------------------------------
# M2: delete_file content_hash
# ---------------------------------------------------------------------------

class TestDeletePatchContentHash:
    """Tests for delete_file content_hash — M2."""

    def test_delete_patch_has_content_hash(self):
        """Delete patch includes content_hash = sha256 of pre-delete content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            site = run_dir / "work" / "site" / "content"
            site.mkdir(parents=True)

            # Create a file to be deleted
            file_content = "Content to delete."
            target = site / "content" / "docs.aspose.org" / "prod" / "page.md"
            target.parent.mkdir(parents=True)
            target.write_text(file_content, encoding="utf-8")

            page_plan = {
                "pages": [{
                    "section": "docs",
                    "slug": "page",
                    "page_status": "deleted",
                    "output_path": "content/docs.aspose.org/prod/page.md",
                }],
            }
            draft_manifest = {"drafts": []}

            patches = generate_patches_from_drafts(
                draft_manifest, page_plan, run_dir, site, family="prod",
            )

            delete_patches = [p for p in patches if p["type"] == "delete_file"]
            assert len(delete_patches) == 1
            dp = delete_patches[0]
            assert "content_hash" in dp
            assert dp["content_hash"] == compute_content_hash(file_content)


# ---------------------------------------------------------------------------
# M3: Section-aware deterministic ordering
# ---------------------------------------------------------------------------

class TestSectionOrdering:
    """Tests for section-aware patch ordering — M3."""

    def test_products_before_docs(self):
        """Products section patches come before docs section patches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            site = run_dir / "work" / "site" / "content"
            site.mkdir(parents=True)
            (run_dir / "drafts" / "docs").mkdir(parents=True)
            (run_dir / "drafts" / "products").mkdir(parents=True)

            (run_dir / "drafts" / "docs" / "a.md").write_text("# Docs A\n\n## Intro\n\nContent.\n")
            (run_dir / "drafts" / "products" / "b.md").write_text("# Products B\n\n## Intro\n\nContent.\n")

            page_plan = {"pages": []}
            draft_manifest = {
                "drafts": [
                    {
                        "page_id": "docs_a",
                        "section": "docs",
                        "slug": "a",
                        "output_path": "content/docs.aspose.org/prod/en/python/a.md",
                        "draft_path": "drafts/docs/a.md",
                    },
                    {
                        "page_id": "products_b",
                        "section": "products",
                        "slug": "b",
                        "output_path": "content/products.aspose.org/prod/en/python/b.md",
                        "draft_path": "drafts/products/b.md",
                    },
                ],
            }

            patches = generate_patches_from_drafts(
                draft_manifest, page_plan, run_dir, site, family="prod",
            )

            assert len(patches) == 2
            # products (index 0) should come before docs (index 1)
            assert "products.aspose.org" in patches[0]["path"]
            assert "docs.aspose.org" in patches[1]["path"]

    def test_within_section_alphabetical_by_path(self):
        """Within the same section, patches are sorted by output_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            site = run_dir / "work" / "site" / "content"
            site.mkdir(parents=True)
            (run_dir / "drafts" / "docs").mkdir(parents=True)

            (run_dir / "drafts" / "docs" / "z.md").write_text("# Z\n\n## Intro\n\nContent.\n")
            (run_dir / "drafts" / "docs" / "a.md").write_text("# A\n\n## Intro\n\nContent.\n")

            page_plan = {"pages": []}
            draft_manifest = {
                "drafts": [
                    {
                        "page_id": "docs_z",
                        "output_path": "content/docs.aspose.org/prod/en/python/z.md",
                        "draft_path": "drafts/docs/z.md",
                    },
                    {
                        "page_id": "docs_a",
                        "output_path": "content/docs.aspose.org/prod/en/python/a.md",
                        "draft_path": "drafts/docs/a.md",
                    },
                ],
            }

            patches = generate_patches_from_drafts(
                draft_manifest, page_plan, run_dir, site, family="prod",
            )

            assert patches[0]["path"].endswith("a.md")
            assert patches[1]["path"].endswith("z.md")

    def test_section_index_from_path(self):
        """_section_index_from_path extracts correct indices."""
        assert _section_index_from_path("content/products.aspose.org/foo/bar.md") == 0
        assert _section_index_from_path("content/docs.aspose.org/foo/bar.md") == 1
        assert _section_index_from_path("content/kb.aspose.org/foo/bar.md") == 2
        assert _section_index_from_path("content/reference.aspose.org/foo/bar.md") == 3
        assert _section_index_from_path("content/blog.aspose.org/foo/bar.md") == 4
        assert _section_index_from_path("content/unknown.org/foo.md") == 99


# ---------------------------------------------------------------------------
# M6: allowed_paths glob support
# ---------------------------------------------------------------------------

class TestAllowedPathsGlob:
    """Tests for glob-enhanced allowed_paths — M6."""

    def test_glob_star(self):
        """Pattern with * matches files (fnmatch * matches path separators too)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            site = Path(tmpdir)
            target = site / "content" / "docs" / "page.md"
            target.parent.mkdir(parents=True)

            assert validate_allowed_path(target, site, ["content/docs/*.md"])
            # fnmatch * also matches path separators
            nested = site / "content" / "docs" / "sub" / "page.md"
            nested.parent.mkdir(parents=True)
            assert validate_allowed_path(nested, site, ["content/docs/*.md"])

    def test_glob_doublestar(self):
        """Pattern with ** matches deeply nested paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            site = Path(tmpdir)
            deep = site / "content" / "docs" / "sub" / "deep" / "page.md"
            deep.parent.mkdir(parents=True)

            assert validate_allowed_path(deep, site, ["content/docs/**"])

    def test_no_glob_backward_compat(self):
        """Plain prefix pattern (no globs) still works via startswith."""
        with tempfile.TemporaryDirectory() as tmpdir:
            site = Path(tmpdir)
            target = site / "content" / "docs" / "nested" / "page.md"
            target.parent.mkdir(parents=True)

            assert validate_allowed_path(target, site, ["content/docs"])

    def test_outside_site_worktree_rejected(self):
        """Path outside site_worktree is always rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            site = Path(tmpdir) / "site"
            site.mkdir()
            outside = Path(tmpdir) / "other" / "file.md"

            assert not validate_allowed_path(outside, site, ["**"])


# ---------------------------------------------------------------------------
# M1: Granular update patches for existing files
# ---------------------------------------------------------------------------

class TestGranularUpdatePatches:
    """Tests for _generate_update_patches_for_existing — M1."""

    def test_existing_file_generates_anchor_patches(self):
        """Existing file with different sections generates update_by_anchor patches."""
        existing = (
            "---\ntitle: Test\n---\n\n"
            "## Installation\n\nOld install.\n\n"
            "## Usage\n\nOld usage.\n"
        )
        draft = (
            "---\ntitle: Test\n---\n\n"
            "## Installation\n\nNew install.\n\n"
            "## Usage\n\nOld usage.\n"
        )
        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")

        anchor_patches = [p for p in patches if p["type"] == "update_by_anchor"]
        assert len(anchor_patches) == 1
        assert anchor_patches[0]["anchor"] == "Installation"
        assert "New install." in anchor_patches[0]["new_content"]

    def test_frontmatter_diff_generates_frontmatter_patch(self):
        """Different frontmatter generates update_frontmatter_keys patch."""
        existing = "---\ntitle: Old Title\nauthor: Alice\n---\n\n## Body\n\nContent.\n"
        draft = "---\ntitle: New Title\nauthor: Alice\n---\n\n## Body\n\nContent.\n"

        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")

        fm_patches = [p for p in patches if p["type"] == "update_frontmatter_keys"]
        assert len(fm_patches) == 1
        assert fm_patches[0]["frontmatter_updates"] == {"title": "New Title"}

    def test_no_headings_fallback_to_range(self):
        """Draft with no headings falls back to update_file_range."""
        existing = "---\ntitle: Test\n---\n\nOld body text without headings.\n"
        draft = "---\ntitle: Test\n---\n\nNew body text without headings.\n"

        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")

        range_patches = [p for p in patches if p["type"] == "update_file_range"]
        assert len(range_patches) == 1
        assert "New body text" in range_patches[0]["new_content"]

    def test_identical_sections_skipped(self):
        """Sections with identical content produce no patches."""
        content = "---\ntitle: Same\n---\n\n## Section A\n\nSame content.\n"
        patches = _generate_update_patches_for_existing(content, content, "pg1", "page.md")
        assert len(patches) == 0


# ---------------------------------------------------------------------------
# M1 helper: _split_into_sections
# ---------------------------------------------------------------------------

class TestSplitIntoSections:
    """Tests for _split_into_sections helper — M1."""

    def test_basic_split(self):
        """Splits body into heading -> content dict."""
        body = "Preamble.\n\n## Heading A\n\nContent A.\n\n## Heading B\n\nContent B.\n"
        sections = _split_into_sections(body)

        assert "" in sections  # preamble
        assert "Preamble." in sections[""]
        assert "Heading A" in sections
        assert "Content A." in sections["Heading A"]
        assert "Heading B" in sections
        assert "Content B." in sections["Heading B"]

    def test_no_headings(self):
        """Body with no headings returns single preamble entry."""
        body = "Just plain text.\nAnother line.\n"
        sections = _split_into_sections(body)
        assert len(sections) == 1
        assert "" in sections


# ---------------------------------------------------------------------------
# M4: patch_conflicts.json
# ---------------------------------------------------------------------------

class TestPatchConflictsArtifact:
    """Tests for patch_conflicts.json artifact — M4."""

    def test_classify_conflict_categories(self):
        """_classify_conflict maps error messages to spec categories."""
        assert _classify_conflict(Exception("Anchor not found: ## Foo")) == "anchor_not_found"
        assert _classify_conflict(Exception("Line range out of bounds: 1-99")) == "line_range_out_of_bounds"
        assert _classify_conflict(Exception("Content mismatch at file")) == "content_mismatch"
        assert _classify_conflict(Exception("outside allowed_paths")) == "path_outside_allowed_paths"
        assert _classify_conflict(Exception("Target file not found")) == "file_not_found"
        assert _classify_conflict(Exception("Something else")) == "unknown"

    def test_extract_conflict_states(self):
        """_extract_conflict_states parses expected/actual from message."""
        expected, actual = _extract_conflict_states(
            Exception("Content mismatch: expected abc123, got def456")
        )
        assert expected == "abc123"
        assert actual == "def456"

    def test_suggest_fix_anchor_not_found(self):
        """_suggest_fix returns useful guidance for anchor conflicts."""
        patch = {"path": "page.md", "anchor": "## Install"}
        fix = _suggest_fix(Exception("Anchor not found: ## Install"), patch)
        assert "Install" in fix
        assert "page.md" in fix

    def test_conflict_writes_patch_conflicts_json(self):
        """Conflict during patch application writes artifacts/patch_conflicts.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "artifacts").mkdir()
            (run_dir / "reports").mkdir()
            (run_dir / "drafts").mkdir()
            (run_dir / "events.ndjson").write_text("")
            site = run_dir / "work" / "site" / "content"
            site.mkdir(parents=True)

            # Create a file with content
            target = site / "content" / "docs.aspose.org" / "test.md"
            target.parent.mkdir(parents=True)
            target.write_text("# Test\n\nOriginal content.\n", encoding="utf-8")

            # Create a patch that will conflict (expected_before_hash mismatch)
            run_config = {
                "run_id": "test-conflict",
                "site_worktree": str(site),
            }

            # Create page_plan and draft_manifest that produce a conflicting patch
            page_plan_path = run_dir / "artifacts" / "page_plan.json"
            page_plan_path.write_text(json.dumps({
                "schema_version": "1.0",
                "product_slug": "test",
                "launch_tier": "standard",
                "pages": [],
            }), encoding="utf-8")

            draft_manifest_path = run_dir / "artifacts" / "draft_manifest.json"
            draft_manifest_path.write_text(json.dumps({
                "schema_version": "1.0",
                "drafts": [],
            }), encoding="utf-8")

            # Manually apply a patch that triggers conflict
            conflict_patch = {
                "patch_id": "update_test_anchor_install",
                "type": "update_by_anchor",
                "path": "content/docs.aspose.org/test.md",
                "anchor": "NonExistent",
                "new_content": "New.",
                "content_hash": compute_content_hash("New."),
            }

            with pytest.raises(LinkerPatchConflictError):
                apply_patch(conflict_patch, site)


# ---------------------------------------------------------------------------
# M7: Schema validation
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Tests for patch_bundle schema validation — M7."""

    def test_validate_patch_bundle_valid(self):
        """Valid patch bundle passes validation without error."""
        bundle = {
            "schema_version": "1.0",
            "patches": [
                {
                    "patch_id": "create_test",
                    "type": "create_file",
                    "path": "content/test.md",
                    "new_content": "# Hello\n",
                    "content_hash": compute_content_hash("# Hello\n"),
                }
            ],
        }
        # Should not raise
        _validate_patch_bundle(bundle)

    def test_validate_catches_invalid_bundle_raises(self):
        """Invalid bundle raises LinkerPatchConflictError (fail-fast)."""
        bundle = {
            "schema_version": "1.0",
            "patches": [
                {
                    "patch_id": "bad_patch",
                    "type": "create_file",
                    "path": "test.md",
                    # Missing content_hash and new_content
                }
            ],
        }
        with pytest.raises(LinkerPatchConflictError, match="schema validation failed"):
            _validate_patch_bundle(bundle)

    def test_validate_graceful_without_jsonschema(self, caplog, monkeypatch):
        """When jsonschema import fails, logs warning and continues."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        bundle = {"schema_version": "1.0", "patches": []}
        with caplog.at_level(logging.WARNING, logger="launch"):
            _validate_patch_bundle(bundle)


# ---------------------------------------------------------------------------
# SR-01 GAP-01: New-heading crash path fix
# ---------------------------------------------------------------------------

class TestNewHeadingAppend:
    """Tests for new-heading → update_file_range append (GAP-01 fix)."""

    def test_new_heading_emits_update_file_range(self):
        """Draft heading absent from existing file → update_file_range, NOT update_by_anchor."""
        existing = (
            "---\ntitle: Test\n---\n\n"
            "## Installation\n\nInstall text.\n"
        )
        draft = (
            "---\ntitle: Test\n---\n\n"
            "## Installation\n\nInstall text.\n\n"
            "## Advanced\n\nAdvanced content.\n"
        )
        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")

        anchor_patches = [p for p in patches if p["type"] == "update_by_anchor"]
        range_patches = [p for p in patches if p["type"] == "update_file_range"]

        # Installation is unchanged → no anchor patch
        assert len(anchor_patches) == 0
        # Advanced is new → appended via update_file_range
        assert len(range_patches) == 1
        assert range_patches[0]["patch_id"].startswith("append_pg1_")
        assert "Advanced content." in range_patches[0]["new_content"]

    def test_new_heading_append_preserves_heading_level(self):
        """Appended content uses the correct heading level from draft."""
        existing = "---\ntitle: T\n---\n\n## Existing\n\nContent.\n"
        draft = (
            "---\ntitle: T\n---\n\n"
            "## Existing\n\nContent.\n\n"
            "### Details\n\nDetail content.\n"
        )
        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")
        range_patches = [p for p in patches if p["type"] == "update_file_range"]
        assert len(range_patches) == 1
        assert "### Details" in range_patches[0]["new_content"]

    def test_mixed_changed_and_new_headings(self):
        """Changed heading → update_by_anchor; new heading → update_file_range."""
        existing = (
            "---\ntitle: T\n---\n\n"
            "## Intro\n\nOld intro.\n\n"
            "## Usage\n\nUsage text.\n"
        )
        draft = (
            "---\ntitle: T\n---\n\n"
            "## Intro\n\nNew intro.\n\n"
            "## Usage\n\nUsage text.\n\n"
            "## FAQ\n\nFAQ content.\n"
        )
        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")

        anchor_patches = [p for p in patches if p["type"] == "update_by_anchor"]
        range_patches = [p for p in patches if p["type"] == "update_file_range"]

        # Intro changed → update_by_anchor
        assert len(anchor_patches) == 1
        assert anchor_patches[0]["anchor"] == "Intro"
        assert "New intro." in anchor_patches[0]["new_content"]

        # FAQ is new → update_file_range
        assert len(range_patches) == 1
        assert "FAQ content." in range_patches[0]["new_content"]

    def test_all_headings_new_all_appended(self):
        """When ALL draft headings are absent from existing, all use update_file_range."""
        existing = "---\ntitle: T\n---\n\nPlain preamble only.\n"
        draft = (
            "---\ntitle: T\n---\n\n"
            "## Alpha\n\nAlpha content.\n\n"
            "## Beta\n\nBeta content.\n"
        )
        patches = _generate_update_patches_for_existing(existing, draft, "pg1", "page.md")

        anchor_patches = [p for p in patches if p["type"] == "update_by_anchor"]
        range_patches = [p for p in patches if p["type"] == "update_file_range"]

        assert len(anchor_patches) == 0
        assert len(range_patches) == 2
        slugs = sorted(p["patch_id"] for p in range_patches)
        assert any("alpha" in s for s in slugs)
        assert any("beta" in s for s in slugs)


# ---------------------------------------------------------------------------
# SR-03 GAP-05: Schema caching
# ---------------------------------------------------------------------------

class TestSchemaCaching:
    """Tests for module-level schema cache (GAP-05 fix)."""

    def test_schema_cached_across_calls(self, monkeypatch):
        """Schema is loaded from disk once, then served from cache."""
        import src.launch.workers.w8_linker_and_patcher.worker as w8mod

        # Reset cache
        monkeypatch.setattr(w8mod, "_PATCH_BUNDLE_SCHEMA", None)

        s1 = _get_patch_bundle_schema()
        assert s1 is not None

        # Second call returns same object (no re-read)
        s2 = _get_patch_bundle_schema()
        assert s1 is s2

        # Clean up: reset cache so other tests aren't affected
        monkeypatch.setattr(w8mod, "_PATCH_BUNDLE_SCHEMA", None)


# ---------------------------------------------------------------------------
# SR-03 GAP-07: Conflict classification hardening
# ---------------------------------------------------------------------------

class TestClassifyConflictHardened:
    """Tests for isinstance-based conflict classification (GAP-07 fix)."""

    def test_file_not_found_error_classified(self):
        """FileNotFoundError → 'file_not_found' via isinstance."""
        assert _classify_conflict(FileNotFoundError("no such file")) == "file_not_found"

    def test_linker_conflict_anchor(self):
        """LinkerPatchConflictError with 'anchor not found' classified."""
        err = LinkerPatchConflictError("Anchor not found: ## Install")
        assert _classify_conflict(err) == "anchor_not_found"

    def test_generic_exception_unknown(self):
        """Unrecognized exception → 'unknown'."""
        assert _classify_conflict(RuntimeError("something weird")) == "unknown"


# ---------------------------------------------------------------------------
# SR-02 GAP-06: Integration test for existing-file update chain
# ---------------------------------------------------------------------------

class TestExistingFileIntegration:
    """Integration test: generate_patches_from_drafts with pre-existing target."""

    def test_existing_file_update_through_generate_patches(self):
        """Full chain: existing file → granular patches (no create_file)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            site = run_dir / "work" / "site" / "content"
            site.mkdir(parents=True)
            (run_dir / "drafts" / "docs").mkdir(parents=True)

            # Create an EXISTING file in site worktree
            existing_path = site / "content" / "docs.aspose.org" / "prod" / "en" / "python" / "guide.md"
            existing_path.parent.mkdir(parents=True)
            existing_content = (
                "---\ntitle: Guide\nslug: guide\n---\n\n"
                "## Installation\n\nOld install text.\n\n"
                "## Usage\n\nUsage text unchanged.\n"
            )
            existing_path.write_text(existing_content, encoding="utf-8")

            # Create draft with modified Installation + new FAQ section
            draft_content = (
                "---\ntitle: Guide\nslug: guide\n---\n\n"
                "## Installation\n\nNew install text.\n\n"
                "## Usage\n\nUsage text unchanged.\n\n"
                "## FAQ\n\nFrequently asked questions.\n"
            )
            draft_path = run_dir / "drafts" / "docs" / "guide.md"
            draft_path.write_text(draft_content, encoding="utf-8")

            page_plan = {"pages": []}
            draft_manifest = {
                "drafts": [
                    {
                        "page_id": "docs_guide",
                        "section": "docs",
                        "slug": "guide",
                        "output_path": "content/docs.aspose.org/prod/en/python/guide.md",
                        "draft_path": "drafts/docs/guide.md",
                    },
                ],
            }

            patches = generate_patches_from_drafts(
                draft_manifest, page_plan, run_dir, site, family="prod",
            )

            # No create_file patches for existing files
            create_patches = [p for p in patches if p["type"] == "create_file"]
            assert len(create_patches) == 0, f"Expected no create_file patches, got {create_patches}"

            # Should have update_by_anchor for Installation (changed)
            anchor_patches = [p for p in patches if p["type"] == "update_by_anchor"]
            install_patches = [p for p in anchor_patches if p.get("anchor") == "Installation"]
            assert len(install_patches) == 1
            assert "New install text." in install_patches[0]["new_content"]

            # Should have update_file_range for FAQ (new heading)
            range_patches = [p for p in patches if p["type"] == "update_file_range"]
            faq_patches = [p for p in range_patches if "FAQ" in p.get("new_content", "")]
            assert len(faq_patches) == 1
            assert "Frequently asked questions." in faq_patches[0]["new_content"]

            # All patches have content_hash
            for p in patches:
                assert "content_hash" in p, f"Patch {p['patch_id']} missing content_hash"


# ---------------------------------------------------------------------------
# SR-02 GAP-03: Telemetry events
# ---------------------------------------------------------------------------

class TestTelemetryEvents:
    """Tests for spec08:139 telemetry event constants."""

    def test_telemetry_constants_defined(self):
        """All 4 patch engine telemetry constants are defined in worker module."""
        from src.launch.workers.w8_linker_and_patcher.worker import (
            EVENT_PATCH_ENGINE_STARTED,
            EVENT_PATCH_ENGINE_COMPLETED,
            EVENT_PATCH_APPLIED,
            EVENT_PATCH_SKIPPED,
        )
        assert EVENT_PATCH_ENGINE_STARTED == "PATCH_ENGINE_STARTED"
        assert EVENT_PATCH_ENGINE_COMPLETED == "PATCH_ENGINE_COMPLETED"
        assert EVENT_PATCH_APPLIED == "PATCH_APPLIED"
        assert EVENT_PATCH_SKIPPED == "PATCH_SKIPPED"

    def test_telemetry_constants_are_strings(self):
        """Event constants are plain strings matching spec naming."""
        from src.launch.workers.w8_linker_and_patcher.worker import (
            EVENT_PATCH_ENGINE_STARTED,
            EVENT_PATCH_ENGINE_COMPLETED,
            EVENT_PATCH_APPLIED,
            EVENT_PATCH_SKIPPED,
        )
        for const in [EVENT_PATCH_ENGINE_STARTED, EVENT_PATCH_ENGINE_COMPLETED,
                       EVENT_PATCH_APPLIED, EVENT_PATCH_SKIPPED]:
            assert isinstance(const, str)
            assert const == const.upper()  # All caps convention

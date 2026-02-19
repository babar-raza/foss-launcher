"""Tests for TC-1760 through TC-1764: Incremental Update Support.

Covers:
- TC-1760: RunLayout.load_previous_artifact / load_previous_drafts
- TC-1762: W2 claim merging (_normalize_claim_identity, _merge_claims_incremental)
- TC-1763: W4 page preservation (_apply_page_preservation)
- TC-1764: W5 draft reuse, W6 delete_file patch, W9 delta summary
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from launch.io.run_layout import RunLayout, create_run_skeleton


# ---------------------------------------------------------------------------
# TC-1760: RunLayout previous artifact loading
# ---------------------------------------------------------------------------

class TestRunLayoutPreviousArtifact:
    """Tests for RunLayout.load_previous_artifact()."""

    def test_returns_none_when_no_previous_path(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        result = layout.load_previous_artifact("product_facts.json", None)
        assert result is None

    def test_returns_none_when_empty_previous_path(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        result = layout.load_previous_artifact("product_facts.json", "")
        assert result is None

    def test_returns_none_when_artifact_missing(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        prev_dir.mkdir()
        (prev_dir / "artifacts").mkdir()
        result = layout.load_previous_artifact("nonexistent.json", str(prev_dir))
        assert result is None

    def test_loads_valid_json_artifact(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)

        data = {"claims": [{"claim_id": "c1", "claim_text": "test"}]}
        (prev_dir / "artifacts" / "product_facts.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        result = layout.load_previous_artifact("product_facts.json", str(prev_dir))
        assert result is not None
        assert result["claims"][0]["claim_id"] == "c1"

    def test_returns_none_on_invalid_json(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)
        (prev_dir / "artifacts" / "bad.json").write_text("not json!", encoding="utf-8")

        result = layout.load_previous_artifact("bad.json", str(prev_dir))
        assert result is None


class TestRunLayoutPreviousDrafts:
    """Tests for RunLayout.load_previous_drafts()."""

    def test_returns_empty_when_no_previous_path(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        result = layout.load_previous_drafts(None)
        assert result == {}

    def test_returns_empty_when_drafts_dir_missing(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        prev_dir.mkdir()
        result = layout.load_previous_drafts(str(prev_dir))
        assert result == {}

    def test_loads_all_md_files(self, tmp_path: Path):
        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        drafts = prev_dir / "drafts"

        # Create draft structure
        (drafts / "docs").mkdir(parents=True)
        (drafts / "kb").mkdir(parents=True)
        (drafts / "docs" / "guide.md").write_text("# Guide\nContent here", encoding="utf-8")
        (drafts / "kb" / "faq.md").write_text("# FAQ\nQ&A here", encoding="utf-8")

        result = layout.load_previous_drafts(str(prev_dir))
        assert len(result) == 2
        # Check content is loaded
        values = list(result.values())
        assert any("# Guide" in v for v in values)
        assert any("# FAQ" in v for v in values)


# ---------------------------------------------------------------------------
# TC-1762: W2 Claim Merging
# ---------------------------------------------------------------------------

class TestNormalizeClaimIdentity:
    """Tests for _normalize_claim_identity()."""

    def test_basic_normalization(self):
        from launch.workers.w2_facts_builder.worker import _normalize_claim_identity

        result = _normalize_claim_identity("Hello World", "feature")
        assert result == "feature::hello world"

    def test_whitespace_normalization(self):
        from launch.workers.w2_facts_builder.worker import _normalize_claim_identity

        result1 = _normalize_claim_identity("Hello   World", "feature")
        result2 = _normalize_claim_identity("Hello World", "feature")
        assert result1 == result2

    def test_case_insensitive(self):
        from launch.workers.w2_facts_builder.worker import _normalize_claim_identity

        result1 = _normalize_claim_identity("Hello World", "Feature")
        result2 = _normalize_claim_identity("hello world", "feature")
        assert result1 == result2

    def test_different_kinds_produce_different_keys(self):
        from launch.workers.w2_facts_builder.worker import _normalize_claim_identity

        result1 = _normalize_claim_identity("Hello", "feature")
        result2 = _normalize_claim_identity("Hello", "limitation")
        assert result1 != result2


class TestMergeClaimsIncremental:
    """Tests for _merge_claims_incremental()."""

    def _make_claim(self, claim_id: str, text: str, kind: str = "feature") -> Dict[str, Any]:
        return {
            "claim_id": claim_id,
            "claim_text": text,
            "claim_kind": kind,
            "truth_status": "fact",
            "citations": [{"path": "README.md", "start_line": 1, "end_line": 1}],
        }

    def test_no_previous_claims_returns_current(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [self._make_claim("c1", "Feature A")]
        merged, meta = _merge_claims_incremental(current, {"claims": []})

        assert len(merged) == 1
        assert merged[0]["claim_id"] == "c1"
        assert meta["matched"] == 0
        assert meta["new"] == 1
        assert meta["deprecated"] == 0

    def test_matched_claims_preserve_old_id(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [self._make_claim("new-id", "Feature A", "feature")]
        previous = {"claims": [self._make_claim("old-id", "Feature A", "feature")]}

        merged, meta = _merge_claims_incremental(current, previous)

        assert len(merged) == 1
        assert merged[0]["claim_id"] == "old-id"  # Preserved old ID
        assert meta["matched"] == 1
        assert meta["new"] == 0

    def test_new_claims_keep_new_id(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [
            self._make_claim("c1", "Feature A"),
            self._make_claim("c2", "Brand New Feature"),
        ]
        previous = {"claims": [self._make_claim("old-c1", "Feature A")]}

        merged, meta = _merge_claims_incremental(current, previous)

        assert meta["matched"] == 1
        assert meta["new"] == 1
        # Find the new claim
        new_claim = next(c for c in merged if c["claim_text"] == "Brand New Feature")
        assert new_claim["claim_id"] == "c2"

    def test_deprecated_claims_added_with_flag(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [self._make_claim("c1", "Feature A")]
        previous = {"claims": [
            self._make_claim("old-c1", "Feature A"),
            self._make_claim("old-c2", "Removed Feature"),
        ]}

        merged, meta = _merge_claims_incremental(current, previous)

        assert meta["deprecated"] == 1
        deprecated = [c for c in merged if c.get("deprecated")]
        assert len(deprecated) == 1
        assert deprecated[0]["claim_text"] == "Removed Feature"

    def test_metadata_has_all_fields(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [self._make_claim("c1", "A"), self._make_claim("c2", "B")]
        previous = {"claims": [self._make_claim("p1", "A"), self._make_claim("p2", "C")]}

        _, meta = _merge_claims_incremental(current, previous)

        assert meta["merge_performed"] is True
        assert "previous_claim_count" in meta
        assert "current_claim_count" in meta
        assert "matched" in meta
        assert "new" in meta
        assert "deprecated" in meta
        assert "final_claim_count" in meta
        assert meta["final_claim_count"] == meta["matched"] + meta["new"] + meta["deprecated"]

    def test_case_insensitive_matching(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [self._make_claim("new-c1", "feature a")]
        previous = {"claims": [self._make_claim("old-c1", "Feature A")]}

        merged, meta = _merge_claims_incremental(current, previous)

        assert meta["matched"] == 1
        assert merged[0]["claim_id"] == "old-c1"

    def test_empty_previous_facts(self):
        from launch.workers.w2_facts_builder.worker import _merge_claims_incremental

        current = [self._make_claim("c1", "Feature A")]
        merged, meta = _merge_claims_incremental(current, {})

        assert len(merged) == 1
        assert meta["new"] == 1
        assert meta["previous_claim_count"] == 0


# ---------------------------------------------------------------------------
# TC-1763: W4 Page Preservation
# ---------------------------------------------------------------------------

class TestApplyPagePreservation:
    """Tests for _apply_page_preservation()."""

    def _make_page(
        self, section: str, slug: str, claim_ids: List[str]
    ) -> Dict[str, Any]:
        return {
            "section": section,
            "slug": slug,
            "required_claim_ids": claim_ids,
            "title": f"{section}/{slug}",
            "output_path": f"content/{section}/{slug}/_index.md",
        }

    def test_noop_when_incremental_disabled(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        page_plan = {"pages": [self._make_page("docs", "guide", ["c1"])]}
        run_config = {"incremental": {"enabled": False}}

        result = _apply_page_preservation(page_plan, run_config, layout)
        # Should return unchanged — no page_status added
        assert "page_status" not in result["pages"][0]

    def test_noop_when_no_incremental_config(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        page_plan = {"pages": [self._make_page("docs", "guide", ["c1"])]}
        run_config = {}

        result = _apply_page_preservation(page_plan, run_config, layout)
        assert "page_status" not in result["pages"][0]

    def test_all_new_when_no_previous_plan(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)
        # No page_plan.json in prev_run

        page_plan = {"pages": [self._make_page("docs", "guide", ["c1"])]}
        run_config = {
            "incremental": {
                "enabled": True,
                "previous_run_path": str(prev_dir),
            }
        }

        result = _apply_page_preservation(page_plan, run_config, layout)
        assert result["pages"][0]["page_status"] == "new"

    def test_preserved_when_high_overlap(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)

        # Previous plan has same page with same claims
        prev_plan = {"pages": [self._make_page("docs", "guide", ["c1", "c2", "c3"])]}
        (prev_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(prev_plan), encoding="utf-8"
        )

        # Current plan: 3 of 4 claims match (75% overlap)
        page_plan = {"pages": [self._make_page("docs", "guide", ["c1", "c2", "c3", "c4"])]}
        run_config = {
            "incremental": {
                "enabled": True,
                "previous_run_path": str(prev_dir),
                "page_preservation_threshold": 0.75,
            }
        }

        result = _apply_page_preservation(page_plan, run_config, layout)
        assert result["pages"][0]["page_status"] == "preserved"

    def test_updated_when_low_overlap(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)

        # Previous: claims c1, c2
        prev_plan = {"pages": [self._make_page("docs", "guide", ["c1", "c2"])]}
        (prev_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(prev_plan), encoding="utf-8"
        )

        # Current: claims c3, c4 (completely different)
        page_plan = {"pages": [self._make_page("docs", "guide", ["c3", "c4"])]}
        run_config = {
            "incremental": {
                "enabled": True,
                "previous_run_path": str(prev_dir),
                "page_preservation_threshold": 0.75,
            }
        }

        result = _apply_page_preservation(page_plan, run_config, layout)
        assert result["pages"][0]["page_status"] == "updated"

    def test_deleted_pages_added(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)

        # Previous had a page that's no longer in current
        prev_plan = {"pages": [
            self._make_page("docs", "guide", ["c1"]),
            self._make_page("docs", "old-page", ["c5", "c6"]),
        ]}
        (prev_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(prev_plan), encoding="utf-8"
        )

        page_plan = {"pages": [self._make_page("docs", "guide", ["c1"])]}
        run_config = {
            "incremental": {
                "enabled": True,
                "previous_run_path": str(prev_dir),
            }
        }

        result = _apply_page_preservation(page_plan, run_config, layout)

        # Should have 2 pages: preserved guide + deleted old-page
        statuses = {p["slug"]: p["page_status"] for p in result["pages"]}
        assert statuses["guide"] == "preserved"
        assert statuses["old-page"] == "deleted"

    def test_empty_claims_both_sides_is_preserved(self, tmp_path: Path):
        from launch.workers.w4_ia_planner.worker import _apply_page_preservation

        layout = RunLayout(run_dir=tmp_path)
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)

        prev_plan = {"pages": [self._make_page("docs", "guide", [])]}
        (prev_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(prev_plan), encoding="utf-8"
        )

        page_plan = {"pages": [self._make_page("docs", "guide", [])]}
        run_config = {
            "incremental": {
                "enabled": True,
                "previous_run_path": str(prev_dir),
            }
        }

        result = _apply_page_preservation(page_plan, run_config, layout)
        assert result["pages"][0]["page_status"] == "preserved"


# ---------------------------------------------------------------------------
# TC-1764: W6 delete_file patch + W9 delta summary
# ---------------------------------------------------------------------------

class TestDeleteFilePatch:
    """Tests for W6 _apply_delete_file_patch and generate_patches_from_drafts delete support."""

    def test_delete_patch_removes_file(self, tmp_path: Path):
        from launch.workers.w8_linker_and_patcher.worker import _apply_delete_file_patch

        target = tmp_path / "content" / "page.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Old Content", encoding="utf-8")

        patch = {"patch_id": "delete_test", "type": "delete_file", "path": "content/page.md"}
        result = _apply_delete_file_patch(patch, target)

        assert result["status"] == "applied"
        assert not target.exists()

    def test_delete_patch_skips_missing_file(self, tmp_path: Path):
        from launch.workers.w8_linker_and_patcher.worker import _apply_delete_file_patch

        target = tmp_path / "content" / "nonexistent.md"
        patch = {"patch_id": "delete_test", "type": "delete_file", "path": "content/nonexistent.md"}

        result = _apply_delete_file_patch(patch, target)
        assert result["status"] == "skipped"

    def test_apply_patch_routes_delete_type(self, tmp_path: Path):
        from launch.workers.w8_linker_and_patcher.worker import apply_patch

        site = tmp_path / "site"
        site.mkdir()
        target = site / "page.md"
        target.write_text("old", encoding="utf-8")

        patch = {"patch_id": "del1", "type": "delete_file", "path": "page.md"}
        result = apply_patch(patch, site)
        assert result["status"] == "applied"
        assert not target.exists()


class TestW9DeltaSummary:
    """Tests for W9 generate_pr_body with incremental delta."""

    def test_pr_body_includes_incremental_section(self):
        from launch.workers.w11_pr_manager.worker import generate_pr_body

        validation_report = {"ok": True, "profile": "local", "gates": [], "issues": []}
        patch_bundle = {"patches": [
            {"type": "create_file", "path": "new.md"},
            {"type": "delete_file", "path": "old.md"},
        ]}
        run_config = {
            "incremental": {
                "enabled": True,
                "previous_run_path": "/tmp/prev-run",
            }
        }

        body = generate_pr_body("run-123", "test-product", validation_report, patch_bundle, run_config)

        assert "Incremental Update Summary" in body
        assert "Previous run" in body
        assert "Deleted" in body

    def test_pr_body_no_incremental_section_when_disabled(self):
        from launch.workers.w11_pr_manager.worker import generate_pr_body

        validation_report = {"ok": True, "profile": "local", "gates": [], "issues": []}
        patch_bundle = {"patches": [{"type": "create_file", "path": "new.md"}]}
        run_config = {}

        body = generate_pr_body("run-123", "test-product", validation_report, patch_bundle, run_config)

        assert "Incremental Update Summary" not in body

    def test_pr_body_shows_delete_count(self):
        from launch.workers.w11_pr_manager.worker import generate_pr_body

        validation_report = {"ok": True, "profile": "local", "gates": [], "issues": []}
        patch_bundle = {"patches": [
            {"type": "delete_file", "path": "old1.md"},
            {"type": "delete_file", "path": "old2.md"},
        ]}
        run_config = {}

        body = generate_pr_body("run-123", "test-product", validation_report, patch_bundle, run_config)

        # Even without incremental mode, delete count should appear in Changes section
        assert "Files Deleted" in body
        assert "2" in body

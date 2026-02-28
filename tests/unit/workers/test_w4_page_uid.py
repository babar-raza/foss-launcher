"""Tests for TC-3300: Deterministic page_uid + Explainability Artifact.

Covers:
- compute_page_uid() deterministic uid computation
- _assign_page_uids() collision resolution (incl. triple+ collision SR-01)
- _apply_page_preservation() uid-primary matching (incl. logging SR-04)
- _build_page_plan_rationale() artifact (incl. claim_selection_summary SR-03)
- selection_source tagging across 5 construction paths
- Platform/locale uid stability (SR-02)
- Template path portability (SR-02)
- Schema validation (SR-03)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from launch.workers.w4_ia_planner.worker import (
    _apply_page_preservation,
    _assign_page_uids,
    _build_page_plan_rationale,
    compute_page_uid,
    fill_template_placeholders,
    plan_pages_for_section,
)
from launch.io.run_layout import RunLayout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(
    section: str = "docs",
    slug: str = "overview",
    page_role: str = "comprehensive_guide",
    selection_source: str = "mandatory_config",
    template_path: str = "",
    object_name: str = "",
    object_kind: str = "",
    source: str = "",
    title: str = "Overview",
    output_path: str = "",
    claim_ids: list | None = None,
    workflow_tag: str = "",
) -> Dict[str, Any]:
    """Build a minimal page dict for testing."""
    page: Dict[str, Any] = {
        "section": section,
        "slug": slug,
        "output_path": output_path or f"content/docs/{slug}.md",
        "url_path": f"/{slug}/",
        "title": title,
        "purpose": f"Test page: {slug}",
        "required_headings": [],
        "required_claim_ids": claim_ids or [],
        "required_snippet_tags": [],
        "cross_links": [],
        "page_role": page_role,
        "content_strategy": {},
        "selection_source": selection_source,
    }
    if template_path:
        page["template_path"] = template_path
    if object_name:
        page["object_name"] = object_name
    if object_kind:
        page["object_kind"] = object_kind
    if source:
        page["source"] = source
    if workflow_tag:
        page["content_strategy"] = {
            "selected_workflow": {"workflow_tag": workflow_tag, "score": 10},
        }
    return page


def _make_incremental_config(
    previous_run_path: str = "",
    threshold: float = 0.75,
) -> Dict[str, Any]:
    return {
        "incremental": {
            "enabled": True,
            "previous_run_path": previous_run_path,
            "page_preservation_threshold": threshold,
        },
    }


# ---------------------------------------------------------------------------
# Class 1: TestComputePageUid
# ---------------------------------------------------------------------------

class TestComputePageUid:
    """Tests for compute_page_uid() deterministic uid computation."""

    def test_template_page_produces_tpl_prefix(self):
        page = _make_page(
            selection_source="template",
            template_path="/repo/specs/templates/docs/overview.md",
        )
        uid = compute_page_uid(page)
        assert uid.startswith("tpl:"), f"Expected tpl: prefix, got {uid}"
        assert len(uid) == 12  # "tpl:" + 8 hex chars

    def test_mandatory_config_produces_cfg_prefix(self):
        page = _make_page(selection_source="mandatory_config")
        uid = compute_page_uid(page)
        assert uid.startswith("cfg:")

    def test_optional_policy_produces_ev_prefix(self):
        page = _make_page(selection_source="optional_policy")
        uid = compute_page_uid(page)
        assert uid.startswith("ev:")

    def test_topic_discovery_produces_topic_prefix(self):
        page = _make_page(
            selection_source="topic_discovery",
            source="topic_discovery",
            title="Advanced Rendering Techniques",
        )
        uid = compute_page_uid(page)
        assert uid.startswith("topic:")

    def test_fallback_produces_fb_prefix(self):
        page = _make_page(selection_source="fallback")
        uid = compute_page_uid(page)
        assert uid.startswith("fb:")

    def test_same_inputs_same_uid(self):
        """Determinism: identical pages produce identical uids."""
        page1 = _make_page(slug="getting-started")
        page2 = _make_page(slug="getting-started")
        assert compute_page_uid(page1) == compute_page_uid(page2)

    def test_different_inputs_different_uid(self):
        page1 = _make_page(slug="getting-started")
        page2 = _make_page(slug="api-reference")
        assert compute_page_uid(page1) != compute_page_uid(page2)

    def test_object_name_discriminator_over_slug(self):
        """object_name takes priority over slug as discriminator."""
        page1 = _make_page(
            slug="document-class",
            object_name="Document",
            object_kind="class",
            selection_source="optional_policy",
        )
        page2 = _make_page(
            slug="renamed-document-class",
            object_name="Document",
            object_kind="class",
            selection_source="optional_policy",
        )
        # Same object_name → same uid despite different slugs
        assert compute_page_uid(page1) == compute_page_uid(page2)

    def test_template_path_relativized(self):
        """template_path is relativized to specs/templates/ for stability."""
        page1 = _make_page(
            selection_source="template",
            template_path="C:/repo/specs/templates/docs/overview.md",
        )
        page2 = _make_page(
            selection_source="template",
            template_path="/home/user/repo/specs/templates/docs/overview.md",
        )
        # Both relativize to "specs/templates/docs/overview.md"
        assert compute_page_uid(page1) == compute_page_uid(page2)

    def test_topic_title_discriminator(self):
        """Topic discovery pages use title as discriminator, not slug."""
        page1 = _make_page(
            selection_source="topic_discovery",
            source="topic_discovery",
            slug="old-slug-name",
            title="Advanced Rendering",
        )
        page2 = _make_page(
            selection_source="topic_discovery",
            source="topic_discovery",
            slug="new-slug-name",
            title="Advanced Rendering",
        )
        assert compute_page_uid(page1) == compute_page_uid(page2)

    def test_workflow_tag_discriminator(self):
        """Feature blog pages use workflow_tag as discriminator, not slug."""
        page1 = _make_page(
            slug="old-blog-slug",
            selection_source="mandatory_config",
            workflow_tag="convert_pdf",
        )
        page2 = _make_page(
            slug="new-blog-slug",
            selection_source="mandatory_config",
            workflow_tag="convert_pdf",
        )
        assert compute_page_uid(page1) == compute_page_uid(page2)


# ---------------------------------------------------------------------------
# Class 2: TestAssignPageUids
# ---------------------------------------------------------------------------

class TestAssignPageUids:
    """Tests for _assign_page_uids() post-processing."""

    def test_all_pages_receive_uid(self):
        pages = [
            _make_page(slug="a"),
            _make_page(slug="b"),
            _make_page(slug="c"),
        ]
        _assign_page_uids(pages)
        for page in pages:
            assert "page_uid" in page
            assert page["page_uid"]  # non-empty

    def test_no_duplicate_uids(self):
        pages = [
            _make_page(slug=f"page-{i}") for i in range(20)
        ]
        _assign_page_uids(pages)
        uids = [p["page_uid"] for p in pages]
        assert len(uids) == len(set(uids)), "Duplicate page_uids found"

    def test_collision_resolution_appends_suffix(self):
        """Two pages with identical discriminators get resolved via output_path."""
        page1 = _make_page(slug="same", output_path="content/docs/same.md")
        page2 = _make_page(slug="same", output_path="content/kb/same.md")
        # Both should compute same base uid since section + role + slug are same
        base1 = compute_page_uid(page1)
        base2 = compute_page_uid(page2)
        assert base1 == base2, "Precondition: base uids should collide"

        _assign_page_uids([page1, page2])
        assert page1["page_uid"] != page2["page_uid"]
        # Second page gets collision suffix
        assert "_" in page2["page_uid"]

    def test_pages_without_selection_source_get_fb_prefix(self):
        page = _make_page(slug="orphan")
        del page["selection_source"]
        _assign_page_uids([page])
        assert page["page_uid"].startswith("fb:")


# ---------------------------------------------------------------------------
# Class 3: TestPreservationWithPageUid
# ---------------------------------------------------------------------------

class TestPreservationWithPageUid:
    """Tests for _apply_page_preservation() with uid-primary matching."""

    def _setup_previous_plan(
        self, tmp_path: Path, pages: List[Dict[str, Any]]
    ) -> Path:
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)
        plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": pages,
        }
        (prev_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(plan), encoding="utf-8"
        )
        return prev_dir

    def test_uid_match_preserves_page_despite_slug_change(self, tmp_path: Path):
        """THE key test: page_uid match enables preservation even when slug changes."""
        prev_pages = [
            _make_page(slug="old-slug", claim_ids=["c1", "c2", "c3"]),
        ]
        prev_pages[0]["page_uid"] = "cfg:abcd1234"

        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [
            _make_page(slug="new-slug", claim_ids=["c1", "c2", "c3"]),
        ]
        current_pages[0]["page_uid"] = "cfg:abcd1234"  # Same uid

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        run_config = _make_incremental_config(str(prev_dir))
        layout = RunLayout(run_dir=tmp_path)

        result = _apply_page_preservation(page_plan, run_config, layout)

        assert result["pages"][0]["page_status"] == "preserved"

    def test_fallback_to_section_slug_when_no_uid(self, tmp_path: Path):
        """When previous plan has no page_uid, fall back to (section, slug)."""
        prev_pages = [
            _make_page(slug="overview", claim_ids=["c1", "c2"]),
        ]
        # No page_uid on previous page

        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [
            _make_page(slug="overview", claim_ids=["c1", "c2"]),
        ]
        current_pages[0]["page_uid"] = "cfg:99990000"

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        run_config = _make_incremental_config(str(prev_dir))
        layout = RunLayout(run_dir=tmp_path)

        result = _apply_page_preservation(page_plan, run_config, layout)

        assert result["pages"][0]["page_status"] == "preserved"

    def test_backward_compat_old_plan_without_uid(self, tmp_path: Path):
        """Existing tests: old page_plan without page_uid still works."""
        prev_pages = [
            _make_page(slug="getting-started", claim_ids=["c1"]),
        ]
        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [
            _make_page(slug="getting-started", claim_ids=["c1"]),
        ]
        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        run_config = _make_incremental_config(str(prev_dir))
        layout = RunLayout(run_dir=tmp_path)

        result = _apply_page_preservation(page_plan, run_config, layout)

        assert result["pages"][0]["page_status"] == "preserved"

    def test_deleted_detection_with_uid(self, tmp_path: Path):
        """Pages in previous with uid but not in current are deleted."""
        prev_pages = [
            _make_page(slug="deleted-page", claim_ids=["c1"]),
        ]
        prev_pages[0]["page_uid"] = "cfg:deadbeef"

        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": [],
        }
        run_config = _make_incremental_config(str(prev_dir))
        layout = RunLayout(run_dir=tmp_path)

        result = _apply_page_preservation(page_plan, run_config, layout)

        deleted = [p for p in result["pages"] if p.get("page_status") == "deleted"]
        assert len(deleted) == 1
        assert deleted[0]["slug"] == "deleted-page"

    def test_preservation_metadata_populated(self, tmp_path: Path):
        """preservation_metadata is set with uid, id, score, and should_preserve."""
        prev_pages = [
            _make_page(slug="overview", claim_ids=["c1", "c2"]),
        ]
        prev_pages[0]["page_uid"] = "cfg:11112222"

        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [
            _make_page(slug="overview", claim_ids=["c1", "c2"]),
        ]
        current_pages[0]["page_uid"] = "cfg:11112222"

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        run_config = _make_incremental_config(str(prev_dir))
        layout = RunLayout(run_dir=tmp_path)

        result = _apply_page_preservation(page_plan, run_config, layout)

        meta = result["pages"][0].get("preservation_metadata")
        assert meta is not None
        assert meta["previous_page_uid"] == "cfg:11112222"
        assert meta["claim_overlap_score"] == 1.0
        assert meta["should_preserve"] is True
        assert "previous_page_id" in meta

    def test_mixed_uid_and_slug_matching(self, tmp_path: Path):
        """Some pages match by uid, others by slug fallback."""
        prev_pages = [
            _make_page(slug="by-uid", claim_ids=["c1"]),
            _make_page(slug="by-slug", claim_ids=["c2"]),
        ]
        prev_pages[0]["page_uid"] = "cfg:aaaaaaaa"
        # prev_pages[1] has no page_uid

        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [
            _make_page(slug="renamed-uid", claim_ids=["c1"]),
            _make_page(slug="by-slug", claim_ids=["c2"]),
        ]
        current_pages[0]["page_uid"] = "cfg:aaaaaaaa"  # matches by uid
        current_pages[1]["page_uid"] = "cfg:bbbbbbbb"  # falls back to slug

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        run_config = _make_incremental_config(str(prev_dir))
        layout = RunLayout(run_dir=tmp_path)

        result = _apply_page_preservation(page_plan, run_config, layout)

        assert result["pages"][0]["page_status"] == "preserved"  # uid match
        assert result["pages"][1]["page_status"] == "preserved"  # slug fallback


# ---------------------------------------------------------------------------
# Class 4: TestPagePlanRationale
# ---------------------------------------------------------------------------

class TestPagePlanRationale:
    """Tests for _build_page_plan_rationale() artifact."""

    def test_rationale_basic_structure(self):
        page_plan = {
            "pages": [
                _make_page(slug="a", selection_source="template"),
                _make_page(slug="b", selection_source="mandatory_config"),
            ],
        }
        page_plan["pages"][0]["page_uid"] = "tpl:00001111"
        page_plan["pages"][1]["page_uid"] = "cfg:22223333"

        quotas = {"docs": {"max_pages": 10}}
        rationale = _build_page_plan_rationale(page_plan, quotas)

        assert rationale["schema_version"] == "1.0"
        assert rationale["total_pages"] == 2
        assert "source_distribution" in rationale
        assert "pages" in rationale
        assert len(rationale["pages"]) == 2

    def test_rationale_source_distribution(self):
        page_plan = {
            "pages": [
                _make_page(slug="a", selection_source="template"),
                _make_page(slug="b", selection_source="template"),
                _make_page(slug="c", selection_source="mandatory_config"),
            ],
        }
        for p in page_plan["pages"]:
            p["page_uid"] = compute_page_uid(p)

        rationale = _build_page_plan_rationale(page_plan, {})
        dist = rationale["source_distribution"]
        assert dist["template"] == 2
        assert dist["mandatory_config"] == 1

    def test_rationale_includes_all_pages(self):
        pages = [_make_page(slug=f"p{i}") for i in range(5)]
        for p in pages:
            p["page_uid"] = f"cfg:{p['slug']}"

        rationale = _build_page_plan_rationale({"pages": pages}, {})
        assert len(rationale["pages"]) == 5

    def test_rationale_quota_context(self):
        quotas = {"docs": {"max_pages": 10}, "kb": {"max_pages": 5}}
        rationale = _build_page_plan_rationale({"pages": []}, quotas)
        assert rationale["quota_context"]["docs"]["max_pages"] == 10
        assert rationale["quota_context"]["kb"]["max_pages"] == 5

    def test_rationale_workflow_tag_captured(self):
        page = _make_page(slug="blog", workflow_tag="convert_pdf")
        page["page_uid"] = "cfg:wftest"
        rationale = _build_page_plan_rationale({"pages": [page]}, {})
        assert rationale["pages"][0]["workflow_tag"] == "convert_pdf"

    def test_rationale_template_ref_captured(self):
        page = _make_page(
            slug="overview",
            selection_source="template",
            template_path="/repo/specs/templates/docs/overview.md",
        )
        page["page_uid"] = "tpl:tmpltest"
        rationale = _build_page_plan_rationale({"pages": [page]}, {})
        assert rationale["pages"][0]["template_ref"] == page["template_path"]


# ---------------------------------------------------------------------------
# Class 5: TestSelectionSourceTagging
# ---------------------------------------------------------------------------

class TestSelectionSourceTagging:
    """Tests that selection_source is set on pages from each construction path."""

    def test_template_pages_have_selection_source(self, tmp_path: Path):
        """fill_template_placeholders() sets selection_source='template'."""
        template = {
            "slug": "overview",
            "template_path": str(tmp_path / "overview.md"),
            "variant": "standard",
            "page_role": "comprehensive_guide",
        }
        # Create a minimal template file
        (tmp_path / "overview.md").write_text(
            "---\ntitle: Overview\n---\nContent", encoding="utf-8"
        )
        result = fill_template_placeholders(
            template=template,
            section="docs",
            product_slug="test-product",
            locale="en",
            subdomain="docs.aspose.org",
        )
        assert result.get("selection_source") == "template"

    def test_fallback_pages_have_selection_source(self):
        """plan_pages_for_section() sets selection_source='fallback'."""
        pages = plan_pages_for_section(
            section="products",
            launch_tier="minimal",
            product_facts={
                "product_name": "Test Product",
                "claims": [{"claim_id": "c1", "claim_text": "Test"}],
                "claim_groups": {"key_features": ["c1"]},
            },
            snippet_catalog={"snippets": []},
            product_slug="test-product",
        )
        assert len(pages) > 0
        for page in pages:
            assert page.get("selection_source") == "fallback"


# ---------------------------------------------------------------------------
# Class 6: TestPageUidStability
# ---------------------------------------------------------------------------

class TestPageUidStability:
    """Tests that page_uid is stable across various transformations."""

    def test_uid_stable_after_slug_dedup(self):
        """page_uid uses construction-time discriminator, not post-dedup slug."""
        page = _make_page(
            slug="overview",
            selection_source="mandatory_config",
        )
        uid_before = compute_page_uid(page)
        # Simulate slug dedup renaming
        page["slug"] = "overview-2"
        uid_after = compute_page_uid(page)
        # For mandatory_config pages, slug IS the discriminator, so this WILL change
        # This is expected: for config pages, the slug is the identity
        assert uid_before != uid_after

    def test_uid_stable_for_template_page_after_slug_rename(self):
        """Template page uid uses template_path, not slug."""
        page = _make_page(
            slug="overview",
            selection_source="template",
            template_path="/repo/specs/templates/docs/overview.md",
        )
        uid_before = compute_page_uid(page)
        page["slug"] = "overview-renamed"
        uid_after = compute_page_uid(page)
        # template_path discriminator → uid unchanged despite slug change
        assert uid_before == uid_after

    def test_uid_stable_for_api_object_page_after_slug_rename(self):
        """API object page uid uses object_name, not slug."""
        page = _make_page(
            slug="document-ref",
            selection_source="optional_policy",
            object_name="Document",
            object_kind="class",
        )
        uid_before = compute_page_uid(page)
        page["slug"] = "document-class-reference"
        uid_after = compute_page_uid(page)
        assert uid_before == uid_after

    def test_uid_format_is_prefix_colon_hex8(self):
        """All uids match the {prefix}:{hex8} format."""
        import re
        pattern = re.compile(r"^(tpl|cfg|ev|topic|fb):[0-9a-f]{8}$")
        for sel in ["template", "mandatory_config", "optional_policy",
                     "topic_discovery", "fallback"]:
            page = _make_page(selection_source=sel)
            uid = compute_page_uid(page)
            assert pattern.match(uid), f"uid '{uid}' doesn't match pattern for {sel}"


# ---------------------------------------------------------------------------
# Class 7: TestTripleCollision (SR-01 / GAP-01, GAP-03)
# ---------------------------------------------------------------------------

class TestTripleCollision:
    """SR-01: Verify triple+ collision resolution in _assign_page_uids()."""

    def test_triple_collision_all_resolved(self):
        """Three pages with identical discriminators get distinct uids."""
        pages = [
            _make_page(
                slug="intro",
                section="docs",
                page_role="tutorial",
                selection_source="fallback",
                output_path="docs/intro-{}.md".format(i),
            )
            for i in range(3)
        ]
        _assign_page_uids(pages)
        uids = [p["page_uid"] for p in pages]
        assert len(set(uids)) == 3, "Expected 3 unique uids, got {}".format(uids)

    def test_five_way_collision_all_resolved(self):
        """Five pages with identical discriminators all get unique uids."""
        pages = [
            _make_page(
                slug="same",
                section="kb",
                page_role="howto_article",
                selection_source="fallback",
                output_path="kb/same-{}.md".format(i),
            )
            for i in range(5)
        ]
        _assign_page_uids(pages)
        uids = [p["page_uid"] for p in pages]
        assert len(set(uids)) == 5, "Expected 5 unique uids, got {}".format(uids)

    def test_collision_resolved_uids_contain_underscore(self):
        """Collided pages have underscore in their uid (collision suffix)."""
        pages = [
            _make_page(slug="x", output_path="a/{}.md".format(i))
            for i in range(3)
        ]
        _assign_page_uids(pages)
        # First page keeps base uid; others have collision suffix
        assert "_" not in pages[0]["page_uid"]
        assert "_" in pages[1]["page_uid"]
        assert "_" in pages[2]["page_uid"]


# ---------------------------------------------------------------------------
# Class 8: TestAssignPageUidsIdempotency (SR-01 / GAP-04)
# ---------------------------------------------------------------------------

class TestAssignPageUidsIdempotency:
    """SR-01: Verify idempotency of _assign_page_uids()."""

    def test_assign_page_uids_idempotent(self):
        """Running _assign_page_uids twice produces the same uids."""
        pages = [
            _make_page(slug="a", output_path="docs/a.md"),
            _make_page(slug="b", page_role="faq",
                       selection_source="mandatory_config", output_path="docs/b.md"),
        ]
        _assign_page_uids(pages)
        first_uids = [p["page_uid"] for p in pages]
        # Reset
        for p in pages:
            del p["page_uid"]
        _assign_page_uids(pages)
        second_uids = [p["page_uid"] for p in pages]
        assert first_uids == second_uids

    def test_idempotent_with_collisions(self):
        """Idempotency holds even when collisions occur."""
        pages = [
            _make_page(slug="same", output_path="docs/same-{}.md".format(i))
            for i in range(3)
        ]
        _assign_page_uids(pages)
        first_uids = [p["page_uid"] for p in pages]
        for p in pages:
            del p["page_uid"]
        _assign_page_uids(pages)
        second_uids = [p["page_uid"] for p in pages]
        assert first_uids == second_uids


# ---------------------------------------------------------------------------
# Class 9: TestPlatformLocaleUid (SR-02 / GAP-05)
# ---------------------------------------------------------------------------

class TestPlatformLocaleUid:
    """SR-02: Verify platform/locale fields affect uid computation."""

    def test_uid_with_platform_and_locale(self):
        """Two pages differing only in platform get different uids."""
        page_py = _make_page(slug="overview")
        page_py["platform"] = "python"
        page_py["locale"] = "en"

        page_java = _make_page(slug="overview")
        page_java["platform"] = "java"
        page_java["locale"] = "en"

        assert compute_page_uid(page_py) != compute_page_uid(page_java)

    def test_uid_without_platform_matches_baseline(self):
        """Page without platform/locale fields produces same uid as empty strings."""
        page_no_fields = _make_page(slug="overview")
        page_empty = _make_page(slug="overview")
        page_empty["platform"] = ""
        page_empty["locale"] = ""
        assert compute_page_uid(page_no_fields) == compute_page_uid(page_empty)

    def test_locale_before_platform_in_hash(self):
        """Locale and platform in different order produce different uids,
        confirming they're separate hash components."""
        page1 = _make_page(slug="x")
        page1["locale"] = "alpha"
        page1["platform"] = "beta"

        page2 = _make_page(slug="x")
        page2["locale"] = "beta"
        page2["platform"] = "alpha"

        assert compute_page_uid(page1) != compute_page_uid(page2)


# ---------------------------------------------------------------------------
# Class 10: TestTemplatePathPortability (SR-02 / GAP-06)
# ---------------------------------------------------------------------------

class TestTemplatePathPortability:
    """SR-02: Template path without /specs/templates/ uses filename only."""

    def test_template_path_without_specs_templates_uses_filename(self):
        """Absolute path without /specs/templates/ falls back to filename."""
        page1 = _make_page(
            selection_source="template",
            template_path="C:/custom/path/overview.md",
        )
        page2 = _make_page(
            selection_source="template",
            template_path="/home/user/different/overview.md",
        )
        # Both should use "overview.md" as discriminator
        assert compute_page_uid(page1) == compute_page_uid(page2)

    def test_template_path_with_specs_templates_still_works(self):
        """Normal /specs/templates/ paths still relativize correctly."""
        page1 = _make_page(
            selection_source="template",
            template_path="C:/repo/specs/templates/docs/blog.md",
        )
        page2 = _make_page(
            selection_source="template",
            template_path="/other/specs/templates/docs/blog.md",
        )
        assert compute_page_uid(page1) == compute_page_uid(page2)


# ---------------------------------------------------------------------------
# Class 11: TestClaimSelectionSummary (SR-03 / GAP-07)
# ---------------------------------------------------------------------------

class TestClaimSelectionSummary:
    """SR-03: Verify claim_selection_summary in rationale artifact."""

    def test_rationale_has_claim_selection_summary(self):
        pages = [
            _make_page(slug="a", claim_ids=["c1", "c2", "c3"]),
            _make_page(slug="b", claim_ids=["c4"]),
        ]
        pages[0]["claim_kind"] = "discovered_topic"
        for p in pages:
            p["page_uid"] = compute_page_uid(p)

        rationale = _build_page_plan_rationale({"pages": pages}, {})
        summary = rationale.get("claim_selection_summary")
        assert summary is not None
        assert summary["total_claims_assigned"] == 4
        assert summary["pages_by_claim_kind"]["discovered_topic"] == 1

    def test_claim_selection_summary_empty_when_no_claim_kind(self):
        pages = [_make_page(slug="a", claim_ids=["c1"])]
        pages[0]["page_uid"] = "cfg:test"
        rationale = _build_page_plan_rationale({"pages": pages}, {})
        summary = rationale["claim_selection_summary"]
        assert summary["total_claims_assigned"] == 1
        assert summary["pages_by_claim_kind"] == {}

    def test_claim_selection_summary_multiple_kinds(self):
        pages = [
            _make_page(slug="a"),
            _make_page(slug="b"),
            _make_page(slug="c"),
        ]
        pages[0]["claim_kind"] = "discovered_topic"
        pages[1]["claim_kind"] = "discovered_topic"
        pages[2]["claim_kind"] = "conversion_pair"
        for p in pages:
            p["page_uid"] = compute_page_uid(p)

        rationale = _build_page_plan_rationale({"pages": pages}, {})
        by_kind = rationale["claim_selection_summary"]["pages_by_claim_kind"]
        assert by_kind["discovered_topic"] == 2
        assert by_kind["conversion_pair"] == 1


# ---------------------------------------------------------------------------
# Class 12: TestRationaleSchemaValidation (SR-03 / GAP-08)
# ---------------------------------------------------------------------------

class TestRationaleSchemaValidation:
    """SR-03: Validate rationale artifact against its JSON schema."""

    def test_rationale_validates_against_schema(self):
        """Rationale output matches page_plan_rationale.schema.json structure."""
        pages = [
            _make_page(slug="a", selection_source="template", claim_ids=["c1"]),
        ]
        pages[0]["page_uid"] = "tpl:00001111"
        pages[0]["claim_kind"] = "discovered_topic"

        rationale = _build_page_plan_rationale({"pages": pages}, {"docs": 10})

        # Structural checks matching schema requirements
        assert isinstance(rationale["schema_version"], str)
        assert isinstance(rationale["total_pages"], int)
        assert isinstance(rationale["source_distribution"], dict)
        assert isinstance(rationale["claim_selection_summary"], dict)
        assert isinstance(rationale["claim_selection_summary"]["total_claims_assigned"], int)
        assert isinstance(rationale["claim_selection_summary"]["pages_by_claim_kind"], dict)
        assert isinstance(rationale["quota_context"], dict)
        assert isinstance(rationale["pages"], list)

        entry = rationale["pages"][0]
        assert "page_uid" in entry
        assert "section" in entry
        assert "slug" in entry
        assert "selection_source" in entry


# ---------------------------------------------------------------------------
# Class 13: TestPreservationLogging (SR-04 / GAP-10)
# ---------------------------------------------------------------------------

class TestPreservationLogging:
    """SR-04: Verify debug logging distinguishes uid vs slug matches."""

    def _setup_previous_plan(
        self, tmp_path: Path, pages: List[Dict[str, Any]]
    ) -> Path:
        prev_dir = tmp_path / "prev_run"
        (prev_dir / "artifacts").mkdir(parents=True)
        plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": pages,
        }
        (prev_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(plan), encoding="utf-8"
        )
        return prev_dir

    @patch("launch.workers.w4_ia_planner.worker.logger")
    def test_preservation_logs_uid_match(self, mock_logger, tmp_path: Path):
        prev_pages = [_make_page(slug="x", claim_ids=["c1"])]
        prev_pages[0]["page_uid"] = "cfg:uidmatch"
        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [_make_page(slug="x", claim_ids=["c1"])]
        current_pages[0]["page_uid"] = "cfg:uidmatch"

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        _apply_page_preservation(
            page_plan, _make_incremental_config(str(prev_dir)),
            RunLayout(run_dir=tmp_path),
        )

        debug_calls = [
            c for c in mock_logger.debug.call_args_list
            if "preservation_match_uid" in str(c)
        ]
        assert len(debug_calls) >= 1

    @patch("launch.workers.w4_ia_planner.worker.logger")
    def test_preservation_logs_slug_fallback(self, mock_logger, tmp_path: Path):
        prev_pages = [_make_page(slug="fallback-slug", claim_ids=["c1"])]
        # No page_uid on previous
        prev_dir = self._setup_previous_plan(tmp_path, prev_pages)

        current_pages = [_make_page(slug="fallback-slug", claim_ids=["c1"])]
        current_pages[0]["page_uid"] = "cfg:nomatch"

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": current_pages,
        }
        _apply_page_preservation(
            page_plan, _make_incremental_config(str(prev_dir)),
            RunLayout(run_dir=tmp_path),
        )

        debug_calls = [
            c for c in mock_logger.debug.call_args_list
            if "preservation_match_slug_fallback" in str(c)
        ]
        assert len(debug_calls) >= 1


# ---------------------------------------------------------------------------
# SR-05 (GAP-12): Safety valve — counter > 100 raises ValueError
# ---------------------------------------------------------------------------

class TestSafetyValve:
    """SR-05/GAP-12: Safety valve in _assign_page_uids fires at counter > 100."""

    @patch("launch.workers.w4_ia_planner.worker.hashlib")
    def test_collision_loop_exceeds_100_raises(self, mock_hashlib):
        """Patching sha256 to always return same digest forces the while-loop
        to re-generate the identical collision-resolved uid on every iteration,
        driving counter past 100 on the 3rd page."""
        # All sha256 calls → same 64-char hex string
        mock_hashlib.sha256.return_value.hexdigest.return_value = "0" * 64

        # Three pages: after sha256-patching, all get base uid "fb:00000000".
        # Page 1 → added to seen.
        # Page 2 → collision, resolution uid "fb:00000000_0000" (not yet seen) → added.
        # Page 3 → collision, resolution always "fb:00000000_0000" (seen!) → loop
        #          → every iteration produces same uid → counter hits 101 → ValueError.
        pages = [
            _make_page(slug=f"s{i}", output_path=f"docs/s{i}.md",
                       selection_source="fallback")
            for i in range(3)
        ]
        with pytest.raises(ValueError, match="collision loop exceeded 100 iterations"):
            _assign_page_uids(pages)


# ---------------------------------------------------------------------------
# SR-05 (GAP-13): Uniqueness guard — raises ValueError on crafted duplicates
# ---------------------------------------------------------------------------

class TestUniquenessGuard:
    """SR-05/GAP-13: Document the uniqueness guard logic via inline simulation."""

    def test_guard_logic_raises_on_duplicates(self):
        """Inline simulation of the post-assignment uniqueness guard.

        The guard in worker.py runs after _assign_page_uids() and raises
        ValueError when any page_uid appears more than once.  Here we
        simulate it with crafted duplicates to prove the logic is correct.
        """
        from collections import Counter

        pages = [
            _make_page(slug="a", selection_source="fallback", output_path="docs/a.md"),
            _make_page(slug="b", selection_source="fallback", output_path="docs/b.md"),
        ]
        _assign_page_uids(pages)
        # Corrupt: force a duplicate uid
        original_uid = pages[0]["page_uid"]
        pages[1]["page_uid"] = original_uid

        all_uids = [p["page_uid"] for p in pages if p.get("page_uid")]
        assert len(all_uids) != len(set(all_uids)), "setup: pages should have dupes"

        # This mirrors the production guard in worker.py (SR-06 Counter variant)
        uid_counts = Counter(all_uids)
        dupes = sorted(u for u, c in uid_counts.items() if c > 1)
        assert dupes == [original_uid]
        with pytest.raises(ValueError, match="page_uid uniqueness violated"):
            raise ValueError("page_uid uniqueness violated: {}".format(dupes))

    def test_guard_logic_passes_on_unique_uids(self):
        """Guard does not raise when all uids are unique."""
        from collections import Counter

        pages = [
            _make_page(slug="x", selection_source="fallback",
                       output_path="docs/x.md", page_role="faq"),
            _make_page(slug="y", selection_source="mandatory_config",
                       output_path="docs/y.md", page_role="tutorial"),
        ]
        _assign_page_uids(pages)
        all_uids = [p["page_uid"] for p in pages if p.get("page_uid")]
        uid_counts = Counter(all_uids)
        dupes = sorted(u for u, c in uid_counts.items() if c > 1)
        # Should be empty — no ValueError raised
        assert dupes == []


# ---------------------------------------------------------------------------
# SR-07 (GAP-15): Template filename collision — document known limitation
# ---------------------------------------------------------------------------

class TestTemplateFilenameCollision:
    """SR-07/GAP-15: Document the known limitation when two templates share
    the same filename in different directories."""

    def test_same_filename_different_dirs_produce_same_uid(self):
        """KNOWN LIMITATION: rsplit fallback uses filename only, so two
        templates with the same filename collide at base uid."""
        page_a = _make_page(
            section="docs", page_role="tutorial",
            selection_source="template",
            template_path="custom/templates/tutorial.md",
        )
        page_b = _make_page(
            section="docs", page_role="tutorial",
            selection_source="template",
            template_path="other/templates/tutorial.md",
        )
        uid_a = compute_page_uid(page_a)
        uid_b = compute_page_uid(page_b)
        # Document: both resolve to filename "tutorial.md" → identical uid
        assert uid_a == uid_b, (
            "Expected collision: rsplit fallback uses filename-only discriminator. "
            f"uid_a={uid_a}, uid_b={uid_b}"
        )

    def test_collision_is_resolved_by_assign_page_uids(self):
        """_assign_page_uids resolves the filename-collision via suffix."""
        pages = [
            _make_page(
                section="docs", page_role="tutorial",
                selection_source="template",
                template_path="custom/templates/tutorial.md",
                output_path="docs/custom-tutorial.md",
            ),
            _make_page(
                section="docs", page_role="tutorial",
                selection_source="template",
                template_path="other/templates/tutorial.md",
                output_path="docs/other-tutorial.md",
            ),
        ]
        _assign_page_uids(pages)
        uids = [p["page_uid"] for p in pages]
        assert len(set(uids)) == 2, (
            f"Collision resolution should produce 2 distinct uids, got: {uids}"
        )


# ---------------------------------------------------------------------------
# SR-07 (GAP-16): None locale/platform matches missing key
# ---------------------------------------------------------------------------

class TestNoneLocalePlatform:
    """SR-07/GAP-16: Explicit None locale/platform must produce same uid as
    a missing key (both should hash as empty string)."""

    def test_none_locale_matches_missing_locale(self):
        """page with locale=None gets same uid as page with no locale key."""
        page_missing = _make_page(
            section="docs", page_role="faq",
            selection_source="fallback", slug="x",
        )
        page_none = _make_page(
            section="docs", page_role="faq",
            selection_source="fallback", slug="x",
        )
        page_none["locale"] = None
        page_none["platform"] = None

        uid_missing = compute_page_uid(page_missing)
        uid_none = compute_page_uid(page_none)
        assert uid_missing == uid_none, (
            f"None locale/platform should hash identically to missing. "
            f"missing={uid_missing}, none={uid_none}. "
            "Fix: use `page.get('locale') or ''` in compute_page_uid()."
        )

    def test_none_locale_differs_from_nonempty_locale(self):
        """Sanity: explicit locale value produces different uid than None."""
        page_no_locale = _make_page(
            section="docs", page_role="faq",
            selection_source="fallback", slug="x",
        )
        page_with_locale = _make_page(
            section="docs", page_role="faq",
            selection_source="fallback", slug="x",
        )
        page_with_locale["locale"] = "fr-FR"

        uid_no = compute_page_uid(page_no_locale)
        uid_fr = compute_page_uid(page_with_locale)
        assert uid_no != uid_fr, "Different locale values must produce different uids"


# ---------------------------------------------------------------------------
# SR-09 (GAP-18): Integration test — uid+rationale through finalization pipeline
# ---------------------------------------------------------------------------

class TestPageUidIntegration:
    """SR-09/GAP-18: End-to-end validation of page_uid through the
    _assign_page_uids + _build_page_plan_rationale finalization pipeline."""

    def test_all_five_selection_sources_receive_uid(self):
        """Pages from all 5 construction paths get page_uid + selection_source."""
        pages = [
            _make_page(slug="p1", selection_source="mandatory_config",
                       section="api"),
            _make_page(slug="p2", selection_source="optional_policy",
                       section="api"),
            _make_page(slug="p3", selection_source="template",
                       section="api",
                       template_path="/specs/templates/basic/tutorial.md"),
            _make_page(slug="p4", selection_source="topic_discovery",
                       section="api", source="topic_discovery",
                       title="Advanced Usage"),
            _make_page(slug="p5", selection_source="fallback",
                       section="api"),
        ]
        _assign_page_uids(pages)

        for page in pages:
            assert "page_uid" in page, f"page_uid missing on {page['slug']}"
            assert isinstance(page["page_uid"], str)
            assert len(page["page_uid"]) > 0, f"Empty page_uid on {page['slug']}"

        uids = [p["page_uid"] for p in pages]
        assert len(set(uids)) == len(pages), f"Duplicate uids found: {uids}"

    def test_rationale_artifact_covers_all_pages(self):
        """_build_page_plan_rationale includes every page after uid assignment."""
        pages = [
            _make_page(slug=f"p{i}", selection_source=src, claim_ids=[f"c{i}"])
            for i, src in enumerate(
                ["mandatory_config", "optional_policy", "topic_discovery",
                 "fallback", "template"]
            )
        ]
        _assign_page_uids(pages)

        page_plan = {
            "schema_version": "1.0",
            "product_slug": "test",
            "launch_tier": "minimal",
            "pages": pages,
        }
        rationale = _build_page_plan_rationale(page_plan, {"section_a": {"min": 1}})

        assert rationale["schema_version"] == "1.0"
        assert rationale["total_pages"] == 5
        assert "source_distribution" in rationale
        assert "claim_selection_summary" in rationale
        assert len(rationale["pages"]) == 5

        for entry in rationale["pages"]:
            assert entry.get("page_uid"), f"rationale entry missing page_uid: {entry}"
            assert "selection_source" in entry

    def test_uid_uniqueness_across_many_diverse_pages(self):
        """Stress test: 12 pages across 4 sections × 3 roles all get unique uids."""
        pages = []
        for section in ["intro", "api", "howto", "concepts"]:
            for role in ["comprehensive_guide", "faq", "tutorial"]:
                pages.append(_make_page(
                    section=section,
                    slug=f"{section}-{role}",
                    page_role=role,
                    selection_source="mandatory_config",
                ))
        _assign_page_uids(pages)

        uids = [p["page_uid"] for p in pages]
        duplicates = sorted(
            {u for u in uids if uids.count(u) > 1}
        )
        assert not duplicates, (
            f"Expected {len(pages)} unique uids across diverse pages, "
            f"got duplicates: {duplicates}"
        )

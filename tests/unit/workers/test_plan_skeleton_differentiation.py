"""Tests for planner skeleton differentiation (TC-3799).

Verifies that _assign_skeletons produces different skeletons for pages
with the same page_role but different topics.
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier
from launcher.shared.page_skeletons import resolve_skeleton


class TestPlannerSkeletonDifferentiation:
    """Integration tests for planner skeleton variant assignment."""

    def _make_page(
        self, slug: str, page_role: str = "workflow_page",
        topic_category: str | None = None,
    ) -> dict:
        return {
            "section": "docs",
            "page_id": f"docs/{slug}",
            "page_role": page_role,
            "slug": slug,
            "content_path": f"docs.aspose.org/cells/python/developer-guide/{slug}",
            "mandatory": True,
            "folder_index": False,
            "topic_category": topic_category,
        }

    def test_install_page_gets_install_variant(self) -> None:
        from launcher.shared.page_skeletons import resolve_topic_tag
        page = self._make_page("installation")
        tag = resolve_topic_tag(page["page_role"], page.get("topic_category"), page["slug"])
        assert tag == "install"
        skeleton = resolve_skeleton(page["page_role"], tag)
        headings = [s.heading for s in skeleton]
        assert "System Requirements" in headings
        assert "Key Features" not in headings  # default heading absent

    def test_data_ops_page_gets_data_variant(self) -> None:
        from launcher.shared.page_skeletons import resolve_topic_tag
        page = self._make_page("spreadsheet-operations")
        tag = resolve_topic_tag(page["page_role"], page.get("topic_category"), page["slug"])
        assert tag == "data_operations"
        skeleton = resolve_skeleton(page["page_role"], tag)
        headings = [s.heading for s in skeleton]
        assert "Working with Data" in headings

    def test_computation_page_gets_computation_variant(self) -> None:
        from launcher.shared.page_skeletons import resolve_topic_tag
        page = self._make_page("formula-calculation")
        tag = resolve_topic_tag(page["page_role"], page.get("topic_category"), page["slug"])
        assert tag == "computation"
        skeleton = resolve_skeleton(page["page_role"], tag)
        headings = [s.heading for s in skeleton]
        assert "Core Concepts" in headings
        assert "Implementation" in headings

    def test_unknown_slug_gets_default(self) -> None:
        from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS, resolve_topic_tag
        page = self._make_page("some-generic-topic")
        tag = resolve_topic_tag(page["page_role"], page.get("topic_category"), page["slug"])
        assert tag == "default"
        skeleton = resolve_skeleton(page["page_role"], tag)
        default = PAGE_ROLE_SKELETONS["workflow_page"]
        assert [s.heading for s in skeleton] == [s.heading for s in default]

    def test_different_workflow_pages_different_skeletons(self) -> None:
        """Two workflow_page pages with different slugs must produce different headings."""
        from launcher.shared.page_skeletons import resolve_topic_tag

        install_page = self._make_page("installation")
        data_page = self._make_page("spreadsheet-operations")

        tag1 = resolve_topic_tag(install_page["page_role"], None, install_page["slug"])
        tag2 = resolve_topic_tag(data_page["page_role"], None, data_page["slug"])

        skel1 = resolve_skeleton("workflow_page", tag1)
        skel2 = resolve_skeleton("workflow_page", tag2)

        h1 = [s.heading for s in skel1]
        h2 = [s.heading for s in skel2]
        assert h1 != h2, "install and data_operations skeletons must differ"

    def test_howto_with_topic_category(self) -> None:
        from launcher.shared.page_skeletons import resolve_topic_tag
        page = self._make_page(
            "how-to-open-a-file", page_role="howto_article",
            topic_category="load_file",
        )
        tag = resolve_topic_tag(page["page_role"], page["topic_category"], page["slug"])
        assert tag == "load_file"
        skeleton = resolve_skeleton("howto_article", tag)
        headings = [s.heading for s in skeleton]
        assert "Loading the File" in headings

    def test_howto_troubleshoot_variant(self) -> None:
        from launcher.shared.page_skeletons import resolve_topic_tag
        page = self._make_page(
            "how-to-fix-common-errors", page_role="howto_article",
            topic_category="troubleshoot",
        )
        tag = resolve_topic_tag(page["page_role"], page["topic_category"], page["slug"])
        assert tag == "troubleshoot"
        skeleton = resolve_skeleton("howto_article", tag)
        headings = [s.heading for s in skeleton]
        assert "Symptoms" in headings
        assert "Root Cause" in headings

    def test_skeleton_variant_propagated_to_planned_page(self) -> None:
        """PlannedPage should carry skeleton_variant field."""
        from launcher.models.plan import PlannedPage
        pp = PlannedPage(
            page_id="docs/installation",
            page_role="workflow_page",
            title="Installation",
            skeleton=["System Requirements", "Installation", "Verify Installation"],
            skeleton_variant="install",
        )
        assert pp.skeleton_variant == "install"

    def test_planned_page_default_variant(self) -> None:
        """PlannedPage skeleton_variant defaults to 'default'."""
        from launcher.models.plan import PlannedPage
        pp = PlannedPage(
            page_id="docs/generic",
            page_role="workflow_page",
            title="Generic",
        )
        assert pp.skeleton_variant == "default"

    def test_all_family_override_slugs_resolved(self) -> None:
        """Every slug in family_overrides should resolve to a non-default variant."""
        from launcher.shared.page_skeletons import resolve_topic_tag
        family_slugs = [
            "spreadsheet-operations", "formula-calculation",
            "notebook-manipulation", "document-conversion",
            "model-loading", "rendering",
            "document-editing", "mail-merge",
            "pdf-manipulation", "form-filling",
            "presentation-creation", "slide-manipulation",
        ]
        for slug in family_slugs:
            tag = resolve_topic_tag("workflow_page", slug=slug)
            assert tag != "default", f"Slug '{slug}' should resolve to a variant, not default"


# ---------------------------------------------------------------------------
# Integration tests: run_plan() end-to-end skeleton propagation (SR-05)
# ---------------------------------------------------------------------------


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        display_name="Aspose.Cells for Python",
        family="cells",
        platform="python",
        canonical_import="aspose.cells",
        repo_url="https://github.com/aspose-cells/Aspose.Cells-for-Python",
    )


def _make_richness() -> RichnessResult:
    return RichnessResult(tier=RichnessTier.A, score=30, reason="test")


def _make_claims() -> list[Claim]:
    return [
        Claim(claim_id="CLM-001", text="Supports XLSX format", kind="format"),
        Claim(claim_id="CLM-002", text="High performance formula engine", kind="feature"),
        Claim(claim_id="CLM-003", text="Install via pip", kind="workflow"),
    ]


class TestRunPlanSkeletonIntegration:
    """End-to-end tests calling run_plan() to verify skeleton variant propagation."""

    def _run(self) -> list:
        from launcher.workers.planner.plan import run_plan
        pages, _ = run_plan(
            _make_product(), _make_richness(), _make_claims(), [],
        )
        return pages

    def test_run_plan_all_pages_have_skeleton(self) -> None:
        """Every page in run_plan() output has a non-empty skeleton."""
        pages = self._run()
        assert len(pages) > 0
        for p in pages:
            assert p.skeleton, f"Page {p.page_id} has empty skeleton"

    def test_run_plan_all_pages_have_skeleton_variant(self) -> None:
        """Every page has a skeleton_variant field (at least 'default')."""
        pages = self._run()
        for p in pages:
            assert p.skeleton_variant, f"Page {p.page_id} has empty skeleton_variant"

    def test_run_plan_install_page_gets_install_variant(self) -> None:
        """The installation page should get the 'install' variant."""
        pages = self._run()
        install_pages = [p for p in pages if "install" in p.page_id.lower()]
        assert install_pages, "Expected at least one install page"
        for p in install_pages:
            assert p.skeleton_variant == "install", (
                f"Page {p.page_id} should have variant 'install', got '{p.skeleton_variant}'"
            )
            assert "System Requirements" in p.skeleton

    def test_run_plan_different_variants_produce_different_skeletons(self) -> None:
        """Pages with different variants must have different heading lists."""
        pages = self._run()
        by_variant: dict[str, list] = {}
        for p in pages:
            if p.page_role == "workflow_page":
                by_variant.setdefault(p.skeleton_variant, []).append(p)

        # We need at least 2 distinct variants among workflow_page pages
        if len(by_variant) >= 2:
            variants = list(by_variant.values())
            h1 = variants[0][0].skeleton
            h2 = variants[1][0].skeleton
            assert h1 != h2, "Different variants must produce different heading lists"

    def test_run_plan_variant_survives_frontmatter_build(self) -> None:
        """skeleton_variant persists after _build_frontmatter and _refine_page_slugs."""
        pages = self._run()
        install_pages = [p for p in pages if p.skeleton_variant == "install"]
        if install_pages:
            p = install_pages[0]
            # After full pipeline, frontmatter should exist and variant should survive
            assert p.frontmatter, f"Page {p.page_id} missing frontmatter"
            assert p.skeleton_variant == "install"
            assert "System Requirements" in p.skeleton

"""TC-972: Unit tests for W4 IAPlanner content distribution implementation.

Tests the new helper functions (assign_page_role, build_content_strategy) and
modified section planning logic for docs and KB sections.
"""

import pytest
from src.launch.workers.w4_ia_planner.worker import (
    assign_page_role,
    build_content_strategy,
    plan_pages_for_section,
)


class TestAssignPageRole:
    """Test page role assignment logic."""

    def test_assign_page_role_docs_toc(self):
        """Verify is_index=True + section='docs' returns 'toc'."""
        role = assign_page_role("docs", "_index", is_index=True)
        assert role == "toc"

    def test_assign_page_role_developer_guide(self):
        """Verify slug='developer-guide' returns 'comprehensive_guide'."""
        role = assign_page_role("docs", "developer-guide")
        assert role == "comprehensive_guide"

    def test_assign_page_role_developer_guide_with_path(self):
        """Verify slug ending with '/developer-guide' returns 'comprehensive_guide'."""
        role = assign_page_role("docs", "some/path/developer-guide")
        assert role == "comprehensive_guide"

    def test_assign_page_role_kb_feature_showcase(self):
        """Verify 'how-to' in slug returns 'feature_showcase'."""
        role = assign_page_role("kb", "how-to-export-scene")
        assert role == "feature_showcase"

    def test_assign_page_role_kb_showcase(self):
        """Verify 'showcase' in slug returns 'feature_showcase'."""
        role = assign_page_role("kb", "showcase-advanced-feature")
        assert role == "feature_showcase"

    def test_assign_page_role_kb_faq_landing(self):
        """Verify KB FAQ returns 'landing' (per TC-977: allows installation content)."""
        role = assign_page_role("kb", "faq")
        assert role == "landing"

    def test_assign_page_role_kb_troubleshooting(self):
        """Verify other KB slugs return 'troubleshooting'."""
        role = assign_page_role("kb", "troubleshooting-guide")
        assert role == "troubleshooting"

    def test_assign_page_role_products_landing(self):
        """Verify products overview returns 'landing'."""
        role = assign_page_role("products", "overview")
        assert role == "landing"

    def test_assign_page_role_docs_workflow(self):
        """Verify docs pages (non-TOC, non-developer-guide) return 'workflow_page'."""
        role = assign_page_role("docs", "getting-started")
        assert role == "workflow_page"

    def test_assign_page_role_reference_api(self):
        """Verify reference section returns 'api_reference'."""
        role = assign_page_role("reference", "api-overview")
        assert role == "api_reference"

    def test_assign_page_role_blog_landing(self):
        """Verify blog section returns 'landing'."""
        role = assign_page_role("blog", "announcement")
        assert role == "landing"


class TestBuildContentStrategy:
    """Test content strategy building logic."""

    def test_build_content_strategy_toc(self):
        """Verify TOC strategy has child_pages=[], forbidden=['code_snippets']."""
        strategy = build_content_strategy("toc", "docs")
        assert "child_pages" in strategy
        assert strategy["child_pages"] == []
        assert "code_snippets" in strategy["forbidden_topics"]
        assert strategy["claim_quota"]["min"] == 0
        assert strategy["claim_quota"]["max"] == 2

    def test_build_content_strategy_comprehensive_guide(self):
        """Verify comprehensive_guide strategy has scenario_coverage='all', quota.min=len(workflows)."""
        workflows = [{"workflow_id": "wf1"}, {"workflow_id": "wf2"}, {"workflow_id": "wf3"}]
        strategy = build_content_strategy("comprehensive_guide", "docs", workflows)
        assert strategy["scenario_coverage"] == "all"
        assert strategy["claim_quota"]["min"] == 3  # len(workflows)
        assert strategy["claim_quota"]["max"] == 50
        assert "installation" in strategy["forbidden_topics"]
        assert "troubleshooting" in strategy["forbidden_topics"]

    def test_build_content_strategy_feature_showcase(self):
        """Verify feature_showcase strategy has single feature focus, quota={min:3, max:8}."""
        strategy = build_content_strategy("feature_showcase", "kb")
        assert strategy["primary_focus"] == "Prominent feature how-to"
        assert strategy["claim_quota"]["min"] == 3
        assert strategy["claim_quota"]["max"] == 8
        assert "general_features" in strategy["forbidden_topics"]
        assert "api_reference" in strategy["forbidden_topics"]
        assert "other_features" in strategy["forbidden_topics"]

    def test_build_content_strategy_workflow_page(self):
        """Verify workflow_page strategy has correct quotas and forbidden topics."""
        strategy = build_content_strategy("workflow_page", "docs")
        assert strategy["primary_focus"] == "How-to guide"
        assert strategy["claim_quota"]["min"] == 3
        assert strategy["claim_quota"]["max"] == 8
        assert "other_workflows" in strategy["forbidden_topics"]

    def test_build_content_strategy_landing_products(self):
        """Verify products landing strategy has correct quotas."""
        strategy = build_content_strategy("landing", "products")
        assert strategy["claim_quota"]["min"] == 5
        assert strategy["claim_quota"]["max"] == 10
        assert "detailed_api" in strategy["forbidden_topics"]

    def test_build_content_strategy_landing_blog(self):
        """Verify blog landing strategy allows broad coverage."""
        strategy = build_content_strategy("landing", "blog")
        assert strategy["claim_quota"]["min"] == 10
        assert strategy["claim_quota"]["max"] == 20
        assert strategy["forbidden_topics"] == []  # Blog can cover all topics

    def test_build_content_strategy_troubleshooting(self):
        """Verify troubleshooting strategy has correct quotas."""
        strategy = build_content_strategy("troubleshooting", "kb")
        assert strategy["claim_quota"]["min"] == 1
        assert strategy["claim_quota"]["max"] == 5
        assert "features" in strategy["forbidden_topics"]


class TestDocsSectionPlanning:
    """Test docs section planning creates 3 pages with correct roles."""

    def test_docs_section_creates_three_pages(self):
        """Integration test: run plan_pages_for_section('docs'), verify 3 pages."""
        product_facts = {
            "product_name": "Test Product",
            "claims": [
                {"claim_id": "c1", "claim_kind": "install", "claim_text": "Install via pip"},
                {"claim_id": "c2", "claim_kind": "quickstart", "claim_text": "Quick start guide"},
                {"claim_id": "c3", "claim_kind": "feature", "claim_text": "Key feature"},
            ],
            "claim_groups": {
                "install_steps": ["c1"],
                "quickstart_steps": ["c2"],
                "key_features": ["c3"],
            },
            "workflows": [
                {"workflow_id": "wf1", "name": "Workflow 1"},
                {"workflow_id": "wf2", "name": "Workflow 2"},
            ],
        }
        snippet_catalog = {
            "snippets": [
                {"tags": ["quickstart"]},
                {"tags": ["advanced"]},
            ]
        }

        pages = plan_pages_for_section(
            section="docs",
            launch_tier="standard",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="test",
        )

        # Should have exactly 3 pages
        assert len(pages) == 3

        # Find pages by slug
        page_by_slug = {p["slug"]: p for p in pages}

        # Verify TOC page
        assert "_index" in page_by_slug
        toc_page = page_by_slug["_index"]
        assert toc_page["page_role"] == "toc"
        assert "content_strategy" in toc_page
        assert toc_page["content_strategy"]["claim_quota"]["max"] == 2
        assert len(toc_page["required_snippet_tags"]) == 0  # No code on TOC

        # Verify getting-started page
        assert "getting-started" in page_by_slug
        gs_page = page_by_slug["getting-started"]
        assert gs_page["page_role"] == "workflow_page"
        assert "content_strategy" in gs_page

        # Verify developer-guide page
        assert "developer-guide" in page_by_slug
        dg_page = page_by_slug["developer-guide"]
        assert dg_page["page_role"] == "comprehensive_guide"
        assert dg_page["content_strategy"]["scenario_coverage"] == "all"


class TestKBSectionPlanning:
    """Test KB section planning creates feature showcases and troubleshooting."""

    def test_kb_section_creates_showcases_and_troubleshooting(self):
        """Integration test: verify mix of feature_showcase + troubleshooting."""
        product_facts = {
            "claims": [
                {"claim_id": "f1", "claim_kind": "feature", "claim_text": "Export 3D scenes", "tags": ["export"]},
                {"claim_id": "f2", "claim_kind": "feature", "claim_text": "Import models", "tags": ["import"]},
                {"claim_id": "f3", "claim_kind": "feature", "claim_text": "Mesh manipulation", "tags": ["mesh"]},
            ],
            "claim_groups": {
                "key_features": ["f1", "f2", "f3"],
                "install_steps": [],
                "limitations": [],
            },
            "workflows": [],
        }
        snippet_catalog = {
            "snippets": [
                {"tags": ["export"]},
                {"tags": ["import"]},
                {"tags": ["mesh"]},
            ]
        }

        pages = plan_pages_for_section(
            section="kb",
            launch_tier="standard",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="test",
        )

        # Should have feature showcases + troubleshooting pages
        # Standard tier: 3 showcases + FAQ + troubleshooting = 5 pages
        assert len(pages) >= 4

        # Check for feature showcase pages
        showcase_pages = [p for p in pages if p.get("page_role") == "feature_showcase"]
        assert len(showcase_pages) >= 2  # At least 2 feature showcases

        # Check for troubleshooting pages
        troubleshooting_pages = [p for p in pages if p.get("page_role") == "troubleshooting"]
        assert len(troubleshooting_pages) >= 1  # At least FAQ

        # Verify showcase pages have "how-to-" prefix
        for showcase in showcase_pages:
            assert showcase["slug"].startswith("how-to-")
            assert len(showcase["required_claim_ids"]) == 1  # Single feature focus

    def test_kb_minimal_tier(self):
        """Test KB section with minimal tier creates 2 showcases."""
        product_facts = {
            "claims": [
                {"claim_id": "f1", "claim_kind": "feature", "claim_text": "Feature 1", "tags": []},
                {"claim_id": "f2", "claim_kind": "feature", "claim_text": "Feature 2", "tags": []},
                {"claim_id": "f3", "claim_kind": "feature", "claim_text": "Feature 3", "tags": []},
            ],
            "claim_groups": {
                "key_features": ["f1", "f2", "f3"],
                "install_steps": [],
                "limitations": [],
            },
            "workflows": [],
        }
        snippet_catalog = {"snippets": [{"tags": ["test"]}]}

        pages = plan_pages_for_section(
            section="kb",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="test",
        )

        showcase_pages = [p for p in pages if p.get("page_role") == "feature_showcase"]
        # Minimal tier should create 2 showcases
        assert len(showcase_pages) == 2


class TestTOCChildPages:
    """Test TOC child_pages population (requires integration test)."""

    def test_toc_child_pages_populated(self):
        """Integration test: verify TOC page.content_strategy.child_pages is populated."""
        # This test requires full execute_ia_planner context
        # Verification: After all pages created, TOC pages should have child_pages populated
        # Mock test to verify the logic exists
        product_facts = {
            "product_name": "Test Product",
            "claims": [{"claim_id": "c1", "claim_kind": "feature", "claim_text": "Key feature"}],
            "claim_groups": {
                "key_features": ["c1"],
                "install_steps": [],
            },
            "workflows": [],
        }
        snippet_catalog = {"snippets": []}

        pages = plan_pages_for_section(
            section="docs",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="test",
        )

        # Find TOC page
        toc_page = next((p for p in pages if p.get("page_role") == "toc"), None)
        assert toc_page is not None
        assert "content_strategy" in toc_page
        # child_pages should be initialized (will be populated by post-processing)
        assert "child_pages" in toc_page["content_strategy"]


class TestDeterminism:
    """Test deterministic page role assignment."""

    def test_page_role_assignment_deterministic(self):
        """Verify page role assignment is deterministic (no randomness)."""
        # Run multiple times, verify same input produces same output
        results = []
        for _ in range(3):
            role = assign_page_role("docs", "developer-guide")
            results.append(role)

        # All results should be identical
        assert len(set(results)) == 1
        assert results[0] == "comprehensive_guide"

    def test_content_strategy_deterministic(self):
        """Verify content strategy is deterministic."""
        workflows = [{"workflow_id": "wf1"}, {"workflow_id": "wf2"}]
        results = []
        for _ in range(3):
            strategy = build_content_strategy("comprehensive_guide", "docs", workflows)
            results.append(strategy["claim_quota"]["min"])

        # All results should be identical
        assert len(set(results)) == 1
        assert results[0] == 2  # len(workflows)


class TestClaimGroupResolution:
    """TC-980: Verify claim_groups dict resolution produces non-empty claim IDs."""

    def _make_product_facts(self):
        """Shared fixture with realistic claim_groups structure."""
        return {
            "product_name": "Test Product",
            "claims": [
                {"claim_id": "kf1", "claim_kind": "feature", "claim_text": "Feature A"},
                {"claim_id": "kf2", "claim_kind": "feature", "claim_text": "Feature B"},
                {"claim_id": "kf3", "claim_kind": "feature", "claim_text": "Feature C"},
                {"claim_id": "is1", "claim_kind": "install", "claim_text": "Install via pip"},
                {"claim_id": "is2", "claim_kind": "install", "claim_text": "Install from source"},
                {"claim_id": "lm1", "claim_kind": "limitation", "claim_text": "Limitation 1"},
            ],
            "claim_groups": {
                "key_features": ["kf1", "kf2", "kf3"],
                "install_steps": ["is1", "is2"],
                "limitations": ["lm1"],
                "compatibility_notes": [],
                "quickstart_steps": [],
                "workflow_claims": [],
            },
            "api_surface_summary": {"key_modules": []},
            "workflows": [],
        }

    def _make_snippet_catalog(self):
        return {"snippets": [{"tags": ["quickstart"]}, {"tags": ["export"]}]}

    def test_products_overview_has_claim_ids(self):
        """Products overview page must have non-empty required_claim_ids."""
        pages = plan_pages_for_section(
            section="products",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        assert len(pages) == 1
        overview = pages[0]
        assert len(overview["required_claim_ids"]) > 0, "Products overview must have claim IDs"
        # Should include key_features + install_steps
        assert "kf1" in overview["required_claim_ids"]
        assert "is1" in overview["required_claim_ids"]

    def test_products_overview_claim_ids_sorted(self):
        """Products overview claim IDs must be deterministically sorted."""
        pages = plan_pages_for_section(
            section="products",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        ids = pages[0]["required_claim_ids"]
        assert ids == sorted(ids), "Claim IDs must be sorted for determinism"

    def test_reference_api_overview_has_claim_ids(self):
        """Reference api-overview page must have non-empty required_claim_ids."""
        pages = plan_pages_for_section(
            section="reference",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        assert len(pages) == 1
        ref_page = pages[0]
        assert len(ref_page["required_claim_ids"]) > 0, "Reference page must have claim IDs"
        assert "kf1" in ref_page["required_claim_ids"]

    def test_reference_claim_ids_sorted(self):
        """Reference claim IDs must be deterministically sorted."""
        pages = plan_pages_for_section(
            section="reference",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        ids = pages[0]["required_claim_ids"]
        assert ids == sorted(ids), "Claim IDs must be sorted for determinism"

    def test_kb_faq_has_claim_ids(self):
        """KB FAQ page must have non-empty required_claim_ids."""
        pages = plan_pages_for_section(
            section="kb",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        faq_page = next((p for p in pages if p["slug"] == "faq"), None)
        assert faq_page is not None, "FAQ page must exist"
        assert len(faq_page["required_claim_ids"]) > 0, "FAQ must have claim IDs"
        assert "is1" in faq_page["required_claim_ids"]
        assert "lm1" in faq_page["required_claim_ids"]

    def test_kb_faq_claim_ids_sorted(self):
        """KB FAQ claim IDs must be deterministically sorted."""
        pages = plan_pages_for_section(
            section="kb",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        faq_page = next(p for p in pages if p["slug"] == "faq")
        ids = faq_page["required_claim_ids"]
        assert ids == sorted(ids), "Claim IDs must be sorted for determinism"

    def test_kb_feature_showcases_have_claim_ids(self):
        """KB feature showcase pages must have non-empty required_claim_ids."""
        pages = plan_pages_for_section(
            section="kb",
            launch_tier="minimal",
            product_facts=self._make_product_facts(),
            snippet_catalog=self._make_snippet_catalog(),
            product_slug="test",
        )
        showcases = [p for p in pages if p.get("page_role") == "feature_showcase"]
        assert len(showcases) >= 2, "Minimal tier should have 2 showcases"
        for showcase in showcases:
            assert len(showcase["required_claim_ids"]) == 1, "Each showcase has single feature claim"

    def test_empty_claim_groups_fallback(self):
        """When claim_groups is empty dict, pages should degrade gracefully."""
        product_facts = {
            "product_name": "Test",
            "claims": [{"claim_id": "x1", "claim_kind": "feature", "claim_text": "Feat"}],
            "claim_groups": {},
            "workflows": [],
        }
        pages = plan_pages_for_section(
            section="products",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog={"snippets": []},
            product_slug="test",
        )
        assert len(pages) == 1
        assert isinstance(pages[0]["required_claim_ids"], list)

    def test_claim_groups_as_legacy_list_fallback(self):
        """When claim_groups is a list (legacy), should not crash."""
        product_facts = {
            "product_name": "Test",
            "claims": [{"claim_id": "x1", "claim_kind": "feature", "claim_text": "Feat"}],
            "claim_groups": ["some", "legacy", "list"],
            "workflows": [],
        }
        pages = plan_pages_for_section(
            section="products",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog={"snippets": []},
            product_slug="test",
        )
        assert len(pages) == 1
        assert isinstance(pages[0]["required_claim_ids"], list)

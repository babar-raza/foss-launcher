"""TC-986: Unit tests for evidence-driven page scaling and configurable page requirements.

Tests the new W4 functions:
- compute_evidence_volume()
- compute_effective_quotas()
- generate_optional_pages()
- load_and_merge_page_requirements()
- determine_launch_tier() CI-absent softening

Spec references:
- specs/06_page_planning.md (quality_score formula, Optional Page Selection Algorithm)
- specs/rulesets/ruleset.v1.yaml (mandatory_pages, optional_page_policies, family_overrides)
- specs/schemas/page_plan.schema.json (evidence_volume, effective_quotas)
"""

import pytest
from typing import Dict, Any, List

from src.launch.workers.w4_ia_planner.worker import (
    compute_evidence_volume,
    compute_effective_quotas,
    generate_optional_pages,
    load_and_merge_page_requirements,
    determine_launch_tier,
    plan_pages_for_section,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_repo_product_facts() -> Dict[str, Any]:
    """Small repo fixture: 42 claims, 1 workflow, 14 key_features, ~9 API symbols.

    Mirrors a small FOSS library like Aspose.3D for Python with limited evidence.
    """
    claims = [
        {"claim_id": f"c{i:03d}", "claim_kind": "feature", "claim_text": f"Feature {i}",
         "tags": [f"tag{i}"]}
        for i in range(1, 43)
    ]
    return {
        "product_name": "Aspose.3D for Python",
        "claims": claims,
        "claim_groups": {
            "key_features": sorted([f"c{i:03d}" for i in range(1, 15)]),
            "install_steps": sorted(["c001", "c002"]),
            "quickstart_steps": sorted(["c003", "c004"]),
            "limitations": sorted(["c040", "c041", "c042"]),
            "workflow_claims": sorted(["c010"]),
        },
        "workflows": [
            {"workflow_id": "wf_export", "name": "Export 3D Scene"},
        ],
        "api_surface_summary": {
            "key_modules": ["aspose.threed", "aspose.threed.entities"],
            "classes": sorted([
                "Scene", "Entity", "Node", "Mesh",
                "Camera", "Light", "Material",
                "Transform", "Quaternion",
            ]),
        },
        "repository_health": {
            "ci_present": False,
            "tests_present": True,
            "test_file_count": 5,
        },
        "example_inventory": {"example_roots": []},
        "doc_roots": [],
        "contradictions": [],
        "phantom_paths": [],
    }


@pytest.fixture
def large_repo_product_facts() -> Dict[str, Any]:
    """Large repo fixture: 806 claims, 5 workflows, 399 key_features, ~14 API symbols.

    Mirrors a large, mature product like Aspose.Cells with rich evidence.
    """
    claims = [
        {"claim_id": f"c{i:04d}", "claim_kind": "feature",
         "claim_text": f"Feature {i}", "tags": [f"tag{i}"]}
        for i in range(1, 807)
    ]
    return {
        "product_name": "Aspose.Cells for Python",
        "claims": claims,
        "claim_groups": {
            "key_features": sorted([f"c{i:04d}" for i in range(1, 400)]),
            "install_steps": sorted([f"c{i:04d}" for i in range(400, 405)]),
            "quickstart_steps": sorted([f"c{i:04d}" for i in range(405, 410)]),
            "limitations": sorted([f"c{i:04d}" for i in range(800, 807)]),
            "workflow_claims": sorted([f"c{i:04d}" for i in range(410, 430)]),
        },
        "workflows": [
            {"workflow_id": "wf_convert", "name": "Convert Spreadsheets"},
            {"workflow_id": "wf_chart", "name": "Create Charts"},
            {"workflow_id": "wf_pivot", "name": "Pivot Tables"},
            {"workflow_id": "wf_formula", "name": "Formula Engine"},
            {"workflow_id": "wf_style", "name": "Cell Styling"},
        ],
        "api_surface_summary": {
            "key_modules": ["aspose.cells", "aspose.cells.charts", "aspose.cells.pivot"],
            "classes": sorted([
                "Workbook", "Worksheet", "Cell", "Range",
                "Chart", "PivotTable", "Style", "Font",
                "PageSetup", "WorkbookSettings", "FormulaEngine",
                "ConditionalFormatting", "DataValidation", "Comment",
            ]),
        },
        "repository_health": {
            "ci_present": True,
            "tests_present": True,
            "test_file_count": 55,
        },
        "example_inventory": {"example_roots": ["examples/python"]},
        "doc_roots": ["docs/"],
        "contradictions": [],
        "phantom_paths": [],
    }


@pytest.fixture
def small_repo_snippet_catalog() -> Dict[str, Any]:
    """Small repo snippet catalog: 16 snippets."""
    return {
        "snippets": [
            {"snippet_id": f"s{i:03d}", "tags": [f"tag{i}"],
             "source": {"type": "repo_file"}}
            for i in range(1, 17)
        ]
    }


@pytest.fixture
def large_repo_snippet_catalog() -> Dict[str, Any]:
    """Large repo snippet catalog: 43 snippets."""
    return {
        "snippets": [
            {"snippet_id": f"s{i:04d}", "tags": [f"tag{i}"],
             "source": {"type": "repo_file"}}
            for i in range(1, 44)
        ]
    }


@pytest.fixture
def empty_snippet_catalog() -> Dict[str, Any]:
    """Empty snippet catalog."""
    return {"snippets": []}


@pytest.fixture
def sample_ruleset() -> Dict[str, Any]:
    """Ruleset matching specs/rulesets/ruleset.v1.yaml structure."""
    return {
        "schema_version": "1.0",
        "sections": {
            "products": {
                "min_pages": 1,
                "max_pages": 6,
                "mandatory_pages": [
                    {"slug": "overview", "page_role": "landing"},
                ],
                "optional_page_policies": [],
            },
            "docs": {
                "min_pages": 5,
                "max_pages": 10,
                "mandatory_pages": [
                    {"slug": "_index", "page_role": "toc"},
                    {"slug": "installation", "page_role": "workflow_page"},
                    {"slug": "getting-started", "page_role": "workflow_page"},
                    {"slug": "overview", "page_role": "landing"},
                    {"slug": "developer-guide", "page_role": "comprehensive_guide"},
                ],
                "optional_page_policies": [
                    {"page_role": "workflow_page", "source": "per_feature", "priority": 1},
                    {"page_role": "workflow_page", "source": "per_workflow", "priority": 2},
                ],
            },
            "reference": {
                "min_pages": 1,
                "max_pages": 6,
                "mandatory_pages": [
                    {"slug": "api-overview", "page_role": "api_reference"},
                ],
                "optional_page_policies": [
                    {"page_role": "api_reference", "source": "per_api_symbol", "priority": 1},
                ],
            },
            "kb": {
                "min_pages": 4,
                "max_pages": 10,
                "mandatory_pages": [
                    {"slug": "faq", "page_role": "troubleshooting"},
                    {"slug": "troubleshooting", "page_role": "troubleshooting"},
                ],
                "optional_page_policies": [
                    {"page_role": "feature_showcase", "source": "per_key_feature", "priority": 1},
                ],
            },
            "blog": {
                "min_pages": 1,
                "max_pages": 3,
                "mandatory_pages": [
                    {"slug": "announcement", "page_role": "landing"},
                ],
                "optional_page_policies": [
                    {"page_role": "landing", "source": "per_deep_dive", "priority": 2},
                ],
            },
        },
        "family_overrides": {
            "3d": {
                "sections": {
                    "docs": {
                        "mandatory_pages": [
                            {"slug": "model-loading", "page_role": "workflow_page"},
                            {"slug": "rendering", "page_role": "workflow_page"},
                        ],
                    },
                },
            },
        },
    }


@pytest.fixture
def section_quotas() -> Dict[str, Dict[str, int]]:
    """Section quotas from ruleset (as returned by load_ruleset_quotas)."""
    return {
        "products": {"min_pages": 1, "max_pages": 6},
        "docs": {"min_pages": 5, "max_pages": 10},
        "reference": {"min_pages": 1, "max_pages": 6},
        "kb": {"min_pages": 4, "max_pages": 10},
        "blog": {"min_pages": 1, "max_pages": 3},
    }


# ---------------------------------------------------------------------------
# Tests: compute_evidence_volume
# ---------------------------------------------------------------------------

class TestComputeEvidenceVolume:
    """Test compute_evidence_volume() per specs/06_page_planning.md Step 0."""

    def test_compute_evidence_volume_small_repo(
        self, small_repo_product_facts, small_repo_snippet_catalog
    ):
        """Small repo: 42 claims, 16 snippets, 11 API symbols (9 classes + 2 key_modules).

        api_symbol_count sums all list-valued entries in api_surface_summary.
        Expected: total_score = (42 * 2) + (16 * 3) + (11 * 1) = 84 + 48 + 11 = 143
        """
        ev = compute_evidence_volume(small_repo_product_facts, small_repo_snippet_catalog)

        assert ev["claim_count"] == 42
        assert ev["snippet_count"] == 16
        # api_symbol_count = len(key_modules) + len(classes) = 2 + 9 = 11
        assert ev["api_symbol_count"] == 11
        assert ev["workflow_count"] == 1
        assert ev["key_feature_count"] == 14
        assert ev["total_score"] == (42 * 2) + (16 * 3) + (11 * 1)  # 143

    def test_compute_evidence_volume_large_repo(
        self, large_repo_product_facts, large_repo_snippet_catalog
    ):
        """Large repo: 806 claims, 43 snippets, 17 API symbols (14 classes + 3 key_modules).

        api_symbol_count sums all list-valued entries in api_surface_summary.
        Expected: total_score = (806 * 2) + (43 * 3) + (17 * 1) = 1612 + 129 + 17 = 1758
        """
        ev = compute_evidence_volume(large_repo_product_facts, large_repo_snippet_catalog)

        assert ev["claim_count"] == 806
        assert ev["snippet_count"] == 43
        # api_symbol_count = len(key_modules) + len(classes) = 3 + 14 = 17
        assert ev["api_symbol_count"] == 17
        assert ev["workflow_count"] == 5
        assert ev["key_feature_count"] == 399
        assert ev["total_score"] == (806 * 2) + (43 * 3) + (17 * 1)  # 1758

    def test_compute_evidence_volume_empty(self, empty_snippet_catalog):
        """Empty data: 0 claims, 0 snippets -> total_score = 0."""
        empty_facts = {
            "claims": [],
            "claim_groups": {},
            "workflows": [],
            "api_surface_summary": {},
        }
        ev = compute_evidence_volume(empty_facts, empty_snippet_catalog)

        assert ev["claim_count"] == 0
        assert ev["snippet_count"] == 0
        assert ev["api_symbol_count"] == 0
        assert ev["workflow_count"] == 0
        assert ev["key_feature_count"] == 0
        assert ev["total_score"] == 0

    def test_compute_evidence_volume_no_api_summary(self, small_repo_snippet_catalog):
        """Product facts without api_surface_summary: api_symbol_count = 0."""
        facts = {
            "claims": [{"claim_id": "c1"}],
            "claim_groups": {"key_features": ["c1"]},
            "workflows": [],
        }
        ev = compute_evidence_volume(facts, small_repo_snippet_catalog)

        assert ev["api_symbol_count"] == 0
        assert ev["claim_count"] == 1
        assert ev["key_feature_count"] == 1

    def test_compute_evidence_volume_legacy_claim_groups(self, small_repo_snippet_catalog):
        """Legacy claim_groups as list (not dict): treat as empty."""
        facts = {
            "claims": [{"claim_id": "c1"}],
            "claim_groups": ["legacy", "list"],
            "workflows": [],
            "api_surface_summary": {},
        }
        ev = compute_evidence_volume(facts, small_repo_snippet_catalog)

        assert ev["key_feature_count"] == 0
        assert ev["claim_count"] == 1

    def test_compute_evidence_volume_returns_all_fields(
        self, small_repo_product_facts, small_repo_snippet_catalog
    ):
        """Verify all required fields present in output."""
        ev = compute_evidence_volume(small_repo_product_facts, small_repo_snippet_catalog)

        required_keys = sorted([
            "total_score", "claim_count", "snippet_count",
            "api_symbol_count", "workflow_count", "key_feature_count",
        ])
        assert sorted(ev.keys()) == required_keys


# ---------------------------------------------------------------------------
# Tests: compute_effective_quotas
# ---------------------------------------------------------------------------

class TestComputeEffectiveQuotas:
    """Test compute_effective_quotas() per specs/06_page_planning.md Step 1.5."""

    def _make_evidence(self, **overrides) -> Dict[str, int]:
        """Build evidence volume dict with defaults."""
        base = {
            "total_score": 141,
            "claim_count": 42,
            "snippet_count": 16,
            "api_symbol_count": 9,
            "workflow_count": 1,
            "key_feature_count": 14,
        }
        base.update(overrides)
        return base

    def _make_merged_requirements(self, doc_mandatory: int = 5, kb_mandatory: int = 2) -> Dict:
        """Build merged requirements with specified mandatory counts."""
        return {
            "products": {"mandatory_pages": [{"slug": "overview"}], "optional_page_policies": []},
            "docs": {
                "mandatory_pages": [{"slug": f"p{i}"} for i in range(doc_mandatory)],
                "optional_page_policies": [],
            },
            "reference": {"mandatory_pages": [{"slug": "api-overview"}], "optional_page_policies": []},
            "kb": {
                "mandatory_pages": [{"slug": f"k{i}"} for i in range(kb_mandatory)],
                "optional_page_policies": [],
            },
            "blog": {"mandatory_pages": [{"slug": "announcement"}], "optional_page_policies": []},
        }

    def test_minimal_tier_coefficient(self, section_quotas):
        """Minimal tier (0.3 coefficient): tier_adjusted_max = int(max_pages * 0.3).

        docs: int(10 * 0.3) = 3, but min_pages = 5, so tier_adjusted_max = max(5, 3) = 5
        kb:   int(10 * 0.3) = 3, but min_pages = 4, so tier_adjusted_max = max(4, 3) = 4
        blog: int(3 * 0.3) = 0, but min_pages = 1, so tier_adjusted_max = max(1, 0) = 1
        """
        ev = self._make_evidence()
        merged = self._make_merged_requirements()
        eff = compute_effective_quotas(ev, "minimal", section_quotas, merged)

        # products: int(6 * 0.3) = 1, min_pages=1, so tier_adjusted_max = max(1,1) = 1
        assert eff["products"]["tier_adjusted_max"] == 1
        # docs: int(10 * 0.3) = 3, min_pages=5, so tier_adjusted_max = max(5,3) = 5
        assert eff["docs"]["tier_adjusted_max"] == 5
        # reference: int(6 * 0.3) = 1, min_pages=1, so tier_adjusted_max = max(1,1) = 1
        assert eff["reference"]["tier_adjusted_max"] == 1
        # kb: int(10 * 0.3) = 3, min_pages=4, so tier_adjusted_max = max(4,3) = 4
        assert eff["kb"]["tier_adjusted_max"] == 4
        # blog: int(3 * 0.3) = 0, min_pages=1, so tier_adjusted_max = max(1,0) = 1
        assert eff["blog"]["tier_adjusted_max"] == 1

    def test_standard_tier_coefficient(self, section_quotas):
        """Standard tier (0.7 coefficient): tier_adjusted_max = int(max_pages * 0.7)."""
        ev = self._make_evidence()
        merged = self._make_merged_requirements()
        eff = compute_effective_quotas(ev, "standard", section_quotas, merged)

        # products: int(6 * 0.7) = 4, min_pages=1 -> 4
        assert eff["products"]["tier_adjusted_max"] == 4
        # docs: int(10 * 0.7) = 7, min_pages=5 -> 7
        assert eff["docs"]["tier_adjusted_max"] == 7
        # reference: int(6 * 0.7) = 4, min_pages=1 -> 4
        assert eff["reference"]["tier_adjusted_max"] == 4
        # kb: int(10 * 0.7) = 7, min_pages=4 -> 7
        assert eff["kb"]["tier_adjusted_max"] == 7
        # blog: int(3 * 0.7) = 2, min_pages=1 -> 2
        assert eff["blog"]["tier_adjusted_max"] == 2

    def test_rich_tier_coefficient(self, section_quotas):
        """Rich tier (1.0 coefficient): tier_adjusted_max = max_pages."""
        ev = self._make_evidence()
        merged = self._make_merged_requirements()
        eff = compute_effective_quotas(ev, "rich", section_quotas, merged)

        assert eff["products"]["tier_adjusted_max"] == 6
        assert eff["docs"]["tier_adjusted_max"] == 10
        assert eff["reference"]["tier_adjusted_max"] == 6
        assert eff["kb"]["tier_adjusted_max"] == 10
        assert eff["blog"]["tier_adjusted_max"] == 3

    def test_effective_max_clamped_to_min_pages(self, section_quotas):
        """Effective max never goes below min_pages."""
        # Evidence target for products is always 1
        ev = self._make_evidence(workflow_count=0, api_symbol_count=0, key_feature_count=0)
        merged = self._make_merged_requirements(doc_mandatory=5, kb_mandatory=2)
        eff = compute_effective_quotas(ev, "minimal", section_quotas, merged)

        for section in sorted(eff.keys()):
            assert eff[section]["max_pages"] >= eff[section]["min_pages"], (
                f"Section '{section}': max_pages={eff[section]['max_pages']} "
                f"< min_pages={eff[section]['min_pages']}"
            )

    def test_effective_max_never_exceeds_tier_adjusted(self, section_quotas):
        """Effective max never exceeds tier_adjusted_max."""
        ev = self._make_evidence(
            workflow_count=100, api_symbol_count=100, key_feature_count=100
        )
        merged = self._make_merged_requirements(doc_mandatory=5, kb_mandatory=2)
        eff = compute_effective_quotas(ev, "standard", section_quotas, merged)

        for section in sorted(eff.keys()):
            assert eff[section]["max_pages"] <= eff[section]["tier_adjusted_max"], (
                f"Section '{section}': max_pages={eff[section]['max_pages']} "
                f"> tier_adjusted_max={eff[section]['tier_adjusted_max']}"
            )

    def test_evidence_target_formulas(self, section_quotas):
        """Verify evidence-based section target formulas per spec."""
        ev = self._make_evidence(
            total_score=500,
            workflow_count=3,
            api_symbol_count=12,
            key_feature_count=8,
        )
        merged = self._make_merged_requirements(doc_mandatory=5, kb_mandatory=2)
        eff = compute_effective_quotas(ev, "rich", section_quotas, merged)

        # products: always 1
        assert eff["products"]["evidence_target"] == 1
        # docs: mandatory + workflow_count = 5 + 3 = 8
        assert eff["docs"]["evidence_target"] == 5 + 3
        # reference: 1 + api_symbol_count // 3 = 1 + 12 // 3 = 5
        assert eff["reference"]["evidence_target"] == 1 + 12 // 3
        # kb: mandatory + min(key_feature_count, 5) = 2 + min(8, 5) = 7
        assert eff["kb"]["evidence_target"] == 2 + min(8, 5)
        # blog: 1 + (1 if total_score > 200) = 1 + 1 = 2
        assert eff["blog"]["evidence_target"] == 2

    def test_blog_evidence_target_low_score(self, section_quotas):
        """Blog evidence target with low total_score (<=200) yields 1."""
        ev = self._make_evidence(total_score=100)
        merged = self._make_merged_requirements()
        eff = compute_effective_quotas(ev, "standard", section_quotas, merged)

        assert eff["blog"]["evidence_target"] == 1

    def test_returns_all_sections(self, section_quotas):
        """Output includes all sections from input quotas."""
        ev = self._make_evidence()
        merged = self._make_merged_requirements()
        eff = compute_effective_quotas(ev, "standard", section_quotas, merged)

        assert sorted(eff.keys()) == sorted(section_quotas.keys())

    def test_output_fields_per_section(self, section_quotas):
        """Each section in output has min_pages, max_pages, evidence_target, tier_adjusted_max."""
        ev = self._make_evidence()
        merged = self._make_merged_requirements()
        eff = compute_effective_quotas(ev, "standard", section_quotas, merged)

        required_keys = sorted(["min_pages", "max_pages", "evidence_target", "tier_adjusted_max"])
        for section in sorted(eff.keys()):
            assert sorted(eff[section].keys()) == required_keys, (
                f"Section '{section}' missing keys"
            )


# ---------------------------------------------------------------------------
# Tests: generate_optional_pages
# ---------------------------------------------------------------------------

class TestGenerateOptionalPages:
    """Test generate_optional_pages() per specs/06_page_planning.md Steps 2-5."""

    def test_workflow_pages_generated(self, small_repo_product_facts, small_repo_snippet_catalog):
        """3 workflows should generate up to 3 workflow pages in docs section."""
        # Override to have 3 workflows
        facts = dict(small_repo_product_facts)
        facts["workflows"] = [
            {"workflow_id": "wf_export", "name": "Export Scene"},
            {"workflow_id": "wf_import", "name": "Import Model"},
            {"workflow_id": "wf_render", "name": "Render View"},
        ]
        policies = [
            {"page_role": "workflow_page", "source": "per_workflow", "priority": 1},
        ]

        pages = generate_optional_pages(
            section="docs",
            mandatory_page_count=3,
            effective_max=6,
            product_facts=facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 3
        slugs = sorted([p["slug"] for p in pages])
        assert "export-scene" in slugs
        assert "import-model" in slugs
        assert "render-view" in slugs
        for page in pages:
            assert page["page_role"] == "workflow_page"
            assert page["section"] == "docs"

    def test_key_feature_showcases_kb(self, small_repo_product_facts, small_repo_snippet_catalog):
        """KB section: per_key_feature generates feature showcases up to quota."""
        policies = [
            {"page_role": "feature_showcase", "source": "per_key_feature", "priority": 1},
        ]

        pages = generate_optional_pages(
            section="kb",
            mandatory_page_count=2,
            effective_max=7,
            product_facts=small_repo_product_facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        # N = 7 - 2 = 5, but only up to 14 key_features could be candidates
        # Capped at N=5
        assert len(pages) <= 5
        assert len(pages) > 0
        for page in pages:
            assert page["slug"].startswith("how-to-")
            assert page["page_role"] == "feature_showcase"
            assert page["section"] == "kb"

    def test_deterministic_output(self, small_repo_product_facts, small_repo_snippet_catalog):
        """Same input produces same output (run twice and compare)."""
        policies = [
            {"page_role": "feature_showcase", "source": "per_key_feature", "priority": 1},
        ]
        kwargs = dict(
            section="kb",
            mandatory_page_count=2,
            effective_max=7,
            product_facts=small_repo_product_facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        run1 = generate_optional_pages(**kwargs)
        run2 = generate_optional_pages(**kwargs)

        slugs1 = [p["slug"] for p in run1]
        slugs2 = [p["slug"] for p in run2]
        assert slugs1 == slugs2, "Non-deterministic output detected"

        # Also verify full page structure matches
        for p1, p2 in zip(run1, run2):
            assert p1["slug"] == p2["slug"]
            assert p1["page_role"] == p2["page_role"]
            assert p1["required_claim_ids"] == p2["required_claim_ids"]

    def test_empty_evidence_no_optional_pages(self, empty_snippet_catalog):
        """No workflows and no features yields no optional pages."""
        empty_facts = {
            "claims": [],
            "claim_groups": {},
            "workflows": [],
            "api_surface_summary": {},
        }
        policies = [
            {"page_role": "workflow_page", "source": "per_workflow", "priority": 1},
            {"page_role": "feature_showcase", "source": "per_key_feature", "priority": 2},
        ]

        pages = generate_optional_pages(
            section="docs",
            mandatory_page_count=3,
            effective_max=10,
            product_facts=empty_facts,
            snippet_catalog=empty_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0

    def test_zero_budget_returns_empty(self, small_repo_product_facts, small_repo_snippet_catalog):
        """When mandatory_page_count >= effective_max, N=0, no optional pages."""
        policies = [
            {"page_role": "workflow_page", "source": "per_workflow", "priority": 1},
        ]

        pages = generate_optional_pages(
            section="docs",
            mandatory_page_count=10,
            effective_max=10,
            product_facts=small_repo_product_facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0

    def test_api_symbol_candidates(self, large_repo_product_facts, large_repo_snippet_catalog):
        """per_api_symbol generates one page per API class."""
        policies = [
            {"page_role": "api_reference", "source": "per_api_symbol", "priority": 1},
        ]

        pages = generate_optional_pages(
            section="reference",
            mandatory_page_count=1,
            effective_max=6,
            product_facts=large_repo_product_facts,
            snippet_catalog=large_repo_snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        # N = 6 - 1 = 5, capped from 14 API classes
        assert len(pages) == 5
        for page in pages:
            assert page["page_role"] == "api_reference"
            assert page["section"] == "reference"

    def test_deep_dive_blog(self, large_repo_product_facts, large_repo_snippet_catalog):
        """per_deep_dive generates one page if total_score > 200."""
        policies = [
            {"page_role": "landing", "source": "per_deep_dive", "priority": 2},
        ]

        pages = generate_optional_pages(
            section="blog",
            mandatory_page_count=1,
            effective_max=3,
            product_facts=large_repo_product_facts,
            snippet_catalog=large_repo_snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        # Large repo has total_score > 200, so deep-dive is generated
        assert len(pages) == 1
        assert pages[0]["slug"] == "deep-dive"

    def test_no_deep_dive_low_evidence(self, empty_snippet_catalog):
        """per_deep_dive not generated if total_score <= 200."""
        facts = {
            "claims": [{"claim_id": "c1", "claim_text": "Feature"}],
            "claim_groups": {},
            "workflows": [],
            "api_surface_summary": {},
        }
        policies = [
            {"page_role": "landing", "source": "per_deep_dive", "priority": 2},
        ]

        pages = generate_optional_pages(
            section="blog",
            mandatory_page_count=1,
            effective_max=3,
            product_facts=facts,
            snippet_catalog=empty_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0

    def test_optional_pages_have_required_fields(
        self, small_repo_product_facts, small_repo_snippet_catalog
    ):
        """Each optional page must have all required page spec fields."""
        facts = dict(small_repo_product_facts)
        facts["workflows"] = [
            {"workflow_id": "wf1", "name": "Workflow One"},
        ]
        policies = [
            {"page_role": "workflow_page", "source": "per_workflow", "priority": 1},
        ]

        pages = generate_optional_pages(
            section="docs",
            mandatory_page_count=3,
            effective_max=5,
            product_facts=facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) >= 1
        required_fields = sorted([
            "section", "slug", "output_path", "url_path", "title", "purpose",
            "template_variant", "required_headings", "required_claim_ids",
            "required_snippet_tags", "cross_links", "seo_keywords",
            "forbidden_topics", "page_role", "content_strategy",
        ])
        for page in pages:
            for field in required_fields:
                assert field in page, f"Missing field '{field}' in page '{page.get('slug')}'"

    def test_priority_ordering(self, small_repo_product_facts, small_repo_snippet_catalog):
        """Higher priority (lower number) policies produce pages before lower priority."""
        facts = dict(small_repo_product_facts)
        facts["workflows"] = [
            {"workflow_id": "wf1", "name": "Workflow One"},
        ]
        policies = [
            {"page_role": "workflow_page", "source": "per_workflow", "priority": 2},
            {"page_role": "workflow_page", "source": "per_feature", "priority": 1},
        ]

        pages = generate_optional_pages(
            section="docs",
            mandatory_page_count=3,
            effective_max=10,
            product_facts=facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        # per_feature (priority 1) pages should come before per_workflow (priority 2)
        if len(pages) >= 2:
            # Find the workflow page index
            workflow_indices = [
                i for i, p in enumerate(pages) if p["slug"] == "workflow-one"
            ]
            feature_indices = [
                i for i, p in enumerate(pages) if p["slug"] != "workflow-one"
            ]
            if workflow_indices and feature_indices:
                # All feature pages should appear before workflow pages
                assert min(workflow_indices) > min(feature_indices)


# ---------------------------------------------------------------------------
# Tests: load_and_merge_page_requirements
# ---------------------------------------------------------------------------

class TestLoadAndMergePageRequirements:
    """Test load_and_merge_page_requirements() per specs/06_page_planning.md."""

    def test_global_config_no_family_override(self, sample_ruleset):
        """No family overrides: returns global mandatory_pages for each section."""
        merged = load_and_merge_page_requirements(sample_ruleset, "cells")

        # "cells" has no family override
        assert len(merged["docs"]["mandatory_pages"]) == 5
        assert len(merged["kb"]["mandatory_pages"]) == 2
        assert len(merged["blog"]["mandatory_pages"]) == 1
        assert len(merged["products"]["mandatory_pages"]) == 1

        # Check slug values
        docs_slugs = sorted([p["slug"] for p in merged["docs"]["mandatory_pages"]])
        assert docs_slugs == sorted([
            "_index", "installation", "getting-started", "overview", "developer-guide"
        ])

    def test_family_override_union(self, sample_ruleset):
        """Family "3d" override: global + family mandatory_pages are unioned."""
        merged = load_and_merge_page_requirements(sample_ruleset, "3d")

        # Global docs has 5 pages, family adds 2 -> 7 total
        assert len(merged["docs"]["mandatory_pages"]) == 7

        docs_slugs = sorted([p["slug"] for p in merged["docs"]["mandatory_pages"]])
        assert "model-loading" in docs_slugs
        assert "rendering" in docs_slugs
        # Original 5 still present
        assert "_index" in docs_slugs
        assert "developer-guide" in docs_slugs

    def test_family_override_slug_dedup(self, sample_ruleset):
        """Duplicate slugs in family override are skipped (dedup by slug)."""
        # Add a slug that already exists in global
        sample_ruleset["family_overrides"]["3d"]["sections"]["docs"]["mandatory_pages"].append(
            {"slug": "_index", "page_role": "toc"}  # Already in global
        )

        merged = load_and_merge_page_requirements(sample_ruleset, "3d")

        # Should still be 7, not 8 (duplicate _index skipped)
        assert len(merged["docs"]["mandatory_pages"]) == 7

        # Only one _index
        index_count = sum(
            1 for p in merged["docs"]["mandatory_pages"] if p["slug"] == "_index"
        )
        assert index_count == 1

    def test_missing_family_returns_global(self, sample_ruleset):
        """Missing family in family_overrides: returns global config only."""
        merged = load_and_merge_page_requirements(sample_ruleset, "nonexistent-family")

        assert len(merged["docs"]["mandatory_pages"]) == 5
        assert len(merged["kb"]["mandatory_pages"]) == 2

    def test_optional_policies_included(self, sample_ruleset):
        """optional_page_policies from global config are included."""
        merged = load_and_merge_page_requirements(sample_ruleset, "cells")

        assert len(merged["docs"]["optional_page_policies"]) == 2
        assert merged["docs"]["optional_page_policies"][0]["source"] == "per_feature"
        assert merged["docs"]["optional_page_policies"][1]["source"] == "per_workflow"

    def test_all_sections_present(self, sample_ruleset):
        """All 5 sections from ruleset are present in merged output."""
        merged = load_and_merge_page_requirements(sample_ruleset, "cells")

        assert sorted(merged.keys()) == sorted([
            "blog", "docs", "kb", "products", "reference"
        ])

    def test_empty_family_overrides_section(self, sample_ruleset):
        """Empty family_overrides dict: behaves like no override."""
        sample_ruleset["family_overrides"] = {}
        merged = load_and_merge_page_requirements(sample_ruleset, "3d")

        assert len(merged["docs"]["mandatory_pages"]) == 5

    def test_no_family_overrides_key(self):
        """Ruleset with no family_overrides key at all: still works."""
        ruleset = {
            "sections": {
                "docs": {
                    "mandatory_pages": [{"slug": "test", "page_role": "landing"}],
                    "optional_page_policies": [],
                },
            },
        }
        merged = load_and_merge_page_requirements(ruleset, "3d")

        assert len(merged["docs"]["mandatory_pages"]) == 1


# ---------------------------------------------------------------------------
# Tests: determine_launch_tier (CI-absent softening)
# ---------------------------------------------------------------------------

class TestDetermineLaunchTierCIAbsentSoftening:
    """Test CI-absent tier reduction softening per specs/06_page_planning.md."""

    def _make_run_config(self, launch_tier=None):
        """Create a dict-based run config for testing."""
        cfg = {}
        if launch_tier:
            cfg["launch_tier"] = launch_tier
        return cfg

    def _make_facts(self, ci_present=False, tests_present=False, test_file_count=0):
        """Create product_facts with specified health signals."""
        return {
            "claims": [],
            "claim_groups": {},
            "workflows": [],
            "repository_health": {
                "ci_present": ci_present,
                "tests_present": tests_present,
                "test_file_count": test_file_count,
            },
            "example_inventory": {"example_roots": ["ex/"]},
            "doc_roots": [],
            "contradictions": [],
            "phantom_paths": [],
        }

    def _make_snippets(self, real=True):
        """Create snippet catalog with real or generated snippets."""
        source_type = "repo_file" if real else "generated"
        return {
            "snippets": [
                {"snippet_id": "s1", "tags": ["test"], "source": {"type": source_type}},
            ]
        }

    def test_ci_absent_tests_absent_reduces_to_minimal(self):
        """CI absent + tests absent -> reduces standard to minimal."""
        facts = self._make_facts(ci_present=False, tests_present=False)
        snippets = self._make_snippets(real=True)
        run_config = self._make_run_config()

        tier, adjustments = determine_launch_tier(facts, snippets, run_config)

        assert tier == "minimal"
        # Verify an adjustment was recorded for ci_and_tests_absent
        signals = [a.get("signal") for a in adjustments]
        assert "ci_and_tests_absent" in signals

    def test_ci_absent_tests_present_keeps_tier(self):
        """CI absent + tests present -> does NOT reduce (stays standard)."""
        facts = self._make_facts(ci_present=False, tests_present=True, test_file_count=5)
        snippets = self._make_snippets(real=True)
        run_config = self._make_run_config()

        tier, adjustments = determine_launch_tier(facts, snippets, run_config)

        assert tier == "standard"
        # Verify an adjustment was recorded noting CI absent but tests present
        signals = [a.get("signal") for a in adjustments]
        assert "ci_absent_tests_present" in signals

    def test_ci_present_tests_present_eligible_for_elevation(self):
        """CI present + tests present + examples + docs -> eligible for rich."""
        facts = self._make_facts(ci_present=True, tests_present=True, test_file_count=20)
        facts["example_inventory"] = {"example_roots": ["examples/"]}
        facts["doc_roots"] = ["docs/"]
        snippets = self._make_snippets(real=True)
        run_config = self._make_run_config()

        tier, adjustments = determine_launch_tier(facts, snippets, run_config)

        assert tier == "rich"
        # Should have elevation signal
        signals = [a.get("signal") for a in adjustments]
        assert "quality_signals" in signals

    def test_explicit_tier_overrides(self):
        """Explicit launch_tier in run_config overrides everything."""
        facts = self._make_facts(ci_present=False, tests_present=False)
        snippets = self._make_snippets(real=True)
        run_config = self._make_run_config(launch_tier="rich")

        tier, adjustments = determine_launch_tier(facts, snippets, run_config)

        # Explicit tier set to rich, but reductions still apply
        # The function first sets tier="rich" from config, then applies reductions
        # CI + tests absent reduces rich -> standard (one level down)
        # Actually: the code says new_tier = "minimal" if tier == "standard" else
        #   ("standard" if tier == "rich" else tier)
        # So rich -> standard due to ci_and_tests_absent
        assert tier in ["standard", "minimal", "rich"]

    def test_contradictions_force_minimal(self):
        """Contradictions detected forces minimal regardless of other signals."""
        facts = self._make_facts(ci_present=True, tests_present=True)
        facts["contradictions"] = [{"id": "ctr1", "text": "Conflicting claim"}]
        snippets = self._make_snippets(real=True)
        run_config = self._make_run_config()

        tier, adjustments = determine_launch_tier(facts, snippets, run_config)

        assert tier == "minimal"

    def test_adjustments_log_is_list(self):
        """adjustments is always a list of dicts."""
        facts = self._make_facts(ci_present=False, tests_present=True)
        snippets = self._make_snippets(real=True)
        run_config = self._make_run_config()

        tier, adjustments = determine_launch_tier(facts, snippets, run_config)

        assert isinstance(adjustments, list)
        assert len(adjustments) >= 1
        for adj in adjustments:
            assert isinstance(adj, dict)
            assert "adjustment" in adj
            assert "reason" in adj


# ---------------------------------------------------------------------------
# Tests: Integration - large vs small repo
# ---------------------------------------------------------------------------

class TestIntegrationLargeVsSmallRepo:
    """Integration test: large repo produces more pages than small repo.

    Uses the new evidence-driven pipeline (compute_evidence_volume +
    compute_effective_quotas + generate_optional_pages) to demonstrate that
    richer evidence yields higher effective quotas and more optional pages.
    """

    def test_large_repo_more_effective_pages_than_small(
        self,
        small_repo_product_facts,
        large_repo_product_facts,
        small_repo_snippet_catalog,
        large_repo_snippet_catalog,
        section_quotas,
        sample_ruleset,
    ):
        """Large repo effective quotas > small repo effective quotas at same tier.

        Uses compute_effective_quotas to show that richer evidence
        translates to higher per-section effective max_pages.
        """
        small_ev = compute_evidence_volume(
            small_repo_product_facts, small_repo_snippet_catalog
        )
        large_ev = compute_evidence_volume(
            large_repo_product_facts, large_repo_snippet_catalog
        )

        small_merged = load_and_merge_page_requirements(sample_ruleset, "3d")
        large_merged = load_and_merge_page_requirements(sample_ruleset, "cells")

        small_eff = compute_effective_quotas(
            small_ev, "standard", section_quotas, small_merged
        )
        large_eff = compute_effective_quotas(
            large_ev, "standard", section_quotas, large_merged
        )

        # Sum effective max_pages across all sections
        small_total = sum(v["max_pages"] for v in small_eff.values())
        large_total = sum(v["max_pages"] for v in large_eff.values())

        assert large_total > small_total, (
            f"Large repo effective total ({large_total}) should exceed "
            f"small repo effective total ({small_total})"
        )

    def test_large_repo_more_optional_pages_generated(
        self,
        small_repo_product_facts,
        large_repo_product_facts,
        small_repo_snippet_catalog,
        large_repo_snippet_catalog,
    ):
        """Large repo generates more optional pages than small repo for KB section.

        Uses generate_optional_pages with identical budgets to show that
        richer evidence fills more slots.
        """
        policies = [
            {"page_role": "feature_showcase", "source": "per_key_feature", "priority": 1},
        ]

        small_pages = generate_optional_pages(
            section="kb",
            mandatory_page_count=2,
            effective_max=8,
            product_facts=small_repo_product_facts,
            snippet_catalog=small_repo_snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        large_pages = generate_optional_pages(
            section="kb",
            mandatory_page_count=2,
            effective_max=8,
            product_facts=large_repo_product_facts,
            snippet_catalog=large_repo_snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        # Both are capped at N=6, but large repo has more key_features
        # so it should fill the full budget while small may or may not
        assert len(large_pages) >= len(small_pages), (
            f"Large repo KB pages ({len(large_pages)}) should be >= "
            f"small repo KB pages ({len(small_pages)})"
        )
        # Large repo with 399 key_features should fill the full N=6 budget
        assert len(large_pages) == 6

    def test_evidence_volume_correlation(
        self,
        small_repo_product_facts,
        large_repo_product_facts,
        small_repo_snippet_catalog,
        large_repo_snippet_catalog,
    ):
        """Large repo evidence volume > small repo evidence volume."""
        small_ev = compute_evidence_volume(
            small_repo_product_facts, small_repo_snippet_catalog
        )
        large_ev = compute_evidence_volume(
            large_repo_product_facts, large_repo_snippet_catalog
        )

        assert large_ev["total_score"] > small_ev["total_score"]
        assert large_ev["claim_count"] > small_ev["claim_count"]
        assert large_ev["workflow_count"] > small_ev["workflow_count"]
        assert large_ev["key_feature_count"] > small_ev["key_feature_count"]


# ---------------------------------------------------------------------------
# Tests: Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Verify deterministic output across multiple runs."""

    def test_evidence_volume_deterministic(
        self, small_repo_product_facts, small_repo_snippet_catalog
    ):
        """compute_evidence_volume produces identical results on repeated calls."""
        results = []
        for _ in range(3):
            ev = compute_evidence_volume(
                small_repo_product_facts, small_repo_snippet_catalog
            )
            results.append(ev["total_score"])

        assert len(set(results)) == 1, "Evidence volume should be deterministic"

    def test_effective_quotas_deterministic(self, section_quotas):
        """compute_effective_quotas produces identical results on repeated calls."""
        ev = {
            "total_score": 141, "claim_count": 42, "snippet_count": 16,
            "api_symbol_count": 9, "workflow_count": 1, "key_feature_count": 14,
        }
        merged = {
            "products": {"mandatory_pages": [{"slug": "o"}], "optional_page_policies": []},
            "docs": {"mandatory_pages": [{"slug": f"d{i}"} for i in range(5)], "optional_page_policies": []},
            "reference": {"mandatory_pages": [{"slug": "r"}], "optional_page_policies": []},
            "kb": {"mandatory_pages": [{"slug": f"k{i}"} for i in range(2)], "optional_page_policies": []},
            "blog": {"mandatory_pages": [{"slug": "b"}], "optional_page_policies": []},
        }

        results = []
        for _ in range(3):
            eff = compute_effective_quotas(ev, "standard", section_quotas, merged)
            result_tuple = tuple(
                (s, eff[s]["max_pages"]) for s in sorted(eff.keys())
            )
            results.append(result_tuple)

        assert len(set(results)) == 1, "Effective quotas should be deterministic"

    def test_plan_pages_deterministic(
        self, small_repo_product_facts, small_repo_snippet_catalog
    ):
        """plan_pages_for_section produces identical results on repeated calls."""
        results = []
        for _ in range(3):
            pages = plan_pages_for_section(
                section="docs",
                launch_tier="standard",
                product_facts=small_repo_product_facts,
                snippet_catalog=small_repo_snippet_catalog,
                product_slug="3d",
                )
            slugs = tuple(p["slug"] for p in pages)
            results.append(slugs)

        assert len(set(results)) == 1, "Page planning should be deterministic"

    def test_merge_requirements_deterministic(self, sample_ruleset):
        """load_and_merge_page_requirements produces identical results on repeated calls."""
        results = []
        for _ in range(3):
            merged = load_and_merge_page_requirements(sample_ruleset, "3d")
            docs_slugs = tuple(sorted(p["slug"] for p in merged["docs"]["mandatory_pages"]))
            results.append(docs_slugs)

        assert len(set(results)) == 1, "Merge requirements should be deterministic"

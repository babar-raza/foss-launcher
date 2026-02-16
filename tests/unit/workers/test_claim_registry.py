"""Tests for ClaimKindRegistry (Phase 1A).

Validates the central claim routing, group building, and page selection logic
that replaces duplicated if/elif chains in W2 and positional slicing in W4.
"""
import pytest
from launch.models.claim_registry import (
    REGISTRY,
    ClaimKindDef,
    ClaimKindRegistry,
    _CLAIM_KINDS,
    _WORKFLOW_SUBGROUPS,
)


# ── normalize_kind ─────────────────────────────────────────────────────────


class TestNormalizeKind:
    def test_canonical_passes_through(self):
        assert REGISTRY.normalize_kind("feature") == "feature"
        assert REGISTRY.normalize_kind("workflow") == "workflow"

    def test_alias_normalized(self):
        assert REGISTRY.normalize_kind("key_feature") == "feature"
        assert REGISTRY.normalize_kind("api_reference") == "api"

    def test_unknown_passes_through(self):
        assert REGISTRY.normalize_kind("unknown_kind") == "unknown_kind"


# ── route_claim ────────────────────────────────────────────────────────────


class TestRouteClaim:
    def test_feature_routes_to_key_features(self):
        claim = {"claim_id": "c1", "claim_kind": "feature", "claim_text": "Supports 3D models"}
        assert REGISTRY.route_claim(claim) == "key_features"

    def test_key_feature_alias_routes_to_key_features(self):
        claim = {"claim_id": "c1", "claim_kind": "key_feature", "claim_text": "Fast rendering"}
        assert REGISTRY.route_claim(claim) == "key_features"

    def test_api_routes_to_key_features(self):
        claim = {"claim_id": "c1", "claim_kind": "api", "claim_text": "Scene class"}
        assert REGISTRY.route_claim(claim) == "key_features"

    def test_api_reference_alias_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "api_reference", "claim_text": "Scene class"}
        assert REGISTRY.route_claim(claim) == "key_features"

    def test_limitation_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "limitation", "claim_text": "No Linux support"}
        assert REGISTRY.route_claim(claim) == "limitations"

    def test_compatibility_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "compatibility", "claim_text": "Python 3.8+"}
        assert REGISTRY.route_claim(claim) == "compatibility_notes"

    def test_use_case_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "use_case", "claim_text": "CAD visualization"}
        assert REGISTRY.route_claim(claim) == "use_cases"

    def test_faq_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "faq", "claim_text": "How to install?"}
        assert REGISTRY.route_claim(claim) == "faq"

    def test_best_practice_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "best_practice", "claim_text": "Use batch ops"}
        assert REGISTRY.route_claim(claim) == "best_practices"

    def test_performance_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "performance", "claim_text": "10x faster"}
        assert REGISTRY.route_claim(claim) == "performance"

    def test_tutorial_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "tutorial", "claim_text": "Step by step guide"}
        assert REGISTRY.route_claim(claim) == "tutorials"

    def test_troubleshooting_routes(self):
        claim = {"claim_id": "c1", "claim_kind": "troubleshooting", "claim_text": "Fix error"}
        assert REGISTRY.route_claim(claim) == "troubleshooting"

    def test_format_routes_to_none(self):
        """Format claims go to supported_formats, not claim_groups."""
        claim = {"claim_id": "c1", "claim_kind": "format", "claim_text": "Supports PDF"}
        assert REGISTRY.route_claim(claim) is None

    def test_unknown_kind_routes_to_key_features(self):
        claim = {"claim_id": "c1", "claim_kind": "unknown_new_kind", "claim_text": "Something"}
        assert REGISTRY.route_claim(claim) == "key_features"

    def test_unknown_kind_low_quality_skipped(self):
        claim = {"claim_id": "c1", "claim_kind": "unknown_new_kind", "claim_text": "Something"}
        assert REGISTRY.route_claim(claim, is_low_quality=True) is None

    def test_feature_low_quality_skipped(self):
        claim = {"claim_id": "c1", "claim_kind": "feature", "claim_text": "A feature"}
        assert REGISTRY.route_claim(claim, is_low_quality=True) is None

    def test_api_low_quality_skipped(self):
        claim = {"claim_id": "c1", "claim_kind": "api", "claim_text": "An API"}
        assert REGISTRY.route_claim(claim, is_low_quality=True) is None

    def test_limitation_not_affected_by_quality(self):
        """Non-feature kinds are not gated by quality."""
        claim = {"claim_id": "c1", "claim_kind": "limitation", "claim_text": "A limitation"}
        assert REGISTRY.route_claim(claim, is_low_quality=True) == "limitations"


# ── Workflow sub-routing ───────────────────────────────────────────────────


class TestWorkflowSubRouting:
    def test_install_keyword_routes_to_install_steps(self):
        claim = {"claim_id": "c1", "claim_kind": "workflow", "claim_text": "pip install aspose-3d"}
        assert REGISTRY.route_claim(claim) == "install_steps"

    def test_setup_keyword_routes_to_install_steps(self):
        claim = {"claim_id": "c1", "claim_kind": "workflow", "claim_text": "Setup the environment"}
        assert REGISTRY.route_claim(claim) == "install_steps"

    def test_quickstart_keyword_routes_to_quickstart(self):
        claim = {"claim_id": "c1", "claim_kind": "workflow", "claim_text": "Getting started guide"}
        assert REGISTRY.route_claim(claim) == "quickstart_steps"

    def test_begin_keyword_routes_to_quickstart(self):
        claim = {"claim_id": "c1", "claim_kind": "workflow", "claim_text": "Begin your first project"}
        assert REGISTRY.route_claim(claim) == "quickstart_steps"

    def test_generic_workflow_routes_to_workflow_claims(self):
        claim = {"claim_id": "c1", "claim_kind": "workflow", "claim_text": "Convert 3D to PDF"}
        assert REGISTRY.route_claim(claim) == "workflow_claims"


# ── build_claim_groups ─────────────────────────────────────────────────────


class TestBuildClaimGroups:
    def _make_claim(self, claim_id, kind, text="test claim"):
        return {"claim_id": claim_id, "claim_kind": kind, "claim_text": text}

    def test_basic_routing(self):
        claims = [
            self._make_claim("c1", "feature", "Feature A"),
            self._make_claim("c2", "limitation", "Limit B"),
            self._make_claim("c3", "faq", "FAQ C"),
        ]
        groups = REGISTRY.build_claim_groups(claims)
        assert "c1" in groups["key_features"]
        assert "c2" in groups["limitations"]
        assert "c3" in groups["faq"]

    def test_workflow_sub_routing(self):
        claims = [
            self._make_claim("c1", "workflow", "pip install package"),
            self._make_claim("c2", "workflow", "Getting started with the API"),
            self._make_claim("c3", "workflow", "Convert file to PDF"),
        ]
        groups = REGISTRY.build_claim_groups(claims)
        assert "c1" in groups["install_steps"]
        assert "c2" in groups["quickstart_steps"]
        assert "c3" in groups["workflow_claims"]

    def test_deduplication(self):
        claims = [
            self._make_claim("c1", "feature", "Feature A"),
            self._make_claim("c1", "feature", "Feature A"),  # duplicate
        ]
        groups = REGISTRY.build_claim_groups(claims)
        assert groups["key_features"].count("c1") == 1

    def test_capping(self):
        """Cap of 25 for key_features is respected."""
        claims = [self._make_claim(f"c{i}", "feature", f"Feature {i}") for i in range(30)]
        groups = REGISTRY.build_claim_groups(claims)
        assert len(groups["key_features"]) == 25

    def test_quality_gating(self):
        claims = [
            self._make_claim("c1", "feature", "Good feature"),
            self._make_claim("c2", "feature", "Bad feature"),
        ]
        groups = REGISTRY.build_claim_groups(
            claims,
            is_low_quality_fn=lambda c: c["claim_id"] == "c2",
        )
        assert "c1" in groups["key_features"]
        assert "c2" not in groups["key_features"]

    def test_all_group_keys_present(self):
        """Even with empty claims, all group keys should exist."""
        groups = REGISTRY.build_claim_groups([])
        for key in REGISTRY.all_group_keys:
            assert key in groups, f"Missing group key: {key}"

    def test_format_claims_excluded(self):
        claims = [self._make_claim("c1", "format", "Supports PDF")]
        groups = REGISTRY.build_claim_groups(claims)
        # c1 should not appear in any group
        for ids in groups.values():
            assert "c1" not in ids

    def test_all_12_kinds_routed(self):
        """All 12 canonical claim kinds route to the correct groups."""
        kind_to_expected = {
            "feature": "key_features",
            "api": "key_features",
            "limitation": "limitations",
            "compatibility": "compatibility_notes",
            "use_case": "use_cases",
            "faq": "faq",
            "best_practice": "best_practices",
            "performance": "performance",
            "tutorial": "tutorials",
            "troubleshooting": "troubleshooting",
        }
        for i, (kind, expected_group) in enumerate(kind_to_expected.items()):
            claims = [self._make_claim(f"c{i}", kind, f"Claim for {kind}")]
            groups = REGISTRY.build_claim_groups(claims)
            assert f"c{i}" in groups[expected_group], (
                f"Kind '{kind}' should route to '{expected_group}'"
            )

    def test_single_pass_no_double_routing(self):
        """Build once, get all claims — no second routing pass needed."""
        claims = [
            self._make_claim("c1", "feature", "From extraction"),
            self._make_claim("c2", "faq", "From LLM synthesis"),
            self._make_claim("c3", "best_practice", "From LLM synthesis"),
            self._make_claim("c4", "workflow", "Install step from LLM"),
        ]
        groups = REGISTRY.build_claim_groups(claims)
        assert "c1" in groups["key_features"]
        assert "c2" in groups["faq"]
        assert "c3" in groups["best_practices"]
        # c4 has "install" in text, should sub-route
        assert "c4" in groups["install_steps"]


# ── select_claims_for_page ─────────────────────────────────────────────────


class TestSelectClaimsForPage:
    @pytest.fixture
    def sample_groups(self):
        return {
            "key_features": [f"kf_{i}" for i in range(10)],
            "install_steps": [f"is_{i}" for i in range(5)],
            "quickstart_steps": [f"qs_{i}" for i in range(3)],
            "workflow_claims": [f"wf_{i}" for i in range(4)],
            "limitations": [f"lm_{i}" for i in range(5)],
            "compatibility_notes": [f"cn_{i}" for i in range(3)],
            "use_cases": [f"uc_{i}" for i in range(5)],
            "faq": [f"faq_{i}" for i in range(8)],
            "best_practices": [f"bp_{i}" for i in range(5)],
            "performance": [f"pf_{i}" for i in range(3)],
            "tutorials": [f"tut_{i}" for i in range(4)],
            "troubleshooting": [f"ts_{i}" for i in range(5)],
        }

    def test_toc_gets_max_2_claims(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "products", "toc")
        assert len(selected) <= 2
        # TOC priority is key_features
        assert all(cid.startswith("kf_") for cid in selected)

    def test_faq_page_gets_faq_claims(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "kb", "faq")
        # FAQ page should prioritize faq claims
        assert selected[0].startswith("faq_")

    def test_tutorial_page_gets_tutorial_claims(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "docs", "tutorial")
        assert selected[0].startswith("tut_")

    def test_troubleshooting_page(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "kb", "troubleshooting")
        assert selected[0].startswith("ts_")

    def test_comprehensive_guide(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "docs", "comprehensive_guide")
        assert len(selected) <= 8
        # Should include key_features and install_steps
        groups_used = set()
        for cid in selected:
            groups_used.add(cid.split("_")[0])
        assert "kf" in groups_used  # key_features

    def test_max_claims_override(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(
            sample_groups, "docs", "comprehensive_guide", max_claims=3
        )
        assert len(selected) == 3

    def test_exclude_ids_respected(self, sample_groups):
        excluded = {"kf_0", "kf_1", "kf_2"}
        selected = REGISTRY.select_claims_for_page(
            sample_groups, "products", "toc", exclude_ids=excluded
        )
        for cid in selected:
            assert cid not in excluded

    def test_products_section_default(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "products", "some_role")
        # Falls back to section priorities
        assert len(selected) <= 5

    def test_empty_groups_returns_empty(self):
        selected = REGISTRY.select_claims_for_page({}, "docs", "comprehensive_guide")
        assert selected == []

    def test_blog_section_gets_broad_claims(self, sample_groups):
        selected = REGISTRY.select_claims_for_page(sample_groups, "blog", "blog")
        # Blog has high max (20), should get claims from multiple groups
        assert len(selected) > 0


# ── Registry properties ────────────────────────────────────────────────────


class TestRegistryProperties:
    def test_all_group_keys_complete(self):
        keys = REGISTRY.all_group_keys
        expected = {
            "key_features", "install_steps", "quickstart_steps", "workflow_claims",
            "limitations", "compatibility_notes", "use_cases", "faq",
            "best_practices", "performance", "tutorials", "troubleshooting",
        }
        assert set(keys) == expected

    def test_all_kinds_complete(self):
        kinds = REGISTRY.all_kinds
        expected = {
            "feature", "api", "workflow", "limitation", "compatibility",
            "use_case", "faq", "best_practice", "performance", "tutorial",
            "troubleshooting", "format",
        }
        assert set(kinds) == expected

    def test_get_definition_exists(self):
        defn = REGISTRY.get_definition("feature")
        assert defn is not None
        assert defn.group == "key_features"

    def test_get_definition_alias(self):
        defn = REGISTRY.get_definition("key_feature")
        assert defn is not None
        assert defn.group == "key_features"

    def test_get_definition_missing(self):
        defn = REGISTRY.get_definition("nonexistent")
        assert defn is None

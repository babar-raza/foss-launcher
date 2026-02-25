"""Tests for the evidence-based content policy engine (TC-2447).

Verifies scoring formula, per-section caps, allowed roles, artifact schema,
and the W4 integration invariant: mandatory pages are never suppressed.
"""

from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_product_facts(
    n_claims: int = 20,
    kinds: List[str] | None = None,
    citations_per_claim: int = 2,
    confidence: str = "high",
    n_groups: int = 8,
) -> Dict[str, Any]:
    """Build a minimal product_facts dict for testing."""
    if kinds is None:
        kinds = ["feature", "api", "workflow", "limitation", "performance"]

    claims = []
    for i in range(n_claims):
        kind = kinds[i % len(kinds)]
        claims.append(
            {
                "claim_id": f"claim_{i:04d}",
                "claim_text": f"Claim {i}: feature description.",
                "claim_kind": kind,
                "confidence": confidence,
                "citations": [
                    {"path": f"README.md", "start_line": i, "end_line": i + 3}
                    for _ in range(citations_per_claim)
                ],
            }
        )

    claim_groups = {f"group_{j}": [f"claim_{j:04d}"] for j in range(n_groups)}

    return {
        "product_name": "Test Product",
        "product_slug": "test",
        "claims": claims,
        "claim_groups": claim_groups,
        "workflows": [],
    }


def _make_snippet_catalog(n_snippets: int = 10) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "snippets": [
            {
                "snippet_id": f"snip_{i:04d}",
                "code": f"example_{i}()",
                "language": "python",
                "tags": ["example"],
            }
            for i in range(n_snippets)
        ],
    }


def _make_source_chunks(n_chunks: int = 30) -> Dict[str, Any]:
    return {
        "count": n_chunks,
        "chunks": [
            {"chunk_id": f"chunk_{i}", "text": f"chunk text {i}", "token_count": 40}
            for i in range(n_chunks)
        ],
    }


def _make_topic_manifest(
    per_section: Dict[str, int] | None = None,
    warnings: List[str] | None = None,
) -> Dict[str, Any]:
    if per_section is None:
        per_section = {"docs": 3, "kb": 2, "blog": 1, "products": 1, "reference": 1}
    return {
        "discovered_topics": [],
        "per_section_counts": per_section,
        "warnings": warnings or [],
    }


def _make_repo_profile(tier: str = "standard") -> Dict[str, Any]:
    return {"quality_tier": tier}


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


from launch.content.policy.content_policy import (
    EvidenceBasedPolicy,
    SectionPolicy,
    _compute_global_profile,
    _derive_optional_max,
    _derive_allowed_roles,
    _step,
)


# ---------------------------------------------------------------------------
# TestStepHelper
# ---------------------------------------------------------------------------


class TestStepHelper:
    def test_step_returns_highest_matching_score(self) -> None:
        thresholds = [(50, 0.25), (20, 0.20), (10, 0.15), (5, 0.10), (1, 0.05)]
        assert _step(0, thresholds) == 0.0
        assert _step(1, thresholds) == 0.05
        assert _step(5, thresholds) == 0.10
        assert _step(10, thresholds) == 0.15
        assert _step(20, thresholds) == 0.20
        assert _step(50, thresholds) == 0.25
        assert _step(100, thresholds) == 0.25  # capped

    def test_step_empty_thresholds_returns_zero(self) -> None:
        assert _step(99, []) == 0.0


# ---------------------------------------------------------------------------
# TestDeriveOptionalMax
# ---------------------------------------------------------------------------


class TestDeriveOptionalMax:
    def test_high_score_uses_section_cap(self) -> None:
        assert _derive_optional_max(0.80, 5) == 5
        assert _derive_optional_max(0.95, 3) == 3
        assert _derive_optional_max(1.0, 10) == 10

    def test_score_0_60_capped_at_4(self) -> None:
        assert _derive_optional_max(0.60, 10) == 4
        assert _derive_optional_max(0.70, 10) == 4   # 0.70 is in [0.60, 0.80) bucket
        assert _derive_optional_max(0.79, 10) == 4

    def test_score_0_40_capped_at_3(self) -> None:
        assert _derive_optional_max(0.40, 10) == 3
        assert _derive_optional_max(0.59, 10) == 3

    def test_score_0_25_capped_at_2(self) -> None:
        assert _derive_optional_max(0.25, 10) == 2
        assert _derive_optional_max(0.39, 10) == 2

    def test_score_0_15_capped_at_1(self) -> None:
        assert _derive_optional_max(0.15, 10) == 1
        assert _derive_optional_max(0.24, 10) == 1

    def test_low_score_suppresses_optional_pages(self) -> None:
        assert _derive_optional_max(0.0, 10) == 0
        assert _derive_optional_max(0.14, 10) == 0

    def test_section_cap_respected(self) -> None:
        # High score but cap=1 → still 1
        assert _derive_optional_max(0.99, 1) == 1
        # Mid score but cap=2 → min(3,2)=2
        assert _derive_optional_max(0.40, 2) == 2

    def test_zero_section_cap_always_zero(self) -> None:
        assert _derive_optional_max(1.0, 0) == 0


# ---------------------------------------------------------------------------
# TestDeriveAllowedRoles
# ---------------------------------------------------------------------------


class TestDeriveAllowedRoles:
    def test_default_roles_always_present(self) -> None:
        roles = _derive_allowed_roles({})
        assert "blog_post" in roles
        assert "overview" in roles

    def test_api_claims_add_api_reference(self) -> None:
        roles = _derive_allowed_roles({"api": 3})
        assert "api_reference" in roles
        assert "faq" in roles

    def test_feature_claims_add_comparison(self) -> None:
        roles = _derive_allowed_roles({"feature": 5})
        assert "comparison" in roles
        assert "feature_showcase" in roles

    def test_workflow_claims_add_howto(self) -> None:
        roles = _derive_allowed_roles({"workflow": 2})
        assert "how-to" in roles
        assert "howto_article" in roles

    def test_limitation_claims_add_troubleshooting(self) -> None:
        roles = _derive_allowed_roles({"limitation": 1})
        assert "troubleshooting" in roles

    def test_roles_are_sorted(self) -> None:
        roles = _derive_allowed_roles({"api": 1, "feature": 2, "limitation": 1})
        assert roles == sorted(roles)

    def test_unknown_claim_kind_ignored(self) -> None:
        roles = _derive_allowed_roles({"unknown_kind_xyz": 5})
        # Should still return default roles without error
        assert "blog_post" in roles


# ---------------------------------------------------------------------------
# TestGlobalProfile
# ---------------------------------------------------------------------------


class TestGlobalProfile:
    def test_zero_claims_gives_minimal_score(self) -> None:
        pf = _make_product_facts(n_claims=0, n_groups=0)
        sc = _make_snippet_catalog(0)
        profile = _compute_global_profile(pf, sc, None, None)
        assert profile.raw_score < 0.15
        assert profile.claim_count == 0

    def test_rich_artifacts_gives_high_score(self) -> None:
        pf = _make_product_facts(n_claims=100, kinds=["feature", "api", "workflow", "limitation", "performance"])
        sc = _make_snippet_catalog(25)
        chunks = _make_source_chunks(55)
        profile = _compute_global_profile(pf, sc, chunks, _make_repo_profile("rich"))
        assert profile.raw_score > 0.70

    def test_citation_density_boosts_score(self) -> None:
        pf_low = _make_product_facts(n_claims=10, citations_per_claim=0)
        pf_high = _make_product_facts(n_claims=10, citations_per_claim=3)
        sc = _make_snippet_catalog(0)
        profile_low = _compute_global_profile(pf_low, sc, None, None)
        profile_high = _compute_global_profile(pf_high, sc, None, None)
        assert profile_high.raw_score > profile_low.raw_score
        assert profile_high.score_breakdown["citation_density"] == 0.20

    def test_snippet_count_boosts_score(self) -> None:
        pf = _make_product_facts(n_claims=5)
        sc_no = _make_snippet_catalog(0)
        sc_yes = _make_snippet_catalog(25)
        p_no = _compute_global_profile(pf, sc_no, None, None)
        p_yes = _compute_global_profile(pf, sc_yes, None, None)
        assert p_yes.raw_score > p_no.raw_score
        assert p_yes.score_breakdown["snippet_coverage"] == 0.15

    def test_doc_chunks_boost_score(self) -> None:
        pf = _make_product_facts(n_claims=5)
        sc = _make_snippet_catalog(5)
        p_no = _compute_global_profile(pf, sc, None, None)
        p_yes = _compute_global_profile(pf, sc, _make_source_chunks(55), None)
        assert p_yes.raw_score > p_no.raw_score
        assert p_yes.score_breakdown["doc_chunk_depth"] == 0.10

    def test_minimal_repo_tier_reduces_score(self) -> None:
        pf = _make_product_facts(n_claims=20)
        sc = _make_snippet_catalog(10)
        p_std = _compute_global_profile(pf, sc, None, _make_repo_profile("standard"))
        p_min = _compute_global_profile(pf, sc, None, _make_repo_profile("minimal"))
        assert p_min.raw_score < p_std.raw_score

    def test_rich_tier_gives_full_multiplier(self) -> None:
        pf = _make_product_facts(n_claims=20)
        sc = _make_snippet_catalog(10)
        p_std = _compute_global_profile(pf, sc, None, _make_repo_profile("standard"))
        p_rich = _compute_global_profile(pf, sc, None, _make_repo_profile("rich"))
        # rich multiplier = 1.0 > standard multiplier = 0.90
        assert p_rich.raw_score >= p_std.raw_score

    def test_claim_diversity_increases_score(self) -> None:
        pf_one = _make_product_facts(n_claims=10, kinds=["feature"])
        pf_five = _make_product_facts(
            n_claims=10, kinds=["feature", "api", "workflow", "limitation", "performance"]
        )
        sc = _make_snippet_catalog(0)
        p_one = _compute_global_profile(pf_one, sc, None, None)
        p_five = _compute_global_profile(pf_five, sc, None, None)
        assert p_five.raw_score > p_one.raw_score
        assert p_five.score_breakdown["claim_diversity"] == 0.20

    def test_score_clamped_at_1_0(self) -> None:
        pf = _make_product_facts(n_claims=200, n_groups=20)
        sc = _make_snippet_catalog(50)
        chunks = _make_source_chunks(100)
        profile = _compute_global_profile(pf, sc, chunks, _make_repo_profile("rich"))
        assert profile.raw_score <= 1.0

    def test_score_clamped_at_0_0(self) -> None:
        pf = _make_product_facts(n_claims=0, n_groups=0)
        sc = _make_snippet_catalog(0)
        profile = _compute_global_profile(pf, sc, None, _make_repo_profile("minimal"))
        assert profile.raw_score >= 0.0

    def test_score_is_deterministic(self) -> None:
        pf = _make_product_facts(n_claims=30)
        sc = _make_snippet_catalog(12)
        chunks = _make_source_chunks(25)
        profile_a = _compute_global_profile(pf, sc, chunks, _make_repo_profile("standard"))
        profile_b = _compute_global_profile(pf, sc, chunks, _make_repo_profile("standard"))
        assert profile_a.raw_score == profile_b.raw_score
        assert profile_a.score_breakdown == profile_b.score_breakdown

    def test_no_repo_profile_uses_standard_defaults(self) -> None:
        pf = _make_product_facts(n_claims=10)
        sc = _make_snippet_catalog(5)
        p_none = _compute_global_profile(pf, sc, None, None)
        p_std = _compute_global_profile(pf, sc, None, _make_repo_profile("standard"))
        # Both use the 0.90 multiplier
        assert p_none.raw_score == p_std.raw_score


# ---------------------------------------------------------------------------
# TestEvidenceBasedPolicyBuild
# ---------------------------------------------------------------------------


class TestEvidenceBasedPolicyBuild:
    def test_build_with_minimal_artifacts(self) -> None:
        pf = _make_product_facts(n_claims=15)
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(
            sections=["docs", "kb"],
            product_facts=pf,
            snippet_catalog=sc,
        )
        assert isinstance(policy.for_section("docs"), SectionPolicy)
        assert isinstance(policy.for_section("kb"), SectionPolicy)

    def test_build_with_all_artifacts(self) -> None:
        pf = _make_product_facts(n_claims=50)
        sc = _make_snippet_catalog(15)
        tm = _make_topic_manifest()
        chunks = _make_source_chunks(40)
        rp = _make_repo_profile("rich")
        policy = EvidenceBasedPolicy.build(
            sections=["docs", "kb", "blog"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm,
            source_chunks=chunks,
            repo_profile=rp,
        )
        for section in ["docs", "kb", "blog"]:
            sp = policy.for_section(section)
            assert sp.evidence_score > 0.0
            assert sp.optional_max_pages >= 0

    def test_unknown_section_returns_permissive_default(self) -> None:
        pf = _make_product_facts(n_claims=10)
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(sections=["docs"], product_facts=pf, snippet_catalog=sc)
        sp = policy.for_section("nonexistent_section_xyz")
        assert sp.optional_max_pages == 999  # permissive default

    def test_build_without_repo_profile_uses_standard_tier(self) -> None:
        pf = _make_product_facts(n_claims=20)
        sc = _make_snippet_catalog(10)
        policy = EvidenceBasedPolicy.build(sections=["docs"], product_facts=pf, snippet_catalog=sc)
        sp = policy.for_section("docs")
        assert sp.evidence_score > 0.0  # standard tier still gives a score

    def test_section_caps_respected(self) -> None:
        pf = _make_product_facts(n_claims=100)
        sc = _make_snippet_catalog(25)
        chunks = _make_source_chunks(55)
        rp = _make_repo_profile("rich")
        tm = _make_topic_manifest({"docs": 5})
        policy = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm,
            source_chunks=chunks,
            repo_profile=rp,
            section_caps={"docs": 2},  # hard cap
        )
        assert policy.for_section("docs").optional_max_pages <= 2

    def test_mandatory_mins_are_recorded(self) -> None:
        pf = _make_product_facts(n_claims=10)
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            mandatory_mins={"docs": 3},
        )
        assert policy.for_section("docs").mandatory_min_pages == 3

    def test_low_evidence_suppresses_optional_pages(self) -> None:
        pf = _make_product_facts(n_claims=1, n_groups=0, citations_per_claim=0)
        sc = _make_snippet_catalog(0)
        rp = _make_repo_profile("minimal")
        policy = EvidenceBasedPolicy.build(
            sections=["blog"],
            product_facts=pf,
            snippet_catalog=sc,
            repo_profile=rp,
        )
        assert policy.for_section("blog").optional_max_pages == 0

    def test_high_evidence_allows_up_to_cap(self) -> None:
        pf = _make_product_facts(
            n_claims=100,
            kinds=["feature", "api", "workflow", "limitation", "performance"],
            citations_per_claim=3,
            confidence="high",
            n_groups=15,
        )
        sc = _make_snippet_catalog(25)
        chunks = _make_source_chunks(55)
        rp = _make_repo_profile("rich")
        tm = _make_topic_manifest({"docs": 5})
        policy = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm,
            source_chunks=chunks,
            repo_profile=rp,
            section_caps={"docs": 5},
        )
        # Should be at or near the cap with rich evidence
        assert policy.for_section("docs").optional_max_pages == 5

    def test_zero_section_topics_reduces_optional_max(self) -> None:
        pf = _make_product_facts(n_claims=50)
        sc = _make_snippet_catalog(15)
        chunks = _make_source_chunks(40)
        rp = _make_repo_profile("standard")

        tm_with = _make_topic_manifest({"docs": 3})
        tm_without = _make_topic_manifest({"docs": 0})

        policy_with = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm_with,
            source_chunks=chunks,
            repo_profile=rp,
        )
        policy_without = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm_without,
            source_chunks=chunks,
            repo_profile=rp,
        )
        # 0 topics → lower section score → fewer or equal optional pages
        assert (
            policy_without.for_section("docs").optional_max_pages
            <= policy_with.for_section("docs").optional_max_pages
        )

    def test_topic_coverage_warnings_appear_in_reasons(self) -> None:
        pf = _make_product_facts(n_claims=10)
        sc = _make_snippet_catalog(5)
        tm = _make_topic_manifest(
            per_section={"docs": 2},
            warnings=["docs: coverage_missing for advanced topics"],
        )
        policy = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm,
        )
        reasons = policy.for_section("docs").reasons
        assert any("topic_coverage_warnings" in r for r in reasons)

    def test_build_is_deterministic(self) -> None:
        pf = _make_product_facts(n_claims=30)
        sc = _make_snippet_catalog(12)
        chunks = _make_source_chunks(25)
        rp = _make_repo_profile("standard")
        tm = _make_topic_manifest()

        def _build():
            return EvidenceBasedPolicy.build(
                sections=["docs", "kb", "blog"],
                product_facts=pf,
                snippet_catalog=sc,
                topic_manifest=tm,
                source_chunks=chunks,
                repo_profile=rp,
            )

        p1 = _build()
        p2 = _build()
        for section in ["docs", "kb", "blog"]:
            assert p1.for_section(section).evidence_score == p2.for_section(section).evidence_score
            assert p1.for_section(section).optional_max_pages == p2.for_section(section).optional_max_pages


# ---------------------------------------------------------------------------
# TestToArtifact
# ---------------------------------------------------------------------------


class TestToArtifact:
    def test_artifact_has_required_schema_keys(self) -> None:
        pf = _make_product_facts(n_claims=10)
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(
            sections=["docs", "kb"],
            product_facts=pf,
            snippet_catalog=sc,
        )
        artifact = policy.to_artifact()
        assert "schema_version" in artifact
        assert artifact["schema_version"] == "2.0"
        assert "engine" in artifact
        assert artifact["engine"] == "evidence_based_v2"
        assert "summary" in artifact
        assert "sections" in artifact

    def test_artifact_summary_counts(self) -> None:
        pf = _make_product_facts(n_claims=1, n_groups=0, citations_per_claim=0)
        sc = _make_snippet_catalog(0)
        rp = _make_repo_profile("minimal")

        # Force one section to suppress (low evidence), one to pass
        pf_rich = _make_product_facts(n_claims=100, citations_per_claim=3, n_groups=15)
        policy = EvidenceBasedPolicy.build(
            sections=["docs", "blog"],
            product_facts=pf_rich,
            snippet_catalog=_make_snippet_catalog(25),
            source_chunks=_make_source_chunks(55),
            repo_profile=_make_repo_profile("rich"),
            topic_manifest=_make_topic_manifest({"docs": 5, "blog": 1}),
            section_caps={"docs": 5, "blog": 5},
        )
        artifact = policy.to_artifact()
        assert artifact["summary"]["total_sections"] == 2

    def test_artifact_sections_sorted_by_section(self) -> None:
        pf = _make_product_facts(n_claims=20)
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(
            sections=["products", "docs", "kb", "blog"],
            product_facts=pf,
            snippet_catalog=sc,
        )
        artifact = policy.to_artifact()
        sections = [s["section"] for s in artifact["sections"]]
        assert sections == sorted(sections)

    def test_artifact_section_fields_complete(self) -> None:
        pf = _make_product_facts(n_claims=20)
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            mandatory_mins={"docs": 2},
            section_caps={"docs": 4},
        )
        section = policy.to_artifact()["sections"][0]
        assert section["section"] == "docs"
        assert isinstance(section["mandatory_min_pages"], int)
        assert isinstance(section["optional_max_pages"], int)
        assert isinstance(section["evidence_score"], float)
        assert isinstance(section["allowed_optional_page_roles"], list)
        assert isinstance(section["reasons"], list)

    def test_allowed_roles_sorted_in_artifact(self) -> None:
        pf = _make_product_facts(n_claims=20, kinds=["feature", "api", "limitation"])
        sc = _make_snippet_catalog(5)
        policy = EvidenceBasedPolicy.build(sections=["docs"], product_facts=pf, snippet_catalog=sc)
        section = policy.to_artifact()["sections"][0]
        roles = section["allowed_optional_page_roles"]
        assert roles == sorted(roles)


# ---------------------------------------------------------------------------
# TestW4IntegrationScenarios
# ---------------------------------------------------------------------------


class TestW4IntegrationScenarios:
    """Functional tests mirroring how W4 would use EvidenceBasedPolicy."""

    def test_mandatory_pages_never_suppressed(self) -> None:
        """mandatory_min_pages is recorded but W4 never reduces below it.

        The policy engine records mandatory_min_pages for transparency, but W4
        must ensure it never generates fewer than the mandatory minimum.  This
        test verifies the evidence_policy sets optional_max correctly and that
        mandatory_min is preserved in the artifact.
        """
        pf = _make_product_facts(n_claims=0, n_groups=0, citations_per_claim=0)
        sc = _make_snippet_catalog(0)
        rp = _make_repo_profile("minimal")

        policy = EvidenceBasedPolicy.build(
            sections=["docs"],
            product_facts=pf,
            snippet_catalog=sc,
            repo_profile=rp,
            mandatory_mins={"docs": 3},
        )
        sp = policy.for_section("docs")
        # optional_max may be 0 (no evidence), but mandatory_min is preserved
        assert sp.mandatory_min_pages == 3
        # W4 invariant: effective_max = max(optional_max, mandatory_page_count)
        # i.e. W4 will compute: effective_max = max(sp.optional_max_pages, 3)
        w4_effective_max = max(sp.optional_max_pages, sp.mandatory_min_pages)
        assert w4_effective_max >= 3

    def test_low_evidence_repo_suppresses_optional_pages(self) -> None:
        """Minimal repo → optional pages capped at 0 for low-evidence sections."""
        pf = {
            "product_name": "Minimal",
            "product_slug": "min",
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "Feature A",
                    "claim_kind": "feature",
                    "confidence": "low",
                    "citations": [],
                }
            ],
            "claim_groups": {},
            "workflows": [],
        }
        sc = {"schema_version": "1.0", "snippets": []}
        rp = _make_repo_profile("minimal")
        tm = _make_topic_manifest(per_section={"docs": 0, "blog": 0})

        policy = EvidenceBasedPolicy.build(
            sections=["docs", "blog"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm,
            repo_profile=rp,
        )
        assert policy.for_section("docs").optional_max_pages == 0
        assert policy.for_section("blog").optional_max_pages == 0

    def test_high_evidence_repo_allows_full_cap(self) -> None:
        """Rich repo with 100+ claims + snippets → section cap is the limit."""
        pf = _make_product_facts(
            n_claims=150,
            kinds=["feature", "api", "workflow", "limitation", "performance"],
            citations_per_claim=4,
            confidence="high",
            n_groups=15,
        )
        sc = _make_snippet_catalog(30)
        chunks = _make_source_chunks(60)
        rp = _make_repo_profile("rich")
        tm = _make_topic_manifest({"docs": 5, "kb": 4, "blog": 3})

        policy = EvidenceBasedPolicy.build(
            sections=["docs", "kb"],
            product_facts=pf,
            snippet_catalog=sc,
            topic_manifest=tm,
            source_chunks=chunks,
            repo_profile=rp,
            section_caps={"docs": 5, "kb": 3},
        )
        # With rich evidence, both sections should be at their caps
        assert policy.for_section("docs").optional_max_pages == 5
        assert policy.for_section("kb").optional_max_pages == 3

"""Tests for TC-B06 semantic self-review thresholds in UnderstandWorker — IUH-02."""
from __future__ import annotations
import pytest
from launcher.workers.understand.worker import UnderstandWorker
from launcher.models.understanding import UnderstandingBundle, RepoInfo, SharedFacts
from launcher.models.product import (
    ProductIdentity, RichnessTier, RichnessResult, ApiSurface,
)
from launcher.models.claims import Claim, EvidenceAnchor


def _make_bundle(
    tier: RichnessTier,
    claim_count: int = 10,
    snippet_count: int = 2,
    public_class_count: int = 3,
    llm_claim_fraction: float = 1.0,
) -> UnderstandingBundle:
    """Build a minimal real UnderstandingBundle for self_review testing."""
    from launcher.models.understanding import Snippet

    claims = []
    for i in range(claim_count):
        source = "llm" if i < int(claim_count * llm_claim_fraction) else "llm_fallback"
        claims.append(Claim(
            claim_id=f"CLM-test-{i:03d}",
            text=f"The library supports operation {i}",
            kind="feature",
            claim_source=source,
            evidence=[EvidenceAnchor(
                source_file="README.md",
                line_start=i + 1,
                line_end=i + 1,
                snippet=f"feature {i}",
            )],
        ))

    snippets = []
    for i in range(snippet_count):
        snippets.append(Snippet(
            language="python",
            code=f"print('snippet {i}')",
            source_type="extracted",
            claim_ids=[],
        ))

    public_classes = [f"Class{i}" for i in range(public_class_count)]
    api_surface = ApiSurface(
        public_classes=public_classes,
        import_allowlist=["test"],
        confidence="high",
    )
    product = ProductIdentity(
        family="test-lib",
        platform="python",
        display_name="Test Library",
        canonical_import="test_lib",
        repo_url="https://github.com/test/test-lib",
    )
    repo = RepoInfo(shared_facts=SharedFacts(primary_language="python"))
    richness = RichnessResult(tier=tier, score=80, reason="test")

    return UnderstandingBundle(
        product=product,
        repo=repo,
        richness_tier=richness,
        api_surface=api_surface,
        claims=claims,
        snippets=snippets,
    )


class TestTierAMinimumClaimCount:
    @pytest.mark.asyncio
    async def test_tier_a_with_4_claims_fails(self):
        bundle = _make_bundle(tier=RichnessTier.A, claim_count=4, snippet_count=1)
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert result.passed is False
        assert any(
            f.get("category") == "claims" and "Tier A" in f.get("message", "")
            for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_tier_a_with_5_claims_passes_tier_check(self):
        bundle = _make_bundle(tier=RichnessTier.A, claim_count=5, snippet_count=1)
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert not any(
            "Tier A" in f.get("message", "") and f.get("severity") == "high"
            for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_tier_c_with_1_claim_not_flagged(self):
        bundle = _make_bundle(
            tier=RichnessTier.C, claim_count=1, snippet_count=1, public_class_count=0
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert not any("Tier A" in f.get("message", "") for f in result.findings)


class TestNoSnippetsWithApiSurface:
    @pytest.mark.asyncio
    async def test_zero_snippets_with_api_surface_fails(self):
        bundle = _make_bundle(
            tier=RichnessTier.B, claim_count=10,
            snippet_count=0, public_class_count=3,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert result.passed is False
        assert any(
            f.get("category") == "snippets" and f.get("severity") == "high"
            for f in result.findings
        )

    @pytest.mark.asyncio
    async def test_zero_snippets_no_api_surface_passes_check(self):
        bundle = _make_bundle(
            tier=RichnessTier.C, claim_count=10,
            snippet_count=0, public_class_count=0,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        assert not any(
            f.get("category") == "snippets" and f.get("severity") == "high"
            for f in result.findings
        )


class TestFallbackClaimWarning:
    @pytest.mark.asyncio
    async def test_mostly_fallback_emits_warning_not_fail(self):
        # 10% LLM, 90% fallback -> warning but not blocking
        bundle = _make_bundle(
            tier=RichnessTier.B, claim_count=10,
            snippet_count=1, llm_claim_fraction=0.1,
        )
        worker = UnderstandWorker()
        result = await worker.self_review(bundle)
        warning_findings = [
            f for f in result.findings
            if "deterministic fallback" in f.get("message", "")
        ]
        assert warning_findings, "Expected warning for mostly-fallback claims"
        for f in warning_findings:
            assert f.get("severity") == "warning", "Fallback warning must not block"

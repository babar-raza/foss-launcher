"""Tests for TC-HYBRID-09: scenario-aware planning."""
import pytest
from launcher.models.claims import Claim, EvidenceAnchor
from launcher.workers.planner.plan import detect_primary_scenario, _set_blog_variants


def _claim(kind: str, text: str = "some claim text") -> Claim:
    return Claim(claim_id=f"c-{kind}-{hash(text)%1000}", text=text, kind=kind)


class TestDetectPrimaryScenario:
    def test_returns_default_for_empty_claims(self):
        assert detect_primary_scenario([]) == "default"

    def test_tutorial_when_30pct_tutorial_kind(self):
        claims = [_claim("tutorial")] * 3 + [_claim("feature")] * 7
        assert detect_primary_scenario(claims) == "tutorial"

    def test_tutorial_from_example_kind(self):
        claims = [_claim("example")] * 4 + [_claim("api")] * 6
        assert detect_primary_scenario(claims) == "tutorial"

    def test_tutorial_from_workflow_kind(self):
        claims = [_claim("workflow")] * 3 + [_claim("feature")] * 7
        assert detect_primary_scenario(claims) == "tutorial"

    def test_migration_when_20pct_migration_text(self):
        claims = [_claim("use_case", "migrate from old API")] * 2 + [_claim("feature")] * 8
        assert detect_primary_scenario(claims) == "migration"

    def test_migration_uses_text_signal_not_kind(self):
        claims = [_claim("feature", "upgrade from v1 to v2")] * 3 + [_claim("api")] * 7
        assert detect_primary_scenario(claims) == "migration"

    def test_evaluation_when_20pct_comparison_text(self):
        claims = [_claim("feature", "better than other library")] * 2 + [_claim("feature")] * 8
        assert detect_primary_scenario(claims) == "evaluation"

    def test_announcement_when_40pct_feature_no_tutorial(self):
        claims = [_claim("feature")] * 5 + [_claim("install")] * 3 + [_claim("api")] * 2
        assert detect_primary_scenario(claims) == "announcement"

    def test_no_announcement_when_tutorial_present(self):
        claims = [_claim("feature")] * 5 + [_claim("tutorial")] * 5
        # tutorial takes priority (50% > 30% threshold)
        assert detect_primary_scenario(claims) == "tutorial"

    def test_default_for_mixed_signals(self):
        claims = [_claim("api")] * 5 + [_claim("config")] * 5
        assert detect_primary_scenario(claims) == "default"


class TestSetBlogVariants:
    def test_sets_variant_on_feature_blog(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "tutorial")
        assert pages[0]["skeleton_variant"] == "tutorial"

    def test_skips_non_blog_pages(self):
        pages = [{"page_id": "docs/api", "page_role": "api_reference"}]
        _set_blog_variants(pages, "tutorial")
        assert "skeleton_variant" not in pages[0]

    def test_does_not_override_existing_variant(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog", "skeleton_variant": "install"}]
        _set_blog_variants(pages, "tutorial")
        assert pages[0]["skeleton_variant"] == "install"

    def test_skips_when_scenario_default(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "default")
        assert pages[0].get("skeleton_variant") is None

    def test_skips_unregistered_variant(self):
        # "evaluation" variant is not registered for feature_blog
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "evaluation")
        assert pages[0].get("skeleton_variant") is None

    def test_migration_variant_registered(self):
        pages = [{"page_id": "blog/p1", "page_role": "feature_blog"}]
        _set_blog_variants(pages, "migration")
        assert pages[0]["skeleton_variant"] == "migration"

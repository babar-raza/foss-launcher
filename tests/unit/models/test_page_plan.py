"""Tests for PagePlan model.

Validates:
- PagePlan serialization (to_dict/from_dict)
- Round-trip consistency
- Optional fields handling
- Validation logic
- Sub-component models (PageEntry, ContentStrategy, ClaimQuota, LaunchTierAdjustment)

TC-1031: Typed Artifact Models -- Worker Models
"""

import pytest

from src.launch.models.page_plan import (
    ClaimQuota,
    ContentStrategy,
    LaunchTierAdjustment,
    PageEntry,
    PagePlan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_page_entry_data() -> dict:
    """Create minimal PageEntry dict for testing."""
    return {
        "section": "docs",
        "slug": "overview",
        "output_path": "content/docs/python/overview/_index.md",
        "url_path": "/docs/python/overview/",
        "title": "Overview",
        "purpose": "Product overview page",
        "required_headings": ["Features", "Installation"],
        "required_claim_ids": ["claim_001", "claim_002"],
        "required_snippet_tags": ["install"],
        "cross_links": ["https://products.aspose.org/3d/python/"],
    }


def _minimal_page_plan_data() -> dict:
    """Create minimal PagePlan dict for testing."""
    return {
        "schema_version": "1.0",
        "product_slug": "aspose-3d",
        "launch_tier": "standard",
        "pages": [_minimal_page_entry_data()],
    }


# ---------------------------------------------------------------------------
# ClaimQuota tests
# ---------------------------------------------------------------------------

def test_claim_quota_defaults():
    """Test ClaimQuota with defaults."""
    quota = ClaimQuota()
    data = quota.to_dict()
    assert data["min"] == 0
    assert data["max"] == 999


def test_claim_quota_custom():
    """Test ClaimQuota with custom values."""
    quota = ClaimQuota(min_claims=3, max_claims=10)
    data = quota.to_dict()
    assert data["min"] == 3
    assert data["max"] == 10


def test_claim_quota_round_trip():
    """Test ClaimQuota round-trip."""
    original = ClaimQuota(min_claims=2, max_claims=8)
    data = original.to_dict()
    restored = ClaimQuota.from_dict(data)
    assert restored.min_claims == original.min_claims
    assert restored.max_claims == original.max_claims


# ---------------------------------------------------------------------------
# ContentStrategy tests
# ---------------------------------------------------------------------------

def test_content_strategy_minimal():
    """Test ContentStrategy with no fields."""
    strategy = ContentStrategy()
    data = strategy.to_dict()
    assert data == {}


def test_content_strategy_full():
    """Test ContentStrategy with all fields."""
    strategy = ContentStrategy(
        primary_focus="Product installation guide",
        forbidden_topics=["troubleshooting", "pricing"],
        claim_quota=ClaimQuota(min_claims=2, max_claims=5),
        child_pages=["install", "setup"],
        scenario_coverage="all",
    )
    data = strategy.to_dict()
    assert data["primary_focus"] == "Product installation guide"
    assert data["forbidden_topics"] == ["pricing", "troubleshooting"]  # sorted
    assert data["claim_quota"]["min"] == 2
    assert data["claim_quota"]["max"] == 5
    assert data["child_pages"] == ["install", "setup"]
    assert data["scenario_coverage"] == "all"


def test_content_strategy_round_trip():
    """Test ContentStrategy round-trip."""
    original = ContentStrategy(
        primary_focus="Test focus",
        claim_quota=ClaimQuota(min_claims=1, max_claims=3),
    )
    data = original.to_dict()
    restored = ContentStrategy.from_dict(data)
    assert restored.primary_focus == original.primary_focus
    assert restored.claim_quota.min_claims == original.claim_quota.min_claims


# ---------------------------------------------------------------------------
# LaunchTierAdjustment tests
# ---------------------------------------------------------------------------

def test_launch_tier_adjustment_minimal():
    """Test LaunchTierAdjustment with required fields only."""
    adj = LaunchTierAdjustment(adjustment="elevated", reason="High star count")
    data = adj.to_dict()
    assert data["adjustment"] == "elevated"
    assert data["reason"] == "High star count"
    assert "from_tier" not in data
    assert "to_tier" not in data


def test_launch_tier_adjustment_full():
    """Test LaunchTierAdjustment with all fields."""
    adj = LaunchTierAdjustment(
        adjustment="elevated",
        reason="High star count",
        from_tier="minimal",
        to_tier="standard",
        signal="github_stars",
    )
    data = adj.to_dict()
    assert data["from_tier"] == "minimal"
    assert data["to_tier"] == "standard"
    assert data["signal"] == "github_stars"


def test_launch_tier_adjustment_round_trip():
    """Test LaunchTierAdjustment round-trip."""
    original = LaunchTierAdjustment(
        adjustment="unchanged",
        reason="Default tier",
        from_tier="standard",
        to_tier="standard",
    )
    data = original.to_dict()
    restored = LaunchTierAdjustment.from_dict(data)
    assert restored.adjustment == original.adjustment
    assert restored.from_tier == original.from_tier


# ---------------------------------------------------------------------------
# PageEntry tests
# ---------------------------------------------------------------------------

def test_page_entry_minimal():
    """Test PageEntry with required fields."""
    data = _minimal_page_entry_data()
    entry = PageEntry.from_dict(data)
    assert entry.section == "docs"
    assert entry.slug == "overview"
    assert entry.title == "Overview"


def test_page_entry_with_optional():
    """Test PageEntry with optional fields."""
    data = _minimal_page_entry_data()
    data["template_path"] = "specs/templates/docs/overview.md"
    data["template_variant"] = "standard"
    data["seo_keywords"] = ["aspose", "3d"]
    data["forbidden_topics"] = ["pricing"]
    data["token_mappings"] = {"__PRODUCT__": "Aspose.3D"}
    data["page_role"] = "workflow_page"
    data["content_strategy"] = {
        "primary_focus": "Overview of product",
        "claim_quota": {"min": 2, "max": 5},
    }

    entry = PageEntry.from_dict(data)
    assert entry.template_path == "specs/templates/docs/overview.md"
    assert entry.template_variant == "standard"
    assert entry.page_role == "workflow_page"
    assert entry.content_strategy.primary_focus == "Overview of product"
    assert entry.content_strategy.claim_quota.min_claims == 2


def test_page_entry_to_dict_deterministic():
    """Test PageEntry.to_dict sorts lists."""
    entry = PageEntry(
        section="docs",
        slug="test",
        output_path="content/test.md",
        url_path="/test/",
        title="Test",
        purpose="Test page",
        required_claim_ids=["c_002", "c_001"],
        required_snippet_tags=["z_tag", "a_tag"],
        cross_links=["https://z.example.org/", "https://a.example.org/"],
        seo_keywords=["zebra", "apple"],
    )
    data = entry.to_dict()
    assert data["required_claim_ids"] == ["c_001", "c_002"]
    assert data["required_snippet_tags"] == ["a_tag", "z_tag"]
    assert data["cross_links"] == ["https://a.example.org/", "https://z.example.org/"]
    assert data["seo_keywords"] == ["apple", "zebra"]


def test_page_entry_round_trip():
    """Test PageEntry round-trip."""
    data = _minimal_page_entry_data()
    original = PageEntry.from_dict(data)
    serialized = original.to_dict()
    restored = PageEntry.from_dict(serialized)
    assert restored.section == original.section
    assert restored.slug == original.slug
    assert restored.title == original.title
    assert restored.output_path == original.output_path


# ---------------------------------------------------------------------------
# PagePlan tests
# ---------------------------------------------------------------------------

def test_page_plan_minimal():
    """Test PagePlan with minimal required fields."""
    plan = PagePlan(
        schema_version="1.0",
        product_slug="aspose-3d",
        launch_tier="standard",
    )
    data = plan.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["product_slug"] == "aspose-3d"
    assert data["launch_tier"] == "standard"
    assert data["pages"] == []
    assert "launch_tier_adjustments" not in data
    assert "inferred_product_type" not in data


def test_page_plan_with_optional():
    """Test PagePlan with all optional fields."""
    plan = PagePlan(
        schema_version="1.0",
        product_slug="aspose-3d",
        launch_tier="rich",
        pages=[],
        launch_tier_adjustments=[
            LaunchTierAdjustment(adjustment="elevated", reason="Rich evidence"),
        ],
        inferred_product_type="sdk",
        evidence_volume={"claims": 50, "snippets": 20},
        effective_quotas={"docs": 10, "kb": 5},
    )
    data = plan.to_dict()
    assert len(data["launch_tier_adjustments"]) == 1
    assert data["inferred_product_type"] == "sdk"
    assert data["evidence_volume"]["claims"] == 50
    assert data["effective_quotas"]["docs"] == 10


def test_page_plan_from_dict():
    """Test PagePlan.from_dict with full data."""
    data = _minimal_page_plan_data()
    plan = PagePlan.from_dict(data)
    assert plan.product_slug == "aspose-3d"
    assert plan.launch_tier == "standard"
    assert len(plan.pages) == 1
    assert plan.pages[0].section == "docs"


def test_page_plan_round_trip():
    """Test PagePlan round-trip."""
    data = _minimal_page_plan_data()
    data["launch_tier_adjustments"] = [
        {"adjustment": "unchanged", "reason": "Default"},
    ]
    data["inferred_product_type"] = "library"
    data["evidence_volume"] = {"claims": 30}
    data["effective_quotas"] = {"docs": 8}

    original = PagePlan.from_dict(data)
    serialized = original.to_dict()
    restored = PagePlan.from_dict(serialized)
    assert restored.product_slug == original.product_slug
    assert restored.launch_tier == original.launch_tier
    assert len(restored.pages) == len(original.pages)
    assert restored.inferred_product_type == original.inferred_product_type
    assert len(restored.launch_tier_adjustments) == 1


def test_page_plan_validate_valid():
    """Test validate() on valid page plan."""
    data = _minimal_page_plan_data()
    plan = PagePlan.from_dict(data)
    assert plan.validate() is True


def test_page_plan_validate_invalid_tier():
    """Test validate() rejects invalid launch_tier."""
    plan = PagePlan(
        schema_version="1.0",
        product_slug="aspose-3d",
        launch_tier="invalid_tier",
    )
    with pytest.raises(ValueError, match="launch_tier"):
        plan.validate()


def test_page_plan_validate_empty_slug():
    """Test validate() rejects empty product_slug."""
    plan = PagePlan(
        schema_version="1.0",
        product_slug="",
        launch_tier="standard",
    )
    with pytest.raises(ValueError, match="product_slug"):
        plan.validate()


def test_page_plan_validate_invalid_section():
    """Test validate() rejects invalid page section."""
    plan = PagePlan(
        schema_version="1.0",
        product_slug="aspose-3d",
        launch_tier="standard",
        pages=[
            PageEntry(
                section="invalid_section",
                slug="test",
                output_path="test.md",
                url_path="/test/",
                title="Test",
                purpose="Test",
            ),
        ],
    )
    with pytest.raises(ValueError, match="section"):
        plan.validate()


def test_page_plan_validate_invalid_page_role():
    """Test validate() rejects invalid page_role."""
    plan = PagePlan(
        schema_version="1.0",
        product_slug="aspose-3d",
        launch_tier="standard",
        pages=[
            PageEntry(
                section="docs",
                slug="test",
                output_path="test.md",
                url_path="/test/",
                title="Test",
                purpose="Test",
                page_role="invalid_role",
            ),
        ],
    )
    with pytest.raises(ValueError, match="page_role"):
        plan.validate()


def test_page_plan_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_page_plan_data()
    plan = PagePlan.from_dict(data)
    json_str = plan.to_json()
    restored = PagePlan.from_json(json_str)
    assert restored.product_slug == plan.product_slug
    assert len(restored.pages) == len(plan.pages)

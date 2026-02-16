"""Tests for the Recipe System (Phase 6).

Validates:
- Recipe model serialization (to_dict/from_dict round-trip)
- Sub-model parsing: ClaimSpec, PageSpec, SectionSpec, SiteSpec, QualitySpec
- Recipe query methods: get_section, get_page, all_pages, section_names
- Recipe validation: missing fields, duplicates, bounds
- Registry integration: apply_llm_strategies, apply_site_config
- Loading: load_recipe from JSON, recipe_from_run_config
"""

import json
import pytest
from pathlib import Path

from launch.models.recipe import (
    ClaimSpec,
    PageSpec,
    SectionSpec,
    SiteSpec,
    QualitySpec,
    Recipe,
    load_recipe,
    recipe_from_run_config,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_recipe_dict():
    """A complete recipe dict matching the plan spec."""
    return {
        "name": "aspose-3d-python",
        "version": "1.0",
        "description": "Recipe for Aspose.3D Python documentation",
        "product": "aspose-3d",
        "platform": "python",
        "family": "3d",
        "site": {
            "domain": "aspose.org",
            "output_template": "content/{subdomain}/{family}/{locale}/{platform}/{section}/{slug}.md",
            "url_template": "https://{subdomain}/{family}/{platform}/{slug}/",
        },
        "sections": {
            "docs": {
                "pages": [
                    {
                        "role": "comprehensive_guide",
                        "slug": "overview",
                        "title": "Aspose.3D for Python Overview",
                        "claims": {"kinds": ["feature", "api"], "min": 10, "max": 25},
                        "tone": "technical",
                        "audience": "intermediate",
                    },
                    {
                        "role": "tutorial",
                        "slug": "getting-started",
                        "claims": {"kinds": ["workflow", "use_case"], "min": 5},
                        "tone": "tutorial-friendly",
                    },
                ],
                "max_pages": 10,
            },
            "kb": {
                "pages": [
                    {
                        "role": "faq",
                        "slug": "index",
                        "claims": {"kinds": ["faq", "troubleshooting"], "min": 10},
                    },
                    {
                        "role": "troubleshooting",
                        "slug": "common-issues",
                        "mandatory": False,
                    },
                ],
            },
        },
        "llm_strategies": {
            "w5.tutorial": {"temperature": 0.7, "model": "gemma3:27b"},
            "w5.faq": {"temperature": 0.3, "model": "recommended"},
        },
        "quality": {
            "min_content_quality": 4,
            "min_technical_accuracy": 4,
            "min_usability": 3,
            "max_review_rounds": 3,
            "review_enabled": True,
        },
    }


@pytest.fixture
def sample_recipe(sample_recipe_dict):
    return Recipe.from_dict(sample_recipe_dict)


# ── ClaimSpec Tests ───────────────────────────────────────────────────────


class TestClaimSpec:
    def test_default(self):
        cs = ClaimSpec()
        assert cs.kinds == []
        assert cs.min == 0
        assert cs.max == 0
        assert cs.groups == []

    def test_from_dict(self):
        cs = ClaimSpec.from_dict({"kinds": ["feature", "api"], "min": 5, "max": 25})
        assert cs.kinds == ["feature", "api"]
        assert cs.min == 5
        assert cs.max == 25

    def test_from_dict_non_dict(self):
        cs = ClaimSpec.from_dict("invalid")
        assert cs.kinds == []

    def test_to_dict(self):
        cs = ClaimSpec(kinds=["feature"], min=5, max=10)
        d = cs.to_dict()
        assert d["kinds"] == ["feature"]
        assert d["min"] == 5
        assert d["max"] == 10

    def test_to_dict_empty(self):
        cs = ClaimSpec()
        assert cs.to_dict() == {}

    def test_round_trip(self):
        original = ClaimSpec(kinds=["workflow", "api"], min=3, max=15, groups=["key_features"])
        d = original.to_dict()
        restored = ClaimSpec.from_dict(d)
        assert restored.kinds == sorted(original.kinds)
        assert restored.min == original.min
        assert restored.max == original.max


# ── PageSpec Tests ────────────────────────────────────────────────────────


class TestPageSpec:
    def test_default(self):
        ps = PageSpec(role="faq", slug="index")
        assert ps.role == "faq"
        assert ps.slug == "index"
        assert ps.mandatory is True
        assert ps.tone == ""
        assert ps.audience == ""

    def test_from_dict(self):
        ps = PageSpec.from_dict({
            "role": "tutorial",
            "slug": "getting-started",
            "title": "Getting Started",
            "tone": "tutorial-friendly",
            "audience": "beginner",
            "mandatory": False,
            "claims": {"kinds": ["workflow"], "min": 5},
        })
        assert ps.role == "tutorial"
        assert ps.slug == "getting-started"
        assert ps.title == "Getting Started"
        assert ps.tone == "tutorial-friendly"
        assert ps.audience == "beginner"
        assert ps.mandatory is False
        assert ps.claims is not None
        assert ps.claims.kinds == ["workflow"]

    def test_to_dict_minimal(self):
        ps = PageSpec(role="faq", slug="index")
        d = ps.to_dict()
        assert d == {"role": "faq", "slug": "index"}

    def test_to_dict_full(self):
        ps = PageSpec(
            role="tutorial", slug="guide",
            title="Guide", tone="technical", audience="advanced",
            mandatory=False, strategy_override="w5.custom",
        )
        d = ps.to_dict()
        assert d["title"] == "Guide"
        assert d["mandatory"] is False
        assert d["strategy_override"] == "w5.custom"

    def test_round_trip(self):
        original = PageSpec(
            role="faq", slug="index", title="FAQ",
            claims=ClaimSpec(kinds=["faq"], min=10),
            tone="technical",
        )
        d = original.to_dict()
        restored = PageSpec.from_dict(d)
        assert restored.role == original.role
        assert restored.slug == original.slug
        assert restored.title == original.title
        assert restored.claims is not None
        assert restored.claims.min == 10


# ── SectionSpec Tests ─────────────────────────────────────────────────────


class TestSectionSpec:
    def test_from_dict(self):
        data = {
            "pages": [
                {"role": "faq", "slug": "index"},
                {"role": "troubleshooting", "slug": "common-issues", "mandatory": False},
            ],
            "max_pages": 5,
        }
        ss = SectionSpec.from_dict("kb", data)
        assert ss.name == "kb"
        assert len(ss.pages) == 2
        assert ss.max_pages == 5

    def test_mandatory_pages(self):
        ss = SectionSpec(
            name="kb",
            pages=[
                PageSpec(role="faq", slug="index", mandatory=True),
                PageSpec(role="troubleshooting", slug="issues", mandatory=False),
            ],
        )
        assert len(ss.mandatory_pages) == 1
        assert ss.mandatory_pages[0].slug == "index"

    def test_optional_pages(self):
        ss = SectionSpec(
            name="kb",
            pages=[
                PageSpec(role="faq", slug="index", mandatory=True),
                PageSpec(role="troubleshooting", slug="issues", mandatory=False),
            ],
        )
        assert len(ss.optional_pages) == 1
        assert ss.optional_pages[0].slug == "issues"

    def test_get_page(self):
        ss = SectionSpec(
            name="docs",
            pages=[PageSpec(role="tutorial", slug="guide")],
        )
        assert ss.get_page("guide") is not None
        assert ss.get_page("nonexistent") is None

    def test_to_dict(self):
        ss = SectionSpec(
            name="docs",
            pages=[PageSpec(role="faq", slug="index")],
            max_pages=10,
            allow_optional=False,
        )
        d = ss.to_dict()
        assert len(d["pages"]) == 1
        assert d["max_pages"] == 10
        assert d["allow_optional"] is False


# ── SiteSpec Tests ────────────────────────────────────────────────────────


class TestSiteSpec:
    def test_default(self):
        ss = SiteSpec()
        assert ss.domain == ""
        assert ss.output_template == ""

    def test_from_dict(self):
        ss = SiteSpec.from_dict({
            "domain": "custom.org",
            "output_template": "out/{slug}.md",
        })
        assert ss.domain == "custom.org"
        assert ss.output_template == "out/{slug}.md"

    def test_from_dict_non_dict(self):
        ss = SiteSpec.from_dict(None)
        assert ss.domain == ""

    def test_apply_to_site_config(self):
        from launch.models.site_config import SiteConfig
        config = SiteConfig()
        spec = SiteSpec(
            domain="custom.org",
            output_template="custom/{slug}.md",
            subdomain_map={"docs": "docs.custom.org"},
        )
        spec.apply_to_site_config(config)
        assert config.domain == "custom.org"
        assert config.output_path_template == "custom/{slug}.md"
        assert config.subdomain_map["docs"] == "docs.custom.org"
        # Other subdomains preserved
        assert "products" in config.subdomain_map

    def test_to_dict_empty(self):
        assert SiteSpec().to_dict() == {}


# ── QualitySpec Tests ─────────────────────────────────────────────────────


class TestQualitySpec:
    def test_defaults(self):
        qs = QualitySpec()
        assert qs.min_content_quality == 4
        assert qs.min_technical_accuracy == 4
        assert qs.min_usability == 4
        assert qs.max_review_rounds == 3
        assert qs.review_enabled is True

    def test_from_dict(self):
        qs = QualitySpec.from_dict({"min_usability": 3, "max_review_rounds": 5})
        assert qs.min_usability == 3
        assert qs.max_review_rounds == 5
        # Other defaults preserved
        assert qs.min_content_quality == 4

    def test_from_dict_non_dict(self):
        qs = QualitySpec.from_dict("invalid")
        assert qs.min_content_quality == 4

    def test_to_dict(self):
        qs = QualitySpec(min_usability=3)
        d = qs.to_dict()
        assert d["min_usability"] == 3
        assert d["review_enabled"] is True


# ── Recipe Tests ──────────────────────────────────────────────────────────


class TestRecipe:
    def test_from_dict(self, sample_recipe):
        assert sample_recipe.name == "aspose-3d-python"
        assert sample_recipe.product == "aspose-3d"
        assert sample_recipe.platform == "python"
        assert sample_recipe.family == "3d"

    def test_section_names(self, sample_recipe):
        assert sample_recipe.section_names == ["docs", "kb"]

    def test_get_section(self, sample_recipe):
        docs = sample_recipe.get_section("docs")
        assert docs is not None
        assert docs.name == "docs"
        assert len(docs.pages) == 2
        assert docs.max_pages == 10

    def test_get_section_missing(self, sample_recipe):
        assert sample_recipe.get_section("nonexistent") is None

    def test_get_pages_for_section(self, sample_recipe):
        pages = sample_recipe.get_pages_for_section("docs")
        assert len(pages) == 2
        assert pages[0].role == "comprehensive_guide"
        assert pages[1].role == "tutorial"

    def test_get_pages_for_missing_section(self, sample_recipe):
        assert sample_recipe.get_pages_for_section("nonexistent") == []

    def test_get_page(self, sample_recipe):
        page = sample_recipe.get_page("docs", "overview")
        assert page is not None
        assert page.role == "comprehensive_guide"
        assert page.title == "Aspose.3D for Python Overview"

    def test_get_page_missing(self, sample_recipe):
        assert sample_recipe.get_page("docs", "nonexistent") is None
        assert sample_recipe.get_page("nonexistent", "overview") is None

    def test_all_pages(self, sample_recipe):
        all_pages = sample_recipe.all_pages
        assert len(all_pages) == 4  # 2 docs + 2 kb

    def test_all_page_roles(self, sample_recipe):
        roles = sample_recipe.all_page_roles
        assert "comprehensive_guide" in roles
        assert "tutorial" in roles
        assert "faq" in roles
        assert "troubleshooting" in roles

    def test_total_pages(self, sample_recipe):
        assert sample_recipe.total_pages == 4

    def test_quality(self, sample_recipe):
        assert sample_recipe.quality.min_content_quality == 4
        assert sample_recipe.quality.min_usability == 3
        assert sample_recipe.quality.review_enabled is True

    def test_llm_strategies(self, sample_recipe):
        assert "w5.tutorial" in sample_recipe.llm_strategies
        assert sample_recipe.llm_strategies["w5.tutorial"]["temperature"] == 0.7

    def test_site_config(self, sample_recipe):
        assert sample_recipe.site.domain == "aspose.org"

    def test_claims_on_page(self, sample_recipe):
        page = sample_recipe.get_page("docs", "overview")
        assert page.claims is not None
        assert page.claims.kinds == ["feature", "api"]
        assert page.claims.min == 10
        assert page.claims.max == 25

    def test_get_claim_spec(self, sample_recipe):
        cs = sample_recipe.get_claim_spec("docs", "overview")
        assert cs is not None
        assert cs.min == 10

    def test_get_claim_spec_missing(self, sample_recipe):
        assert sample_recipe.get_claim_spec("docs", "nonexistent") is None

    def test_round_trip(self, sample_recipe_dict):
        recipe = Recipe.from_dict(sample_recipe_dict)
        d = recipe.to_dict()
        # Verify key fields survive round-trip
        assert d["name"] == "aspose-3d-python"
        assert d["product"] == "aspose-3d"
        assert "docs" in d["sections"]
        assert len(d["sections"]["docs"]["pages"]) == 2
        assert "w5.tutorial" in d["llm_strategies"]
        assert d["quality"]["min_content_quality"] == 4


class TestRecipeValidation:
    def test_valid_recipe(self, sample_recipe):
        errors = sample_recipe.validate()
        assert errors == []

    def test_missing_role(self):
        recipe = Recipe.from_dict({
            "sections": {
                "docs": {
                    "pages": [{"slug": "overview"}],
                },
            },
        })
        errors = recipe.validate()
        assert any("missing 'role'" in e for e in errors)

    def test_missing_slug(self):
        recipe = Recipe.from_dict({
            "sections": {
                "docs": {
                    "pages": [{"role": "tutorial"}],
                },
            },
        })
        errors = recipe.validate()
        assert any("missing 'slug'" in e for e in errors)

    def test_duplicate_slugs(self):
        recipe = Recipe.from_dict({
            "sections": {
                "docs": {
                    "pages": [
                        {"role": "tutorial", "slug": "guide"},
                        {"role": "faq", "slug": "guide"},
                    ],
                },
            },
        })
        errors = recipe.validate()
        assert any("duplicate slug 'guide'" in e for e in errors)

    def test_quality_bounds(self):
        recipe = Recipe.from_dict({
            "quality": {"min_content_quality": 0, "min_usability": 6},
        })
        errors = recipe.validate()
        assert len(errors) == 2

    def test_quality_max_review_rounds(self):
        recipe = Recipe.from_dict({
            "quality": {"max_review_rounds": 0},
        })
        errors = recipe.validate()
        assert any("max_review_rounds" in e for e in errors)

    def test_invalid_strategy_key(self):
        recipe = Recipe.from_dict({
            "llm_strategies": {"no_dot": {"temperature": 0.5}},
        })
        errors = recipe.validate()
        assert any("worker.content_type" in e for e in errors)


class TestRecipeRegistryIntegration:
    def test_apply_llm_strategies(self, sample_recipe):
        from launch.llm.strategy import StrategyRegistry
        registry = StrategyRegistry()

        count = sample_recipe.apply_llm_strategies(registry)
        assert count == 2

        tutorial = registry.get("w5", "tutorial")
        assert tutorial.temperature == 0.7
        assert tutorial.model == "gemma3:27b"

    def test_apply_llm_strategies_empty(self):
        from launch.llm.strategy import StrategyRegistry
        recipe = Recipe()
        registry = StrategyRegistry()
        assert recipe.apply_llm_strategies(registry) == 0

    def test_apply_site_config(self, sample_recipe):
        from launch.models.site_config import SiteConfig
        config = SiteConfig()
        sample_recipe.apply_site_config(config)
        assert config.domain == "aspose.org"


# ── Loading Tests ─────────────────────────────────────────────────────────


class TestLoadRecipe:
    def test_load_from_json(self, tmp_path, sample_recipe_dict):
        path = tmp_path / "recipe.json"
        path.write_text(json.dumps(sample_recipe_dict), encoding="utf-8")

        recipe = load_recipe(path)
        assert recipe.name == "aspose-3d-python"
        assert recipe.total_pages == 4

    def test_load_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_recipe(tmp_path / "missing.json")

    def test_load_unsupported_format(self, tmp_path):
        path = tmp_path / "recipe.toml"
        path.write_text("key = value")
        with pytest.raises(ValueError, match="Unsupported"):
            load_recipe(path)

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "recipe.json"
        path.write_text("[1,2,3]")  # Array, not mapping
        with pytest.raises(ValueError, match="mapping"):
            load_recipe(path)


class TestRecipeFromRunConfig:
    def test_extracts_recipe(self, sample_recipe_dict):
        run_config = {"recipe": sample_recipe_dict, "other": "stuff"}
        recipe = recipe_from_run_config(run_config)
        assert recipe is not None
        assert recipe.name == "aspose-3d-python"

    def test_returns_none_when_missing(self):
        assert recipe_from_run_config({}) is None
        assert recipe_from_run_config({"recipe": "not_a_dict"}) is None


# ── Empty / Edge Cases ────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_recipe(self):
        recipe = Recipe.from_dict({})
        assert recipe.name == ""
        assert recipe.total_pages == 0
        assert recipe.section_names == []
        assert recipe.all_pages == []
        assert recipe.validate() == []

    def test_recipe_with_only_quality(self):
        recipe = Recipe.from_dict({"quality": {"review_enabled": False}})
        assert recipe.quality.review_enabled is False
        assert recipe.total_pages == 0

    def test_section_allow_optional_default(self):
        ss = SectionSpec.from_dict("docs", {"pages": []})
        assert ss.allow_optional is True

    def test_section_disallow_optional(self):
        ss = SectionSpec.from_dict("docs", {"pages": [], "allow_optional": False})
        assert ss.allow_optional is False

    def test_page_with_headings(self):
        ps = PageSpec.from_dict({
            "role": "tutorial", "slug": "guide",
            "headings": ["Introduction", "Prerequisites", "Steps"],
        })
        assert ps.headings == ["Introduction", "Prerequisites", "Steps"]
        d = ps.to_dict()
        assert "headings" in d

    def test_page_with_template_path(self):
        ps = PageSpec.from_dict({
            "role": "landing", "slug": "index",
            "template_path": "specs/templates/docs/3d/overview.md",
        })
        assert ps.template_path == "specs/templates/docs/3d/overview.md"

    def test_claim_spec_with_groups(self):
        cs = ClaimSpec.from_dict({"groups": ["key_features", "install_steps"]})
        assert "key_features" in cs.groups
        assert "install_steps" in cs.groups

"""Tests for ProductProfile model.

Validates:
- Serialization (to_dict/from_dict round-trip)
- from_product_facts() builder
- Inference helpers (category, audience, tone, complexity)
- Properties (has_rich_content, audience_label)
"""

import pytest
from launch.models.product_profile import (
    ProductProfile,
    _infer_category,
    _infer_audience,
    _infer_tone,
    _infer_complexity,
)


class TestProductProfileBasic:
    def test_default_values(self):
        p = ProductProfile(product_name="TestLib")
        assert p.product_name == "TestLib"
        assert p.product_family == ""
        assert p.content_tone == "technical"
        assert p.complexity_level == "intermediate"
        assert p.primary_audience == []
        assert p.claim_summary == {}
        assert p.maturity == "stable"

    def test_to_dict_round_trip(self):
        p = ProductProfile(
            product_name="Aspose.3D",
            product_family="3d",
            product_slug="aspose-3d",
            primary_audience=["Python developers", "3D artists"],
            key_differentiators=["Fast rendering", "Wide format support"],
            content_tone="tutorial-friendly",
            claim_summary={"feature": 25, "workflow": 8},
        )
        d = p.to_dict()
        p2 = ProductProfile.from_dict(d)

        assert p2.product_name == "Aspose.3D"
        assert p2.product_family == "3d"
        assert p2.content_tone == "tutorial-friendly"
        assert p2.claim_summary == {"feature": 25, "workflow": 8}

    def test_to_dict_sorted_determinism(self):
        p = ProductProfile(
            product_name="Test",
            primary_audience=["Z users", "A users"],
            supported_platforms=["java", "python"],
            claim_summary={"workflow": 3, "feature": 10},
        )
        d = p.to_dict()
        assert d["primary_audience"] == ["A users", "Z users"]
        assert d["supported_platforms"] == ["java", "python"]
        assert list(d["claim_summary"].keys()) == ["feature", "workflow"]

    def test_from_dict_defaults(self):
        p = ProductProfile.from_dict({"product_name": "X"})
        assert p.product_name == "X"
        assert p.content_tone == "technical"
        assert p.complexity_level == "intermediate"


class TestFromProductFacts:
    def test_basic_construction(self):
        product_facts = {
            "product_name": "Aspose.3D",
            "product_family": "3d",
            "product_slug": "aspose-3d",
            "claims": [
                {"claim_id": "c1", "claim_text": "Fast rendering", "claim_kind": "feature"},
                {"claim_id": "c2", "claim_text": "FBX support", "claim_kind": "feature"},
            ],
            "claim_groups": {
                "key_features": ["c1", "c2"],
            },
        }
        p = ProductProfile.from_product_facts(product_facts)
        assert p.product_name == "Aspose.3D"
        assert p.product_family == "3d"
        assert p.claim_summary["feature"] == 2
        assert len(p.key_differentiators) == 2

    def test_uses_enriched_text(self):
        product_facts = {
            "product_name": "TestLib",
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "raw text",
                    "enriched_text": "Marketing-ready text",
                    "claim_kind": "feature",
                },
            ],
            "claim_groups": {"key_features": ["c1"]},
        }
        p = ProductProfile.from_product_facts(product_facts)
        assert p.key_differentiators == ["Marketing-ready text"]

    def test_with_code_analysis(self):
        product_facts = {
            "product_name": "TestLib",
            "claims": [],
            "claim_groups": {},
        }
        code_analysis = {
            "positioning": {
                "short_description": "A powerful testing library.",
            }
        }
        p = ProductProfile.from_product_facts(product_facts, code_analysis=code_analysis)
        assert p.short_description == "A powerful testing library."

    def test_with_run_config(self):
        product_facts = {
            "product_name": "TestLib",
            "product_family": "",
            "claims": [],
            "claim_groups": {},
        }
        run_config = {
            "family": "test",
            "target_platform": "python",
        }
        p = ProductProfile.from_product_facts(product_facts, run_config=run_config)
        assert p.product_family == "test"
        assert "python" in p.supported_platforms


class TestInferCategory:
    def test_known_families(self):
        assert "3D" in _infer_category("3d", {})
        assert "spreadsheet" in _infer_category("cells", {})
        assert "document" in _infer_category("words", {})
        assert "notebook" in _infer_category("note", {})

    def test_unknown_family_with_description(self):
        result = _infer_category("custom", {"product_description": "An SDK for testing"})
        assert "development kit" in result

    def test_unknown_family_fallback(self):
        result = _infer_category("unknown", {})
        assert "library" in result


class TestInferAudience:
    def test_from_target_audience(self):
        result = _infer_audience({"target_audience": "Python developers"})
        assert "Python developers" in result

    def test_from_who_it_is_for(self):
        result = _infer_audience({"who_it_is_for": "data scientists"})
        assert "data scientists" in result

    def test_default_audience(self):
        result = _infer_audience({})
        assert "software developers" in result


class TestInferTone:
    def test_explicit_config(self):
        assert _infer_tone({}, {"content_tone": "marketing"}) == "marketing"

    def test_tutorial_heavy(self):
        pf = {"claim_groups": {"tutorials": list(range(8)), "workflow_claims": list(range(5))}}
        assert _infer_tone(pf, {}) == "tutorial-friendly"

    def test_default_technical(self):
        assert _infer_tone({}, {}) == "technical"


class TestInferComplexity:
    def test_from_enrichment(self):
        claims = [
            {"audience_level": "beginner"},
            {"audience_level": "beginner"},
            {"audience_level": "intermediate"},
        ]
        assert _infer_complexity({"claims": claims}) == "beginner"

    def test_default(self):
        assert _infer_complexity({}) == "intermediate"
        assert _infer_complexity({"claims": []}) == "intermediate"


class TestProperties:
    def test_has_rich_content_true(self):
        p = ProductProfile(
            product_name="Test",
            claim_summary={"feature": 10, "workflow": 5},
            key_differentiators=["A", "B"],
        )
        assert p.has_rich_content is True

    def test_has_rich_content_false_few_claims(self):
        p = ProductProfile(
            product_name="Test",
            claim_summary={"feature": 3},
            key_differentiators=["A", "B"],
        )
        assert p.has_rich_content is False

    def test_has_rich_content_false_few_differentiators(self):
        p = ProductProfile(
            product_name="Test",
            claim_summary={"feature": 20},
            key_differentiators=["A"],
        )
        assert p.has_rich_content is False

    def test_audience_label(self):
        p = ProductProfile(product_name="Test", primary_audience=["devs", "testers"])
        assert p.audience_label == "devs, testers"

    def test_audience_label_default(self):
        p = ProductProfile(product_name="Test")
        assert p.audience_label == "software developers"

    def test_json_round_trip(self):
        p = ProductProfile(
            product_name="Test",
            claim_summary={"feature": 5},
        )
        json_str = p.to_json()
        p2 = ProductProfile.from_json(json_str)
        assert p2.product_name == "Test"
        assert p2.claim_summary == {"feature": 5}

"""Tests for Ruleset model.

Validates:
- Ruleset serialization (to_dict/from_dict)
- Round-trip consistency
- Sub-component models (StyleRules, TruthRules, EditingRules, etc.)
- YAML loading
- Validation logic
- Family overrides

TC-1030: Typed Artifact Models -- Foundation
"""

import pytest
import tempfile
from pathlib import Path

from src.launch.models.ruleset import (
    ClaimsRules,
    EditingRules,
    FamilyOverride,
    HugoRules,
    LimitsBySection,
    MandatoryPage,
    OptionalPagePolicy,
    Ruleset,
    SectionConfig,
    SectionOverride,
    StyleBySection,
    StyleRules,
    TruthRules,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_style() -> StyleRules:
    return StyleRules(tone="technical", audience="developers", forbid_marketing_superlatives=True)


def _minimal_truth() -> TruthRules:
    return TruthRules(no_uncited_facts=True, forbid_inferred_formats=True)


def _minimal_editing() -> EditingRules:
    return EditingRules(diff_only=True, forbid_full_rewrite_existing_files=True)


def _minimal_section(min_pages: int = 1) -> SectionConfig:
    return SectionConfig(min_pages=min_pages)


def _minimal_sections() -> dict:
    return {
        "products": _minimal_section(1),
        "docs": _minimal_section(5),
        "reference": _minimal_section(1),
        "kb": _minimal_section(4),
        "blog": _minimal_section(1),
    }


def _minimal_ruleset_data() -> dict:
    return {
        "schema_version": "1.0",
        "style": {"tone": "technical", "audience": "developers", "forbid_marketing_superlatives": True},
        "truth": {"no_uncited_facts": True, "forbid_inferred_formats": True},
        "editing": {"diff_only": True, "forbid_full_rewrite_existing_files": True},
        "sections": {
            "products": {"min_pages": 1},
            "docs": {"min_pages": 5},
            "reference": {"min_pages": 1},
            "kb": {"min_pages": 4},
            "blog": {"min_pages": 1},
        },
    }


# ---------------------------------------------------------------------------
# StyleRules tests
# ---------------------------------------------------------------------------

def test_style_rules_minimal():
    """Test StyleRules with required fields."""
    style = _minimal_style()
    data = style.to_dict()
    assert data["tone"] == "technical"
    assert data["audience"] == "developers"
    assert data["forbid_marketing_superlatives"] is True
    assert "forbid_em_dash" not in data
    assert "forbid_weasel_words" not in data


def test_style_rules_full():
    """Test StyleRules with all fields."""
    style = StyleRules(
        tone="technical",
        audience="developers",
        forbid_marketing_superlatives=True,
        forbid_em_dash=True,
        prefer_short_sentences=True,
        forbid_weasel_words=["best", "seamless", "ultimate"],
    )
    data = style.to_dict()
    assert data["forbid_em_dash"] is True
    assert data["prefer_short_sentences"] is True
    assert data["forbid_weasel_words"] == ["best", "seamless", "ultimate"]  # sorted


def test_style_rules_round_trip():
    """Test StyleRules round-trip."""
    original = StyleRules(
        tone="instructional",
        audience="beginners",
        forbid_marketing_superlatives=False,
        forbid_weasel_words=["revolutionary", "best"],
    )
    data = original.to_dict()
    restored = StyleRules.from_dict(data)
    assert restored.tone == original.tone
    assert restored.audience == original.audience
    assert sorted(restored.forbid_weasel_words) == sorted(original.forbid_weasel_words)


# ---------------------------------------------------------------------------
# TruthRules tests
# ---------------------------------------------------------------------------

def test_truth_rules_minimal():
    """Test TruthRules with required fields."""
    truth = _minimal_truth()
    data = truth.to_dict()
    assert data["no_uncited_facts"] is True
    assert data["forbid_inferred_formats"] is True
    assert "allow_external_citations" not in data


def test_truth_rules_full():
    """Test TruthRules with all fields."""
    truth = TruthRules(
        no_uncited_facts=True,
        forbid_inferred_formats=True,
        allow_external_citations=False,
        allow_inference=False,
    )
    data = truth.to_dict()
    assert data["allow_external_citations"] is False
    assert data["allow_inference"] is False


# ---------------------------------------------------------------------------
# EditingRules tests
# ---------------------------------------------------------------------------

def test_editing_rules_minimal():
    """Test EditingRules with required fields."""
    editing = _minimal_editing()
    data = editing.to_dict()
    assert data["diff_only"] is True
    assert data["forbid_full_rewrite_existing_files"] is True
    assert "forbid_deleting_existing_files" not in data


def test_editing_rules_full():
    """Test EditingRules with all fields."""
    editing = EditingRules(
        diff_only=True,
        forbid_full_rewrite_existing_files=True,
        forbid_deleting_existing_files=True,
    )
    data = editing.to_dict()
    assert data["forbid_deleting_existing_files"] is True


# ---------------------------------------------------------------------------
# SectionConfig tests
# ---------------------------------------------------------------------------

def test_section_config_minimal():
    """Test SectionConfig with min_pages only."""
    section = SectionConfig(min_pages=5)
    data = section.to_dict()
    assert data["min_pages"] == 5
    assert "max_pages" not in data
    assert "style_by_section" not in data
    assert "mandatory_pages" not in data
    assert "optional_page_policies" not in data


def test_section_config_full():
    """Test SectionConfig with all fields."""
    section = SectionConfig(
        min_pages=5,
        max_pages=10,
        style_by_section=StyleBySection(tone="instructional", voice="direct"),
        limits_by_section=LimitsBySection(max_words=3000, max_headings=10),
        mandatory_pages=[
            MandatoryPage(slug="_index", page_role="toc"),
            MandatoryPage(slug="overview", page_role="landing"),
        ],
        optional_page_policies=[
            OptionalPagePolicy(page_role="workflow_page", source="per_feature", priority=1),
        ],
    )
    data = section.to_dict()
    assert data["min_pages"] == 5
    assert data["max_pages"] == 10
    assert data["style_by_section"]["tone"] == "instructional"
    assert data["limits_by_section"]["max_words"] == 3000
    assert len(data["mandatory_pages"]) == 2
    assert len(data["optional_page_policies"]) == 1


def test_section_config_round_trip():
    """Test SectionConfig round-trip."""
    original = SectionConfig(
        min_pages=3,
        max_pages=8,
        mandatory_pages=[MandatoryPage(slug="faq", page_role="troubleshooting")],
    )
    data = original.to_dict()
    restored = SectionConfig.from_dict(data)
    assert restored.min_pages == original.min_pages
    assert restored.max_pages == original.max_pages
    assert len(restored.mandatory_pages) == 1
    assert restored.mandatory_pages[0].slug == "faq"


# ---------------------------------------------------------------------------
# HugoRules / ClaimsRules tests
# ---------------------------------------------------------------------------

def test_hugo_rules():
    """Test HugoRules serialization."""
    hugo = HugoRules(
        allow_shortcodes=["note", "tabs", "code"],
        forbid_raw_html_except_claim_markers=True,
    )
    data = hugo.to_dict()
    assert data["allow_shortcodes"] == ["code", "note", "tabs"]  # sorted
    assert data["forbid_raw_html_except_claim_markers"] is True


def test_claims_rules():
    """Test ClaimsRules serialization."""
    claims = ClaimsRules(
        marker_style="html_comment",
        html_comment_prefix="claim_id:",
        remove_markers_on_publish=False,
    )
    data = claims.to_dict()
    assert data["marker_style"] == "html_comment"
    assert data["html_comment_prefix"] == "claim_id:"
    assert data["remove_markers_on_publish"] is False


# ---------------------------------------------------------------------------
# Family overrides tests
# ---------------------------------------------------------------------------

def test_family_override():
    """Test FamilyOverride serialization."""
    override = FamilyOverride(
        sections={
            "docs": SectionOverride(
                mandatory_pages=[
                    MandatoryPage(slug="model-loading", page_role="workflow_page"),
                ],
            ),
        }
    )
    data = override.to_dict()
    assert "sections" in data
    assert "docs" in data["sections"]
    assert len(data["sections"]["docs"]["mandatory_pages"]) == 1


def test_family_override_round_trip():
    """Test FamilyOverride round-trip."""
    original = FamilyOverride(
        sections={
            "docs": SectionOverride(
                mandatory_pages=[MandatoryPage(slug="rendering", page_role="workflow_page")],
            ),
        }
    )
    data = original.to_dict()
    restored = FamilyOverride.from_dict(data)
    assert "docs" in restored.sections
    assert len(restored.sections["docs"].mandatory_pages) == 1
    assert restored.sections["docs"].mandatory_pages[0].slug == "rendering"


# ---------------------------------------------------------------------------
# Ruleset tests
# ---------------------------------------------------------------------------

def test_ruleset_minimal():
    """Test Ruleset with minimal required fields."""
    data = _minimal_ruleset_data()
    ruleset = Ruleset.from_dict(data)
    assert ruleset.schema_version == "1.0"
    assert ruleset.style.tone == "technical"
    assert ruleset.truth.no_uncited_facts is True
    assert ruleset.editing.diff_only is True
    assert ruleset.sections["docs"].min_pages == 5
    assert ruleset.hugo is None
    assert ruleset.claims is None
    assert ruleset.family_overrides is None


def test_ruleset_full():
    """Test Ruleset with all fields."""
    data = _minimal_ruleset_data()
    data["hugo"] = {"allow_shortcodes": ["note"], "forbid_raw_html_except_claim_markers": True}
    data["claims"] = {"marker_style": "html_comment", "html_comment_prefix": "claim_id:"}
    data["family_overrides"] = {
        "3d": {
            "sections": {
                "docs": {
                    "mandatory_pages": [{"slug": "model-loading", "page_role": "workflow_page"}],
                },
            },
        },
    }

    ruleset = Ruleset.from_dict(data)
    assert ruleset.hugo is not None
    assert ruleset.hugo.allow_shortcodes == ["note"]
    assert ruleset.claims is not None
    assert ruleset.claims.marker_style == "html_comment"
    assert ruleset.family_overrides is not None
    assert "3d" in ruleset.family_overrides


def test_ruleset_round_trip():
    """Test Ruleset serialization round-trip."""
    data = _minimal_ruleset_data()
    data["hugo"] = {"allow_shortcodes": ["note", "tabs"]}
    data["claims"] = {"marker_style": "html_comment"}
    data["sections"]["docs"]["mandatory_pages"] = [
        {"slug": "_index", "page_role": "toc"},
        {"slug": "overview", "page_role": "landing"},
    ]

    original = Ruleset.from_dict(data)
    serialized = original.to_dict()
    restored = Ruleset.from_dict(serialized)

    assert restored.style.tone == original.style.tone
    assert restored.truth.no_uncited_facts == original.truth.no_uncited_facts
    assert restored.editing.diff_only == original.editing.diff_only
    assert restored.sections["docs"].min_pages == original.sections["docs"].min_pages
    assert len(restored.sections["docs"].mandatory_pages) == 2
    assert restored.hugo.allow_shortcodes == sorted(original.hugo.allow_shortcodes)


def test_ruleset_validate_valid():
    """Test validate() on valid Ruleset."""
    ruleset = Ruleset(
        schema_version="1.0",
        style=_minimal_style(),
        truth=_minimal_truth(),
        editing=_minimal_editing(),
        sections=_minimal_sections(),
    )
    assert ruleset.validate() is True


def test_ruleset_validate_missing_section():
    """Test validate() rejects missing required sections."""
    sections = _minimal_sections()
    del sections["blog"]
    ruleset = Ruleset(
        schema_version="1.0",
        style=_minimal_style(),
        truth=_minimal_truth(),
        editing=_minimal_editing(),
        sections=sections,
    )
    with pytest.raises(ValueError, match="Missing required sections"):
        ruleset.validate()


def test_ruleset_validate_negative_min_pages():
    """Test validate() rejects negative min_pages."""
    sections = _minimal_sections()
    sections["docs"] = SectionConfig(min_pages=-1)
    ruleset = Ruleset(
        schema_version="1.0",
        style=_minimal_style(),
        truth=_minimal_truth(),
        editing=_minimal_editing(),
        sections=sections,
    )
    with pytest.raises(ValueError, match="min_pages"):
        ruleset.validate()


def test_ruleset_validate_invalid_marker_style():
    """Test validate() rejects invalid claims.marker_style."""
    ruleset = Ruleset(
        schema_version="1.0",
        style=_minimal_style(),
        truth=_minimal_truth(),
        editing=_minimal_editing(),
        sections=_minimal_sections(),
        claims=ClaimsRules(marker_style="xml_attribute"),  # Invalid
    )
    with pytest.raises(ValueError, match="marker_style"):
        ruleset.validate()


def test_ruleset_load_from_yaml():
    """Test load_from_yaml with actual ruleset file."""
    # Use the actual ruleset.v1.yaml from the repo
    repo_root = Path(__file__).parent.parent.parent.parent
    ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1.yaml"

    if not ruleset_path.exists():
        pytest.skip("ruleset.v1.yaml not found")

    ruleset = Ruleset.load_from_yaml(ruleset_path)
    assert ruleset.schema_version == "1.0"
    assert ruleset.style.tone == "technical"
    assert ruleset.truth.no_uncited_facts is True
    assert ruleset.editing.diff_only is True
    assert "docs" in ruleset.sections
    assert "products" in ruleset.sections
    assert ruleset.sections["docs"].min_pages == 5
    assert ruleset.validate() is True


def test_ruleset_load_from_yaml_round_trip():
    """Test load_from_yaml produces same result after to_dict/from_dict."""
    repo_root = Path(__file__).parent.parent.parent.parent
    ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1.yaml"

    if not ruleset_path.exists():
        pytest.skip("ruleset.v1.yaml not found")

    original = Ruleset.load_from_yaml(ruleset_path)
    serialized = original.to_dict()
    restored = Ruleset.from_dict(serialized)

    assert restored.style.tone == original.style.tone
    assert restored.truth.no_uncited_facts == original.truth.no_uncited_facts
    assert restored.sections["docs"].min_pages == original.sections["docs"].min_pages

    # Verify family overrides are preserved
    if original.family_overrides:
        assert restored.family_overrides is not None
        for family_name in original.family_overrides:
            assert family_name in restored.family_overrides


def test_ruleset_load_from_yaml_missing_file():
    """Test load_from_yaml raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        Ruleset.load_from_yaml(Path("/nonexistent/ruleset.yaml"))


def test_ruleset_load_from_yaml_invalid_content():
    """Test load_from_yaml raises ValueError for invalid YAML content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("just a string, not a mapping")
        f.flush()
        with pytest.raises(ValueError, match="must be a mapping"):
            Ruleset.load_from_yaml(Path(f.name))


def test_ruleset_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_ruleset_data()
    ruleset = Ruleset.from_dict(data)
    json_str = ruleset.to_json()
    restored = Ruleset.from_json(json_str)
    assert restored.style.tone == ruleset.style.tone
    assert restored.sections["docs"].min_pages == ruleset.sections["docs"].min_pages


def test_ruleset_deterministic_serialization():
    """Test that to_dict produces deterministic output."""
    data = _minimal_ruleset_data()
    data["style"]["forbid_weasel_words"] = ["ultimate", "best", "seamless"]
    data["hugo"] = {"allow_shortcodes": ["tabs", "note", "code"]}

    ruleset = Ruleset.from_dict(data)
    dict1 = ruleset.to_dict()
    dict2 = ruleset.to_dict()

    # Verify exact equality
    assert dict1 == dict2

    # Verify sorting
    assert dict1["style"]["forbid_weasel_words"] == ["best", "seamless", "ultimate"]
    assert dict1["hugo"]["allow_shortcodes"] == ["code", "note", "tabs"]
    assert list(dict1["sections"].keys()) == ["blog", "docs", "kb", "products", "reference"]

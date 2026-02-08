"""Tests for FrontmatterContract model.

Validates:
- FrontmatterContract serialization (to_dict/from_dict)
- Round-trip consistency
- SectionContract sub-model
- Validation logic

TC-1030: Typed Artifact Models -- Foundation
"""

import pytest

from src.launch.models.frontmatter import FrontmatterContract, SectionContract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_section() -> SectionContract:
    """Create a minimal SectionContract for testing."""
    return SectionContract(
        sample_size=10,
        required_keys=["title", "description"],
        optional_keys=["draft", "tags"],
        key_types={"title": "string", "description": "string", "draft": "boolean", "tags": "array_string"},
    )


def _minimal_sections() -> dict:
    """Create minimal sections dict for testing."""
    section = _minimal_section()
    return {
        "products": section,
        "docs": section,
        "reference": section,
        "kb": section,
        "blog": section,
    }


def _minimal_frontmatter_data() -> dict:
    """Create minimal FrontmatterContract dict for testing."""
    section_data = {
        "sample_size": 10,
        "required_keys": ["title", "description"],
        "optional_keys": ["draft", "tags"],
        "key_types": {"title": "string", "description": "string", "draft": "boolean", "tags": "array_string"},
    }
    return {
        "schema_version": "1.0",
        "site_repo_url": "https://github.com/test/site",
        "site_sha": "a" * 40,
        "sections": {
            "products": section_data,
            "docs": section_data,
            "reference": section_data,
            "kb": section_data,
            "blog": section_data,
        },
    }


# ---------------------------------------------------------------------------
# SectionContract tests
# ---------------------------------------------------------------------------

def test_section_contract_minimal():
    """Test SectionContract serialization."""
    section = _minimal_section()
    data = section.to_dict()
    assert data["sample_size"] == 10
    assert data["required_keys"] == ["description", "title"]  # sorted
    assert data["optional_keys"] == ["draft", "tags"]  # sorted
    assert "default_values" not in data


def test_section_contract_with_defaults():
    """Test SectionContract with default_values."""
    section = SectionContract(
        sample_size=5,
        required_keys=["title"],
        optional_keys=["weight"],
        key_types={"title": "string", "weight": "integer"},
        default_values={"weight": 0, "draft": False},
    )
    data = section.to_dict()
    assert "default_values" in data
    assert data["default_values"]["weight"] == 0


def test_section_contract_round_trip():
    """Test SectionContract round-trip."""
    original = SectionContract(
        sample_size=15,
        required_keys=["title", "weight", "description"],
        optional_keys=["tags", "categories"],
        key_types={"title": "string", "weight": "integer", "description": "string"},
        default_values={"weight": 10},
    )
    data = original.to_dict()
    restored = SectionContract.from_dict(data)
    assert restored.sample_size == original.sample_size
    assert sorted(restored.required_keys) == sorted(original.required_keys)
    assert sorted(restored.optional_keys) == sorted(original.optional_keys)
    assert restored.default_values == original.default_values


def test_section_contract_sorted_key_types():
    """Test that key_types are sorted deterministically."""
    section = SectionContract(
        sample_size=1,
        required_keys=[],
        optional_keys=[],
        key_types={"z_field": "string", "a_field": "integer", "m_field": "boolean"},
    )
    data = section.to_dict()
    keys = list(data["key_types"].keys())
    assert keys == ["a_field", "m_field", "z_field"]


# ---------------------------------------------------------------------------
# FrontmatterContract tests
# ---------------------------------------------------------------------------

def test_frontmatter_contract_minimal():
    """Test FrontmatterContract with minimal data."""
    data = _minimal_frontmatter_data()
    contract = FrontmatterContract.from_dict(data)
    assert contract.schema_version == "1.0"
    assert contract.site_repo_url == "https://github.com/test/site"
    assert contract.site_sha == "a" * 40
    assert set(contract.sections.keys()) == {"products", "docs", "reference", "kb", "blog"}


def test_frontmatter_contract_round_trip():
    """Test FrontmatterContract serialization round-trip."""
    data = _minimal_frontmatter_data()
    original = FrontmatterContract.from_dict(data)
    serialized = original.to_dict()
    restored = FrontmatterContract.from_dict(serialized)

    assert restored.site_repo_url == original.site_repo_url
    assert restored.site_sha == original.site_sha
    assert set(restored.sections.keys()) == set(original.sections.keys())
    for name in restored.sections:
        assert restored.sections[name].sample_size == original.sections[name].sample_size


def test_frontmatter_contract_validate_valid():
    """Test validate() on valid FrontmatterContract."""
    contract = FrontmatterContract(
        schema_version="1.0",
        site_repo_url="https://github.com/test/site",
        site_sha="a" * 40,
        sections=_minimal_sections(),
    )
    assert contract.validate() is True


def test_frontmatter_contract_validate_missing_section():
    """Test validate() rejects missing required sections."""
    sections = _minimal_sections()
    del sections["blog"]  # Remove required section
    contract = FrontmatterContract(
        schema_version="1.0",
        site_repo_url="https://github.com/test/site",
        site_sha="a" * 40,
        sections=sections,
    )
    with pytest.raises(ValueError, match="Missing required sections"):
        contract.validate()


def test_frontmatter_contract_validate_empty_url():
    """Test validate() rejects empty site_repo_url."""
    contract = FrontmatterContract(
        schema_version="1.0",
        site_repo_url="",
        site_sha="a" * 40,
        sections=_minimal_sections(),
    )
    with pytest.raises(ValueError, match="site_repo_url"):
        contract.validate()


def test_frontmatter_contract_validate_invalid_key_type():
    """Test validate() rejects invalid key types."""
    sections = _minimal_sections()
    sections["docs"] = SectionContract(
        sample_size=5,
        required_keys=["title"],
        optional_keys=[],
        key_types={"title": "invalid_type"},
    )
    contract = FrontmatterContract(
        schema_version="1.0",
        site_repo_url="https://github.com/test/site",
        site_sha="a" * 40,
        sections=sections,
    )
    with pytest.raises(ValueError, match="invalid type"):
        contract.validate()


def test_frontmatter_contract_validate_bad_sample_size():
    """Test validate() rejects sample_size < 1."""
    sections = _minimal_sections()
    sections["products"] = SectionContract(
        sample_size=0,
        required_keys=["title"],
        optional_keys=[],
        key_types={"title": "string"},
    )
    contract = FrontmatterContract(
        schema_version="1.0",
        site_repo_url="https://github.com/test/site",
        site_sha="a" * 40,
        sections=sections,
    )
    with pytest.raises(ValueError, match="sample_size"):
        contract.validate()


def test_frontmatter_contract_json_round_trip():
    """Test JSON serialization round-trip."""
    data = _minimal_frontmatter_data()
    contract = FrontmatterContract.from_dict(data)
    json_str = contract.to_json()
    restored = FrontmatterContract.from_json(json_str)
    assert restored.site_repo_url == contract.site_repo_url
    assert set(restored.sections.keys()) == set(contract.sections.keys())

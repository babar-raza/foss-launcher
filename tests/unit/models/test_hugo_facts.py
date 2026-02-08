"""Tests for HugoFacts model.

Validates:
- HugoFacts serialization (to_dict/from_dict)
- Round-trip consistency
- Deterministic sorting
- Validation logic

TC-1030: Typed Artifact Models -- Foundation
"""

import pytest

from src.launch.models.hugo_facts import HugoFacts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_hugo_facts_data() -> dict:
    """Create minimal HugoFacts dict for testing."""
    return {
        "schema_version": "1.0",
        "languages": ["en"],
        "default_language": "en",
        "default_language_in_subdir": False,
        "permalinks": {},
        "outputs": {},
        "taxonomies": {},
        "source_files": ["config.toml"],
    }


# ---------------------------------------------------------------------------
# HugoFacts tests
# ---------------------------------------------------------------------------

def test_hugo_facts_minimal():
    """Test HugoFacts with minimal required fields."""
    facts = HugoFacts(
        schema_version="1.0",
        languages=["en"],
        default_language="en",
        default_language_in_subdir=False,
        permalinks={},
        outputs={},
        taxonomies={},
        source_files=["config.toml"],
    )
    data = facts.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["languages"] == ["en"]
    assert data["default_language"] == "en"
    assert data["default_language_in_subdir"] is False
    assert data["permalinks"] == {}
    assert data["outputs"] == {}
    assert data["taxonomies"] == {}
    assert data["source_files"] == ["config.toml"]


def test_hugo_facts_full():
    """Test HugoFacts with all fields populated."""
    facts = HugoFacts(
        schema_version="1.0",
        languages=["en", "fr", "de"],
        default_language="en",
        default_language_in_subdir=True,
        permalinks={"posts": "/:year/:month/:title/"},
        outputs={"home": ["HTML", "RSS"], "section": ["HTML"]},
        taxonomies={"tag": "tags", "category": "categories"},
        source_files=["config/_default/config.toml", "config/_default/languages.toml"],
    )
    data = facts.to_dict()
    assert data["languages"] == ["de", "en", "fr"]  # sorted
    assert data["default_language_in_subdir"] is True
    assert data["permalinks"]["posts"] == "/:year/:month/:title/"
    assert data["outputs"]["home"] == ["HTML", "RSS"]  # sorted
    assert data["taxonomies"]["tag"] == "tags"


def test_hugo_facts_from_dict():
    """Test HugoFacts.from_dict."""
    data = _minimal_hugo_facts_data()
    data["languages"] = ["en", "fr"]
    data["permalinks"] = {"blog": "/:slug/"}
    data["taxonomies"] = {"tag": "tags"}
    data["outputs"] = {"page": ["HTML"]}

    facts = HugoFacts.from_dict(data)
    assert facts.languages == ["en", "fr"]
    assert facts.default_language == "en"
    assert facts.permalinks == {"blog": "/:slug/"}
    assert facts.taxonomies == {"tag": "tags"}


def test_hugo_facts_round_trip():
    """Test HugoFacts serialization round-trip."""
    data = {
        "schema_version": "1.0",
        "languages": ["en", "fr", "de"],
        "default_language": "en",
        "default_language_in_subdir": True,
        "permalinks": {"posts": "/:year/:title/", "docs": "/:title/"},
        "outputs": {"home": ["HTML", "RSS", "JSON"], "section": ["HTML"]},
        "taxonomies": {"tag": "tags", "category": "categories"},
        "source_files": ["config.toml", "languages.toml"],
    }
    original = HugoFacts.from_dict(data)
    serialized = original.to_dict()
    restored = HugoFacts.from_dict(serialized)

    assert sorted(restored.languages) == sorted(original.languages)
    assert restored.default_language == original.default_language
    assert restored.default_language_in_subdir == original.default_language_in_subdir
    assert restored.permalinks == original.permalinks
    assert restored.taxonomies == original.taxonomies
    assert sorted(restored.source_files) == sorted(original.source_files)


def test_hugo_facts_deterministic_sorting():
    """Test that outputs and taxonomies are sorted deterministically."""
    facts = HugoFacts(
        schema_version="1.0",
        languages=["fr", "en", "de"],
        default_language="en",
        default_language_in_subdir=False,
        permalinks={"z_section": "/z/", "a_section": "/a/"},
        outputs={"z_kind": ["RSS", "HTML"], "a_kind": ["JSON", "HTML"]},
        taxonomies={"z_tax": "z_taxes", "a_tax": "a_taxes"},
        source_files=["z.toml", "a.toml"],
    )
    data = facts.to_dict()

    # Languages sorted
    assert data["languages"] == ["de", "en", "fr"]

    # Permalinks sorted by key
    assert list(data["permalinks"].keys()) == ["a_section", "z_section"]

    # Outputs sorted by key, values sorted
    assert list(data["outputs"].keys()) == ["a_kind", "z_kind"]
    assert data["outputs"]["z_kind"] == ["HTML", "RSS"]
    assert data["outputs"]["a_kind"] == ["HTML", "JSON"]

    # Taxonomies sorted by key
    assert list(data["taxonomies"].keys()) == ["a_tax", "z_tax"]

    # Source files sorted
    assert data["source_files"] == ["a.toml", "z.toml"]


def test_hugo_facts_validate_valid():
    """Test validate() on valid HugoFacts."""
    data = _minimal_hugo_facts_data()
    facts = HugoFacts.from_dict(data)
    assert facts.validate() is True


def test_hugo_facts_validate_empty_languages():
    """Test validate() rejects empty languages list."""
    facts = HugoFacts(
        schema_version="1.0",
        languages=[],
        default_language="en",
        default_language_in_subdir=False,
        permalinks={},
        outputs={},
        taxonomies={},
        source_files=[],
    )
    with pytest.raises(ValueError, match="languages"):
        facts.validate()


def test_hugo_facts_validate_empty_default_language():
    """Test validate() rejects empty default_language."""
    facts = HugoFacts(
        schema_version="1.0",
        languages=["en"],
        default_language="",
        default_language_in_subdir=False,
        permalinks={},
        outputs={},
        taxonomies={},
        source_files=[],
    )
    with pytest.raises(ValueError, match="default_language"):
        facts.validate()


def test_hugo_facts_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_hugo_facts_data()
    facts = HugoFacts.from_dict(data)
    json_str = facts.to_json()
    restored = HugoFacts.from_json(json_str)
    assert restored.default_language == facts.default_language
    assert restored.languages == facts.languages

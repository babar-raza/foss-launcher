"""Tests for ProductFacts and EvidenceMap models.

Validates:
- ProductFacts serialization
- EvidenceMap serialization
- Optional fields handling
"""

import pytest

from src.launch.models.product_facts import EvidenceMap, ProductFacts


def test_product_facts_minimal():
    """Test ProductFacts with minimal required fields."""
    facts = ProductFacts(
        schema_version="v1.0",
        product_name="Test Product",
        product_slug="test-product",
        repo_url="https://github.com/test/repo",
        repo_sha="a" * 40,
        positioning={"tagline": "Test", "short_description": "Desc"},
        supported_platforms=["python"],
        claims=[],
        claim_groups={
            "key_features": [],
            "install_steps": [],
            "quickstart_steps": [],
            "workflow_claims": [],
            "limitations": [],
            "compatibility_notes": [],
        },
        supported_formats=[],
        workflows=[],
        api_surface_summary={},
        example_inventory=[],
    )

    data = facts.to_dict()

    assert data["schema_version"] == "v1.0"
    assert data["product_name"] == "Test Product"
    assert data["product_slug"] == "test-product"
    assert data["repo_url"] == "https://github.com/test/repo"
    assert data["repo_sha"] == "a" * 40
    assert "version" not in data
    assert "license" not in data


def test_product_facts_with_optional():
    """Test ProductFacts with optional fields."""
    facts = ProductFacts(
        schema_version="v1.0",
        product_name="Test Product",
        product_slug="test-product",
        repo_url="https://github.com/test/repo",
        repo_sha="b" * 40,
        positioning={"tagline": "Test", "short_description": "Desc"},
        supported_platforms=["python"],
        claims=[],
        claim_groups={
            "key_features": [],
            "install_steps": [],
            "quickstart_steps": [],
            "workflow_claims": [],
            "limitations": [],
            "compatibility_notes": [],
        },
        supported_formats=[],
        workflows=[],
        api_surface_summary={},
        example_inventory=[],
        version="1.0.0",
        license={"spdx_id": "MIT"},
        limitations=["limit1", "limit2"],
    )

    data = facts.to_dict()

    assert data["version"] == "1.0.0"
    assert data["license"] == {"spdx_id": "MIT"}
    assert data["limitations"] == ["limit1", "limit2"]


def test_product_facts_round_trip():
    """Test ProductFacts serialization round-trip."""
    original = ProductFacts(
        schema_version="v1.0",
        product_name="Test",
        product_slug="test",
        repo_url="https://github.com/test/repo",
        repo_sha="c" * 40,
        positioning={"tagline": "T", "short_description": "D"},
        supported_platforms=["python", "node"],
        claims=[{"claim_id": "c1", "claim_text": "text", "claim_kind": "feature", "truth_status": "fact"}],
        claim_groups={
            "key_features": ["c1"],
            "install_steps": [],
            "quickstart_steps": [],
            "workflow_claims": [],
            "limitations": [],
            "compatibility_notes": [],
        },
        supported_formats=[],
        workflows=[],
        api_surface_summary={"module1": ["func1", "func2"]},
        example_inventory=[],
    )

    data = original.to_dict()
    restored = ProductFacts.from_dict(data)

    assert restored.product_name == original.product_name
    assert restored.product_slug == original.product_slug
    assert restored.supported_platforms == original.supported_platforms
    assert restored.claims == original.claims
    assert restored.api_surface_summary == original.api_surface_summary


def test_evidence_map_minimal():
    """Test EvidenceMap with minimal fields."""
    emap = EvidenceMap(
        schema_version="v1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="d" * 40,
        claims=[],
    )

    data = emap.to_dict()

    assert data["schema_version"] == "v1.0"
    assert data["repo_url"] == "https://github.com/test/repo"
    assert data["repo_sha"] == "d" * 40
    assert data["claims"] == []
    # contradictions should not appear if empty
    assert "contradictions" not in data


def test_evidence_map_with_claims():
    """Test EvidenceMap with claims and citations."""
    claim = {
        "claim_id": "c1",
        "claim_text": "Supports Python 3.8+",
        "claim_kind": "compatibility",
        "truth_status": "fact",
        "citations": [
            {"path": "README.md", "start_line": 10, "end_line": 12, "source_type": "readme_technical"}
        ],
    }

    emap = EvidenceMap(
        schema_version="v1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="e" * 40,
        claims=[claim],
        contradictions=[],
    )

    data = emap.to_dict()

    assert len(data["claims"]) == 1
    assert data["claims"][0]["claim_id"] == "c1"
    assert len(data["claims"][0]["citations"]) == 1


def test_evidence_map_round_trip():
    """Test EvidenceMap serialization round-trip."""
    original = EvidenceMap(
        schema_version="v1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="f" * 40,
        claims=[
            {
                "claim_id": "c1",
                "claim_text": "test",
                "claim_kind": "feature",
                "truth_status": "fact",
                "citations": [],
            }
        ],
        contradictions=[
            {
                "claim_a_id": "c1",
                "claim_b_id": "c2",
                "resolution": "prefer_higher_priority",
                "winning_claim_id": "c1",
            }
        ],
    )

    data = original.to_dict()
    restored = EvidenceMap.from_dict(data)

    assert restored.repo_url == original.repo_url
    assert restored.repo_sha == original.repo_sha
    assert len(restored.claims) == 1
    assert len(restored.contradictions) == 1

"""Tests for TC-2389: Worker I/O contract validation."""
import pytest
from launch.workers._shared.contracts import (
    validate_artifact,
    DEFINED_SCHEMAS,
    PRODUCT_FACTS_SCHEMA,
    PAGE_PLAN_SCHEMA,
    SECTION_DRAFT_SCHEMA,
)


def test_validate_artifact_product_facts_valid():
    """Valid product_facts dict → True."""
    data = {
        "product_name": "Aspose.3D",
        "claims": [{"claim_id": "c1", "claim_text": "Supports 3D formats"}],
        "claim_groups": {"key_features": ["c1"]},
    }
    assert validate_artifact(data, "product_facts") is True


def test_validate_artifact_product_facts_missing_field():
    """Missing required field 'claims' → False."""
    data = {
        "product_name": "Aspose.3D",
        "claim_groups": {},
    }
    assert validate_artifact(data, "product_facts") is False


def test_validate_artifact_page_plan_valid():
    """Valid page_plan with pages array → True."""
    data = {
        "pages": [
            {"slug": "index", "page_role": "landing", "output_path": "content/index.md"}
        ]
    }
    assert validate_artifact(data, "page_plan") is True


def test_validate_artifact_unknown_schema():
    """Unknown schema name → True (backwards compat)."""
    assert validate_artifact({"anything": "goes"}, "nonexistent_schema") is True


def test_validate_artifact_section_draft_valid():
    """Valid section_draft → True."""
    data = {
        "sections": [
            {"heading": "Introduction", "level": 2, "body": "Some content here."}
        ]
    }
    assert validate_artifact(data, "section_draft") is True


def test_validate_artifact_section_draft_missing_body():
    """Section draft missing required 'body' field → False."""
    data = {
        "sections": [
            {"heading": "Introduction", "level": 2}
        ]
    }
    assert validate_artifact(data, "section_draft") is False


def test_defined_schemas_contains_all():
    """DEFINED_SCHEMAS has all expected schema keys."""
    assert "product_facts" in DEFINED_SCHEMAS
    assert "page_plan" in DEFINED_SCHEMAS
    assert "section_draft" in DEFINED_SCHEMAS


def test_validate_artifact_empty_pages_array():
    """Page plan with empty pages array → True (valid empty list)."""
    data = {"pages": []}
    assert validate_artifact(data, "page_plan") is True

"""Tests for PatchBundle model.

Validates:
- PatchBundle serialization (to_dict/from_dict)
- Round-trip consistency
- Optional fields handling
- Validation logic
- Sub-component models (Patch)

TC-1031: Typed Artifact Models -- Worker Models
"""

import pytest

from src.launch.models.patch_bundle import (
    Patch,
    PatchBundle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_file_patch_data() -> dict:
    """Create a create_file patch dict for testing."""
    return {
        "patch_id": "create_overview",
        "type": "create_file",
        "path": "content/docs/python/overview/_index.md",
        "new_content": "---\ntitle: Overview\n---\n# Overview\n",
        "content_hash": "a" * 64,
    }


def _update_anchor_patch_data() -> dict:
    """Create an update_by_anchor patch dict for testing."""
    return {
        "patch_id": "update_install",
        "type": "update_by_anchor",
        "path": "content/docs/python/install/_index.md",
        "anchor": "## Installation",
        "new_content": "Run `pip install aspose-3d`",
        "content_hash": "b" * 64,
    }


def _update_frontmatter_patch_data() -> dict:
    """Create an update_frontmatter_keys patch dict for testing."""
    return {
        "patch_id": "update_fm_overview",
        "type": "update_frontmatter_keys",
        "path": "content/docs/python/overview/_index.md",
        "frontmatter_updates": {"draft": False, "weight": 10},
        "content_hash": "c" * 64,
    }


def _minimal_bundle_data() -> dict:
    """Create minimal PatchBundle dict for testing."""
    return {
        "schema_version": "1.0",
        "patches": [_create_file_patch_data()],
    }


# ---------------------------------------------------------------------------
# Patch tests
# ---------------------------------------------------------------------------

def test_patch_create_file():
    """Test Patch with create_file type."""
    data = _create_file_patch_data()
    patch = Patch.from_dict(data)
    assert patch.patch_id == "create_overview"
    assert patch.patch_type == "create_file"
    assert patch.path == "content/docs/python/overview/_index.md"
    assert patch.new_content is not None
    assert patch.content_hash == "a" * 64


def test_patch_update_by_anchor():
    """Test Patch with update_by_anchor type."""
    data = _update_anchor_patch_data()
    patch = Patch.from_dict(data)
    assert patch.patch_type == "update_by_anchor"
    assert patch.anchor == "## Installation"
    assert patch.new_content is not None


def test_patch_update_frontmatter():
    """Test Patch with update_frontmatter_keys type."""
    data = _update_frontmatter_patch_data()
    patch = Patch.from_dict(data)
    assert patch.patch_type == "update_frontmatter_keys"
    assert patch.frontmatter_updates == {"draft": False, "weight": 10}


def test_patch_with_expected_before_hash():
    """Test Patch with expected_before_hash."""
    data = _create_file_patch_data()
    data["expected_before_hash"] = "e" * 64
    patch = Patch.from_dict(data)
    assert patch.expected_before_hash == "e" * 64
    result = patch.to_dict()
    assert result["expected_before_hash"] == "e" * 64


def test_patch_update_file_range():
    """Test Patch with update_file_range type."""
    patch = Patch(
        patch_id="range_update",
        patch_type="update_file_range",
        path="content/test.md",
        content_hash="d" * 64,
        new_content="Updated content",
        start_line=5,
        end_line=10,
    )
    data = patch.to_dict()
    assert data["type"] == "update_file_range"
    assert data["start_line"] == 5
    assert data["end_line"] == 10


def test_patch_to_dict_deterministic():
    """Test Patch.to_dict key ordering."""
    data = _create_file_patch_data()
    patch = Patch.from_dict(data)
    result = patch.to_dict()
    # Verify required fields are present
    assert "patch_id" in result
    assert "type" in result
    assert "path" in result
    assert "content_hash" in result


def test_patch_round_trip():
    """Test Patch round-trip."""
    data = _create_file_patch_data()
    original = Patch.from_dict(data)
    serialized = original.to_dict()
    restored = Patch.from_dict(serialized)
    assert restored.patch_id == original.patch_id
    assert restored.patch_type == original.patch_type
    assert restored.path == original.path
    assert restored.content_hash == original.content_hash
    assert restored.new_content == original.new_content


# ---------------------------------------------------------------------------
# PatchBundle tests
# ---------------------------------------------------------------------------

def test_patch_bundle_minimal():
    """Test PatchBundle with empty patches."""
    bundle = PatchBundle(schema_version="1.0")
    data = bundle.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["patches"] == []


def test_patch_bundle_from_dict():
    """Test PatchBundle.from_dict."""
    data = _minimal_bundle_data()
    bundle = PatchBundle.from_dict(data)
    assert bundle.schema_version == "1.0"
    assert len(bundle.patches) == 1
    assert bundle.patches[0].patch_id == "create_overview"


def test_patch_bundle_multiple_patch_types():
    """Test PatchBundle with multiple patch types."""
    data = {
        "schema_version": "1.0",
        "patches": [
            _create_file_patch_data(),
            _update_anchor_patch_data(),
            _update_frontmatter_patch_data(),
        ],
    }
    bundle = PatchBundle.from_dict(data)
    assert len(bundle.patches) == 3
    types = [p.patch_type for p in bundle.patches]
    assert "create_file" in types
    assert "update_by_anchor" in types
    assert "update_frontmatter_keys" in types


def test_patch_bundle_round_trip():
    """Test PatchBundle round-trip."""
    data = {
        "schema_version": "1.0",
        "patches": [
            _create_file_patch_data(),
            _update_anchor_patch_data(),
        ],
    }
    original = PatchBundle.from_dict(data)
    serialized = original.to_dict()
    restored = PatchBundle.from_dict(serialized)
    assert restored.schema_version == original.schema_version
    assert len(restored.patches) == len(original.patches)
    assert restored.patches[0].patch_id == original.patches[0].patch_id
    assert restored.patches[1].patch_id == original.patches[1].patch_id


def test_patch_bundle_validate_valid():
    """Test validate() on valid bundle."""
    data = _minimal_bundle_data()
    bundle = PatchBundle.from_dict(data)
    assert bundle.validate() is True


def test_patch_bundle_validate_invalid_type():
    """Test validate() rejects invalid patch type."""
    bundle = PatchBundle(
        schema_version="1.0",
        patches=[
            Patch(
                patch_id="bad",
                patch_type="invalid_type",
                path="test.md",
                content_hash="f" * 64,
            ),
        ],
    )
    with pytest.raises(ValueError, match="patch type"):
        bundle.validate()


def test_patch_bundle_validate_empty_patch_id():
    """Test validate() rejects empty patch_id."""
    bundle = PatchBundle(
        schema_version="1.0",
        patches=[
            Patch(
                patch_id="",
                patch_type="create_file",
                path="test.md",
                content_hash="f" * 64,
            ),
        ],
    )
    with pytest.raises(ValueError, match="patch_id"):
        bundle.validate()


def test_patch_bundle_validate_empty_path():
    """Test validate() rejects empty path."""
    bundle = PatchBundle(
        schema_version="1.0",
        patches=[
            Patch(
                patch_id="test",
                patch_type="create_file",
                path="",
                content_hash="f" * 64,
            ),
        ],
    )
    with pytest.raises(ValueError, match="path"):
        bundle.validate()


def test_patch_bundle_validate_empty_content_hash():
    """Test validate() rejects empty content_hash."""
    bundle = PatchBundle(
        schema_version="1.0",
        patches=[
            Patch(
                patch_id="test",
                patch_type="create_file",
                path="test.md",
                content_hash="",
            ),
        ],
    )
    with pytest.raises(ValueError, match="content_hash"):
        bundle.validate()


def test_patch_bundle_json_round_trip():
    """Test JSON serialization round-trip via base class methods."""
    data = _minimal_bundle_data()
    bundle = PatchBundle.from_dict(data)
    json_str = bundle.to_json()
    restored = PatchBundle.from_json(json_str)
    assert restored.schema_version == bundle.schema_version
    assert len(restored.patches) == len(bundle.patches)

"""Tests for base model classes.

Validates:
- Stable serialization (to_dict/from_dict round-trip)
- JSON serialization with deterministic output
- Schema validation hooks
"""

import json
from pathlib import Path

import pytest

from src.launch.models.base import Artifact, BaseModel


class ConcreteModel(BaseModel):
    """Concrete implementation for testing BaseModel."""

    def __init__(self, value: str):
        self.value = value

    def to_dict(self):
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data):
        return cls(value=data["value"])


class ConcreteArtifact(Artifact):
    """Concrete implementation for testing Artifact."""

    def __init__(self, schema_version: str, data: str):
        super().__init__(schema_version)
        self.data = data

    def to_dict(self):
        result = super().to_dict()
        result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data):
        return cls(schema_version=data["schema_version"], data=data["data"])


def test_base_model_round_trip():
    """Test that to_dict/from_dict preserves data."""
    original = ConcreteModel("test_value")
    data = original.to_dict()
    restored = ConcreteModel.from_dict(data)

    assert restored.value == original.value


def test_base_model_to_json_deterministic():
    """Test that to_json produces deterministic output."""
    model1 = ConcreteModel("test")
    model2 = ConcreteModel("test")

    json1 = model1.to_json()
    json2 = model2.to_json()

    assert json1 == json2
    # Verify it's valid JSON
    assert json.loads(json1) == {"value": "test"}


def test_base_model_from_json():
    """Test deserialization from JSON string."""
    json_str = '{"value": "test_value"}'
    model = ConcreteModel.from_json(json_str)
    assert model.value == "test_value"


def test_artifact_includes_schema_version():
    """Test that Artifact always includes schema_version."""
    artifact = ConcreteArtifact("v1.0", "test_data")
    data = artifact.to_dict()

    assert "schema_version" in data
    assert data["schema_version"] == "v1.0"
    assert data["data"] == "test_data"


def test_artifact_round_trip():
    """Test Artifact serialization round-trip."""
    original = ConcreteArtifact("v1.0", "test_data")
    data = original.to_dict()
    restored = ConcreteArtifact.from_dict(data)

    assert restored.schema_version == original.schema_version
    assert restored.data == original.data


def test_artifact_json_stable_keys():
    """Test that JSON output has stable key ordering."""
    artifact = ConcreteArtifact("v1.0", "test")
    json_str = artifact.to_json()

    # Parse and verify keys are in expected order
    parsed = json.loads(json_str)
    keys = list(parsed.keys())

    # schema_version should be first (from base class)
    assert keys[0] == "schema_version"
    assert "data" in keys

"""Tests for RunConfig ingestion configuration (TC-1021).

Validates:
- Backward compatibility: RunConfig works without ingestion section
- Full ingestion section round-trip (to_dict/from_dict)
- Partial ingestion section handling
- Helper methods return correct defaults when ingestion is absent
- Helper methods return configured values when ingestion is present
- Schema validation against updated run_config.schema.json

Spec references:
- specs/02_repo_ingestion.md (scan_directories, gitignore_mode)
- specs/05_example_curation.md (example_directories)
- specs/schemas/run_config.schema.json (ingestion property)
"""

import json
from pathlib import Path

import pytest

from src.launch.models.run_config import RunConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_run_config_data(**overrides):
    """Build a minimal valid RunConfig dict for testing.

    All required fields are present; optional fields can be injected via overrides.
    """
    base = {
        "schema_version": "1.2",
        "product_slug": "test-product",
        "product_name": "Test Product",
        "family": "test",
        "github_repo_url": "https://github.com/test/repo",
        "github_ref": "a" * 40,
        "required_sections": ["products", "docs"],
        "site_layout": {
            "content_root": "content",
            "subdomain_roots": {
                "products": "content/products.aspose.org",
                "docs": "content/docs.aspose.org",
                "kb": "content/kb.aspose.org",
                "reference": "content/reference.aspose.org",
                "blog": "content/blog.aspose.org",
            },
            "localization": {
                "mode_by_section": {
                    "products": "dir",
                    "docs": "dir",
                    "kb": "dir",
                    "reference": "dir",
                    "blog": "filename",
                },
            },
        },
        "allowed_paths": ["content/products.aspose.org/test/en/"],
        "llm": {
            "api_base_url": "http://127.0.0.1:11434/v1",
            "model": "test-model",
            "decoding": {"temperature": 0.0},
        },
        "mcp": {"enabled": True, "listen_host": "127.0.0.1", "listen_port": 8787},
        "telemetry": {"endpoint_url": "http://127.0.0.1:8765", "project": "test"},
        "commit_service": {
            "endpoint_url": "http://127.0.0.1:4320/v1",
            "github_token_env": "GITHUB_TOKEN",
            "commit_message_template": "test commit",
            "commit_body_template": "test body",
        },
        "templates_version": "templates.v1",
        "ruleset_version": "ruleset.v1",
        "allow_inference": False,
        "max_fix_attempts": 3,
        "budgets": {
            "max_runtime_s": 3600,
            "max_llm_calls": 500,
            "max_llm_tokens": 1000000,
            "max_file_writes": 100,
            "max_patch_attempts": 5,
            "max_lines_per_file": 500,
            "max_files_changed": 100,
        },
        "locales": ["en"],
    }
    base.update(overrides)
    return base


FULL_INGESTION = {
    "scan_directories": ["src/", "docs/"],
    "exclude_patterns": ["*.pyc", "__pycache__/**"],
    "gitignore_mode": "strict",
    "example_directories": ["tutorials/", "cookbook/"],
    "record_binary_files": False,
    "detect_phantom_paths": False,
}


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

class TestRunConfigIngestionBackwardCompat:
    """Ensure RunConfig works identically when ingestion section is absent."""

    def test_no_ingestion_section_from_dict(self):
        """RunConfig.from_dict works without ingestion key."""
        data = _minimal_run_config_data()
        assert "ingestion" not in data
        rc = RunConfig.from_dict(data)
        assert rc.ingestion is None

    def test_no_ingestion_section_to_dict(self):
        """to_dict omits ingestion when it is None."""
        data = _minimal_run_config_data()
        rc = RunConfig.from_dict(data)
        result = rc.to_dict()
        assert "ingestion" not in result

    def test_no_ingestion_round_trip(self):
        """Round-trip preserves all required fields when ingestion is absent."""
        data = _minimal_run_config_data()
        rc = RunConfig.from_dict(data)
        restored = RunConfig.from_dict(rc.to_dict())
        assert restored.product_slug == rc.product_slug
        assert restored.product_name == rc.product_name
        assert restored.family == rc.family
        assert restored.github_ref == rc.github_ref
        assert restored.ingestion is None


# ---------------------------------------------------------------------------
# Ingestion section tests
# ---------------------------------------------------------------------------

class TestRunConfigIngestionSection:
    """Test ingestion section handling in RunConfig model."""

    def test_empty_ingestion_section(self):
        """Empty ingestion dict is preserved through round-trip."""
        data = _minimal_run_config_data(ingestion={})
        rc = RunConfig.from_dict(data)
        assert rc.ingestion == {}
        result = rc.to_dict()
        assert result["ingestion"] == {}

    def test_full_ingestion_section(self):
        """Full ingestion dict is preserved through round-trip."""
        data = _minimal_run_config_data(ingestion=FULL_INGESTION)
        rc = RunConfig.from_dict(data)
        assert rc.ingestion == FULL_INGESTION
        result = rc.to_dict()
        assert result["ingestion"] == FULL_INGESTION

    def test_partial_ingestion_section(self):
        """Partial ingestion dict (only some fields) is preserved."""
        partial = {"scan_directories": ["src/"], "gitignore_mode": "ignore"}
        data = _minimal_run_config_data(ingestion=partial)
        rc = RunConfig.from_dict(data)
        assert rc.ingestion == partial
        result = rc.to_dict()
        assert result["ingestion"] == partial

    def test_ingestion_round_trip_deterministic(self):
        """Two round-trips produce identical output (determinism)."""
        data = _minimal_run_config_data(ingestion=FULL_INGESTION)
        rc1 = RunConfig.from_dict(data)
        rc2 = RunConfig.from_dict(rc1.to_dict())
        json1 = rc1.to_json()
        json2 = rc2.to_json()
        assert json1 == json2


# ---------------------------------------------------------------------------
# Helper method default tests (no ingestion section)
# ---------------------------------------------------------------------------

class TestIngestionHelperDefaults:
    """Verify helper methods return schema defaults when ingestion is None."""

    @pytest.fixture()
    def rc_no_ingestion(self):
        return RunConfig.from_dict(_minimal_run_config_data())

    def test_get_scan_directories_default(self, rc_no_ingestion):
        """Default scan_directories is [\".\"] per spec."""
        assert rc_no_ingestion.get_scan_directories() == ["."]

    def test_get_exclude_patterns_default(self, rc_no_ingestion):
        """Default exclude_patterns is [] per schema."""
        assert rc_no_ingestion.get_exclude_patterns() == []

    def test_get_gitignore_mode_default(self, rc_no_ingestion):
        """Default gitignore_mode is \"respect\" per spec."""
        assert rc_no_ingestion.get_gitignore_mode() == "respect"

    def test_get_example_directories_default(self, rc_no_ingestion):
        """Default example_directories is [] per spec."""
        assert rc_no_ingestion.get_example_directories() == []

    def test_get_record_binary_files_default(self, rc_no_ingestion):
        """Default record_binary_files is True per schema."""
        assert rc_no_ingestion.get_record_binary_files() is True

    def test_get_detect_phantom_paths_default(self, rc_no_ingestion):
        """Default detect_phantom_paths is True per schema."""
        assert rc_no_ingestion.get_detect_phantom_paths() is True


# ---------------------------------------------------------------------------
# Helper method defaults with empty ingestion section
# ---------------------------------------------------------------------------

class TestIngestionHelperDefaultsEmptySection:
    """Verify helpers return defaults when ingestion is {} (no sub-keys)."""

    @pytest.fixture()
    def rc_empty_ingestion(self):
        return RunConfig.from_dict(_minimal_run_config_data(ingestion={}))

    def test_get_scan_directories_empty(self, rc_empty_ingestion):
        assert rc_empty_ingestion.get_scan_directories() == ["."]

    def test_get_exclude_patterns_empty(self, rc_empty_ingestion):
        assert rc_empty_ingestion.get_exclude_patterns() == []

    def test_get_gitignore_mode_empty(self, rc_empty_ingestion):
        assert rc_empty_ingestion.get_gitignore_mode() == "respect"

    def test_get_example_directories_empty(self, rc_empty_ingestion):
        assert rc_empty_ingestion.get_example_directories() == []

    def test_get_record_binary_files_empty(self, rc_empty_ingestion):
        assert rc_empty_ingestion.get_record_binary_files() is True

    def test_get_detect_phantom_paths_empty(self, rc_empty_ingestion):
        assert rc_empty_ingestion.get_detect_phantom_paths() is True


# ---------------------------------------------------------------------------
# Helper method configured value tests
# ---------------------------------------------------------------------------

class TestIngestionHelperConfiguredValues:
    """Verify helpers return configured values when ingestion is populated."""

    @pytest.fixture()
    def rc_full_ingestion(self):
        return RunConfig.from_dict(_minimal_run_config_data(ingestion=FULL_INGESTION))

    def test_get_scan_directories_configured(self, rc_full_ingestion):
        assert rc_full_ingestion.get_scan_directories() == ["src/", "docs/"]

    def test_get_exclude_patterns_configured(self, rc_full_ingestion):
        assert rc_full_ingestion.get_exclude_patterns() == ["*.pyc", "__pycache__/**"]

    def test_get_gitignore_mode_configured(self, rc_full_ingestion):
        assert rc_full_ingestion.get_gitignore_mode() == "strict"

    def test_get_example_directories_configured(self, rc_full_ingestion):
        assert rc_full_ingestion.get_example_directories() == ["tutorials/", "cookbook/"]

    def test_get_record_binary_files_configured_false(self, rc_full_ingestion):
        assert rc_full_ingestion.get_record_binary_files() is False

    def test_get_detect_phantom_paths_configured_false(self, rc_full_ingestion):
        assert rc_full_ingestion.get_detect_phantom_paths() is False


# ---------------------------------------------------------------------------
# Edge cases for boolean helpers
# ---------------------------------------------------------------------------

class TestIngestionBooleanEdgeCases:
    """Verify boolean helpers handle explicit False correctly (not confused with None)."""

    def test_record_binary_files_explicit_true(self):
        rc = RunConfig.from_dict(_minimal_run_config_data(
            ingestion={"record_binary_files": True}
        ))
        assert rc.get_record_binary_files() is True

    def test_record_binary_files_explicit_false(self):
        rc = RunConfig.from_dict(_minimal_run_config_data(
            ingestion={"record_binary_files": False}
        ))
        assert rc.get_record_binary_files() is False

    def test_detect_phantom_paths_explicit_true(self):
        rc = RunConfig.from_dict(_minimal_run_config_data(
            ingestion={"detect_phantom_paths": True}
        ))
        assert rc.get_detect_phantom_paths() is True

    def test_detect_phantom_paths_explicit_false(self):
        rc = RunConfig.from_dict(_minimal_run_config_data(
            ingestion={"detect_phantom_paths": False}
        ))
        assert rc.get_detect_phantom_paths() is False


# ---------------------------------------------------------------------------
# Schema validation test
# ---------------------------------------------------------------------------

class TestIngestionSchemaValidation:
    """Validate ingestion section against JSON schema."""

    @pytest.fixture()
    def schema(self):
        schema_path = Path(__file__).parent.parent.parent.parent / "specs" / "schemas" / "run_config.schema.json"
        return json.loads(schema_path.read_text(encoding="utf-8"))

    def test_schema_has_ingestion_property(self, schema):
        """Schema defines the ingestion property."""
        assert "ingestion" in schema["properties"]

    def test_ingestion_not_required(self, schema):
        """ingestion is NOT in the required array (backward compat)."""
        assert "ingestion" not in schema.get("required", [])

    def test_ingestion_has_all_subfields(self, schema):
        """Schema ingestion property has all 6 sub-fields."""
        ing = schema["properties"]["ingestion"]["properties"]
        expected = sorted([
            "scan_directories",
            "exclude_patterns",
            "gitignore_mode",
            "example_directories",
            "record_binary_files",
            "detect_phantom_paths",
        ])
        assert sorted(ing.keys()) == expected

    def test_ingestion_additional_properties_false(self, schema):
        """Schema ingestion property blocks unknown fields."""
        assert schema["properties"]["ingestion"].get("additionalProperties") is False

    def test_gitignore_mode_enum_values(self, schema):
        """gitignore_mode enum matches spec: respect, ignore, strict."""
        gm = schema["properties"]["ingestion"]["properties"]["gitignore_mode"]
        assert sorted(gm["enum"]) == sorted(["respect", "ignore", "strict"])

    def test_scan_directories_default(self, schema):
        """scan_directories default is [\".\"]."""
        sd = schema["properties"]["ingestion"]["properties"]["scan_directories"]
        assert sd.get("default") == ["."]

    def test_gitignore_mode_default(self, schema):
        """gitignore_mode default is \"respect\"."""
        gm = schema["properties"]["ingestion"]["properties"]["gitignore_mode"]
        assert gm.get("default") == "respect"

    def test_example_directories_default(self, schema):
        """example_directories default is []."""
        ed = schema["properties"]["ingestion"]["properties"]["example_directories"]
        assert ed.get("default") == []

    def test_record_binary_files_default(self, schema):
        """record_binary_files default is True."""
        rb = schema["properties"]["ingestion"]["properties"]["record_binary_files"]
        assert rb.get("default") is True

    def test_detect_phantom_paths_default(self, schema):
        """detect_phantom_paths default is True."""
        dp = schema["properties"]["ingestion"]["properties"]["detect_phantom_paths"]
        assert dp.get("default") is True


# ---------------------------------------------------------------------------
# Pilot config backward compatibility
# ---------------------------------------------------------------------------

class TestPilotConfigBackwardCompat:
    """Ensure existing pilot configs can still be loaded as RunConfig."""

    def _load_yaml_as_dict(self, path: Path):
        """Load YAML file and return as dict."""
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_pilot_3d_config_loads(self):
        """pilot-aspose-3d-foss-python config loads without error."""
        path = Path(__file__).parent.parent.parent.parent / "specs" / "pilots" / "pilot-aspose-3d-foss-python" / "run_config.pinned.yaml"
        if not path.exists():
            pytest.skip(f"Pilot config not found: {path}")
        data = self._load_yaml_as_dict(path)
        rc = RunConfig.from_dict(data)
        assert rc.product_slug == "pilot-aspose-3d-foss-python"
        assert rc.ingestion is None  # No ingestion section in existing config

    def test_pilot_note_config_loads(self):
        """pilot-aspose-note-foss-python config loads without error."""
        path = Path(__file__).parent.parent.parent.parent / "specs" / "pilots" / "pilot-aspose-note-foss-python" / "run_config.pinned.yaml"
        if not path.exists():
            pytest.skip(f"Pilot config not found: {path}")
        data = self._load_yaml_as_dict(path)
        rc = RunConfig.from_dict(data)
        assert rc.product_slug == "pilot-aspose-note-foss-python"
        assert rc.ingestion is None  # No ingestion section in existing config

    def test_pilot_config_helpers_return_defaults(self):
        """Pilot configs without ingestion section get correct helper defaults."""
        path = Path(__file__).parent.parent.parent.parent / "specs" / "pilots" / "pilot-aspose-3d-foss-python" / "run_config.pinned.yaml"
        if not path.exists():
            pytest.skip(f"Pilot config not found: {path}")
        data = self._load_yaml_as_dict(path)
        rc = RunConfig.from_dict(data)
        assert rc.get_scan_directories() == ["."]
        assert rc.get_exclude_patterns() == []
        assert rc.get_gitignore_mode() == "respect"
        assert rc.get_example_directories() == []
        assert rc.get_record_binary_files() is True
        assert rc.get_detect_phantom_paths() is True

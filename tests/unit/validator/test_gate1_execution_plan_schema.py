"""Tests for TC-3540: execution_plan.schema.json evolution.

Verifies the schema accepts all fields produced by the autopilot code,
including new fields added in TC-3540 (guardrail_applied, llm_rationale,
hydrated_artifact_count, provenance_status, timestamp).

Fields are sourced from src/launch/cli/main.py lines 476-495.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import jsonschema


SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "specs" / "schemas" / "execution_plan.schema.json"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _minimal_valid() -> dict:
    return {
        "schema_version": "1.0",
        "baseline_start_worker": "W1",
        "final_start_worker": "W1",
        "reasons": [{"code": "CHECKPOINT_MISSING", "message": "W1 checkpoint absent"}],
        "target_repo_sha": "abc123def456",
    }


class TestExecutionPlanSchemaBaseline:
    def test_minimal_valid_passes(self):
        schema = _load_schema()
        doc = _minimal_valid()
        jsonschema.validate(doc, schema)  # Should not raise

    def test_unknown_field_rejected(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["totally_unknown_field_xyz"] = "value"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)

    def test_missing_required_field_rejected(self):
        schema = _load_schema()
        doc = _minimal_valid()
        del doc["target_repo_sha"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)


class TestExecutionPlanSchemaNewFields:
    """TC-3540: New fields observed in pilot runs must be accepted.

    Source evidence: src/launch/cli/main.py lines 476-495 (execution_plan dict).
    Real pilot files also confirmed all five fields present.
    """

    def test_guardrail_applied_true_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["guardrail_applied"] = True
        jsonschema.validate(doc, schema)

    def test_guardrail_applied_false_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["guardrail_applied"] = False
        jsonschema.validate(doc, schema)

    def test_llm_rationale_string_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["llm_rationale"] = "LLM suggested starting from W5 due to stale W5 artifacts."
        jsonschema.validate(doc, schema)

    def test_llm_rationale_empty_string_accepted(self):
        """Empty string is the default value written by main.py when LLM is not used."""
        schema = _load_schema()
        doc = _minimal_valid()
        doc["llm_rationale"] = ""
        jsonschema.validate(doc, schema)

    def test_llm_rationale_null_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["llm_rationale"] = None
        jsonschema.validate(doc, schema)

    def test_hydrated_artifact_count_integer_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["hydrated_artifact_count"] = 5
        jsonschema.validate(doc, schema)

    def test_hydrated_artifact_count_zero_accepted(self):
        """Zero is the value written when llm_planner_used=False."""
        schema = _load_schema()
        doc = _minimal_valid()
        doc["hydrated_artifact_count"] = 0
        jsonschema.validate(doc, schema)

    def test_hydrated_artifact_count_null_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["hydrated_artifact_count"] = None
        jsonschema.validate(doc, schema)

    def test_provenance_status_string_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["provenance_status"] = "valid"
        jsonschema.validate(doc, schema)

    def test_provenance_status_none_accepted(self):
        """'none' is the literal string written by main.py when hydrate_source is 'none'."""
        schema = _load_schema()
        doc = _minimal_valid()
        doc["provenance_status"] = "none"
        jsonschema.validate(doc, schema)

    def test_provenance_status_null_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["provenance_status"] = None
        jsonschema.validate(doc, schema)

    def test_timestamp_iso8601_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["timestamp"] = "2026-02-28T10:00:00Z"
        jsonschema.validate(doc, schema)

    def test_timestamp_with_offset_accepted(self):
        """Real pilot files use datetime.now(timezone.utc).isoformat() which includes +00:00."""
        schema = _load_schema()
        doc = _minimal_valid()
        doc["timestamp"] = "2026-02-27T12:04:54.956982+00:00"
        jsonschema.validate(doc, schema)

    def test_timestamp_null_accepted(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["timestamp"] = None
        jsonschema.validate(doc, schema)

    def test_all_new_fields_together(self):
        """Validates all 5 new TC-3540 fields can coexist in one document."""
        schema = _load_schema()
        doc = _minimal_valid()
        doc["guardrail_applied"] = True
        doc["llm_rationale"] = "LLM said W5"
        doc["hydrated_artifact_count"] = 3
        doc["provenance_status"] = "valid"
        doc["timestamp"] = "2026-02-28T10:00:00Z"
        doc["llm_planner_used"] = True
        doc["heal_mode"] = False
        jsonschema.validate(doc, schema)

    def test_pilot_cells_plan_validates(self):
        """Replica of actual pilot-aspose-cells execution_plan.json — must validate."""
        schema = _load_schema()
        doc = {
            "baseline_start_worker": "W1",
            "final_start_worker": "W1",
            "goal": "validate",
            "guardrail_applied": False,
            "hydrate_source": "none",
            "hydrated_artifact_count": 0,
            "llm_planner_used": False,
            "llm_rationale": "",
            "provenance_status": "none",
            "reasons": [
                {
                    "code": "ARTIFACT_MISSING:repo_inventory.json",
                    "message": "artifacts/repo_inventory.json failed check",
                }
            ],
            "ruleset_version": "ruleset.v1_1",
            "schema_version": "1.0",
            "target_repo_sha": "0000000000000000000000000000000000000000",
            "templates_version": "templates.v1",
            "timestamp": "2026-02-27T12:04:54.956982+00:00",
        }
        jsonschema.validate(doc, schema)

    def test_pilot_3d_plan_validates(self):
        """Replica of actual pilot-aspose-3d execution_plan.json — must validate."""
        schema = _load_schema()
        doc = {
            "baseline_start_worker": "W5",
            "final_start_worker": "W5",
            "goal": "validate",
            "guardrail_applied": False,
            "hydrate_source": ".foss_state\\3d\\python\\artifacts\\37114723be16c9c9441c8fb93116b044ad1aa6b5",
            "hydrated_artifact_count": 22,
            "llm_planner_used": False,
            "llm_rationale": "",
            "provenance_status": ".foss_state\\3d\\python\\artifacts\\37114723be16c9c9441c8fb93116b044ad1aa6b5",
            "reasons": [
                {
                    "code": "DRAFTS_EMPTY",
                    "message": "No .md files found under drafts/",
                }
            ],
            "ruleset_version": "ruleset.v1_1",
            "schema_version": "1.0",
            "target_repo_sha": "37114723be16c9c9441c8fb93116b044ad1aa6b5",
            "templates_version": "templates.v1",
            "timestamp": "2026-02-27T15:18:04.800723+00:00",
        }
        jsonschema.validate(doc, schema)


class TestExecutionPlanSchemaExistingFields:
    """Existing fields must still work correctly after TC-3540 additions."""

    def test_reasons_with_evidence_paths(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["reasons"] = [
            {
                "code": "CHECKPOINT_MISSING",
                "message": "No W3 checkpoint",
                "evidence_paths": ["artifacts/api_inventory.json"],
            }
        ]
        jsonschema.validate(doc, schema)

    def test_llm_suggested_start_worker_null(self):
        schema = _load_schema()
        doc = _minimal_valid()
        doc["llm_suggested_start_worker"] = None
        jsonschema.validate(doc, schema)

    def test_full_realistic_plan_without_new_fields(self):
        """A plan produced before TC-3540 fields were written must still validate."""
        schema = _load_schema()
        doc = {
            "schema_version": "1.0",
            "baseline_start_worker": "W5",
            "llm_suggested_start_worker": "W5",
            "final_start_worker": "W5",
            "reasons": [{"code": "CHECKPOINT_W4_PRESENT", "message": "W4 artifact found"}],
            "hydrate_source": "sha-abc123",
            "target_repo_sha": "deadbeef",
            "ruleset_version": "1.2",
            "templates_version": "1.0",
            "goal": "draft",
            "heal_mode": False,
            "llm_planner_used": True,
        }
        jsonschema.validate(doc, schema)

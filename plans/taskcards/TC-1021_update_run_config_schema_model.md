---
id: TC-1021
title: "Update run_config Schema + Model for Configurable Ingestion"
status: Done
owner: agent-c
updated: "2026-02-07"
tags: [schema, models, ingestion, phase-1]
depends_on: [TC-1020]
allowed_paths:
  - "specs/schemas/run_config.schema.json"
  - "src/launch/models/run_config.py"
  - "tests/unit/models/test_run_config*.py"
  - "plans/taskcards/TC-1021_*"
  - "reports/agents/agent_c/TC-1021/**"
evidence_required:
  - reports/agents/agent_c/TC-1021/evidence.md
  - reports/agents/agent_c/TC-1021/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1021: Update run_config Schema + Model for Configurable Ingestion

## Objective

Add configurable ingestion settings to `run_config.schema.json` and the Python `RunConfig` model. The specs updated by TC-1020 introduced three new configuration areas that need schema and model support:

- `run_config.ingestion.scan_directories` (default: `["."]`)
- `run_config.ingestion.gitignore_mode` (enum: `"respect"/"ignore"/"strict"`, default: `"respect"`)
- `run_config.ingestion.example_directories` (default: `[]`)

Plus additional fields for fine-grained control: `exclude_patterns`, `record_binary_files`, `detect_phantom_paths`.

## Required spec references

- `specs/02_repo_ingestion.md` -- Configurable scan directories (TC-1020), .gitignore support (TC-1020)
- `specs/05_example_curation.md` -- Configurable example discovery directories (TC-1020)
- `specs/schemas/run_config.schema.json` -- Schema definition
- `specs/01_system_contract.md` -- System inputs and contract

## Scope

### In scope

- Add `ingestion` property to `run_config.schema.json` with 6 sub-fields
- Add `ingestion` field to `RunConfig` Python model (`__init__`, `to_dict`, `from_dict`)
- Add helper methods: `get_scan_directories()`, `get_exclude_patterns()`, `get_gitignore_mode()`, `get_example_directories()`, `get_record_binary_files()`, `get_detect_phantom_paths()`
- Unit tests for new model fields and helpers
- Backward compatibility: existing pilot configs must still load without error

### Out of scope

- W1/W2/W3 worker implementation changes (those are separate taskcards)
- New pilot configs that use the ingestion section
- Schema validation library changes

## Inputs

- Current `run_config.schema.json` (617 lines)
- Current `run_config.py` model (218 lines)
- TC-1020 spec changes in `specs/02_repo_ingestion.md` and `specs/05_example_curation.md`

## Outputs

- Updated `specs/schemas/run_config.schema.json` with `ingestion` property
- Updated `src/launch/models/run_config.py` with `ingestion` field and helpers
- New test file `tests/unit/models/test_run_config_ingestion.py`

## Allowed paths

- `specs/schemas/run_config.schema.json`
- `src/launch/models/run_config.py`
- `tests/unit/models/test_run_config*.py`
- `plans/taskcards/TC-1021_*`
- `reports/agents/agent_c/TC-1021/**`

### Allowed paths rationale

Schema and model files are the direct targets. Tests validate the changes. Taskcard and evidence paths are standard agent outputs.

## Implementation steps

1. Read current schema and model files
2. Add `ingestion` property to JSON schema with all 6 sub-fields, proper types, defaults, and description
3. Add `ingestion` optional parameter to `RunConfig.__init__`, `to_dict`, and `from_dict`
4. Add helper methods with safe defaults for missing ingestion section
5. Write unit tests covering: round-trip, defaults, partial config, full config, helpers
6. Verify existing pilot configs still validate (no required fields added)
7. Run full test suite

## Failure modes

1. **Schema validation breaks existing configs**
   - Detection: Existing pilot configs fail to load
   - Resolution: Ensure all new fields are optional (not in `required` array)
   - Gate: Schema validation in `from_dict`

2. **Helper methods return wrong defaults**
   - Detection: Unit tests for default values fail
   - Resolution: Each helper must handle None ingestion section and missing sub-keys
   - Gate: Unit tests with assertions on defaults

3. **Non-deterministic serialization**
   - Detection: `to_dict` output differs between runs
   - Resolution: Use stable field ordering in `to_dict`, sorted keys in JSON
   - Gate: Determinism test comparing two serializations

## Task-specific review checklist

- [ ] All 6 ingestion sub-fields present in schema with correct types
- [ ] Schema defaults match spec requirements (scan_directories=["."], gitignore_mode="respect", etc.)
- [ ] `additionalProperties: false` on ingestion object
- [ ] Python model accepts `ingestion=None` (backward compat)
- [ ] All helper methods handle missing ingestion section gracefully
- [ ] Helper methods handle missing individual fields gracefully
- [ ] Round-trip test: `from_dict(to_dict(config)) == config`
- [ ] Existing pilot configs still load without modification
- [ ] No new required fields added to schema root

## Deliverables

- Updated schema: `specs/schemas/run_config.schema.json`
- Updated model: `src/launch/models/run_config.py`
- Tests: `tests/unit/models/test_run_config_ingestion.py`
- Evidence: `reports/agents/agent_c/TC-1021/evidence.md`
- Self-review: `reports/agents/agent_c/TC-1021/self_review.md`

## Acceptance checks

- [ ] Schema validates with `jsonschema` library
- [ ] All existing pilot configs validate against updated schema
- [ ] `RunConfig.from_dict()` works with and without `ingestion` section
- [ ] All helper methods return correct defaults when `ingestion` is absent
- [ ] Full test suite passes: `PYTHONHASHSEED=0 pytest tests/ -x`
- [ ] No regressions in existing tests

## Self-review

See `reports/agents/agent_c/TC-1021/self_review.md`

## Preconditions / dependencies

- TC-1020 (update specs) is complete -- specs now reference `run_config.ingestion.*` fields

## Test plan

- Unit tests in `tests/unit/models/test_run_config_ingestion.py`:
  - `test_run_config_no_ingestion_section` -- backward compat
  - `test_run_config_empty_ingestion_section` -- empty dict
  - `test_run_config_full_ingestion_section` -- all fields populated
  - `test_run_config_partial_ingestion_section` -- some fields only
  - `test_get_scan_directories_default` -- returns ["."]
  - `test_get_scan_directories_configured` -- returns configured value
  - `test_get_exclude_patterns_default` -- returns []
  - `test_get_gitignore_mode_default` -- returns "respect"
  - `test_get_example_directories_default` -- returns []
  - `test_get_record_binary_files_default` -- returns True
  - `test_get_detect_phantom_paths_default` -- returns True
  - `test_ingestion_round_trip` -- from_dict(to_dict) preserves data
- Run full test suite to verify no regressions

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract

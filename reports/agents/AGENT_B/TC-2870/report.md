# TC-2870 Evidence Report: Enable Multi-Pass Generation Prevention Engine

> Agent: agent_b
> Taskcard: TC-2870
> Date: 2026-02-26

## Gap Analysis

### Root Cause
The RunConfig model (Round 12) was extended with 4 optional fields, but only `review_enabled`
was added to `specs/schemas/run_config.schema.json`. Because the schema has
`additionalProperties: false`, any config setting `multi_pass_generation`, `incremental`, or
`prompt_library_path` was rejected at validation time (`src/launch/io/run_config.py:26`).

Additionally, `multi_pass.py` had hardcoded temperatures (0.3/0.1/0.3) in 5 LLM call sites.
The config temperature values from `RunConfig.get_multi_pass_config()` were computed but
never consumed by the orchestrator.

### Orphaned Fields

| Field | Model (run_config.py) | Schema | Status |
|-------|----------------------|--------|--------|
| `multi_pass_generation` | Line 88 | **MISSING** -> FIXED | Added object with 6 sub-properties |
| `incremental` | Line 89 | **MISSING** -> FIXED | Added object with 2 sub-properties |
| `prompt_library_path` | Line 90 | **MISSING** -> FIXED | Added string property |
| `review_enabled` | Line 91 | Present (line 437) | Already correct |

## Changes Made

### Phase 1: Schema Fix
**File**: `specs/schemas/run_config.schema.json`
- Added `multi_pass_generation` object property with 6 sub-fields:
  `enabled`, `skip_refine_for_thin_pages`, `min_claims_for_outline`,
  `outline_temperature`, `draft_temperature`, `refine_temperature`
- Added `incremental` object property with 2 sub-fields: `enabled`, `previous_run_path`
- Added `prompt_library_path` string property

### Phase 2: Temperature Wiring
**File**: `src/launch/workers/w5_section_writer/multi_pass.py`
- Added 3 instance variables in `__init__`: `_outline_temperature`, `_draft_temperature`, `_refine_temperature`
- Read from config dict with fallback defaults matching previous hardcoded values (0.3/0.1/0.3)
- Replaced 5 hardcoded temperature values in LLM call sites with instance vars

### Phase 3: Pilot Config Activation
- `configs/pilots/pilot-aspose-cells-foss-python.yaml` — added `multi_pass_generation` block
- `configs/pilots/pilot-aspose-note-foss-python.resolved.yaml` — added `multi_pass_generation` block
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` — added block
- `specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml` — added block
- `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml` — added block
- All pilots: `enabled: true`, all temperatures: `0.0` (determinism)

### Phase 4: Documentation
**File**: `docs/reference/config.md`
- Added `multi_pass_generation` section with field table and determinism note

### Phase 5: Tests
- `test_llm_temperatures_from_config` — verifies 0.0 temps flow through config to LLM calls
- `test_multi_pass_generation_accepted_by_real_schema` — validates config block against real schema
- `test_incremental_accepted_by_real_schema` — validates incremental + prompt_library_path in schema

## Verification Evidence

### Schema Validation
```
$ PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/validate_schemas.py
SUCCESS: All 34 schema(s) are valid
```

### Config Dry-Run
```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launch.cli.main run \
    --config specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml --dry-run
Config validation passed
Would create RUN_DIR: runs/r_20260226T172151Z_launch_pilot-aspose-cells-foss-python_...
```

### RunConfig Parsing
```
$ python -c "... RunConfig.from_dict(data) ..."
multi_pass_enabled: True
multi_pass_config: {'enabled': True, 'skip_refine_for_thin_pages': True,
  'min_claims_for_outline': 3, 'outline_temperature': 0.0,
  'draft_temperature': 0.0, 'refine_temperature': 0.0}
```

### Test Suite
```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
6584 passed, 13 skipped, 3 xfailed, 9 xpassed in 141.75s
```

### Targeted Tests
```
$ pytest tests/.../test_tc_1780_prompt_multipass.py::...test_llm_called_with_correct_temperatures
$ pytest tests/.../test_tc_1780_prompt_multipass.py::...test_llm_temperatures_from_config
$ pytest tests/.../test_run_config.py::test_multi_pass_generation_accepted_by_real_schema
$ pytest tests/.../test_run_config.py::test_incremental_accepted_by_real_schema
4 passed in 0.66s
```

## Backward Compatibility
- Existing test `test_llm_called_with_correct_temperatures` still passes: when no temp overrides
  are in config, fallback defaults (0.3/0.1/0.3) match previous hardcoded behavior
- Configs without `multi_pass_generation` still work (field is optional, default `enabled: false`)

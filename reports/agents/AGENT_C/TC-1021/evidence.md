# TC-1021 Evidence: Update run_config Schema + Model for Configurable Ingestion

## Summary

Added configurable ingestion settings to `run_config.schema.json` and the Python `RunConfig` model per TC-1020 spec requirements. All 6 sub-fields are optional with backward-compatible defaults.

## Files Changed

| File | Action | Lines Changed |
|------|--------|---------------|
| `specs/schemas/run_config.schema.json` | Modified | +38 (ingestion property block) |
| `src/launch/models/run_config.py` | Modified | +63 (ingestion field + 6 helper methods) |
| `tests/unit/models/test_run_config_ingestion.py` | Created | 296 lines (42 tests) |
| `plans/taskcards/TC-1021_update_run_config_schema_model.md` | Created | Taskcard |

## Schema Changes

Added `ingestion` property to `run_config.schema.json` properties object (NOT to `required` array):

```json
"ingestion": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "scan_directories":     { "type": "array",   "default": ["."],      ... },
    "exclude_patterns":     { "type": "array",   "default": [],         ... },
    "gitignore_mode":       { "type": "string",  "enum": [...],  "default": "respect" },
    "example_directories":  { "type": "array",   "default": [],         ... },
    "record_binary_files":  { "type": "boolean", "default": true,       ... },
    "detect_phantom_paths": { "type": "boolean", "default": true,       ... }
  }
}
```

## Model Changes

1. Added `ingestion: Optional[Dict[str, Any]] = None` to `__init__` parameters
2. Added `self.ingestion = ingestion` assignment
3. Added `ingestion` to `to_dict()` (only included if not None)
4. Added `ingestion=data.get("ingestion")` to `from_dict()`
5. Added 6 helper methods with safe defaults:
   - `get_scan_directories()` -> `["."]` when absent
   - `get_exclude_patterns()` -> `[]` when absent
   - `get_gitignore_mode()` -> `"respect"` when absent
   - `get_example_directories()` -> `[]` when absent
   - `get_record_binary_files()` -> `True` when absent
   - `get_detect_phantom_paths()` -> `True` when absent

## Test Results

### TC-1021 specific tests (42 tests)
```
tests/unit/models/test_run_config_ingestion.py  42 passed in 0.42s
```

### Full test suite
```
2087 passed, 12 skipped, 1 warning in 95.84s
```

Zero regressions.

## Backward Compatibility Verification

Tested loading existing pilot configs:
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` -- loads OK, ingestion=None, all helpers return defaults
- `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml` -- loads OK, ingestion=None, all helpers return defaults
- `configs/pilots/pilot-aspose-note-foss-python.resolved.yaml` -- loads OK (manually verified)

No existing configs require modification.

## Determinism Verification

- JSON schema is valid JSON (verified with `json.load`)
- `to_json()` output is deterministic (tested with `sort_keys=True`)
- Round-trip test: `from_dict(to_dict(config))` produces identical JSON output
- `PYTHONHASHSEED=0` was set for all test runs

## Spec Alignment

| Spec Reference | Field | Default | Status |
|----------------|-------|---------|--------|
| specs/02_repo_ingestion.md "Configurable scan directories" | scan_directories | ["."] | Implemented |
| specs/02_repo_ingestion.md ".gitignore support" | gitignore_mode | "respect" | Implemented |
| specs/05_example_curation.md "Configurable example discovery" | example_directories | [] | Implemented |
| Schema extension (TC-1021) | exclude_patterns | [] | Implemented |
| Schema extension (TC-1021) | record_binary_files | true | Implemented |
| Schema extension (TC-1021) | detect_phantom_paths | true | Implemented |

## Commands Run

```bash
# Validate schema JSON syntax
.venv/Scripts/python.exe -c "import json; json.load(open('specs/schemas/run_config.schema.json'))"

# Run TC-1021 specific tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/test_run_config_ingestion.py -v
# Result: 42 passed

# Run full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
# Result: 2087 passed, 12 skipped, 0 failed
```

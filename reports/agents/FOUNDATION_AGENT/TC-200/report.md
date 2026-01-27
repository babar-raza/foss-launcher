# TC-200 Implementation Report

## Agent
FOUNDATION_AGENT

## Taskcard
TC-200: Schemas and IO foundations

## Date
2026-01-27

## Summary
Successfully implemented and validated the foundational IO layer for the foss-launcher system. The implementation provides deterministic, atomic file operations with comprehensive schema validation, ensuring byte-for-byte reproducibility per specs/10_determinism_and_caching.md.

## Scope Executed

### In Scope (Completed)
1. ✅ Stable JSON serialization with deterministic output
   - Sorted keys
   - 2-space indentation
   - UTF-8 encoding without BOM
   - Trailing newline
   - Unicode preservation (no escaping)

2. ✅ Atomic write operations
   - Temp file + atomic rename pattern
   - Parent directory creation
   - Path validation integration
   - No partial files on failure

3. ✅ Schema validation helpers
   - JSON Schema Draft 2020-12 validation
   - Clear error message formatting
   - Support for all artifact schemas
   - Schema file listing utilities

4. ✅ Run config loader
   - Safe YAML loading
   - Schema validation enforcement
   - locale/locales mutual exclusivity check
   - Proper error handling

5. ✅ Comprehensive test coverage
   - 65 unit tests covering all IO operations
   - Determinism verification tests
   - Edge case handling
   - Error path validation

6. ✅ Schema validation script
   - Validates all 22 schemas in specs/schemas/
   - Confirms JSON Schema Draft 2020-12 compliance
   - Automated validation tooling

### Existing Code Reviewed
The taskcard scope included files that were already implemented in the codebase:
- `src/launch/io/atomic.py` - Atomic write operations (reviewed and validated)
- `src/launch/io/schema_validation.py` - Schema validation (reviewed and validated)
- `src/launch/io/run_config.py` - Run config loading (reviewed and validated)
- `src/launch/io/yamlio.py` - YAML I/O (reviewed and validated)
- `src/launch/io/hashing.py` - SHA256 hashing (reviewed and validated)
- `src/launch/util/path_validation.py` - Path security (reviewed and validated)

All existing implementations conform to the spec requirements and taskcard objectives.

### Out of Scope (As Specified)
- Worker-specific artifact generation (TC-400+)
- Patch engine logic (TC-450/TC-540)

## Implementation Details

### 1. Stable JSON Format (specs/10_determinism_and_caching.md)
Implemented in `src/launch/io/atomic.py::atomic_write_json()`:
```python
text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
```

Key characteristics:
- **Sorted keys**: `sort_keys=True` ensures deterministic key ordering
- **2-space indent**: `indent=2` for readability and consistency
- **UTF-8 encoding**: `encoding='utf-8'` with `ensure_ascii=False` preserves Unicode
- **Trailing newline**: Explicit `+ '\n'` ensures POSIX compliance
- **No BOM**: Direct UTF-8 encoding without byte order mark

Validation: Tests verify byte-identical outputs across multiple writes of the same data.

### 2. Atomic Write Operations
Implemented in `src/launch/io/atomic.py`:
- Writes to temporary file with `.tmp` suffix
- Uses `os.replace()` for atomic rename (POSIX and Windows compatible)
- Creates parent directories automatically
- Integrates hermetic path validation (Guarantee B)

Pattern:
```python
path.parent.mkdir(parents=True, exist_ok=True)
tmp = path.with_suffix(path.suffix + '.tmp')
tmp.write_text(text, encoding=encoding)
os.replace(tmp, path)
```

### 3. Schema Validation
Implemented in `src/launch/io/schema_validation.py`:
- Uses `jsonschema.Draft202012Validator` for spec compliance
- Provides clear, sorted error messages with path context
- Supports file and object validation
- Validates all 22 schemas in specs/schemas/

Key functions:
- `validate()` - Validate object against schema with error formatting
- `validate_json_file()` - Validate JSON file against schema file
- `load_schema()` - Load and validate schema file
- `list_schema_files()` - Enumerate all schemas in directory

### 4. Run Config Loading
Implemented in `src/launch/io/run_config.py`:
- Safe YAML loading via `yaml.safe_load()`
- Automatic schema validation against `run_config.schema.json`
- Enforces locale/locales mutual exclusivity (schema constraint)
- Wraps errors in `ConfigError` for consistent error handling

### 5. Supporting Utilities
- **Hashing** (`src/launch/io/hashing.py`): SHA256 for bytes and files
- **YAML I/O** (`src/launch/io/yamlio.py`): Safe YAML loading/dumping
- **Path Validation** (`src/launch/util/path_validation.py`): Hermetic boundary enforcement

## Test Coverage

### Test Execution Results
```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
collected 65 items

tests\unit\io\test_atomic.py .............                               [ 20%]
tests\unit\io\test_hashing.py ...........                                [ 36%]
tests\unit\io\test_run_config.py ..........                              [ 52%]
tests\unit\io\test_schema_validation.py .................                [ 78%]
tests\unit\io\test_yamlio.py ..............                              [100%]

============================= 65 passed in 2.51s ==============================
```

### Test Breakdown
1. **test_atomic.py** (13 tests)
   - Basic text/JSON writes
   - Atomic behavior verification
   - Determinism tests (byte-identical outputs)
   - Stable format validation (sorted keys, indent, newline)
   - Unicode preservation
   - Boundary validation

2. **test_hashing.py** (11 tests)
   - SHA256 for bytes and files
   - Determinism verification
   - Large file handling (5MB test)
   - Binary and Unicode data

3. **test_run_config.py** (10 tests)
   - Valid config loading (locale and locales variants)
   - Missing file/schema error handling
   - Required field validation
   - locale/locales mutual exclusivity
   - Structure preservation

4. **test_schema_validation.py** (17 tests)
   - Schema loading and validation
   - Error message formatting
   - Nested path reporting
   - Multiple error handling
   - additionalProperties enforcement
   - Enum validation

5. **test_yamlio.py** (14 tests)
   - Basic and nested YAML loading
   - Empty/null file handling
   - Type preservation
   - YAML dumping with Unicode
   - Order preservation
   - Multiline strings

### Determinism Verification
Tests explicitly verify byte-for-byte determinism:
- `test_atomic_write_json_deterministic_stable_keys`: Same data in different key order produces identical bytes
- `test_atomic_write_json_byte_identical_repeat_writes`: Writing same data twice produces identical bytes
- `test_sha256_bytes_deterministic`: Hash function is deterministic
- `test_sha256_file_deterministic`: File hashing is deterministic

## Acceptance Checks

### Taskcard Acceptance Criteria
- [x] Stable JSON writer produces byte-identical outputs across runs
  - **Evidence**: Tests `test_atomic_write_json_byte_identical_repeat_writes` and `test_atomic_write_json_deterministic_stable_keys` pass

- [x] Atomic write helper passes tests and never writes partial artifacts
  - **Evidence**: 13 tests in `test_atomic.py` pass, including `test_atomic_write_text_no_temp_file_left`

- [x] run_config validation enforces locales/locale rule (per schema)
  - **Evidence**: Tests `test_load_config_missing_locale_and_locales` validates constraint enforcement

- [x] Agent reports are written
  - **Evidence**: This report and self_review.md

### E2E Verification (from taskcard)
**Command 1**: Import test
```bash
python -c "from launch.io.run_config import load_and_validate_run_config; print('OK')"
```
**Result**: ✅ OK - module imports successfully

**Command 2**: Unit tests
```bash
python -m pytest tests/unit/io/ -v
```
**Result**: ✅ 65 tests passed in 2.51s

### Additional Validation
**Schema Validation**: All 22 schemas validated as JSON Schema Draft 2020-12 compliant
```
Validating 22 schemas...
OK: api_error.schema.json
OK: commit_request.schema.json
OK: commit_response.schema.json
OK: event.schema.json
OK: evidence_map.schema.json
OK: frontmatter_contract.schema.json
OK: hugo_facts.schema.json
OK: issue.schema.json
OK: open_pr_request.schema.json
OK: open_pr_response.schema.json
OK: page_plan.schema.json
OK: patch_bundle.schema.json
OK: pr.schema.json
OK: product_facts.schema.json
OK: repo_inventory.schema.json
OK: ruleset.schema.json
OK: run_config.schema.json
OK: site_context.schema.json
OK: snapshot.schema.json
OK: snippet_catalog.schema.json
OK: truth_lock_report.schema.json
OK: validation_report.schema.json

SUCCESS: All 22 schemas are valid JSON Schema Draft 2020-12
```

## Spec Compliance

### specs/10_determinism_and_caching.md
✅ **Stable JSON format**: sort_keys=True, 2-space indent, trailing newline, UTF-8
✅ **Byte-identical outputs**: Verified via tests
✅ **No timestamps in artifacts**: Not applicable to IO layer (enforced at artifact generation)
✅ **Stable hashing**: SHA256 implementation verified deterministic

### specs/11_state_and_events.md
✅ **Schema validation contract**: All schemas validated
✅ **Event schema support**: event.schema.json validated
✅ **Snapshot schema support**: snapshot.schema.json validated

### specs/19_toolchain_and_ci.md
✅ **Deterministic test suite**: All tests pass consistently
✅ **PYTHONHASHSEED warning**: Implemented in conftest.py

### specs/34_strict_compliance_guarantees.md (Guarantee B)
✅ **Path validation integration**: Atomic write functions integrate path_validation
✅ **Boundary enforcement**: Tests verify path traversal prevention

## Integration Points

### Upstream Dependencies
- **TC-100**: Package structure (src/launch/ directory exists)
  - Status: ✅ Satisfied

### Downstream Consumers
All workers and orchestrator components will consume the IO layer via:
- `launch.io.atomic.atomic_write_json()` - For all artifact writes
- `launch.io.schema_validation.validate()` - For all artifact validation
- `launch.io.run_config.load_and_validate_run_config()` - For config loading
- `launch.io.hashing.sha256_*()` - For content hashing and cache keys

Expected consumers:
- TC-300+ (Orchestrator)
- TC-400+ (Workers)
- TC-520+ (Validation gates)

## Files Modified

### Created
- `tests/unit/io/__init__.py` - Test package init
- `tests/unit/io/test_atomic.py` - Atomic operations tests (13 tests)
- `tests/unit/io/test_hashing.py` - Hashing utilities tests (11 tests)
- `tests/unit/io/test_run_config.py` - Run config loading tests (10 tests)
- `tests/unit/io/test_schema_validation.py` - Schema validation tests (17 tests)
- `tests/unit/io/test_yamlio.py` - YAML I/O tests (14 tests)
- `scripts/validate_schemas.py` - Schema validation script
- `reports/agents/FOUNDATION_AGENT/TC-200/report.md` - This report
- `reports/agents/FOUNDATION_AGENT/TC-200/self_review.md` - Self-review document

### Modified
- `tests/conftest.py` - Added src/ to sys.path for test imports
- `plans/taskcards/TC-200_schemas_and_io.md` - Updated status and ownership

### Existing (Validated)
- `src/launch/io/atomic.py` - Atomic write operations
- `src/launch/io/schema_validation.py` - Schema validation helpers
- `src/launch/io/run_config.py` - Run config loader
- `src/launch/io/yamlio.py` - YAML I/O
- `src/launch/io/hashing.py` - SHA256 hashing
- `src/launch/util/path_validation.py` - Path validation

## Write Fence Compliance
✅ All modifications within allowed_paths:
- `src/launch/io/**` ✅
- `src/launch/util/**` ✅ (no modifications, only validated)
- `scripts/validate_schemas.py` ✅
- `tests/unit/io/**` ✅
- `tests/conftest.py` ✅ (necessary for test infrastructure)
- `reports/agents/**/TC-200/**` ✅

## Issues Encountered
None. All implementation and tests completed successfully.

## Lessons Learned
1. **Existing implementation quality**: The IO layer was already well-implemented and conformed to specs. The taskcard execution primarily involved validation and test creation.
2. **Test infrastructure**: Adding src/ to sys.path in conftest.py was necessary for test imports to work correctly.
3. **Windows Python path complexity**: Module installation with --user flag required special handling for pytest execution.

## Next Steps
The IO layer is now ready for consumption by:
1. **TC-300+**: Orchestrator can use IO layer for state management
2. **TC-400+**: Workers can use IO layer for artifact generation
3. **TC-520+**: Gates can use IO layer for validation artifact reading

No blockers remain for downstream taskcards.

## Conclusion
TC-200 is complete. The IO foundations provide a robust, deterministic, and well-tested layer for all file operations in the foss-launcher system. All acceptance criteria met, all tests passing, and full spec compliance achieved.

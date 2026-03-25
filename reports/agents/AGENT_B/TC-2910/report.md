# TC-2910 Report: W2 Quality Uplift

## Status: COMPLETE

## Changes Made

### Phase 1: @property Extraction
- **File:** `src/launch/workers/w2_facts_builder/code_analyzer.py`
- Added `@property` decorator detection in `analyze_python_file()`
- Properties are collected into a `property_names` list and stored on class dict
- `build_api_inventory()` now propagates `properties` from code_analysis (was hardcoded `[]`)
- Added `.pyi` to `discover_source_files()` extension list

### Phase 2: Constructor + Class Constants
- **File:** `src/launch/workers/w2_facts_builder/code_analyzer.py`
- `__init__` parameters extracted (excluding `self`/`cls`) with name + annotation
- Stored as `constructor: {parameters: [{name, annotation}]}` or `None`
- Class-level `UPPERCASE` constants extracted (not starting with `_`)
- Stored as `class_constants: [str]`

### Phase 3: Source Location
- **File:** `src/launch/workers/w2_facts_builder/code_analyzer.py`
- `source_file` (relative path) and `start_line` added to each class entry
- Guard: empty string when `repo_dir` is `None`

### Phase 4: repo_truth Expansion
- **File:** `src/launch/workers/w2_facts_builder/code_analyzer.py`
- `build_repo_truth()` now includes:
  - `supported_formats` from `code_analysis.constants.supported_formats` (normalized uppercase)
  - `dependencies` from manifest (handles both list and dict formats)
  - `entrypoints` from manifest console_scripts

### Phase 5: W5 Prompt Enrichment
- **File:** `src/launch/workers/w5_section_writer/multi_pass.py`
- `_format_api_symbols_block()` enhanced to show:
  - `properties=[...]` (cap 10)
  - `constructor(param: type, ...)` (cap 8 params)
  - `constants=[...]` (cap 10)
  - Empty fields omitted

### Phase 6: Schema + Tests + Docs
- **File:** `specs/schemas/api_inventory.schema.json` — added constructor, class_constants, source_file, start_line
- **File:** `specs/schemas/repo_truth.schema.json` — added supported_formats, dependencies, entrypoints
- **File:** `tests/unit/workers/test_w2_code_analyzer.py` — 28 new tests
- **File:** `tests/unit/workers/test_w5_api_symbols_block.py` — 9 new tests (new file)
- **File:** `docs/dev/w2_quality_uplift.md` — developer note

## Commands Run
```bash
# New TC-2910 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py -x -v -k "Property or Constructor or ClassConstants or SourceLocation or Determinism or supported_formats"
# Result: 28 passed

# W5 prompt tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w5_api_symbols_block.py -x -v
# Result: 9 passed

# Full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
# Result: 6867 passed, 13 skipped, 0 failed
```

## Bug Fix During Implementation
- `str.isupper()` returns `True` for `"_INTERNAL"` (underscore is not a cased character)
- Added `not target.id.startswith("_")` guard for class constant extraction
- Test `test_private_constants_excluded` verified the fix

## Acceptance Criteria
- [x] Properties populated for @property-decorated methods
- [x] Constructor parameters extracted with annotations
- [x] Class constants limited to UPPERCASE only (no leading underscore)
- [x] Source file paths are relative (not absolute)
- [x] .pyi stubs discovered by discover_source_files()
- [x] W5 prompt block shows properties, constructors, constants
- [x] Token budget stays reasonable (< 2000 tokens for 20 classes)
- [x] All existing tests still pass (0 regressions)
- [x] Determinism verified (identical output on repeated runs)
- [x] All 6867 tests pass (was 6575, +292 including other new tests in repo)

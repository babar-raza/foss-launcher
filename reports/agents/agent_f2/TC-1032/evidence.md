# TC-1032 Evidence: Centralized ArtifactStore Class

## Agent: agent-f2
## Date: 2026-02-07
## Status: Complete

## Files Created

### 1. `src/launch/io/artifact_store.py` (NEW)
Centralized ArtifactStore class providing:
- `load_artifact(name)` -- Load JSON artifact from `run_dir/artifacts/`
- `load_artifact_or_default(name, default)` -- Safe load with fallback
- `write_artifact(name, data)` -- Atomic JSON write returning `{path, sha256, size}`
- `emit_event(event_type, payload)` -- Append to `events.ndjson`
- `artifact_path(name)` -- Path computation
- `exists(name)` -- Existence check

Design: Reuses `atomic_write_json` from `atomic.py`, `sha256_bytes` from `hashing.py`, and `validate`/`load_schema` from `schema_validation.py`. No duplication of existing utilities.

### 2. `src/launch/io/__init__.py` (MODIFIED - 1 line added)
Added `from .artifact_store import ArtifactStore` and `__all__` export.

### 3. `tests/unit/io/test_artifact_store.py` (NEW)
33 test cases organized into 7 test classes:
- `TestArtifactPath` (2 tests) -- path construction
- `TestExists` (3 tests) -- existence checking
- `TestLoadArtifact` (4 tests) -- happy path, not found, invalid JSON, type check
- `TestLoadArtifactOrDefault` (4 tests) -- exists, missing, None default, invalid JSON
- `TestWriteArtifact` (5 tests) -- write, sha256 entry, relative path, parent dirs, overwrite
- `TestDeterminism` (4 tests) -- same bytes, sorted keys, trailing newline, sha256 consistency
- `TestEmitEvent` (5 tests) -- append, multiple events, required fields, default IDs, creates file
- `TestSchemaValidation` (6 tests) -- load validates, load rejects, write validates, write rejects, no schemas_dir, missing schema file

## Duplication Analysis

### emit_event duplication found (9 copies):
1. `src/launch/workers/w1_repo_scout/worker.py:87`
2. `src/launch/workers/w2_facts_builder/worker.py:91`
3. `src/launch/workers/w3_snippet_curator/worker.py:66`
4. `src/launch/workers/w4_ia_planner/worker.py:219`
5. `src/launch/workers/w5_section_writer/worker.py:84`
6. `src/launch/workers/w6_linker_and_patcher/worker.py:86`
7. `src/launch/workers/w7_validator/worker.py:64`
8. `src/launch/workers/w8_fixer/worker.py:69`
9. `src/launch/workers/w9_pr_manager/worker.py:90`

### load_artifact duplication found (14+ copies):
- W5 has 4 separate functions: `load_page_plan`, `load_product_facts`, `load_snippet_catalog`, `load_evidence_map`
- W7 has `load_json_artifact`
- W8 has `load_json_artifact`
- W4 has inline load patterns at lines 264, 287
- W6 has inline load patterns at lines 131, 154
- W2 has inline load patterns at lines 209, 312
- W9 has inline load patterns at lines 355, 358

### Inconsistencies found:
- W8 emit_event uses plain dicts, others use Event model
- W8 emit_event does not pass `ensure_ascii=False`, others do
- W5 load functions raise `SectionWriterError`, W8 raises `FixerArtifactMissingError`, W7 raises generic
- Some workers use `with open()`, others use `path.read_text()`

ArtifactStore normalizes all these into a single consistent implementation.

## Test Results

### ArtifactStore tests:
```
tests/unit/io/test_artifact_store.py ................................. [100%]
33 passed in 0.52s
```

### Full test suite:
```
2004 passed, 12 skipped in 77.44s
```

Zero regressions introduced.

## Key Design Decisions

1. **Lazy import of Event model** -- Prevents circular import (models/ may import from io/)
2. **Optional schema validation** -- `schemas_dir=None` silently skips validation; backward compatible
3. **Forward-slash normalization** -- `entry["path"]` uses forward slashes for cross-platform consistency
4. **Default ID generation** -- `run_id` defaults to `run_dir.name`, trace/span IDs default to new UUIDs
5. **No modification of existing files** -- Only __init__.py touched (adding 3 lines); all other io files untouched

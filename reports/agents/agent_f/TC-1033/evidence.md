# TC-1033 Evidence: Write-Time Validation + Worker Migration to ArtifactStore

## Summary
Successfully implemented two-part enhancement: (A) write-time schema validation in atomic_write_json(), and (B) migration of all 9 workers to use centralized ArtifactStore.

## Part A: Write-Time Validation

### Change
Added optional `schema_path: Optional[str] = None` parameter to `atomic_write_json()` in `src/launch/io/atomic.py`.

When `schema_path` is provided:
1. Loads the JSON schema from the given path
2. Validates data against schema BEFORE writing
3. If validation fails, raises ValueError (file NOT written)
4. If validation passes, proceeds with normal atomic write

Backward compatible: parameter defaults to None (no validation).

### Tests
- All 13 existing atomic tests pass
- All 33 existing ArtifactStore tests pass

## Part B: Worker Migration

### Workers Migrated (9 total)

| Worker | File | emit_event | load_* functions | emit_artifact_written |
|--------|------|------------|-----------------|----------------------|
| W1 RepoScout | w1_repo_scout/worker.py | Delegated to ArtifactStore | N/A | Delegated (sha256_bytes) |
| W2 FactsBuilder | w2_facts_builder/worker.py | Delegated to ArtifactStore | N/A | Delegated (sha256_bytes) |
| W3 SnippetCurator | w3_snippet_curator/worker.py | Delegated to ArtifactStore | N/A | Delegated (sha256_bytes) |
| W4 IAPlanner | w4_ia_planner/worker.py | Delegated to ArtifactStore | load_product_facts, load_snippet_catalog | N/A |
| W5 SectionWriter | w5_section_writer/worker.py | Delegated to ArtifactStore | load_page_plan, load_product_facts, load_snippet_catalog, load_evidence_map | N/A |
| W6 LinkerPatcher | w6_linker_and_patcher/worker.py | Delegated to ArtifactStore | load_page_plan, load_draft_manifest | N/A |
| W7 Validator | w7_validator/worker.py | Delegated to ArtifactStore | load_json_artifact | N/A |
| W8 Fixer | w8_fixer/worker.py | Delegated to ArtifactStore | load_json_artifact | N/A |
| W9 PRManager | w9_pr_manager/worker.py | Delegated to ArtifactStore | Inline loads replaced | N/A |

### Migration Pattern
Each worker function was refactored to:
1. Create ArtifactStore instance using the worker's run_dir
2. Delegate to store.emit_event() / store.load_artifact()
3. Convert exceptions to preserve worker-specific error types
4. Keep function signatures identical for backward compatibility

### Test Results (per-worker)

| Worker | Tests | Result |
|--------|-------|--------|
| W1 | 12 | 12 PASS |
| W2 | 8 | 8 PASS |
| W3 | 11 | 11 PASS |
| W4 | 41 | 41 PASS |
| W5 | 17 | 17 PASS |
| W6 | 20 | 20 PASS |
| W7 | 20 | 20 PASS |
| W8 | 25 | 25 PASS |
| W9 | 18 | 18 PASS |

### Full Test Suite
```
2235 passed, 12 skipped, 1 warning in 82.80s
```

Zero failures. All 2235 tests pass after complete migration.

## Duplicated Code Eliminated

### emit_event duplication: 9 copies reduced to 9 thin wrappers
Before: Each worker had a full emit_event() implementation creating Event objects, opening files, writing NDJSON.
After: Each emit_event() is a 4-line wrapper delegating to ArtifactStore.emit_event().

### emit_artifact_written_event duplication: 3 copies refactored
Before: W1, W2, W3 each had full implementations computing SHA-256 and emitting events.
After: Use centralized sha256_bytes() from hashing module + ArtifactStore.emit_event().

### load_* function duplication: 10+ copies refactored
Before: Each worker had per-artifact load functions doing file I/O + JSON parsing + error handling.
After: Each delegates to ArtifactStore.load_artifact() with exception conversion to preserve worker-specific error types.

## Files Modified
1. `src/launch/io/atomic.py` - Added schema_path parameter
2. `src/launch/workers/w1_repo_scout/worker.py` - emit_event + emit_artifact_written_event
3. `src/launch/workers/w2_facts_builder/worker.py` - emit_event + emit_artifact_written_event
4. `src/launch/workers/w3_snippet_curator/worker.py` - emit_event + emit_artifact_written_event
5. `src/launch/workers/w4_ia_planner/worker.py` - emit_event + load_product_facts + load_snippet_catalog
6. `src/launch/workers/w5_section_writer/worker.py` - emit_event + 4 load functions
7. `src/launch/workers/w6_linker_and_patcher/worker.py` - emit_event + 2 load functions
8. `src/launch/workers/w7_validator/worker.py` - emit_event + load_json_artifact
9. `src/launch/workers/w8_fixer/worker.py` - emit_event + load_json_artifact
10. `src/launch/workers/w9_pr_manager/worker.py` - emit_event + inline load replacement

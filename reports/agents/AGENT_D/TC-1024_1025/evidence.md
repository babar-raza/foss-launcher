# Evidence: TC-1024 + TC-1025

## Agent: agent-d
## Date: 2026-02-07
## Taskcards: TC-1024 (.gitignore support + phantom path detection), TC-1025 (fingerprinting improvements)

## Test Results

### Full test suite
```
2235 passed, 12 skipped, 1 warning in 83.73s
```

### TC-402 fingerprint tests (70 tests)
```
70 passed in 0.89s
```

Breakdown of new tests added (28 total):
- TestParseGitignore: 3 tests
- TestMatchesGitignore: 5 tests
- TestWalkRepoFilesWithGitignore: 2 tests
- TestWalkRepoFilesConfigurable: 2 tests
- TestDetectPhantomPaths: 8 tests
- TestBuildRepoInventoryEnhanced: 7 tests (+ 1 existing class with 4 existing tests)

## Files Modified

### src/launch/workers/w1_repo_scout/fingerprint.py
- Added imports: `fnmatch`, `logging`, `re`, `Optional`
- Added constants: `DEFAULT_IGNORE_DIRS`, `LARGE_FILE_THRESHOLD_BYTES`
- Added functions: `parse_gitignore()`, `matches_gitignore()`, `walk_repo_files_with_gitignore()`, `detect_phantom_paths()`, `_check_phantom_ref()`
- Modified `walk_repo_files()`: Added `extra_ignore_dirs`, `exclude_patterns` params
- Modified `build_repo_inventory()`: Added `gitignore_mode`, `extra_ignore_dirs`, `exclude_patterns`, `detect_phantoms` params; now populates `paths_detailed`, `gitignored_files`, `phantom_paths`, `large_files`
- Modified `emit_fingerprint_events()`: Added optional `large_files` param; emits `REPO_SCOUT_LARGE_FILE` events

### src/launch/workers/w1_repo_scout/discover_docs.py
- Modified `discover_documentation_files()`: Added `gitignore_mode` param; marks entries with `gitignored: True` when matching .gitignore patterns

### src/launch/workers/w1_repo_scout/discover_examples.py
- Modified `discover_example_files()`: Added `gitignore_mode` param; marks entries with `gitignored: True` when matching .gitignore patterns

### src/launch/workers/w1_repo_scout/worker.py
- Updated TC-402 step: Passes `gitignore_mode`, `exclude_patterns`, `detect_phantoms` to `build_repo_inventory()`
- Updated TC-403 step: Passes `gitignore_mode` to `discover_documentation_files()`
- Updated TC-404 step: Passes `gitignore_mode` to `discover_example_files()`

### tests/unit/workers/test_tc_402_fingerprint.py
- Added 6 new test classes with 28 tests

## Backward Compatibility

All new parameters have backward-compatible defaults:
- `gitignore_mode` defaults to `"respect"`
- `extra_ignore_dirs` defaults to `None`
- `exclude_patterns` defaults to `None`
- `detect_phantoms` defaults to `True`
- `large_files` defaults to `None`
- `paths` field remains a flat string list (backward compatible)
- `paths_detailed` is an additive field

## Design Decisions

1. **stdlib only**: Used `fnmatch` from stdlib instead of `pathspec` external dependency
2. **Exhaustive mandate**: Gitignored files are RECORDED but MARKED, never excluded
3. **Backward compatible paths**: Kept `paths` as flat list; added `paths_detailed` separately
4. **Deterministic output**: All lists sorted; phantom_paths sorted by (referenced_path, referencing_file, reference_line)
5. **Phantom detection scope**: Only scans .md, .rst, .txt files to avoid false positives
6. **Negation patterns**: Gracefully skipped (not supported) rather than crashing

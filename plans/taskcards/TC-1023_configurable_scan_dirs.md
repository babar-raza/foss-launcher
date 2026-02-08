---
id: TC-1023
title: "Configurable scan directories for code/example discovery"
status: Complete
priority: Normal
owner: "agent-d"
updated: "2026-02-07"
tags: ["w1", "discovery", "ingestion", "configurable"]
depends_on: ["TC-1020", "TC-1021"]
allowed_paths:
  - plans/taskcards/TC-1023_configurable_scan_dirs.md
  - src/launch/workers/w1_repo_scout/discover_examples.py
  - src/launch/workers/w1_repo_scout/worker.py
  - tests/unit/workers/test_tc_404_discover_examples.py
  - reports/agents/agent_d/TC-1022_1023/evidence.md
  - reports/agents/agent_d/TC-1022_1023/self_review.md
evidence_required:
  - reports/agents/agent_d/TC-1022_1023/evidence.md
  - reports/agents/agent_d/TC-1022_1023/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1023 — Configurable scan directories

## Objective
Expand `discover_examples.py` to accept configurable scan directories, exclude patterns, and extra example directories from `run_config.ingestion`, and to record all files regardless of language detection (no unknown-language skip).

## Problem Statement
The existing example discovery is hardcoded to scan the entire repo root and skip files with unknown language. This prevents operators from controlling which directories are scanned and causes loss of visibility for non-standard code files (config files, data files in example directories).

## Required spec references
- specs/02_repo_ingestion.md (Configurable scan directories, TC-1020)
- specs/05_example_curation.md (Configurable example discovery directories, TC-1020)
- specs/21_worker_contracts.md (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic output)

## Scope

### In scope
- Add `scan_directories` and `exclude_patterns` params to `discover_example_files()`
- Add `extra_example_dirs` param to `identify_example_roots()`
- Add `_matches_exclude_pattern()` helper function using `fnmatch`
- Remove `if language == "unknown": continue` (record all files)
- Add `file_size_bytes` to output entries
- Update `worker.py` to pass config values from `run_config_obj`
- Update tests for new behavior
- Maintain backward compatibility (defaults match current behavior)

### Out of scope
- Changes to `discover_docs.py` (handled by TC-1022)
- Changes to W2/W3/W4 workers
- .gitignore support (handled by TC-1024)

## Inputs
- Existing `discover_examples.py` with hardcoded scan behavior
- Existing `test_tc_404_discover_examples.py` tests
- RunConfig model with `get_scan_directories()`, `get_exclude_patterns()`, `get_example_directories()` helpers (TC-1021)

## Outputs
- Modified `discover_examples.py` with configurable discovery
- Modified `worker.py` with config passthrough
- Updated `test_tc_404_discover_examples.py` with TC-1023 test classes

## Allowed paths
- plans/taskcards/TC-1023_configurable_scan_dirs.md
- src/launch/workers/w1_repo_scout/discover_examples.py
- src/launch/workers/w1_repo_scout/worker.py
- tests/unit/workers/test_tc_404_discover_examples.py
- reports/agents/agent_d/TC-1022_1023/evidence.md
- reports/agents/agent_d/TC-1022_1023/self_review.md

### Allowed paths rationale
TC-1023 modifies example discovery, the W1 worker integrator, and associated tests to support configurable scan directories.

## Implementation steps

### Step 1: Add _matches_exclude_pattern helper
Add `_matches_exclude_pattern(relative_path, exclude_patterns)` using `fnmatch` for glob-style matching.

### Step 2: Update identify_example_roots
Add `extra_example_dirs: Optional[List[str]] = None` parameter. Merge extra dirs into roots with deduplication and validation.

### Step 3: Update discover_example_files
Add `scan_directories` and `exclude_patterns` params. Remove unknown language skip. Add `file_size_bytes`. Use `scan_directories` for phase 2 scan. Apply exclude patterns.

### Step 4: Update worker.py
Pass `run_config_obj.get_example_directories()` to `identify_example_roots()`. Pass `run_config_obj.get_scan_directories()` and `run_config_obj.get_exclude_patterns()` to `discover_example_files()`.

### Step 5: Update tests
Rename `test_skip_non_code_files` to `test_records_non_code_files_tc1023`. Add `TestTC1023ConfigurableScanDirs` and `TestMatchesExcludePattern` test classes.

## Failure modes

### Failure mode 1: Exclude patterns too aggressive
**Detection:** Expected files missing from discovery results
**Resolution:** Review fnmatch pattern semantics; ensure patterns match relative paths
**Spec/Gate:** specs/02_repo_ingestion.md exclude patterns

### Failure mode 2: scan_directories path normalization failure
**Detection:** Files not discovered despite being in configured directories
**Resolution:** Ensure path separator normalization (backslash to forward slash); validate directory existence
**Spec/Gate:** specs/02_repo_ingestion.md configurable scan directories

### Failure mode 3: Backward compatibility broken
**Detection:** Existing tests fail with default parameters
**Resolution:** Ensure scan_directories defaults to ["."] and exclude_patterns defaults to []
**Spec/Gate:** specs/21_worker_contracts.md backward compatibility

## Task-specific review checklist
1. [x] discover_example_files accepts scan_directories and exclude_patterns
2. [x] identify_example_roots accepts extra_example_dirs
3. [x] Unknown language files are recorded (no skip)
4. [x] file_size_bytes present on all output entries
5. [x] Exclude patterns use fnmatch glob semantics
6. [x] scan_directories defaults to ["."] (entire repo)
7. [x] exclude_patterns defaults to [] (no exclusions)
8. [x] worker.py passes config values via RunConfig helpers
9. [x] Backward compatibility maintained (defaults match old behavior)
10. [x] Non-existent extra_example_dirs silently ignored

## Deliverables
- Modified `src/launch/workers/w1_repo_scout/discover_examples.py`
- Modified `src/launch/workers/w1_repo_scout/worker.py`
- Updated `tests/unit/workers/test_tc_404_discover_examples.py`
- Evidence at `reports/agents/agent_d/TC-1022_1023/evidence.md`
- Self-review at `reports/agents/agent_d/TC-1022_1023/self_review.md`

## Acceptance checks
1. [x] All 68 tests in test_tc_404_discover_examples.py pass
2. [x] Full test suite passes (2207 passed, 12 skipped)
3. [x] Unknown language files recorded in example roots
4. [x] Exclude patterns correctly filter files
5. [x] scan_directories limits phase 2 scan scope
6. [x] Extra example directories merged into roots
7. [x] file_size_bytes present on all entries
8. [x] Backward compatibility: defaults produce same results as before (for known-language files)

## Preconditions / dependencies
- TC-1020 complete (specs updated for configurable ingestion)
- TC-1021 complete (run_config schema + model with ingestion helpers)

## Test plan
1. Test exclude patterns filter files correctly
2. Test scan_directories limits search scope
3. Test default scan_directories=["."] scans entire repo
4. Test extra_example_dirs merged into roots
5. Test non-existent extra dirs silently ignored
6. Test file_size_bytes present on root and pattern entries
7. Test unknown language recorded in example roots
8. Test _matches_exclude_pattern helper

## Self-review

### 12D Checklist
1. **Determinism:** Sorted example_roots, sorted output by (-relevance_score, path)
2. **Dependencies:** No new external dependencies; uses stdlib fnmatch
3. **Documentation:** Updated module docstring, inline comments for TC-1023
4. **Data preservation:** More files recorded (unknown language kept); no data loss
5. **Deliberate design:** Optional params with backward-compatible defaults; fnmatch for familiar glob semantics
6. **Detection:** Tests cover exclude patterns, scan dirs, unknown language, file_size_bytes
7. **Diagnostics:** language_counts in summary now includes "unknown" count
8. **Defensive coding:** OSError handling for stat(); path normalization; nonexistent dirs ignored
9. **Direct testing:** 68 tests pass in test_tc_404; full suite 2207 passed
10. **Deployment safety:** Fully backward compatible -- all new params have safe defaults
11. **Delta tracking:** Modified discover_examples.py, worker.py, test_tc_404
12. **Downstream impact:** More example files visible to W3 SnippetCurator; no breaking changes

### Verification results
- [x] Tests: 68/68 PASS (test_tc_404_discover_examples.py)
- [x] Full suite: 2207/2207 PASS, 12 skipped
- [x] Evidence captured: reports/agents/agent_d/TC-1022_1023/

## E2E verification
```powershell
PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_404_discover_examples.py -x -v
PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests/ -x
```

**Expected results:**
- 68/68 tests pass in test_tc_404_discover_examples.py
- Full suite: 2207 passed, 12 skipped

## Integration boundary proven
**Upstream:** W1 RepoScout `worker.py` calls `identify_example_roots(repo_dir, extra_example_dirs=...)` and `discover_example_files(repo_dir, example_roots, scan_directories=..., exclude_patterns=...)` with values from `run_config_obj`.

**Downstream:** `discovered_examples.json` is consumed by W3 SnippetCurator. The new fields (`file_size_bytes`) and additional entries (unknown language) are additive -- no breaking changes.

**Contract:**
- Output format: List of dicts with path, language, complexity, relevance_score, source_type, file_size_bytes
- Defaults: scan_directories=["."], exclude_patterns=[], extra_example_dirs=[]
- Unknown language files recorded with language="unknown"
- Deterministic ordering: sorted by (-relevance_score, path)

## Evidence Location
`reports/agents/agent_d/TC-1022_1023/evidence.md`

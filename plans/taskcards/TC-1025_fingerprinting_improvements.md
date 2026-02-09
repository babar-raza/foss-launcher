---
id: TC-1025
title: "Fingerprinting improvements: configurable ignore_dirs, file_size_bytes, large file telemetry"
status: Done
priority: Normal
owner: agent-d
updated: "2026-02-07"
tags: ["w1", "repo-scout", "fingerprint", "telemetry", "configuration"]
depends_on: ["TC-402", "TC-1021"]
allowed_paths:
  - plans/taskcards/TC-1025_fingerprinting_improvements.md
  - src/launch/workers/w1_repo_scout/fingerprint.py
  - src/launch/workers/w1_repo_scout/worker.py
  - tests/unit/workers/test_tc_402_fingerprint.py
  - reports/agents/agent_d/TC-1024_1025/evidence.md
  - reports/agents/agent_d/TC-1024_1025/self_review.md
evidence_required:
  - reports/agents/agent_d/TC-1025/evidence.md
  - reports/agents/agent_d/TC-1025/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1025 -- Fingerprinting Improvements

## Objective
Make `ignore_dirs` configurable by merging hardcoded defaults with `run_config.ingestion.exclude_patterns`, add `file_size_bytes` tracking per file in `repo_inventory.paths_detailed`, and emit `REPO_SCOUT_LARGE_FILE` telemetry for files exceeding 50 MB.

## Problem Statement
The `walk_repo_files()` function used hardcoded `ignore_dirs` with no way to extend them via configuration. The inventory did not include per-file size information, and there was no telemetry for unusually large files that could impact performance.

## Required spec references
- specs/02_repo_ingestion.md (Configurable ingestion settings)
- specs/10_determinism_and_caching.md (Deterministic output)
- specs/11_state_and_events.md (Event emission)
- specs/21_worker_contracts.md (W1 contract)

## Scope

### In scope
- Extract `DEFAULT_IGNORE_DIRS` as module-level constant
- Add `extra_ignore_dirs` and `exclude_patterns` parameters to `walk_repo_files()`
- Add `paths_detailed` field with `file_size_bytes` per file
- Add `large_files` field and `REPO_SCOUT_LARGE_FILE` telemetry event
- Add `LARGE_FILE_THRESHOLD_BYTES` constant (50 MB)
- Pass `exclude_patterns` from run_config through worker.py
- Maintain backward-compatible `paths` as flat string list

### Out of scope
- Changing the fingerprint algorithm itself
- Adding per-file hashes to paths_detailed
- Modifying binary detection logic

## Inputs
- `run_config.ingestion.exclude_patterns` (list of glob patterns)
- Repository file system

## Outputs
- `repo_inventory.json` with `paths_detailed` (list of {path, file_size_bytes, gitignored?})
- `repo_inventory.json` with `large_files` (list of paths > 50 MB)
- `REPO_SCOUT_LARGE_FILE` telemetry events in events.ndjson
- Backward-compatible `paths` field (flat string list)

## Allowed paths
- plans/taskcards/TC-1025_fingerprinting_improvements.md
- src/launch/workers/w1_repo_scout/fingerprint.py
- src/launch/workers/w1_repo_scout/worker.py
- tests/unit/workers/test_tc_402_fingerprint.py
- reports/agents/agent_d/TC-1024_1025/evidence.md
- reports/agents/agent_d/TC-1024_1025/self_review.md

## Implementation steps

### Step 1: Extract DEFAULT_IGNORE_DIRS constant
Moved hardcoded `ignore_dirs` set to module-level `DEFAULT_IGNORE_DIRS` frozenset. Added `LARGE_FILE_THRESHOLD_BYTES = 50 * 1024 * 1024`.

### Step 2: Add configurable parameters to walk_repo_files
Added `extra_ignore_dirs` and `exclude_patterns` parameters. Merged with defaults using set union.

### Step 3: Add file_size_bytes to inventory
Added `paths_detailed` field containing dicts with `path`, `file_size_bytes`, and optional `gitignored` flag. Kept `paths` as flat list for backward compatibility.

### Step 4: Add large file detection and telemetry
Files exceeding `LARGE_FILE_THRESHOLD_BYTES` are tracked in `large_files` list. Logger warning emitted. `emit_fingerprint_events()` now accepts optional `large_files` parameter and emits `REPO_SCOUT_LARGE_FILE` events.

### Step 5: Wire through worker.py
Updated `execute_repo_scout()` to pass `exclude_patterns` from run_config to `build_repo_inventory()`.

### Step 6: Write tests
Added TestWalkRepoFilesConfigurable (2 tests) and TestBuildRepoInventoryEnhanced (7 tests) covering all new features.

## Failure modes

### Failure mode 1: exclude_patterns too aggressive
**Detection:** Expected files missing from inventory
**Resolution:** Review fnmatch patterns; ensure patterns match intended scope
**Spec/Gate:** specs/02_repo_ingestion.md exhaustive mandate

### Failure mode 2: paths field type change breaks downstream
**Detection:** Tests expecting string list fail
**Resolution:** Maintained paths as flat string list; added paths_detailed separately
**Spec/Gate:** Backward compatibility

### Failure mode 3: Large file telemetry floods events
**Detection:** Excessive REPO_SCOUT_LARGE_FILE events in events.ndjson
**Resolution:** Events only emitted for files > 50 MB; threshold is configurable via constant
**Spec/Gate:** specs/11_state_and_events.md

## Task-specific review checklist
1. [x] DEFAULT_IGNORE_DIRS extracted as frozenset
2. [x] extra_ignore_dirs merged with defaults (not replacing)
3. [x] exclude_patterns use fnmatch (stdlib)
4. [x] paths field remains flat string list (backward compat)
5. [x] paths_detailed includes file_size_bytes for every file
6. [x] large_files threshold is 50 MB
7. [x] REPO_SCOUT_LARGE_FILE event emitted via logger + events
8. [x] All parameters have backward-compatible defaults

## Deliverables
- Modified src/launch/workers/w1_repo_scout/fingerprint.py
- Modified src/launch/workers/w1_repo_scout/worker.py
- 9 new tests in tests/unit/workers/test_tc_402_fingerprint.py
- Evidence at reports/agents/agent_d/TC-1024_1025/evidence.md

## Acceptance checks
1. [x] All 2235 tests pass (PYTHONHASHSEED=0)
2. [x] paths field is flat string list
3. [x] paths_detailed has file_size_bytes
4. [x] large_files populated when threshold exceeded
5. [x] exclude_patterns configurable via run_config
6. [x] No external dependencies added

## Preconditions / dependencies
- TC-402 (repo fingerprinting) complete
- TC-1021 (RunConfig ingestion helpers) complete

## Test plan
1. TestWalkRepoFilesConfigurable: 2 tests for extra_ignore_dirs and exclude_patterns
2. TestBuildRepoInventoryEnhanced: 7 tests for paths_detailed, large_files, backward compat

## Self-review
See reports/agents/agent_d/TC-1024_1025/self_review.md

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_402_fingerprint.py -x -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

## Integration boundary proven
**Upstream:** run_config.ingestion.exclude_patterns provides configurable patterns
**Downstream:** repo_inventory.json paths_detailed and large_files consumed by downstream workers
**Contract:** paths remains flat string list; paths_detailed is additive; large_files is additive

## Evidence Location
`reports/agents/agent_d/TC-1024_1025/evidence.md`

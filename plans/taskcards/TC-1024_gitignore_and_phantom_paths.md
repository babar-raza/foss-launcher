---
id: TC-1024
title: ".gitignore support + phantom path detection in W1 RepoScout"
status: Done
priority: Normal
owner: agent-d
updated: "2026-02-07"
tags: ["w1", "repo-scout", "gitignore", "phantom-paths", "discovery"]
depends_on: ["TC-402", "TC-1022"]
allowed_paths:
  - plans/taskcards/TC-1024_gitignore_and_phantom_paths.md
  - src/launch/workers/w1_repo_scout/fingerprint.py
  - src/launch/workers/w1_repo_scout/discover_docs.py
  - src/launch/workers/w1_repo_scout/discover_examples.py
  - src/launch/workers/w1_repo_scout/worker.py
  - tests/unit/workers/test_tc_402_fingerprint.py
  - reports/agents/agent_d/TC-1024_1025/evidence.md
  - reports/agents/agent_d/TC-1024_1025/self_review.md
evidence_required:
  - reports/agents/agent_d/TC-1024/evidence.md
  - reports/agents/agent_d/TC-1024/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1024 -- .gitignore Support + Phantom Path Detection

## Objective
Implement .gitignore file parsing and phantom path detection in W1 RepoScout's fingerprint module, ensuring gitignored files are marked but still recorded (exhaustive mandate) and broken file references in markdown docs are detected.

## Problem Statement
The `respect_gitignore` parameter in `walk_repo_files()` was declared but never implemented. Phantom path detection (checking for broken file references in docs) was listed as a placeholder `[]` in `repo_inventory.json` but never populated.

## Required spec references
- specs/02_repo_ingestion.md (Exhaustive file discovery, gitignore handling)
- specs/10_determinism_and_caching.md (Deterministic output ordering)
- specs/21_worker_contracts.md (W1 RepoScout contract)

## Scope

### In scope
- Implement `parse_gitignore()` function using stdlib `fnmatch` (no external deps)
- Implement `matches_gitignore()` for pattern matching
- Implement `walk_repo_files_with_gitignore()` that classifies files
- Add `gitignore_mode` parameter plumbing through worker.py
- Implement `detect_phantom_paths()` for markdown link/image reference checking
- Mark gitignored files in discover_docs.py and discover_examples.py
- Add comprehensive tests for all new functions

### Out of scope
- Full gitspec compliance (negation patterns, nested .gitignore files)
- External dependency additions (pathspec, gitpython)
- Changes to W2-W9 workers

## Inputs
- `run_config.ingestion.gitignore_mode` (respect | ignore | strict)
- `run_config.ingestion.detect_phantom_paths` (boolean)
- `.gitignore` file at repository root
- Markdown/text files in repository

## Outputs
- `repo_inventory.json` with populated `gitignored_files`, `phantom_paths`, and `gitignored` flags in `paths_detailed`
- Gitignored markers in discovered_docs.json and discovered_examples.json entries
- 28 new tests added to test_tc_402_fingerprint.py

## Allowed paths
- plans/taskcards/TC-1024_gitignore_and_phantom_paths.md
- src/launch/workers/w1_repo_scout/fingerprint.py
- src/launch/workers/w1_repo_scout/discover_docs.py
- src/launch/workers/w1_repo_scout/discover_examples.py
- src/launch/workers/w1_repo_scout/worker.py
- tests/unit/workers/test_tc_402_fingerprint.py
- reports/agents/agent_d/TC-1024_1025/evidence.md
- reports/agents/agent_d/TC-1024_1025/self_review.md

## Implementation steps

### Step 1: Implement gitignore parsing
Added `parse_gitignore()` and `matches_gitignore()` functions to fingerprint.py using stdlib `fnmatch`. Supports wildcard patterns, directory patterns, and path-based patterns. Negation patterns are gracefully skipped.

### Step 2: Implement walk_repo_files_with_gitignore
Created `walk_repo_files_with_gitignore()` that returns both all files and gitignored classification. Gitignored files are RECORDED (exhaustive mandate) but marked separately.

### Step 3: Implement phantom path detection
Added `detect_phantom_paths()` and helper `_check_phantom_ref()` that scan markdown/text files for broken links and image references. Handles relative paths, anchors, query strings, and URL filtering.

### Step 4: Wire through worker.py
Updated `execute_repo_scout()` to pass `gitignore_mode` from `run_config_obj.get_gitignore_mode()` to `build_repo_inventory()`, `discover_documentation_files()`, and `discover_example_files()`.

### Step 5: Mark gitignored files in discovery modules
Updated `discover_docs.py` and `discover_examples.py` to accept `gitignore_mode`, parse gitignore patterns, and add `gitignored: True` to matching entries.

### Step 6: Write tests
Added 28 new tests covering parse_gitignore, matches_gitignore, walk_repo_files_with_gitignore, detect_phantom_paths, and enhanced build_repo_inventory.

## Failure modes

### Failure mode 1: Gitignore patterns match too broadly
**Detection:** Unexpected files marked as gitignored in inventory
**Resolution:** Review matches_gitignore pattern logic; add more specific test cases
**Spec/Gate:** specs/02_repo_ingestion.md exhaustive mandate

### Failure mode 2: Phantom detection false positives
**Detection:** Valid links incorrectly flagged as phantom
**Resolution:** Improve URL/anchor filtering in _check_phantom_ref; add edge case tests
**Spec/Gate:** specs/02_repo_ingestion.md

### Failure mode 3: Non-deterministic phantom path output
**Detection:** test_deterministic_output fails
**Resolution:** Ensure sorted() is applied to phantom_paths before return
**Spec/Gate:** specs/10_determinism_and_caching.md

## Task-specific review checklist
1. [x] parse_gitignore returns empty list when no .gitignore exists
2. [x] Gitignored files are RECORDED in inventory (not excluded)
3. [x] Phantom paths are sorted deterministically
4. [x] URLs (http, https, mailto) are excluded from phantom detection
5. [x] Anchors (#section) are excluded from phantom detection
6. [x] Relative path resolution handles .. and . components
7. [x] All new parameters have backward-compatible defaults
8. [x] No external dependencies added (stdlib only)

## Deliverables
- Modified src/launch/workers/w1_repo_scout/fingerprint.py with gitignore + phantom detection
- Modified src/launch/workers/w1_repo_scout/discover_docs.py with gitignore marking
- Modified src/launch/workers/w1_repo_scout/discover_examples.py with gitignore marking
- Modified src/launch/workers/w1_repo_scout/worker.py with config plumbing
- 28 new tests in tests/unit/workers/test_tc_402_fingerprint.py
- Evidence at reports/agents/agent_d/TC-1024_1025/evidence.md

## Acceptance checks
1. [x] All 2235 tests pass (PYTHONHASHSEED=0)
2. [x] Gitignored files are recorded but marked
3. [x] Phantom paths detected for broken markdown links
4. [x] URLs and anchors correctly excluded from phantom detection
5. [x] Deterministic output ordering maintained
6. [x] No external dependencies added

## Preconditions / dependencies
- TC-402 (repo fingerprinting) complete
- TC-1022 (exhaustive discovery) complete
- TC-1021 (RunConfig ingestion helpers) complete

## Test plan
1. TestParseGitignore: 3 tests for .gitignore file parsing
2. TestMatchesGitignore: 5 tests for pattern matching
3. TestWalkRepoFilesWithGitignore: 2 tests for classified file walking
4. TestDetectPhantomPaths: 8 tests for phantom detection
5. TestBuildRepoInventoryEnhanced: 7 tests for inventory integration

## Self-review
See reports/agents/agent_d/TC-1024_1025/self_review.md

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_402_fingerprint.py -x -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

## Integration boundary proven
**Upstream:** run_config.ingestion provides gitignore_mode and detect_phantom_paths settings
**Downstream:** repo_inventory.json consumed by W2-W9 workers, now includes gitignored_files and phantom_paths
**Contract:** All new fields are additive; existing consumers unaffected by backward-compatible paths field

## Evidence Location
`reports/agents/agent_d/TC-1024_1025/evidence.md`

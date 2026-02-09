---
id: TC-1022
title: "Exhaustive documentation discovery (remove extension filters)"
status: Done
priority: Normal
owner: "agent-d"
updated: "2026-02-07"
tags: ["w1", "discovery", "ingestion", "exhaustive"]
depends_on: ["TC-1020", "TC-1021"]
allowed_paths:
  - plans/taskcards/TC-1022_exhaustive_doc_discovery.md
  - src/launch/workers/w1_repo_scout/discover_docs.py
  - tests/unit/workers/test_tc_403_discover_docs.py
  - tests/unit/workers/test_tc_400_repo_scout.py
  - reports/agents/agent_d/TC-1022_1023/evidence.md
  - reports/agents/agent_d/TC-1022_1023/self_review.md
evidence_required:
  - reports/agents/agent_d/TC-1022_1023/evidence.md
  - reports/agents/agent_d/TC-1022_1023/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1022 — Exhaustive documentation discovery

## Objective
Modify `discover_docs.py` to record ALL files in the repository (not just `.md`/`.rst`/`.txt`), adding binary detection, `file_extension` and `file_size_bytes` fields, and removing the 50-line content scan limit.

## Problem Statement
The existing documentation discovery only records files with documentation-related extensions (`.md`, `.rst`, `.txt`), meaning the pipeline loses visibility of source code files, config files, and binary assets. This limits downstream workers' ability to understand the full repo structure.

## Required spec references
- specs/02_repo_ingestion.md (Exhaustive file recording, TC-1020)
- specs/03_evidence_and_truthlock.md (Evidence completeness)
- specs/05_example_curation.md (Example discovery integration)
- specs/21_worker_contracts.md (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic output)

## Scope

### In scope
- Remove extension-based filtering from `discover_documentation_files()` (extensions used for SCORING only)
- Record ALL text-readable files with full metadata
- Record binary files with `is_binary: true`, `doc_type: "binary"`, `relevance_score: 10`
- Add `file_extension`, `file_size_bytes`, `is_binary` fields to every output entry
- Remove 50-line content scan limit in `check_content_based_detection()` (full file scan)
- Add `DOC_EXTENSIONS`, `BINARY_EXTENSIONS` constants
- Add `is_binary_file()` function
- Update `build_discovered_docs_artifact()` to include `binary_count` in summary
- Update tests for new behavior

### Out of scope
- Changes to `discover_examples.py` (handled by TC-1023)
- Changes to W2/W3/W4 workers
- Schema changes (handled by TC-1020/TC-1021)

## Inputs
- Existing `discover_docs.py` with extension-based filtering
- Existing `test_tc_403_discover_docs.py` tests
- specs/02_repo_ingestion.md updated by TC-1020

## Outputs
- Modified `discover_docs.py` with exhaustive discovery
- Updated `test_tc_403_discover_docs.py` with new test classes
- Updated `test_tc_400_repo_scout.py` for integration test compatibility

## Allowed paths
- plans/taskcards/TC-1022_exhaustive_doc_discovery.md
- src/launch/workers/w1_repo_scout/discover_docs.py
- tests/unit/workers/test_tc_403_discover_docs.py
- tests/unit/workers/test_tc_400_repo_scout.py
- reports/agents/agent_d/TC-1022_1023/evidence.md
- reports/agents/agent_d/TC-1022_1023/self_review.md

### Allowed paths rationale
TC-1022 modifies the documentation discovery module and its tests to implement exhaustive file recording.

## Implementation steps

### Step 1: Add constants and helper functions
Add `DOC_EXTENSIONS`, `BINARY_EXTENSIONS` sets and `is_binary_file()` function to `discover_docs.py`.

### Step 2: Update check_content_based_detection
Remove 50-line limit; scan full file content for keyword detection.

### Step 3: Rewrite discover_documentation_files
Record ALL files: binary files with `is_binary: true`, non-doc-extension files with reduced score, doc-extension files with full scoring.

### Step 4: Update build_discovered_docs_artifact
Add `binary_count` to discovery summary.

### Step 5: Update tests
Rename/update existing tests for new behavior. Add `TestBinaryDetection` and `TestExhaustiveDiscovery` test classes.

### Step 6: Fix integration test
Update `test_no_docs_no_examples` in `test_tc_400_repo_scout.py` to expect non-zero docs_found.

## Failure modes

### Failure mode 1: Binary files incorrectly classified as text
**Detection:** Test assertions for binary detection fail
**Resolution:** Verify BINARY_EXTENSIONS set covers common binary formats; check null byte heuristic
**Spec/Gate:** specs/02_repo_ingestion.md binary assets discovery

### Failure mode 2: Relevance scoring regression
**Detection:** Existing tests for doc relevance scores fail
**Resolution:** Ensure DOC_EXTENSIONS files retain original scoring logic; non-doc files get reduced score
**Spec/Gate:** specs/02_repo_ingestion.md relevance scoring

### Failure mode 3: Non-deterministic output ordering
**Detection:** Determinism tests fail on repeated runs
**Resolution:** Ensure all file iteration uses sorted() and stable sort keys
**Spec/Gate:** specs/10_determinism_and_caching.md

## Task-specific review checklist
1. [x] DOC_EXTENSIONS includes all standard doc formats (.md, .rst, .txt, .adoc, .html, .htm)
2. [x] BINARY_EXTENSIONS includes common binary formats (.png, .jpg, .gif, .pdf, .zip, etc.)
3. [x] is_binary_file() uses both extension check and null byte heuristic
4. [x] All output entries include file_extension, file_size_bytes, is_binary fields
5. [x] Binary files get relevance_score: 10 and doc_type: "binary"
6. [x] Non-doc-extension text files get reduced score (max(score - 20, 10))
7. [x] Content-based detection only applied to DOC_EXTENSIONS files
8. [x] Full file scan (no 50-line limit) for content-based keyword detection
9. [x] build_discovered_docs_artifact includes binary_count in summary
10. [x] Tests cover binary detection, exhaustive discovery, and backward compatibility

## Deliverables
- Modified `src/launch/workers/w1_repo_scout/discover_docs.py`
- Updated `tests/unit/workers/test_tc_403_discover_docs.py`
- Updated `tests/unit/workers/test_tc_400_repo_scout.py`
- Evidence at `reports/agents/agent_d/TC-1022_1023/evidence.md`
- Self-review at `reports/agents/agent_d/TC-1022_1023/self_review.md`

## Acceptance checks
1. [x] All 64 tests in test_tc_403_discover_docs.py pass
2. [x] All tests in test_tc_400_repo_scout.py pass
3. [x] Full test suite passes (2207 passed, 12 skipped)
4. [x] Binary files correctly detected and recorded with is_binary: true
5. [x] Non-doc-extension text files recorded with reduced relevance score
6. [x] Full file content scan (no 50-line limit) working
7. [x] Deterministic output ordering maintained

## Preconditions / dependencies
- TC-1020 complete (specs updated for exhaustive ingestion)
- TC-1021 complete (run_config schema + model updated)

## Test plan
1. Test binary file detection via extension and null byte heuristic
2. Test exhaustive discovery records .py, .yaml, .json files
3. Test full file scan detects keywords beyond line 50
4. Test relevance scoring: doc extensions vs non-doc extensions
5. Test backward compatibility with existing scoring logic

## Self-review

### 12D Checklist
1. **Determinism:** File iteration uses sorted(); output sorted by (-relevance_score, path)
2. **Dependencies:** No new dependencies; only logic changes in existing module
3. **Documentation:** Updated module docstring and inline comments for TC-1022
4. **Data preservation:** All files now recorded; no data loss. Binary files safely handled.
5. **Deliberate design:** Extension-based filtering removed for recording but kept for scoring. Binary detection uses dual approach (extension + null byte).
6. **Detection:** Tests cover binary detection, exhaustive discovery, and full scan
7. **Diagnostics:** binary_count added to discovery summary for observability
8. **Defensive coding:** OSError handling for file reads; null byte check with limited read (8KB)
9. **Direct testing:** 64 tests pass in test_tc_403; full suite 2207 passed
10. **Deployment safety:** Backward compatible -- existing doc files retain scoring; new files simply added
11. **Delta tracking:** Modified discover_docs.py, test_tc_403, test_tc_400
12. **Downstream impact:** W2/W3 see more files in discovered_docs.json; no breaking changes

### Verification results
- [x] Tests: 64/64 PASS (test_tc_403_discover_docs.py)
- [x] Full suite: 2207/2207 PASS, 12 skipped
- [x] Evidence captured: reports/agents/agent_d/TC-1022_1023/

## E2E verification
```powershell
PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_403_discover_docs.py -x -v
PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests/ -x
```

**Expected results:**
- 64/64 tests pass in test_tc_403_discover_docs.py
- Full suite: 2207 passed, 12 skipped

## Integration boundary proven
**Upstream:** W1 RepoScout worker.py calls `discover_documentation_files(repo_dir)` and feeds results to `build_discovered_docs_artifact()`.

**Downstream:** `discovered_docs.json` is consumed by W2 FactsBuilder for evidence extraction. The new exhaustive format adds fields but does not remove any existing fields.

**Contract:**
- Output format: List of dicts with path, doc_type, relevance_score, file_extension, file_size_bytes, is_binary
- Binary files: is_binary=True, doc_type="binary", relevance_score=10
- Non-doc text files: reduced score (max(score - 20, 10))
- Deterministic ordering: sorted by (-relevance_score, path)

## Evidence Location
`reports/agents/agent_d/TC-1022_1023/evidence.md`

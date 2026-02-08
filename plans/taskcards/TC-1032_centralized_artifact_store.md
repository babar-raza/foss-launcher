---
id: TC-1032
title: "Centralized ArtifactStore Class"
status: In-Progress
priority: Normal
owner: agent-f2
updated: "2026-02-07"
tags: ["infrastructure", "io", "phase-3"]
depends_on: []
allowed_paths:
  - src/launch/io/artifact_store.py
  - src/launch/io/__init__.py
  - tests/unit/io/**
  - plans/taskcards/TC-1032_*
  - reports/agents/agent_f2/TC-1032/**
evidence_required: true
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1032 -- Centralized ArtifactStore Class

## Objective
Create a centralized ArtifactStore class that provides unified artifact loading, writing, and event emission, eliminating the 14+ duplicated `load_<artifact>()` functions and 9+ duplicated `emit_event()` calls across workers.

## Problem Statement
Every worker (W1 through W9) contains its own copy of `emit_event()`, each nearly identical but with minor inconsistencies (some use `Event` model objects, some use plain dicts; some pass `ensure_ascii=False`, some don't). Similarly, workers like W5 have 4 separate `load_page_plan()`, `load_product_facts()`, `load_snippet_catalog()`, `load_evidence_map()` functions that all do the same thing: check exists, open file, json.load, wrap error. This duplication violates DRY and creates maintenance burden where a fix in one worker may not propagate to others.

## Required spec references
- specs/10_determinism_and_caching.md (Deterministic JSON output)
- specs/11_state_and_events.md (Event log format and append-only semantics)
- specs/21_worker_contracts.md (Worker artifact contracts)
- specs/29_project_repo_structure.md (Run directory layout)

## Scope

### In scope
- Create `src/launch/io/artifact_store.py` with `ArtifactStore` class
- Provide `load_artifact()`, `load_artifact_or_default()`, `write_artifact()`, `emit_event()`, `artifact_path()`, `exists()` methods
- Reuse existing `atomic_write_json`, `sha256_bytes`, schema validation utilities
- Create comprehensive test suite at `tests/unit/io/test_artifact_store.py`
- Update `src/launch/io/__init__.py` to export ArtifactStore

### Out of scope
- Migrating existing workers to use ArtifactStore (future taskcards)
- Modifying existing io files (atomic.py, hashing.py, schema_validation.py)
- Removing existing per-worker emit_event/load functions (breaking change, deferred)

## Inputs
- Existing patterns from `src/launch/io/atomic.py` (atomic writes)
- Existing patterns from `src/launch/io/hashing.py` (sha256_bytes)
- Existing patterns from `src/launch/io/schema_validation.py` (validate, load_schema)
- Existing emit_event patterns from 9 worker modules
- Existing load_artifact patterns from W5, W7, W8 workers

## Outputs
- `src/launch/io/artifact_store.py` -- ArtifactStore class
- `src/launch/io/__init__.py` -- Updated with ArtifactStore export
- `tests/unit/io/test_artifact_store.py` -- 33 test cases
- `reports/agents/agent_f2/TC-1032/evidence.md` -- Evidence bundle
- `reports/agents/agent_f2/TC-1032/self_review.md` -- 12D self-review

## Allowed paths
- src/launch/io/artifact_store.py
- src/launch/io/__init__.py
- tests/unit/io/**
- plans/taskcards/TC-1032_*
- reports/agents/agent_f2/TC-1032/**

### Allowed paths rationale
TC-1032 creates a NEW file (artifact_store.py) in the io module, adds an export to __init__.py, and writes tests. This is allowed per plan governance: "TC-1030/1031/1032 create NEW files (not modify existing)". The __init__.py change is minimal (adding one import/export line).

## Implementation steps

### Step 1: Analyze existing patterns
Read all 9 worker emit_event implementations and all load_artifact patterns to identify common interface.

### Step 2: Create ArtifactStore class
Create `src/launch/io/artifact_store.py` with:
- `__init__(run_dir, schemas_dir=None)` - constructor
- `artifact_path(name)` - path computation
- `exists(name)` - existence check
- `load_artifact(name, validate_schema=True)` - JSON load with optional schema validation
- `load_artifact_or_default(name, default, validate_schema=True)` - safe load
- `write_artifact(name, data, schema_id=None)` - atomic JSON write returning index entry
- `emit_event(event_type, payload, run_id=None, trace_id=None, span_id=None)` - event emission

### Step 3: Update __init__.py
Add `from .artifact_store import ArtifactStore` and `__all__` export.

### Step 4: Write tests
Create 33 tests covering all methods, error cases, determinism, and schema validation.

### Step 5: Verify
Run full test suite to confirm no regressions.

## Failure modes

### Failure mode 1: Import cycle with Event model
**Detection:** ImportError at module load time mentioning circular import
**Resolution:** Use lazy import inside emit_event method body (already implemented)
**Spec/Gate:** Python import resolution

### Failure mode 2: atomic_write_json path validation rejects artifact writes
**Detection:** PathValidationError from atomic.py during write_artifact
**Resolution:** Set LAUNCH_TASKCARD_ENFORCEMENT=disabled for local dev; in production the run_dir is under output/ which is not protected
**Spec/Gate:** Guarantee B (path validation)

### Failure mode 3: Schema validation breaks existing tests
**Detection:** ValueError from jsonschema during load_artifact
**Resolution:** validate_schema defaults to True but is skippable; when schemas_dir is None, validation is silently skipped
**Spec/Gate:** specs/schemas/*.schema.json

## Task-specific review checklist
1. [x] ArtifactStore reuses existing atomic.py functions (no duplication)
2. [x] ArtifactStore reuses existing hashing.py functions (no duplication)
3. [x] ArtifactStore reuses existing schema_validation.py functions (no duplication)
4. [x] JSON output is deterministic: indent=2, sort_keys=True, ensure_ascii=False
5. [x] Event emission follows events.ndjson append-only pattern
6. [x] No modification to existing io files (atomic.py, hashing.py, etc.)
7. [x] All 33 tests pass
8. [x] Full test suite (2004 tests) passes with no regressions

## Deliverables
- `src/launch/io/artifact_store.py` -- ArtifactStore class (268 lines)
- `src/launch/io/__init__.py` -- Updated with export (4 lines)
- `tests/unit/io/test_artifact_store.py` -- 33 test cases (339 lines)
- `plans/taskcards/TC-1032_centralized_artifact_store.md` -- This taskcard
- `reports/agents/agent_f2/TC-1032/evidence.md` -- Evidence
- `reports/agents/agent_f2/TC-1032/self_review.md` -- 12D self-review

## Acceptance checks
1. [x] ArtifactStore class exists at src/launch/io/artifact_store.py
2. [x] All 6 public methods implemented and tested
3. [x] 33/33 artifact_store tests pass
4. [x] 2004/2004 full suite tests pass (no regressions)
5. [x] JSON output is byte-for-byte deterministic
6. [x] Event emission matches existing events.ndjson format
7. [x] Schema validation is optional and gracefully skipped when no schema

## Preconditions / dependencies
- Python virtual environment with jsonschema installed
- Existing io module (atomic.py, hashing.py, schema_validation.py)
- No blocking dependencies on other taskcards

## Test plan
1. Test load_artifact happy path: write JSON manually, load via store, verify match
2. Test load_artifact FileNotFoundError: attempt load of missing artifact
3. Test load_artifact_or_default: verify default returned when file missing
4. Test write_artifact: write data, verify file on disk, verify SHA-256 in entry
5. Test determinism: write same data twice, verify byte-identical output
6. Test emit_event: verify NDJSON line appended with required fields
7. Test schema validation: verify valid data passes, invalid data raises ValueError

## Self-review

### 12D Checklist
1. **Determinism:** JSON output uses sort_keys=True, indent=2, ensure_ascii=False + trailing newline. SHA-256 computed from written bytes. Tests verify byte-for-byte determinism.
2. **Dependencies:** No new dependencies. Reuses jsonschema (already in project), atomic.py, hashing.py, schema_validation.py.
3. **Documentation:** Comprehensive docstrings on every method. Module-level docstring explains purpose and spec references.
4. **Data preservation:** Read-only for loads; atomic writes for writes (temp + rename). No data corruption risk.
5. **Deliberate design:** Centralized class chosen over utility functions for encapsulation of run_dir state. Optional schema validation to maintain backward compatibility.
6. **Detection:** FileNotFoundError for missing artifacts. ValueError for schema violations. JSONDecodeError for malformed files.
7. **Diagnostics:** Event emission to events.ndjson provides audit trail. SHA-256 in write entries enables integrity verification.
8. **Defensive coding:** Separate exists() check before load. Default parameter in load_artifact_or_default. Lazy import of Event model to avoid circular dependencies.
9. **Direct testing:** 33 unit tests covering all methods, error paths, determinism, and schema validation.
10. **Deployment safety:** New file only; no modification to existing code. Workers can adopt ArtifactStore incrementally.
11. **Delta tracking:** Created 1 new source file, updated 1 export, created 1 test file. No existing code modified.
12. **Downstream impact:** Enables future worker refactoring (TC-1033+). No existing behavior changed.

### Verification results
- [x] Tests: 33/33 PASS (artifact_store tests)
- [x] Full suite: 2004/2004 PASS (no regressions)
- [x] Evidence captured: reports/agents/agent_f2/TC-1032/

## E2E verification
```bash
# Run artifact store tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_artifact_store.py -v

# Run full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Expected artifacts:**
- `tests/unit/io/test_artifact_store.py` -- 33 tests all passing
- `src/launch/io/artifact_store.py` -- ArtifactStore class with 6 public methods

**Expected results:**
- 33/33 artifact_store tests pass
- 2004/2004 full suite tests pass
- No import errors or circular dependencies

## Integration boundary proven
**Upstream:** ArtifactStore consumes run_dir (Path) from the orchestrator and schemas_dir from repo_root/specs/schemas. It reads JSON files written by any upstream worker.

**Downstream:** Workers (W1-W9) can import ArtifactStore to replace their duplicated load/emit functions. The written artifacts follow the same format (indent=2, sort_keys=True, trailing newline) as existing workers.

**Contract:**
- load_artifact returns parsed dict, raises FileNotFoundError if missing
- write_artifact returns {path, sha256, size} entry dict
- emit_event appends NDJSON line to events.ndjson
- All JSON output is deterministic (specs/10_determinism_and_caching.md)

## Evidence Location
`reports/agents/agent_f2/TC-1032/evidence.md`

---
id: TC-1033
title: "Write-time validation + worker migration to ArtifactStore"
status: Done
priority: Normal
owner: agent-f
updated: "2026-02-07"
tags: ["infrastructure", "refactoring", "artifact-store"]
depends_on: ["TC-1030", "TC-1031", "TC-1032"]
allowed_paths:
  - plans/taskcards/TC-1033_write_time_validation_migration.md
  - src/launch/io/atomic.py
  - src/launch/workers/w1_repo_scout/worker.py
  - src/launch/workers/w2_facts_builder/worker.py
  - src/launch/workers/w3_snippet_curator/worker.py
  - src/launch/workers/w4_ia_planner/worker.py
  - src/launch/workers/w5_section_writer/worker.py
  - src/launch/workers/w6_linker_and_patcher/worker.py
  - src/launch/workers/w7_validator/worker.py
  - src/launch/workers/w8_fixer/worker.py
  - src/launch/workers/w9_pr_manager/worker.py
  - reports/agents/agent_f/TC-1033/evidence.md
  - reports/agents/agent_f/TC-1033/self_review.md
evidence_required:
  - reports/agents/agent_f/TC-1033/evidence.md
  - reports/agents/agent_f/TC-1033/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1033 -- Write-Time Validation + Worker Migration to ArtifactStore

## Objective
Enhance atomic_write_json() with optional write-time schema validation and migrate all 9 workers (W1-W9) to use the centralized ArtifactStore class for artifact I/O and event emission, eliminating duplicated load/emit helper functions across the codebase.

## Problem Statement
The codebase had 9 workers each containing near-identical emit_event() functions (14+ copies) and duplicated load_<artifact>() functions (10+ copies). This duplication violates DRY, makes maintenance expensive, and increases the risk of inconsistent behavior across workers. TC-1032 introduced a centralized ArtifactStore class; this taskcard completes the migration so all workers use it.

## Required spec references
- specs/10_determinism_and_caching.md (Deterministic output guarantees)
- specs/11_state_and_events.md (Event log format and emission)
- specs/21_worker_contracts.md (Worker artifact contracts)
- specs/29_project_repo_structure.md (Run directory layout)

## Scope

### In scope
- Part A: Add optional schema_path parameter to atomic_write_json() for write-time validation
- Part B: Migrate all 9 workers (W1-W9) to delegate to ArtifactStore for:
  - Event emission (emit_event functions)
  - Artifact loading (load_* functions)
  - Artifact hashing (emit_artifact_written_event functions)
- Preserve all existing function signatures for backward compatibility
- Maintain all existing test passing status (2235 tests)

### Out of scope
- Changing any external worker API (signatures, return values, error types)
- Adding new tests (existing 2235 tests provide full coverage)
- Modifying ArtifactStore itself (TC-1032 deliverable)
- Removing worker-specific error types

## Inputs
- src/launch/io/atomic.py (existing atomic write functions)
- src/launch/io/artifact_store.py (TC-1032 ArtifactStore class)
- src/launch/workers/w{1-9}*/worker.py (9 worker files with duplicated helpers)
- 2235 existing tests

## Outputs
- Enhanced atomic_write_json() with optional schema_path parameter
- 9 migrated worker files using ArtifactStore for load/emit/hash operations
- All 2235 tests passing (verified)

## Allowed paths
- plans/taskcards/TC-1033_write_time_validation_migration.md
- src/launch/io/atomic.py
- src/launch/workers/w1_repo_scout/worker.py
- src/launch/workers/w2_facts_builder/worker.py
- src/launch/workers/w3_snippet_curator/worker.py
- src/launch/workers/w4_ia_planner/worker.py
- src/launch/workers/w5_section_writer/worker.py
- src/launch/workers/w6_linker_and_patcher/worker.py
- src/launch/workers/w7_validator/worker.py
- src/launch/workers/w8_fixer/worker.py
- src/launch/workers/w9_pr_manager/worker.py
- reports/agents/agent_f/TC-1033/evidence.md
- reports/agents/agent_f/TC-1033/self_review.md

### Allowed paths rationale
TC-1033 modifies the atomic I/O layer and all 9 worker modules to centralize artifact operations through ArtifactStore.

## Implementation steps

### Step 1: Part A - Add schema_path to atomic_write_json()
Added optional `schema_path: Optional[str] = None` parameter to `atomic_write_json()`. When provided, validates data against the JSON schema BEFORE writing. If validation fails, raises ValueError without writing invalid data. Backward compatible (defaults to None).

### Step 2: Part B - Worker migration pattern
For each worker, applied the same migration pattern:
1. Added `from ...io.artifact_store import ArtifactStore` import
2. Replaced emit_event() function body to delegate to `ArtifactStore.emit_event()`
3. Replaced load_* function bodies to delegate to `ArtifactStore.load_artifact()`
4. Replaced emit_artifact_written_event() to use `sha256_bytes()` from centralized hashing
5. Preserved all function signatures and error types for backward compatibility

### Step 3: Worker-by-worker migration
Migrated in order: W5, W4, W6, W7, W8, W1, W2, W3, W9. Ran relevant tests after each migration to catch regressions immediately.

### Step 4: Full test suite verification
Ran complete test suite: 2235 passed, 12 skipped, 0 failures.

## Failure modes

### Failure mode 1: Worker function signature change breaks callers
**Detection:** ImportError or TypeError in tests importing worker functions
**Resolution:** Keep all function signatures identical; only change internal implementation
**Spec/Gate:** specs/21_worker_contracts.md

### Failure mode 2: Error type conversion breaks error handling
**Detection:** Tests expecting SectionWriterError get FileNotFoundError instead
**Resolution:** Wrap ArtifactStore calls with try/except to convert exceptions to worker-specific types
**Spec/Gate:** specs/28_coordination_and_handoffs.md

### Failure mode 3: Event format change breaks event consumers
**Detection:** Event parsing fails or events.ndjson has different structure
**Resolution:** ArtifactStore.emit_event() produces compatible format; verify with existing tests
**Spec/Gate:** specs/11_state_and_events.md

## Task-specific review checklist
1. [x] atomic_write_json schema_path parameter is backward compatible (defaults to None)
2. [x] All 9 worker emit_event functions delegate to ArtifactStore
3. [x] All load_* functions preserve worker-specific error types
4. [x] No external API changes (function signatures, return types unchanged)
5. [x] W7/W8 parent_span_id preserved in payload when present
6. [x] Centralized sha256_bytes used instead of per-worker hashlib calls
7. [x] All 2235 tests pass with no failures
8. [x] No new dependencies introduced

## Deliverables
- Modified src/launch/io/atomic.py with schema_path parameter
- 9 migrated worker files (w1 through w9)
- Evidence at reports/agents/agent_f/TC-1033/evidence.md
- Self-review at reports/agents/agent_f/TC-1033/self_review.md

## Acceptance checks
1. [x] atomic_write_json() accepts optional schema_path parameter
2. [x] All 9 workers use ArtifactStore for event emission
3. [x] All load functions delegate to ArtifactStore.load_artifact
4. [x] No external API changes (backward compatible)
5. [x] All 2235 tests pass (0 failures)
6. [x] Evidence bundle created with all artifacts

## Preconditions / dependencies
- TC-1030: Typed artifact models foundation (Complete)
- TC-1031: Typed worker models W3-W9 (Complete)
- TC-1032: Centralized ArtifactStore class (Complete)

## Test plan
1. Run each worker's tests after migration (verified per-worker)
2. Run full test suite: 2235 passed, 12 skipped, 0 failures
3. Verify backward compatibility of atomic_write_json (13 tests pass)
4. Verify ArtifactStore tests still pass (33 tests pass)

## Self-review

### 12D Checklist

1. **Determinism:** ArtifactStore.emit_event() uses ensure_ascii=False, sort_keys=True for consistent JSON. All load operations are deterministic (file read).

2. **Dependencies:** No new dependencies. Reuses existing ArtifactStore (TC-1032), hashing module, schema_validation module.

3. **Documentation:** Added TC-1033 docstring comments to all migrated functions explaining the delegation pattern.

4. **Data preservation:** All worker-specific error types preserved via try/except wrappers. No data transformation or loss.

5. **Deliberate design:** Chose delegation pattern (keep wrapper functions, delegate to ArtifactStore) to preserve backward compatibility with 50+ test imports.

6. **Detection:** Existing tests (2235) catch any behavioral changes. Per-worker test runs after each migration.

7. **Diagnostics:** ArtifactStore centralizes logging. Worker-specific error messages preserved.

8. **Defensive coding:** schema_path validation happens BEFORE write (no invalid data written). Exception conversion preserves worker-specific error types.

9. **Direct testing:** 2235 tests pass covering all migrated code paths.

10. **Deployment safety:** Pure internal refactoring; no external API changes. Can be verified with existing test suite.

11. **Delta tracking:** Modified 10 files: atomic.py + 9 worker files. All changes are delegation rewrites, not behavioral changes.

12. **Downstream impact:** No user-facing changes. Workers continue to produce identical output. Event format compatible with existing consumers.

### Verification results
- [x] Tests: 2235/2235 PASS (12 skipped)
- [x] All worker tests pass individually
- [x] Evidence captured: reports/agents/agent_f/TC-1033/

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Expected results:**
- 2235 passed, 12 skipped, 0 failures

## Integration boundary proven
**Upstream:** ArtifactStore (TC-1032) provides centralized load_artifact(), write_artifact(), emit_event() methods.

**Downstream:** All 9 workers (W1-W9) now delegate to ArtifactStore instead of using duplicated inline implementations. Orchestrator calls workers with identical signatures.

**Contract:**
- Worker function signatures unchanged
- Worker-specific error types preserved
- Event format compatible (NDJSON with required fields)
- Artifact loading returns same data types (dict)

## Evidence Location
`reports/agents/agent_f/TC-1033/evidence.md`

# TC-3355 — W8 Hardening Healing Evidence

**Date**: 2026-02-28
**Taskcard**: TC-3355
**Healing plan**: `plans/healing/12_tc3350_w8_hardening_healing.md`

## Changes Summary

### SR-01: Fix New-Heading Crash Path + Fail-Fast Schema Validation
- **GAP-01 (CRITICAL)**: `_generate_update_patches_for_existing()` now distinguishes between changed headings (→ `update_by_anchor`) and new headings absent from existing file (→ `update_file_range` append at end). Previously all headings used `update_by_anchor` which crashed with `LinkerPatchConflictError("Anchor not found")` for new headings.
- **GAP-02 (HIGH)**: `_validate_patch_bundle()` now raises `LinkerPatchConflictError` on schema validation failure instead of silently logging error. Bundle is written BEFORE validation so artifact is available for inspection on failure.
- **Tests**: 4 new tests (TestNewHeadingAppend) + 1 updated test (test_validate_catches_invalid_bundle_raises)

### SR-02: Integration Test + Telemetry Events
- **GAP-06 (HIGH)**: Integration test `test_existing_file_update_through_generate_patches` verifies full existing-file chain: existing file with modified section + new section → no `create_file` patches, correct `update_by_anchor` for changed section, correct `update_file_range` for new section.
- **GAP-03 (MEDIUM)**: 4 telemetry event constants defined locally in worker.py (`EVENT_PATCH_ENGINE_STARTED`, `EVENT_PATCH_ENGINE_COMPLETED`, `EVENT_PATCH_APPLIED`, `EVENT_PATCH_SKIPPED`). Defined locally because `src/launch/models/event.py` is owned by TC-250. Events emitted at: entry (STARTED), per-patch (APPLIED/SKIPPED), before completion (COMPLETED).
- **Tests**: 3 new tests (TestExistingFileIntegration, TestTelemetryEvents)

### SR-03: Schema Caching + Conflict Classification Hardening
- **GAP-05 (LOW)**: Module-level `_PATCH_BUNDLE_SCHEMA` cache with `_get_patch_bundle_schema()` helper. Schema loaded from disk once, then served from cache.
- **GAP-07 (LOW)**: `_classify_conflict()` now uses `isinstance(error, FileNotFoundError)` before string matching. String patterns widened (e.g., `"anchor" in msg and "not found" in msg` instead of `"anchor not found" in msg`).
- **Tests**: 4 new tests (TestSchemaCaching, TestClassifyConflictHardened)

### SR-04: Missing Phase 0 Audit + Phase 1 Design Reports
- `reports/ops/w8_audit_20260228.md`: All 7 spec mismatches documented with code locations, spec references, severity, risk assessment, dependency graph.
- `reports/ops/w8_design_20260228.md`: Per-mismatch design decisions, alternatives considered, key decisions, GAPs found post-ship, dependency graph.

## Files Modified

| File | Changes |
|------|---------|
| `src/launch/workers/w8_linker_and_patcher/worker.py` | +~65 lines: GAP-01 new-heading branch, GAP-02 fail-fast, GAP-05 schema cache, GAP-07 classify hardening, GAP-03 telemetry constants + 4 emit calls |
| `tests/unit/workers/test_w8_hardening.py` | +~120 lines: 11 new tests (4 GAP-01 + 1 GAP-02 update + 1 GAP-05 + 3 GAP-07 + 1 GAP-06 + 2 GAP-03) |
| `plans/taskcards/TC-3355_w8_hardening_healing.md` | NEW taskcard |
| `plans/taskcards/INDEX.md` | +1 line (TC-3355 entry) |
| `plans/healing/12_tc3350_w8_hardening_healing.md` | SR-01..SR-04 status → Done |
| `reports/ops/w8_audit_20260228.md` | NEW |
| `reports/ops/w8_design_20260228.md` | NEW |

## Test Results

```
tests/unit/workers/test_w8_hardening.py: 37 passed (26 original + 11 new)
tests/unit/workers/test_tc_450_linker_and_patcher.py: 17 passed (no regressions)
tests/unit/workers/test_w6_linker_edge_cases.py: 26 passed (no regressions)
tests/unit/workers/test_w6_content_export.py: 3 passed (no regressions)

Full suite: 7612 passed, 13 skipped, 0 failed
```

## Evidence Commands Run

```bash
# Targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w8_hardening.py -x -v
# Regression tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_450_linker_and_patcher.py tests/unit/workers/test_w6_linker_edge_cases.py tests/unit/workers/test_w6_content_export.py -x -v
# Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
# Taskcard validation
.venv/Scripts/python.exe tools/validate_taskcards.py | grep TC-3355  # → [OK]
```

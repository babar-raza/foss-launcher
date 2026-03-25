# TC-3250 Implementation Report — SHA-Scoped Two-Layer Worker Cache

**Date**: 2026-02-27
**Agent**: agent_b
**Session**: dreamy-brewing-rocket (implementation) + healing session
**Status**: Complete

---

## Summary

Implemented a two-layer worker cache in the state store:
- **RAW layer** (`raw/<sha>/w1/`): W1 artifacts keyed by SHA only; stable extraction, reused across interpretation changes
- **DERIVED layer** (`derived/<sha>/<sig>/`): W2/W3/W4 artifacts keyed by (SHA, interpretation_signature); invalidated when engine/ruleset/templates logic changes
- **Legacy layout** (`artifacts/<sha>/`): W5/W8/W9 still published here (unchanged behavior)

Post-implementation healing (5 cards) addressed gaps in test coverage, observability, evidence accuracy, and ENGINE_VERSION drift detection.

---

## Files Modified

| File | Change | Source |
|------|--------|--------|
| `src/launch/provenance/provenance.py` | Added `ENGINE_VERSION = "1.0.0"` and `compute_interpretation_signature()` | TC-3250 |
| `src/launch/provenance/__init__.py` | Exported `ENGINE_VERSION`, `compute_interpretation_signature` | TC-3250 |
| `src/launch/state_store/store.py` | Added 8 new functions, 3 event constants, extracted `_ARTIFACT_WORKER_MAP`, updated `publish_run_artifacts`, added 2 debug log lines (SR-05), TODO comment (SR-05) | TC-3250 + SR-05 |
| `src/launch/state_store/__init__.py` | Exported all new symbols | TC-3250 |
| `src/launch/cli/main.py` | Updated Step 4 (two-layer hydration) + Step 12 (unconditional raw/derived publish) | TC-3250 |
| `tests/unit/state_store/test_store_two_layer.py` | New — 35 tests (6 classes) | TC-3250 + SR-03 + SR-05 |
| `tests/unit/cli/test_drive_two_layer.py` | New — 12 tests (4 classes) | TC-3250 |
| `tests/unit/state_store/test_store.py` | Updated 3 tests for new `publish_run_artifacts` behavior | TC-3250 |
| `tests/unit/cli/test_drive.py` | Updated 2 tests + added 3 negative regression tests (SR-02) | TC-3250 + SR-02 |
| `tests/integration/test_drive_e2e.py` | Updated `test_publish_after_run_round_trips` | TC-3250 |
| `tools/check_engine_version_drift.py` | New — CI-compatible ENGINE_VERSION drift detection | SR-04 |
| `src/launch/provenance/.engine_version_lock.json` | New — lockfile for drift detection | SR-04 |
| `tests/unit/provenance/test_engine_version_drift.py` | New — 7 tests | SR-04 |

---

## New API

### `src/launch/provenance/provenance.py`

```python
ENGINE_VERSION = "1.0.0"  # bump when W2/W3/W4 interpretation changes

def compute_interpretation_signature(run_config: Dict[str, Any]) -> str:
    """12-char SHA-256 prefix of engine_version + ruleset_version + templates_version."""
```

### `src/launch/state_store/store.py` — new functions

```python
# Path helpers
get_raw_dir(store_root, store_key, repo_sha) -> Path
get_derived_dir(store_root, store_key, repo_sha, sig) -> Path

# Finders (return None if not found)
find_raw_artifact_set(store_root, store_key, repo_sha) -> Optional[Path]
find_derived_artifact_set(store_root, store_key, repo_sha, sig) -> Optional[Path]

# Hydrators (return file count)
hydrate_from_raw(run_dir, raw_set) -> int
hydrate_from_derived(run_dir, derived_set) -> int

# Publishers (return file count, safe to call on partial runs)
publish_raw_artifacts(store_root, store_key, repo_sha, run_dir) -> int
publish_derived_artifacts(store_root, store_key, repo_sha, sig, run_dir) -> int

# Event constants
STORE_HYDRATE_RAW_USED = "STORE_HYDRATE_RAW_USED"
STORE_HYDRATE_DERIVED_USED = "STORE_HYDRATE_DERIVED_USED"
STORE_DERIVED_MISS_SIGNATURE = "STORE_DERIVED_MISS_SIGNATURE"
```

---

## Test Results

### Final counts (after healing)

```
Command: .venv/Scripts/python.exe -m pytest tests/unit/state_store/ tests/unit/cli/test_drive.py
         tests/unit/cli/test_drive_two_layer.py tests/integration/test_drive_e2e.py
         tests/unit/provenance/ --tb=short
Result: 137 passed, 0 failed
```

### Full suite

```
Command: .venv/Scripts/python.exe -m pytest tests/ --tb=no
Result: 7460 passed, 13 skipped, 6 failed (slug tests — pre-existing, unrelated to TC-3250)
Baseline: 7296 passed (TC-3220)
```

### Per-file test reconciliation

| File | Total tests | New | Updated | Source |
|------|-------------|-----|---------|--------|
| `test_store_two_layer.py` | 35 | 35 | — | TC-3250 (27) + SR-03 (6) + SR-05 (2) |
| `test_drive_two_layer.py` | 12 | 12 | — | TC-3250 |
| `test_drive.py` | 30 | 3 | 2 | SR-02 (3 new) + TC-3250 (2 updated) |
| `test_store.py` | 31 | 0 | 3 | TC-3250 (3 updated) |
| `test_drive_e2e.py` | 5 | 0 | 1 | TC-3250 (1 updated) |
| `test_engine_version_drift.py` | 7 | 7 | — | SR-04 |
| **Totals** | **120** | **57** | **6** | |

**Note**: The original report claimed +54 new tests (7350−7296). The actual delta attributable to TC-3250 was 39 new tests in the initial implementation. The discrepancy of ~15 was due to untracked test files from concurrent sessions present in the working tree. This was identified and documented in the healing plan (GAP-01). The healing cards added 18 more tests (SR-02: 3, SR-03: 6, SR-04: 7, SR-05: 2), bringing the total attributable new tests to 57.

---

## Healing Cards Executed

| Card | Gap(s) | Status | Summary |
|------|--------|--------|---------|
| SR-01 | GAP-01, GAP-02 | Done | Reconciled test counts; rewrote evidence with honest scores |
| SR-02 | GAP-03 | Done | 3 negative regression tests proving W1/W2 skip |
| SR-03 | GAP-06 | Done | 6 edge-case resilience tests (empty dirs, corrupt JSON, etc.) |
| SR-04 | GAP-04 | Done | `tools/check_engine_version_drift.py` + lockfile + 7 tests |
| SR-05 | GAP-05, GAP-07 | Done | 2 debug log lines + TODO comment + 2 caplog tests |

---

## Non-Negotiables Verified

| Non-Negotiable | Status |
|----------------|--------|
| `compute_interpretation_signature` is deterministic | Verified — sorted JSON keys, no timestamps, `TestInterpretationSignature` proves stability |
| `publish_run_artifacts` skips W1/W2/W3/W4 | Verified — guarded by `worker_id not in _RAW_WORKERS and worker_id not in _DERIVED_WORKERS`; 3 negative regression tests (SR-02) |
| `find_raw_artifact_set` returns None if no W1 files | Verified — checks for JSON files; edge cases tested (SR-03) |
| `find_derived_artifact_set` returns None for wrong sig | Verified — `test_find_derived_set_wrong_sig`; empty dirs tested (SR-03) |
| Legacy fallback in drive() Step 4 is `else` branch | Verified — `if raw_set is not None: ... else: legacy_fallback` |
| Publishing is unconditional for raw+derived | Verified — Step 12a always runs; Step 12b gated on exit_code==0 |
| `_safe_copy_file` collision detection intact | Verified — not modified |
| Old `artifacts/<sha>/` stores still hydrate | Verified — `TestBackwardCompatibilityFallback` in `test_drive_two_layer.py` |
| Write fence respected | Verified — only files in `allowed_paths` modified |
| ENGINE_VERSION drift detectable | Verified (SR-04) — `tools/check_engine_version_drift.py` + lockfile |

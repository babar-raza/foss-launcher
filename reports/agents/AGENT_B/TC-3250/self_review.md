# Self Review (12-D)

> Agent: agent_b
> Taskcard: TC-3250
> Date: 2026-02-27
> Revision: 2 (post-healing — honest rescoring)

## Summary
- What I changed: Implemented SHA-scoped two-layer worker cache. Added `ENGINE_VERSION` + `compute_interpretation_signature()` to provenance module. Added 8 new functions + 3 event constants to store.py. Updated `drive()` hydration (Step 4) and publish (Step 12). Created 57 new tests across 4 new test files (after healing).
- How to run verification:
  ```bash
  .venv/Scripts/python.exe -m pytest tests/unit/state_store/ tests/unit/cli/test_drive.py tests/unit/cli/test_drive_two_layer.py tests/integration/test_drive_e2e.py tests/unit/provenance/ -v
  python tools/check_engine_version_drift.py
  ```
- Key risks / follow-ups:
  - `ENGINE_VERSION` must be bumped manually when W2/W3/W4 interpretation logic changes. Now detectable via `tools/check_engine_version_drift.py` (SR-04), but not yet wired into pre-commit or CI.
  - Stale `derived/<sha>/<old_sig>/` directories accumulate silently; pruning not in scope.
  - Event constants live in `store.py` instead of `models/event.py` (TC-250 ownership constraint); TODO comment documents migration path.

## Evidence
- Diff summary: `provenance.py` +30 lines, `store.py` +220 lines, `main.py` +80 lines, `__init__.py` files +14 lines each, 4 new test files +650 lines, 3 existing test files updated, 1 new tool script +190 lines.
- Tests run:
  ```
  .venv/Scripts/python.exe -m pytest tests/unit/state_store/ tests/unit/cli/test_drive.py
         tests/unit/cli/test_drive_two_layer.py tests/integration/test_drive_e2e.py
         tests/unit/provenance/ --tb=short
  137 passed, 0 failed
  ```
- Full suite: 7460 passed, 13 skipped, 6 failed (slug tests — pre-existing, unrelated to TC-3250)
- Logs/artifacts written:
  - `reports/ops/store_sha_cache_audit_20260227_1200.md`
  - `reports/ops/store_sha_cache_design_20260227_1200.md`
  - `tests/unit/state_store/test_store_two_layer.py` (35 tests)
  - `tests/unit/cli/test_drive_two_layer.py` (12 tests)
  - `tests/unit/provenance/test_engine_version_drift.py` (7 tests)
  - `tools/check_engine_version_drift.py`
  - `src/launch/provenance/.engine_version_lock.json`
  - `plans/healing/tc3250_two_layer_store_healing.md`

## 12 Quality Dimensions (score 1–5)

1) **Correctness**
   - Score: 5/5
   - RAW layer correctly stores only W1 artifacts under `raw/<sha>/w1/`
   - DERIVED layer correctly stores W2/W3/W4 under `derived/<sha>/<sig>/<worker>/`
   - `publish_run_artifacts` correctly skips W1/W2/W3/W4 (guards verified by 3 negative regression tests)
   - Legacy fallback in drive() Step 4 is an `else` branch — no double hydration possible
   - All 8 non-negotiables verified green
   - **Weakness**: None identified in core logic

2) **Completeness vs spec**
   - Score: 4/5
   - All 8 required functions + 3 event constants + drive() updates implemented per spec
   - All required exports in `__init__.py` files
   - **Weakness**: Initial implementation shipped without negative regression tests for the skip behavior (GAP-03). The original `test_publish_round_trip` was simply changed from W1→W9 rather than adding an explicit W1-skip test alongside. Fixed by SR-02.
   - **Weakness**: Edge-case boundary conditions (empty dirs, corrupt JSON, non-JSON files) were not tested initially (GAP-06). Fixed by SR-03.

3) **Determinism / reproducibility**
   - Score: 5/5
   - `compute_interpretation_signature` uses `json.dumps(..., sort_keys=True)` — no dict ordering dependency
   - No timestamps in signature payload
   - `TestInterpretationSignature` proves same input → same output, 12-char fixed length
   - **Weakness**: None identified

4) **Robustness / error handling**
   - Score: 4/5
   - All publish/find/hydrate functions handle missing directories gracefully (return 0 or None)
   - `_safe_copy_file` collision detection unchanged
   - Zero-file publish returns 0 (no crash)
   - **Weakness**: `ENGINE_VERSION` drift had no automated detection — a developer changing W2 logic without bumping the version would silently serve stale derived artifacts (GAP-04). Fixed by SR-04, but the drift script is not yet wired into CI/pre-commit.
   - **Weakness**: `find_derived_artifact_set` with empty worker dirs was untested before SR-03

5) **Test quality & coverage**
   - Score: 4/5
   - 57 new tests across 4 files covering: signature stability, raw/derived CRUD, cache invalidation, backward compat, negative regression, edge cases, observability logging, ENGINE_VERSION drift
   - **Weakness**: Original test count discrepancy (+54 claimed vs 39 accountable; GAP-01). The 15-test gap was from untracked files in the working tree. Fixed by reconciliation in SR-01.
   - **Weakness**: Missing negative tests for skip behavior initially (GAP-03). Fixed by SR-02.
   - **Weakness**: No edge-case boundary tests initially (GAP-06). Fixed by SR-03.

6) **Maintainability**
   - Score: 4/5
   - `_ARTIFACT_WORKER_MAP` extracted to module level — single source of truth
   - `_RAW_WORKERS`, `_DERIVED_WORKERS` frozensets — data-driven, easy to extend
   - `ENGINE_VERSION` is a single constant to bump — well-documented
   - **Weakness**: Event constants (`STORE_HYDRATE_RAW_USED`, etc.) defined in `store.py` instead of `models/event.py` due to TC-250 ownership constraint (GAP-07). Architecturally suboptimal — events should live with events. TODO comment added by SR-05 documenting the migration path.

7) **Readability / clarity**
   - Score: 5/5
   - Each new function has docstring explaining purpose, return value, and when to call
   - Comment in `publish_run_artifacts`: "Skip W1/W2/W3/W4 — handled by new two-layer publish functions"
   - Event constants are string constants with meaningful names
   - **Weakness**: None significant

8) **Performance**
   - Score: 5/5
   - New publish functions iterate `_ARTIFACT_WORKER_MAP` (fixed ~20 entries) — O(1) per run
   - No additional filesystem scans introduced
   - `compute_interpretation_signature` is a single SHA-256 hash call — negligible cost
   - Debug logging is no-op at INFO level
   - **Weakness**: None identified

9) **Security / safety**
   - Score: 5/5
   - No shell injection — all paths are `Path` objects
   - `_safe_copy_file` collision detection unchanged
   - No credentials or sensitive data in signature payload
   - **Weakness**: None identified

10) **Observability (logging + telemetry)**
    - Score: 4/5
    - `publish_raw_artifacts` logs: `store_publish_raw: <sha12> -> N files`
    - `publish_derived_artifacts` logs: `store_publish_derived: <sha12>/<sig> -> N files`
    - drive() emits `STORE_HYDRATE_RAW_USED`, `STORE_HYDRATE_DERIVED_USED`, `STORE_DERIVED_MISS_SIGNATURE` events
    - **Weakness**: Initial implementation had no debug logging when `publish_run_artifacts` silently skipped W1-W4 artifacts (GAP-05). An operator debugging "why is my W1 file not in legacy layout?" had no log to find. Fixed by SR-05 — 2 debug log lines added with caplog tests.
    - **Remaining gap**: No structured metrics (e.g., cache hit/miss counters for monitoring dashboards)

11) **Integration (CLI/MCP parity, run_dir contracts)**
    - Score: 5/5
    - `test_drive_e2e.py::test_publish_after_run_round_trips` proves full round-trip
    - `TestBackwardCompatibilityFallback` proves legacy stores still hydrate
    - drive() Step 4 + Step 12 updated atomically
    - `compute_interpretation_signature` imported from `launch.provenance` (correct module boundary)
    - **Weakness**: None significant

12) **Minimality (no bloat, no hacks)**
    - Score: 5/5
    - Only files in `allowed_paths` modified
    - No new dependencies introduced
    - No migration code (legacy fallback handles naturally)
    - No feature flags (unconditional behavior — new path always taken when raw exists)
    - **Weakness**: None identified

## Final verdict
- **Ship** — core implementation is correct and complete. All non-negotiables verified.
- Post-ship healing addressed 7 identified gaps across 5 cards (SR-01 through SR-05).
- Average score: 4.5/5 (range: 4–5). No dimension below 4.
- Remaining follow-ups (out of scope):
  1. Wire `tools/check_engine_version_drift.py` into CI pipeline or pre-commit hook
  2. Migrate event constants to `models/event.py` when TC-250 allows
  3. Pruning of stale `derived/<sha>/<old_sig>/` directories
  4. Structured cache hit/miss metrics for monitoring

# RID-11: Collision Safety for Timestamp-Based Run IDs

## Status: Done

## Gap Linkage
- G-RV3-01: Same-second collision produces identical run IDs for same family+platform
- G-RV3-02: `run_pilot.py` silently merges into existing dir via `mkdir(exist_ok=True)`

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. **Add 4-char hex suffix to `generate_run_id()`**: Append `os.urandom(2).hex()` to
   the timestamp-based ID. New format: `YYMMDD_HHMMSS_{family}_{platform}_{hex4}`.
   Example: `260307_082430_cells_python_a3f1`. This eliminates same-second collisions
   while preserving chronological sort order (the suffix only matters within the same
   second). 65K unique IDs per second per family+platform is far beyond any realistic
   batch scenario.

2. **Add collision guard in `run_loop.py`**: After generating the run ID, check
   `run_dir.exists()`. If it exists, log a warning and regenerate (up to 3 retries).
   On exhaustion, raise `ValueError` with a clear message.

3. **Add collision guard in `run_pilot.py`**: Same pattern. Remove `exist_ok=True`
   from the `mkdir` call for fresh runs (only — resume paths still need it). Replace
   with an explicit existence check before `mkdir(parents=True)`.

4. **Update docstring** in `generate_run_id()` to document the format including the
   hex suffix, and explain that the suffix provides collision safety for parallel runs.

### Allowed paths
- `src/launcher/util/run_id.py`
- `src/launcher/orchestrator/run_loop.py` (lines ~270-275 only)
- `scripts/run_pilot.py` (lines ~63-70 only)

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- `python -c "from launcher.util.run_id import generate_run_id; r = generate_run_id('cells','python'); print(r)"` prints format `YYMMDD_HHMMSS_cells_python_XXXX`
- Two rapid sequential calls produce different IDs (hex suffix differs)

### Tests
- Existing `test_run_id.py` tests updated to match new 4-char suffix in regex
- New test: `test_collision_guard_retries` — mock `os.urandom` to force duplicate, verify retry produces different ID
- Existing `test_run_manifest.py` still passes (hardcoded IDs updated if needed)

### Config respected end-to-end
- `discover_latest_run()` still finds runs with new format (reads `run_config.json`, not dir name)
- Resume via `--run-id` with new-format ID works

### No mock data in production paths
- No hardcoded run IDs in production code

## Deliverables
- Updated `src/launcher/util/run_id.py` with hex4 suffix
- Patched collision-guard blocks in `run_loop.py` and `run_pilot.py`
- Updated tests in `test_run_id.py` for new regex + collision test
- Updated hardcoded IDs in `test_run_manifest.py` if format changed

## Hard Rules
- Keep public signature `generate_run_id(family: str, platform: str) -> str` unchanged
- No network in offline tests
- `run_pilot.py` and `run_loop.py` (CLI entrypoints) stay in parity for collision handling
- Deterministic test via `PYTHONHASHSEED=0`
- No new deps (`os.urandom` is stdlib)
- Code/docs/tests in sync

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Hex suffix added, collision guard in both call sites, docstring updated, tests cover collision |
| Consistency | Same guard pattern in both entrypoints; single generation function |
| Production grading | 65K IDs/sec/family+platform; retry on collision; clear error on exhaustion; no silent dir reuse |
| Systematic approach | Single function → two guarded call sites → tests verify all three |
| Correctness & spec alignment | Format `YYMMDD_HHMMSS_{family}_{platform}_{hex4}`, sorts chronologically, contains family+platform |
| Scope adherence | Only 3 production files touched |
| Maintainability | Docstring explains format, collision probability, and MAX_PATH budget |
| Testability | Regex test, collision-retry test with mocked urandom, uniqueness test |
| Robustness | Retry loop with cap, explicit mkdir without exist_ok, ValueError on exhaustion |
| Performance | Single urandom(2) call per attempt, max 3 retries, negligible |
| Integration fit | Reuses existing module, lazy import pattern matches codebase |
| Observability | Collision retries logged at WARNING; run ID logged at INFO at pipeline start |
| Minimality | ~10 lines changed per file, no unnecessary noise |

## Now (Runbook)

```bash
# 1. Edit src/launcher/util/run_id.py — add os.urandom(2).hex() suffix, update docstring
# 2. Edit src/launcher/orchestrator/run_loop.py — add collision guard with 3 retries
# 3. Edit scripts/run_pilot.py — add collision guard, remove exist_ok=True for fresh runs
# 4. Update tests/unit/util/test_run_id.py — regex, collision test
# 5. Update tests/unit/orchestrator/test_run_manifest.py if hardcoded IDs changed
# 6. Verify
python -c "from launcher.util.run_id import generate_run_id; print(generate_run_id('cells','python'))"
# 7. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py tests/unit/orchestrator/test_run_manifest.py -v
# 8. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

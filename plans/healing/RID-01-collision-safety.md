# RID-01: Run ID Collision Safety

## Status: Done

## Gap Linkage
- G-RID-01: `hex4` gives only 65K IDs/day — birthday-paradox collision at production volumes
- G-RID-02: No collision guard at call sites — `mkdir(exist_ok=True)` silently overwrites
- G-RID-06: Docstring doesn't explain design rationale

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Increase hex suffix from 4 to 6 chars in `generate_run_id()` (16M unique IDs/day, format becomes `r_{YYMMDD}_{hex6}`, 15 chars total — still 12 chars shorter than original 27-char format).
2. Add a collision-retry loop in both call sites (`run_loop.py` and `run_pilot.py`) that regenerates the ID if the target directory already exists. Cap retries at 5 with a clear error on exhaustion.
3. Expand docstring to explain Windows MAX_PATH rationale, collision probability, and caller responsibility.

### Allowed paths
- `src/launcher/util/run_id.py`
- `src/launcher/orchestrator/run_loop.py` (lines ~269-275 only)
- `scripts/run_pilot.py` (lines ~63-69 only)

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- `python -c "from launcher.util.run_id import generate_run_id; rid = generate_run_id(); assert len(rid) == 15; print(rid)"` succeeds
- Full pipeline run (`python scripts/run_pilot.py`) creates a directory matching `r_\d{6}_[0-9a-f]{6}`

### Tests
- Existing `test_run_id_guard.py` still passes (2/2)
- New test `test_generate_run_id_format` asserts: regex match, length == 15, 1000 unique calls produce 1000 unique IDs
- New test `test_collision_retry` patches `uuid.uuid4` to return duplicates, verifies retry loop generates a new ID when `run_dir.exists()` returns True

### Config respected end-to-end
- `discover_latest_run()` still finds runs with new shorter IDs (verified by integration test or manual run + resume)

### No mock data in production paths
- No hardcoded run IDs in production code

## Deliverables
- Full replacement for `src/launcher/util/run_id.py` (hex6, expanded docstring)
- Patched collision-retry blocks in `run_loop.py` and `run_pilot.py`
- New test file `tests/unit/util/test_run_id.py` with format + collision tests

## Hard Rules
- Keep public signature `generate_run_id() -> str` unchanged
- No network in offline tests
- `run_pilot.py` and `run_loop.py` (CLI entrypoints) stay in parity
- Deterministic test via `PYTHONHASHSEED=0`
- No new deps
- Code/docs/tests in sync

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | hex6 applied, collision guard in both call sites, docstring complete |
| Consistency | Same function used everywhere, same retry pattern in both callers |
| Production grading | 16M IDs/day capacity, retry on collision, clear error on exhaustion |
| Systematic approach | Single function, two guarded call sites, dedicated test file |
| Correctness & spec alignment | Format `r_{YYMMDD}_{hex6}`, 15 chars, regex-verified in test |
| Scope adherence | Only 3 files touched + 1 new test file |
| Maintainability | Docstring explains rationale, collision probability, MAX_PATH context |
| Testability | Format test, uniqueness test, collision-retry test with mocked uuid |
| Robustness | Retry loop with cap, clear ValueError on exhaustion |
| Performance | Single uuid4 call per attempt, max 5 retries, negligible |
| Integration fit | Reuses existing module, lazy import pattern matches codebase |
| Observability | Run ID still logged at pipeline start in both entrypoints |
| Minimality | 3 files changed, 1 new test file, no unnecessary noise |

## Now (Runbook)

```bash
# 1. Edit run_id.py — hex4→hex6, expand docstring
# 2. Edit run_loop.py lines ~269-275 — add retry loop
# 3. Edit run_pilot.py lines ~63-69 — add retry loop
# 4. Create tests/unit/util/test_run_id.py
# 5. Verify format
python -c "from launcher.util.run_id import generate_run_id; r=generate_run_id(); print(r, len(r))"
# 6. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py tests/unit/orchestrator/test_run_id_guard.py -v
# 7. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

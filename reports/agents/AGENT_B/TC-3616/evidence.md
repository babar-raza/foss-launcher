# TC-3616 Evidence — CLI validate → canonical engine + MCP NOT_IMPLEMENTED

## Summary

TC-3616 eliminates the parallel-implementation violation in specs/29 §Rule 3 by:
1. Routing `launch validate` through `validation_engine.run_gates()` (same engine as pipeline)
2. Writing `validation_report.json` (canonical) instead of `validation_report.site.json`
3. Replacing the MCP stub `ok:True` with an honest `NOT_IMPLEMENTED` error

## Files Changed

| File | Change |
|------|--------|
| `src/launch/validators/cli.py` | Full refactor: remove 4-gate scaffold, delegate to `run_gates()`, write canonical report |
| `src/launch/cli/triage.py` | Update `.site.json` fallback warning to reference TC-3616 fix path |
| `src/launch/mcp/handlers.py` | Replace stub ok:True with `_error_response(ERROR_INTERNAL, "TC-470 blocked...")` |
| `tests/unit/validators/test_cli_validate_engine.py` | New: 8 tests for engine delegation |
| `tests/unit/validators/__init__.py` | New: empty init |
| `tests/unit/mcp/test_handlers_validate.py` | New: 7 MCP NOT_IMPLEMENTED tests |
| `tests/unit/mcp/test_tc_512_tool_handlers.py` | Updated: `test_handle_launch_validate_success` → `test_handle_launch_validate_returns_not_implemented` |
| `plans/taskcards/TC-3616_cli_validate_canonical_engine.md` | New taskcard |
| `plans/taskcards/INDEX.md` | Registered TC-3616 |

## Commands Run

### Phase 0: Bootstrap verification
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -v tests/unit/test_bootstrap.py
```
Result: **5 passed** (5/5 ✅)

### Phase 5: Targeted tests

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/validators/test_cli_validate_engine.py -v
```
Result: **8 passed** ✅

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/mcp/ -v
```
Result: **65 passed** (7 new from test_handlers_validate.py) ✅

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_triage.py -v
```
Result: **37 passed** ✅

### Phase 6: Full suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short
```
Result: **7849 passed, 13 skipped, 3 xfailed, 0 failed** ✅
(+15 net new from 7834 baseline)

## Determinism Verification

`test_validate_content_hash_is_deterministic` verifies:
- Input: same `gate_results` + `all_issues` lists
- `json.dumps(..., sort_keys=True)` → stable byte string
- `sha256().hexdigest()` → stable hex string
- Test constructs expected hash independently and asserts equality

## Backward Compat

- `.site.json` fallback kept in `triage.py` for pre-TC-3616 run directories
- Old runs with only `.site.json` still readable (with updated warning)
- W9 pipeline unchanged: still writes `validation_report.json` via its own path

## Key Design Decision

`validators/cli.py` previously had 4 custom gates + 9 not-implemented gates.
After TC-3616, it delegates entirely to `validation_engine.run_gates()` which
runs all 41 gates from `gates_registry.yaml`. Gates with missing artifacts
silently pass via `graceful_artifact_skip: true` in the registry.

## Acceptance Checks

- [x] `validators/cli.py` no longer contains custom gate implementations
- [x] `validation_report.json` written by `launch validate`
- [x] `validation_report.site.json` NOT written by `launch validate`
- [x] MCP `handle_launch_validate()` returns `ok: False` with INTERNAL error code
- [x] `triage.py` fallback warning references TC-3616 fix path
- [x] `generation_id` is UUID v4 in written report
- [x] `content_hash` is deterministic SHA-256 (verified by test)
- [x] Full test suite: 7849 passed, 0 failed

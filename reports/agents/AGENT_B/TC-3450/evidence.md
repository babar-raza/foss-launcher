# TC-3450 Evidence — W10 Stale Path Guard

**Taskcard**: plans/taskcards/TC-3450_w10_stale_path_guard.md
**Date**: 2026-02-28
**Agent**: agent_b (Docs & Admin closure — Agent D)

---

## Implementation Summary

### Files Modified

- `src/launch/workers/w10_fixer/worker.py` — +1 constant, +18-line guard in `execute_fixer()`
- `tests/unit/workers/test_w10_path_normalization.py` — 1 test updated, 4 new tests in `TestStalePathGuard`

### Key Implementation Points

1. **EVENT_FIXER_STALE_PATH_DETECTED constant** at line 96:
   ```python
   EVENT_FIXER_STALE_PATH_DETECTED = "FIXER_STALE_PATH_DETECTED"
   ```

2. **Stale path guard in `execute_fixer()`** (lines 1639-1654): inserted after `_normalize_issue_paths()` call and before `FIXER_STARTED` event emission. Guard checks `issue.location.path`, emits `FIXER_STALE_PATH_DETECTED` telemetry event, then raises `StaleValidationReportError` with `issue_id` and resolved path in message.

3. **`isinstance(_stale_loc, dict)` guard** prevents AttributeError when `location` is a non-dict value.

4. **`test_truly_missing_file_raises_stale_error`** (line 304): existing test updated from old behaviour (returned `status:"unfixable"`) to new behaviour (raises `StaleValidationReportError`).

5. **`TestStalePathGuard` class** (4 new deterministic tests, line 379+):
   - `test_stale_path_raises_stale_validation_report_error` — missing path raises `StaleValidationReportError`
   - `test_stale_path_error_message_contains_path_and_issue_id` — error message includes resolved path string and issue_id
   - `test_existing_path_guard_passes_no_exception` — file exists → guard passes, no exception raised
   - `test_no_location_path_guard_skipped` — issue without `location.path` → no `StaleValidationReportError`

---

## Verified Implementation (grep evidence)

```
$ grep -n "FIXER_STALE_PATH_DETECTED\|StaleValidationReportError.*stale\|StaleValidationReportError" \
    src/launch/workers/w10_fixer/worker.py | head -20

96:EVENT_FIXER_STALE_PATH_DETECTED = "FIXER_STALE_PATH_DETECTED"
130:class StaleValidationReportError(FixerError):
149:    4. On mismatch raise :class:`StaleValidationReportError`.
155:        StaleValidationReportError: If content_hash does not match.
182:            raise StaleValidationReportError(
1601:    except (FixerArtifactMissingError, StaleValidationReportError) as e:
1639:    # since W9 ran).  Emit a telemetry event then raise StaleValidationReportError
1649:                    EVENT_FIXER_STALE_PATH_DETECTED,
1654:                raise StaleValidationReportError(

$ grep -n "TestStalePathGuard\|test_stale_path\|test_existing_path_guard\|test_no_location_path\|test_truly_missing" \
    tests/unit/workers/test_w10_path_normalization.py | head -20

304:    def test_truly_missing_file_raises_stale_error(self, run_dir: Path):
379:class TestStalePathGuard:
413:    def test_stale_path_raises_stale_validation_report_error(self, run_dir: Path):
420:    def test_stale_path_error_message_contains_path_and_issue_id(self, run_dir: Path):
431:    def test_existing_path_guard_passes_no_exception(self, run_dir: Path):
444:    def test_no_location_path_guard_skipped(self, run_dir: Path):
```

---

## Test Commands and Output

### Targeted stale tests (5 tests — 4 TestStalePathGuard + 1 updated test)

```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/workers/test_w10_path_normalization.py -v -k "stale" 2>&1 | tail -20

============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.7.3, asyncio-0.26.0, cov-5.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 26 items / 21 deselected / 5 selected

tests\unit\workers\test_w10_path_normalization.py .....                  [100%]

=============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\config\__init__.py:1474
  C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\.venv\Lib\site-packages\_pytest\config\__init__.py:1474: PytestConfigWarning: Unknown config option: env

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 5 passed, 21 deselected, 1 warning in 0.85s =================
```

### Full test_w10_path_normalization.py (26 tests)

```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/workers/test_w10_path_normalization.py -v 2>&1 | tail -20

============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.7.3, asyncio-0.26.0, cov-5.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 26 items

tests\unit\workers\test_w10_path_normalization.py ...................... [ 84%]
....                                                                     [100%]

=============================== warnings summary ===============================
.venv\Lib\site-packages\_pytest\config\__init__.py:1474
  C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\.venv\Lib\site-packages\_pytest\config\__init__.py:1474: PytestConfigWarning: Unknown config option: env

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 26 passed, 1 warning in 1.35s =========================
```

**Result**: 26 passed, 0 failed — all tests green including 4 new `TestStalePathGuard` tests and 1 updated `test_truly_missing_file_raises_stale_error`.

---

## Acceptance Check Verification

- [x] `EVENT_FIXER_STALE_PATH_DETECTED` constant defined at line 96, before first use at line 1649
- [x] Guard placed AFTER `_normalize_issue_paths()` call — path fully resolved before check
- [x] Guard placed BEFORE `emit_event(FIXER_STARTED)` — no partial fix telemetry logged
- [x] `isinstance(_stale_loc, dict)` guard in place at line 1640
- [x] Exception message at line 1654 contains both `issue_id!r` and `_stale_path!r`
- [x] `test_truly_missing_file_raises_stale_error` uses `pytest.raises(StaleValidationReportError)`
- [x] All 4 `TestStalePathGuard` tests are deterministic (`tmp_path` fixture, no LLM)
- [x] Guard checks only `location.path`, not `issue.files[]`
- [x] No new imports added to worker.py (all infrastructure pre-existing)
- [x] Gate count remains 41 (no new gates)

---

## Spec Alignment

- `specs/28_coordination_and_handoffs.md:71-84` — Fix loop policy: W10 raises on stale state so orchestrator can re-run W9.
- `specs/21_worker_contracts.md:290-320` — W10 contract: fix exactly one issue per call, raise clearly on precondition failure.
- `specs/11_state_and_events.md` — Event emission: `FIXER_STALE_PATH_DETECTED` emitted before raise for observability.

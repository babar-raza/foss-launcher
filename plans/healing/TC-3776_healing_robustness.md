# TC-3776 Healing: Robustness & Error Handling

## Context

TC-3776 moved git clone from Understand/Scout to Intake. The refactoring
is functionally correct (933 tests pass), but the self-review identified
two robustness gaps: (1) clone failure produces an unstructured exception
instead of a clean self-review failure, and (2) Understand has no guard
against stale `repo_dir` paths.

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-01 | Clone failure in Intake.run() not caught | SR-01 |
| G-02 | No repo_dir validity guard at Understand entry | SR-01 |
| G-05 | No test for clone exception path in Intake.run() | SR-01 |

---

## Taskcard SR-01: Guard clone failure + validate repo_dir at Understand entry

**Status:** Not Started
**Gap linkage:** G-01, G-02, G-05
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Wrap `clone_repo_cached()` call in `IntakeWorker.run()` with try/except.
   On failure: set `repo_dir=""`, `repo_sha=""`, log the error. Let
   self_review catch the empty `repo_dir` and produce a structured failure.
2. Add a guard at the top of `UnderstandWorker.run()` that validates
   `repo_dir.is_dir()` before proceeding. Raise `ValueError` with a
   clear message if the path is invalid.
3. Add a test `test_clone_exception_produces_empty_repo_dir` in
   `test_intake.py` that patches `clone_repo_cached` to raise
   `subprocess.CalledProcessError` and asserts self_review fails.
4. Add a test `test_understand_rejects_missing_repo_dir` in
   `test_understand.py` that passes an IntakeBundle with a nonexistent
   `repo_dir` and asserts `ValueError` is raised.

**Allowed paths:**
- `src/launcher/workers/intake/worker.py`
- `src/launcher/workers/understand/worker.py`
- `tests/unit/workers/test_intake.py`
- `tests/unit/workers/test_understand.py`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py tests/unit/workers/test_understand.py -v` — all pass
- **Tests:**
  - `test_clone_exception_produces_empty_repo_dir` exists and passes
  - `test_understand_rejects_missing_repo_dir` exists and passes
  - All existing intake/understand tests still pass (no regressions)
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** Mocks only in test files

### Deliverables

- Updated `src/launcher/workers/intake/worker.py` (try/except around clone)
- Updated `src/launcher/workers/understand/worker.py` (repo_dir guard)
- Updated `tests/unit/workers/test_intake.py` (clone exception test)
- Updated `tests/unit/workers/test_understand.py` (missing repo_dir test)

### Hard rules

- Keep public signatures unchanged (`IntakeWorker.run`, `UnderstandWorker.run`)
- No network in offline tests — mock `clone_repo_cached`
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

### Review dimensions — what 5/5 means for SR-01

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Both error paths tested (clone exception + stale path) |
| Consistency | Same error reporting pattern as existing self_review findings |
| Production grading | No unstructured exceptions escape to the graph builder |
| Systematic approach | Guard placed at the earliest possible point (entry of each worker) |
| Correctness | try/except catches CalledProcessError + generic Exception |
| Scope adherence | Only 4 files touched, all within allowed paths |
| Maintainability | Error messages reference the failing component and suggest remediation |
| Testability | Two new focused tests, one per gap |
| Robustness | Clone failure → structured self-review failure → clean pipeline stop |
| Performance | Zero overhead on happy path (try/except is free in Python) |
| Integration fit | Uses existing SelfReviewResult pattern, no new abstractions |
| Observability | Error logged with `logger.error` before being surfaced |
| Minimality | ~10 lines changed in each worker, 2 new test methods |

### Now (runbook)

```bash
# 1. Edit intake/worker.py — wrap clone call in try/except
# 2. Edit understand/worker.py — add repo_dir.is_dir() guard after line 40
# 3. Add test_clone_exception_produces_empty_repo_dir to test_intake.py
# 4. Add test_understand_rejects_missing_repo_dir to test_understand.py
# 5. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py tests/unit/workers/test_understand.py -v
# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
```

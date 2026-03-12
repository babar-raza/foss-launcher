# TC-3797 Healing Plan — Post-Implementation Hardening

## Context

TC-3797 implemented hybrid resume (auto-discovery + explicit `--run-id`) for
both `run_loop.py` and `run_pilot.py`. Self-review identified 5 gaps ranging
from a correctness bug (snapshot overwrite) to missing test coverage and input
validation. This plan converts each gap into an executable taskcard.

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| GAP-01 | Snapshot overwritten on resume (contradicts append design) | **Blocker** | SR-01 |
| GAP-02 | `--run-id` without `--resume-from` silently reuses dir | High | SR-02 |
| GAP-03 | Path resolution inconsistency (`run_dir` vs `layout.run_dir`) | Medium | SR-03 |
| GAP-04 | Flaky mtime test (`time.sleep(0.05)`) | Medium | SR-04 |
| GAP-05 | Missing integration/resume-flow tests | High | SR-05 |

---

## Taskcard SR-01 — Fix snapshot overwrite on resume

**Status:** Done
**Gap linkage:** GAP-01
**Role:** Senior engineer. Drop-in, production-ready.

### Problem

In `execute_run()` at `src/launcher/orchestrator/run_loop.py:293-295`, the
initial snapshot is created and written unconditionally:

```python
initial_snap = create_initial_snapshot(run_id)
write_snapshot(layout.snapshot_file, initial_snap)
```

On resume, this **destroys** the previous run's snapshot, contradicting the
"preserve/append" design decision agreed with the user.

### Scope

**Fix:** Wrap the initial snapshot write in `if not resume_from:` so that
resumed runs preserve their existing `snapshot.json`. The `events.ndjson`
append is already correct.

**Allowed paths:**
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/orchestrator/test_resume_snapshot.py` (new)

**Forbidden:** any other file/path

### Implementation detail

In `src/launcher/orchestrator/run_loop.py`, change lines 293-295 from:

```python
    # -- Write initial snapshot ------------------------------------------------
    initial_snap = create_initial_snapshot(run_id)
    write_snapshot(layout.snapshot_file, initial_snap)
```

To:

```python
    # -- Write initial snapshot (skip on resume to preserve existing state) ----
    if not resume_from:
        initial_snap = create_initial_snapshot(run_id)
        write_snapshot(layout.snapshot_file, initial_snap)
```

### Acceptance checks

- **CLI:** `python -c "..."` or manual: resume a run, verify `snapshot.json`
  mtime is unchanged from the original run.
- **Tests:** New test `test_resume_does_not_overwrite_snapshot` that creates a
  run dir with a known snapshot, calls `execute_run(resume_from="evaluate")`,
  and asserts the snapshot file content is unchanged.
- **Regression:** Fresh run (no resume) still writes initial snapshot.
- **Config respected end-to-end:** N/A (no config change).
- **No mock data in production paths:** Confirmed.

### Deliverables

1. Edited `src/launcher/orchestrator/run_loop.py` (2-line change)
2. New test file `tests/unit/orchestrator/test_resume_snapshot.py` with
   happy path (resume preserves) + regression (fresh run writes)

### Hard rules

- Public signature of `execute_run` unchanged.
- No new dependencies.
- Deterministic: no randomness in test.
- Code/docs/tests in sync.

### Review dimensions (what 5/5 means for this card)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Snapshot preserved on resume, written on fresh run |
| Robustness | Works for all resume_from values including "intake" |
| Testability | Both paths (resume/fresh) have dedicated assertions |
| Minimality | Exactly one `if` guard added, nothing else touched |
| Integration | Events still append; snapshot still written at end of run |

### Runbook

```bash
# 1. Apply the edit
#    (Edit run_loop.py lines 293-295 as described above)

# 2. Write the test file
#    tests/unit/orchestrator/test_resume_snapshot.py

# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_resume_snapshot.py -v

# 4. Run full suite for regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard SR-02 — Guard `--run-id` without `--resume-from`

**Status:** Done
**Gap linkage:** GAP-02
**Role:** Senior engineer. Drop-in, production-ready.

### Problem

If a user passes `--run-id` without `--resume-from`, the code silently reuses
an existing directory, overwrites `run_config.json` and snapshot, and appends
events — corrupting the original run's data. This is undefined behavior that
should be an explicit error.

### Scope

**Fix:** Add a validation guard in both entry points: CLI `main.py` and
`scripts/run_pilot.py`. Also add the same guard in `execute_run()` itself
as defense-in-depth.

**Allowed paths:**
- `src/launcher/cli/main.py`
- `src/launcher/orchestrator/run_loop.py`
- `scripts/run_pilot.py`
- `tests/unit/orchestrator/test_run_id_guard.py` (new)

**Forbidden:** any other file/path

### Implementation detail

**In `src/launcher/cli/main.py`**, after the existing `stop_after`/`resume_from`
validation block (after line 111), add:

```python
    if run_id and not resume_from:
        typer.echo(
            "Error: --run-id requires --resume-from (to avoid corrupting an existing run)",
            err=True,
        )
        raise typer.Exit(code=1)
```

**In `src/launcher/orchestrator/run_loop.py`**, at the top of `execute_run()`
(before the runs_root resolution), add:

```python
    if run_id and not resume_from:
        raise ValueError("run_id requires resume_from (to avoid corrupting an existing run)")
```

**In `scripts/run_pilot.py`**, before the 3-way branch (before line 47), add:

```python
    if run_id and not resume_from:
        raise SystemExit("--run-id requires --resume-from (to avoid corrupting an existing run)")
```

### Acceptance checks

- **CLI:** `launch run config.yaml --run-id foo` (no `--resume-from`) prints
  error and exits with code 1.
- **Tests:** `test_run_id_without_resume_raises` for `execute_run`.
- **Regression:** `--run-id` with `--resume-from` still works.
- **Config respected end-to-end:** N/A.
- **No mock data in production paths:** Confirmed.

### Deliverables

1. Edited `src/launcher/cli/main.py` (4-line guard)
2. Edited `src/launcher/orchestrator/run_loop.py` (2-line guard)
3. Edited `scripts/run_pilot.py` (2-line guard)
4. New test `tests/unit/orchestrator/test_run_id_guard.py`

### Hard rules

- Public signatures unchanged.
- Parity across all 3 entry points (CLI, orchestrator, script).
- No new dependencies.

### Review dimensions (what 5/5 means for this card)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | All 3 entry points reject `--run-id` without `--resume-from` |
| Robustness | Clear error message; no silent data corruption |
| Scope adherence | Guard added at boundary + defense-in-depth |
| Testability | Dedicated test for the ValueError path |
| Minimality | Only guard logic added, nothing else touched |

### Runbook

```bash
# 1. Apply edits to main.py, run_loop.py, run_pilot.py

# 2. Write test file tests/unit/orchestrator/test_run_id_guard.py

# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_run_id_guard.py -v

# 4. Manual CLI check
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml --run-id fake_id 2>&1 | grep -i error

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard SR-03 — Normalize path resolution in execute_run

**Status:** Not Started
**Gap linkage:** GAP-03
**Role:** Senior engineer. Drop-in, production-ready.

### Problem

In `execute_run()`, the `run_dir` variable is sometimes resolved (via
`RunLayout(run_dir=run_dir.resolve())`) and sometimes not. This means
`run_dir` (used for `ArtifactStore`, events, state) may differ from
`layout.run_dir` (resolved). On Windows with OneDrive paths, this can cause
path comparison mismatches.

Additionally, the existing-dir branch bypasses `_validate_run_dir()`, which
normally ensures the parent is named `runs/`.

### Scope

**Fix:** Resolve `run_dir` once immediately after the 3-way branch, before
any use. Remove the `.resolve()` from the `RunLayout` constructor call.
Add `_validate_run_dir` call for existing dirs too.

**Allowed paths:**
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/io/test_run_layout.py` (update existing)

**Forbidden:** any other file/path

### Implementation detail

In `src/launcher/orchestrator/run_loop.py`, after the 3-way branch and
before the `logger.info("Starting pipeline run")` line, add:

```python
    run_dir = run_dir.resolve()
```

Then change:

```python
    if run_dir.exists():
        layout = RunLayout(run_dir=run_dir.resolve())
    else:
        layout = create_run_skeleton(run_dir)
```

To:

```python
    if run_dir.exists():
        layout = RunLayout(run_dir=_validate_run_dir(run_dir))
    else:
        layout = create_run_skeleton(run_dir)
```

Import `_validate_run_dir` from `run_layout` (it's module-private, so either
make it package-private or inline the check).

### Acceptance checks

- **Tests:** Existing `test_run_layout.py` tests still pass.
- **Regression:** `str(run_dir) == layout.run_dir` is always true after change.
- **No mock data in production paths:** Confirmed.

### Deliverables

1. Edited `src/launcher/orchestrator/run_loop.py` (3-line change)
2. Updated `tests/unit/io/test_run_layout.py` if needed

### Hard rules

- No new dependencies.
- Path is resolved exactly once, early.
- `_validate_run_dir` check applies to both new and existing dirs.

### Review dimensions (what 5/5 means for this card)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `run_dir` and `layout.run_dir` always point to same resolved path |
| Consistency | Both branches (new/existing) go through same validation |
| Integration | No downstream path comparison issues |
| Minimality | One `.resolve()` call moved earlier; one redundant `.resolve()` removed |

### Runbook

```bash
# 1. Apply edit to run_loop.py

# 2. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard SR-04 — Fix flaky mtime test

**Status:** Done
**Gap linkage:** GAP-04
**Role:** Senior engineer. Drop-in, production-ready.

### Problem

`test_returns_newest_by_mtime` uses `time.sleep(0.05)` to create a mtime
difference between two directories. This is fragile on slow CI, containers,
or filesystems with coarse mtime granularity.

### Scope

**Fix:** Replace `time.sleep` with deterministic `os.utime()` calls to set
explicit mtimes.

**Allowed paths:**
- `tests/unit/io/test_run_layout.py`

**Forbidden:** any other file/path

### Implementation detail

Replace the test method:

```python
def test_returns_newest_by_mtime(self, tmp_path: Path) -> None:
    import os
    runs = tmp_path / "runs"
    runs.mkdir()
    old = _make_run_dir(runs, "run_old", "cells", "python")
    new = _make_run_dir(runs, "run_new", "cells", "python")
    # Set deterministic mtimes (old=1000s, new=2000s epoch)
    os.utime(old, (1000.0, 1000.0))
    os.utime(new, (2000.0, 2000.0))

    result = discover_latest_run(runs, "cells", "python")
    assert result is not None
    assert result.name == "run_new"
```

### Acceptance checks

- **Tests:** `test_returns_newest_by_mtime` passes reliably (no sleep).
- **Regression:** All other `test_run_layout.py` tests unchanged.
- **No mock data in production paths:** Test-only change.

### Deliverables

1. Edited `tests/unit/io/test_run_layout.py` (one test method rewritten)

### Hard rules

- No `time.sleep` in tests.
- Deterministic ordering guaranteed by `os.utime`.
- No new dependencies.

### Review dimensions (what 5/5 means for this card)

| Dimension | 5/5 means |
|-----------|-----------|
| Test quality | Zero flakiness risk; deterministic mtime control |
| Minimality | Single test method changed |
| Correctness | Still verifies newest-by-mtime semantics |

### Runbook

```bash
# 1. Edit test method in tests/unit/io/test_run_layout.py

# 2. Run targeted test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_layout.py::TestDiscoverLatestRun::test_returns_newest_by_mtime -v

# 3. Run full io tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_run_layout.py -v
```

---

## Taskcard SR-05 — Add integration tests for resume flow

**Status:** Not Started
**Gap linkage:** GAP-05
**Role:** Senior engineer. Drop-in, production-ready.

### Problem

The current test suite only covers `discover_latest_run` (utility function).
The actual resume flow in `execute_run()` — the most critical path — has zero
test coverage. Neither `_build_resume_state` warning, CLI `--run-id` passing,
nor `run_pilot.py` resume behavior are tested.

### Scope

**Fix:** Add integration-level tests that exercise `execute_run` with
`resume_from` and/or `run_id`, using mock workers. Also test the
`_build_resume_state` warning path.

**Allowed paths:**
- `tests/unit/orchestrator/test_resume_flow.py` (new)
- `tests/unit/orchestrator/test_build_resume_state.py` (new)

**Forbidden:** any other file/path

### Test cases to implement

**`test_resume_flow.py`:**

1. `test_resume_autodiscovers_existing_run` — Create a run dir with
   checkpoints and `run_config.json`, call `execute_run(resume_from="evaluate")`
   with mock workers, verify the discovered run dir is reused (not a new one).

2. `test_resume_with_explicit_run_id` — Same setup but pass explicit
   `run_id`, verify that exact dir is used.

3. `test_fresh_run_creates_new_dir` — Call `execute_run()` with no resume,
   verify a new run dir is created.

4. `test_resume_no_matching_run_raises` — Empty runs dir, call with
   `resume_from="evaluate"`, verify `ValueError` raised.

**`test_build_resume_state.py`:**

5. `test_warns_when_no_checkpoints_found` — Call `_build_resume_state` with
   `resume_from="evaluate"` on an empty dir, verify warning is logged
   (use `caplog` fixture).

6. `test_loads_checkpoints_before_resume_point` — Create intake + understand
   checkpoints, resume from "generate", verify both loaded into
   `worker_outputs`.

7. `test_does_not_load_checkpoints_at_or_after_resume_point` — Create all
   checkpoints, resume from "generate", verify "generate"/"evaluate"/"publish"
   are NOT in `worker_outputs`.

### Acceptance checks

- **Tests:** All 7 new tests pass.
- **CLI:** N/A (tested via unit tests against `execute_run`).
- **Regression:** Full suite still passes.
- **No mock data in production paths:** Tests use `tmp_path` and mock workers.
- **Config respected end-to-end:** Tests use minimal `RunConfig`.

### Deliverables

1. New `tests/unit/orchestrator/test_resume_flow.py` (4 tests)
2. New `tests/unit/orchestrator/test_build_resume_state.py` (3 tests)

### Hard rules

- No network calls (mock workers return static dicts).
- Deterministic (PYTHONHASHSEED=0 compatible).
- Uses `tmp_path` for all filesystem operations.
- No new dependencies.

### Review dimensions (what 5/5 means for this card)

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All 3 resume branches + warning path + checkpoint loading tested |
| Test quality | No sleep, no network, deterministic, isolated via tmp_path |
| Correctness | Tests verify actual resume behavior, not just utility functions |
| Integration | Tests exercise execute_run end-to-end (with mock workers) |
| Robustness | Error paths tested (no matching run, missing checkpoints) |

### Runbook

```bash
# 1. Write test files

# 2. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_resume_flow.py tests/unit/orchestrator/test_build_resume_state.py -v

# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

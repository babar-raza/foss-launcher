---
id: TC-4221
title: "Add scout to _VALID_WORKERS, worker_order, and _KNOWN_PIPELINE_WORKERS"
status: Done
priority: Low
owner: "orchestrator"
updated: "2026-03-12"
tags: [cli, scout, pipeline]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4221_scout-valid-workers.md
  - src/launcher/cli/main.py
  - src/launcher/orchestrator/run_loop.py
  - tests/unit/cli/
  - tests/unit/orchestrator/test_run_loop.py
evidence_required:
  - reports/agents/B/TC-4221/evidence.md
---

# Taskcard TC-4221 — Add scout to _VALID_WORKERS, worker_order, and _KNOWN_PIPELINE_WORKERS

## Objective

`--stop-after scout` is rejected at startup with a validation error such as
`"scout" is not a valid worker name`, even though scout is a fully registered,
functioning worker. The root cause is that "scout" is absent from three
hardcoded lists: `_VALID_WORKERS` in `main.py`, the `worker_order` tuple used
for index-based resume/stop logic, and `_KNOWN_PIPELINE_WORKERS` in
`run_loop.py`. Any user attempting to run the pipeline through the scout phase
only — a common debugging workflow — receives an immediate rejection with no
useful guidance.

Fix: add "scout" at the correct ordinal position (between "intake" and
"understand") in all three lists so that `--stop-after scout`,
`--resume-from scout`, and `--resume-from scout --stop-after scout` all behave
identically to the same flags for every other worker.

## Required spec references

- `specs/system_overview.md` — canonical worker execution order
- `specs/worker_understand.md` — confirms scout precedes understand
- `src/launcher/cli/main.py` — contains `_VALID_WORKERS` and `worker_order`
- `src/launcher/orchestrator/run_loop.py` — contains `_KNOWN_PIPELINE_WORKERS`

## Scope

### In scope

- Add "scout" to `_VALID_WORKERS` in `src/launcher/cli/main.py`
- Add "scout" to `worker_order` tuple in `src/launcher/cli/main.py` (between
  "intake" and "understand")
- Add "scout" to `_KNOWN_PIPELINE_WORKERS` in
  `src/launcher/orchestrator/run_loop.py` (same ordinal position)
- Add or update unit tests verifying that "scout" passes CLI validation and
  produces correct resume/stop indices

### Out of scope

- Changes to the scout worker implementation itself
- Changes to pipeline topology or config
- Changes to any schema file

## Inputs

- `src/launcher/cli/main.py` (current, missing "scout" in three lists)
- `src/launcher/orchestrator/run_loop.py` (current, missing "scout" in
  `_KNOWN_PIPELINE_WORKERS`)
- Existing unit tests in `tests/unit/cli/` and
  `tests/unit/orchestrator/test_run_loop.py`

## Outputs

- `src/launcher/cli/main.py` with "scout" present in `_VALID_WORKERS` and
  `worker_order`
- `src/launcher/orchestrator/run_loop.py` with "scout" present in
  `_KNOWN_PIPELINE_WORKERS`
- Passing unit tests for all affected validation paths

## Allowed paths

- plans/taskcards/TC-4221_scout-valid-workers.md
- src/launcher/cli/main.py
- src/launcher/orchestrator/run_loop.py
- tests/unit/cli/
- tests/unit/orchestrator/test_run_loop.py

### Allowed paths rationale

Only the two source files containing the hardcoded lists require modification.
Test files in the two listed directories are permitted to add coverage for the
new entry. No schema, config, or spec file requires a change.

## Implementation steps

### Step 1: Locate all three hardcoded lists

Open `src/launcher/cli/main.py` and find:

1. `_VALID_WORKERS` — a set or list of accepted worker name strings used for
   `--stop-after` / `--resume-from` argument validation.
2. `worker_order` — a tuple defining the canonical left-to-right execution
   sequence; the CLI converts worker names to integers using
   `worker_order.index(name)` to compare resume and stop positions.

Open `src/launcher/orchestrator/run_loop.py` and find:

3. `_KNOWN_PIPELINE_WORKERS` — used by the run loop for similar ordinal
   resolution and guard checks.

Confirm "scout" is absent from all three. Note the current sequence so the
insertion position can be determined precisely (expected: intake → understand,
so scout goes between them).

### Step 2: Edit `src/launcher/cli/main.py`

In `_VALID_WORKERS`, add `"scout"` so the set/list reads (in order):
`"intake"`, `"scout"`, `"understand"`, `"generate"`, `"evaluate"`, `"publish"`
(adjust if additional workers exist).

In `worker_order`, insert `"scout"` between `"intake"` and `"understand"` at
the same ordinal position. Verify the tuple index of "understand" shifts by
exactly 1 after the insertion — this preserves all existing index arithmetic
for workers that follow scout.

### Step 3: Edit `src/launcher/orchestrator/run_loop.py`

In `_KNOWN_PIPELINE_WORKERS`, insert `"scout"` between `"intake"` and
`"understand"` using the same logic as Step 2. Confirm the list is in execution
order, not alphabetical order.

### Step 4: Update or add unit tests

In `tests/unit/cli/` (create a new file if no CLI argument test exists):
- Assert that `--stop-after scout` passes validation without error.
- Assert that `--resume-from scout` passes validation without error.
- Assert that `worker_order.index("scout")` equals
  `worker_order.index("intake") + 1`.

In `tests/unit/orchestrator/test_run_loop.py`:
- Assert that `"scout"` is present in `_KNOWN_PIPELINE_WORKERS`.
- Assert its index is `_KNOWN_PIPELINE_WORKERS.index("intake") + 1`.

### Step 5: Run the test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/ \
  tests/unit/orchestrator/test_run_loop.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
```

Confirm zero new failures.

## Failure modes

### Failure mode 1: "scout" inserted at wrong ordinal position

**Symptom**: `--resume-from intake --stop-after understand` skips scout or
runs it twice; index arithmetic for downstream workers is off by 1.
**Detection**: Unit tests asserting `worker_order.index("scout") ==
worker_order.index("intake") + 1` fail.
**Resolution**: Recheck the insertion index; the tuple must preserve the
canonical pipeline order defined in `specs/system_overview.md`.
**Gate**: `test_run_loop.py` index assertions.

### Failure mode 2: Only one of the three lists is updated

**Symptom**: CLI validation accepts "scout" but the run loop still rejects it
(or vice versa), causing confusing partial failures.
**Detection**: Test that exercises the run loop path fails while CLI test passes.
**Resolution**: Grep all source files for the other two list identifiers;
confirm all three are updated before marking Done.
**Gate**: Full test suite and manual grep check `grep -r "_VALID_WORKERS\|worker_order\|_KNOWN_PIPELINE_WORKERS" src/`.

### Failure mode 3: Existing worker index tests break due to index shift

**Symptom**: Tests that assert `worker_order.index("understand") == N` now
fail because understand shifted from index N to N+1.
**Detection**: Pre-existing tests in `test_run_loop.py` or `tests/unit/cli/`
fail with `AssertionError: 2 != 3` (or similar).
**Resolution**: Update those tests to use relative assertions
(`index("understand") == index("scout") + 1`) instead of hard-coded integers.
**Gate**: Full test suite.

### Failure mode 4: `_VALID_WORKERS` is a frozenset and insertion fails silently

**Symptom**: The file edits without error but "scout" is not in the frozenset
at runtime due to a code path that rebuilds the set from a different source.
**Detection**: `assert "scout" in _VALID_WORKERS` unit test fails at runtime.
**Resolution**: Trace the construction of `_VALID_WORKERS`; if it is derived
from `worker_order`, updating `worker_order` alone is sufficient — confirm
which is the source of truth.
**Gate**: Explicit membership assertion in unit test.

## Task-specific review checklist

1. [ ] `"scout"` present in `_VALID_WORKERS` in `main.py`
2. [ ] `"scout"` present in `worker_order` in `main.py` between "intake" and
       "understand"
3. [ ] `"scout"` present in `_KNOWN_PIPELINE_WORKERS` in `run_loop.py` at the
       same ordinal position
4. [ ] All three lists have identical ordering for the scout entry (no
       divergence between CLI and run loop)
5. [ ] `--stop-after scout` no longer raises a validation error (unit test or
       manual check)
6. [ ] `--resume-from scout --stop-after scout` accepted without error
7. [ ] No pre-existing test broken by the index shift
8. [ ] Evidence file created at `reports/agents/B/TC-4221/evidence.md`

## Deliverables

1. Updated `src/launcher/cli/main.py` with "scout" in `_VALID_WORKERS` and
   `worker_order`
2. Updated `src/launcher/orchestrator/run_loop.py` with "scout" in
   `_KNOWN_PIPELINE_WORKERS`
3. New or updated unit tests in `tests/unit/cli/` and
   `tests/unit/orchestrator/test_run_loop.py`
4. Evidence at `reports/agents/B/TC-4221/evidence.md`

## Acceptance checks

- [ ] `pytest tests/unit/cli/ -v` — all pass
- [ ] `pytest tests/unit/orchestrator/test_run_loop.py -v` — all pass
- [ ] `pytest -x -q` — 0 new failures
- [ ] `"scout"` confirmed in all three lists via code inspection
- [ ] `--stop-after scout` accepted by CLI argument parser (unit test or live
      invocation)

## Self-review

### Verification results

- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-4221/evidence.md
- [ ] All three lists verified updated: `_VALID_WORKERS`, `worker_order`,
      `_KNOWN_PIPELINE_WORKERS`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/ \
  tests/unit/orchestrator/test_run_loop.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
# Optional live smoke test:
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml \
  --stop-after scout --run-id smoke_scout_4221
```

**Expected results**:
- CLI and run_loop tests all pass
- Full suite: 0 new failures
- Live run (if executed): pipeline stops cleanly after scout phase with no
  "not a valid worker" error

## Integration boundary proven

**Upstream**: User passes `--stop-after scout` or `--resume-from scout` on the
command line; `main.py` validates the string against `_VALID_WORKERS` and
resolves it to an index via `worker_order`.
**Downstream**: `run_loop.py` uses `_KNOWN_PIPELINE_WORKERS` to apply the same
ordinal logic at execution time; a mismatch between CLI and run loop lists
causes inconsistent behaviour.
**Contract**: All three lists must be in sync and in canonical pipeline order.
The fix must be applied atomically to all three; a partial fix is worse than no
fix because it produces misleading partial acceptance.

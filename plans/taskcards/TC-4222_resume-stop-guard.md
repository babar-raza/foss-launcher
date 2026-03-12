---
id: TC-4222
title: "Allow --resume-from X --stop-after X by changing >= to > guard"
status: Done
priority: Low
owner: "orchestrator"
updated: "2026-03-12"
tags: [cli, resume, stop-after]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4222_resume-stop-guard.md
  - src/launcher/cli/main.py
  - tests/unit/cli/
  - tests/unit/test_pipeline_e2e.py
evidence_required:
  - reports/agents/B/TC-4222/evidence.md
---

# Taskcard TC-4222 — Allow --resume-from X --stop-after X by changing >= to > guard

## Objective

The CLI rejects `--resume-from X --stop-after X` — the valid, idiomatic way to
re-run a single worker in isolation — with the error message
`"--resume-from must come before --stop-after"` (or similar). The root cause is
a guard on `main.py:118` that reads `resume_idx >= stop_idx`. The `>=` operator
incorrectly treats equal indices (resume == stop, meaning "run exactly this one
worker") as invalid. The correct semantic is that `resume_idx > stop_idx` is
the only truly illegal case (you cannot resume after the stop point). Change
the operator from `>=` to `>` and update the error message to accurately
describe the constraint.

## Required spec references

- `src/launcher/cli/main.py` — line ~118, the guard that must be changed
- `specs/system_overview.md` — defines resume/stop semantics for the pipeline
  CLI

## Scope

### In scope

- Change `resume_idx >= stop_idx` to `resume_idx > stop_idx` on the guard line
  in `main.py`
- Update the accompanying error message to accurately describe the new
  constraint: "resume-from worker must not come after stop-after worker"
- Add unit tests in `tests/unit/cli/` covering the equal case (resume == stop)
  and the still-illegal case (resume > stop)

### Out of scope

- Changes to the run loop execution logic
- Changes to worker order definitions (covered by TC-4221)
- Changes to any schema or config file

## Inputs

- `src/launcher/cli/main.py` (current, with `>=` guard at ~line 118)
- Existing tests in `tests/unit/cli/`

## Outputs

- `src/launcher/cli/main.py` with `>` guard and updated error message
- Unit tests confirming the boundary behaviour at resume == stop and
  resume > stop

## Allowed paths

- plans/taskcards/TC-4222_resume-stop-guard.md
- src/launcher/cli/main.py
- tests/unit/cli/

### Allowed paths rationale

The change is a one-character operator replacement on a single guard line.
Only `main.py` requires a source edit. New test coverage goes in the existing
CLI test directory. No other file is affected.

## Implementation steps

### Step 1: Locate the guard

Open `src/launcher/cli/main.py`. Search for the condition that compares
`resume_idx` and `stop_idx` (approximately line 118). Confirm the current
operator is `>=` and note the exact error message raised.

### Step 2: Apply the fix

Change the operator:

```python
# Before
if resume_idx >= stop_idx:
    raise ValueError("--resume-from must come before --stop-after")

# After
if resume_idx > stop_idx:
    raise ValueError(
        "--resume-from worker must not come after --stop-after worker "
        "(equal is allowed: re-runs exactly that one worker)"
    )
```

The error message update is mandatory — the old message was factually wrong for
the equal case and would confuse users who try `--resume-from X --stop-after X`
after reading the error.

### Step 3: Add unit tests

In `tests/unit/cli/` (new file `test_resume_stop_guard.py` if none exists,
otherwise extend the relevant existing file):

```python
def test_resume_equals_stop_is_allowed():
    """--resume-from understand --stop-after understand must not raise."""
    # Call the argument validation function with equal indices and assert no exception.

def test_resume_after_stop_is_rejected():
    """--resume-from evaluate --stop-after understand must raise ValueError."""
    # Call with resume_idx > stop_idx and assert ValueError is raised.

def test_resume_before_stop_is_allowed():
    """--resume-from understand --stop-after evaluate must not raise."""
    # Baseline: normal usage still works.
```

The test should invoke the validation logic directly (not spawn a subprocess)
by importing the relevant function or by constructing the argument namespace
and calling the validation helper.

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
```

Confirm all three new test cases pass and no pre-existing tests regress.

## Failure modes

### Failure mode 1: Guard line number has shifted; edit applied to wrong line

**Symptom**: The `>=` on a different comparison is changed; the actual guard is
untouched and the bug persists.
**Detection**: Unit test `test_resume_equals_stop_is_allowed` still raises
ValueError after the edit.
**Resolution**: Re-read `main.py` and locate the guard by searching for
`resume_idx` assignments and the comparison rather than relying on a line
number.
**Gate**: Unit test with equal indices.

### Failure mode 2: Error message update omitted

**Symptom**: The operator is fixed but the message still reads "must come
before", which is inaccurate and misleading when resume > stop is rejected.
**Detection**: Code review / review checklist item; no automated gate unless a
test asserts on the message text.
**Resolution**: Ensure both the operator and the message are updated in the
same commit.
**Gate**: Review checklist item 4.

### Failure mode 3: New test imports a symbol that does not exist

**Symptom**: `test_resume_stop_guard.py` fails with `ImportError` because the
validation helper is private or not exported.
**Detection**: `pytest tests/unit/cli/` fails at collection time.
**Resolution**: Import at the module level (not the function level) to detect
this early; alternatively patch the argparse namespace and call
`main.validate_run_args` if that function exists.
**Gate**: Test collection succeeds.

## Task-specific review checklist

1. [ ] `resume_idx >= stop_idx` changed to `resume_idx > stop_idx` on the
       guard line in `main.py`
2. [ ] Error message updated to accurately describe the remaining constraint
       (resume after stop is illegal; equal is legal)
3. [ ] Unit test `test_resume_equals_stop_is_allowed` added and passes
4. [ ] Unit test `test_resume_after_stop_is_rejected` added and passes
5. [ ] Unit test `test_resume_before_stop_is_allowed` (baseline) present and
       passes
6. [ ] No pre-existing CLI tests broken
7. [ ] Evidence file created at `reports/agents/B/TC-4222/evidence.md`

## Deliverables

1. Updated `src/launcher/cli/main.py` with `>` guard and corrected error
   message
2. New or updated unit tests in `tests/unit/cli/`
3. Evidence at `reports/agents/B/TC-4222/evidence.md`

## Acceptance checks

- [ ] `pytest tests/unit/cli/ -v` — all pass including the three new cases
- [ ] `pytest -x -q` — 0 new failures
- [ ] Manual or automated check: `--resume-from understand --stop-after
      understand` is accepted by the CLI without error
- [ ] Manual or automated check: `--resume-from evaluate --stop-after
      understand` is rejected with the updated error message

## Self-review

### Verification results

- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B/TC-4222/evidence.md
- [ ] Operator confirmed changed from `>=` to `>` via code inspection
- [ ] Error message confirmed updated

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -10
# Optional live smoke test (equal case):
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml \
  --resume-from understand --stop-after understand \
  --run-id 260311_190711_cells_python_6882
```

**Expected results**:
- All CLI tests pass including three new boundary cases
- Full suite: 0 new failures
- Live run (if executed): pipeline accepts equal resume/stop and runs exactly
  the understand worker

## Integration boundary proven

**Upstream**: User passes `--resume-from X --stop-after X`; `main.py` resolves
both to integer indices and runs the guard.
**Downstream**: If the guard passes, `run_loop.py` receives a valid `[resume,
stop]` window and executes workers in that range. Equal indices produce a
single-worker window which is legal and useful.
**Contract**: The guard's sole responsibility is to prevent logically impossible
windows (start after end). Equal is not impossible — it is a degenerate but
valid single-step window. The `>` operator correctly encodes this.

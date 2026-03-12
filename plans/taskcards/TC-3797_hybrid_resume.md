---
id: TC-3797
title: "Fix broken resume: hybrid run discovery + explicit run ID"
status: Done
priority: High
owner: "claude"
updated: "2026-03-07"
tags: [resume, run-loop, cli, bugfix]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3797_hybrid_resume.md
  - src/launcher/io/run_layout.py
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/cli/main.py
  - scripts/run_pilot.py
  - tests/test_run_layout.py
  - tests/test_run_loop.py
evidence_required:
  - reports/TC-3797/evidence.md
---

# Taskcard TC-3797 — Fix broken resume: hybrid run discovery + explicit run ID

## Objective

Fix the completely broken `resume_from` feature in both `run_pilot.py` and
`run_loop.py`. Currently, resume generates a new run_id and empty directory,
so checkpoints from the previous run are never found. Implement a hybrid
approach: (1) explicit `--run-id` to reuse a specific run, (2) auto-discovery
of the latest run for the same family+platform when no run_id is provided.

## Required spec references

- `specs/06_orchestrator_run_loop.md` (Section: resume_from semantics)
- `specs/05_io_layer.md` (Section: run directory layout)

## Scope

### In scope
- Add `discover_latest_run()` utility to `run_layout.py`
- Wire hybrid resume logic into `execute_run()` in `run_loop.py`
- Add `--run-id` CLI option to `main.py`
- Update `run_pilot.py` with same hybrid logic + argparse
- Add checkpoint existence warning in `_build_resume_state()`
- Unit tests for discovery and resume behavior

### Out of scope
- Changing run_id naming conventions (kept as-is for both scripts)
- Adding cross-run checkpoint migration
- Modifying checkpoint format or contents

## Inputs

- Existing run directories under `runs/` containing `run_config.json`
- `resume_from` worker name (string)
- Optional explicit `run_id` (string)

## Outputs

- Working resume that reuses existing run directories
- `discover_latest_run()` utility function
- `--run-id` CLI option on both `main.py` and `run_pilot.py`

## Allowed paths

- plans/taskcards/TC-3797_hybrid_resume.md
- src/launcher/io/run_layout.py
- src/launcher/orchestrator/run_loop.py
- src/launcher/cli/main.py
- scripts/run_pilot.py
- tests/test_run_layout.py
- tests/test_run_loop.py

### Allowed paths rationale
- `run_layout.py`: owns run directory concerns, natural home for discovery
- `run_loop.py`: contains `execute_run()` and `_build_resume_state()`
- `main.py`: CLI entry point needs `--run-id` option
- `run_pilot.py`: direct runner script needs same fix
- `tests/`: unit tests for new and changed behavior

## Implementation steps

### Step 1: Add `discover_latest_run()` to `run_layout.py`
Scan subdirs of runs_root, read run_config.json, match family+platform, return newest by mtime.

### Step 2: Update `execute_run()` in `run_loop.py`
Three-way branch: (a) resume+no run_id → auto-discover, (b) no run_id → generate new, (c) explicit run_id → use directly. Skip `create_run_skeleton` for existing dirs.

### Step 3: Add `--run-id` to CLI `main.py`
New typer.Option, pass through to execute_run.

### Step 4: Update `run_pilot.py`
Same three-way branch. Switch to argparse for cleaner arg handling.

### Step 5: Add checkpoint warning to `_build_resume_state()`
Log warning when no checkpoints found and resume_from != "intake".

### Step 6: Write tests

## Failure modes

### Failure mode 1: No previous run exists
**Detection**: `discover_latest_run` returns None
**Resolution**: Raise ValueError with clear message including family+platform
**Gate**: N/A — runtime error

### Failure mode 2: Previous run has no checkpoints
**Detection**: `_build_resume_state` returns empty worker_outputs for non-intake resume
**Resolution**: Log warning; pipeline will re-execute workers (degraded but functional)
**Gate**: N/A — warning log

### Failure mode 3: Corrupted run_config.json in old run dir
**Detection**: JSON decode error during discovery scan
**Resolution**: Skip that directory with debug log, continue scanning
**Gate**: N/A — graceful degradation

## Task-specific review checklist

1. [x] `discover_latest_run` correctly filters by family AND platform
2. [x] `discover_latest_run` handles empty runs dir (returns None)
3. [x] `discover_latest_run` skips corrupted/missing run_config.json
4. [x] `execute_run` reuses existing dir when resuming (no skeleton overwrite)
5. [x] `execute_run` creates new dir for fresh runs (backward compatible)
6. [x] `_build_resume_state` warns when no checkpoints found
7. [x] CLI `--run-id` option works and passes through correctly
8. [x] `run_pilot.py` auto-discovers when resuming without explicit run_id

## Deliverables

1. Modified `src/launcher/io/run_layout.py` with `discover_latest_run()`
2. Modified `src/launcher/orchestrator/run_loop.py` with hybrid resume
3. Modified `src/launcher/cli/main.py` with `--run-id`
4. Modified `scripts/run_pilot.py` with hybrid resume + argparse
5. Tests in `tests/test_run_layout.py` and/or `tests/test_run_loop.py`

## Acceptance checks

1. [ ] `discover_latest_run` unit tests pass
2. [ ] Existing test suite passes (no regressions)
3. [ ] Resume with auto-discovery finds correct run dir
4. [ ] Resume with explicit `--run-id` uses that dir
5. [ ] Fresh run (no resume) still generates new run_id

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3797/evidence.md

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/test_run_layout.py tests/test_run_loop.py -v
.venv/Scripts/python.exe -m pytest tests/ -v --timeout=60
```

**Expected results**:
- All new tests pass
- No regressions in existing tests

## Integration boundary proven

**Upstream**: `run_config.json` written by each run (already exists)
**Downstream**: `_build_resume_state()` loads checkpoints from discovered dir
**Contract**: `run_config.json` contains `family` and `platform` string fields

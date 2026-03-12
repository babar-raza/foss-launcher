---
id: TC-4256
title: "Stop emitting Python properties as callable methods in understand"
status: In-Progress
priority: Critical
owner: "Agent-B"
updated: "2026-03-12"
tags: [understand, python, properties, methods, api-surface]
depends_on: [TC-4255]
allowed_paths:
  - plans/taskcards/TC-4256_understand-stop-emitting-properties-as-methods.md
  - src/launcher/shared/code_analyzer.py
  - tests/unit/workers/test_understand.py
  - reports/TC-4256/evidence.md
  - reports/agents/B_implementation/ORCH-04/changes.md
  - reports/agents/B_implementation/ORCH-04/evidence.md
  - reports/agents/B_implementation/ORCH-04/self_review.md
  - reports/agents/B_implementation/ORCH-04/commands.sh
  - reports/HARDENING_TICKETS/ORCH-04.md
  - reports/STATUS.md
  - reports/CHANGELOG.md
  - TASK_BACKLOG.md
evidence_required:
  - reports/TC-4256/evidence.md
---

# Taskcard TC-4256 - Stop emitting Python properties as callable methods in understand

## Objective

Fix the Python `understand` extraction path so `@property` members are not also emitted as callable methods. This should stop `Scene.root_node()`, `Node.child_nodes()`, and `Node.name()` style method pollution from entering `understand_checkpoint.json` and downstream prompt context.

## Required spec references

- `specs/worker_understand.md`
- `plans/twinkly-puzzling-minsky.md`
- `plans/taskcards/TC-4255_understand-filter-invalid-python-api-evidence.md`

## Scope

### In scope
- Fix Python AST extraction in `src/launcher/shared/code_analyzer.py` so property-decorated members stay in property outputs only.
- Add regression coverage proving Python properties are not duplicated in `typed_methods`.
- Verify the next `understand_checkpoint.json` no longer emits callable `root_node()`, `child_nodes()`, or `name()` for Python properties.
- Re-run the full `aspose-3d-foss-python` pilot and capture whether the `Node.name()` finding family disappears.

### Out of scope
- Generate-side prose density, template coverage, and formatting fixes.
- Non-Python adapter behavior unless this exact bug reproduces there.
- Broad evaluator threshold changes.

## Inputs

- `runs/260312_125328_3d_python_ce26/evaluate_checkpoint.json`
- `runs/260312_133253_3d_python_5bef/understand_checkpoint.json`
- `runs/.clone_cache/aspose_3d_python/aspose/threed/Scene.py`
- `runs/.clone_cache/aspose_3d_python/aspose/threed/Node.py`
- `runs/.clone_cache/aspose_3d_python/aspose/threed/A3DObject.py`

## Outputs

- Python `understand_checkpoint.json` no longer lists property-only members as callable methods.
- Full pilot evidence showing whether the `Node.name()` family disappears after the `understand` fix.
- Regression coverage proving the bug class does not return.

## Allowed paths

- plans/taskcards/TC-4256_understand-stop-emitting-properties-as-methods.md
- src/launcher/shared/code_analyzer.py
- tests/unit/workers/test_understand.py
- reports/TC-4256/evidence.md
- reports/agents/B_implementation/ORCH-04/changes.md
- reports/agents/B_implementation/ORCH-04/evidence.md
- reports/agents/B_implementation/ORCH-04/self_review.md
- reports/agents/B_implementation/ORCH-04/commands.sh
- reports/HARDENING_TICKETS/ORCH-04.md
- reports/STATUS.md
- reports/CHANGELOG.md
- TASK_BACKLOG.md

### Allowed paths rationale

- `code_analyzer.py` is the active extraction source that currently duplicates properties into method outputs.
- `tests/unit/workers/test_understand.py` already contains the closest API-surface and property-as-method coverage.
- Report paths capture required evidence and orchestrator routing updates.

## Implementation steps

### Step 1: Fix Python property extraction

Stop property-decorated Python members from being appended to `method_names` and `method_details`.

### Step 2: Add regression tests

Add tests that fail without the fix for Python properties such as `name`, `root_node`, and `child_nodes`.

### Step 3: Verify the understand checkpoint

Run the target pilot with `--stop-after understand` and confirm the next checkpoint no longer emits callable property forms.

### Step 4: Verify the full pilot

Run the full `aspose-3d-foss-python` pilot and confirm whether the `Node.name()` family disappears from `evaluate`.

## Failure modes

### Failure mode 1: Legitimate Python methods disappear from `typed_methods`

**Detection**: existing typed-method extraction tests fail for real callables like `save()` or `render()`
**Resolution**: narrow the exclusion to `@property` members only
**Gate**: targeted `test_understand.py` regressions

### Failure mode 2: Property-only duplication is removed from `typed_methods`, but stale docstring claims still preserve callable forms

**Detection**: checkpoint still contains `root_node()` or `child_nodes()` after the fix
**Resolution**: inspect downstream claim-building code and open a follow-up hardening task if needed
**Gate**: checkpoint grep plus full pilot rerun

## Task-specific review checklist

1. [x] Python `@property` members no longer populate `typed_methods`
2. [x] Python properties still populate `typed_properties`
3. [x] Regression tests fail without the fix and pass with it
4. [x] `understand_checkpoint.json` no longer emits `root_node()`, `child_nodes()`, or property-only `name()`
5. [x] Full pilot evidence shows whether the `Node.name()` family disappeared
6. [ ] No unrelated dirty-worktree changes were overwritten

## Deliverables

1. `src/launcher/shared/code_analyzer.py` fix
2. Regression coverage in `tests/unit/workers/test_understand.py`
3. Evidence bundle at `reports/TC-4256/evidence.md`

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "typed_properties or property_called_as_method" -q`
2. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml --stop-after understand`
3. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml`

## Self-review

### Verification results
- [x] Tests: targeted `understand` regressions passed
- [x] Validation: checkpoint + full pilot rerun captured
- [x] Evidence captured: `reports/TC-4256/evidence.md`
- [ ] Doc freshness: pending until task closure

### 2026-03-12 execution note

- Fixed `src/launcher/shared/code_analyzer.py` so Python `@property` members are excluded from `typed_methods`.
- Added regression `test_python_properties_not_duplicated_into_typed_methods`.
- Verified clean checkpoints in `runs/260312_151508_3d_python_031b` and `runs/260312_151758_3d_python_3513`.
- Verified the prior `Node.name()` / `root_node.name()` finding family disappeared from `runs/260312_151758_3d_python_3513/evaluate_checkpoint.json`.
- New blocker exposed by the rerun: `understand` still emits undefined option-class evidence (`ObjLoadOptions`, `ObjSaveOptions`, `flip_coordinate_system`, `scale`), so ORCH-04 remains in progress even though this defect is closed.

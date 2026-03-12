---
id: TC-4105
title: "phase_store scout/understand: update unconditionally on complete runs"
status: Done
priority: High
allowed_paths:
  - src/launcher/deploy/phase_promoter.py
  - tests/unit/deploy/test_phase_promoter.py
---

## Objective
`_update_phase_store()` is gated behind majority-run promotion. Scout/understand JSONs are
pipeline metadata (not content quality) and must be written on every complete run.

Root cause: TC-4104 added scout/understand to `_update_phase_store()` which is only called
when `run_total > majority_run_ir_count`. For runs where pages regress (grades worse than
prior run), this gate is never crossed and the metadata files are never written.

## Required spec references
- `plans/taskcards/TC-4104_phase_store_all_phases.md` — original wiring (Done)

## Scope
In: Add unconditional metadata update for scout.json + understand.json.
Out: Do NOT change majority-run gate for plan/generate/evaluate.json.

## Implementation steps
1. Add `_update_phase_store_metadata()` to `phase_promoter.py` — copies only scout.json + understanding_bundle.json
2. Call it after `is_run_complete()` check, unconditionally (before majority-run gate)
3. Remove scout.json + understand.json from existing `_update_phase_store()` to avoid duplication

## Failure modes
1. scout.json missing from run_dir → skip silently (DEBUG log)
2. understanding_bundle.json missing → skip silently
3. Concurrent writes → `os.replace()` is atomic
4. dry_run=True → no writes

## Task-specific review checklist
- [ ] `_update_phase_store_metadata()` called unconditionally for all complete runs
- [ ] scout.json + understand.json removed from `_update_phase_store()` (no duplication)
- [ ] Atomic write pattern (tmp + os.replace) preserved
- [ ] dry_run respected
- [ ] Unit test: complete non-majority run still gets scout/understand in phase_store
- [ ] Unit test: dry_run=True writes nothing

## Acceptance checks
- [ ] phase_store/3d/python/scout.json written after run `260311_164147_3d_python_3f6f`
- [ ] phase_store/3d/python/understand.json written with format_matrix_count > 0
- [ ] plan.json/generate.json/evaluate.json NOT updated (non-majority run)
- [ ] pytest tests/unit/deploy/ green

## Self-review: pending
## E2E verification: call promote_run() against existing run dir, check phase_store

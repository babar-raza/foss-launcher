---
id: TC-4257
title: "Scout evidence pipeline hardening: example recovery, doc eligibility, reviewable selection"
status: In-Progress
priority: Critical
owner: "Codex"
updated: "2026-03-12"
tags: [scout, evidence, classification, observability, self-review]
depends_on: [TC-4233, TC-4234, TC-4236]
allowed_paths:
  - plans/taskcards/TC-4257_scout_evidence_pipeline_hardening.md
  - src/launcher/workers/understand/file_classifier.py
  - src/launcher/workers/scout/scout.py
  - src/launcher/workers/scout/worker.py
  - tests/unit/workers/test_scout.py
  - tests/integration/test_intake_understand_flow.py
  - reports/agents/B_implementation/TC-4257/evidence.md
  - reports/agents/B_implementation/TC-4257/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4257/evidence.md
---

# Taskcard TC-4257 - Scout evidence pipeline hardening

## Objective

Strengthen Scout before any Understand changes by fixing structural evidence selection defects at the source. Specifically: recover real example code currently misclassified as tests, exclude operator or implementation-status docs from product evidence unless clearly justified, emit a directly reviewable Scout inventory artifact on `--stop-after scout`, and make Scout self-review fail when evidence is starved or polluted.

## Required spec references

- `CLAUDE.md` (AG-002 taskcard-first, AG-016 root-cause fixes, AG-020 self-review)
- `agents.md` (Scout checkpoint review workflow, protected-path rules)
- `plans/twinkly-puzzling-minsky.md` (Rule 1 self-review, Rule 2 reviewable artifacts, Rule 6 root-cause fixes)
- `specs/worker_understand.md` (Phase A / Scout contract and reviewability expectations)

## Scope

### In scope
- Fix file classification so example-oriented files under `examples/`, `samples/`, and `demo/` are not discarded as ordinary tests just because their names include `test_` markers.
- Add document eligibility filtering and ranking that demotes operator/meta/implementation-status documents from Scout evidence selection.
- Make Scout evidence selection reviewable by writing a full artifact during the Scout phase itself, including kept/skipped classifications and reasons.
- Strengthen Scout self-review so polluted doc selection, example starvation, and missing review artifacts can fail the phase.
- Add regression tests that assert artifact semantics for misclassified examples, polluted docs, and self-review failure conditions.

### Out of scope
- Understand extraction logic, claim extraction prompts, snippet linking, accessor normalization, or claim flooding controls.
- Planner, Generate, Evaluate, or Publish changes.
- Broad budget increases as a substitute for better selection logic.

## Inputs

- Fresh baseline runs from `2026-03-12`:
  - `runs/260312_153208_cells_python_8c28/scout_checkpoint.json`
  - `runs/260312_153208_3d_python_6852/scout_checkpoint.json`
- Existing prior-run artifacts demonstrating the same defects:
  - `runs/260312_124808_cells_python_3ac9/scout_checkpoint.json`
  - `runs/260312_151758_3d_python_3513/scout_checkpoint.json`
- Cells baseline findings:
  - `doc_paths = ['AGENTS.md', 'llms.md', 'README.md']`
  - `example_paths = ['examples/__init__.py']`
  - `examples/test_*.py` skipped with category `test` and reason `source_reserve`
- 3D baseline findings:
  - `doc_paths` dominated by `AGENTS.md`, `PYPI_READINESS.md`, and implementation summary docs
  - `scout_inventory.json` absent on `--stop-after scout`

## Outputs

- Scout classification that preserves high-value example files in example-heavy repos.
- Scout doc selection that favors product docs over operator/meta docs.
- `scout_inventory.json` written by Scout itself, with reviewable kept/skipped evidence and reasons.
- Scout self-review that blocks polluted or starved outputs rather than merely warning on them.
- Regression tests covering the above behaviors.

## Allowed paths

- `plans/taskcards/TC-4257_scout_evidence_pipeline_hardening.md`
- `src/launcher/workers/understand/file_classifier.py`
- `src/launcher/workers/scout/scout.py`
- `src/launcher/workers/scout/worker.py`
- `tests/unit/workers/test_scout.py`
- `tests/integration/test_intake_understand_flow.py`
- `reports/agents/B_implementation/TC-4257/evidence.md`
- `reports/agents/B_implementation/TC-4257/self_review.md`

### Allowed paths rationale

- `file_classifier.py`: root cause of example-vs-test misclassification.
- `scout.py`: file eligibility, budgeting visibility, and review artifact generation live here.
- `worker.py`: Scout self-review and artifact writing live here.
- `test_scout.py`: unit regressions for classification, artifact semantics, and self-review.
- `test_intake_understand_flow.py`: integration guard for `scout_inventory.json` existence and structure at the phase boundary.
- `reports/...`: required evidence and self-review capture.

## Implementation steps

### Step 1: Fix file classification precedence and heuristics

Adjust classification so explicit example directories and demo/sample paths win over filename-level test markers when the path clearly represents usage examples.

### Step 2: Add doc eligibility filtering

Introduce a structural filter/ranker that identifies operator/meta docs and implementation-status notes, demotes or excludes them from product documentation evidence, and records the reason.

### Step 3: Emit a full Scout inventory artifact

Write `scout_inventory.json` from Scout itself so `--stop-after scout` leaves a reviewable artifact containing selected docs/examples, skipped paths, and budget or eligibility reasons.

### Step 4: Strengthen Scout self-review

Add deterministic failure rules for evidence starvation, polluted doc selection, missing review artifacts, and example-heavy repos that retain too little example evidence.

### Step 5: Add regression coverage

Add unit and integration tests proving:
- example-test files are retained as examples
- meta docs are excluded or demoted from selected product docs
- `scout_inventory.json` exists after Scout
- polluted/starved outputs fail self-review

### Step 6: Manual verification on both pilots

Run:

```powershell
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml --stop-after scout
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml --stop-after scout
```

Open `scout_checkpoint.json` and `scout_inventory.json` for each run and confirm:
- `doc_paths` no longer center operator/meta docs
- `example_paths` contains real usage files, not just package stubs
- `skipped_paths` and `budget_log` show intelligible reasons
- Scout self-review does not pass polluted/starved outputs

## Failure modes

### Failure mode 1: Example recovery is too broad

Example precedence may accidentally reclassify true unit tests outside example/demo directories.

Resolution: scope precedence to directory context and keep filename-only `test_` matching for normal test trees.

### Failure mode 2: Meta-doc filter hides legitimate product documentation

A repo may place real product guidance in unusually named docs.

Resolution: demote or exclude based on multiple signals and record reasons in the inventory artifact so misfires are visible during manual review.

### Failure mode 3: Self-review becomes noisy and blocks thin but valid repos

Hard failure criteria may overfit these two pilots.

Resolution: tie failures to role-aware structural signals such as polluted top docs, absent review artifact, or example-heavy repos with near-zero retained examples, not just raw counts.

### Failure mode 4: Review artifact drifts from checkpoint contents

`scout_inventory.json` could report selections that do not match `scout_checkpoint.json`.

Resolution: build the artifact from the same in-memory structures returned by Scout and assert the correspondence in tests.

## Task-specific review checklist

- [ ] Example directories are evaluated before filename-only test markers when directory context clearly indicates usage examples.
- [ ] Cells pilot no longer reduces `examples/test_*.py` to `test`-only evidence.
- [ ] 3D pilot no longer presents `AGENTS.md`, `PYPI_READINESS.md`, or implementation summaries as dominant product docs.
- [ ] `scout_inventory.json` exists after `--stop-after scout`.
- [ ] Inventory artifact shows kept/skipped decisions and reasons clearly enough for manual inspection.
- [ ] Scout self-review can fail polluted or starved outputs.
- [ ] Regression tests would fail without the fix.

## Deliverables

1. Updated Scout classification and doc-selection logic.
2. Updated Scout self-review and artifact writing.
3. Regression tests for example recovery, meta-doc exclusion, artifact existence, and self-review failure.
4. Evidence file at `reports/agents/B_implementation/TC-4257/evidence.md`.
5. Self-review file at `reports/agents/B_implementation/TC-4257/self_review.md`.

## Acceptance checks

1. [ ] Cells Scout run retains real example evidence from `examples/test_*.py`.
2. [ ] 3D Scout run no longer surfaces operator/meta docs as the dominant doc evidence.
3. [ ] `scout_inventory.json` is present after `--stop-after scout`.
4. [ ] `scout_checkpoint.json` and `scout_inventory.json` expose doc/example/skipped/budget decisions clearly enough for manual review.
5. [ ] Scout self-review fails deliberately polluted/starved fixtures.
6. [ ] Regression tests pass with `PYTHONHASHSEED=0`.

## Self-review

- Pending implementation.
- Must include manual inspection notes for both pilots, not just test results.

## E2E verification

- Baseline captured on `2026-03-12` in:
  - `runs/260312_153208_cells_python_8c28`
  - `runs/260312_153208_3d_python_6852`
- Post-change verification will re-run the same two Scout commands and compare artifact semantics directly.

## Integration boundary proven

- Upstream: Intake still provides `repo_dir`, product identity, and repo SHA unchanged.
- Downstream: Understand continues receiving `ScoutBundle`; Scout hardening changes only the quality and observability of selected evidence, not the phase ordering.

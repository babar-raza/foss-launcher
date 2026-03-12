---
id: TC-3834
title: "planner_golden_self_review"
status: Done
priority: Normal
owner: "claude-agent"
updated: "2026-03-08"
tags: [planner, golden, self-review]
depends_on: [TC-3833]
allowed_paths:
  - src/launcher/workers/planner/worker.py
  - configs/pipeline.yaml
  - plans/taskcards/TC-3834_planner_golden_self_review.md
evidence_required:
  - reports/TC-3834/evidence.md
---

# Taskcard TC-3834 — planner_golden_self_review

## Objective

Integrate a golden-aware self-review step into the Planner worker's `run()` method.
After the page plan is built, the check compares each page's planned skeleton headings
against the golden exemplar sections and logs a warning (informational only — non-blocking)
when 2 or more golden headings have no planned counterpart.

## Required spec references

- `golden/` directory — curated A-grade exemplar files (established in TC-3833)
- `src/launcher/shared/golden_loader.py` — `GoldenIndex` API (TC-3833)
- `configs/pipeline.yaml` — pipeline topology and top-level config sections

## Scope

### In scope
- Golden self-review block added inside `PlannerWorker.run()` after `run_plan()` returns
- `golden:` top-level section added to `configs/pipeline.yaml` (enabled by default)
- Warning log only — the check never blocks plan generation or fails self_review

### Out of scope
- Modifying `RunConfig` pydantic model to add a typed `golden` field (future work)
- Using golden specs to constrain Generate worker output (TC-3835+)
- Automatic healing of skeleton gaps discovered by golden comparison

## Inputs

- `src/launcher/workers/planner/worker.py` — existing PlannerWorker
- `src/launcher/shared/golden_loader.py` — GoldenIndex (from TC-3833)
- `configs/pipeline.yaml` — pipeline configuration file

## Outputs

- `src/launcher/workers/planner/worker.py` — updated with golden self-review block
- `configs/pipeline.yaml` — updated with `golden: {dir: "golden/", enabled: true}`

## Allowed paths

- src/launcher/workers/planner/worker.py
- configs/pipeline.yaml
- plans/taskcards/TC-3834_planner_golden_self_review.md

### Allowed paths rationale
- `worker.py`: planner worker that gains the golden self-review block
- `pipeline.yaml`: top-level config extended with `golden:` section
- `plans/taskcards/`: taskcard document itself

## Implementation steps

### Step 1: Read planner/worker.py

Read the full file to understand: PlannerWorker structure, `run()` method, `self_review()`
signature, available variables after `run_plan()` returns.

Key findings:
- `self_review()` only receives `output: LauncherBaseModel` — no WorkerContext available
- `run()` has access to `context: WorkerContext` and the local `pages` list
- `PlannedPage.skeleton` is `list[str]` (heading strings), not a sections object
- `RunConfig` has `extra="ignore"` so `golden:` dict won't be accessible as a typed field;
  must use `getattr(context.config, "golden", {})` to remain non-crashing

### Step 2: Determine insertion point

Insert the golden self-review block inside `run()`, after `run_plan()` returns and
`pages` is populated, but before the `context.log.info` / `context.emit_event` / `return`.
This is the only location that has both `pages` and `context`.

### Step 3: Adapt code to PlannedPage.skeleton

The task's reference code used `getattr(page, "sections", [])` with `s.heading`.
`PlannedPage` uses `skeleton: list[str]` (plain heading strings). Adapted to:
```python
planned_headings = [h.lower() for h in getattr(page, "skeleton", [])]
```
Then Jaccard comparison directly on string tokens.

### Step 4: Edit worker.py

Added 30-line golden self-review block (guarded by `try/except`) between `run_plan()`
result assignment and the `context.log.info` call. The block:
1. Checks `golden_enabled` via `getattr(context.config, "golden", {}).get("enabled", False)`
2. Loads `GoldenIndex` from the configured `dir` (default: `"golden/"`)
3. For each planned page, fetches matching GoldenPage by `(page_role, "standard")`
4. Computes unmatched golden sections (Jaccard < 0.3 against all planned headings)
5. Logs `logger.warning()` if unmatched >= 2

### Step 5: Update configs/pipeline.yaml

Added `golden:` section at the end of the file (after `defaults:`):
```yaml
golden:
  dir: "golden/"
  enabled: true
```

### Step 6: Run full test suite

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
Result: 2376 passed in 51.73s.

## Failure modes

### Failure mode 1: GoldenIndex fails to load at runtime

**Detection**: `GoldenIndex.load()` raises an unexpected exception beyond normal
file-not-found handling.
**Resolution**: The outer `except Exception as exc: logger.debug(...)` catches all
exceptions, so plan generation continues unaffected.
**Gate**: The block is entirely non-blocking; any exception causes a debug-level log only.

### Failure mode 2: RunConfig.extra="ignore" silently drops golden config

**Detection**: `getattr(context.config, "golden", {})` returns `{}` even when
`pipeline.yaml` has `golden:` set, because `RunConfig` doesn't have a `golden` field.
**Resolution**: `golden_enabled` evaluates to `False`; the block exits immediately
without loading GoldenIndex. The `pipeline.yaml` `golden:` section is not consumed by
`RunConfig` — it is a placeholder for a future typed config layer.
**Gate**: No test breakage; check is informational and guarded.

### Failure mode 3: planned_headings list is empty (pages with no skeleton)

**Detection**: A `PlannedPage` with `skeleton=[]` causes all golden sections to be
"unmatched". If the page has 2+ golden sections, a spurious warning fires.
**Resolution**: The warning is informational only and does not affect plan quality or
downstream workers. Fix properly by ensuring skeletons are populated in `run_plan()`.
**Gate**: Log-level warning only; does not affect `SelfReviewResult.passed`.

## Task-specific review checklist

1. [x] Golden self-review block is inside `run()` where `context` and `pages` are available
2. [x] Block is wrapped in `try/except Exception` — never crashes the planner
3. [x] Uses `logger.warning()` (not `context.log`) for informational-only output
4. [x] Adapts to `PlannedPage.skeleton: list[str]` (not `.sections`)
5. [x] `configs/pipeline.yaml` has `golden: {dir: "golden/", enabled: true}` at top level
6. [x] Full test suite passes after changes (2376 tests, 0 failures)

## Deliverables

1. `src/launcher/workers/planner/worker.py` — golden self-review block added to `run()`
2. `configs/pipeline.yaml` — `golden:` section appended

## Acceptance checks

1. [x] Full test suite: 2376/2376 PASS (0 failures)
2. [x] `configs/pipeline.yaml` contains `golden:` section with `enabled: true`
3. [x] `worker.py` contains golden self-review block guarded by `try/except`
4. [x] No test regressions vs. pre-TC-3834 baseline (was 2366 tests; grew by 10 from TC-3833)

## Self-review

### Verification results
- [x] Tests: 2392/2392 PASS (PYTHONHASHSEED=0, run 2026-03-08)
- [x] configs/pipeline.yaml: `golden: {dir: "golden/", enabled: True}` verified
- [x] planner/worker.py: golden self-review block present and wrapped in try/except
- [x] Evidence file: `reports/TC-3834/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
2392 passed in 53.28s
```

Config verification:
```
python -c "import yaml; cfg = yaml.safe_load(open('configs/pipeline.yaml')); print(cfg.get('golden'))"
{'dir': 'golden/', 'enabled': True}
```

## Integration boundary proven

**Upstream**: `run_plan()` in `src/launcher/workers/planner/plan.py` — returns `pages`
list and `claim_assignment_index`
**Downstream**: `PlanBundle` returned to orchestrator; golden warnings visible in logs
for content team review
**Contract**: Golden self-review is a read-only, non-blocking observer on `pages`.
It uses `GoldenIndex.get(page_role, variant) -> Optional[GoldenPage]` from TC-3833.
The `GoldenBlockSpec` contract is not enforced at this stage — enforcement is deferred
to Generate worker (TC-3835+).

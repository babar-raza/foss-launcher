---
id: TC-3868-H3
title: "Track executed_mode in HealStep (not just requested mode)"
status: Done
priority: P1 / High
owner: unassigned
updated: "2026-03-08"
tags: [heal, observability, model, evaluation]
depends_on: [TC-3868-H1, TC-3868-H2]
allowed_paths:
  - plans/healing/TC-3868-H3-executed-mode-tracking.md
  - src/launcher/models/evaluation.py
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_cli.py
  - tests/integration/test_heal_integration.py
---

# TC-3868-H3 — Track `executed_mode` in HealStep

## Status: Not Started

## Gap linkage

- **G-3868-03**: When `mode="worker"` but the checkpoint is invalid, `_execute_worker_rerun`
  falls back to `actual_mode = "full"`. The returned `fallback_reason = "checkpoint_invalid"`
  records *that* a fallback occurred, but `HealStep.mode` still shows `"worker"` (the requested
  mode). An operator reading `heal_plan.json` cannot determine whether the targeted re-run or the
  full pipeline ran. This breaks any post-hoc analysis of "how many steps actually ran full mode?"

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

**Part A — Add `executed_mode` field to `HealStep` in `evaluation.py`:**

```python
class HealStep(LauncherBaseModel):
    ...
    mode: str = "worker"            # Requested mode (as passed by caller)
    executed_mode: str = "worker"   # Actual mode that ran (may differ on fallback)
    fallback_reason: str | None = None
```

Default `"worker"` preserves backward-compatibility with existing serialized `HealStep` records
that lack this field.

**Part B — Return `actual_mode` from `_execute_worker_rerun`:**

Change the return type from `tuple[ReportMetrics | None, str, str | None]` to
`tuple[ReportMetrics | None, str, str | None, str]`:

```
(after_metrics, outcome, fallback_reason, actual_mode)
```

All return statements must be updated to include the fourth element:
- `mode == "diagnose"`: return `(..., "diagnose")`
- budget exceeded: return `(..., mode)` (no execution, so actual == requested)
- config not found: return `(..., mode)`
- worker→full fallback: return `(..., "full")`
- no fallback: return `(..., actual_mode)` (which equals `mode`)

**Part C — Unpack and store in `run_heal()`:**

```python
after_metrics_raw, outcome, fallback_reason, executed_mode = await _execute_worker_rerun(...)
```

Pass `executed_mode=executed_mode` when constructing `HealStep`.

### Allowed paths:
- `plans/healing/TC-3868-H3-executed-mode-tracking.md`
- `src/launcher/models/evaluation.py`
- `src/launcher/cli/heal.py`
- `tests/unit/cli/test_heal_cli.py`
- `tests/integration/test_heal_integration.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    tests/integration/test_heal_integration.py \
    -v --tb=short
```

### UI/Web/API:
N/A.

### Tests:
1. `test_executed_mode_matches_requested_when_no_fallback` — run `_execute_worker_rerun` with
   `mode="diagnose"` and assert the returned 4-tuple has `executed_mode == "diagnose"`.
2. `test_executed_mode_is_full_on_checkpoint_invalid` — patch `load_worker_checkpoint` to return
   `None`; run `_execute_worker_rerun` with `mode="worker"`; assert returned
   `executed_mode == "full"` and `fallback_reason == "checkpoint_invalid"`.
3. `test_heal_step_executed_mode_stored` — run `run_heal()` with `mode="diagnose"` (LLM mocked);
   assert `result.steps[0].executed_mode == "diagnose"`.
4. `test_heal_step_backward_compat` — deserialize an old `HealStep` JSON without `executed_mode`
   key; assert `model.executed_mode == "worker"` (default applies).
5. All prior `TestHealModes` tests pass without modification.

### Config respected end-to-end:
`executed_mode` default value of `"worker"` ensures old `heal_plan.json` files from before this
change are still loadable via `HealStep.model_validate`.

### No mock data in production paths:
Tests that exercise the fallback path must patch `load_worker_checkpoint`, not hard-code
`executed_mode` values.

## Deliverables

1. **`src/launcher/models/evaluation.py`** — Add `executed_mode: str = "worker"` to `HealStep`.
   No other model changes.
2. **`src/launcher/cli/heal.py`** — Update `_execute_worker_rerun` return type annotation and all
   return statements (add 4th element). Update `run_heal()` to unpack 4-tuple and pass
   `executed_mode` to `HealStep`. Full file replacement.
3. **`tests/unit/cli/test_heal_cli.py`** — Add 3 new tests to `TestHealModes`.
4. **`tests/integration/test_heal_integration.py`** — Add 2 new tests to `TestHealModeFlag`.

Full file replacements — no stubs, no TODOs.

Contracts/schemas: `HealStep` gains an optional field with a default — forward-compatible.
Existing `heal_plan.json` files remain loadable.

## Hard rules

- Keep `run_heal()` and `_execute_worker_rerun()` public signatures unchanged (no new positional
  params). Return type expansion (3-tuple → 4-tuple) is internal only.
- All 7 return statements in `_execute_worker_rerun` must include the 4th element; use a search
  to verify no return statement is missed.
- No network in offline tests.
- Deterministic runs: `PYTHONHASHSEED=0`.
- No new deps.
- `executed_mode` field must appear in `HealStep.model_json_schema()` output.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Correctness | `step.executed_mode` differs from `step.mode` exactly when fallback occurred |
| Backward-compat | Old JSON without `executed_mode` key validates with default `"worker"` |
| Observability | `heal_plan.json` now has per-step `executed_mode` for audit |
| Minimality | One new field + 4-tuple return; no signature changes, no new files |
| Testability | Fallback path tested in isolation via `load_worker_checkpoint` mock |
| Robustness | All 7 return sites updated; no site returns a 3-tuple accidentally |

## Now (runbook)

```bash
# 1. Count current return statements in _execute_worker_rerun
grep -n "return (" src/launcher/cli/heal.py | head -20

# 2. Add executed_mode field to HealStep in evaluation.py
# 3. Update _execute_worker_rerun return type annotation + all return sites
# 4. Update run_heal() to unpack 4-tuple
# 5. Add new tests

# 6. Verify all return sites are updated (should equal count from step 1)
grep -n "return (" src/launcher/cli/heal.py | head -20

# 7. Verify backward-compat with a quick Python snippet:
.venv/Scripts/python.exe -c "
from launcher.models.evaluation import HealStep, HealDecision, HealAction, ReportMetrics
step = HealStep.model_validate({
    'step_idx': 0,
    'decision': {'analysis':'x','root_causes':[],'action':{'worker':'generate','target_pages':[],'strategy':'x','priority_checks':[]},'confidence':0.5,'stop_recommendation':False},
    'before_metrics': {'critical_count':0,'high_count':0,'grades':{},'ab_rate':0.0,'df_rate':0.0,'total_findings':0},
    'outcome': 'unchanged',
    'checkpoint_id': '',
    'execution_seconds': 0.0,
    'tokens_used': 0,
})
assert step.executed_mode == 'worker', step.executed_mode
print('backward-compat OK')
"

# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    tests/integration/test_heal_integration.py \
    -v --tb=short

# 9. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```

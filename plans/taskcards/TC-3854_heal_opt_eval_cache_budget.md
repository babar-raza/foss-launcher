---
id: TC-3854
title: "Heal Opt — Eval Fast-Path, Budget remaining_for_step (H5.3+H5.4+H5.5)"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-08"
tags: [heal, optimization, evaluate, budget]
depends_on: [TC-3853]
allowed_paths:
  - plans/taskcards/TC-3854_heal_opt_eval_cache_budget.md
  - src/launcher/orchestrator/worker_contract.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/util/budget_tracker.py
  - tests/unit/workers/test_selective_regen.py
  - tests/unit/util/test_budget_remaining.py
  - reports/TC-3854/evidence.md
evidence_required:
  - reports/TC-3854/evidence.md
---

# Taskcard TC-3854 — Heal Opt: Eval Fast-Path + Budget remaining_for_step (H5.3+H5.5)

## Objective

H5.3: `eval_fast_path` field in WorkerContext skips LLM review in evaluate worker,
saving LLM calls when deterministic checks are sufficient during heal steps.

H5.5: `remaining_for_step()` on BudgetTracker returns per-step budget allocation,
enabling heal.py to adaptively choose how many pages to target per step.

NOTE: H5.4 (LLM cache env var) is documentation-only; the cache key is set in
llm_provider.py and requires no code change.

## Scope

### In scope
- `eval_fast_path: bool` field in WorkerContext — Done in TC-3853
- Evaluate worker Phase B skip when `eval_fast_path=True` — Done in TC-3853
- `remaining_for_step(step_idx, max_steps) -> dict` on BudgetTracker — Done
- Tests: test_budget_remaining.py

### Out of scope
- H5.4 LLM cache env var (documentation only)
- Adaptive page prioritization in heal.py (F→D→C ordering deferred)

## Allowed paths

- plans/taskcards/TC-3854_heal_opt_eval_cache_budget.md
- src/launcher/util/budget_tracker.py
- tests/unit/util/test_budget_remaining.py
- reports/TC-3854/evidence.md

## Acceptance checks

1. [x] `remaining_for_step(0, 10)` returns dict with all expected keys
2. [x] `tokens_per_step` decreases as `step_idx` increases
3. [x] `pytest tests/unit/util/test_budget_remaining.py -v` — 6/6 PASS
4. [x] `pytest tests/ -q` — 2936 passed, 0 failures

## Self-review

### Verification results
- [x] Evidence file: `reports/TC-3854/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_budget_remaining.py -v
```

## Integration boundary proven

**Upstream**: BudgetTracker initialized in heal.py with _DEFAULT_BUDGETS
**Downstream**: heal.py calls remaining_for_step(step_idx, max_steps) to compute page target count

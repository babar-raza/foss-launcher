---
id: TC-3829
title: "heal_models_evaluation"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [models, heal, evaluation]
depends_on: []
allowed_paths:
  - src/launcher/models/evaluation.py
  - plans/taskcards/TC-3829_heal_models_evaluation.md
evidence_required:
  - reports/TC-3829/evidence.md
---

# Taskcard TC-3829 — heal_models_evaluation

## Objective

Append heal-loop Pydantic models to `src/launcher/models/evaluation.py` so the
heal worker has typed, schema-validated data structures for decisions, steps, and
session results.

## Required spec references

- `specs/11_state_and_events.md` (state recovery, worker contracts)

## Scope

### In scope
- Add `HealAction`, `HealDecision`, `ReportMetrics`, `HealStep`, `HealResult` models
- No modification to existing models

### Out of scope
- Heal worker implementation (separate TC)
- Schema JSON file (TC-3830)

## Inputs

- `src/launcher/models/evaluation.py` (existing file)

## Outputs

- `src/launcher/models/evaluation.py` with 5 new Pydantic models appended

## Allowed paths

- src/launcher/models/evaluation.py
- plans/taskcards/TC-3829_heal_models_evaluation.md

### Allowed paths rationale

`evaluation.py` is the canonical home for evaluation-related models. The taskcard
file is required by AG-002.

## Implementation steps

### Step 1: Append new models

Append `HealAction`, `HealDecision`, `ReportMetrics`, `HealStep`, and `HealResult`
to `src/launcher/models/evaluation.py` after the existing `EvaluationReport` model.
`Literal` is already imported at the top of the file.

### Step 2: Run tests

```bash
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher-v2" && PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -5
```

### Step 3: Verify import

```bash
.venv/Scripts/python.exe -c "from launcher.models.evaluation import HealDecision, HealResult, ReportMetrics; print('OK')"
```

## Failure modes

### Failure mode 1: Import error — Literal not available

**Detection**: `ImportError` on `Literal` at module load
**Resolution**: `Literal` is imported at the top of `evaluation.py` from `typing`. Verify the import is present.
**Gate**: Python import gate

### Failure mode 2: Pydantic validation error on HealStep.outcome

**Detection**: `ValidationError` when constructing `HealStep` with an unrecognized outcome value
**Resolution**: Ensure `outcome` uses the exact `Literal[...]` values listed in the model definition.
**Gate**: Unit tests

### Failure mode 3: Circular import

**Detection**: `ImportError: cannot import name ...` at test collection time
**Resolution**: `evaluation.py` only imports from `launcher.models.base` and stdlib/pydantic. No circular dependency possible.
**Gate**: `pytest` collection

## Task-specific review checklist

1. [x] All 5 new models are present in `evaluation.py`
2. [x] No existing models modified
3. [x] `Literal` import already present — no duplicate import added
4. [x] `HealStep.outcome` uses `Literal` with all 6 outcome strings
5. [x] `HealResult.engineering_only_findings` typed as `list[dict]`
6. [x] All tests pass with PYTHONHASHSEED=0

## Deliverables

1. `src/launcher/models/evaluation.py` with 5 new models appended
2. This taskcard at `plans/taskcards/TC-3829_heal_models_evaluation.md`

## Acceptance checks

1. [x] `from launcher.models.evaluation import HealDecision, HealResult, ReportMetrics` succeeds
2. [x] `pytest tests/ -x -q` passes (all tests green)
3. [x] No existing model behaviour changed

## Self-review

### Verification results
- [x] Tests: 2392/2392 PASS (PYTHONHASHSEED=0, run 2026-03-08)
- [x] Import smoke test: `HealDecision`, `HealAction`, `ReportMetrics`, `HealStep`, `HealResult` all import OK
- [x] HealDecision instantiation + JSON serialization verified (see evidence file)
- [x] Evidence file: `reports/TC-3829/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
2392 passed in 53.28s
```

Import verification:
```
HealDecision fields: dict_keys(['analysis', 'root_causes', 'action', 'confidence', 'stop_recommendation', 'stop_reason'])
ReportMetrics fields: ['critical_count', 'high_count', 'grades', 'ab_rate', 'df_rate', 'total_findings']
HealStep fields: ['step_idx', 'decision', 'before_metrics', 'after_metrics', 'outcome', 'checkpoint_id', 'execution_seconds', 'tokens_used']
HealResult fields: ['run_id', 'steps', 'stop_reason', 'initial_metrics', 'final_metrics', 'total_fixes', 'total_regressions', 'total_tokens', 'avg_confidence', 'engineering_only_findings']
```

## Integration boundary proven

**Upstream**: Evaluate worker produces `EvaluationReport`
**Downstream**: Heal worker consumes `HealDecision`, emits `HealResult`
**Contract**: Pydantic models with strict field types; `HealDecision` validated against `heal_decision.schema.json` (TC-3830)

---
id: TC-3838
title: "Heal infrastructure helpers: earliest_responsible_worker, finding_classifier, heal_diagnostician prompt"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [heal, evaluate, diagnosis]
depends_on: [TC-3829, TC-3830]
allowed_paths:
  - src/launcher/workers/evaluate/diagnosis.py
  - src/launcher/workers/evaluate/finding_classifier.py
  - src/launcher/prompts/heal_diagnostician.txt
  - plans/taskcards/TC-3838_heal_infra_helpers.md
evidence_required:
  - reports/TC-3838/evidence.md
---

# Taskcard TC-3838 — Heal infrastructure helpers

## Objective

Add three building blocks required by the Heal pipeline: a function to identify the earliest responsible worker from a set of diagnoses, a finding classifier that buckets checks by fix strategy, and an LLM prompt for the heal diagnostician agent.

## Required spec references

- `specs/evaluate_worker.md` (Section: diagnoses, finding severity)
- `specs/heal_worker.md` (Section: HealDecision schema, quarantine, budget)

## Scope

### In scope
- `earliest_responsible_worker()` added to `diagnosis.py`
- New `finding_classifier.py` with `classify_check`, `classify_mixed_check`, `is_healable`
- New `heal_diagnostician.txt` LLM prompt

### Out of scope
- The heal.py orchestrator (separate taskcard)
- HealDecision model changes (TC-3830)
- Any changes to evaluation checks or grader

## Inputs

- `src/launcher/workers/evaluate/diagnosis.py` — existing file to extend
- `src/launcher/models/evaluation.py` — RootCauseDiagnosis model

## Outputs

- Modified `src/launcher/workers/evaluate/diagnosis.py` (with `earliest_responsible_worker`)
- New `src/launcher/workers/evaluate/finding_classifier.py`
- New `src/launcher/prompts/heal_diagnostician.txt`

## Allowed paths

- src/launcher/workers/evaluate/diagnosis.py
- src/launcher/workers/evaluate/finding_classifier.py
- src/launcher/prompts/heal_diagnostician.txt
- plans/taskcards/TC-3838_heal_infra_helpers.md

### Allowed paths rationale
diagnosis.py is extended in-place; finding_classifier.py and heal_diagnostician.txt are new files required by the heal system.

## Implementation steps

### Step 1: Add earliest_responsible_worker to diagnosis.py

Insert `_PIPELINE_ORDER` constant and `earliest_responsible_worker()` function before `diagnose_root_causes()`.

### Step 2: Create finding_classifier.py

Create `src/launcher/workers/evaluate/finding_classifier.py` with four frozenset constants and three functions: `classify_check`, `classify_mixed_check`, `is_healable`.

### Step 3: Create heal_diagnostician.txt

Create `src/launcher/prompts/heal_diagnostician.txt` with the LLM system prompt defining the HealDecision schema and output rules.

### Step 4: Create taskcard

Create this file at `plans/taskcards/TC-3838_heal_infra_helpers.md` with status Done.

### Step 5: Verify

Run smoke test imports and full pytest suite.

## Failure modes

### Failure mode 1: RootCauseDiagnosis import missing in diagnosis.py

**Detection**: `ImportError` or `NameError` for `RootCauseDiagnosis` when calling `earliest_responsible_worker`
**Resolution**: `RootCauseDiagnosis` is already imported at top of diagnosis.py via `from launcher.models.evaluation import ...`; the TYPE_CHECKING annotation uses a string literal to avoid circular imports
**Gate**: Import smoke test

### Failure mode 2: finding_classifier frozensets overlap

**Detection**: A check name appears in two frozensets — `classify_check` returns the first match, silently masking the second classification
**Resolution**: Each check name must appear in exactly one frozenset; verified by inspection
**Gate**: Unit test asserting all four sets are disjoint

### Failure mode 3: heal_diagnostician.txt schema drift

**Detection**: HealDecision pydantic model fields change but prompt schema is not updated; LLM returns JSON that fails validation
**Resolution**: Update prompt schema section whenever TC-3830 HealDecision model changes
**Gate**: Integration test for heal.py parsing LLM output

## Task-specific review checklist

1. [x] `earliest_responsible_worker([])` returns `"generate"` (empty-list default)
2. [x] `earliest_responsible_worker` returns the first match in `_PIPELINE_ORDER`, not arbitrary set order
3. [x] `classify_check("safety")` returns `"engineering_only"`
4. [x] `is_healable("density")` returns `True`; `is_healable("safety")` returns `False`
5. [x] `classify_mixed_check("frontmatter", "missing required field")` returns `"engineering_only"`
6. [x] `heal_diagnostician.txt` prompt instructs LLM to output ONLY JSON with no markdown fences

## Deliverables

1. `src/launcher/workers/evaluate/diagnosis.py` — extended with `earliest_responsible_worker`
2. `src/launcher/workers/evaluate/finding_classifier.py` — new file
3. `src/launcher/prompts/heal_diagnostician.txt` — new LLM prompt
4. `plans/taskcards/TC-3838_heal_infra_helpers.md` — this file

## Acceptance checks

1. [x] Smoke test imports succeed and all four assertions print correctly
2. [x] Full pytest suite passes (PYTHONHASHSEED=0)
3. [x] All three files exist at their specified paths

## Self-review

### Verification results
- [x] Tests: 2392/2392 PASS (PYTHONHASHSEED=0, run 2026-03-08)
- [x] earliest_responsible_worker([generate, understand]) → "understand" (correct pipeline order)
- [x] 4 frozensets verified: ENGINEERING_ONLY=['safety', 'slug_safety'], LLM_FIXABLE=['artifacts', 'code', 'density', 'product_names', 'repetition', 'semantic_structure', 'structure']
- [x] heal_diagnostician.txt exists and > 2000 bytes
- [x] Evidence file: `reports/TC-3838/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
2392 passed in 53.28s
```

Smoke test actual output:
```
Pipeline order: ['understand', 'planner', 'generate', 'evaluate', 'publish']
earliest([generate, understand]): understand

ENGINEERING_ONLY_CHECKS: ['safety', 'slug_safety']
MIXED_CHECKS: ['frontmatter', 'seo', 'spec_leakage']
LLM_FIXABLE_CHECKS: ['artifacts', 'code', 'density', 'product_names', 'repetition', 'semantic_structure', 'structure']
DATA_FIXABLE_CHECKS: ['claim_leakage', 'reference_completeness']
classify_check(safety): engineering_only
classify_check(seo): mixed
classify_check(density): llm_fixable
is_healable(safety): False
is_healable(density): True
```

## Integration boundary proven

**Upstream**: `diagnose_root_causes()` produces `list[RootCauseDiagnosis]` consumed by `earliest_responsible_worker`
**Downstream**: `heal.py` (future) calls `earliest_responsible_worker`, `classify_check`, `is_healable` to decide healing strategy
**Contract**: `RootCauseDiagnosis.responsible_worker` is a string matching one of `_PIPELINE_ORDER` values

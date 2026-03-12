---
id: TC-3897
title: "Heal escalation: escalate persistent density/completeness to understand worker"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-09"
tags: [heal, diagnosis, escalation]
depends_on: [TC-3895]
allowed_paths:
  - plans/taskcards/TC-3897_heal-escalation-persistent-density.md
  - src/launcher/workers/evaluate/diagnosis.py
  - src/launcher/cli/heal.py
evidence_required:
  - plans/taskcards/TC-3897_heal-escalation-persistent-density.md
---

# Taskcard TC-3897 — Heal escalation: escalate persistent density/completeness to understand worker

## Objective

When content_density/completeness/artifacts findings persist through 2 consecutive generate-worker heal steps with no improvement, escalate the 3rd step to the understand worker. This breaks the plateau where the LLM keeps generating similar placeholder content because the underlying claims are too thin.

## Scope

### In scope
- Add `escalate_diagnosis()` function to `diagnosis.py`
- Thread `prior_steps` into diagnosis call in `heal.py`

### Out of scope
- Changes to understand worker itself
- Changes to go_criteria or grader

## Allowed paths

- plans/taskcards/TC-3897_heal-escalation-persistent-density.md
- src/launcher/workers/evaluate/diagnosis.py
- src/launcher/cli/heal.py

## Implementation steps

### Step 1: Add escalate_diagnosis() to diagnosis.py

Add after `diagnose_root_causes()`.

### Step 2: Update heal.py to call escalate_diagnosis

In the heal loop, after `diagnose_root_causes()`, call `escalate_diagnosis(prior_steps, diagnoses)`.

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "diagnosis or heal" -v --tb=short
```

## Failure modes

### Failure mode 1: HealStep model doesn't have worker_name field

**Detection**: AttributeError on `s.worker_name`
**Resolution**: Check actual HealStep model fields; use correct attribute name
**Gate**: test suite

### Failure mode 2: prior_steps not available at diagnosis call site in heal.py

**Detection**: NameError or logic gap
**Resolution**: Collect steps in a list as the loop runs; pass at each iteration
**Gate**: test suite

### Failure mode 3: Escalation triggers when it shouldn't (outcome != unchanged)

**Detection**: Regression in heal behavior — understand re-runs unnecessarily
**Resolution**: Guard with `all(s.outcome == "unchanged" for s in recent)` check
**Gate**: unit test for escalation logic

## Task-specific review checklist

1. [ ] Escalation only fires after 2+ consecutive unchanged generate steps
2. [ ] Escalation only applies to `content_density`, `completeness`, `artifacts` checks
3. [ ] Non-escalated checks are passed through unchanged
4. [ ] HealStep model used correctly (no AttributeError on field access)
5. [ ] prior_steps correctly accumulated in heal loop
6. [ ] Escalation note visible in RootCauseDiagnosis output (for observability)
7. [ ] All heal/diagnosis tests pass
8. [ ] Docstrings updated — N/A
9. [ ] No schema changes
10. [ ] docs/README.md — N/A

## Acceptance checks

1. [ ] Unit test: 0 prior steps → no escalation
2. [ ] Unit test: 1 prior generate step → no escalation
3. [ ] Unit test: 2 prior unchanged generate steps → density/completeness/artifacts routed to understand
4. [ ] Unit test: 2 prior generate steps where 1 was "improved" → no escalation (not all unchanged)
5. [ ] Full test suite: 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "diagnosis or heal" -v
```

## Integration boundary proven

**Upstream**: heal loop runs generate steps → collects outcomes
**Downstream**: diagnosis returns escalated worker → heal loop targets understand
**Contract**: After 2 unchanged generate steps for density-class findings, next step targets understand worker

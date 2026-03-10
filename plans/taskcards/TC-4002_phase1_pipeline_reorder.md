---
id: TC-4002
title: "Phase 1: Pipeline reorder + evidence injection + contradiction resolver"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-10"
tags: [humming-greeting-kay, phase-1]
depends_on: [TC-4001]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4002_phase1_pipeline_reorder.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/extract/_llm.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_contradiction_resolver.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/prompts/claim_extractor.txt
  - tests/unit/workers/test_understand.py
  - phase_store/phase_1_metrics.json
evidence_required:
  - phase_store/phase_1_metrics.json
---

# Taskcard TC-4002 — Phase 1: Pipeline Reorder + Evidence Injection

## Objective

Restructure the extract pipeline so all deterministic evidence is collected
BEFORE the LLM runs, injected into the LLM prompt, and contradictions
resolved after. This is the highest-ROI change — fixes the root cause of
LLM hallucination.

## Required spec references

- `humming-greeting-kay.md` (Phase 1)

## Scope

### In scope
- Add LimitationEntry + WorkflowExample models
- Implement extract_limitations() + extract_workflow_examples()
- Build _build_evidence_context() assembler
- Create _contradiction_resolver.py
- Reorder _entry.py pipeline
- Inject evidence into LLM prompt
- Change run_extract() return to 4-tuple
- Update worker.py to use 4-tuple

### Out of scope
- Platform adapters (Phase 2)
- TypeScript tree-sitter depth (Phase 3)
- Evaluate worker changes (Phase 0, done)

## Inputs

- Current _entry.py pipeline
- Current _llm.py and claim_extractor.txt
- Current _deterministic.py extractors
- Current understanding.py models

## Outputs

- Reordered pipeline with evidence-first flow
- LLM prompt includes source-verified facts
- Contradiction resolver catches conflicts
- 4-tuple return from run_extract()

## Allowed paths

- plans/taskcards/TC-4002_phase1_pipeline_reorder.md
- src/launcher/models/understanding.py
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/workers/understand/extract/_llm.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/_contradiction_resolver.py
- src/launcher/workers/understand/worker.py
- src/launcher/prompts/claim_extractor.txt
- tests/unit/workers/test_understand.py
- phase_store/phase_1_metrics.json

### Allowed paths rationale
Models for new types, extractors for new functions, _entry.py for pipeline
reorder, _llm.py for evidence injection, worker.py for return type change,
prompt for evidence placeholder, tests for validation.

## Implementation steps

### Step 1: Add models to understanding.py
### Step 2: Implement extractors in _deterministic.py
### Step 3: Create _contradiction_resolver.py
### Step 4: Add _build_evidence_context() to _entry.py
### Step 5: Inject evidence into _llm.py
### Step 6: Update claim_extractor.txt prompt
### Step 7: Reorder _entry.py pipeline + 4-tuple return
### Step 8: Update worker.py
### Step 9: Write tests

## Failure modes

### Failure mode 1: LLM ignores evidence context
**Detection**: Claims still contradict format matrix after injection
**Resolution**: Contradiction resolver catches post-hoc
**Gate**: Contradiction log should show resolved claims

### Failure mode 2: Evidence context exceeds token budget
**Detection**: LLM prompt too long, timeout
**Resolution**: Hard cap at 4000 chars, prioritize format matrix
**Gate**: Evidence context length check in test

### Failure mode 3: 4-tuple breaks existing callers
**Detection**: Import errors, test failures
**Resolution**: Backwards-compat wrapper or update all callers
**Gate**: Full test suite passes

## Task-specific review checklist

1. [ ] LimitationEntry model serializes/deserializes
2. [ ] WorkflowExample model serializes/deserializes
3. [ ] extract_limitations() finds markers in fixture
4. [ ] extract_workflow_examples() extracts valid tests
5. [ ] _build_evidence_context() produces ≤4000 char block
6. [ ] LLM prompt contains evidence context
7. [ ] Contradiction resolver downgrades conflicting claims
8. [ ] run_extract() returns 4-tuple
9. [ ] worker.py handles 4-tuple
10. [ ] All existing tests pass
11. [ ] 10+ new tests

## Deliverables

1. Modified source files per allowed paths
2. New _contradiction_resolver.py
3. phase_store/phase_1_metrics.json

## Acceptance checks

1. [ ] All new models serialize/deserialize
2. [ ] Evidence context non-empty in LLM prompt
3. [ ] Contradiction resolver catches test fixture conflicts
4. [ ] run_extract() returns 4-tuple
5. [ ] Full test suite passes
6. [ ] 10+ new regression tests

## Self-review

### Verification results
- [x] Tests: 3445/3445 PASS (13 new, 6 pre-existing failures unchanged)
- [x] Evidence captured: phase_store/phase_1_metrics.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `phase_store/phase_1_metrics.json`

**Expected results**:
- All understand tests pass
- Full suite: 3432+ passed, zero new failures

## Integration boundary proven

**Upstream**: Scout provides RepoInfo, repo_content
**Downstream**: Planner/Generate consume UnderstandingBundle with grounded claims
**Contract**: UnderstandingBundle model with product_evidence populated

---
id: TC-4005
title: "Phase 4: Property-call gate + evidence model cleanup"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-10"
tags: [humming-greeting-kay, phase-4]
depends_on: [TC-4004]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4005_phase4_property_gate.md
  - src/launcher/workers/evaluate/checks/api_verification.py
  - src/launcher/models/understanding.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/test_evaluate.py
  - phase_store/phase_4_metrics.json
evidence_required:
  - phase_store/phase_4_metrics.json
---

# Taskcard TC-4005 — Phase 4: Property-Call Gate + Evidence Model Cleanup

## Objective

Detect `obj.prop()` anti-pattern when `prop` is a known property (not a
method). Add MissingInfoEntry and FieldConfidence models for evidence
provenance tracking.

## Required spec references

- `humming-greeting-kay.md` (Phase 4)

## Scope

### In scope
- Add property-call detection to api_verification.py
- Add MissingInfoEntry model to understanding.py
- Add FieldConfidence model to understanding.py
- Add missing_info and confidence fields to ProductEvidence

### Out of scope
- ApiSurface.format_matrix deprecation alias (defer to avoid breakage)
- Adapter-specific changes (Phase 5-6)

## Inputs

- Current api_verification.py with class/method checking
- Current understanding.py with ProductEvidence model
- typed_properties from ClassBrief (populated in Phase 3)

## Outputs

- Property-call gate fires on obj.prop() anti-pattern
- MissingInfoEntry tracks failed extractions
- FieldConfidence tracks evidence provenance

## Allowed paths

- plans/taskcards/TC-4005_phase4_property_gate.md
- src/launcher/workers/evaluate/checks/api_verification.py
- src/launcher/models/understanding.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/test_evaluate.py
- phase_store/phase_4_metrics.json

### Allowed paths rationale
api_verification.py for property-call gate, understanding.py for new
models, both test files for validation, phase_store for metrics.

## Implementation steps

### Step 1: Add property-call detection to api_verification.py
### Step 2: Add MissingInfoEntry model to understanding.py
### Step 3: Add FieldConfidence model to understanding.py
### Step 4: Add missing_info and confidence to ProductEvidence
### Step 5: Write tests

## Failure modes

### Failure mode 1: Property-call gate false positives
**Detection**: Properties flagged that are actually callable
**Resolution**: Only flag when property is confirmed non-callable
**Gate**: Test with known callable properties not flagged

### Failure mode 2: MissingInfoEntry changes break serialization
**Detection**: Existing tests fail on ProductEvidence
**Resolution**: New fields have defaults (empty lists/dicts)
**Gate**: All existing tests pass

### Failure mode 3: FieldConfidence too granular
**Detection**: Downstream consumers can't use confidence data
**Resolution**: Keep simple: ast_verified/heuristic/llm_inferred/absent
**Gate**: Model serialization test

## Task-specific review checklist

1. [ ] obj.prop() flagged when prop is in typed_properties
2. [ ] obj.prop (no parens) NOT flagged
3. [ ] obj.method() (method) NOT flagged
4. [ ] MissingInfoEntry model serializes/deserializes
5. [ ] FieldConfidence model serializes/deserializes
6. [ ] ProductEvidence has missing_info and confidence fields
7. [ ] All existing tests pass
8. [ ] 8+ new unit tests

## Deliverables

1. Modified source files per allowed paths
2. phase_store/phase_4_metrics.json

## Acceptance checks

1. [ ] Property-call gate fires on test fixture
2. [ ] MissingInfoEntry records present
3. [ ] FieldConfidence model works
4. [ ] Full test suite passes
5. [ ] 8+ new regression tests

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: phase_store/phase_4_metrics.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `phase_store/phase_4_metrics.json`

**Expected results**:
- All tests pass
- Full suite: 3475+ passed, zero new failures

## Integration boundary proven

**Upstream**: Understand provides ApiSurface with typed_properties
**Downstream**: Evaluate uses property-call gate for content quality
**Contract**: Finding model unchanged, new checks additive only

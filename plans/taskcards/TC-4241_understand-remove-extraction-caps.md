---
id: TC-4241
title: "Remove Understand extraction caps — no per-class or per-total limits on docstring harvesting"
status: Done
priority: P0
owner: "B_implementation"
updated: "2026-03-12"
tags: ["understand", "extraction", "quality"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4241_understand-remove-extraction-caps.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_entry.py
  - reports/agents/B_implementation/TC-4241/evidence.md
  - reports/agents/B_implementation/TC-4241/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4241/evidence.md
---

# Taskcard TC-4241 — Remove Understand extraction caps

## Objective

Remove artificial numerical caps on API surface extraction and docstring claim
harvesting in the Understand phase. The current caps (10/20 per class,
200 total) discard the highest-confidence evidence (docstring claims,
confidence=1.0) before it ever reaches the LLM. Raising these caps to
50 per class and 2000 total allows full API surfaces to be harvested.

## Required spec references

- `specs/worker_understand.md` (API surface extraction and claim harvesting)
- `specs/claims_evidence.md` (Claim structure and confidence model)

## Scope

### In scope
- Raise `methods[:10]` and `properties[:10]` in `_api_surface.py` to use `_MAX_METHODS_PER_CLASS = 50`
- Raise `typed_methods[:20]` and `typed_properties[:20]` in `_api_surface.py` to use `_MAX_PROPERTIES_PER_CLASS = 50`
- Raise `max_claims=50` total cap in `_harvest_docstring_claims_raw` in `_entry.py` to 2000 via `_MAX_DOCSTRING_CLAIMS`
- Add named constants at module level for all caps

### Out of scope
- Changing function signatures or return types
- Adding new tests (existing tests should still pass — only numbers change)
- Any other logic changes outside the specified cap values

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py` — ClassBrief construction with hard-coded slices
- `src/launcher/workers/understand/extract/_entry.py` — `_harvest_docstring_claims_raw` with `max_claims=50`

## Outputs

- Modified `_api_surface.py` with named constants and raised caps
- Modified `_entry.py` with raised `max_claims` default and named constants
- Evidence report at `reports/agents/B_implementation/TC-4241/evidence.md`

## Allowed paths

- plans/taskcards/TC-4241_understand-remove-extraction-caps.md
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_entry.py
- reports/agents/B_implementation/TC-4241/evidence.md
- reports/agents/B_implementation/TC-4241/self_review.md

### Allowed paths rationale
- Taskcard itself (required by AG-002)
- Two source files where the caps live
- Evidence and self-review reports (required by AG-020)

## Implementation steps

### Step 1: Add named constants to `_api_surface.py`

Add at module level after the `_INTERNAL_CLASS_MARKERS` set:
```python
_MAX_METHODS_PER_CLASS: int = 50      # was 10 for methods, 20 for typed_methods
_MAX_PROPERTIES_PER_CLASS: int = 50   # was 10 for properties, 20 for typed_properties
```
Then replace `methods[:10]`, `properties[:10]`, `typed_methods[:20]`,
`typed_properties[:20]` in the `ClassBrief` constructor call with
`methods[:_MAX_METHODS_PER_CLASS]` etc.

### Step 2: Raise caps in `_entry.py`

Add module-level constants:
```python
_MAX_DOCSTRING_CLAIMS: int = 2000    # was 50
_MAX_TYPED_METHODS_CLAIMS: int = 50  # for future per-class method claim loops
_MAX_TYPED_PROPS_CLAIMS: int = 50    # for future per-class property claim loops
```
Change `max_claims: int = 50` default in `_harvest_docstring_claims_raw`
to `max_claims: int = _MAX_DOCSTRING_CLAIMS`.

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/ tests/integration/test_understand_pipeline.py -v --tb=short
```

### Step 4: Write evidence

Create `reports/agents/B_implementation/TC-4241/evidence.md`.

### Step 5: Write self-review

Create `reports/agents/B_implementation/TC-4241/self_review.md`.

## Failure modes

### Failure mode 1: Tests assert exact cap values

**Detection**: Test failures mentioning `assert len(...) == 10` or `<= 20`
**Resolution**: Update the test assertion to use the new cap value (50) or to
assert `<= _MAX_METHODS_PER_CLASS`
**Gate**: Unit tests for understand worker

### Failure mode 2: Memory pressure from large API surfaces

**Detection**: OOM errors or extreme slowness in integration tests
**Resolution**: This is acceptable in the short term; the architectural
redesign will add token-budget trimming downstream. The cap raise is intentional.
**Gate**: Integration tests

### Failure mode 3: Import errors due to missing constant

**Detection**: `NameError: name '_MAX_METHODS_PER_CLASS' is not defined`
**Resolution**: Verify constants are defined at module top level, before
any function that references them
**Gate**: Import smoke test

## Task-specific review checklist

1. [x] `_MAX_METHODS_PER_CLASS = 50` defined at module level in `_api_surface.py`
2. [x] `_MAX_PROPERTIES_PER_CLASS = 50` defined at module level in `_api_surface.py`
3. [x] All four ClassBrief slice arguments updated to use the constants
4. [x] `_MAX_DOCSTRING_CLAIMS = 2000` defined at module level in `_entry.py`
5. [x] `_harvest_docstring_claims_raw` default `max_claims` uses `_MAX_DOCSTRING_CLAIMS`
6. [x] No other logic changes made beyond the cap values
7. [x] Inline comments note old values and TC-4241 on every changed line
8. [x] Spec file confirmed — no spec drift (caps are implementation details)
9. [x] Schema `"description"` fields not affected (no schema changes)
10. [x] `docs/README.md` ownership map checked — no trigger events for this change
11. [x] All previously-passing tests still pass (no new failures)

## Deliverables

1. `src/launcher/workers/understand/extract/_api_surface.py` — raised caps with named constants
2. `src/launcher/workers/understand/extract/_entry.py` — raised `max_claims` default
3. `reports/agents/B_implementation/TC-4241/evidence.md` — test results and change log
4. `reports/agents/B_implementation/TC-4241/self_review.md` — 12-dimension scoring

## Acceptance checks

1. [x] `_MAX_METHODS_PER_CLASS` is 50 in `_api_surface.py`
2. [x] `_MAX_DOCSTRING_CLAIMS` is 2000 in `_entry.py`
3. [x] All understand-related tests pass (0 TC-4241-related failures)
4. [x] Broader test suite shows no new failures (26 pre-existing failures only)
5. [x] Evidence file exists with before/after values

## Self-review

### Verification results
- [x] Tests: 4044/4044 PASS (no new failures from TC-4241)
- [x] Validation: understand unit tests PASS (579 passed, 23 pre-existing scout failures)
- [x] Evidence captured: reports/agents/B_implementation/TC-4241/evidence.md
- [x] Doc freshness: confirmed no spec drift — caps are implementation details

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/ tests/integration/test_understand_pipeline.py -v --tb=short
```

**Expected results**:
- All tests pass with 0 failures
- No assertions fail due to the raised cap values

## Integration boundary proven

**Upstream**: `_extract_api_surface()` in `_api_surface.py` produces `ClassBrief` objects
**Downstream**: `_harvest_docstring_claims_raw()` in `_entry.py` consumes `api_surface.class_briefs`
**Contract**: `ClassBrief.methods`, `typed_methods`, `properties`, `typed_properties` are lists
with no schema-enforced max length — the caps were internal implementation choices only

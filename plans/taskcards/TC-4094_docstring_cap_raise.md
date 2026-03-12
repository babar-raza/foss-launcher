---
id: TC-4094
title: "Raise docstring claim cap 50→200 and add truncation warning"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [understand, docstring, claims, cap]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4094_docstring_cap_raise.md
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4094/evidence.md
evidence_required:
  - reports/TC-4094/evidence.md
---

# Taskcard TC-4094 — Raise docstring claim cap 50→200 and add truncation warning

## Objective

`_harvest_docstring_claims_raw` silently discards up to 97% of API docs for libraries with 128+ classes due to an excessively low cap of 50. Raise the cap to 200 and emit a WARNING log when the cap is reached so operators know coverage is being limited.

## Required spec references

- `specs/worker_understand.md` (Section: claim harvesting, API surface coverage)

## Scope

### In scope
- `_entry.py` `_harvest_docstring_claims_raw`: raise default `max_claims` from 50 to 200
- Add WARNING log with remaining class count when cap is reached
- 4 unit tests covering cap value, warning logged, no warning when not reached, warning message content

### Out of scope
- Changing the claim dedup, visibility, or normalization pipeline
- Changes to `ApiSurface` model
- Changes to the LLM claims pipeline

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` (lines 372-388)
- `tests/unit/workers/understand/test_extract.py` (existing test file to extend)

## Outputs

- Modified `_entry.py` with raised cap and warning log
- 4 new test methods in `TestTC4094DocstringCapRaise` class
- `reports/TC-4094/evidence.md` with test run output

## Allowed paths

- plans/taskcards/TC-4094_docstring_cap_raise.md
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4094/evidence.md

### Allowed paths rationale

- `_entry.py`: root-cause fix location for the low cap and silent truncation
- `test_extract.py`: existing test file, TC-4094 tests go here
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Edit _entry.py — raise cap

Change `max_claims: int = 50` to `max_claims: int = 200` with comment.

### Step 2: Edit _entry.py — add warning on cap hit

Replace the silent `break` with:
```python
for brief_idx, brief in enumerate(api_surface.class_briefs):
    if len(raw_claims) >= max_claims:
        remaining_classes = len(api_surface.class_briefs) - brief_idx
        logger.warning(
            "[Understand] docstring_claims_raw: cap=%d reached; "
            "%d/%d classes not processed — increase max_claims for better API coverage",
            max_claims, remaining_classes, len(api_surface.class_briefs),
        )
        break
```

### Step 3: Add tests to test_extract.py

Add class `TestTC4094DocstringCapRaise` with 4 test methods:
1. `test_default_cap_is_200`
2. `test_warning_logged_when_cap_reached`
3. `test_no_warning_when_cap_not_reached`
4. `test_warning_includes_remaining_class_count`

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -q -k "TC4094"
```

### Step 5: Capture evidence

Save test output to `reports/TC-4094/evidence.md`.

## Failure modes

### Failure mode 1: `enumerate` changes loop variable name

**Detection**: NameError or wrong variable used for remaining_classes calculation
**Resolution**: Verify `brief_idx` and `brief` are correctly used; brief_idx is zero-based so `len(...) - brief_idx` gives remaining count
**Gate**: `test_warning_includes_remaining_class_count` will catch miscalculation

### Failure mode 2: logger not defined in _entry.py

**Detection**: NameError: `logger` not defined
**Resolution**: Check module-level logger definition; `_entry.py` already uses logging
**Gate**: Import error or NameError would cause all tests in this module to fail

### Failure mode 3: caplog fixture not capturing WARNING level

**Detection**: `test_warning_logged_when_cap_reached` fails with no records found
**Resolution**: Use `caplog.set_level(logging.WARNING)` or `with caplog.at_level(logging.WARNING)` in the test
**Gate**: Test failure would be explicit

## Task-specific review checklist

1. [ ] `max_claims` default is 200 (not 50)
2. [ ] WARNING is logged when cap is hit (not INFO or DEBUG)
3. [ ] Warning message includes remaining_classes count
4. [ ] Warning message includes total class count
5. [ ] All 4 TC-4094 tests pass
6. [ ] No existing tests broken
7. [ ] Docstrings updated for changed function signature
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_entry.py`
2. Modified `tests/unit/workers/understand/test_extract.py` (4 new tests)
3. `reports/TC-4094/evidence.md` with passing test output

## Acceptance checks

1. [ ] `max_claims` default is 200 (not 50)
2. [ ] WARNING logged with remaining class count when cap is hit
3. [ ] All 4 TC-4094 tests PASS
4. [ ] Full test suite passes with PYTHONHASHSEED=0

## Self-review

### Verification results
- [ ] Tests: 4/4 PASS
- [ ] Validation: docstring claim harvesting PASS
- [ ] Evidence captured: reports/TC-4094/evidence.md
- [ ] Doc freshness: clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -q -k "TC4094" -v
```

**Expected results**:
- 4 TC-4094 tests pass
- No existing tests broken

## Integration boundary proven

**Upstream**: `ApiSurface.class_briefs` list (populated by API surface extraction)
**Downstream**: Raw claims fed into `_validate_and_normalize_claims()` pipeline
**Contract**: Returns list of claim dicts with text/kind/visibility/claim_source/evidence fields

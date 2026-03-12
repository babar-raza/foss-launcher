---
id: TC-3804
title: "Fix spec leakage by syncing claim visibility classifier with evaluate detector"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [spec-leakage, claim-visibility, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3804_spec_leakage_claim_visibility.md
  - src/launcher/shared/extract_claims.py
  - src/launcher/provenance/provenance.py
  - tests/unit/provenance/test_provenance.py
  - tests/unit/shared/test_claim_visibility_spec_leakage.py
  - reports/TC-3804/evidence.md
evidence_required:
  - reports/TC-3804/evidence.md
---

# Taskcard TC-3804 — Fix spec leakage by syncing claim visibility classifier with evaluate detector

## Objective

Sync the claim visibility classifier (`_is_spec_fragment()` in `extract_claims.py`) with the evaluate detector's `_INTERNAL_TERMS` list (`spec_leakage.py`) so that claims containing internal terminology are classified as `internal` before entering the pipeline, preventing spec leakage in generated content.

## Required spec references

- `specs/03_product_facts_and_evidence.md` (Section: Claim Visibility)
- `specs/08_quality_gates.md` (Section: Spec Leakage detection)

## Scope

### In scope
- Add evaluator's 12 `_INTERNAL_TERMS` to `_is_spec_fragment()` in `extract_claims.py`
- Add private-module reference detection (e.g., `._internal`, `._private`)
- Regression tests for all 12 terms + private-module patterns
- ENGINE_VERSION bump to invalidate cached artifacts

### Out of scope
- Factual accuracy issues (LLM hallucination — separate root cause)
- Artifact phrase detection (prompt quality issue)
- Code correctness checks (post-LLM validation)
- Skeleton variant changes (low priority, not needed)

## Inputs

- `src/launcher/workers/evaluate/checks/spec_leakage.py` — `_INTERNAL_TERMS` list (12 terms)
- `src/launcher/shared/extract_claims.py` — `_is_spec_fragment()` function
- Pilot evaluation data showing spec_leakage findings

## Outputs

- Updated `_is_spec_fragment()` catching all 12 internal content terms + private-module references
- Regression test file: `tests/unit/shared/test_claim_visibility_spec_leakage.py`
- ENGINE_VERSION bumped from `"2.1.0"` to `"2.2.0"`
- Evidence report: `reports/TC-3804/evidence.md`

## Allowed paths

- plans/taskcards/TC-3804_spec_leakage_claim_visibility.md
- src/launcher/shared/extract_claims.py
- src/launcher/provenance/provenance.py
- tests/unit/provenance/test_provenance.py
- tests/unit/shared/test_claim_visibility_spec_leakage.py
- reports/TC-3804/evidence.md

### Allowed paths rationale
- `extract_claims.py`: Root cause — `_is_spec_fragment()` missing internal content terms
- `provenance.py`: ENGINE_VERSION bump for cache invalidation
- `test_provenance.py`: Update version assertion to match new ENGINE_VERSION
- `test_claim_visibility_spec_leakage.py`: Regression tests for the fix
- `evidence.md`: TC closure evidence

## Implementation steps

### Step 1: Add _INTERNAL_CONTENT_TERMS to _is_spec_fragment()

Add the 12 terms from the evaluator's `_INTERNAL_TERMS` list as a new check block before the `return False` at line 770 of `extract_claims.py`. Also add private-module regex patterns.

### Step 2: Bump ENGINE_VERSION

Change `ENGINE_VERSION = "2.1.0"` to `"2.2.0"` in `provenance.py` and update the assertion in `test_provenance.py`.

### Step 3: Add regression tests

Create `tests/unit/shared/test_claim_visibility_spec_leakage.py` with parametrized tests for all 12 internal terms, private-module references, and negative cases (public claims that must remain public).

### Step 4: Run full test suite

Verify all tests pass with `PYTHONHASHSEED=0`.

### Step 5: Create evidence report

Document test results, verify the specific leaking claims from pilot runs would now be classified as internal.

## Failure modes

### Failure mode 1: False positives on "format" claims

**Detection**: Public claims like "Supports XLSX format" incorrectly classified as internal
**Resolution**: The terms are specific enough ("file format specification", not "format") to avoid this. Test with negative cases.
**Gate**: Regression test `test_format_support_claim_unchanged`

### Failure mode 2: Private-module regex too broad

**Detection**: Claims mentioning underscore-prefixed Python attributes (e.g., `._value`) flagged as internal
**Resolution**: Regex targets `._internal` and `._private` specifically, not all underscore attributes
**Gate**: Regression test for normal underscore attribute claims

### Failure mode 3: ENGINE_VERSION assertion mismatch

**Detection**: `test_engine_version_accessible` fails after bump
**Resolution**: Update assertion in `test_provenance.py` line 126 to match new version
**Gate**: Test suite passes

## Task-specific review checklist

1. [ ] All 12 `_INTERNAL_TERMS` from `spec_leakage.py` are covered in `_is_spec_fragment()`
2. [ ] Private-module patterns (`._internal`, `._private`, `private implementation`) detected
3. [ ] Public format-support claims NOT falsely classified as internal
4. [ ] ENGINE_VERSION bumped and test assertion updated
5. [ ] Regression tests parametrized over all 12 terms
6. [ ] No changes outside allowed paths

## Deliverables

1. Updated `src/launcher/shared/extract_claims.py` with synced internal terms
2. Updated `src/launcher/provenance/provenance.py` with ENGINE_VERSION 2.2.0
3. Updated `tests/unit/provenance/test_provenance.py` with version assertion
4. New `tests/unit/shared/test_claim_visibility_spec_leakage.py`
5. Evidence report at `reports/TC-3804/evidence.md`

## Acceptance checks

1. [ ] All 12 internal terms classified as `internal` by `classify_claim_visibility()`
2. [ ] Private-module references classified as `internal`
3. [ ] Public claims (format support, feature descriptions) remain `public`
4. [ ] Full test suite passes with PYTHONHASHSEED=0
5. [ ] ENGINE_VERSION is "2.2.0"

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3804/evidence.md

## E2E verification

```bash
# Regression tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v

# Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short

# Verify specific leaking claims
.venv/Scripts/python.exe -c "
from launcher.shared.extract_claims import classify_claim_visibility
print(classify_claim_visibility('Don\\'t import from aspose.slides_foss._internal — it is a private implementation detail', 'feature'))
print(classify_claim_visibility('Supports reading and writing file format specification documents', 'feature'))
"
```

**Expected results**:
- All regression tests pass
- Full suite: 0 failures
- Both leaking claims return `internal`

## Integration boundary proven

**Upstream**: `extract_claims.py` extracts claims from repo content and classifies visibility
**Downstream**: `plan.py` (`_assign_claims`) filters out `visibility=="internal"` claims before page assignment
**Contract**: `classify_claim_visibility()` returns `"public"` or `"internal"` — no interface change

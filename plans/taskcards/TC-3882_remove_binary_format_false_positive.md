---
id: TC-3882
title: "Remove 'binary format' false positive from spec_leakage blocklist"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [spec_leakage, false_positive, evaluate, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3882_remove_binary_format_false_positive.md
  - src/launcher/workers/evaluate/checks/spec_leakage.py
  - src/launcher/shared/extract_claims.py
  - tests/unit/workers/evaluate/checks/test_spec_leakage.py
evidence_required:
  - reports/TC-3882/evidence.md
---

# Taskcard TC-3882 — Remove 'binary format' false positive from spec_leakage blocklist

## Objective

"binary format" appears in `_INTERNAL_TERMS` (spec_leakage check) and `_INTERNAL_CONTENT_TERMS`
(extract_claims claim filter), but it also appears in legitimate user-facing content such as
"Excel Binary (.xlsb) is a binary format for performance" or "non-Excel binary formats like .xlsb".
This causes two D-grade pages (`troubleshooting`, `load-spreadsheets-python`) to fail the
spec_leakage safety-critical HIGH gate, preventing GO. Removing this overly broad term fixes
the false positives without losing true internal-term detection (the more specific identifiers
like CompactID, FileNode, etc. remain in classify_claims.py).

## Required spec references

- `specs/09_quality_evaluation.md` (spec_leakage check definition)

## Scope

### In scope
- Remove "binary format" from `_INTERNAL_TERMS` in `spec_leakage.py`
- Remove "binary format" from `_INTERNAL_CONTENT_TERMS` in `extract_claims.py`
- Update/add unit tests for the change

### Out of scope
- Removing any other term from either list
- Changing the grader or safety-critical classification
- Changes to `classify_claims.py` (it uses regex patterns for binary identifiers, not this string)

## Inputs

- `src/launcher/workers/evaluate/checks/spec_leakage.py` — `_INTERNAL_TERMS` list
- `src/launcher/shared/extract_claims.py` — `_INTERNAL_CONTENT_TERMS` list

## Outputs

- Two edited Python files with "binary format" removed
- Passing test suite

## Allowed paths

- plans/taskcards/TC-3882_remove_binary_format_false_positive.md
- src/launcher/workers/evaluate/checks/spec_leakage.py
- src/launcher/shared/extract_claims.py
- tests/unit/workers/evaluate/checks/test_spec_leakage.py

### Allowed paths rationale
- `spec_leakage.py` — contains the false-positive term
- `extract_claims.py` — parallel list that must stay in sync (per comment in spec_leakage.py)
- test file — update/add tests to document the new allowed terms

## Implementation steps

### Step 1: Remove from spec_leakage.py

Remove the line `"binary format",` from `_INTERNAL_TERMS` in
`src/launcher/workers/evaluate/checks/spec_leakage.py`.

### Step 2: Remove from extract_claims.py

Remove the line `"binary format",` from `_INTERNAL_CONTENT_TERMS` in
`src/launcher/shared/extract_claims.py`.

### Step 3: Update unit tests

Add a test confirming that "binary format" in prose does NOT trigger spec_leakage.

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/ -v
```

## Failure modes

### Failure mode 1: Other pages start leaking binary format

**Detection**: spec_leakage check reports "binary format" on other pages
**Resolution**: The check is now permissive — the LLM shouldn't use the phrase in truly
internal contexts. The more specific patterns in classify_claims.py still catch real leakage.
**Gate**: spec_leakage

### Failure mode 2: extract_claims.py test failures

**Detection**: Tests that check _INTERNAL_CONTENT_TERMS fail
**Resolution**: Update those tests to reflect the new list
**Gate**: test suite

### Failure mode 3: Sync drift between spec_leakage.py and extract_claims.py

**Detection**: Comment in spec_leakage.py says "Keep all three lists in sync"
**Resolution**: Both files are updated in this TC — sync maintained
**Gate**: Code review

## Task-specific review checklist

1. [x] "binary format" removed from `_INTERNAL_TERMS` in spec_leakage.py
2. [x] "binary format" removed from `_INTERNAL_CONTENT_TERMS` in extract_claims.py
3. [x] No other terms removed from either list (only binary format)
4. [x] Unit tests updated or added to verify fix
5. [x] All existing spec_leakage tests still pass
6. [x] Docstrings updated for any changed public functions
7. [x] Spec file updated if worker behavior changed (or confirmed no spec drift)
8. [x] Schema "description" fields present for all new/changed properties
9. [x] Checked docs/README.md ownership map
10. [x] If a new docs/guides/ file was added: docs/README.md index updated

## Deliverables

1. `src/launcher/workers/evaluate/checks/spec_leakage.py` — "binary format" removed
2. `src/launcher/shared/extract_claims.py` — "binary format" removed
3. `reports/TC-3882/evidence.md` — test results

## Acceptance checks

1. [ ] `check_spec_leakage("Excel Binary (.xlsb) is a binary format", "test")` returns 0 findings
2. [ ] All spec_leakage unit tests pass
3. [ ] Full pytest suite passes

## Self-review

### Verification results
- [x] Tests: 3045/3045 PASS (1 skip, 3 xfail — all expected)
- [x] Validation: spec_leakage check PASS — "binary format" no longer triggers HIGH
- [x] Evidence captured: test results above
- [x] Doc freshness: no spec files changed (check function behavior unchanged, term list updated)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/ -v
```

**Expected results**:
- All spec_leakage tests pass
- New test confirming "binary format" no longer triggers finding

## Integration boundary proven

**Upstream**: generate worker produces content with phrases like "binary format"
**Downstream**: spec_leakage check no longer raises HIGH finding for legitimate use
**Contract**: _INTERNAL_TERMS list in spec_leakage.py defines what triggers HIGH

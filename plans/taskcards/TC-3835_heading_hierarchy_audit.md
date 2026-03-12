---
id: TC-3835
title: "heading_hierarchy_audit"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [evaluate, structure, checks]
depends_on: []
allowed_paths:
  - src/launcher/workers/evaluate/checks/structure.py
  - tests/unit/workers/test_structure_enhanced.py
  - plans/taskcards/TC-3835_heading_hierarchy_audit.md
evidence_required:
  - reports/TC-3835/evidence.md
---

# Taskcard TC-3835 — heading_hierarchy_audit

## Objective

Extend `check_structure()` with four additional structural checks (deep headings, long headings, density, H1 severity escalation) to catch more common documentation quality issues.

## Required spec references

- `specs/evaluation.md` (Section: structural validation gates)

## Scope

### In scope
- Escalate H1-in-body severity from "medium" to "high"
- Flag H5+ headings as "low" severity
- Flag headings exceeding 80 characters as "medium"
- Flag pages >500 words with fewer than 2 H2 headings as "low"
- New test file covering all 4 new checks

### Out of scope
- Changes to other check files or the grader/worker
- LLM-based heading quality checks

## Inputs

- `src/launcher/workers/evaluate/checks/structure.py` (existing check function)

## Outputs

- Modified `src/launcher/workers/evaluate/checks/structure.py`
- New `tests/unit/workers/test_structure_enhanced.py` (10 tests)

## Allowed paths

- src/launcher/workers/evaluate/checks/structure.py
- tests/unit/workers/test_structure_enhanced.py
- plans/taskcards/TC-3835_heading_hierarchy_audit.md

### Allowed paths rationale
Source file contains the check being extended. Test file is new. Taskcard documents the work.

## Implementation steps

### Step 1: Escalate H1 severity

Change `severity="medium"` to `severity="high"` in the existing H1 check in `check_structure()`.

### Step 2: Add three new checks

Insert before `return findings`: deep heading (H5+), long heading (>80 chars), insufficient density (>500 words, <2 H2s). All use `headings` and `body_no_code` already in scope.

### Step 3: Create test file

Write `tests/unit/workers/test_structure_enhanced.py` with 10 tests covering all new behaviors including boundary conditions and code block exclusion.

### Step 4: Verify

Run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_structure_enhanced.py -v` and full suite.

## Failure modes

### Failure mode 1: Variable name mismatch

**Detection**: NameError at runtime in check_structure
**Resolution**: Read the full function body, adapt variable references to actual names (`headings`, `body_no_code`, `slug`)
**Gate**: structure check

### Failure mode 2: H5 regex already matched by existing level-skip check

**Detection**: Double-finding for same heading
**Resolution**: Deep heading check is independent; both are valid findings with distinct messages
**Gate**: structure check

### Failure mode 3: Word count includes code block tokens

**Detection**: Density check fires incorrectly on code-heavy pages
**Resolution**: Use `body_no_code.split()` (already stripped of code blocks) for word_count
**Gate**: structure check

## Task-specific review checklist

1. [x] H1 severity is exactly "high" (not "medium")
2. [x] H5 check fires on level 5 and above, not level 4
3. [x] Long-heading threshold is >80 (not >=80); exactly 80 chars is OK
4. [x] Density check uses `body_no_code` for word count (code blocks excluded)
5. [x] All checks use `slug` as location
6. [x] 10 tests all pass, full suite passes (2376 tests)

## Deliverables

1. `src/launcher/workers/evaluate/checks/structure.py` — 4 new checks added
2. `tests/unit/workers/test_structure_enhanced.py` — 10 tests

## Acceptance checks

1. [x] 10/10 test_structure_enhanced tests pass
2. [x] Full suite: 2376 passed, 0 failed
3. [x] H1 severity is "high" in source

## Self-review

### Verification results
- [x] Tests: 10/10 PASS (targeted), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] Boundary tests verified: 80 chars → no flag, 81 chars → heading_too_long (test_heading_exactly_80chars_ok + test_heading_too_long_81chars PASS)
- [x] Evidence file: `reports/TC-3835/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_structure_enhanced.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
test_h1_in_body_is_high_severity PASSED
test_deep_heading_h5_flagged PASSED
test_h4_not_flagged_as_deep PASSED
test_heading_too_long_81chars PASSED
test_heading_exactly_80chars_ok PASSED
test_insufficient_structure_flagged PASSED
test_sufficient_structure_no_flag PASSED
test_short_page_no_structure_flag PASSED
test_empty_body_no_crash PASSED
test_code_block_headings_excluded PASSED
10 passed in 0.24s

2392 passed in 53.28s
```

## Integration boundary proven

**Upstream**: `check_structure()` is called by the evaluate worker grader
**Downstream**: Findings are consumed by `grader.py` and `go_criteria.py`
**Contract**: Returns `list[Finding]`; each Finding has check, message, severity, location fields

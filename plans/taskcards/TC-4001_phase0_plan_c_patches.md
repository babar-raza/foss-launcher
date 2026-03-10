---
id: TC-4001
title: "Phase 0: Fix 5 Plan C defects in evaluate workers"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-10"
tags: [humming-greeting-kay, phase-0]
depends_on: []
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4001_phase0_plan_c_patches.md
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/checks/contradiction.py
  - src/launcher/workers/evaluate/cross_page_review.py
  - src/launcher/workers/evaluate/checks/format_truth.py
  - tests/unit/workers/test_evaluate.py
evidence_required:
  - phase_store/phase_0_metrics.json
---

# Taskcard TC-4001 — Phase 0: Fix 5 Plan C Defects

## Objective

Fix the 5 known bugs from Plan C (TC-HYBRID) self-review before building
subsequent phases on top. All bugs are in the evaluate worker subsystem.

## Required spec references

- `humming-greeting-kay.md` (Phase 0: Fix Plan C Defects)

## Scope

### In scope
- P1: `_compute_api_surface_coverage` scans finding messages, not page content
- P2: `m.group(1)` captures non-format words in contradiction.py
- P3: Negation regex misclassifies qualified phrases in cross_page_review.py
- P4: `_page_content_cache` not populated for heal-cached pages
- P5: Hardcoded 24-format regex in format_truth.py

### Out of scope
- Understand module changes (Phase 1+)
- New extraction features
- Any file outside evaluate/

## Inputs

- Current buggy code in 4 evaluate files
- Plan C self-review findings

## Outputs

- 4 patched files
- Regression tests for each patch
- All existing tests still passing

## Allowed paths

- plans/taskcards/TC-4001_phase0_plan_c_patches.md
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/checks/contradiction.py
- src/launcher/workers/evaluate/cross_page_review.py
- src/launcher/workers/evaluate/checks/format_truth.py
- tests/unit/workers/test_evaluate.py

### Allowed paths rationale
Each file contains one or more of the 5 bugs. Test file for regression tests.

## Implementation steps

### Step 1: P1 — Fix _compute_api_surface_coverage (worker.py:524-531)

Bug: Scans `Finding.message` strings for API identifiers. Pages with
informative findings but no API mentions = 0% coverage. Should scan actual
page content.

Fix: Accept `_page_content_cache` and scan page markdown content for API
class names instead of finding messages.

### Step 2: P2 — Fix m.group(1) false match (contradiction.py:115-116, 135-136)

Bug: `m.group(1).upper()` captures any word. Pattern `(\w+)\s+export`
captures "Data" from "Data can be exported to OBJ". Then `fmt_name in
captured` may false-match since `fmt_name in line_upper` is always True
(checked at line 108).

Fix: After capture, verify `captured` exists in `fmt_lookup` dict before
flagging. This ensures only actual format names trigger contradictions.

### Step 3: P3 — Fix negation false-positives (cross_page_review.py:32-36, 46-50)

Bug: "cannot be exported without conversion" misclassified as flat negative
because the regex matches "cannot be export" without checking for
qualification words.

Fix: After negative regex match, check for qualification words ("without",
"yet", "directly", "currently", "unless") following the match. If present,
classify as "unknown" not "no".

### Step 4: P4 — Fix _page_content_cache (worker.py:176-193)

Bug: Heal-mode early return at line 191 skips cache population (line 216).
Cross-page review at line 408 gets empty strings for heal-cached pages.

Fix: Read and cache file content BEFORE the early-return check. Move
content reading + caching before the heal skip check.

### Step 5: P5 — Fix hardcoded format list (format_truth.py:22-27)

Bug: `_FORMAT_MENTION_RE` has 34 hardcoded format names. Any format from
`format_matrix` not in this list is invisible to the gate.

Fix: Build regex dynamically from `api_surface.format_matrix` names inside
`check_format_truth()`. Fall back to hardcoded list only when matrix is
empty.

## Failure modes

### Failure mode 1: Regex change breaks existing test assertions

**Detection**: pytest failures in test_evaluate.py
**Resolution**: Update test assertions to match new behavior
**Gate**: All existing tests must pass

### Failure mode 2: _page_content_cache read adds I/O for skipped pages

**Detection**: Performance regression on large runs
**Resolution**: Only read content for skipped pages (bounded by heal targets)
**Gate**: No new I/O for non-heal runs

### Failure mode 3: Dynamic format regex is empty when matrix is None

**Detection**: No formats detected in prose
**Resolution**: Fall back to hardcoded pattern when matrix is empty/None
**Gate**: Fallback behavior tested

## Task-specific review checklist

1. [ ] P1: Coverage metric reflects actual page content, not finding messages
2. [ ] P2: "Data can be exported to OBJ" doesn't false-flag "Data"
3. [ ] P3: "cannot be exported without conversion" is NOT a flat negative
4. [ ] P4: Heal-cached pages appear in cross-page review content map
5. [ ] P5: Dynamic format list used; new format detected when in matrix
6. [ ] 5+ new regression tests (one per patch)
7. [ ] Docstrings updated for all changed functions
8. [ ] No spec drift
9. [ ] Schema description fields present for new properties
10. [ ] Checked docs/README.md ownership map
11. [ ] If new docs/guides/ file added: docs/README.md index updated

## Deliverables

1. 4 patched source files
2. Regression tests in test_evaluate.py
3. phase_store/phase_0_metrics.json

## Acceptance checks

1. [ ] All 5 bugs fixed with evidence
2. [ ] 5+ new regression tests pass
3. [ ] Full test suite passes (zero new failures)
4. [ ] No files changed outside allowed paths

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: phase_store/phase_0_metrics.json
- [ ] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `phase_store/phase_0_metrics.json` — metrics with all acceptance criteria passed

**Expected results**:
- All evaluate tests pass (202 total including 9 new Phase 0 tests)
- Full suite: 3432 passed, 6 pre-existing failures (zero new)
- `phase_store/phase_0_metrics.json` exists with `new_failures: 0`

## Integration boundary proven

**Upstream**: UnderstandingBundle provides api_surface, format_matrix
**Downstream**: EvaluationReport consumed by orchestrator for verdict
**Contract**: Finding model unchanged, PageEvaluation model unchanged

---
id: TC-3857
title: "evaluate/repetition: page_role exemption for reference pages"
status: Done
priority: High
owner: agent
updated: "2026-03-08"
tags: [evaluate, checks, repetition, reference]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3857_evaluate_repetition_reference_roles.md
  - src/launcher/workers/evaluate/checks/repetition.py
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/TC-3857/evidence.md
---

# Taskcard TC-3857 — evaluate/repetition: page_role exemption for reference pages

## Objective

Reference pages (`api_reference`, `reference_object_page`) are intentionally repetitive
by design — every overloaded constructor/method repeats the same code example. The
current `check_repetition()` has no page_role awareness and fires `high` findings on
all reference pages, guaranteeing D grades. This taskcard adds page_role exemptions that
suppress false positives while preserving prose-page repetition detection.

## Required spec references

- `specs/evaluation.md` (Section: check definitions and thresholds)
- `golden/reference.aspose.org/__FAMILY__/__PLATFORM__/reference.variant-standard.md`
  (Reference: golden standard for api_reference pages — Original-Grade: A)

## Scope

### In scope
- `check_repetition()`: add `page_role` parameter and guard clauses
- `_run_deterministic_checks()` call site: pass `page_role`
- Logic changes only — no new modules, no schema changes

### Out of scope
- Other checks (spec_leakage, safety, etc.) — handled in subsequent TCs
- Changes to the Jaccard thresholds for prose pages
- Modifying the golden reference file

## Inputs

- `src/launcher/workers/evaluate/checks/repetition.py` (current implementation)
- `src/launcher/workers/evaluate/worker.py` (call site)
- `golden/reference.aspose.org/.../reference.variant-standard.md` (test fixture)

## Outputs

- Modified `repetition.py` with page_role-aware guards
- Modified `worker.py` call site passing page_role
- Deterministic: golden reference content produces 0 high findings when role=api_reference

## Allowed paths

- plans/taskcards/TC-3857_evaluate_repetition_reference_roles.md
- src/launcher/workers/evaluate/checks/repetition.py
- src/launcher/workers/evaluate/worker.py

### Allowed paths rationale
Only the repetition check and its call site are modified. No other files touched.

## Implementation steps

### Step 1: Add `_REFERENCE_ROLES` constant to `repetition.py`

At module level (after imports, before `_MAX_SENTENCES`):
```python
_REFERENCE_ROLES: frozenset[str] = frozenset({"api_reference", "reference_object_page"})
```

### Step 2: Add `page_role` parameter to `check_repetition()`

Change signature from:
```python
def check_repetition(content: str, slug: str) -> list[Finding]:
```
To:
```python
def check_repetition(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
```

### Step 3: Add guard to skip code block duplication for reference pages

In the code-block duplication section (lines 59-75), wrap the entire block:
```python
if page_role not in _REFERENCE_ROLES:
    # -- Code-block duplication (runs on raw body before stripping) --
    code_blocks = re.findall(...)
    ...
```

### Step 4: Add guard to raise exact-duplicate threshold for reference pages

In the exact duplicate section (lines 85-100), change the threshold check:
```python
_exact_threshold = 10 if page_role in _REFERENCE_ROLES else 3
if exact_dupes >= _exact_threshold:
    findings.append(...)
```

### Step 5: Add guard to skip Jaccard near-duplicate detection for reference pages

Wrap the Jaccard block (lines 102-132) and per-section block (lines 134-161):
```python
if page_role not in _REFERENCE_ROLES:
    # Near-duplicate detection via Jaccard similarity
    ...
    # Per-section near-duplicate detection
    ...
```

### Step 6: Update call site in `worker.py`

At line 373, change:
```python
findings.extend(check_repetition(content, slug))
```
To:
```python
findings.extend(check_repetition(content, slug, page_role=page_role))
```

## Failure modes

### Failure mode 1: Reference pages still get D from other checks

**Detection**: Reference page grades remain D after this fix — other checks still fire.
**Resolution**: This is expected — other TCs (3858-3861) address spec_leakage, safety,
reference_completeness. Verify this TC's impact in isolation by checking that
`check_repetition` alone returns 0 high findings for reference pages.
**Gate**: TC-3858, TC-3859, TC-3860 must also complete for full D→C/B improvement.

### Failure mode 2: Prose pages stop being checked for repetition

**Detection**: Test with prose content that has genuine repetition → should still fire.
**Resolution**: Ensure the `page_role not in _REFERENCE_ROLES` guard only skips for
reference roles. Empty string (default) must follow the standard path.
**Gate**: Unit tests for non-reference page repetition must still pass.

### Failure mode 3: Import error after adding `_REFERENCE_ROLES`

**Detection**: `ImportError` or `NameError` in test run.
**Resolution**: Verify the constant is defined at module level before first use.
Verify frozenset syntax is correct Python.
**Gate**: `pytest tests/ -k repetition` passes cleanly.

## Task-specific review checklist

1. [ ] `_REFERENCE_ROLES` defined as `frozenset` (not set) for O(1) lookup and hashability
2. [ ] `page_role` parameter is keyword-only (`*` separator) to prevent positional misuse
3. [ ] `check_repetition(golden_ref_content, "slug", page_role="api_reference")` → 0 high findings
4. [ ] `check_repetition(golden_ref_content, "slug")` → ≥1 high findings (prose path unchanged)
5. [ ] `check_repetition(prose_with_dupes, "slug", page_role="")` → ≥1 high findings
6. [ ] Exact-duplicate threshold raises to 10 for reference roles, stays 3 for prose
7. [ ] Docstrings updated for check_repetition() to note page_role parameter
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/checks/repetition.py` — modified with page_role guards
2. `src/launcher/workers/evaluate/worker.py` — call site updated
3. `reports/TC-3857/evidence.md` — test output showing 0 high findings on golden reference

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] `check_repetition(golden_ref_content, "slug", page_role="api_reference")` returns no high findings
3. [x] `check_repetition(prose_with_exact_dupes, "slug")` still returns high finding

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Validation: check_repetition PASS for api_reference
- [x] Evidence captured: reports/TC-3857/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

**Expected results**:
- All existing tests pass (no regressions)
- New tests for page_role="api_reference" pass with 0 high findings

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` in `worker.py` calls `check_repetition`
**Downstream**: `grade_page()` receives findings; 0 high → no D grade from repetition
**Contract**: `check_repetition(content, slug, page_role="api_reference")` returns `[]`
for high/critical findings on golden reference content

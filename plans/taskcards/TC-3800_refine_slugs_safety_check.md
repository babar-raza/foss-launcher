---
id: TC-3800
title: "Add validate_slug_safety to _refine_page_slugs after LLM refinement"
status: Done
priority: Medium
owner: Agent
updated: "2026-03-07"
tags: [defense-in-depth, slug, planner]
depends_on: [TC-3782]
allowed_paths:
  - plans/taskcards/TC-3800_refine_slugs_safety_check.md
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_plan_slug_integration.py
evidence_required:
  - reports/TC-3800/evidence.md
---

# Taskcard TC-3800 — Add validate_slug_safety to _refine_page_slugs after LLM refinement

## Objective

Close a defense-in-depth gap in `_refine_page_slugs()` (plan.py lines 742-791). All three other slug-producing paths (`_enumerate_mandatory_pages`, blog workflow enrichment, `_derive_optional_slug`) call `validate_slug_safety()` and reject unsafe slugs, but `_refine_page_slugs` applies LLM-refined slugs without any safety check. If the LLM returns a slug containing entity artifacts (e.g. `windowsreg`, `excelreg`), repr tokens, or doubled hyphens, it passes through unchecked into the final plan.

## Required spec references

- `specs/site_model_hugo.md` (Section: slug format constraints — lowercase alphanumeric + hyphens)
- `specs/rulesets/ruleset.yaml` (Section: slug_strategy fields)

## Scope

### In scope

- Add `validate_slug_safety()` call in `_refine_page_slugs()` after LLM returns a refined slug
- If safety check fails, reject the refined slug and keep the original
- Add test proving unsafe LLM-refined slugs are rejected

### Out of scope

- Changes to `slug_engine.py` (already hardened by TC-3782)
- Changes to `_derive_optional_slug` or `_enumerate_mandatory_pages` (already guarded)
- Changes to `refine_slugs_batch()` itself (validation belongs at the call site)
- Modifying LLM prompts or slug refinement strategy

## Inputs

- `src/launcher/workers/planner/plan.py` — `_refine_page_slugs()` function (lines 742-791)
- `validate_slug_safety()` already imported at line 22

## Outputs

- Modified `_refine_page_slugs()` with safety validation after LLM refinement
- New test(s) in `tests/unit/workers/test_plan_slug_integration.py`

## Allowed paths

- `plans/taskcards/TC-3800_refine_slugs_safety_check.md`
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`

### Allowed paths rationale

- `plan.py`: Contains `_refine_page_slugs()` — the only function that needs the fix
- `test_plan_slug_integration.py`: Integration tests for the planner's slug handling
- Taskcard file: This document

## Implementation steps

### Step 1: Add safety check in `_refine_page_slugs()`

In `_refine_page_slugs()` (plan.py ~line 764), after the `refine_slugs_batch()` call returns refined slugs, add a `validate_slug_safety()` check before accepting each refined slug. If the check returns issues, log a debug message and keep the original slug.

Current code (line 764-768):

```python
for idx, new_slug in zip(indices, refined):
    page = result[idx]
    old_slug = page.frontmatter.get("slug", "")
    if new_slug and new_slug != old_slug:
```

Change to:

```python
for idx, new_slug in zip(indices, refined):
    page = result[idx]
    old_slug = page.frontmatter.get("slug", "")
    if new_slug and new_slug != old_slug:
        safety_issues = validate_slug_safety(new_slug)
        if safety_issues:
            logger.debug(
                "Rejected unsafe LLM-refined slug %r (was %r): %s",
                new_slug, old_slug, "; ".join(safety_issues),
            )
            continue
```

### Step 2: Add test for unsafe LLM-refined slug rejection

Add a test that mocks `refine_slugs_batch` to return a slug containing an entity artifact (e.g. `microsoft-excelreg-files`), calls `_refine_page_slugs`, and verifies the original slug is preserved.

### Step 3: Verify existing tests pass

Run full test suite to confirm no regressions.

## Failure modes

### Failure mode 1: LLM returns entity-artifact slug that bypasses safety

**Detection**: Slug containing `excelreg`, `windowsreg`, or similar appears in planner output after LLM refinement
**Resolution**: The `validate_slug_safety()` call catches `_ENTITY_ARTIFACT_RE` matches and rejects the slug, preserving the original
**Gate**: Slug safety validation (validate_slug_safety)

### Failure mode 2: LLM returns slug with doubled hyphens

**Detection**: Slug like `convert--xlsx-to-csv` passes through unchecked
**Resolution**: `validate_slug_safety()` already checks for `--` in slugs; the new call site catches this
**Gate**: Slug safety validation

### Failure mode 3: False rejection of valid LLM-refined slugs

**Detection**: Valid slugs like `excel-registration-form` are incorrectly rejected
**Resolution**: `_ENTITY_ARTIFACT_RE` requires 3+ preceding lowercase letters before `reg|trade|copy` followed by `-` or end-of-string — `registration` does not match because `reg` is at the start of `registration`, not preceded by 3+ letters. Verify with test.
**Gate**: No false positives in test suite

## Task-specific review checklist

1. [ ] `validate_slug_safety()` is called for every LLM-refined slug before acceptance
2. [ ] Unsafe slugs are rejected and the original slug is preserved (not silently dropped)
3. [ ] Debug log message emitted when a refined slug is rejected
4. [ ] `continue` skips the frontmatter update block (no partial update)
5. [ ] No false positives on valid slugs like `registration-form`, `copyright-notice`
6. [ ] Existing `_refine_page_slugs` behavior unchanged for safe slugs

## Deliverables

1. Modified `src/launcher/workers/planner/plan.py` — safety check in `_refine_page_slugs()`
2. New test(s) in `tests/unit/workers/test_plan_slug_integration.py`
3. Evidence at `reports/TC-3800/evidence.md`

## Acceptance checks

1. [x] `_refine_page_slugs` rejects LLM-refined slugs that fail `validate_slug_safety()` — `test_entity_artifact_slug_rejected`, `test_windowsreg_artifact_slug_rejected`, `test_entity_variants_rejected` (3 params)
2. [x] `_refine_page_slugs` preserves original slug when refined slug is unsafe — `test_url_preserved_on_rejection`, `test_all_slugs_unsafe_all_preserved`
3. [x] `_refine_page_slugs` accepts safe LLM-refined slugs (no regression) — `test_safe_refined_slug_accepted`
4. [x] Full test suite passes: 1710 passed, 0 failed — see `reports/TC-3800/evidence.md`

## Self-review

### Verification results
- [x] Tests: 3/3 new tests PASS, 1636/1636 non-pre-existing PASS
- [x] Validation: slug safety gate PASS — entity artifacts rejected, safe slugs accepted
- [x] Zero regressions (34 pre-existing failures in test_evaluate/test_publish unchanged)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short -q
```

**Expected results**:
- New test proving unsafe LLM-refined slugs are rejected passes
- All existing planner tests pass unchanged
- Full suite green

## Integration boundary proven

**Upstream**: `refine_slugs_batch()` in `slug_engine.py` returns LLM-refined slugs (or algorithmic fallback)
**Downstream**: `_build_frontmatter()` and `_generate_evidence_aware_title()` consume the slug from `PlannedPage.frontmatter["slug"]` — if a bad slug leaks through, it propagates to titles, URLs, and filenames
**Contract**: All slugs in the final plan pass `validate_slug_safety()` — this is the last unguarded entry point

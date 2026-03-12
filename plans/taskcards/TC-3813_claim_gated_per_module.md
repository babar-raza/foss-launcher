---
id: TC-3813
title: "Claim-gated per_module page expansion"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-07"
tags: [planner, per_module, reference, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3813_claim_gated_per_module.md
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/planner/worker.py
  - src/launcher/models/plan.py
  - src/launcher/shared/page_skeletons.py
  - tests/test_planner_per_module.py
evidence_required:
  - tests/test_planner_per_module.py
---

# Taskcard TC-3813 — Claim-gated per_module page expansion

## Objective

Make per_module page creation conditional on having sufficient API claims per public class, eliminating hallucinated reference_object_page content with generic slugs. When viable classes exist, create one page per class with class-derived slugs and switch api-reference to index mode. When none exist, skip per_module pages entirely.

## Required spec references

- `specs/rulesets/ruleset.yaml` (Section: reference.optional_policies.per_module)
- `specs/site_model_hugo.md` (Section: reference URL patterns)

## Scope

### In scope
- Passing api_surface to the planner
- Building class-to-claims index via word-boundary text matching
- Gating per_module expansion on minimum claim count per class
- Deriving slugs from class names (CamelCase → kebab-case)
- Adding target_class field to PlannedPage model
- Adding api_reference_index skeleton variant
- Class-aware claim assignment for per_module pages

### Out of scope
- Surfacing method/property details from code_analyzer into UnderstandingBundle (separate TC)
- Changes to generate worker prompts for reference_object_page (existing prompts adequate)
- Changes to evaluate checks (existing reference_completeness check adequate)
- Modifying ruleset.yaml tier_budget values (behavioral change only, not config)

## Inputs

- UnderstandingBundle (api_surface.public_classes, claims)
- ruleset.yaml (per_module policy with tier_budget)

## Outputs

- Modified planner that creates per_module pages only when viable
- PlannedPage objects with target_class set for reference_object_page pages
- api_reference page switches to index skeleton when sub-pages exist

## Allowed paths

- plans/taskcards/TC-3813_claim_gated_per_module.md
- src/launcher/workers/planner/plan.py
- src/launcher/workers/planner/worker.py
- src/launcher/models/plan.py
- src/launcher/shared/page_skeletons.py
- tests/test_planner_per_module.py

### Allowed paths rationale
- plan.py: Core planner logic (new helpers, gated expansion, class-aware assignment)
- worker.py: Pass api_surface from bundle to run_plan()
- models/plan.py: Add target_class field to PlannedPage
- page_skeletons.py: Add api_reference_index skeleton variant
- tests/: New unit tests for the feature

## Implementation steps

### Step 1: Add target_class field to PlannedPage

Add `target_class: str = ""` to PlannedPage in models/plan.py. Backward-compatible default.

### Step 2: Pass api_surface to planner

In worker.py, pass `bundle.api_surface` to `run_plan()`. In plan.py, add `api_surface` parameter to `run_plan()` and thread to `_apply_optional_expansion()`.

### Step 3: Add _class_name_to_slug() helper

CamelCase splitting with acronym handling: `WorksheetCollection → worksheet-collection`, `PDFDocument → pdf-document`. Validate with `validate_slug_safety()`.

### Step 4: Add _build_class_claim_index() helper

Map each public class to claim IDs by word-boundary matching claim text. Consider claims with kind in {"api", "feature", "example"}.

### Step 5: Implement claim-gated per_module expansion

In `_apply_optional_expansion()`, for `kind == "per_module"`: build class-claim index, filter to viable classes (>= 2 claims), cap budget at viable count, create pages with class-derived slugs and target_class set. Mark api-reference page with skeleton_variant="index" when sub-pages are created.

### Step 6: Add api_reference_index skeleton

Add new skeleton entry in page_skeletons.py with Overview, Public API (table), Common Patterns, See Also sections.

### Step 7: Class-aware claim assignment

In `_assign_claims()`, when page has target_class, prioritize claims mentioning that class.

### Step 8: Wire target_class into PlannedPage construction

In `_assign_claims()` PlannedPage construction loop, read target_class from page dict.

### Step 9: Write tests and run regression suite

## Failure modes

### Failure mode 1: CamelCase splitting produces invalid slugs

**Detection**: `validate_slug_safety()` returns issues for generated slug
**Resolution**: Fall back to lowercase class name with hyphens; if still invalid, use `{kind}-{family_kw}-{index}`
**Gate**: Slug safety gate (G6)

### Failure mode 2: Zero public_classes in api_surface

**Detection**: `api_surface is None` or `len(api_surface.public_classes) == 0`
**Resolution**: Skip per_module expansion entirely (same as budget=0). Existing unconditional path not reached.
**Gate**: N/A — graceful degradation

### Failure mode 3: Slug collision between class-derived slugs

**Detection**: `_disambiguate_slugs()` detects duplicate page_ids
**Resolution**: Existing disambiguation logic appends suffix. No new code needed.
**Gate**: Permalink uniqueness validation in `_validate_plan()`

### Failure mode 4: Word-boundary matching produces false positives

**Detection**: Short class names like "Pr" match unrelated words ("provides", "process")
**Resolution**: Require minimum class name length of 3 for matching, or exact case match for short names
**Gate**: Claim assignment sanity check in self_review

## Task-specific review checklist

1. [ ] _build_class_claim_index handles empty claims list
2. [ ] _build_class_claim_index handles empty public_classes list
3. [ ] _class_name_to_slug handles acronyms (PDF, HTML, XLSX)
4. [ ] _class_name_to_slug handles single-word names (Workbook, Cell)
5. [ ] per_module pages NOT created when 0 viable classes
6. [ ] api-reference page stays inline (default skeleton) when no sub-pages
7. [ ] api-reference page switches to index skeleton when sub-pages exist
8. [ ] target_class flows through to PlannedPage correctly
9. [ ] Backward-compatible: existing plans/bundles still deserialize

## Deliverables

1. Modified src/launcher/workers/planner/plan.py with gated expansion
2. Modified src/launcher/workers/planner/worker.py passing api_surface
3. Modified src/launcher/models/plan.py with target_class field
4. Modified src/launcher/shared/page_skeletons.py with index skeleton
5. New tests/test_planner_per_module.py

## Acceptance checks

1. [ ] Existing planner tests pass (PYTHONHASHSEED=0)
2. [ ] New per_module tests pass (0 claims, some claims, budget capping)
3. [ ] _class_name_to_slug produces correct output for 5+ test cases
4. [ ] No per_module-spreadsheets-* slugs generated when 0 API claims

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: slug safety PASS
- [ ] Evidence captured: tests/test_planner_per_module.py

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_planner_per_module.py tests/ -v -x
```

**Expected results**:
- All existing planner tests pass
- New per_module gating tests pass
- No per_module-spreadsheets fallback slugs in test output

## Integration boundary proven

**Upstream**: UnderstandingBundle provides api_surface.public_classes + claims
**Downstream**: Generate worker receives PlannedPage with target_class; prompts focus on that class
**Contract**: PlannedPage.target_class is optional str (empty = no class focus). api_reference skeleton variant "index" is selected when sub-pages exist.

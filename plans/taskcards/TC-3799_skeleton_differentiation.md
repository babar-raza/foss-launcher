---
id: TC-3799
title: "Claim-aware skeleton differentiation for planner"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [planner, skeleton, content-quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3799_skeleton_differentiation.md
  - src/launcher/models/plan.py
  - src/launcher/shared/page_skeletons.py
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/shared/test_skeleton_variants.py
  - tests/unit/workers/test_plan_skeleton_differentiation.py
evidence_required:
  - reports/TC-3799/evidence.md
---

# Taskcard TC-3799 — Claim-aware skeleton differentiation for planner

## Objective

Make pages with the same `page_role` but different topics produce structurally different section headings. Currently all pages of the same role get identical skeletons (e.g. every `workflow_page` gets Overview/Key Features/Prerequisites/Code Examples), making output homogeneous. This taskcard adds topic-aware skeleton variants driven by `topic_category` and slug semantics.

## Required spec references

- `specs/07_section_templates.md` (Section: canonical skeleton structure per page role)
- `specs/rulesets/ruleset.yaml` (Section: mandatory pages with topic_category field)

## Scope

### In scope
- `workflow_page`: 3 topic variants + default (install, data_operations, computation)
- `howto_article`: 5 topic variants + default (load_file, save_file, convert_formats, troubleshoot, optimize_performance)
- New `skeleton_variant` field on PlannedPage model
- Resolution logic: topic_category → slug pattern → "default"
- Generator consumption of variant-aware skeleton lookup
- Structure directives for new section headings
- Unit tests for variant registry and planner integration

### Out of scope
- Claim-kind-based differentiation (requires planner step reorder — follow-up)
- Variants for feature_showcase, comprehensive_guide, tutorial, api_reference (follow-up)
- Hugo template file creation for variants (templates already override skeletons)

## Inputs

- `specs/rulesets/ruleset.yaml` (page definitions with topic_category)
- `src/launcher/shared/page_skeletons.py` (existing PAGE_ROLE_SKELETONS registry)
- `src/launcher/models/plan.py` (PlannedPage model)

## Outputs

- Expanded skeleton registry with 8 topic variants
- PlannedPage objects carrying `skeleton_variant` field
- Generator using variant-aware skeleton lookup
- Structure directives for 12 new section headings
- Unit tests

## Allowed paths

- plans/taskcards/TC-3799_skeleton_differentiation.md
- src/launcher/models/plan.py
- src/launcher/shared/page_skeletons.py
- src/launcher/workers/planner/plan.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_prompt.py
- tests/unit/shared/test_skeleton_variants.py
- tests/unit/workers/test_plan_skeleton_differentiation.py

### Allowed paths rationale
- `plan.py` (model): Add skeleton_variant field
- `page_skeletons.py`: Variant registry + resolution functions
- `plan.py` (planner): Use variant-aware skeleton assignment + propagate field
- `worker.py` (generate): Consume variant when falling back from templates
- `section_prompt.py`: Structure directives for new headings
- Test files: Verify correctness

## Implementation steps

### Step 1: Add skeleton_variant to PlannedPage model

Edit `src/launcher/models/plan.py` to add `skeleton_variant: str = "default"` field. Backward-compatible default.

### Step 2: Add variant registry and resolution to page_skeletons.py

Add at module level:
- `TOPIC_CATEGORY_MAP` dict
- `SLUG_TOPIC_MAP` dict
- `SKELETON_VARIANTS` dict keyed by (page_role, topic_tag)
- `resolve_topic_tag()` function
- `resolve_skeleton()` function

Define 8 variant skeletons (3 workflow_page + 5 howto_article) with topic-appropriate headings, content_hints, and word counts.

### Step 3: Update planner _assign_skeletons

Replace flat `PAGE_ROLE_SKELETONS[role]` lookup with `resolve_topic_tag()` + `resolve_skeleton()`. Store `skeleton_variant` on page dict.

### Step 4: Propagate skeleton_variant through PlannedPage reconstructions

Update `_assign_claims()`, `_build_frontmatter()`, `_refine_page_slugs()` to pass `skeleton_variant` through all PlannedPage reconstructions.

### Step 5: Update generator fallback path

In `_generate_page()`, replace `PAGE_ROLE_SKELETONS.get(page_plan.page_role, [])` with `resolve_skeleton(page_plan.page_role, page_plan.skeleton_variant)`.

### Step 6: Add structure directives for new headings

Add entries in `_STRUCTURE_DIRECTIVES` for: working with data, loading the file, saving the file, conversion steps, symptoms, root cause, optimization steps, benchmarks, supported formats, output options, core concepts, implementation.

### Step 7: Write tests

Create `tests/unit/shared/test_skeleton_variants.py` and `tests/unit/workers/test_plan_skeleton_differentiation.py`.

### Step 8: Run full test suite

Verify all tests pass with `PYTHONHASHSEED=0`.

## Failure modes

### Failure mode 1: Unknown topic_tag breaks skeleton lookup

**Detection**: `resolve_skeleton()` returns empty list or raises KeyError
**Resolution**: `resolve_skeleton()` always falls back to `PAGE_ROLE_SKELETONS[page_role]`, then to a single "Content" section
**Gate**: Planner self-review checks page has non-empty skeleton

### Failure mode 2: New heading missing structure directive

**Detection**: Logger warning "No structure directive for heading 'X'" during generation
**Resolution**: Add missing entry to `_STRUCTURE_DIRECTIVES` in section_prompt.py
**Gate**: Gate template_label_headings checks heading alignment

### Failure mode 3: PlannedPage deserialization fails for existing plans

**Detection**: `model_validate()` raises ValidationError on old plan JSON without `skeleton_variant`
**Resolution**: Field has `= "default"` default, so missing field deserializes correctly. Verify with test.
**Gate**: Planner worker self-review

## Task-specific review checklist

1. [ ] `PAGE_ROLE_SKELETONS` dict unchanged (backward compat)
2. [ ] Every variant skeleton has unique headings vs its role's default
3. [ ] All new SkeletonSection entries have non-empty content_hint
4. [ ] `resolve_skeleton()` falls back to default for unknown tags
5. [ ] `skeleton_variant` propagated through all 4 PlannedPage construction sites
6. [ ] Generator uses `resolve_skeleton()` instead of raw dict lookup
7. [ ] All new headings have `_STRUCTURE_DIRECTIVES` entries
8. [ ] No import cycles introduced

## Deliverables

1. Modified source files (6 files)
2. New test files (2 files)
3. Evidence at reports/TC-3799/evidence.md

## Acceptance checks

1. [ ] All existing tests pass (9454+)
2. [ ] New variant tests pass
3. [ ] `resolve_topic_tag("workflow_page", slug="installation")` returns "install"
4. [ ] `resolve_skeleton("workflow_page", "install")` returns different headings than default
5. [ ] Two workflow_page PlannedPages with different slugs produce different skeleton lists

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3799/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

**Expected results**:
- All existing tests pass
- New tests in test_skeleton_variants.py and test_plan_skeleton_differentiation.py pass

## Integration boundary proven

**Upstream**: Planner receives claims, product evidence, and ruleset pages (with topic_category)
**Downstream**: Generator receives PlannedPage with skeleton_variant; looks up variant-aware SkeletonSection list
**Contract**: PlannedPage.skeleton_variant is a string; resolve_skeleton() always returns list[SkeletonSection] (never empty)

# PM-05: Scope skeleton_variant Preservation + Audit PlannedPage Reconstructions

## Status: Done

## Gap Linkage: PM-G6, PM-G7

## Role
Senior engineer. Drop-in, production-ready.

## Context
TC-3813 modified `_assign_skeletons()` to honour a pre-set `skeleton_variant`
value. However, the check is overly broad — it applies to ALL pages, not just
`api_reference` pages that were switched to "index" mode. Any page that
accidentally has `skeleton_variant` set before skeleton assignment would now
skip topic_tag resolution, potentially breaking variant selection for other
page roles.

Additionally, the self-review noted that `PlannedPage` is a frozen pydantic
model that gets reconstructed in multiple places. TC-3813 patched
`_build_frontmatter` and `_refine_page_slugs` to include `target_class`, but
there may be other reconstruction sites that were missed.

## Scope

### Fix
1. In `_assign_skeletons()`, narrow the skeleton_variant preservation check to
   only apply when the pre-set variant is a known per_module variant (i.e.,
   `"index"`), not for any arbitrary non-default value. Alternatively, check
   that the pre-set variant is a registered key in `SKELETON_VARIANTS` for
   this role before using it.
2. Audit ALL locations in `plan.py` where `PlannedPage(...)` is constructed.
   Verify each includes `target_class=`. If any are missing, fix them.
3. Add a grep-based or AST-based test that asserts every `PlannedPage(`
   construction in `plan.py` includes `target_class=`.

### Allowed paths
- `src/launcher/workers/planner/plan.py`
- `tests/test_planner_per_module.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- New test: `test_skeleton_variant_not_overridden_for_non_api_reference` —
  verify that a non-api_reference page with topic_category set still gets
  correct topic_tag resolution even if skeleton_variant was somehow set
- New test: `test_all_planned_page_constructions_include_target_class` —
  grep plan.py source for `PlannedPage(` and assert each includes `target_class`
- Existing tests pass

### Config respected end-to-end
- N/A

### No mock data in production paths
- N/A

## Deliverables
- Modified `src/launcher/workers/planner/plan.py`: narrowed skeleton_variant check
- Modified `tests/test_planner_per_module.py`: 2 new tests
- Any missing `target_class=` in PlannedPage constructions fixed

## Hard rules
- Keep public signatures unchanged
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Robustness | skeleton_variant preservation cannot break non-api_reference pages |
| Correctness | Every PlannedPage construction includes target_class |
| Testability | Structural test prevents future regressions |
| Thoroughness | Full audit of all construction sites, not just known ones |

## Now (runbook)

```bash
# 1. Grep for all PlannedPage( constructions in plan.py
grep -n "PlannedPage(" src/launcher/workers/planner/plan.py

# 2. Verify each includes target_class=. Fix any that don't.

# 3. In _assign_skeletons(), change the preset_variant check to:
#    if preset_variant and preset_variant != "default":
#        from launcher.shared.page_skeletons import SKELETON_VARIANTS
#        if (role, preset_variant) in SKELETON_VARIANTS:
#            topic_tag = preset_variant

# 4. Add tests

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

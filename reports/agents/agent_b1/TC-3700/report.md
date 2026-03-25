# TC-3700: Single Source of Truth for Page Structure in W4/W5

**Date:** 2026-03-04
**Agent:** agent_b1
**Status:** Complete

## Summary

TC-3700 eliminates structural divergence between W4's internal heading maps and W5's page skeleton registry. W4 now derives `section_types` from `page_skeletons.py` — the single source of truth — and emits `section_types: Dict[str, str]` in every page plan entry.

## Tests: 15 passed

```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\.claude\worktrees\agent-ae10d612
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.7.3, asyncio-0.26.0, cov-5.0.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 15 items

tests\unit\workers\w4_ia_planner\test_tc3700_skeleton_single_source.py ...............

======================== 15 passed, 1 warning in 1.07s ========================
```

## Full suite (no regressions)

Pre-existing failures (13, all in worktree fixture/taskcard path issues unrelated to TC-3700):
- tests/unit/io/test_atomic_taskcard.py (2 failures — missing TC-100 taskcard in worktree)
- tests/unit/orchestrator/test_run_loop_taskcard.py (1 failure — taskcard event test)
- tests/unit/test_validation_engine_golden.py (1 failure — missing fixture files in worktree)
- tests/unit/util/test_taskcard_loader.py (5 failures — missing taskcards in worktree)
- tests/unit/workers/w9/test_gate_fixtures.py (4 failures — missing fixtures in worktree)

Result: **13 failed, 8611 passed, 13 skipped, 3 xfailed** (same pre-existing failures as before TC-3700)

## Files Changed

### Modified: `src/launch/workers/w5_section_writer/page_skeletons.py`
- Added `VALID_SECTION_TYPES` frozenset (7 allowed values: intro, workflow_code, links, next_steps, reference_table, faq_pair, callout)
- Added `section_type: str = "intro"` field to `SkeletonSection` NamedTuple
- Added `_validate_skeleton_section()` validation function (raises ValueError for invalid section_types)
- Added module-load validation loop over all PAGE_ROLE_SKELETONS entries
- Added `get_section_types(page_role)` helper returning `{heading: section_type}` dict
- Assigned `section_type` to all 17 page roles × all sections (approx. 85 SkeletonSection instances)

### Modified: `src/launch/workers/w4_ia_planner/worker.py`
- Added import: `from ..w5_section_writer.page_skeletons import get_section_types as _get_section_types`
- Added TC-3700 enrichment loop in main worker function (after `_sanitize_page_spec_fields`, before `_refine_slugs`): adds `section_types` dict to every page plan entry that has a `page_role`

### Created: `tests/unit/workers/w4_ia_planner/__init__.py`
- Empty init file for test package

### Created: `tests/unit/workers/w4_ia_planner/test_tc3700_skeleton_single_source.py`
- 15 test functions across 8 test classes
- Test 1: `test_all_skeletons_have_section_type` — all SkeletonSection entries have non-empty section_type
- Test 2: `test_section_type_valid_values` — all section_type values in VALID_SECTION_TYPES
- Test 3: `test_w4_page_plan_emits_section_types` (+ 2 variants) — page entries gain section_types key
- Test 4: `test_w4_derives_headings_from_skeleton` + `test_skeleton_source_matches_w4_import` — import alias verified
- Test 5: `test_sections_deterministic_order` + `test_section_types_order_matches_skeleton_order` — deterministic
- Test 6: `test_unknown_section_type_raises` + `test_valid_section_types_do_not_raise` — validation enforcement
- Test 7: `test_all_page_roles_have_skeletons` + `test_w4_unknown_roles_return_empty_dict` — coverage
- Test 8: `test_skeleton_sections_nonempty` + `test_most_skeletons_have_three_or_more_sections` — size check

## Commands Run

```bash
# Verify page_skeletons changes
PYTHONPATH=src .venv/Scripts/python.exe -c "from launch.workers.w5_section_writer.page_skeletons import get_section_types; print(get_section_types('landing'))"

# Run TC-3700 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w4_ia_planner/test_tc3700_skeleton_single_source.py -v --tb=short
# Result: 15 passed

# Run full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
# Result: 13 failed (pre-existing), 8611 passed, 13 skipped, 3 xfailed
```

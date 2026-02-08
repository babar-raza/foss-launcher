# TC-984 Evidence Report: W4 Evidence-Driven Page Scaling Implementation

**Task**: TC-984 - W4 IAPlanner: Evidence-Driven Page Scaling + Configurable Page Requirements
**Agent**: Agent-B (Implementation)
**Date**: 2026-02-05
**Status**: Complete

## Files Changed

- `src/launch/workers/w4_ia_planner/worker.py` (modified)

## Summary of Changes

### Step 1: Softened CI-absent tier reduction in determine_launch_tier() (~line 413)
- **Before**: CI absent alone dropped standard -> minimal
- **After**: Only reduces when BOTH CI and tests are absent. If CI absent but tests present, logs adjustment with signal `ci_absent_tests_present` but keeps tier unchanged.
- **Spec ref**: specs/06_page_planning.md "CI-absent tier reduction softening (TC-983, binding)"

### Step 2: Added load_ruleset() function (~line 296)
- New helper to load the full ruleset dict (needed by load_and_merge_page_requirements)
- Reuses same path logic as load_ruleset_quotas()

### Step 3: Added load_and_merge_page_requirements() function (~line 524)
- Reads mandatory_pages + optional_page_policies from ruleset sections
- Reads family_overrides for product_slug (if exists)
- Merges: global mandatory_pages UNION family mandatory_pages (deduplicate by slug)
- Returns dict: {section_name: {"mandatory_pages": [...], "optional_page_policies": [...]}}
- **Spec ref**: specs/06_page_planning.md "Configurable Page Requirements (TC-983)"

### Step 4: Added compute_evidence_volume() function (~line 603)
- Computes: total_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)
- Returns dict with total_score, claim_count, snippet_count, api_symbol_count, workflow_count, key_feature_count
- claim_groups accessed as TOP-LEVEL dict (not per-claim field)
- **Spec ref**: specs/06_page_planning.md "Step 0: Compute evidence volume"

### Step 5: Added compute_effective_quotas() function (~line 650)
- Tier coefficients: {"minimal": 0.3, "standard": 0.7, "rich": 1.0}
- Evidence-based section targets per spec formulas
- effective_max = clamp(evidence_target, min_pages, tier_adjusted_max)
- **Spec ref**: specs/06_page_planning.md "Step 1.5: Compute effective quotas"

### Step 6: Added generate_optional_pages() function (~line 710)
- Supports all 5 policy sources: per_feature, per_workflow, per_key_feature, per_api_symbol, per_deep_dive
- Scores candidates: quality_score = (claim_count * 2) + (snippet_count * 3)
- Sorts by (priority asc, quality_score desc, slug asc) -- DETERMINISTIC
- Selects top N = effective_max - mandatory_page_count
- Builds full page spec structures using existing helpers
- **Spec ref**: specs/06_page_planning.md "Optional Page Selection Algorithm"

### Step 7: Added _default_headings_for_role() helper (~line 870)
- Returns standard heading structures for each page_role
- Used by generate_optional_pages() for required_headings

### Step 8: Refactored execute_ia_planner() (~line 2448+)
- Loads full ruleset via load_ruleset()
- Calls load_and_merge_page_requirements(ruleset, product_slug)
- Calls compute_evidence_volume(product_facts, snippet_catalog)
- Calls compute_effective_quotas(evidence_volume, launch_tier, section_quotas, merged_requirements)
- Replaced static quota with effective_quotas in template pathway
- Added evidence-driven optional page injection loop after main template loop
- Deduplicates optional pages by slug against existing pages

### Step 9: Added output fields to page_plan dict (~line 2629)
- evidence_volume dict added to page_plan output
- effective_quotas dict (section -> {max_pages}) added to page_plan output
- Both validated against page_plan.schema.json (additionalProperties: true)

## Commands Run

```
# Syntax check
python -c "import ast; ast.parse(open('src/launch/workers/w4_ia_planner/worker.py').read()); print('OK')"
# Output: Syntax OK

# W4 unit tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/ -k "test_w4" -v --tb=short
# Output: 108 passed, 1 failed (pre-existing: test_docs_templates_allow_locale_folder)

# Content distribution + quota tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_content_distribution.py tests/unit/workers/test_w4_quota_enforcement.py -v
# Output: 45 passed

# Full unit suite
.venv/Scripts/python.exe -m pytest tests/unit/ -v --tb=short -q
# Output: 1785 passed, 23 failed (all pre-existing), 3 skipped

# Smoke tests for all new functions
python -c "<import and test all 5 new functions>"
# Output: ALL SMOKE TESTS PASSED

# Tier softening verification
python -c "<test CI-absent with tests present, CI+tests absent, CI+tests present>"
# Output: ALL TIER SOFTENING TESTS PASSED

# generate_optional_pages verification
python -c "<test per_feature + per_workflow policies, N=0 edge case>"
# Output: ALL GENERATE_OPTIONAL_PAGES TESTS PASSED
```

## Pre-existing Test Failures (NOT caused by TC-984)

Verified by git stash + re-run:
- `test_plan_pages_minimal_tier` - asserts len(pages) <= 2 but plan_pages_for_section always creates 3 docs pages (pre-existing)
- `test_check_url_collisions_none` / `test_check_url_collisions_detected` - missing "section" key in test data (TC-969 pre-existing)
- `test_docs_templates_allow_locale_folder` - template enumeration filtering (pre-existing)
- 19 other failures in tc_902, tc_480, tc_440, etc. (all pre-existing, confirmed via git stash)

## Determinism Verification

1. All new functions use sorted() for list outputs
2. generate_optional_pages() sorts by (priority, -quality_score, slug) for deterministic tie-breaking
3. effective_quotas dict in page_plan is built from sorted(effective_quotas.items())
4. No randomness, no hash-dependent ordering, no timestamps
5. PYTHONHASHSEED=0 is set in pytest config

## Acceptance Checks

- [x] All 5 new functions exist and are callable (load_and_merge_page_requirements, compute_evidence_volume, compute_effective_quotas, generate_optional_pages, _default_headings_for_role)
- [x] load_ruleset() helper added for full ruleset loading
- [x] execute_ia_planner() uses config-driven mandatory pages via merged_requirements
- [x] evidence_volume and effective_quotas present in page_plan output
- [x] Tier reduction softened (CI-absent alone doesn't force minimal)
- [x] No regressions in existing test suite (all failures are pre-existing)
- [x] All new functions are deterministic (sorted inputs, no randomness)
- [x] Proper docstrings citing spec references on all new functions

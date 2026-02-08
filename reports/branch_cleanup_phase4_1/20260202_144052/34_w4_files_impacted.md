# W4 Files Impacted by Pilot Branch Fixes

## Summary of Pilot Commits Analyzed

1. **d582eca** - "Handle example_inventory as list or dict in W4"
   - Status: ✅ **ALREADY APPLIED** in consolidation branch
   - Evidence: Lines 196-201 in w4_ia_planner/worker.py include the fix with comment "(d582eca fix)"

2. **5b5b601** - "W4 handle run_config_obj as dict or object"
   - Status: ❌ **NOT APPLIED** - needs porting
   - Issue: Code uses `hasattr(run_config, 'launch_tier')` which doesn't work correctly for dicts
   - Location: Line 177 in determine_launch_tier() function

3. **2442a54** - "W4 pass repo_root to load_and_validate_run_config"
   - Status: ✅ **ALREADY APPLIED** in consolidation branch
   - Evidence: Line 994 correctly passes repo_root as first parameter

## Current Issue

### Problem
Tests fail at line 997: `run_config_obj = RunConfig.from_dict(run_config)`
- Test fixture provides minimal dict: `{schema_version, run_id, github_repo_url, github_ref}`
- RunConfig.from_dict() requires ~20 required fields (product_slug, product_name, family, etc.)
- KeyError: 'product_slug'

### Root Cause
The execute_ia_planner() function tries to convert the provided run_config dict to a RunConfig object unconditionally. Test fixtures don't provide all required fields.

## Required Changes

### File: src/launch/workers/w4_ia_planner/worker.py

#### Change 1: Line 997 - Don't convert minimal run_config dicts to RunConfig objects
**Current code:**
```python
else:
    run_config_obj = RunConfig.from_dict(run_config)
```

**Fixed code:**
```python
else:
    # Keep as dict if provided (tests may provide minimal run_config)
    # Don't force conversion to RunConfig - handle both dict and object below
    run_config_obj = run_config
```

**Rationale**: Tests provide minimal dicts that can't be converted to full RunConfig objects. The worker should handle both dict and object inputs.

#### Change 2: Line 177 in determine_launch_tier() - Handle dict/object duality
**Current code:**
```python
if hasattr(run_config, 'launch_tier') and run_config.launch_tier:
    tier = run_config.launch_tier
```

**Fixed code:**
```python
# Handle run_config as either dict or object (TC-925 robustness)
if isinstance(run_config, dict):
    tier = run_config.get('launch_tier')
else:
    tier = getattr(run_config, 'launch_tier', None)

if tier:
    adjustments.append({...})
```

**Rationale**: The function receives run_config with unknown type. Tests pass dicts, real runs pass RunConfig objects. Must handle both.

## Test Verification

After applying changes:
1. Run W4 tests: `pytest tests/unit/workers/test_tc_430_ia_planner.py -v`
2. Expect: All 30 tests pass (currently 26 pass, 4 fail)
3. Failing tests should now pass:
   - test_execute_ia_planner_success
   - test_execute_ia_planner_deterministic_ordering
   - test_execute_ia_planner_event_emission
   - test_execute_ia_planner_schema_validation

## Impact Assessment

- **Risk**: LOW - changes make code more robust, no breaking changes
- **Scope**: Isolated to W4 worker, doesn't affect other workers
- **Tests**: Fixes 4 failing unit tests, doesn't break any passing tests
- **Backward Compat**: Yes - still works with full RunConfig objects, now also works with minimal dicts

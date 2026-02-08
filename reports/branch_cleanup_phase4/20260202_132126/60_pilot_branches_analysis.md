# Pilot Branches Analysis

## Unique Commits Found

### feat/golden-2pilots-20260130 (12 unique commits not in current)

Most critical commits:
- **d582eca**: "Handle example_inventory as list or dict in W4" - CRITICAL W4 fix
- c118b0b: "Wrap determine_launch_tier call" - Debug improvement
- dafc20c: "Add logging to find list.get() error in W4" - Debug improvement
- 5b5b601: "W4 handle run_config_obj as dict or object" - Type flexibility fix
- 2442a54: "W4 pass repo_root to load_and_validate_run_config" - Parameter fix
- a0e605d: "formalize TC-700-703 taskcards" - Documentation
- fc60462-581682a: Clone/ref placeholder fixes

### feat/pilot1-hardening-vfv-20260130 (1 unique commit)

- **4bed867**: "Fix W4 path construction (family + subdomain)" - Path fix

### feat/pilot-e2e-golden-3d-20260129 (2 unique commits)

- **c666914**: "Phase N0 taskcard hygiene + golden capture prep (TC-633)"
- **795ef77**: "implement TC-631 offline-safe PR manager for pilot E2E"

## Integration Attempts

### Cherry-pick d582eca (W4 example_inventory fix)

**Status**: FAILED with merge conflict in src/launch/workers/w4_ia_planner/worker.py

The W4 code has diverged significantly between branches. Manual merge resolution required.

## Impact Assessment

The W4 fixes in feat/golden-2pilots-20260130 may be related to the test failures in test_tc_430_ia_planner.py. However, cherry-picking conflicts indicate significant code divergence.

## Recommendation

These pilot branch commits need careful manual integration:
1. Review W4 changes in both branches
2. Reconcile the example_inventory handling approaches
3. Update test fixtures to match final implementation
4. Re-run full test suite


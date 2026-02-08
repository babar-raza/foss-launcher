---
id: TC-925
title: "Fix W4 IAPlanner load_and_validate_run_config signature mismatch"
status: In-Progress
priority: Critical
owner: "SUPERVISOR"
updated: "2026-02-02"
tags: ["w4", "ia-planner", "signature", "blocker"]
depends_on: ["TC-902"]
allowed_paths:
  - plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - tests/unit/workers/w4/test_tc_925_config_loading.py
  - reports/agents/**/TC-925/**
evidence_required:
  - reports/agents/SUPERVISOR/TC-925/w4_fix.diff
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-925 — Fix W4 IAPlanner load_and_validate_run_config signature mismatch

## Objective
Fix W4 IAPlanner function signature mismatch that causes pilot VFV runs to fail at W4 entry with error: `load_and_validate_run_config() missing 1 required positional argument: 'config_path'`

## Problem Statement
src/launch/workers/w4_ia_planner/worker.py:988 calls:
```python
run_config_obj = load_and_validate_run_config(config_path)
```

But the function signature (src/launch/io/run_config.py:15) requires:
```python
def load_and_validate_run_config(repo_root: Path, config_path: Path) -> Dict[str, Any]:
```

This causes both pilots to fail at W4 entry with exit_code=2.

## Root Cause
W4's `execute_ia_planner()` function always attempts to reload config from file (lines 986-997), even though `run_config` is already passed as a parameter. This differs from W2/W3 pattern which only reload if `run_config` is None.

## Required spec references
- specs/06_page_planning.md (W4 IAPlanner contract)
- specs/21_worker_contracts.md (Worker coordination patterns)
- specs/10_determinism_and_caching.md (Config loading consistency)

## Scope

### In scope
- Fix W4 config loading logic to follow W2 pattern (only reload if None)
- Use passed-in `run_config` parameter instead of reloading from file
- Add unit test verifying W4 no longer throws signature error

### Out of scope
- Changing load_and_validate_run_config() signature (all other workers use it correctly)
- Modifying W4's page planning logic beyond config loading

## Allowed paths
- plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- tests/unit/workers/w4/test_tc_925_config_loading.py
- reports/agents/**/TC-925/**

## Implementation

### Current Code (lines 985-997 of w4_ia_planner/worker.py):
```python
# Load run config as model if it exists
config_path = run_dir / "run_config.yaml"
if config_path.exists():
    run_config_obj = load_and_validate_run_config(config_path)  # BUG: missing repo_root
else:
    # Use a simple object with just the fields we need
    class MinimalRunConfig:
        def __init__(self, launch_tier=None):
            self.launch_tier = launch_tier

    run_config_obj = MinimalRunConfig(
        launch_tier=run_config.get("launch_tier")
    )
```

### Fixed Code (following W2 pattern):
```python
# Load run_config if not provided (follow W2 pattern)
if run_config is None:
    repo_root = Path(__file__).parent.parent.parent.parent
    run_config_path = run_dir / "run_config.yaml"
    config_data = load_and_validate_run_config(repo_root, run_config_path)
    run_config_obj = RunConfig.from_dict(config_data)
else:
    run_config_obj = RunConfig.from_dict(run_config)
```

Note: May need to import RunConfig model or use dict directly depending on W4 usage.

## Success Criteria
1. W4 no longer throws `missing 1 required positional argument: 'config_path'`
2. Pilot-1 VFV run produces `artifacts/page_plan.json` and `artifacts/validation_report.json`
3. Unit test `test_tc_925_config_loading.py` passes
4. validate_swarm_ready 21/21 PASS
5. pytest passes for W4 tests

## Testing
Unit test should:
- Mock `execute_ia_planner()` call with `run_config` dict parameter
- Assert no TypeError raised
- Verify W4 uses passed-in config rather than reloading

## Inputs
- src/launch/workers/w4_ia_planner/worker.py (buggy config loading)
- VFV error report showing signature mismatch
- W2 worker.py (correct pattern reference)

## Outputs
- Fixed W4 worker.py following W2 pattern
- Unit test: tests/unit/workers/w4/test_tc_925_config_loading.py
- VFV reports showing W4 produces page_plan.json

## Implementation steps
1. Analyze W4 execute_ia_planner config loading logic (lines 985-997)
2. Compare with W2 execute_facts_builder correct pattern (lines 417-423)
3. Replace W4 config loading with W2 pattern (check if run_config is None before reloading)
4. Create unit test verifying fix (mock execute_ia_planner with run_config provided)
5. Run unit test: pytest tests/unit/workers/w4/test_tc_925_config_loading.py
6. Verify gates: validate_swarm_ready

## Deliverables
- src/launch/workers/w4_ia_planner/worker.py (lines 772-779 fixed)
- tests/unit/workers/w4/test_tc_925_config_loading.py (2 tests passing)
- Pilot VFV reports showing W4 success

## Acceptance checks
1. Unit test passes: test_tc_925_config_loading.py (2/2 tests)
2. W4 no longer throws TypeError about missing config_path
3. Pilot-1 VFV produces artifacts/page_plan.json
4. validate_swarm_ready 21/21 PASS

## E2E verification
Run full pilot VFV with both runs:
```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output report.json --goldenize
```

Expected artifacts:
- **artifacts/page_plan.json** in both run1 and run2 directories
- **artifacts/validation_report.json** in both run1 and run2 directories
- W4 log entries showing "Starting page planning for run <run_id>"
- W4 log entries showing "Page plan written successfully"
- No TypeError about missing config_path parameter

## Integration boundary proven
**Upstream integration:** W4 receives `run_config` dict from orchestrator graph via execute_ia_planner() parameter. Orchestrator loads config using load_and_validate_run_config(repo_root, config_path) and passes as dict.

**Downstream integration:** W4 uses RunConfig.from_dict(run_config) to convert to model object, then passes to determine_launch_tier() and plan_pages_for_section(). These functions consume launch_tier, product_facts, and platform fields.

**Contract:** W4 must NOT reload config from file when run_config parameter is provided (follows W2 pattern). Only reload if run_config is None.

## Task-specific review checklist
1. [ ] W4 execute_ia_planner() checks if run_config parameter is None before reloading
2. [ ] When run_config is provided, W4 uses it directly without file I/O
3. [ ] When run_config is None, W4 calls load_and_validate_run_config(repo_root, config_path) with both required arguments
4. [ ] repo_root is correctly computed (Path(__file__).parent.parent.parent.parent or from context)
5. [ ] Config loading logic matches W2 pattern (lines 417-423 of w2_facts_builder/worker.py)
6. [ ] Unit test test_w4_config_loading_with_provided_config() verifies no file reload when config passed
7. [ ] Unit test test_w4_config_loading_without_config() verifies file reload when config is None
8. [ ] No TypeError raised during pilot VFV runs at W4 entry
9. [ ] W4 produces artifacts/page_plan.json in both run1 and run2 directories
10. [ ] validate_swarm_ready shows 21/21 gates PASS after fix

## Failure modes

### Failure mode 1: TypeError persists with "missing 1 required positional argument"
**Detection:** Pilot VFV fails at W4 entry with same error: `load_and_validate_run_config() missing 1 required positional argument: 'config_path'`
**Resolution:** Verify fix was applied to correct function in w4_ia_planner/worker.py (lines 985-997); ensure both repo_root and config_path arguments are passed to load_and_validate_run_config(); check that repo_root is a valid Path object
**Spec/Gate:** specs/06_page_planning.md (W4 IAPlanner contract)

### Failure mode 2: W4 reloads config from file even when provided as parameter
**Detection:** Logs show "Loading config from file" message when run_config was passed; unit test for provided config fails
**Resolution:** Add conditional check: `if run_config is None:` before calling load_and_validate_run_config(); ensure provided run_config is used directly via RunConfig.from_dict(run_config) or similar conversion
**Spec/Gate:** specs/21_worker_contracts.md (Worker coordination patterns)

### Failure mode 3: W4 fails to produce page_plan.json after config fix
**Detection:** No TypeError but artifacts/page_plan.json missing from run directories; W4 logs show "Page planning failed" or no W4 execution logs
**Resolution:** Check that run_config contains all required fields (launch_tier, product_facts, platform); verify W4's determine_launch_tier() and plan_pages_for_section() can consume the config format; ensure config conversion to model object succeeded
**Spec/Gate:** specs/06_page_planning.md (Page planning requirements), Gate H (IA planning gate)

## Self-review
- [x] Function signature matches definition (repo_root + config_path)
- [x] Follows W2 pattern (only reload if run_config is None)
- [x] Unit test covers both paths (with and without run_config)
- [x] No breaking changes to W4 page planning logic
- [x] TC-925 allowed paths enforced (only W4 worker.py and test file modified)

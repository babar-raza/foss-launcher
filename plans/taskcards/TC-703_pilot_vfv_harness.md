---
id: TC-703
title: "Pilot VFV Harness + Autonomous Golden Capture"
status: Done
owner: "PILOT_OPS_AGENT"
updated: "2026-01-30"
depends_on:
  - TC-520
  - TC-522
  - TC-702
allowed_paths:
  - scripts/run_pilot_vfv.py
  - scripts/run_multi_pilot_vfv.py
  - tests/e2e/test_tc_703_pilot_vfv.py
  - reports/agents/**/TC-703/**
evidence_required:
  - reports/agents/<agent>/TC-703/report.md
  - reports/agents/<agent>/TC-703/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-703 — Pilot VFV Harness + Autonomous Golden Capture

## Objective
Create VFV (Verify-Fix-Verify) automation harness for running pilots and capturing golden artifacts. Enable two-run determinism verification with automatic golden artifact capture when determinism passes.

## Required spec references
- specs/13_pilots.md
- specs/10_determinism_and_caching.md
- specs/09_validation_gates.md
- specs/schemas/page_plan.schema.json
- specs/schemas/validation_report.schema.json

## Scope
### In scope
- Single-pilot VFV script (run_pilot_vfv.py)
- Multi-pilot batch VFV script (run_multi_pilot_vfv.py)
- Two-run pilot execution with artifact verification
- Canonical JSON hash computation (SHA256)
- Determinism comparison and reporting
- Auto-capture of golden artifacts (--goldenize flag)
- E2E tests for VFV scripts

### Out of scope
- Pilot run_config changes (work with existing configs)
- Worker implementation changes (only automation scripts)
- Golden artifact validation logic (only capture)

## Inputs
- specs/pilots/<pilot_id>/run_config.pinned.yaml
- Pilot execution artifacts (page_plan.json, validation_report.json)

## Outputs
- VFV determinism report (PASS/FAIL)
- Golden artifacts (if --goldenize flag set):
  - specs/pilots/<pilot_id>/expected_page_plan.json
  - specs/pilots/<pilot_id>/expected_validation_report.json
  - Updated specs/pilots/<pilot_id>/notes.md with hashes

## Allowed paths
- scripts/run_pilot_vfv.py
- scripts/run_multi_pilot_vfv.py
- tests/e2e/test_tc_703_pilot_vfv.py
- reports/agents/**/TC-703/**

## Implementation steps
1) **Create run_pilot_vfv.py script**:
   - Accept --pilot <pilot_id> argument
   - Accept --goldenize flag (optional)
   - Accept --verbose flag (optional)
   - Run pilot E2E twice (run1, run2)
   - Verify both artifacts exist (page_plan.json, validation_report.json)
   - Compute canonical JSON hashes (SHA256)
   - Compare hash1 vs hash2
   - Report determinism PASS/FAIL
   - If --goldenize and PASS: copy artifacts to expected_*.json

2) **Create run_multi_pilot_vfv.py script**:
   - Accept --pilots <comma_separated_list> argument
   - Accept --goldenize flag (optional)
   - Run each pilot VFV sequentially
   - Aggregate results
   - Support batch golden capture

3) **Implement canonical hash computation**:
   - Use json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
   - Compute SHA256 of canonical JSON bytes
   - Return hex digest for comparison

4) **Implement golden capture logic**:
   - Copy page_plan.json → expected_page_plan.json
   - Copy validation_report.json → expected_validation_report.json
   - Update notes.md with timestamp, hashes, determinism status

5) **Create E2E tests**:
   - Skip by default (require RUN_PILOT_E2E=1)
   - Test script existence
   - Test help command functionality
   - Test error handling for missing arguments

## Failure modes

### Failure mode 1: VFV script cannot find pilot config
**Detection:** FileNotFoundError when reading specs/pilots/<pilot_id>/run_config.pinned.yaml; VFV exits with error before running pilot
**Resolution:** Check pilot_id argument is valid before execution; verify specs/pilots/<pilot_id>/ directory exists; list available pilots in error message; provide clear usage example with valid pilot names
**Spec/Gate:** specs/13_pilots.md (pilot directory structure and naming)

### Failure mode 2: Artifacts missing after pilot execution completes
**Detection:** FileNotFoundError when reading page_plan.json or validation_report.json after E2E run; pilot appears to complete but required artifacts not found
**Resolution:** Check artifact existence with specific paths; report which exact artifacts are missing (page_plan, validation_report, both); verify RUN_DIR structure; check for worker failures in logs; exit with code 1 and actionable error message
**Spec/Gate:** specs/21_worker_contracts.md (W4 page_plan.json output, W7 validation_report.json output)

### Failure mode 3: Canonical hashes differ across two runs (determinism failure)
**Detection:** hash1 != hash2 for same artifact type; SHA256 comparison fails despite supposedly identical inputs
**Resolution:** Do NOT auto-goldenize when hashes differ; report which specific artifacts differ (page_plan vs validation_report); display both hashes for comparison; exit with code 1; require manual investigation of non-determinism root cause; save both artifacts for diff analysis
**Spec/Gate:** specs/10_determinism_and_caching.md (reproducibility requirement - bit-for-bit identical outputs)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] Single-pilot VFV script exists and is executable
- [ ] Multi-pilot batch VFV script exists and is executable
- [ ] Both scripts respond to --help flag
- [ ] Scripts use correct exit codes (0=PASS, 1=FAIL, 2=ERROR)
- [ ] Canonical hash computation uses sort_keys=True
- [ ] Golden capture only occurs when determinism passes
- [ ] notes.md updated with timestamp and hashes when goldenizing
- [ ] E2E tests skip by default (require RUN_PILOT_E2E=1)
- [ ] All scripts within allowed_paths only

## E2E verification
**Concrete command(s) to run:**
```bash
# Test single-pilot VFV
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --verbose

# Test multi-pilot VFV
python scripts/run_multi_pilot_vfv.py --pilots pilot-aspose-3d-foss-python,pilot-aspose-note-foss-python

# Test golden capture
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --goldenize

# Execute TC-703 test suite
RUN_PILOT_E2E=1 python -m pytest tests/e2e/test_tc_703_pilot_vfv.py -v
```

**Expected artifacts:**
- scripts/run_pilot_vfv.py
- scripts/run_multi_pilot_vfv.py
- tests/e2e/test_tc_703_pilot_vfv.py
- Golden artifacts (if --goldenize used):
  - specs/pilots/<pilot_id>/expected_page_plan.json
  - specs/pilots/<pilot_id>/expected_validation_report.json
  - Updated specs/pilots/<pilot_id>/notes.md

**Success criteria:**
- [ ] VFV scripts execute successfully
- [ ] Determinism check reports PASS or FAIL correctly
- [ ] Golden capture only occurs on PASS
- [ ] All E2E tests pass (when RUN_PILOT_E2E=1)

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-520/TC-522 (pilot execution) → TC-703 (VFV automation)
- Upstream: TC-702 (deterministic validation reports) → TC-703 (hash comparison)
- Contracts: Canonical hash format, golden artifact locations

## Deliverables
- Code:
  - scripts/run_pilot_vfv.py (243 lines)
  - scripts/run_multi_pilot_vfv.py (69 lines)
  - tests/e2e/test_tc_703_pilot_vfv.py (127 lines)
- Reports:
  - reports/agents/<agent>/TC-703/report.md
  - reports/agents/<agent>/TC-703/self_review.md

## Acceptance checks
- [ ] run_pilot_vfv.py script exists and is executable
- [ ] run_multi_pilot_vfv.py script exists and is executable
- [ ] Both scripts respond to --help
- [ ] Scripts use correct exit codes
- [ ] Canonical hash computation implemented
- [ ] Golden capture logic implemented
- [ ] notes.md update logic implemented
- [ ] E2E tests created (6 tests, skip-by-default)
- [ ] All tests pass when RUN_PILOT_E2E=1
- [ ] Scripts within allowed_paths only

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

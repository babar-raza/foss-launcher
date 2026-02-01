---
taskcard_id: TC-903
title: "VFV Harness: Strict 2-run determinism with goldenization"
status: In-Progress
owner: VFV_OPERATOR
depends_on:
  - TC-520
  - TC-522
  - TC-560
spec_ref: c78c3ffbb53ece25d97372756b65a212d8d112a6
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - scripts/run_pilot_vfv.py
  - scripts/run_multi_pilot_vfv.py
  - tests/e2e/test_tc_903_vfv.py
  - reports/agents/**/TC-903/**
evidence_required:
  - reports/agents/<agent>/TC-903/report.md
  - reports/agents/<agent>/TC-903/self_review.md
  - runs/tc903_vfv_operator_20260201_HHMMSS/tc903_evidence.zip
  - Test output: pytest tests/e2e/test_tc_903_vfv.py -v
updated: "2026-02-01"
---

# TC-903: VFV Harness - Strict 2-run determinism with goldenization

## Objective

Create a VFV (Verify-First-Validate) harness script that executes pilots twice, verifies BOTH critical artifacts (page_plan.json and validation_report.json) exist in each run, computes canonical JSON hashes for determinism verification, and goldenizes artifacts only on PASS.

This taskcard delivers a production-ready VFV operator that ensures artifact determinism before goldenization, preventing non-deterministic artifacts from polluting the regression baseline.

## Required spec references

- `specs/30_determinism_harness.md` - Determinism verification requirements
- `specs/31_pilots_and_regression.md` - Pilot execution and golden artifact management
- `specs/schemas/page_plan.schema.json` - Page plan artifact schema
- `specs/schemas/validation_report.schema.json` - Validation report artifact schema
- `specs/34_strict_compliance_guarantees.md` - Guarantee K (version locking)

## Scope

### In scope

1. **Preflight checks**:
   - Reject placeholder all-zero SHAs (e.g., "0000000000000000000000000000000000000000") unless --allow_placeholders flag is set
   - Print repo URLs and pinned SHAs being used for transparency
   - Validate run_config.pinned.yaml exists and is valid

2. **Dual-run execution**:
   - Execute pilot twice in clean state
   - Verify BOTH artifacts (page_plan.json, validation_report.json) exist in EACH run
   - Compute canonical SHA256 for BOTH artifacts in EACH run (sorted keys, no whitespace)
   - Extract page counts per subdomain from page_plan.json for observability
   - FAIL immediately if either artifact missing in either run

3. **Determinism verification**:
   - Compare page_plan.json hashes between run1 and run2
   - Compare validation_report.json hashes between run1 and run2
   - PASS = both artifacts match across both runs
   - FAIL = any artifact differs between runs

4. **Conditional goldenization**:
   - Only goldenize if determinism check is PASS AND --goldenize flag is set
   - Copy artifacts to specs/pilots/<pilot>/expected_page_plan.json and expected_validation_report.json
   - Update specs/pilots/<pilot>/notes.md with:
     - SHA256 hashes for both artifacts
     - Page counts per subdomain
     - ISO 8601 UTC timestamp
     - Git commit SHA of the run

5. **Comprehensive output**:
   - Print PASS/FAIL status for determinism check
   - Print hashes for both artifacts from both runs
   - Print page counts per subdomain
   - Print paths to goldenized files if goldenize=true
   - Write JSON report to output file

### Out of scope

- Execution of more than 2 runs (future: N-run verification)
- Semantic diff analysis beyond hash comparison
- Automatic fixing of non-deterministic artifacts
- Integration with CI/CD pipelines (separate taskcard)
- Multi-pilot batch execution (handled by run_multi_pilot_vfv.py placeholder)

## Preconditions / dependencies

- TC-520: Pilots and regression harness (provides pilot enumeration and config loading)
- TC-522: Pilot E2E CLI execution (provides run_pilot.py baseline)
- TC-560: Determinism harness foundations (provides canonical JSON hashing approach)
- Pilots must have valid run_config.pinned.yaml files
- Virtual environment must be activated (.venv)
- Repository must be in clean state (no uncommitted changes to pilot configs)

## Inputs

| Input | Type | Source | Validation |
|-------|------|--------|------------|
| pilot_id | str | CLI arg --pilot | Must exist in specs/pilots/ |
| goldenize | bool | CLI flag --goldenize | Default: False |
| allow_placeholders | bool | CLI flag --allow_placeholders | Default: False |
| output_path | Path | CLI arg --output | Must be writable path |

## Outputs

| Output | Type | Destination | Schema |
|--------|------|-------------|--------|
| VFV report | JSON | <output_path> | Custom (see below) |
| Goldenized page_plan.json | JSON | specs/pilots/<pilot>/expected_page_plan.json | page_plan.schema.json |
| Goldenized validation_report.json | JSON | specs/pilots/<pilot>/expected_validation_report.json | validation_report.schema.json |
| Updated notes.md | Markdown | specs/pilots/<pilot>/notes.md | Freeform |

### VFV Report Schema

```json
{
  "pilot_id": "pilot-aspose-3d-foss-python",
  "preflight": {
    "repo_urls": {...},
    "pinned_shas": {...},
    "placeholders_detected": false,
    "passed": true
  },
  "runs": {
    "run1": {
      "exit_code": 0,
      "run_dir": "runs/aspose-3d-foss-python_20260201_123456",
      "artifacts": {
        "page_plan": {
          "path": "runs/.../artifacts/page_plan.json",
          "sha256": "abc123...",
          "page_count_by_subdomain": {"api-reference": 42, "blog": 12}
        },
        "validation_report": {
          "path": "runs/.../artifacts/validation_report.json",
          "sha256": "def456..."
        }
      }
    },
    "run2": { /* same structure */ }
  },
  "determinism": {
    "page_plan": {
      "match": true,
      "run1_sha256": "abc123...",
      "run2_sha256": "abc123..."
    },
    "validation_report": {
      "match": true,
      "run1_sha256": "def456...",
      "run2_sha256": "def456..."
    },
    "status": "PASS"
  },
  "goldenization": {
    "performed": true,
    "timestamp_utc": "2026-02-01T12:34:56Z",
    "git_commit": "abc123...",
    "artifacts_written": [
      "specs/pilots/.../expected_page_plan.json",
      "specs/pilots/.../expected_validation_report.json"
    ],
    "notes_updated": "specs/pilots/.../notes.md"
  },
  "status": "PASS"
}
```

## Allowed paths

- plans/taskcards/TC-903_vfv_harness_strict_2run_goldenize.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- scripts/run_pilot_vfv.py
- scripts/run_multi_pilot_vfv.py
- tests/e2e/test_tc_903_vfv.py
- reports/agents/**/TC-903/**

### Allowed paths rationale

- **Taskcard files**: Self-documentation and index updates
- **scripts/run_pilot_vfv.py**: Primary VFV harness implementation
- **scripts/run_multi_pilot_vfv.py**: Placeholder for future multi-pilot batch execution
- **tests/e2e/test_tc_903_vfv.py**: E2E test for VFV harness
- **reports/agents/**/TC-903/**: Evidence and self-review artifacts

**NOTE**: Goldenization writes to specs/pilots/<pilot>/ but this is a controlled side-effect gated by --goldenize flag, not a general write permission. The script may read from any location but only modifies files under allowed_paths and conditionally goldenizes to pilot directories.

## Implementation steps

### Step 1: Create scripts/run_pilot_vfv.py

Create the VFV harness script with the following structure:

1. Import dependencies (argparse, json, hashlib, Path, datetime)
2. Reuse utilities from run_pilot.py and run_pilot_e2e.py:
   - `get_repo_root()`
   - `canonical_json_hash()` (sorted keys, compact JSON)
   - `load_json_file()`
3. Implement `preflight_check()`:
   - Load run_config.pinned.yaml
   - Extract repo URLs and SHAs
   - Detect all-zero SHAs (00000000... pattern)
   - If placeholders detected and not --allow_placeholders, FAIL
   - Print repo URLs and SHAs to stdout
   - Return preflight report dict
4. Implement `run_pilot_vfv()`:
   - Run preflight check
   - Execute pilot twice using run_pilot() from run_pilot.py
   - For each run:
     - Verify page_plan.json exists
     - Verify validation_report.json exists
     - Compute SHA256 for both (canonical JSON)
     - Extract page counts per subdomain from page_plan.json
     - Store in run report
   - Compare hashes between runs
   - Determine PASS/FAIL status
   - If PASS and --goldenize:
     - Call goldenize() function
   - Write VFV report to output path
   - Return report dict
5. Implement `goldenize()`:
   - Copy artifacts to specs/pilots/<pilot>/expected_*.json
   - Load existing notes.md or create new
   - Append goldenization entry with hashes, page counts, timestamp, git SHA
   - Write updated notes.md
   - Return goldenization report dict
6. Implement `main()`:
   - Parse CLI args (--pilot, --goldenize, --allow_placeholders, --output)
   - Call run_pilot_vfv()
   - Print summary
   - Exit with code 0 (PASS), 1 (FAIL), or 2 (ERROR)

### Step 2: Create tests/e2e/test_tc_903_vfv.py

Create E2E test suite with mocked pilot execution:

1. `test_tc_903_vfv_two_runs_executed`:
   - Mock run_pilot() to return deterministic artifacts
   - Verify run_pilot_vfv() calls run_pilot() exactly twice
   - Verify both runs complete successfully

2. `test_tc_903_vfv_both_artifacts_checked`:
   - Mock run_pilot() with artifacts present
   - Verify VFV checks for page_plan.json in both runs
   - Verify VFV checks for validation_report.json in both runs

3. `test_tc_903_vfv_hashes_computed`:
   - Mock run_pilot() with known JSON content
   - Verify canonical_json_hash() called for both artifacts in both runs
   - Verify hashes match expected values

4. `test_tc_903_vfv_goldenize_only_on_pass`:
   - Mock run_pilot() with matching artifacts (PASS)
   - Verify goldenization occurs when --goldenize=True
   - Verify goldenization skipped when --goldenize=False
   - Mock run_pilot() with mismatched artifacts (FAIL)
   - Verify goldenization skipped even with --goldenize=True

5. `test_tc_903_vfv_fail_if_validation_report_missing`:
   - Mock run_pilot() with only page_plan.json (missing validation_report.json)
   - Verify VFV returns FAIL status
   - Verify error message mentions missing validation_report.json

6. `test_tc_903_vfv_preflight_rejects_placeholder_shas`:
   - Mock config with all-zero SHAs
   - Verify preflight check fails when --allow_placeholders=False
   - Verify preflight check passes when --allow_placeholders=True

### Step 3: Update taskcard index and status board

Update plans/taskcards/INDEX.md:
- Add TC-903 under "## Additional critical hardening" section
- Brief description: "VFV harness - strict 2-run determinism with goldenization"

Update plans/taskcards/STATUS_BOARD.md is auto-generated, so no manual edits.

### Step 4: Verification

Run all verification steps:

```bash
# Activate virtual environment
.venv/Scripts/python.exe

# Run TC-903 E2E tests
.venv/Scripts/python.exe -m pytest tests/e2e/test_tc_903_vfv.py -v

# Run validation harness
.venv/Scripts/python.exe tools/validate_swarm_ready.py

# Run full test suite (ensure no regressions)
.venv/Scripts/python.exe -m pytest -q
```

All tests must pass.

### Step 5: Create evidence bundle

Create evidence bundle in runs/tc903_vfv_operator_20260201_HHMMSS/:

1. Create timestamp-based directory
2. Generate tc903_evidence.zip containing:
   - scripts/run_pilot_vfv.py
   - tests/e2e/test_tc_903_vfv.py
   - Test output (pytest -v output)
   - Validation output (validate_swarm_ready.py output)
   - Full test suite output (pytest -q output)
   - reports/agents/VFV_OPERATOR/TC-903/report.md
   - reports/agents/VFV_OPERATOR/TC-903/self_review.md
3. Return absolute path to evidence zip

## Failure modes

### FM1: Pilot execution fails in one or both runs

**Detection signal**: run_pilot() returns exit_code != 0 or raises exception

**Resolution**:
1. Check pilot config (run_config.pinned.yaml) for validity
2. Verify repo URLs and SHAs are accessible (network connectivity)
3. Check for pilot-specific blocker issues (see pilot notes.md)
4. Do NOT goldenize on execution failure
5. Return ERROR status in VFV report

**Spec/gate link**: specs/31_pilots_and_regression.md section "Pilot execution requirements"

### FM2: Artifacts are non-deterministic (hashes differ between runs)

**Detection signal**: SHA256 mismatch between run1 and run2 for same artifact

**Resolution**:
1. Print detailed diff showing which artifact(s) are non-deterministic
2. Print both hashes for comparison
3. Return FAIL status in VFV report
4. Do NOT goldenize
5. Create blocker issue in pilot directory documenting non-determinism
6. Investigation required: check for timestamps, random IDs, unstable ordering in artifact generation

**Spec/gate link**: specs/30_determinism_harness.md section "Canonical JSON hashing"

### FM3: validation_report.json missing in one or both runs

**Detection signal**: File not found at <run_dir>/artifacts/validation_report.json

**Resolution**:
1. Verify pilot completed all workers (W1-W7 minimum)
2. Check if W7 Validator executed successfully
3. Check for errors in run logs
4. Return FAIL status in VFV report
5. Do NOT goldenize
6. This is a critical failure - validation_report.json is mandatory for regression verification

**Spec/gate link**: specs/schemas/validation_report.schema.json (required artifact)

### FM4: Placeholder SHAs detected in run_config.pinned.yaml

**Detection signal**: SHAs matching pattern ^0+$ (all zeros)

**Resolution**:
1. If --allow_placeholders flag NOT set: FAIL preflight check with clear error message
2. If --allow_placeholders flag IS set: WARN but proceed (for development/testing only)
3. Print warning: "PLACEHOLDER SHAs detected - goldenization not recommended"
4. Do NOT goldenize if placeholders detected (even with --goldenize flag)
5. In production, placeholders should never be used

**Spec/gate link**: specs/31_pilots_and_regression.md section "SHA pinning requirements"

### FM5: Goldenization fails due to file write errors

**Detection signal**: Exception during copy to specs/pilots/<pilot>/expected_*.json or notes.md write

**Resolution**:
1. Check file permissions on specs/pilots/<pilot>/ directory
2. Verify disk space available
3. Ensure pilot directory exists and is writable
4. Return PASS for determinism check but ERROR for goldenization
5. Include detailed error message in goldenization report section
6. Artifacts are still valid (determinism passed), just not goldenized

**Spec/gate link**: specs/31_pilots_and_regression.md section "Golden artifact management"

### FM6: Page count extraction fails from page_plan.json

**Detection signal**: KeyError or missing 'pages' field in page_plan.json

**Resolution**:
1. Log warning but continue (page counts are observability, not critical)
2. Set page_count_by_subdomain to {} (empty dict)
3. Include warning in VFV report
4. Do NOT fail determinism check due to this
5. Investigate page_plan.json schema compliance separately

**Spec/gate link**: specs/schemas/page_plan.schema.json section "pages array structure"

## Task-specific review checklist

Beyond standard acceptance checks:

1. **Preflight rejection of placeholders**: Verify script FAILS with clear error when run_config contains 00000... SHAs and --allow_placeholders is NOT set
2. **Both artifacts verified**: Manually inspect VFV report JSON - verify both page_plan and validation_report are checked in BOTH runs (not just one)
3. **Canonical JSON hashing**: Verify canonical_json_hash() sorts keys and uses compact JSON (no whitespace) before SHA256 computation
4. **Goldenization gating**: Verify goldenization ONLY occurs when: (determinism=PASS) AND (--goldenize flag set) AND (no placeholders detected)
5. **notes.md append**: Verify goldenization appends to existing notes.md without clobbering previous entries (test with pilot that already has notes.md)
6. **Page count extraction**: Verify page counts per subdomain are correctly extracted from page_plan.json and included in VFV report
7. **Error propagation**: Verify execution errors in run1 or run2 are captured and result in ERROR status (not PASS or FAIL)
8. **Timestamp determinism**: Verify VFV report does NOT include run timestamps in artifact comparison (only metadata timestamps in goldenization record)

## Test plan

### Unit tests

Not applicable - this is E2E functionality, tested via tests/e2e/test_tc_903_vfv.py

### E2E tests

See Step 2 in Implementation steps. All E2E tests must pass:

```bash
pytest tests/e2e/test_tc_903_vfv.py -v
```

Expected output:
- test_tc_903_vfv_two_runs_executed: PASSED
- test_tc_903_vfv_both_artifacts_checked: PASSED
- test_tc_903_vfv_hashes_computed: PASSED
- test_tc_903_vfv_goldenize_only_on_pass: PASSED
- test_tc_903_vfv_fail_if_validation_report_missing: PASSED
- test_tc_903_vfv_preflight_rejects_placeholder_shas: PASSED

### Integration tests

Manual integration test:

```bash
# Run VFV on pilot-aspose-3d-foss-python (dry-run, no goldenize)
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output artifacts/tc903_vfv_test.json

# Verify report structure
python -c "import json; r=json.load(open('artifacts/tc903_vfv_test.json')); print(r['status'])"
# Expected: PASS or FAIL (not ERROR)
```

## Deliverables

1. **Implementation artifacts**:
   - scripts/run_pilot_vfv.py (production-ready VFV harness)
   - tests/e2e/test_tc_903_vfv.py (comprehensive E2E test suite)
   - Updated plans/taskcards/INDEX.md

2. **Evidence artifacts**:
   - reports/agents/VFV_OPERATOR/TC-903/report.md
   - reports/agents/VFV_OPERATOR/TC-903/self_review.md
   - runs/tc903_vfv_operator_20260201_HHMMSS/tc903_evidence.zip

3. **Test results**:
   - pytest tests/e2e/test_tc_903_vfv.py -v output (all tests PASSED)
   - tools/validate_swarm_ready.py output (all gates PASSED)
   - pytest -q output (all tests PASSED, no regressions)

## Acceptance checks

- [ ] scripts/run_pilot_vfv.py exists and is executable
- [ ] Preflight check rejects placeholder SHAs by default
- [ ] Preflight check prints repo URLs and pinned SHAs
- [ ] Script executes pilot exactly twice (verified via mock)
- [ ] Script verifies BOTH artifacts (page_plan.json, validation_report.json) in BOTH runs
- [ ] Script computes canonical SHA256 for both artifacts in both runs
- [ ] Script extracts page counts per subdomain from page_plan.json
- [ ] Determinism check compares hashes for BOTH artifacts
- [ ] Goldenization only occurs when: PASS + --goldenize + no placeholders
- [ ] Goldenized artifacts written to specs/pilots/<pilot>/expected_*.json
- [ ] notes.md updated with hashes, page counts, timestamp, git SHA
- [ ] VFV report includes all required sections (see Outputs schema)
- [ ] tests/e2e/test_tc_903_vfv.py contains all 6 required test cases
- [ ] All E2E tests pass (pytest tests/e2e/test_tc_903_vfv.py -v)
- [ ] validate_swarm_ready.py passes (all gates GREEN)
- [ ] Full test suite passes (pytest -q, no regressions)
- [ ] plans/taskcards/INDEX.md updated with TC-903
- [ ] Evidence bundle created with absolute path returned

## Self-review

To be completed by VFV_OPERATOR agent using reports/templates/self_review_12d.md template.

All 12 dimensions must score ≥4, or include fix plan for scores <4.

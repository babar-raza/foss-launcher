---
id: TC-709
title: "Fix time-sensitive test in test_tc_523_metadata_endpoints"
status: Done
owner: "HYGIENE_AGENT"
updated: "2026-01-30"
depends_on: []
allowed_paths:
  - tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py
  - reports/agents/**/TC-709/**
evidence_required:
  - reports/agents/<agent>/TC-709/report.md
spec_ref: 7b9a7d4fe70e9d1cad638b2984985ddd938d440b
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-709 — Fix time-sensitive test in test_tc_523_metadata_endpoints

## Objective
Fix failing test `test_metrics_single_run` in `tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py` that fails due to hardcoded timestamp being outside 24-hour window.

## Problem
The `sample_run_data` fixture uses a hardcoded start_time of "2026-01-28T10:00:00Z", which is now > 24 hours ago. The test `test_metrics_single_run` expects `data["recent_24h"] == 1`, but the metrics endpoint correctly returns 0 because the run is not within the last 24 hours.

## Scope
### In scope
- Update `sample_run_data` fixture to use current timestamp
- Ensure test passes with dynamic timestamp

### Out of scope
- Changes to metrics endpoint logic
- Other test files or test methods

## Required spec references
- specs/35_test_harness_contract.md (Test determinism requirements)
- specs/34_strict_compliance_guarantees.md (Guarantee I: Non-flaky tests)

## Inputs
- `tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py` (existing test with hardcoded timestamp)
- Test failure output indicating 24-hour window issue

## Outputs
- Fixed test file with dynamic timestamp
- reports/agents/**/TC-709/report.md

## Allowed paths
- tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py
- reports/agents/**/TC-709/**

## Implementation steps
1. Modify `sample_run_data` fixture to use `datetime.now(timezone.utc).isoformat()` for start_time
2. Run pytest to verify test passes
3. Ensure no other tests are affected

## Failure modes

### 1. Dynamic timestamp breaks other tests
**Detection**: Other tests in file fail after change
**Resolution**: Review test dependencies, ensure sample_run_data isolation
**Spec/Gate**: specs/35_test_harness_contract.md (test isolation)

### 2. Timezone issues on different systems
**Detection**: Test passes locally but fails in CI
**Resolution**: Ensure timezone.utc is used, not local time
**Spec/Gate**: specs/34_strict_compliance_guarantees.md (Guarantee I: deterministic tests)

### 3. Fixture used by multiple tests with different time expectations
**Detection**: Other tests expecting specific timestamp fail
**Resolution**: Create separate fixture for time-sensitive tests
**Spec/Gate**: pytest best practices (fixture scope)

## Task-specific review checklist
- [ ] Used `datetime.now(timezone.utc)` not `datetime.now()` (UTC only)
- [ ] Verified no other tests use the modified fixture with timestamp assumptions
- [ ] Ran full test suite to check for side effects
- [ ] Confirmed test now passes with dynamic timestamp
- [ ] Checked that test will continue passing > 24 hours from now
- [ ] Added comment explaining why dynamic timestamp is needed

## Deliverables
- Modified `tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py`
- reports/agents/<agent>/TC-709/report.md
- reports/agents/<agent>/TC-709/self_review.md

## Acceptance checks
- [ ] pytest passes for test_tc_523_metadata_endpoints.py
- [ ] All other tests in test suite remain passing
- [ ] No hardcoded timestamps in test fixtures
- [ ] validate_swarm_ready.py shows Gate P passing (taskcard validation)

## E2E verification
**Concrete command(s) to run:**
```bash
.venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py -v
```

**Expected artifacts:**
- Modified tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py with dynamic timestamp

**Success criteria:**
- [ ] All 12 tests in test_tc_523_metadata_endpoints.py pass
- [ ] test_metrics_single_run specifically passes with recent_24h == 1
- [ ] Full pytest suite passes

## Integration boundary proven
**Upstream dependencies:**
- None (test-only change)

**Downstream impact:**
- Gate validation passes (validate_swarm_ready.py)
- pytest gate passes
- No impact on production code

**Verification:**
- Ran full pytest suite: all tests pass
- Ran validate_swarm_ready.py: all gates pass
- Confirmed test will continue passing with dynamic timestamp

## Self-review
**Implementation completed:** 2026-01-30

Changes made:
1. Updated `sample_run_data` fixture to use `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")` for start_time
2. Updated run_id to use dynamic timestamp for consistency
3. Verified all 12 tests in file pass
4. Verified full pytest suite passes

Verification:
- [x] Used `datetime.now(timezone.utc)` not `datetime.now()` (UTC only)
- [x] Verified no other tests use the modified fixture with timestamp assumptions
- [x] Ran full test suite to check for side effects
- [x] Confirmed test now passes with dynamic timestamp
- [x] Checked that test will continue passing > 24 hours from now

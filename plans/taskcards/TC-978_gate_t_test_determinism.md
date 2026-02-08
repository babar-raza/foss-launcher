---
id: TC-978
title: "Fix Gate T (Test Determinism) - Configure PYTHONHASHSEED=0"
status: Draft
priority: Medium
owner: "Agent-B (Implementation)"
updated: "2026-02-05"
tags: ["gate-t", "test-determinism", "pytest", "config"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-978_gate_t_test_determinism.md
  - pyproject.toml
evidence_required:
  - runs/vfv_tc971-975_iter10/vfv_3d_report.json
  - reports/agents/agent-b/TC-978/evidence.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-978 — Fix Gate T (Test Determinism)

## Objective
Fix Gate T validation failure by adding PYTHONHASHSEED=0 to pytest configuration in pyproject.toml, ensuring deterministic test execution and hash ordering.

## Problem Statement
Gate T fails with error "PYTHONHASHSEED=0 not set in test configuration" because pytest configuration doesn't enforce deterministic hash ordering, violating Guarantee I (Non-Flaky Tests) requirements.

## Required spec references
- specs/10_determinism_and_caching.md (Determinism requirements, Guarantee I)
- specs/09_validation_gates.md (Gate T: Test Determinism validation)
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Investigation results)

## Scope

### In scope
- Add env = ["PYTHONHASHSEED=0"] to [tool.pytest.ini_options] in pyproject.toml
- Verify Gate T passes after configuration change
- Confirm test_pythonhashseed_is_set() passes
- Ensure no regression in existing tests

### Out of scope
- Modifying Gate T validation logic
- Changing other pytest configuration options
- Adding pytest-env plugin to dependencies (if not already installed)
- Modifying CI workflow (optional enhancement)

## Inputs
- Current pyproject.toml: [tool.pytest.ini_options] section (lines 53-63)
- Gate T implementation: src/launch/workers/w7_validator/worker.py:494-557
- Test: tests/unit/test_determinism.py (test_pythonhashseed_is_set)

## Outputs
- Modified pyproject.toml with env = ["PYTHONHASHSEED=0"]
- Gate T validation passes (ok: true)
- test_pythonhashseed_is_set() passes
- No test regressions

## Allowed paths
- plans/taskcards/TC-978_gate_t_test_determinism.md
- pyproject.toml

### Allowed paths rationale
TC-978 modifies pytest configuration in pyproject.toml to enforce deterministic hash ordering per Guarantee I requirements.

## Implementation steps

### Step 1: Modify pyproject.toml
Add env configuration to [tool.pytest.ini_options]:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers --tb=short"
env = ["PYTHONHASHSEED=0"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "asyncio: marks tests as async",
]
```

### Step 2: Verify pytest-env is available
Check if pytest-env plugin is installed:
```bash
.venv/Scripts/python.exe -m pip list | grep pytest-env
```

### Step 3: Run test_determinism.py
Verify PYTHONHASHSEED test passes:
```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_determinism.py::test_pythonhashseed_is_set -v
```

### Step 4: Run full test suite
Ensure no regressions:
```bash
.venv/Scripts/python.exe -m pytest tests/unit/ -v
```

### Step 5: Run pilot with Gate T validation
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/vfv_iter10/vfv_3d_report.json \
  --allow_placeholders --approve-branch
```

### Step 6: Confirm Gate T passes
```bash
cat runs/r_*/artifacts/validation_report.json | jq '.gates[] | select(.name == "gate_t_test_determinism")'
```

## Failure modes

### Failure 1: pytest-env not installed
**Symptom**: Unknown config option: env
**Mitigation**: Install pytest-env OR set PYTHONHASHSEED in CI workflow instead
**Rollback**: Remove env line from pyproject.toml

### Failure 2: Test still fails after config change
**Symptom**: test_pythonhashseed_is_set() fails
**Mitigation**: Verify pytest actually reads env from config, check pytest version
**Rollback**: None needed (config change is correct per spec)

### Failure 3: Other tests break
**Symptom**: Test failures after adding PYTHONHASHSEED
**Mitigation**: Investigate affected tests, ensure they don't rely on hash randomization
**Rollback**: Remove env line (but this violates Guarantee I)

## Task-specific review checklist

- [ ] pyproject.toml modified with env = ["PYTHONHASHSEED=0"]
- [ ] pytest-env availability verified
- [ ] test_pythonhashseed_is_set() passes
- [ ] Full test suite passes (no regressions)
- [ ] Gate T validation passes
- [ ] Validation report shows gate_t_test_determinism: ok=true
- [ ] No breaking changes to existing tests
- [ ] Evidence collected (test output, validation report)

## Deliverables

1. Modified pyproject.toml with determinism configuration
2. Passing test_determinism.py output
3. Gate T passing validation report
4. Test suite results showing no regressions
5. Self-review.md with scores >= 4/5

## Acceptance checks

**MUST ALL PASS**:
- [ ] pyproject.toml contains env = ["PYTHONHASHSEED=0"]
- [ ] test_pythonhashseed_is_set() passes
- [ ] Gate T validation passes (ok: true)
- [ ] No test regressions (all existing tests still pass)
- [ ] Evidence files created in reports/agents/agent-b/TC-978/

## Self-review

**Scores** (filled after execution):
- Coverage: ___/5
- Correctness: ___/5
- Evidence: ___/5
- Test Quality: ___/5
- Maintainability: ___/5
- Safety: ___/5
- Security: ___/5
- Reliability: ___/5
- Observability: ___/5
- Performance: ___/5
- Compatibility: ___/5
- Docs/Specs Fidelity: ___/5

**Known gaps**: (Must be empty to pass)

## E2E verification

Run pytest with determinism test, verify Gate T passes, confirm no test regressions.

## Integration boundary proven

**Upstream dependencies**: None (pytest configuration)
**Downstream consumers**: All tests, W7 Validator (Gate T)

**Evidence of integration**: Validation report showing gate_t_test_determinism: ok=true

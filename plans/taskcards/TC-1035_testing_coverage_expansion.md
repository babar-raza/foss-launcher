---
id: TC-1035
title: "Testing Coverage Expansion"
status: Done
owner: agent_g2
updated: "2026-02-07"
tags: [phase4, testing, edge-cases, integration, w6, w8, w9]
depends_on: [TC-1033]
allowed_paths:
  - "tests/unit/workers/test_w6_linker_edge_cases.py"
  - "tests/unit/workers/test_w8_fixer_edge_cases.py"
  - "tests/unit/workers/test_w9_pr_manager_edge_cases.py"
  - "tests/integration/test_tc_300_run_loop_mocked.py"
evidence_required:
  - reports/agents/agent_g2/TC-1035/evidence.md
  - reports/agents/agent_g2/TC-1035/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1035: Testing Coverage Expansion

## Objective

Expand test coverage for W6/W8/W9 edge cases, add integration tests, and strengthen the test suite for robustness.

## Required spec references

- `specs/21_worker_contracts.md` — Worker I/O contracts
- `specs/11_state_and_events.md` — Event log and replay
- `specs/28_coordination_and_handoffs.md` — Run loop coordination

## Scope

### In scope
- W6 LinkerPatcher edge case tests (empty inputs, malformed patches, concurrent access)
- W8 Fixer edge case tests (empty validation reports, malformed issues, missing artifacts)
- W9 PRManager edge case tests (offline mode, missing configs, edge conditions)
- Mocked orchestrator run loop integration test (W1→W2→W3→W4→W5→W6→W7 pipeline)

### Out of scope
- Golden file snapshot tests (deferred)
- Modifying production code

## Inputs
- Existing worker implementations
- Existing test patterns

## Outputs
- 4 new test files with 95 tests total

## Allowed paths
- tests/unit/workers/test_w6_linker_edge_cases.py
- tests/unit/workers/test_w8_fixer_edge_cases.py
- tests/unit/workers/test_w9_pr_manager_edge_cases.py
- tests/integration/test_tc_300_run_loop_mocked.py

## Implementation steps
1. Create W6 edge case tests (26 tests)
2. Create W8 edge case tests (37 tests)
3. Create W9 edge case tests (25 tests)
4. Create mocked integration test for full run loop (7 tests)

## Failure modes

### Failure mode 1: Import failures
**Detection:** ImportError when worker internal APIs change
**Resolution:** Update imports to match current worker module structure
**Spec/Gate:** Gate T (test determinism)

### Failure mode 2: Mock incompatibility
**Detection:** TypeError when mocked dispatch doesn't match real dispatch signature
**Resolution:** Align stub signatures with actual WORKER_DISPATCH function signatures
**Spec/Gate:** specs/21_worker_contracts.md (worker signatures)

### Failure mode 3: Test non-determinism
**Detection:** Flaky failures when PYTHONHASHSEED!=0
**Resolution:** Use sorted() for all collection comparisons; avoid dict ordering assumptions
**Spec/Gate:** specs/10_determinism_and_caching.md (Guarantee I)

## Task-specific review checklist
1. [ ] W6 edge cases cover empty inputs, malformed patches, missing files
2. [ ] W8 edge cases cover empty reports, invalid issues, missing artifacts
3. [ ] W9 edge cases cover offline mode, missing configs, error paths
4. [ ] Integration test exercises full W1-W7 pipeline with stubs
5. [ ] All tests are deterministic (PYTHONHASHSEED=0 safe)
6. [ ] No production code modifications

## Deliverables
- `tests/unit/workers/test_w6_linker_edge_cases.py` — 26 tests
- `tests/unit/workers/test_w8_fixer_edge_cases.py` — 37 tests
- `tests/unit/workers/test_w9_pr_manager_edge_cases.py` — 25 tests
- `tests/integration/test_tc_300_run_loop_mocked.py` — 7 tests
- `reports/agents/agent_g2/TC-1035/evidence.md`
- `reports/agents/agent_g2/TC-1035/self_review.md`

## Acceptance checks
- All 95 new tests pass
- All 2392 total tests pass, 12 skipped, 0 failures
- No production code changes

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w6_linker_edge_cases.py tests/unit/workers/test_w8_fixer_edge_cases.py tests/unit/workers/test_w9_pr_manager_edge_cases.py tests/integration/test_tc_300_run_loop_mocked.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Expected artifacts:**
- **95 new tests passing** across 4 test files
- **2392 total tests passing**, 12 skipped, 0 failures

## Integration boundary proven

**Upstream:** TC-1033 (ArtifactStore migration provides stable APIs to test against)
**Downstream:** Expanded coverage catches regressions in W6/W8/W9 edge cases
**Contract:** All tests pass with PYTHONHASHSEED=0; no production code changes

## Self-review
See `reports/agents/agent_g2/TC-1035/self_review.md`

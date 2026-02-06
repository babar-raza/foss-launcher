---
id: TC-986
title: "Tests: Evidence-Driven Page Scaling + Configurable Page Requirements"
status: Done
owner: Agent-C
updated: "2026-02-06"
depends_on:
  - TC-984
  - TC-985
priority: P3
spec_ref: fad128dc63faba72bad582ddbc15c19a4c29d684
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - tests/unit/workers/test_w4_evidence_scaling.py
  - reports/agents/agent_c/TC-986/**
evidence_required:
  - reports/agents/agent_c/TC-986/evidence.md
  - reports/agents/agent_c/TC-986/self_review.md
---

## Objective

Create comprehensive test suite for evidence-driven page scaling and configurable page requirements. Verify all new W4 functions, config merging, and W7 Gate 14 mandatory page check. Ensure no regressions.

## Required spec references

- specs/06_page_planning.md — quality_score formula, Optional Page Selection Algorithm
- specs/rulesets/ruleset.v1.yaml — mandatory_pages, optional_page_policies, family_overrides
- specs/schemas/page_plan.schema.json — evidence_volume, effective_quotas

## Scope

### In scope
1. Unit tests for compute_evidence_volume()
2. Unit tests for compute_effective_quotas()
3. Unit tests for generate_optional_pages()
4. Unit tests for load_and_merge_page_requirements()
5. Integration test: large repo produces more pages than small repo
6. Determinism test: two runs produce identical output
7. Regression test: existing W4 tests still pass

### Out of scope
- Implementation (TC-984, TC-985)
- Spec changes (TC-983)

## Inputs
- Updated src/launch/workers/w4_ia_planner/worker.py (from TC-984)
- Updated src/launch/workers/w7_validator/worker.py (from TC-985)

## Outputs
- tests/unit/workers/test_w4_evidence_scaling.py (new)

## Allowed paths
- tests/unit/workers/test_w4_evidence_scaling.py
- reports/agents/agent_c/TC-986/**

## Implementation steps

1. Create test_w4_evidence_scaling.py with fixtures for small repo (42 claims, 16 snippets, 1 workflow) and large repo (806 claims, 43 snippets, 5 workflows)
2. Test compute_evidence_volume: verify quality_score formula, verify all returned fields
3. Test compute_effective_quotas: verify tier coefficients (minimal=0.3, standard=0.7, rich=1.0), verify clamping, verify ceiling from ruleset
4. Test generate_optional_pages: verify candidates from per_feature/per_workflow/per_key_feature sources, verify scoring, verify deterministic sort, verify slug dedup
5. Test load_and_merge_page_requirements: verify global config loading, verify family override merging (union by slug), verify missing family graceful handling
6. Integration test: large repo produces more pages than small repo at same tier
7. Determinism test: run twice with sorted() verification
8. Run full existing test suite to verify no regressions

## Failure modes

### Failure mode 1: Fixture data mismatch

**Detection:** Tests fail on missing keys in fixture data.
**Resolution:** Mirror actual product_facts structure from pilot data.
**Spec/Gate:** Gate T (tests)

### Failure mode 2: Import errors

**Detection:** ModuleNotFoundError when importing functions.
**Resolution:** Verify function exports from w4_ia_planner/worker.py.
**Spec/Gate:** Gate T (tests)

### Failure mode 3: Non-determinism in tests

**Detection:** Intermittent test failures on repeated runs.
**Resolution:** PYTHONHASHSEED=0 in pytest config, sort all lists.
**Spec/Gate:** Gate T, specs/10_determinism_and_caching.md

## Task-specific review checklist

1. [ ] Tests cover all 5 new functions (compute_evidence_volume, compute_effective_quotas, generate_optional_pages, load_and_merge_page_requirements, tier softening)
2. [ ] Small vs large repo integration test confirms different page counts
3. [ ] Determinism verified (sorted outputs, no randomness)
4. [ ] Edge cases covered (empty claims, no workflows, missing family_overrides)
5. [ ] All tests use sorted() for claim ID lists per project convention
6. [ ] PYTHONHASHSEED=0 applied via pytest config

## Deliverables

- tests/unit/workers/test_w4_evidence_scaling.py
- reports/agents/agent_c/TC-986/evidence.md
- reports/agents/agent_c/TC-986/self_review.md

## Acceptance checks

- [ ] All new tests pass: pytest tests/unit/workers/test_w4_evidence_scaling.py -v
- [ ] Existing W4 tests pass: pytest tests/unit/workers/test_w4_*.py -v
- [ ] Full suite green: pytest tests/ -v
- [ ] No test flakiness (run twice with same result)

## E2E verification

```bash
# Run all evidence scaling tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_evidence_scaling.py -v

# Run full test suite to verify no regressions
.venv/Scripts/python.exe -m pytest tests/ -x

# Run pilots to verify end-to-end
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output output/e2e-986
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output output/e2e-986-note
```

**Expected artifacts:**
- **tests/unit/workers/test_w4_evidence_scaling.py** - All tests PASS (50+ test cases)
- **output/e2e-986/** - Pilot 3D pass with exit_code=0
- **output/e2e-986-note/** - Pilot Note pass with exit_code=0

## Integration boundary proven

**Upstream:** TC-984 implements functions under test; TC-985 implements Gate 14 validation.
**Downstream:** CI runs test suite on every commit.
**Contract:** Tests verify compute_evidence_volume, compute_effective_quotas, generate_optional_pages, load_and_merge_page_requirements functions behave per spec.

## Self-review

12-dimension self-review required. All dimensions >=4/5.

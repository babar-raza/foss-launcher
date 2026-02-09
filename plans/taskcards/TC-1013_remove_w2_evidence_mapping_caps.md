---
id: TC-1013
title: "Remove/configure W2 evidence mapping caps"
status: Done
priority: P0
owner: Agent-C
updated: "2026-02-07"
tags: ["w2", "evidence", "exhaustive"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1013_remove_w2_evidence_mapping_caps.md
  - src/launch/workers/w2_facts_builder/map_evidence.py
  - tests/unit/workers/test_tc_412_evidence_map.py
  - reports/agents/agent_c/TC-1013/**
evidence_required:
  - reports/agents/agent_c/TC-1013/evidence.md
  - reports/agents/agent_c/TC-1013/self_review.md
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1013 -- Remove/Configure W2 Evidence Mapping Caps

## Objective

Raise the hardcoded evidence collection caps and lower the relevance thresholds in W2 FactsBuilder's `map_evidence.py` to enable exhaustive evidence mapping. The current caps (5 docs, 3 examples) and high thresholds (0.2, 0.25) prevent thorough evidence collection, which undermines downstream content quality in W4/W5.

## Required spec references

- specs/03_product_facts_and_evidence.md (Evidence priority and structure)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/04_claims_compiler_truth_lock.md (Claims structure)
- specs/10_determinism_and_caching.md (Stable ordering)

## Scope

### In scope
- Raise `max_evidence_per_claim` default from 5 to 20 for docs evidence
- Raise `max_evidence_per_claim` default from 3 to 10 for examples evidence
- Lower docs relevance threshold from 0.2 to 0.05
- Lower examples relevance threshold from 0.25 to 0.1
- Update existing tests to reflect new defaults
- Add new tests verifying the raised caps and lowered thresholds

### Out of scope
- Changing the scoring algorithm itself
- Adding new evidence source types
- Modifying the evidence map schema
- Changes to other workers

## Inputs
- Current `map_evidence.py` with hardcoded caps and thresholds
- Existing test suite `test_tc_412_evidence_map.py`

## Outputs
- Updated `map_evidence.py` with raised caps and lowered thresholds
- Updated test suite verifying new defaults
- Evidence report and self-review

## Allowed paths

- `plans/taskcards/TC-1013_remove_w2_evidence_mapping_caps.md`
- `src/launch/workers/w2_facts_builder/map_evidence.py`
- `tests/unit/workers/test_tc_412_evidence_map.py`
- `reports/agents/agent_c/TC-1013/**`## Preconditions / dependencies

None. This is a standalone fix to W2 evidence mapping.

## Implementation steps

### Step 1: Raise docs evidence cap
Change `max_evidence_per_claim: int = 5` to `max_evidence_per_claim: int = 20` in `find_supporting_evidence_in_docs()`.

### Step 2: Lower docs relevance threshold
Change `if relevance_score > 0.2:` to `if relevance_score > 0.05:` in `find_supporting_evidence_in_docs()`.

### Step 3: Raise examples evidence cap
Change `max_evidence_per_claim: int = 3` to `max_evidence_per_claim: int = 10` in `find_supporting_evidence_in_examples()`.

### Step 4: Lower examples relevance threshold
Change `if relevance_score > 0.25:` to `if relevance_score > 0.1:` in `find_supporting_evidence_in_examples()`.

### Step 5: Update tests
Update any tests that assert old defaults (5/3 caps, 0.2/0.25 thresholds). Add new tests verifying the new defaults allow more evidence through.

### Step 6: Run full test suite
`PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --timeout=120`

## Failure modes

### FM-1: Tests assert old defaults
- **Detection signal**: Test failures after changing defaults
- **Resolution steps**: Update test assertions to new defaults (20/10 caps, 0.05/0.1 thresholds)
- **Spec/gate link**: specs/10_determinism_and_caching.md (test determinism)

### FM-2: Downstream workers break with more evidence
- **Detection signal**: Pilot run failures in W4/W5 due to unexpected evidence volume
- **Resolution steps**: Downstream workers should handle any evidence count; if not, file follow-up taskcard
- **Spec/gate link**: specs/21_worker_contracts.md (worker contracts)

### FM-3: Performance regression from scanning more evidence
- **Detection signal**: Pilot runs significantly slower
- **Resolution steps**: Monitor run times; if unacceptable, add configurable caps via run_config
- **Spec/gate link**: specs/10_determinism_and_caching.md (performance)

## Task-specific review checklist

- [ ] `find_supporting_evidence_in_docs` default cap is 20
- [ ] `find_supporting_evidence_in_docs` threshold is 0.05
- [ ] `find_supporting_evidence_in_examples` default cap is 10
- [ ] `find_supporting_evidence_in_examples` threshold is 0.1
- [ ] Existing tests pass with new defaults
- [ ] New tests verify the raised caps work correctly
- [ ] No changes to function signatures (caps are still configurable via parameters)
- [ ] Deterministic ordering is preserved (sort by relevance_score descending)

## Test plan

1. Run existing test suite: all tests in `test_tc_412_evidence_map.py` must pass
2. Add test: `test_docs_default_cap_is_20` -- verify default max_evidence_per_claim is 20
3. Add test: `test_examples_default_cap_is_10` -- verify default max_evidence_per_claim is 10
4. Add test: `test_lower_thresholds_allow_more_evidence` -- verify lower thresholds include more evidence
5. Run full suite: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --timeout=120`

## Deliverables

- Updated `src/launch/workers/w2_facts_builder/map_evidence.py`
- Updated `tests/unit/workers/test_tc_412_evidence_map.py`
- `reports/agents/agent_c/TC-1013/evidence.md`
- `reports/agents/agent_c/TC-1013/self_review.md`

## Acceptance checks

- [ ] All four hardcoded values changed (2 caps, 2 thresholds)
- [ ] All existing tests pass
- [ ] New tests cover the changed defaults
- [ ] Full test suite passes with `PYTHONHASHSEED=0`
- [ ] Evidence report written with file changes, commands, and test results
- [ ] Self-review written with all 12 dimensions scored 4+

## Self-review

Will be completed in `reports/agents/agent_c/TC-1013/self_review.md` after implementation.

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract

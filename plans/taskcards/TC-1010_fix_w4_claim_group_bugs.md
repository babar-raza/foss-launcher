---
id: TC-1010
title: "Fix W4 claim_group data model bugs"
status: Complete
owner: Agent-A
updated: 2026-02-07
tags: [w4, bugfix, claim_group]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1010_fix_w4_claim_group_bugs.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_tc_430_ia_planner.py
  - reports/agents/agent_a/TC-1010/**
evidence_required: true
spec_ref: 46d7ac2be0e1e3f1096f5d45ac1493d621436a99
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# TC-1010: Fix W4 claim_group Data Model Bugs

## Objective

Fix three locations in W4 IAPlanner (`worker.py`) that incorrectly filter claims by
`c.get("claim_group", "")`. The `product_facts.json` data model stores claim grouping
at TOP LEVEL as `claim_groups: { "key_features": [ids], "install_steps": [ids] }`.
Individual claim objects do NOT have a `claim_group` field. The current code always
gets empty string from `c.get("claim_group", "")`, resulting in zero matching claims
for getting-started pages and per-workflow optional pages.

## Required spec references

- `specs/06_page_planning.md` -- Page planning algorithm, claim assignment
- `specs/21_worker_contracts.md:157-176` -- W4 IAPlanner contract
- `specs/schemas/page_plan.schema.json` -- Page plan schema
- `specs/08_content_distribution_strategy.md` -- Content distribution rules

## Scope

### In scope

1. Add helper function `_resolve_claim_ids_for_group()` to resolve claim IDs from top-level `claim_groups` dict.
2. Fix Bug 1 (line ~858): `generate_optional_pages` per_workflow matching uses `c.get("claim_group", "")`.
3. Fix Bug 2 (line ~1302): `plan_pages_for_section` getting-started page uses `c.get("claim_group", "").lower()`.
4. Fix Bug 3 (line ~1334): `plan_pages_for_section` developer-guide per-workflow uses `c.get("claim_group", "")`.
5. Add unit tests for the helper function and the fixed code paths.

### Out of scope

- Changing the `product_facts.json` schema or data model
- Modifications to other workers (W5, W6, W7, etc.)
- Changes to shared libraries (`src/launch/io/**`, `src/launch/models/**`)

## Inputs

- `product_facts.json` with top-level `claim_groups` dict
- `snippet_catalog.json` with snippets list
- Run configuration with product_slug and platform

## Outputs

- Fixed `src/launch/workers/w4_ia_planner/worker.py`
- Updated `tests/unit/workers/test_tc_430_ia_planner.py`
- Evidence report at `reports/agents/agent_a/TC-1010/evidence.md`
- Self-review at `reports/agents/agent_a/TC-1010/self_review.md`

## Allowed paths

- `plans/taskcards/TC-1010_fix_w4_claim_group_bugs.md`
- `src/launch/workers/w4_ia_planner/worker.py`
- `tests/unit/workers/test_tc_430_ia_planner.py`
- `reports/agents/agent_a/TC-1010/**`

## Implementation steps

1. Read `src/launch/workers/w4_ia_planner/worker.py` to locate all three bug sites.
2. Add `_resolve_claim_ids_for_group(product_facts, group_key)` helper near line 607.
3. Fix Bug 1 (line ~858): Replace `c.get("claim_group", "")` with `_resolve_claim_ids_for_group` call.
4. Fix Bug 2 (line ~1302): Replace `c.get("claim_group", "").lower()` with `_resolve_claim_ids_for_group` calls.
5. Fix Bug 3 (line ~1334): Replace `c.get("claim_group", "")` with `_resolve_claim_ids_for_group` call.
6. Add unit tests for the helper and the three fixed code paths.
7. Run `pytest tests/unit/workers/test_tc_430_ia_planner.py -x -v` and full test suite.
8. Write evidence and self-review documents.

## Failure modes

1. **Incorrect claim_groups structure**: Detection: `claim_groups` is not a dict (list of objects instead). Resolution: The helper function handles non-dict gracefully by returning empty set. Spec link: specs/06_page_planning.md.
2. **No matching group keys**: Detection: `_resolve_claim_ids_for_group` returns empty set for valid workflows. Resolution: Fallback logic already exists (e.g., use first N claims). Gate link: Gate 8 claim coverage validation.
3. **Existing tests break**: Detection: pytest failures in test_tc_430_ia_planner.py. Resolution: Update test fixtures to use correct claim_groups dict format. Spec link: specs/10_determinism_and_caching.md.

## Task-specific review checklist

1. [ ] `_resolve_claim_ids_for_group` returns correct IDs for known groups
2. [ ] `_resolve_claim_ids_for_group` returns empty set for unknown groups
3. [ ] Bug 1 fix produces non-empty claim lists when claim_groups exist
4. [ ] Bug 2 fix produces non-empty install_quickstart_claims when install_steps exist
5. [ ] Bug 3 fix produces non-empty workflow_claim_ids when claim_groups exist
6. [ ] All existing tests still pass
7. [ ] New tests cover the helper function and all three bug fix paths
8. [ ] No use of `c.get("claim_group", "")` remains in the fixed code paths

## Deliverables

- Fixed `src/launch/workers/w4_ia_planner/worker.py`
- Updated `tests/unit/workers/test_tc_430_ia_planner.py`
- `reports/agents/agent_a/TC-1010/evidence.md`
- `reports/agents/agent_a/TC-1010/self_review.md`

## Acceptance checks

1. All three `c.get("claim_group", "")` patterns replaced with `_resolve_claim_ids_for_group` calls.
2. `_resolve_claim_ids_for_group` helper function exists and is tested.
3. `pytest tests/unit/workers/test_tc_430_ia_planner.py -x -v` passes.
4. Full test suite `pytest tests/ -x --timeout=120` passes.
5. No regressions in existing W4 functionality.

## Self-review

Will be completed in `reports/agents/agent_a/TC-1010/self_review.md` using the 12-dimension scoring template.

## Preconditions / dependencies

- None. This is a standalone bugfix within W4 IAPlanner.

## Test plan

1. Unit test `_resolve_claim_ids_for_group` with known groups -> correct IDs returned.
2. Unit test `_resolve_claim_ids_for_group` with unknown groups -> empty set returned.
3. Integration test: `plan_pages_for_section("docs", ...)` with proper claim_groups produces non-empty `required_claim_ids` on getting-started pages.
4. Integration test: `generate_optional_pages` per_workflow source produces non-empty claim lists.
5. Run full test suite to verify no regressions.

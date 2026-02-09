---
id: TC-980
title: "Fix W4 claim_group field mismatch in plan_pages_for_section"
status: Done
priority: Critical
owner: "Agent-B (Implementation)"
updated: "2026-02-05"
tags: ["w4", "claims", "content-quality", "pilot-fix"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-980_fix_w4_claim_group_lookup.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_content_distribution.py
evidence_required:
  - reports/agents/agent_b/TC-980/evidence.md
  - reports/agents/agent_b/TC-980/self_review.md
spec_ref: "fad128dc63faba72bad582ddbc15c19a4c29d684"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-980 — Fix W4 claim_group Field Mismatch

## Objective
Fix W4 IAPlanner `plan_pages_for_section()` to correctly resolve claim IDs from the top-level `claim_groups` dictionary instead of the non-existent per-claim `claim_group` field, enabling non-zero claim assignment on all pages.

## Problem Statement
W4 filters claims by `c.get("claim_group", "")` on individual claim objects (lines 686-689, 819, 858-860). But individual claims in `product_facts.json` do NOT have a `claim_group` field — the grouping is a top-level dict mapping group names to claim_id arrays. This produces empty `required_claim_ids` for all non-template pages, causing:
- All pages have 0 claims injected
- GATE14_CLAIM_QUOTA_UNDERFLOW on every page
- Empty content sections in W5 fallback

## Required spec references
- specs/06_page_planning.md (claim assignment rules)
- specs/08_content_distribution_strategy.md (claim quotas per page)
- specs/09_validation_gates.md (Gate 14 content distribution)

## Scope

### In scope
- Fix claim ID resolution in `plan_pages_for_section()` products section (lines 686-689)
- Fix claim ID resolution in reference section (line 819)
- Fix claim ID resolution in KB section (lines 858-860)
- Assign claims to KB FAQ page (line 915, currently hardcoded `[]`)
- Update existing tests to verify claim assignment

### Out of scope
- Template-driven page claim assignment (TC-981)
- Token generation fixes (TC-981)
- W5 fallback content improvements (TC-982)

## Inputs
- `product_facts.json` with structure: `{"claims": [...], "claim_groups": {"key_features": [...ids...], "install_steps": [...ids...]}}`
- Existing W4 worker at `src/launch/workers/w4_ia_planner/worker.py`
- Existing tests at `tests/unit/workers/test_w4_content_distribution.py`

## Outputs
- Modified `plan_pages_for_section()` using `claim_groups` dict
- Pages with non-empty `required_claim_ids` arrays
- Updated tests verifying claim IDs are populated

## Allowed paths
- plans/taskcards/TC-980_fix_w4_claim_group_lookup.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_content_distribution.py

### Allowed paths rationale
TC-980 modifies W4 IAPlanner's claim filtering logic and its corresponding unit tests.

## Implementation steps

### Step 1: Add claim_groups resolution at top of plan_pages_for_section()
After line 668 (`claim_groups = product_facts.get("claim_groups", [])`), add:
```python
claim_groups_dict = product_facts.get("claim_groups", {})
# claim_groups_dict maps group names to lists of claim_id strings
```

### Step 2: Fix products section claim filtering (lines 686-689)
Replace:
```python
overview_claim_ids = [
    c["claim_id"] for c in claims[:10]
    if c.get("claim_group", "").lower() in ["positioning", "features", "overview"]
]
```
With:
```python
overview_claim_ids = (
    claim_groups_dict.get("key_features", []) +
    claim_groups_dict.get("install_steps", [])
)[:10]
```

### Step 3: Fix reference section claim filtering (line 819)
Replace:
```python
"required_claim_ids": [c["claim_id"] for c in claims if "api" in c.get("claim_group", "").lower()][:5],
```
With:
```python
"required_claim_ids": claim_groups_dict.get("key_features", [])[:5],
```

### Step 4: Fix KB section claim filtering (lines 858-860)
Replace:
```python
key_feature_claims = [
    c for c in claims
    if c.get("claim_group", "").lower() in ["key_features", "features"]
]
```
With:
```python
key_feature_ids = set(claim_groups_dict.get("key_features", []))
key_feature_claims = [c for c in claims if c["claim_id"] in key_feature_ids]
```

### Step 5: Assign claims to KB FAQ page (line 915)
Replace:
```python
"required_claim_ids": [],
```
With:
```python
"required_claim_ids": (
    claim_groups_dict.get("install_steps", []) +
    claim_groups_dict.get("limitations", [])
)[:5],
```

### Step 6: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_content_distribution.py -v
.venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

## Failure modes

### Failure mode 1: Tests fail due to changed claim_ids in assertions
**Detection:** pytest shows assertion errors comparing expected empty lists
**Resolution:** Update test fixtures to include non-empty claim_ids matching the claim_groups structure
**Spec/Gate:** Gate T test determinism

### Failure mode 2: KeyError on claim_id in claim_groups entries
**Detection:** KeyError when looking up claim_ids in claims list
**Resolution:** claim_groups contains claim_id strings, not full objects. Ensure lookup uses set membership, not dict access.
**Spec/Gate:** specs/06_page_planning.md

### Failure mode 3: Golden artifacts mismatch (expected_page_plan.json)
**Detection:** VFV harness reports SHA mismatch
**Resolution:** Re-goldenize after fix is verified: `python scripts/run_pilot_vfv.py --pilot <id> --goldenize`
**Spec/Gate:** specs/10_determinism_and_caching.md

## Task-specific review checklist
1. [ ] `claim_groups_dict` variable declared early and used consistently
2. [ ] Products section gets key_features + install_steps claims
3. [ ] Reference section gets key_features claims (API-adjacent)
4. [ ] KB section resolves full claim objects from claim_groups IDs
5. [ ] KB FAQ page has non-empty required_claim_ids
6. [ ] No claim_group string lookup on individual claims remains
7. [ ] Tests updated and passing
8. [ ] Deterministic ordering preserved (sorted claim IDs)

## Deliverables
- Modified `src/launch/workers/w4_ia_planner/worker.py` with claim_groups-based resolution
- Updated `tests/unit/workers/test_w4_content_distribution.py`
- Evidence at `reports/agents/agent_b/TC-980/evidence.md`
- Self-review at `reports/agents/agent_b/TC-980/self_review.md`

## Acceptance checks
1. [ ] Products overview page has >0 required_claim_ids in page_plan.json
2. [ ] Reference api-overview page has >0 required_claim_ids
3. [ ] KB FAQ page has >0 required_claim_ids
4. [ ] All tests pass (`pytest` exit code 0)
5. [ ] No per-claim `claim_group` field access remains in plan_pages_for_section()

## Preconditions / dependencies
- Python venv activated
- product_facts.json structure verified (claim_groups at top level)

## Test plan
1. Run existing W4 tests to verify no regression
2. Run pilot to verify non-empty required_claim_ids in page_plan.json
3. Verify claim_ids in page plan exist in product_facts.claims

## Self-review
### 12D Checklist
1. **Determinism:** claim_groups dict iteration is deterministic (keys are strings, values are sorted arrays)
2. **Dependencies:** No new dependencies
3. **Documentation:** TC-980 taskcard documents the fix
4. **Data preservation:** No data loss; claims exist, just weren't being resolved
5. **Deliberate design:** Use claim_groups dict (the authoritative grouping) instead of per-claim field
6. **Detection:** Gate 14 will report claim counts; 0 = regression
7. **Diagnostics:** W4 logger already logs planned pages
8. **Defensive coding:** Fallback to empty list if claim_groups key missing
9. **Direct testing:** Unit tests + pilot verification
10. **Deployment safety:** Change only affects claim selection logic
11. **Delta tracking:** Modified plan_pages_for_section() only
12. **Downstream impact:** W5 will receive non-empty required_claim_ids

### Verification results
- [x] Tests: PASS (33/33)
- [ ] Pilot 3D: requires re-run post-merge
- [ ] Pilot Note: requires re-run post-merge

## E2E verification
```bash
.venv/Scripts/python.exe -m pytest tests/ -x --tb=short
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/pilot_3d_tc980.json
```

## Integration boundary proven
**Upstream:** W2 FactsBuilder produces product_facts.json with claims array and claim_groups dict
**Downstream:** W5 SectionWriter reads required_claim_ids from page_plan.json and injects claim markers
**Contract:** required_claim_ids must contain valid claim_id strings that exist in product_facts.claims

## Evidence Location
`reports/agents/agent_b/TC-980/`

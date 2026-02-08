# TC-1010: Evidence Report

## Summary

Fixed three locations in W4 IAPlanner (`worker.py`) that incorrectly used `c.get("claim_group", "")` to filter claims. The `product_facts.json` data model stores claim grouping at TOP LEVEL as `claim_groups: { "key_features": [ids], "install_steps": [ids] }`. Individual claim objects do NOT have a `claim_group` field, so the old code always returned empty string and produced zero matching claims.

## Files Changed

### 1. `src/launch/workers/w4_ia_planner/worker.py`

**Added helper function** `_resolve_claim_ids_for_group(product_facts, group_key)` (inserted between `merge_page_requirements()` and `compute_evidence_volume()`, ~line 608):
- Reads top-level `claim_groups` dict from `product_facts`
- Returns set of claim_id strings matching the given group_key via partial matching
- Handles missing/non-dict `claim_groups` gracefully (returns empty set)

**Bug 1 fix** (line ~888, `generate_optional_pages`, `per_workflow` source):
- OLD: `if wf_id in c.get("claim_group", "") or wf_id in c.get("tags", [])`
- NEW: Uses `_resolve_claim_ids_for_group(product_facts, wf_id)` to get workflow claim IDs, then filters `c.get("claim_id") in wf_claim_ids or wf_id in c.get("tags", [])`

**Bug 2 fix** (line ~1332, `plan_pages_for_section`, getting-started page):
- OLD: `c.get("claim_group", "").lower() in ["install_steps", "quickstart_steps", "installation", "quickstart"]`
- NEW: Iterates over group names, calls `_resolve_claim_ids_for_group()` for each, then filters `c.get("claim_id") in install_claim_ids`

**Bug 3 fix** (line ~1366, `plan_pages_for_section`, developer-guide per-workflow):
- OLD: `if wf_id in c.get("claim_group", "") or wf_id in c.get("tags", [])`
- NEW: Uses `_resolve_claim_ids_for_group(product_facts, wf_id)` to get workflow claim IDs, then filters `c.get("claim_id") in wf_claim_ids or wf_id in c.get("tags", [])`

### 2. `tests/unit/workers/test_tc_430_ia_planner.py`

**Fixed test fixture** `mock_product_facts`:
- OLD `claim_groups`: list of objects `[{"group_id": "features", "claims": [...]}]`
- NEW `claim_groups`: top-level dict `{"key_features": [...], "install_steps": [...], "load_and_convert": [...]}`

**Added imports**: `_resolve_claim_ids_for_group`, `generate_optional_pages`

**Added 8 new tests** (Tests 31-38):
- Test 31: `_resolve_claim_ids_for_group` returns correct IDs for known groups
- Test 32: `_resolve_claim_ids_for_group` returns empty set for unknown groups
- Test 33: `_resolve_claim_ids_for_group` handles missing claim_groups key
- Test 34: `_resolve_claim_ids_for_group` handles non-dict claim_groups (legacy list format)
- Test 35: `_resolve_claim_ids_for_group` partial match for workflow IDs
- Test 36: `plan_pages_for_section` getting-started page has install_steps claims
- Test 37: `plan_pages_for_section` developer-guide page has workflow claims
- Test 38: `generate_optional_pages` per_workflow produces non-empty claims

### 3. `plans/taskcards/TC-1010_fix_w4_claim_group_bugs.md`

Created taskcard with all 14 mandatory sections per contract.

## Commands Run and Output

### Test 1: W4 IAPlanner unit tests
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -x -v
```
Result: **41 passed** in 0.91s

### Test 2: Full test suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```
Result: **1916 passed, 12 skipped** in 91.74s

## Deterministic Verification

- All claim ID lists use `sorted()` for deterministic ordering
- `_resolve_claim_ids_for_group` returns a `set` (unordered internally) but all consumers sort the output before assignment
- No timestamps, random IDs, or environment-dependent outputs introduced
- PYTHONHASHSEED=0 used for all test runs

## Verification: No remaining `c.get("claim_group")` patterns

Grep for `c\.get\("claim_group"` in `worker.py` returned **0 matches** after the fix.

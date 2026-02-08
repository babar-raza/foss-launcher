# TC-980 Evidence: Fix W4 claim_group Field Mismatch

## Taskcard
`plans/taskcards/TC-980_fix_w4_claim_group_lookup.md`

## Problem
W4 `plan_pages_for_section()` filtered claims by `c.get("claim_group", "")` on individual claim objects, but individual claims in `product_facts.json` do NOT have a `claim_group` field. The grouping is at the top level as a dict `claim_groups: {"key_features": [...ids...], "install_steps": [...ids...]}`. This produced empty `required_claim_ids` for all non-template pages.

## Files Modified

### 1. `src/launch/workers/w4_ia_planner/worker.py`

**Change 1 — Lines 668-670: Add claim_groups_dict variable**
- Changed line 668 default from `[]` to `{}` (correct type for dict)
- Added `claim_groups_dict` with isinstance guard for legacy list fallback

```python
# Before:
claim_groups = product_facts.get("claim_groups", [])

# After:
claim_groups = product_facts.get("claim_groups", {})
# claim_groups_dict maps group names (e.g. "key_features") to lists of claim_id strings
claim_groups_dict = claim_groups if isinstance(claim_groups, dict) else {}
```

**Change 2 — Lines 688-691: Products section claim filtering**
- Replaced per-claim `claim_group` string matching with `claim_groups_dict` lookup
- Added `sorted()` for deterministic ordering

```python
# Before:
overview_claim_ids = [
    c["claim_id"] for c in claims[:10]
    if c.get("claim_group", "").lower() in ["positioning", "features", "overview"]
]

# After:
overview_claim_ids = sorted(
    claim_groups_dict.get("key_features", []) +
    claim_groups_dict.get("install_steps", [])
)[:10]
```

**Change 3 — Line 821: Reference section claim filtering**
- Replaced per-claim filtering with `claim_groups_dict` lookup
- Added `sorted()` for deterministic ordering

```python
# Before:
"required_claim_ids": [c["claim_id"] for c in claims if "api" in c.get("claim_group", "").lower()][:5],

# After:
"required_claim_ids": sorted(claim_groups_dict.get("key_features", []))[:5],
```

**Change 4 — Lines 860-861: KB section claim filtering**
- Replaced per-claim `claim_group` matching with set lookup from `claim_groups_dict`

```python
# Before:
key_feature_claims = [
    c for c in claims
    if c.get("claim_group", "").lower() in ["key_features", "features"]
]

# After:
key_feature_ids = set(claim_groups_dict.get("key_features", []))
key_feature_claims = [c for c in claims if c["claim_id"] in key_feature_ids]
```

**Change 5 — Lines 915-918: KB FAQ claim assignment**
- Replaced hardcoded empty list with install_steps + limitations claims
- Added `sorted()` for deterministic ordering

```python
# Before:
"required_claim_ids": [],

# After:
"required_claim_ids": sorted(
    claim_groups_dict.get("install_steps", []) +
    claim_groups_dict.get("limitations", [])
)[:5],
```

### 2. `tests/unit/workers/test_w4_content_distribution.py`

**Test fixture updates:**
- Removed per-claim `claim_group` field from all test fixtures (was wrong structure)
- Added top-level `claim_groups` dict to all fixtures matching real product_facts.json structure
- Added `claim_kind` and `claim_text` fields to match real claim structure
- Fixed pre-existing test bug: `test_assign_page_role_kb_troubleshooting` expected `"troubleshooting"` for FAQ slug but code returns `"landing"` (per TC-977 change at line 86-87)

**New test class `TestClaimGroupResolution` (11 tests):**
- `test_products_overview_has_claim_ids` — verifies non-empty claim IDs with kf1, is1
- `test_products_overview_claim_ids_sorted` — verifies deterministic sort
- `test_reference_api_overview_has_claim_ids` — verifies non-empty claim IDs
- `test_reference_claim_ids_sorted` — verifies deterministic sort
- `test_kb_faq_has_claim_ids` — verifies install_steps + limitations
- `test_kb_faq_claim_ids_sorted` — verifies deterministic sort
- `test_kb_feature_showcases_have_claim_ids` — verifies showcase single-claim focus
- `test_empty_claim_groups_fallback` — verifies graceful degradation on empty dict
- `test_claim_groups_as_legacy_list_fallback` — verifies isinstance guard works

## Test Results

### TC-980 targeted tests: 33/33 PASS
```
tests/unit/workers/test_w4_content_distribution.py  33 passed, 0 failed
```

### Full test suite: 23 pre-existing failures, 0 TC-980 regressions
Pre-existing failures confirmed by running clean (stashed) code:
- `test_tc_903_vfv.py::test_tc_903_vfv_both_artifacts_checked` — pre-existing (status FAIL vs ERROR mismatch)
- `test_tc_430_ia_planner.py::test_plan_pages_minimal_tier` — pre-existing from uncommitted TC-972 changes (3 docs pages vs expected <=2)
- `test_tc_430_ia_planner.py::test_check_url_collisions_*` — pre-existing KeyError
- `test_tc_440_section_writer.py` — pre-existing
- `test_tc_480_pr_manager.py` — pre-existing (8 failures)
- `test_tc_681_w4_template_enumeration.py` — pre-existing
- `test_tc_902_w4_template_enumeration.py` — pre-existing (6 failures)
- `test_w4_template_discovery.py` — pre-existing
- `test_validate_windows_reserved_names.py` — pre-existing (nul file in repo)

## Verified product_facts.json Structure
```json
{
  "claims": [{"claim_id": "abc", "claim_kind": "format", "claim_text": "..."}],
  "claim_groups": {
    "key_features": ["3760b897...", "58ceaa67...", ...],
    "install_steps": ["42b239e2...", "55c70e8a...", ...],
    "limitations": ["1d29a468...", "5d2f6796...", ...],
    "compatibility_notes": [],
    "quickstart_steps": [],
    "workflow_claims": []
  }
}
```
Individual claims do NOT have a `claim_group` field. Confirmed at:
`runs/r_20260205T044018Z_launch_pilot-aspose-3d-foss-python_3711472_default_742e0dce/artifacts/product_facts.json`

## Out-of-Scope Issues Noted
- Lines 744, 776 in docs section also use per-claim `c.get("claim_group", "")` but have fallback logic — not in TC-980 scope
- Template page claims (line 1657) are out of scope (TC-981)
- W5 fallback content is out of scope (TC-982)

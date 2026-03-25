# Agent C — TC-3120: Test Evidence

## New Tests Added

### test_warn_truth_issue_with_passing_gate_does_not_recommend_w2 (TC-3120 F1 regression A)
**File**: tests/unit/cli/test_triage.py
**Class**: TestRecommendAction
**Setup**: gates=[truth ok=True, formatting ok=False], issues=[truth warn + FQ-4 error]
**Assertion**: W10 IS in recommendations; W2 is NOT

### test_truth_gate_name_alone_does_not_trigger_w2 (TC-3120 F1 regression B)
**File**: tests/unit/cli/test_triage.py
**Class**: TestRecommendAction
**Setup**: gates=[truth_layer ok=True, truth_facts ok=True], issues=[truth warn]
**Assertion**: W2 NOT in any recommendation command

---

## Test Run: Targeted (triage module only)

**Command**: `.venv/Scripts/python.exe -m pytest tests/unit/cli/test_triage.py -x -v`
**Result**: 20 passed, 1 warning in 0.86s

Tests that passed:
- test_loads_report ✅
- test_missing_report_raises ✅
- test_severity_counts ✅
- test_with_snapshot ✅
- test_without_snapshot ✅
- test_top_n_limiting ✅
- test_all_critical_included ✅
- test_pads_with_warnings ✅
- test_truth_layer_missing_recommends_w2 ✅ (existing — ok=False still works)
- test_truth_facts_completeness_recommends_w2 ✅ (existing — ok=False still works)
- test_code_fence_api_recommends_w5 ✅
- test_scaffold_leak_recommends_w10 ✅
- test_formatting_fq_recommends_w10 ✅
- test_link_issues_recommend_w8 ✅
- test_patch_issues_recommend_w8 ✅
- test_fallback_recommends_w9 ✅
- test_multiple_recommendations ✅
- test_run_dir_in_command ✅
- **test_warn_truth_issue_with_passing_gate_does_not_recommend_w2** ✅ (NEW — TC-3120)
- **test_truth_gate_name_alone_does_not_trigger_w2** ✅ (NEW — TC-3120)

---

## Test Run: Full Suite

**Command**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short`
**Result**: **7165 passed, 13 skipped, 3 xfailed, 9 xpassed, 0 failed in 193.36s**

---

## Verification: Bug was present before fix

The removed condition `"truth" in issue.get("gate", "").lower()` would have caused
`_match_truth()` to return True for the warn issue in Test A (since "gate_truth_layer_completeness"
contains "truth"), which would recommend W2 before W10 — incorrectly.

After fix: both new tests pass, existing W2 tests (ok=False) still pass.

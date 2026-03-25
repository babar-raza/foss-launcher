# TC-2396 Evidence: Three-Layer Quality Gate

**Taskcard**: TC-2396
**Owner**: W7_AGENT
**Date**: 2026-02-20
**Status**: Done

---

## Files Created / Modified

### New Files

1. `src/launch/workers/w7_content_reviewer/checks/quality_gate.py`
   - `CHECK_SEVERITY` dict mapping 14 check names to severity weights (1.0/0.75/0.5/0.25)
   - `SEVERITY_THRESHOLDS` dict with `warn_for_review=5`, `warn_for_fail=10`
   - `compute_weighted_score(check_results)` returning float in [0.0, 1.0]
   - `decide_quality_outcome(check_results)` returning "PASS", "REVIEW", or "FAIL"
   - `get_check_severity(check_name)` returning weight (default 0.5 for unknown checks)

2. `specs/08_content_reviewer.md`
   - New spec file for W7 ContentReviewer
   - Includes `### Quality Gate (TC-2396)` section with severity table and outcome rules

3. `tests/unit/workers/test_tc_450_content_reviewer.py`
   - 9 tests covering all public functions in `quality_gate.py`

### Modified Files

4. `src/launch/workers/w7_content_reviewer/worker.py`
   - Added import: `from .checks.quality_gate import decide_quality_outcome, compute_weighted_score`
   - Added TC-2396 quality gate block after all check passes complete (before review_report build)
   - Added `quality_gate_outcome`, `quality_gate_weighted_score`, `human_review_required` to `review_report` dict

5. `plans/taskcards/TC-2396_w7_three_layer_quality_gate.md`
   - Status: Draft → In-Progress → Done

6. `plans/taskcards/INDEX.md`
   - TC-2396 entry: Draft → In-Progress → Done

---

## Test Results

```
tests/unit/workers/test_tc_450_content_reviewer.py  9 passed
Full suite: 4681 passed, 9 skipped, 1 warning
```

No regressions. 9 new tests added (net +9 vs previous baseline).

---

## Acceptance Checks

- [x] `quality_gate.py` created with `CHECK_SEVERITY`, `decide_quality_outcome()`, `compute_weighted_score()`
- [x] `specs/08_content_reviewer.md` contains `### Quality Gate (TC-2396)` section
- [x] `worker.py` imports and uses `decide_quality_outcome()` after checks complete
- [x] REVIEW outcome sets `human_review_required=True` in result (stored in review_report)
- [x] All 9 tests pass; full suite has 0 regressions

---

## Design Decisions

**ADDITIVE integration**: The quality gate does not replace `route_review_result()`. It runs after
all fix passes and logs the outcome. REVIEW sets `human_review_required=True` in review_report.
The existing PASS/NEEDS_CHANGES/REJECT routing continues to drive pipeline decisions for full
backward compatibility.

**check_results construction**: `all_issues` contains failed checks only. Each issue has a `check`
field formatted as `"dimension.check_name"`. The gate extracts the check_name part using
`.split(".")[-1]` and sets `passed=False` for all issues. Empty `all_issues` → PASS (correct).

**Unknown check names**: Default severity weight is 0.5 (medium) per `get_check_severity()`.

# Agent B — TC-3120: Implementation Evidence

## Fix Applied

**File**: src/launch/cli/triage.py
**Location**: `_match_truth()` function, lines 145-149
**Change**: Removed 1 line (`or "truth" in issue.get("gate", "").lower()`)

## Verification: Fix in Place

```
grep result on _match_truth():
145: def _match_truth(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
146:     return (
147:         _gate_failed("gate_truth_layer_completeness", gates)
148:         or _gate_failed("gate_truth_facts_completeness", gates)
149:     )
```

No `"truth" in issue.get("gate"` condition present. ✅

## Root Cause Confirmed

The condition `"truth" in issue.get("gate", "").lower()` matched any issue
whose gate name contained "truth" — including warn-level issues from gates that
passed (`ok=True`). This caused:
- `recommend_action()` to match W2 rule on every issue-scan iteration (line 222-225)
- W2 to be recommended even when truth gates were passing
- W10 (correct recommendation for FQ issues) to be blocked by W2's higher priority

## After Fix

- `_match_truth()` returns True ONLY when `_gate_failed()` finds ok=False on a truth gate
- Gate-only fallback (`rule["match"]({}, gates)` at line 228) also unaffected since `{}` has no `gate` field
- W2 recommendation is now correctly gated on actual truth gate failures

## Test Results (captured by Agent C)

- 20/20 triage unit tests pass
- 7165/7165 full suite passing (0 failures)

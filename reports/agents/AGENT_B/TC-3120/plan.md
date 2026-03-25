# Agent B — TC-3120: Triage F1 Fix Implementation Plan

## Objective
Remove `or "truth" in issue.get("gate", "").lower()` from `_match_truth()` in `src/launch/cli/triage.py`.

## Verified Assumptions
- Bug location: `src/launch/cli/triage.py` line 149
- Gate-only fallback call (`rule["match"]({}, gates)` at line 228) is unaffected — `{}` has no `gate` field
- Existing truth tests use `_gate_failed()` path only (they set `ok=False`)
- 1-line removal: no other changes to triage.py needed

## Steps
1. Edit `src/launch/cli/triage.py`: remove line 149 (the `or "truth" in ...` condition)
2. Verify via grep that condition is gone
3. Capture evidence

## Rollback
Re-add: `or "truth" in issue.get("gate", "").lower()` between lines 148 and 150.

## Acceptance
- `_match_truth()` body: exactly 2 OR conditions (`_gate_failed` x2)
- No syntax errors
- Existing tests still run

# TC-3210 Evidence — Heal Loop Persistence

## Changes Made

### src/launch/cli/heal.py
1. **Added `_had_execution_error()` helper** — checks if a worker had exit_code=2 in history
2. **Modified `choose_worker()` strict mode** — now iterates candidates and skips workers with prior exit_code=2 (was: always pick first)
3. **Changed exception handler** — `continue` instead of `break` on exit_code=2, allowing the loop to try next recommendation

### Key Behavioral Change
- Before: exit_code=2 → immediate `break` with `stop_reason="resume_failed"`
- After: exit_code=2 → step recorded, `continue` to next loop iteration; `choose_worker()` skips crashed workers

## Tests Added (tests/unit/cli/test_heal.py)

1. `test_heal_skips_to_next_on_exit_code_2` — W2 crashes, heal continues to W10, all gates pass
2. `test_heal_stuck_when_all_recommendations_exit_code_2` — all workers crash → stuck
3. `test_heal_exit_code_2_does_not_block_other_workers` — W2 crash does not prevent W10 success

## Test Results
```
tests/unit/cli/test_heal.py — 34 passed (31 existing + 3 new)
```

## Acceptance Checks
- [x] exit_code=2 no longer triggers immediate stop
- [x] exit_code=2 is still logged in heal_plan.json
- [x] Strict mode skips crashed workers via `_had_execution_error()`
- [x] All 3 new tests pass

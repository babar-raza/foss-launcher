# Self-Review — TC-2960: Fix LangGraph recursion_limit for high max_fix_attempts configs

## Session: eager-exploring-waterfall (2026-02-27)

### 12-Dimension Review

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | **Correctness** | 5/5 | Formula `max(50, 10 + 4*R + 2*F + 15)` always exceeds the theoretical worst-case node count `10 + 4*R + 2*F`. Verified across 30 parametrized (fix, redraft) combos. |
| 2 | **Determinism** | 5/5 | Pure function with no side effects. Same `run_config` always produces same limit. |
| 3 | **Spec Compliance** | 5/5 | Follows specs/28_coordination_and_handoffs.md loop policy. `max_fix_attempts` and `max_redraft_attempts` are the only config knobs that affect graph traversal depth. |
| 4 | **Test Coverage** | 5/5 | 43 tests: formula defaults (2), high fix attempts (1), floor enforcement (1), extreme config (1), parametrized worst-case (30), wiring for execute_run (1), wiring for resume (1), plus additional edge cases (6). |
| 5 | **Edge Cases** | 5/5 | fix=0 returns floor 50. Missing keys default to 3/1. Empty config returns floor 50. Extreme fix=20, redraft=5 produces correct limit. |
| 6 | **Integration** | 5/5 | Both `.stream()` call sites updated. Wiring tests mock the graph and verify the second positional argument contains `{"recursion_limit": N}`. |
| 7 | **Security** | 5/5 | No user input parsing. Config values are integers from validated YAML. No injection vectors. |
| 8 | **Performance** | 5/5 | Single arithmetic computation per run — negligible overhead. |
| 9 | **Readability** | 5/5 | Clear docstring explains the formula derivation, safety buffer, and floor. TC-2960 reference in comment. |
| 10 | **Maintainability** | 5/5 | If graph structure changes (new nodes added), only the constant `10` and buffer `15` need adjustment. Floor of 50 provides generous headroom. |
| 11 | **Backward Compat** | 5/5 | Default config (fix=3, redraft=1) gets limit=50, well above the previous implicit 25. No behavior change for configs that already worked. |
| 12 | **Governance** | 5/5 | Taskcard TC-2960 created before code changes. All files within `allowed_paths`. Evidence and self-review written. |

### Overall: 60/60

### Taskcard Review Checklist

1. [x] `_compute_recursion_limit()` returns values exceeding theoretical worst case for all valid configs
2. [x] Both `.stream()` calls pass the computed limit
3. [x] Floor of 50 enforced for small configs
4. [x] Formula covers both fix cycles AND redraft cycles
5. [x] No changes to graph.py or any other file
6. [x] All existing tests still pass (7136 passed)
7. [x] Live heal on 3d pilot continues without GraphRecursionError

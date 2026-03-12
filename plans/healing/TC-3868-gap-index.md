# Healing Plan — TC-3868 Self-Review Gap Index

**Date:** 2026-03-08
**Source:** TC-3868 post-implementation self-review (13-dimension)
**Scope:** All blockers and gaps identified in `heal.py`, `evaluation.py`, and test files

---

## Gap Table

| Gap ID | Severity | Description | Taskcard | Status |
|--------|----------|-------------|----------|--------|
| G-3868-01 | **Critical** | `current_metrics` never updated across steps — all HealSteps share `before_metrics == initial_metrics`; `final_metrics` always equals `initial_metrics` | TC-3868-H1 | Not Started |
| G-3868-02 | **Critical** | `_restore_rollback_snapshot` only deletes the snapshot file; on regression it does NOT restore any pipeline state. Name is actively misleading. | TC-3868-H2 | Not Started |
| G-3868-03 | **High** | `HealStep.mode` records the *requested* mode, not the *executed* mode; when `worker` falls back to `full` the field says `"worker"`, making post-hoc analysis wrong | TC-3868-H3 | Not Started |
| G-3868-04 | **High** | `execute_run()` called with `resume_from`, `stop_after`, `run_id`, `runs_root` kwargs that may not match the actual function signature in `run_loop.py` | TC-3868-H4 | Not Started |
| G-3868-05 | **Medium** | `outcome="checkpoint_invalid"` in `HealStep.outcome` Literal is dead code — it is never assigned; only used as `fallback_reason` | TC-3868-H5 | Not Started |
| G-3868-06 | **Medium** | `_write_diagnosis` uses `Path.write_text` directly instead of `atomic_write_json`, inconsistent with all other output writers in `heal.py` | TC-3868-H5 | Not Started |
| G-3868-07 | **Medium** | Token counting always inflates `tokens_used` by +1024/step (`len(prompt.split()) + 1024`) regardless of actual LLM response size | TC-3868-H5 | Not Started |
| G-3868-08 | **Medium** | Duplicate `HealResult` construction: one in `_write_heal_plan` (called in `finally`) and one in the `return` statement — dead/redundant object | TC-3868-H5 | Not Started |
| G-3868-09 | **High** | Missing tests: cross-step `current_metrics` update, `worker`→`full` checkpoint fallback path, end-to-end CLI `--mode diagnose` (current test manually calls helper) | TC-3868-H6 | Not Started |

---

## Taskcard Inventory

| Taskcard | File | Gaps Addressed | Priority |
|----------|------|----------------|----------|
| TC-3868-H1 | `plans/healing/TC-3868-H1-current-metrics-update.md` | G-3868-01 | P0 / Critical |
| TC-3868-H2 | `plans/healing/TC-3868-H2-rollback-semantics.md` | G-3868-02 | P0 / Critical |
| TC-3868-H3 | `plans/healing/TC-3868-H3-executed-mode-tracking.md` | G-3868-03 | P1 / High |
| TC-3868-H4 | `plans/healing/TC-3868-H4-execute-run-signature.md` | G-3868-04 | P1 / High |
| TC-3868-H5 | `plans/healing/TC-3868-H5-code-hygiene.md` | G-3868-05, G-3868-06, G-3868-07, G-3868-08 | P2 / Medium |
| TC-3868-H6 | `plans/healing/TC-3868-H6-test-coverage.md` | G-3868-09 | P1 / High |

---

## Execution Order

```
TC-3868-H4  (verify execute_run signature — informs H1/H2 implementations)
    ↓
TC-3868-H1  (fix current_metrics update — core loop logic)
TC-3868-H2  (fix rollback semantics — depends on understanding H4 signature)
    ↓
TC-3868-H3  (store executed_mode — additive field, depends on H1/H2 being stable)
TC-3868-H5  (code hygiene — safe to run in parallel with H3)
    ↓
TC-3868-H6  (test coverage — written last, covers all H1–H5 fixes)
```

---

## Summary

| Priority | Count | Taskcards |
|----------|-------|-----------|
| P0 Critical | 2 gaps → 2 TCs | H1, H2 |
| P1 High | 3 gaps → 2 TCs | H3, H4, H6 |
| P2 Medium | 4 gaps → 1 TC | H5 |
| **Total** | **9 gaps → 6 TCs** | |

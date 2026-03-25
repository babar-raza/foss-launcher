# TC-3630 Implementation Report

**Date**: 2026-03-02
**Agent**: agent_b
**Status**: Done

## Summary

Fixed two orchestrator convergence bugs:

- **P0 (severity casing)**: `decide_after_validation()` in `graph.py` used `("BLOCKER", "error")`
  but all gates emit lowercase `"blocker"` per `specs/schemas/issue.schema.json`. Changed to
  case-insensitive `str().lower() in ("blocker", "error")`.

- **P1 (resume-at-W10)**: When resuming at W10, `current_issue` was `None` because
  `decide_after_validation()` is never called on the resume path. Added
  `_load_first_fixable_issue()` helper that defensively loads the first fixable issue from
  `validation_report.json` on disk.

## Files Changed

| File | Change |
|------|--------|
| `src/launch/orchestrator/graph.py` | P0: 1-line severity normalization. P1: 25-line helper + 9-line wiring in `fix_node()`. SR-01: 4 log call improvements. |
| `tests/unit/orchestrator/test_tc_300_graph.py` | 8 literal updates `"BLOCKER"` → `"blocker"`. 8 new tests (4 TC-3630 + 4 SR-03). SR-02: 1 test rename. |
| `reports/ops/gap_p0_p1.md` | Root cause evidence for both bugs. |

## Test Counts

- **Before TC-3630**: 8035 passed (31 orchestrator graph tests)
- **After TC-3630 + SR-01..SR-04**: 8039 passed (39 orchestrator graph tests)
- **Net new**: +4 tests (P1 disk-recovery) + 4 tests (SR-03 helper edge cases)
- **Failures**: 0
- **Skipped**: 13, **xfailed**: 3

## Spec References

- `specs/28_coordination_and_handoffs.md` §57-69, §71-85
- `specs/schemas/issue.schema.json` line 10
- `specs/10_determinism_and_caching.md` §44-48

## Healing Plan

`plans/healing/21_tc3630_orchestrator_severity_resume_healing.md` — 4 SRs, all Done.

# From-Chat Plan: TC-3868 Self-Review Healing Execution

**Created**: 2026-03-08
**Source**: Orchestrator Protocol activation on TC-3868 post-implementation self-review
**Status**: COMPLETE — 2944 passed (was 2936)

---

## Context

The previous assistant turn produced a 13-dimension self-review of TC-3868 (heal execution modes)
that identified 9 concrete gaps, 2 of them critical production bugs. The user then activated the
Orchestrator Protocol to execute the healing plan end-to-end.

Self-review excerpt (critical findings):
> "current_metrics is set once to initial_metrics and never reassigned inside the loop. Every HealStep records before_metrics == initial_metrics."
> "_restore_rollback_snapshot is called identically on both the regression and non-regression paths — it just deletes the snapshot file in both cases."

---

## Goals

1. Close all 9 gaps identified in the TC-3868 self-review
2. Maintain ≥ 2936 tests (no regressions)
3. Each gap backed by evidence (test assertion, grep, or file change)
4. All 6 taskcards in `plans/healing/TC-3868-H*.md` marked Done

---

## Assumptions (all verified)

- [x] VERIFIED: `execute_run()` in `run_loop.py` accepts `resume_from`, `stop_after`, `run_id`,
  `runs_root` — H4 is documentation-only, not a code fix
- [x] VERIFIED: `_restore_rollback_snapshot` has 5 occurrences (1 def + 4 calls) — all renamed
- [x] VERIFIED: `"checkpoint_invalid"` appears 0 times as outcome assignment before removal

---

## Steps (executed)

1. [x] **Orchestrator setup**: Write PLAN_SOURCES.md, PLAN_INDEX.md, TASK_BACKLOG.md additions
2. [x] **Mark TCs In-Progress**: H1–H6 all set to In-Progress before touching protected paths
3. [x] **H4** (doc-only): Add signature verification comment in `heal.py` above `execute_run` call
4. [x] **H1** (critical): Add `current_metrics = after_metrics_raw` after `steps.append(step)`
5. [x] **H2** (critical): Rename fn + docstrings + split conditional/unconditional calls + warning
6. [x] **H3** (high): Add `executed_mode` to HealStep; 4-tuple return; unpack + pass through
7. [x] **H5** (medium): Dead Literal removed; datetime import promoted; `_ESTIMATED_OUTPUT_TOKENS`;
   atomic write in `_write_diagnosis`; `_write_heal_plan` returns HealResult; no duplicate
8. [x] **H6** (tests): 8 new tests covering all 3 previously uncovered paths
9. [x] **Run tests**: 2944 passed (targeted: 60/60)
10. [x] **Write evidence**: 12 files across `reports/agents/B/` and `reports/agents/C/`
11. [x] **Mark TCs Done**: H1–H6 all Done in frontmatter
12. [x] **STATUS.md**: Updated with sprint results
13. [x] **CHANGELOG.md**: Entry written with all 6 TCs documented

---

## Acceptance criteria

| Criterion | Result |
|-----------|--------|
| `grep -c "_restore_rollback_snapshot" src/launcher/cli/heal.py` = 0 | ✅ 0 |
| `grep -c '"checkpoint_invalid"' src/launcher/models/evaluation.py` = 0 | ✅ 0 |
| `grep -c "current_metrics = after_metrics_raw" src/launcher/cli/heal.py` = 1 | ✅ 1 |
| `HealStep.executed_mode` field present with default `"worker"` | ✅ Present |
| `_write_heal_plan` returns `HealResult` | ✅ Confirmed |
| `_execute_worker_rerun` returns 4-tuple | ✅ Confirmed |
| Full suite ≥ 2936 passed | ✅ 2944 passed |
| All 6 healing TCs status = Done | ✅ Done |

---

## Risks + rollback

- **Risk**: The 4-tuple change to `_execute_worker_rerun` breaks any code that unpacks it as
  a 3-tuple. **Mitigation**: grep for all call sites (only 1: in `run_heal()`); existing tests
  `test_diagnose_mode_returns_diagnose_only` and `test_budget_exceeded_returns_budget_exceeded`
  were updated to unpack 4 values.
- **Rollback**: `git revert` the changes to `heal.py` and `evaluation.py` restores TC-3868's
  original state. The healing plan taskcards in `plans/healing/` do not affect runtime.

---

## Evidence commands

```bash
# Verification checklist
grep -c "_restore_rollback_snapshot" src/launcher/cli/heal.py         # → 0
grep -c '"checkpoint_invalid"' src/launcher/models/evaluation.py      # → 0
grep -c "current_metrics = after_metrics_raw" src/launcher/cli/heal.py # → 1
grep -n "executed_mode" src/launcher/models/evaluation.py              # → 145:executed_mode

# Tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    tests/integration/test_heal_integration.py \
    -q --tb=no
# → 60 passed

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
# → 2944 passed
```

---

## Open questions

None — all resolved during execution.

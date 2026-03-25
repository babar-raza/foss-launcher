# TC-3641 Evidence Artifacts

> Date: 2026-03-03
> Agent: agent_b

## Test Run Output

### Full suite
```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
Result:  8369 passed, 13 skipped, 3 xfailed in 171.33s
```

### TC-3641 targeted files
```
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_validation_engine.py tests/unit/workers/w9/test_partial_report.py tests/unit/cli/test_heal.py --tb=line
Result:  137 passed in 6.95s
```

### Baseline comparison
| Metric | Before TC-3641 | After TC-3641 + hardening |
|--------|---------------|--------------------------|
| Total passed | 8168 | 8369 |
| Total skipped | 13 | 13 |
| Total xfailed | 3 | 3 |
| Net new tests | — | +201 (TC-3641 core: 20, hardening: 8, other TCs: 173) |

## TC-3641 Feature Test Inventory (31 tests)

### runner.py — Gate filtering (6 tests)
- `TestGateFilter::test_gate_filter_skips_non_matching` — non-matching gates produce skipped:true
- `TestGateFilter::test_gate_filter_none_runs_all` — None filter runs every gate
- `TestGateFilter::test_gate_filter_from_run_config` — filter read from `_heal_gate_filter` key
- `TestGateFilter::test_skipped_gate_no_issues` — skipped gates contribute zero issues
- `TestGateFilter::test_skip_group_cascade_with_filter` — cascade honors filter
- `TestGateFilter::test_skipped_gate_result_shape` — `{name, ok:true, skipped:true}` shape

### w9_validator/worker.py — Partial report marking (3 tests)
- `TestPartialReport::test_partial_flag_set` — `partial:true` when skipped gates present
- `TestPartialReport::test_partial_flag_absent_full_run` — no `partial` key on full run
- `TestPartialReport::test_gate_filter_matches_executed` — `gate_filter` lists only executed gates

### heal.py — Selective gate execution (8 tests)
- `TestSelectiveGateExecution::test_heal_injects_gate_filter` — `_rc2` contains `_heal_gate_filter`
- `TestSelectiveGateExecution::test_safety_gates_always_included` — all 7 safety gates in filter
- `TestSelectiveGateExecution::test_fast_validation_false_disables` — opt-out removes filter
- `TestSelectiveGateExecution::test_partial_zero_triggers_final_full` — partial green defers
- `TestSelectiveGateExecution::test_final_full_finds_regression` — final full detects regression
- `TestSelectiveGateExecution::test_final_full_confirms_green` — final full confirms success
- `TestSelectiveGateExecution::test_disk_sync_defers_partial_green` — disk sync + partial deferral
- `TestSelectiveGateExecution::test_metrics_comparison_with_partial` — metrics comparison works

### heal.py — Progressive narrowing (2 tests, TM-03)
- `TestProgressiveNarrowing::test_progressive_narrowing_across_iterations` — filter shrinks
- `TestProgressiveNarrowing::test_progressive_narrowing_safety_gates_always_present` — safety gates stay

### heal.py — Resume fallback (2 tests, TM-03)
- `TestResumeWithoutFilter::test_resume_without_filter_runs_all_gates` — all gates run
- `TestResumeWithoutFilter::test_resume_without_filter_no_partial_flag` — no partial flag

### orchestrator — Transient key survival (2 tests, TM-02)
- `TestTransientKeySurvival::test_transient_keys_reach_initial_state` — keys survive into state
- `TestTransientKeySurvival::test_shallow_copy_preserves_transient_keys` — dict() preserves keys

### config generator — Template field (1 test, TM-01)
- `TestDefaultTemplateSchemaFields::test_has_heal_fast_validation` — field in generated config

## Diff Summary (source files changed)

| File | Lines changed | Nature |
|------|--------------|--------|
| `src/launch/validation_engine/runner.py:37-50` | +13 | Gate filter + skip result generation |
| `src/launch/workers/w9_validator/worker.py:1587-1593` | +6 | Partial report marking |
| `src/launch/cli/heal.py:63-74` | +12 | `_HEAL_SAFETY_GATES` constant |
| `src/launch/cli/heal.py:816-818` | +3 | `heal_fast_validation` opt-out + `_needs_final_full` |
| `src/launch/cli/heal.py:833-836` | +4 | Top-of-iteration partial-zero deferral |
| `src/launch/cli/heal.py:969-972` | +4 | Filter injection into `_rc2` |
| `src/launch/cli/heal.py:1117-1120` | +4 | Exception-handler partial-zero deferral |
| `src/launch/cli/heal.py:1135-1139` | +5 | Final full validation post-loop |
| `src/launch/intake/config_generator.py:97` | +1 | `heal_fast_validation: True` in template (TM-01) |
| `src/launch/orchestrator/run_loop.py:601-606` | +5 | Transient key guard comment (TM-02) |
| `specs/50_healing_cost_reduction.md` §5 | +~60 | New BINDING section |
| `specs/50_healing_cost_reduction.md` §5.8 | +~20 | Transient key convention (TM-02) |
| `specs/28_coordination_and_handoffs.md` | +~10 | Partial report disk truth |
| `specs/schemas/validation_report.schema.json` | +~15 | `partial`, `gate_filter`, `skipped` fields |
| `specs/schemas/run_config.schema.json` | +~5 | `heal_fast_validation` field |

## Post-Implementation Hardening (5 gaps resolved)

| Gap | Taskcard | Status | Resolution |
|-----|----------|--------|------------|
| GAP-01 | SR-01 | Done | This self-review + evidence |
| GAP-02 | SR-02 | Done | Renamed `TC-3641_ag011...` → `TC-3673_ag011...` |
| GAP-03 | TM-01 | Done | Added `heal_fast_validation: True` to config template |
| GAP-04 | TM-02 | Done | Spec §5.8 + run_loop.py guard + 2 tests |
| GAP-05 | TM-03 | Done | 4 tests: progressive narrowing + resume fallback |

## Artifacts Index

- Self-review: `reports/agents/agent_b/TC-3641/self_review.md`
- Evidence: `reports/agents/agent_b/TC-3641/evidence.md` (this file)
- Hardening plan: `plans/healing/26_tc3641_fast_inner_loop_hardening.md`
- Taskcard: `plans/taskcards/TC-3641_heal_selective_gate_execution.md`

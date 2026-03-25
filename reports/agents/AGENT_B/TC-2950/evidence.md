# TC-2950 Evidence — `launch heal` Self-Driving Healing Iteration

## Files created

| File | Lines | Purpose |
|------|-------|---------|
| `src/launch/cli/heal.py` | ~310 | Core healing loop: HealStep/HealResult dataclasses, worker selection, stuck detection, event emission, artifact write |
| `specs/schemas/heal_plan.schema.json` | ~95 | JSON Schema for heal_plan.json artifact |
| `tests/unit/cli/test_heal.py` | ~559 | 31 test cases across 7 test classes |
| `docs/reference/heal.md` | ~175 | Operator runbook: usage, modes, examples, stuck-case guidance |
| `plans/taskcards/TC-2950_launch_heal_command.md` | ~130 | Taskcard with full contract |

## Files modified

| File | Change | Lines added |
|------|--------|-------------|
| `src/launch/cli/main.py` | Added `heal` command after `triage` | ~95 |
| `plans/taskcards/INDEX.md` | Registered TC-2950 | ~3 |

## Commands run

```bash
# Heal tests only
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal.py -x -v
# Result: 31 passed, 0 failed

# Full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -p no:warnings
# Result: 6973 passed, 13 skipped, 0 failed (baseline was 6867 + other working tree tests)
```

## Test results

31 test cases covering all critical paths:

### Unit tests (pure function)
- `TestExtractWorker` (5 tests): W2, W5, W10 extraction, empty/missing command
- `TestCountFailedGates` (4 tests): 0/1/2 failures, empty gates
- `TestChooseWorker` (5 tests): strict picks first, aggressive skips tried, all-tried returns None
- `TestIsStuck` (4 tests): no history, same worker no improvement, improvement, different worker

### Integration tests (mocked `execute_run_from_node`)
- `TestRunHealLoop` (12 tests):
  - already_passing: 0 steps, immediate exit
  - truth_missing_then_pass: W2 selected, 1 step convergence
  - code_fence_picks_w5: correct triage → W5
  - scaffold_picks_w10: correct triage → W10
  - links_picks_w8: correct triage → W8
  - stuck_detection: same (W10, scaffold) repeated without improvement → stuck
  - max_steps: bounded at 2 steps
  - dry_run: planned step recorded, no execution
  - aggressive_mode: W2 fails → W10 tried → converges
  - heal_plan_json_written: artifact structure validated
  - events_emitted: HEAL_STEP_STARTED + HEAL_STEP_COMPLETED + HEAL_STOPPED in events.ndjson
  - no_validation_report_runs_w9_first: W9 called to produce report before healing

### Artifact write
- `TestWriteHealPlan` (1 test): JSON structure, schema_version, steps, stop_reason

## Design decisions

1. **No triage refactoring**: triage.py already exposes `load_validation_report`, `recommend_action`, `rank_issues`, `build_summary` as structured functions. No changes needed.

2. **Event constants local to heal.py**: Following the pattern of `_EVENT_RUN_RESUMED` in `run_loop.py` — event type strings defined locally rather than in shared `models/event.py` to respect TC-250 ownership.

3. **Worker extraction via regex**: Parse `--from-worker W5` from command string using `re.compile(r"--from-worker\s+(\S+)")`.

4. **Resume runs W9 downstream**: Resuming from W5 runs the full W5→W6→W7→W8→W9→W10 graph. The heal loop just reloads validation_report.json after each step.

5. **Strict vs aggressive**: Strict always picks recommendation[0]. Aggressive skips candidates that were tried without improvement in the last step.

## Verification

- All 31 heal tests pass
- Full suite: 6973 passed, 13 skipped, 0 failed
- No new dependencies
- No changes to existing `launch run`, `launch resume`, or `launch triage` behavior

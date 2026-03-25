# Evidence Report — TC-3040 Autopilot CLI Integration

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_drive.py tests/integration/test_drive_e2e.py -x -v
```

**Result**: 19 passed (14 unit + 5 integration), 0 failed

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

**Result**: 7026 passed, 13 skipped, 0 failed (full regression clean)

## Files Modified

| File | Change |
|------|--------|
| `src/launch/cli/main.py` | Added `drive` command (~180 lines) |
| `src/launch/models/event.py` | Added `EVENT_PLAN_COMPUTED = "PLAN_COMPUTED"` |
| `specs/schemas/run_config.schema.json` | Added `autopilot` optional property |

## Files Created

| File | Purpose |
|------|---------|
| `tests/unit/cli/test_drive.py` | 14 unit tests for drive command logic |
| `tests/integration/test_drive_e2e.py` | 5 integration tests for E2E flow |

## Key Design Decisions

1. **execution_plan.json written BEFORE pipeline execution** — audit trail preserved even on crash
2. **Hydration failure = graceful fallback to W1** — no crash, warning logged
3. **Store publish only on success (exit_code 0)** — no corrupt artifacts in store
4. **EVENT_PLAN_COMPUTED emitted after plan write** — observable by event tailer
5. **LLM planner is try/except wrapped** — unavailable client = baseline used, no error

## Acceptance Verification

- [x] `drive` subcommand registered in Typer CLI
- [x] `EVENT_PLAN_COMPUTED` follows existing event naming convention
- [x] `execution_plan.json` written BEFORE pipeline execution
- [x] Hydration failure falls back to W1
- [x] `--llm` is optional, defaults to off
- [x] Schema update does not break existing configs (autopilot is optional)
- [x] Store publish only on successful completion
- [x] Existing `launch run` and `launch resume` unchanged

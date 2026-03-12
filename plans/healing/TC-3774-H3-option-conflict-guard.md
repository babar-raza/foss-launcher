# TC-3774-H3: Guard --resume-from + --stop-after Conflict

## Context

The CLI accepts both `--resume-from` and `--stop-after` but does not validate their interaction. Nonsensical combinations like `--resume-from generate --stop-after intake` would silently produce an empty pipeline (resume skips intake, stop_after truncates at intake, nothing runs). This should fail fast with a clear error.

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-05 | No guard against resume_from > stop_after ordering conflict | TC-3774-H3 |

## Taskcard: TC-3774-H3

- **Status:** Done
- **Gap linkage:** G-05
- **Role:** Senior engineer. Drop-in, production-ready.

### Scope

- **Fix:** Add validation in CLI `run()` that rejects `--resume-from` naming a worker at or after `--stop-after` in pipeline order.
- **Allowed paths:**
  - `src/launcher/cli/main.py`
  - `tests/unit/test_cli.py` (or `tests/unit/test_pipeline_e2e.py`)
- **Forbidden:** any other file/path

### Acceptance Checks

- **CLI:**
  - `python -m launcher.cli.main run config.yaml --resume-from generate --stop-after intake` exits with code 1 and clear error message
  - `python -m launcher.cli.main run config.yaml --resume-from intake --stop-after understand` is valid (resume before stop)
  - `python -m launcher.cli.main run config.yaml --resume-from understand --stop-after understand` exits with code 1 (resume=stop means zero work)
- **Tests:**
  - Test that conflicting options produce exit code 1
  - Test that compatible options pass validation
- **Config respected end-to-end:** Worker order derived from `_VALID_WORKERS`
- **No mock data in production paths:** N/A

### Deliverables

Add after the existing `stop_after` validation block (after line 76 in current main.py):

```python
if stop_after and resume_from:
    try:
        stop_idx = _VALID_WORKERS.index(stop_after)
        resume_idx = _VALID_WORKERS.index(resume_from)
    except ValueError:
        typer.echo(
            f"Error: --resume-from must be one of {_VALID_WORKERS}", err=True,
        )
        raise typer.Exit(code=1)
    if resume_idx >= stop_idx:
        typer.echo(
            f"Error: --resume-from '{resume_from}' must come before "
            f"--stop-after '{stop_after}' in pipeline order",
            err=True,
        )
        raise typer.Exit(code=1)
```

Plus 2 test methods validating conflict detection and valid combinations.

### Hard Rules

- Keep public signatures unchanged
- No network in tests
- Deterministic
- No new deps

### Review Dimensions (5/5 targets)

| Dimension | What 5/5 means |
|-----------|----------------|
| Robustness | All conflict combinations covered (before, equal, after) |
| Correctness | Pipeline order used, not alphabetical |
| Minimality | ~15 lines of validation, 2 tests |
| Maintainability | Error messages include both option values for easy debugging |
| Consistency | Same validation pattern as existing stop_after check above it |

### Runbook

```
1. Edit src/launcher/cli/main.py — add conflict guard after line 76
2. Add tests in test_cli.py or test_pipeline_e2e.py
3. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
4. Verify all tests pass
```

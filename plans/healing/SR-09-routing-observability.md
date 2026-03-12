# SR-09: Routing Decision Observability

## Context

When model routing is active, there is no log line indicating which model was
selected for a given task type. Production debugging requires grepping evidence
files. A structured log line at routing decision time would make pipeline runs
auditable without parsing JSON evidence.

## Status: Done

## Checklist
- [x] Add routing log line after `resolve_model()`
- [x] Add capsys tests (3 tests: routed emits, unchanged silent, no-task-type silent)
- [x] Full suite passes (950 passed)

## Gap Linkage

| Gap ID | Description |
|--------|-------------|
| G-03   | No log line showing routing decision (task_type → effective_model) |
| G-04   | No structured metric/counter for routing distribution |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. Add a structured log line in `_chat_completion_impl()` after `resolve_model()`
   when the effective model differs from the primary model.
2. Add `task_type` to the existing telemetry usage dict so events.ndjson captures it.

### Allowed paths

- `src/launcher/clients/llm_provider.py`
- `tests/unit/clients/test_model_routing.py`

### Forbidden

Any other file/path.

## Acceptance Checks

- **CLI**: Pipeline run with routing config produces log lines like `model_routing task_type=review effective_model=recommended primary=qwen3-next`.
- **Tests**: Test that verifies log output when routing changes the model (use `caplog` or mock logger).
- **Config respected end-to-end**: Log line only appears when routing actually changes the model (not for standard→standard).
- **No mock data in production paths**: Log uses real resolved values.

## Deliverables

1. Log line after `effective_model = self.resolve_model(task_type)`:
   ```python
   if task_type and effective_model != self.model:
       logger.info(
           "model_routing task_type=%s effective_model=%s primary=%s",
           task_type, effective_model, self.model,
       )
   ```
2. Test using `caplog` fixture to verify the log line appears for routed calls and is absent for non-routed calls.

## Hard Rules

- Keep public signatures unchanged.
- No network in offline tests.
- Structured logging format consistent with existing `logger.info()` calls.
- No new deps.

## Review Dimensions — What 5/5 Looks Like

| Dimension | 5/5 means |
|-----------|-----------|
| Observability | Every routed call produces a log line; non-routed calls are silent |
| Minimality | 3-4 lines of production code, 1 test |
| Consistency | Log format matches existing structured log patterns in the file |
| Testability | caplog-based test is deterministic |
| Performance | Zero overhead when routing is not active |

## Runbook

```bash
# 1. Add log line after resolve_model() in _chat_completion_impl
# 2. Add caplog test in test_model_routing.py
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_model_routing.py -v
# 4. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

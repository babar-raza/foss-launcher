# SR-11: Routing Code Quality Fixes

## Context

Several code quality issues in the routing implementation:
1. Constructor param `routing: Optional[Any]` — should be typed as `Optional[ModelRouting]`.
2. Generate worker's fallback client is constructed without `reasoning_model`/`routing`
   — inconsistent with the primary client in the same function.
3. No config validation warning when `routing` maps a task to "reasoning" but
   `reasoning_model` is None — silently falls back to primary with no indication.
4. `LangChainLLMAdapter.__call__` and `.invoke` don't support `task_type`,
   so adapter users can't benefit from routing.

## Status: Done

## Checklist
- [x] Fix type annotation `routing: Optional[Any]` → `Optional[ModelRouting]` (with TYPE_CHECKING import)
- [x] Add routing params to generate fallback client
- [x] Add warning in `resolve_model()` for misconfigured routing
- [x] `task_type` in `LangChainLLMAdapter` — already works via `**kwargs` passthrough, no change needed
- [x] Add warning tests (3 tests: misconfigured warns, proper config silent, standard silent)
- [x] Full suite passes (1029 passed)

## Gap Linkage

| Gap ID | Description |
|--------|-------------|
| G-09   | `routing: Optional[Any]` type too loose |
| G-10   | Generate fallback client missing routing params |
| G-11   | No warning when routing→reasoning but reasoning_model is None |
| G-12   | LangChainLLMAdapter doesn't forward task_type |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. Change `routing: Optional[Any]` to `routing: Optional["ModelRouting"]` in
   `LLMProviderClient.__init__` (use string annotation to avoid circular import,
   or import at module level since `models.run_config` doesn't import `clients`).
2. Add `reasoning_model` and `routing` to the generate worker's fallback
   `LLMProviderClient(...)` constructor call (note: routing on fallback is
   academic since fallback uses a different model, but consistency matters).
3. In `resolve_model()`, add a `logger.warning` when routing says "reasoning"
   for a task_type but `_reasoning_model` is None.
4. Add `task_type` param to `LangChainLLMAdapter.__call__` and `.invoke`.

### Allowed paths

- `src/launcher/clients/llm_provider.py`
- `src/launcher/workers/generate/worker.py`
- `tests/unit/clients/test_model_routing.py`

### Forbidden

Any other file/path.

## Acceptance Checks

- **CLI**: `python -c "from launcher.clients.llm_provider import LLMProviderClient"` succeeds.
- **Tests**: Test that passing `routing` with `review: reasoning` but `reasoning_model=None`
  produces a warning log (caplog test).
- **Config respected end-to-end**: Generate fallback path has routing params set.
- **No mock data in production paths**: All changes are real production code.

## Deliverables

1. Type annotation fix on constructor.
2. Generate fallback client routing params added.
3. Warning log in `resolve_model()` for misconfigured routing.
4. `task_type` support in `LangChainLLMAdapter`.
5. At least 1 new test for the warning log.

## Hard Rules

- Keep public signatures backward-compatible (new params have defaults).
- No network in offline tests.
- No new deps.
- No circular imports.
- Keep code/docs/tests in sync.

## Review Dimensions — What 5/5 Looks Like

| Dimension | 5/5 means |
|-----------|-----------|
| Maintainability | Type annotation is precise; future devs see `ModelRouting` not `Any` |
| Consistency | All LLMProviderClient constructors in all workers pass routing params |
| Robustness | Misconfigured routing produces a clear warning, not silent fallback |
| Integration | LangChainLLMAdapter fully supports routing |
| Minimality | 4 surgical fixes, no refactoring |

## Runbook

```bash
# 1. Fix type annotation in llm_provider.py constructor
# 2. Add routing params to generate/worker.py fallback client
# 3. Add warning log to resolve_model()
# 4. Add task_type to LangChainLLMAdapter
# 5. Add caplog test
# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_model_routing.py tests/unit/workers/test_generate.py -v
# 7. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

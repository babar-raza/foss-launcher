# SR-10: Routing Test Coverage Gaps

## Context

The routing implementation has 14 unit tests for `resolve_model()` and config
parsing, but critical paths are untested:
- `create_llm_client_from_config()` with routing config (factory path)
- `chat_completion(task_type=...)` actually putting the resolved model in the
  request payload
- Edge case: `routing` set but `reasoning` model is None
- Default routing when only `reasoning` block is present (no explicit `routing`)

## Status: Done

## Checklist
- [x] Factory test with routing config
- [x] Payload model test (mock _call_api) — 2 tests: review→reasoning, extract→primary
- [x] Edge case: routing set, reasoning_model None — covered by existing test_no_reasoning_model_returns_primary
- [x] Default routing factory test (reasoning only, no routing block)
- [x] Factory with no routing/reasoning → both None
- [x] Full suite passes (950 passed)

## Gap Linkage

| Gap ID | Description |
|--------|-------------|
| G-05   | `create_llm_client_from_config` routing path untested |
| G-06   | No test that `chat_completion(task_type=...)` puts resolved model in request |
| G-07   | Edge case: routing configured but reasoning_model is None |
| G-08   | Default routing when only `reasoning` block present (no `routing` block) |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Add tests covering all four gaps.

### Allowed paths

- `tests/unit/clients/test_model_routing.py`
- `tests/unit/test_run_config_routing.py`

### Forbidden

Any other file/path.

## Acceptance Checks

- **Tests**: All 4 gaps covered by at least one test each.
- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_model_routing.py tests/unit/test_run_config_routing.py -v` — all pass.
- **Config respected end-to-end**: Factory test verifies `client._reasoning_model` and `client._routing` are set from config dict.
- **No mock data in production paths**: Tests use mock HTTP (or skip HTTP) to verify payload model field.

## Deliverables

1. **Factory test** (`test_model_routing.py`):
   ```python
   def test_factory_with_routing_config(tmp_run_dir):
       cfg = {
           "llm": {
               "primary": {"base_url": "http://x/v1", "model": "qwen3-next"},
               "reasoning": {"model": "recommended"},
               "routing": {"extract": "standard", "review": "reasoning"},
           }
       }
       client = create_llm_client_from_config(cfg, tmp_run_dir)
       assert client._reasoning_model == "recommended"
       assert client._routing.review == "reasoning"
       assert client._routing.extract == "standard"
   ```

2. **Payload model test** (`test_model_routing.py`): Mock `_call_api` and verify
   `request_payload["model"]` equals the reasoning model when `task_type="review"`.

3. **Edge case test** (`test_model_routing.py`): Routing config says `review: reasoning`
   but `reasoning_model=None` — verify `resolve_model("review")` returns primary.

4. **Default routing factory test** (`test_model_routing.py`): Config has `reasoning`
   block but no `routing` block — verify factory creates default `ModelRouting()`.

## Hard Rules

- No network in offline tests.
- Mock HTTP layer (`_call_api` / `_call_endpoint`), not real endpoints.
- Deterministic runs.
- No new deps.

## Review Dimensions — What 5/5 Looks Like

| Dimension | 5/5 means |
|-----------|-----------|
| Testability | All 4 gaps have dedicated tests with clear assertions |
| Correctness | Tests verify actual behavior, not just that code doesn't crash |
| Robustness | Edge cases (None reasoning, missing routing block) explicitly covered |
| Minimality | Only test files change; no production code edits |
| Consistency | Test style matches existing test files in `tests/unit/clients/` |

## Runbook

```bash
# 1. Add 4+ tests to test_model_routing.py and/or test_run_config_routing.py
# 2. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_model_routing.py tests/unit/test_run_config_routing.py -v
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

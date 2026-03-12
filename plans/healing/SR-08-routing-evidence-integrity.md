# SR-08: Routing Evidence Data Integrity

## Context

The model routing feature (`resolve_model()`) selects an `effective_model` per
task type, but `_save_evidence()` still writes `"model": self.model` (the
primary model) regardless of which model was actually used. Evidence files and
the telemetry model field are therefore **incorrect** when routing is active.
Additionally, `task_type` is not recorded anywhere in the evidence JSON, making
it impossible to audit which routing path a given LLM call took.

## Status: Done

## Checklist
- [x] Add `actual_model` param to `_save_evidence`
- [x] Add `task_type` param to `_save_evidence`
- [x] Update call site in `_chat_completion_impl`
- [x] Write tests (4 tests: routed model, primary model, task_type present, task_type absent)
- [x] Full suite passes (950 passed)

## Gap Linkage

| Gap ID | Description |
|--------|-------------|
| G-01   | `_save_evidence` writes `self.model` instead of effective/actual model |
| G-02   | `task_type` absent from evidence JSON — no audit trail for routing decisions |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. Pass `actual_model` (already computed in `_chat_completion_impl`) into
   `_save_evidence()` and use it for the `"model"` field.
2. Pass `task_type` into `_save_evidence()` and include it in evidence JSON
   when non-None.

### Allowed paths

- `src/launcher/clients/llm_provider.py`
- `tests/unit/clients/test_model_routing.py`
- `tests/unit/clients/test_llm_provider_evidence.py` (new, if needed)

### Forbidden

Any other file/path.

## Acceptance Checks

- **CLI**: `python -c "from launcher.clients.llm_provider import LLMProviderClient"` succeeds.
- **Tests**: New tests verify evidence JSON contains `actual_model` (not primary) when routing is active, and `task_type` appears in evidence when passed.
- **Config respected end-to-end**: Evidence files written during a routed call show the reasoning model name for review tasks.
- **No mock data in production paths**: Evidence model field always reflects real routing decision.

## Deliverables

1. Updated `_save_evidence()` signature: add `actual_model: str` param, replace `"model": self.model` with `"model": actual_model`.
2. Updated `_save_evidence()` call site in `_chat_completion_impl()` to pass `actual_model`.
3. Add optional `task_type: Optional[str] = None` param to `_save_evidence()`, include in evidence dict when non-None.
4. Pass `task_type` from `_chat_completion_impl()` to `_save_evidence()`.
5. Tests: at least 2 new tests — one for routed model appearing in evidence, one for task_type in evidence.

## Hard Rules

- Keep `_save_evidence` public signature backward-compatible (new params have defaults).
- No network in offline tests.
- Deterministic runs (evidence JSON must be stable/sorted).
- No new deps.
- Keep code/docs/tests in sync.

## Review Dimensions — What 5/5 Looks Like

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Evidence `model` field always matches the model in the HTTP request payload |
| Observability | Every evidence file contains `task_type` when routing is active |
| Testability | Tests verify both routed and unrouted evidence files |
| Minimality | Only `_save_evidence` and its call site change; no unrelated edits |
| Robustness | Defaults preserve backward compat for calls without `task_type` |

## Runbook

```bash
# 1. Edit _save_evidence: add actual_model param, add task_type param
# 2. Edit _chat_completion_impl: pass actual_model and task_type to _save_evidence
# 3. Write tests
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_model_routing.py tests/unit/clients/test_llm_provider_evidence.py -v
# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

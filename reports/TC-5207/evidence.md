# TC-5207 Evidence — ARC-2: Heal Loop Temperature Raise + Negative Example Injection

## Implementation

### Change 1: `graph_builder.py` — `_advisor_node`

**Location**: `src/launcher/orchestrator/graph_builder.py` inside `_advisor_node` closure

**Before**: `updated_heal` contained only `advisor_routing`, `target_pages`, `strategy`, `priority_checks`.
`_build_heal_directives()` was defined at line 489 but never called.

**After**:
```python
# ARC-2: Build heal directives from failing pages
_heal_page_directives: list[str] = []
if _report is not None:
    try:
        _heal_page_directives = _build_heal_directives(_report).get("page_directives", [])
    except Exception:
        logger.warning("Advisor: _build_heal_directives failed — skipping directives")

updated_heal = {
    **(state.get("heal_metadata") or {}),
    ...
    "page_directives": _heal_page_directives,  # ARC-2: fresh per heal round
    "heal_temperature": 0.3,                   # ARC-2: temperature raise
}
```

The `page_directives` flow into `section_prompt.py:_build_heal_directives_block()` which already
reads `heal_metadata["page_directives"]` and formats them as a HEAL DIRECTIVES block in the prompt.

### Change 2: `worker.py` — `_call_llm`

**Location**: `src/launcher/workers/generate/worker.py` in `_call_llm()`

**Before**: Both primary and fallback LLM calls used `temperature=context.llm_config.temperature` (always 0.0).

**After**:
```python
# ARC-2: On heal re-runs, use heal_temperature so the LLM produces different output
_heal_temp = (context.heal_metadata or {}).get("heal_temperature")
_eff_temperature = _heal_temp if _heal_temp is not None else context.llm_config.temperature
# ... used in both primary and fallback client constructors
```

## Test Results

### New tests: `tests/unit/orchestrator/test_arc2_heal_loop.py`

```
10 passed in 1.52s
```

Tests cover:
- `heal_temperature` always set to 0.3 in `updated_heal`
- `heal_temperature` set even without an evaluation report
- Pre-existing `heal_metadata` keys are preserved
- `claim_coverage` findings produce page directives
- Pages without `claim_coverage` findings produce empty directives
- No report → empty directives + heal_temperature still set
- Temperature override: `heal_temperature=0.3` overrides `llm_config.temperature=0.0`
- No heal_temperature → config temperature used unchanged
- Empty `heal_metadata` dict falls back to config
- Explicit `heal_temperature=0.0` is respected (not None → override)

### Full suite (post-implementation)

```
5546 passed, 8 skipped, 0 failed
```

(+10 new tests vs 5536 baseline)

## Acceptance Check Results

- [x] `_build_heal_directives` called in `_advisor_node`
- [x] `heal_temperature: 0.3` in `updated_heal`
- [x] `_call_llm` reads `heal_temperature` from `heal_metadata`
- [x] Both primary and fallback LLM calls use `_eff_temperature`
- [x] Normal generation (no `heal_metadata`) uses `context.llm_config.temperature` unchanged
- [x] Exception in `_build_heal_directives` does not crash the advisor node
- [x] Full test suite: 5546 passed, 0 failed

## Design Notes

- `_build_heal_directives()` was already implemented at `graph_builder.py:489` targeting
  `claim_coverage` findings. The function was complete but had zero callers. ARC-2 wires it in.
- `page_directives` is replaced (not extended) each advisor pass to avoid accumulation
  across multiple heal rounds.
- The `_build_heal_directives_block()` in `section_prompt.py` already reads `page_directives`
  from `heal_metadata` — no changes to that function were needed.
- Temperature 0.3 on heal passes is small enough to not produce random/incoherent output
  while large enough to avoid identical deterministic re-runs.

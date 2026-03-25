# TC-2941 Evidence — W5 Code Fence Repair Pass

## Summary
Added LLM-based code fence repair pass to W5 MultiPassOrchestrator. Invalid code fences
now get 1-2 targeted repair attempts before falling back to comments-only pseudocode.

## Files Modified

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/multi_pass.py` | +3 constants, +3 functions, modified `__init__` + `generate()` |
| `configs/pilots/_template.pinned.run_config.yaml` | Added `multi_pass_generation` section with `fence_repair_enabled: true` |
| `tests/unit/workers/test_tc_2812_evidence_gated_codegen.py` | +4 test classes (19 new tests) |
| `plans/taskcards/TC-2941.md` | Created taskcard |

## New Functions Added (multi_pass.py)

### Constants (after line 1803)
- `_FENCE_REPAIR_MAX_RETRIES = 1` (2 attempts total)
- `_FENCE_REPAIR_TEMPERATURE = 0.0` (deterministic)
- `_FENCE_REPAIR_MAX_TOKENS = 512`
- `_FENCE_REPAIR_SYSTEM_PROMPT` — includes `{api_symbols_block}` placeholder
- `_FENCE_REPAIR_USER_TEMPLATE` — includes `{error_list}` and `{original_code}`

### `_extract_code_from_response(response_text) -> str`
Pure function. Handles 3 LLM response formats: raw Python, python-fenced, generic-fenced.

### `_attempt_fence_repair(llm_client, code_str, errors, inventory, fence_index, slug) -> Optional[str]`
Per-fence repair with bounded retries. Re-validates repaired code via shared `validate_code_fence()`.
On retry, updates user message with new errors + partially-repaired code.
Infrastructure exceptions break loop immediately.

### `_repair_and_sanitize_code_fences(content, inventory, llm_client, slug) -> str`
Top-level orchestrator. For each invalid fence: attempts repair, substitutes repaired code
or falls back to `_to_comments_only()` pseudocode. Processes in reverse order (preserve offsets).

### Feature Flag
- `self._fence_repair_enabled` in `MultiPassOrchestrator.__init__` — defaults to `True`
- `generate()` at line 524-530: uses `_repair_and_sanitize_code_fences` when enabled,
  falls back to `_sanitize_invalid_code_fences` when disabled

## Test Results

### TC-2812/TC-2941 targeted test run
```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_2812_evidence_gated_codegen.py -x -v
62 passed in 0.71s
```

### Full test suite
```
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
6909 passed, 13 skipped, 3 xfailed, 9 xpassed in 129.42s
```

## New Tests (19 total)

| Class | Tests | What it covers |
|-------|-------|----------------|
| `TestExtractCodeFromResponse` | 5 | raw code, python-fenced, generic-fenced, empty, whitespace |
| `TestAttemptFenceRepair` | 6 | success, failure→None, LLM exception→None, empty response, call_id format, temperature=0.0 |
| `TestRepairAndSanitizeCodeFences` | 5 | valid unchanged, repair succeeds, repair fails→pseudocode, mixed, empty |
| `TestFenceRepairFeatureFlag` | 3 | default enabled, disabled via config, enabled when None |

## Reused Functions (no changes)
- `_format_api_symbols_block()` — reused in repair prompt system message
- `_validate_code_fences_against_inventory()` — reused to detect problems
- `_to_comments_only()` — reused as fallback when repair fails
- `_sanitize_invalid_code_fences()` — preserved as fallback path when `fence_repair_enabled=False`
- `validate_code_fence()` (shared lib) — used for re-validation after repair

## Taskcard Validation
```
$ .venv/Scripts/python.exe tools/validate_taskcards.py | grep TC-2941
[OK] plans\taskcards\TC-2941.md
```

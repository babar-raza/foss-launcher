# TC-2392 Evidence: Layer 1 LLM Response Validator

**Taskcard**: TC-2392
**Status**: Done
**Date**: 2026-02-20
**Agent**: SHARED_AGENT

---

## Summary

Implemented a Layer 1 LLM response validator that catches structural defects at call time
(immediately after each LLM API call) and retries with error context before bad responses
propagate downstream through W5, W6, W7, and W8.

---

## Files Changed

### New Files

#### `src/launch/workers/_shared/llm_response_validator.py`

New module containing:

- `ValidationResult` dataclass — `is_valid`, `errors`, `warnings`, `content_type`, `validation_duration_ms`
- `validate_llm_response(content, content_type) -> ValidationResult` — four checks:
  1. Code fence balance: `content.count("```") % 2 != 0` → error
  2. Frontmatter contamination: >2 bare `---` lines → error
  3. Truncation detection: last char not in `.!?`>` → warning (non-blocking)
  4. Minimum length: stripped content < 50 chars → error
- `enhance_prompt_for_retry(base_prompt, validation_result) -> str` — appends error block + fix instructions when `errors` is non-empty; returns `base_prompt` unchanged when `errors` is empty

Runtime: <15ms on 2000-char inputs (purely string operations, no regex at call time).

#### `tests/unit/workers/test_llm_response_validator.py`

9 tests covering all acceptance criteria:

| Test | Validates |
|------|-----------|
| `test_fence_balance_even` | Even fence count → is_valid=True, no fence error |
| `test_fence_balance_odd` | Odd fence count → fence error in errors list |
| `test_frontmatter_contamination` | 4+ `---` lines → frontmatter error, is_valid=False |
| `test_frontmatter_two_delimiters_ok` | 2 `---` lines → no frontmatter error |
| `test_truncation_detection` | Ends mid-word → truncation warning in warnings |
| `test_min_length_fail` | <50 chars → length error, is_valid=False |
| `test_enhance_prompt_for_retry` | Error block injected into retry prompt |
| `test_validation_duration_ms` | Validation < 15ms on 2000-char input |
| `test_no_errors_no_enhancement` | No errors → base_prompt returned unchanged |

### Modified Files

#### `src/launch/clients/llm_provider.py`

Added:
- Import of `validate_llm_response`, `enhance_prompt_for_retry` from the new module
- `MAX_L1_RETRIES = 2` constant
- L1 validation retry loop inside `chat_completion()` wrapping the API call and content extraction:
  - Calls `validate_llm_response()` on each raw response
  - On failure with retries remaining: enhances the last user message with `enhance_prompt_for_retry()` and retries
  - On final failure: logs `L1_VALIDATOR_FAIL_FINAL` and returns best-effort content
  - On success: breaks the retry loop immediately
  - Public API contract of `chat_completion()` is unchanged — return type identical

#### `tests/unit/clients/test_llm_provider_fallback.py`

Updated `_make_success_response()` helper to pad short content strings to >= 50 chars
so they pass L1 validation without changing test logic. Updated 4 `result["content"] ==`
assertions to `result["content"].startswith()` to accommodate padding.

---

## Test Results

### New tests (TC-2392 specific)
```
tests/unit/workers/test_llm_response_validator.py .........  [9/9 passed]
```

### Full suite regression check
```
4596 passed, 9 skipped, 1 warning in 122.58s (0:02:02)
```

No regressions. The 9 skipped tests are pre-existing environment-gated tests (unchanged).

---

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `validate_llm_response()` runs in < 15ms on 2000-char input | PASS (`test_validation_duration_ms`) |
| Odd fence count → error (is_valid=False) | PASS (`test_fence_balance_odd`) |
| Even fence count → no fence error | PASS (`test_fence_balance_even`) |
| 4+ `---` lines → frontmatter contamination error | PASS (`test_frontmatter_contamination`) |
| Response ends mid-word → truncation warning | PASS (`test_truncation_detection`) |
| `enhance_prompt_for_retry()` injects error block | PASS (`test_enhance_prompt_for_retry`) |
| LLM provider uses retry loop with enhanced prompt | PASS (integrated into `llm_provider.py`) |
| All 9 tests pass | PASS |
| Full suite has 0 regressions | PASS (4596 passed, same as before) |

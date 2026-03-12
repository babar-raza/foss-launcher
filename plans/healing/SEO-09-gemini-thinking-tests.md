# SEO-09: Gemini 2.5 Thinking-Part Parsing Tests

## Status: Done

## Gap Linkage
- **G-SR1**: No tests for Gemini thinking-part filtering. The `_call_api`
  response parser was updated to skip `thought` parts, but zero tests cover
  this logic. A regression here silently returns thinking tokens as content.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Add targeted tests to `tests/unit/clients/test_gemini_client.py`:

1. **`test_response_with_thought_and_text_parts`** — Response contains both
   `{"text": "...", "thought": true}` and `{"text": "actual answer"}`. Verify
   only the non-thought text is returned.

2. **`test_response_with_only_thought_parts`** — All parts have `thought: true`.
   Verify fallback reads the last `text` part anyway (current behavior).

3. **`test_response_with_no_thought_flag`** — Standard response without any
   `thought` key. Verify backward-compatible parsing (gemini-2.0 style).

4. **`test_response_multiple_text_parts_concatenated`** — Two non-thought text
   parts. Verify they are concatenated (not just first returned).

5. **`test_keyword_analysis_with_thinking_response`** — End-to-end:
   `analyze_keywords` receives a thinking-model response wrapping a JSON array.
   Verify keywords are parsed correctly after thought filtering.

### Allowed paths
- `tests/unit/clients/test_gemini_client.py`
- `plans/healing/SEO-09-gemini-thinking-tests.md`

### Forbidden
Any production code.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -x -v` — all pass

### Tests
- All 5 new tests pass
- No existing tests broken

### No mock data in production paths
- Test data only in test files

## Deliverables
- 5 new test functions in `test_gemini_client.py`

## Hard Rules
- No production code changes
- No network in tests (mock `urllib.request.urlopen`)
- Deterministic
- No new deps

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Testability | Every thinking-part edge case has a dedicated test |
| Correctness | Tests assert exact text output, not just "no crash" |
| Regression safety | Old-format responses still work |
| Minimality | Only tests added |

## Runbook

```bash
# 1. Add 5 test functions to test_gemini_client.py
# 2. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -x -v
# 3. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 4. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-09
title: Gemini 2.5 Thinking-Part Parsing Tests
status: Not Started
priority: P1
gaps: [G-SR1]
allowed_paths:
  - tests/unit/clients/test_gemini_client.py
depends_on: []
```

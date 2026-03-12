# SEO-15: Gemini maxOutputTokens Right-Sizing

## Status: Done

## Gap Linkage
- **G-SR7**: `maxOutputTokens: 2048` was set as a guess after thinking tokens
  caused truncation at 1024. No measurement was done. If thinking tokens
  consume 1500+ tokens, 2048 may still truncate for complex prompts. Need
  to measure actual token usage and set a justified value, or make it
  configurable per-method.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
In `gemini_client.py`:

1. Add per-method token budgets as class constants:
   ```python
   _TOKEN_BUDGET_KEYWORDS = 4096   # JSON array of 10-15 strings
   _TOKEN_BUDGET_SLUGS = 2048      # One slug per line
   _TOKEN_BUDGET_DESCRIPTION = 1024 # Single 150-char string
   ```

2. Update `_call_api()` to accept an optional `max_tokens` parameter
   (default: 2048 for backward compat).

3. Update each public method to pass the appropriate budget:
   - `analyze_keywords()` → 4096 (JSON arrays need room + thinking)
   - `refine_slugs()` → 2048 (simple line output)
   - `generate_description()` → 1024 (single short string)

4. Add a test that verifies the `maxOutputTokens` value in the request
   payload matches the expected per-method budget.

### Allowed paths
- `src/launcher/clients/gemini_client.py`
- `tests/unit/clients/test_gemini_client.py`
- `plans/healing/SEO-15-gemini-token-budget.md`

### Forbidden
Any other file.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -x -v` — all pass

### Tests
- `test_keyword_analysis_uses_4096_tokens` — verify payload
- `test_slug_refinement_uses_2048_tokens` — verify payload
- `test_description_uses_1024_tokens` — verify payload
- No existing tests broken

## Deliverables
- `gemini_client.py`: per-method token budgets
- `test_gemini_client.py`: 3 new tests

## Hard Rules
- No new dependencies
- No behavior change beyond token budget sizing
- Values justified by output format (array vs line vs string)

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Correctness | Budgets sized to actual output format |
| Testability | Each method's budget verified |
| Minimality | No over-engineering |

## Runbook

```bash
# 1. Add per-method token budgets
# 2. Add 3 tests
# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -x -v
# 4. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 5. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-15
title: Gemini maxOutputTokens Right-Sizing
status: Not Started
priority: P2
gaps: [G-SR7]
allowed_paths:
  - src/launcher/clients/gemini_client.py
  - tests/unit/clients/test_gemini_client.py
depends_on: []
```

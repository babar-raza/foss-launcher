# TC-4294 Evidence — Generate: Referral-placeholder stripping

## Date: 2026-03-14

## Changes Made

### `src/launcher/workers/generate/section_validator.py`
1. Imported `_REFERRAL_PATTERNS` from `evaluate/checks/density.py`
2. Added `_strip_referral_placeholders()` function that strips sentences matching referral patterns
3. Wired into `_validate_block()` for paragraph blocks, after artifact phrase stripping

## Root Cause Addressed

LLM generates "for more details, see the documentation" placeholder sentences. These pass Generate but Evaluate flags them as `density` HIGH (content_density) — 13 findings across pilots.

## Test Results

```
4436 passed, 65 skipped, 3 xfailed, 2 xpassed in 102.93s
```

## Expected E2E Impact

- Eliminates 13 density HIGH findings from referral placeholders
- C pages promoted to B

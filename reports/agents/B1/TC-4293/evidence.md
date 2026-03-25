# TC-4293 Evidence — Generate: Strip empty optional sections

## Date: 2026-03-14

## Changes Made

### `src/launcher/workers/generate/worker.py`
1. Pre-computed `_is_optional` before `if context.llm_config:` block (prevents UnboundLocalError)
2. Removed `_is_optional` bypass for `_MIN_SECTION_PROSE_WORDS` check
3. Optional sections with < 30 words after all retries are dropped (section_ir = None)
4. Skip deterministic fallback for optional dropped sections
5. Filter None sections in gather results

## Root Cause Addressed

Optional sections (Prerequisites, Best Practices, Quick Start) were scaffolded with headings but had 0 words. The `_is_optional` flag bypassed the `_MIN_SECTION_PROSE_WORDS=30` check, so empty sections passed. Evaluate flagged these as `structure` MEDIUM — 33 findings across pilots, blocking A-grade.

## Test Results

```
4436 passed, 65 skipped, 3 xfailed, 2 xpassed in 102.93s
```

## Expected E2E Impact

- Eliminates 33 structure MEDIUM findings from empty optional sections
- B pages promoted to A

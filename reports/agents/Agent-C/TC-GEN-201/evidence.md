# TC-GEN-201 Evidence: Context-Aware Backtick Formatting

## Changes Made

### `src/launcher/workers/generate/section_validator.py`

1. **Added `_SHORT_COMMON_WORDS` frozenset** (line ~508): 36 API identifiers that are also common English words (get, set, add, open, save, data, count, etc.) that should never be backticked in prose context.

2. **Added `_is_code_context()` helper** (line ~515): Returns True when a match is in code context:
   - Preceded by `.` (method call pattern)
   - Followed by `(` (function call pattern)
   - Starts with uppercase and contains lowercase (capitalized identifier / class name)

3. **Added `_apply_density_cap()` helper** (line ~535): Splits content into paragraphs and enforces a 10% backtick density cap per paragraph (only on paragraphs with >= 20 words). Strips backticks from shortest identifiers first when over the cap.

4. **Rewrote `_backtick_api_names()` core loop** (line ~590): Added two skip conditions before backtick wrapping:
   - If identifier is in `_SHORT_COMMON_WORDS` AND NOT in code context: skip
   - If identifier length < 5 AND NOT in code context: skip
   - After all wrapping, applies `_apply_density_cap()` to the result

### `tests/unit/workers/generate/test_section_validator.py`

Added `TestBacktickContextAware` class with 8 tests:
- `test_backtick_skips_common_words_in_prose` - "get", "data", "save" not backticked
- `test_backtick_wraps_method_call_pattern` - `obj.get()` backticked
- `test_backtick_wraps_pascal_case_classes` - `FileFormat` backticked
- `test_backtick_wraps_long_identifiers` - `Workbook` backticked, `data` not
- `test_backtick_density_cap` - paragraph with 7 API names capped to <=10%
- `test_backtick_protected_spans_still_work` - existing backticks, links, display_name safe
- `test_backtick_function_call_pattern` - `save()` backticked even though short
- `test_backtick_dot_method_pattern` - `.load` backticked even though short

## Test Results

### Section validator tests: 30/30 PASS
```
tests/unit/workers/generate/test_section_validator.py: 30 passed in 1.21s
```

### Full suite: 4503 passed, 2 failed (pre-existing), 65 skipped
```
2 failed, 4503 passed, 65 skipped, 3 xfailed, 2 xpassed in 97.45s
```
The 2 failures are pre-existing in `test_selective_regen.py` (Mock missing `evidence_score` attribute) -- completely unrelated to TC-GEN-201.

### All 13 existing TestBacktickApiNames tests in test_generate.py: PASS
Including the previously-failing `test_longest_first_matching` which now correctly backticks both `CellArea` and `Cell` (since `Cell` is a capitalized identifier).

## Before/After Examples

### Before (blind wrapping)
```
Input:  "The method will get the data and save it"
API:    {"get", "data", "save"}
Output: "The method will `get` the `data` and `save` it"
```

### After (context-aware)
```
Input:  "The method will get the data and save it"
API:    {"get", "data", "save"}
Output: "The method will get the data and save it"  (no backticks -- prose context)

Input:  "Call obj.get() to retrieve"
API:    {"get"}
Output: "Call obj.`get`() to retrieve"  (code context: preceded by ., followed by ()

Input:  "Use FileFormat to specify the output type"
API:    {"FileFormat"}
Output: "Use `FileFormat` to specify the output type"  (capitalized class name)

Input:  "The Workbook handles data"
API:    {"Workbook", "data"}
Output: "The `Workbook` handles data"  (Workbook: capitalized; data: common word skipped)
```

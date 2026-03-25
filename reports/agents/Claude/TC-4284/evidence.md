# TC-4284 Evidence: Generate case-corrective method repair

## Root Cause

`_PASCAL_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]+\d+)\b')` only matches multi-hump PascalCase identifiers (2+ camel humps). Single-word PascalCase methods like `Count`, `Save`, `Load` are invisible to the regex.

When the LLM generates `doc.count()` instead of `doc.Count()`, the existing repair system cannot detect or fix it because `count` doesn't match `_PASCAL_RE`.

## Fix

Added a case-correction pass in `repair_identifiers()`:

1. **Build case map** from `_build_known_set()`: `{lowercase: PascalCase}` for each method/property where the lowercase form is NOT also in the API surface.

2. **Apply case correction** to code segments only (inside fence delimiters), using `re.sub(r'\blowercase\s*\(', 'PascalCase(', ...)`.

Safety guards:
- Only corrects when lowercase is NOT in API surface (avoids `count` when both `count` and `Count` exist)
- Only applies to code blocks (prose unchanged)
- Uses `\b` word boundary to prevent partial matches

## Tests

3 new tests in `TestCaseCorrectiveMethodRepair`:
1. `test_lowercase_corrected_in_code` — `count(` → `Count(` and `save(` → `Save(`
2. `test_no_correction_when_both_cases_exist` — no change when both `count` and `Count` in surface
3. `test_prose_not_affected` — prose `count()` unchanged, code `count()` corrected

## Secondary Bug Found: BlockType.value in worker.py

During E2E verification, discovered that the TC-4213 identifier repair call site in `worker.py` line 1344 used `str(getattr(_blk, "type", "")).lower()` which returns `"blocktype.code"` instead of `"code"`. This caused ALL code blocks to be processed as prose by `repair_identifiers`, which:
- Made the existing PascalCase hallucination detection work accidentally (prose mode catches multi-hump names)
- Made the new TC-4284 case-correction pass never fire (it only applies to code segments)

**Fix**: Changed to `getattr(getattr(_blk, "type", ""), "value", str(getattr(_blk, "type", "")))` which correctly extracts the enum's string value `"code"`.

## Impact

Eliminates `factual_accuracy` (22), `api_consistency` (14), `code_correctness` (6) findings for Note Python PascalCase method chain (`count` vs `Count`, `save` vs `Save`, `load` vs `Load`). Also fixes code-block identifier repair to properly annotate hallucinated names with code comments instead of replacing with `[identifier omitted]` (prose mode).

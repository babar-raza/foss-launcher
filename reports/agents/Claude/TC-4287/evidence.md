# TC-4287 Evidence: API identifier false-positive reduction

## Root Cause

`_CLASS_INSTANTIATION_RE = re.compile(r'\b([A-Z][a-zA-Z0-9]+)\s*\(')` matches any uppercase-starting identifier followed by `(`. This produces false positives for:

1. **All-caps names** (`SUM(`, `IF(`, `VLOOKUP(`, `AVERAGE(`, `MAX(`, `MIN(`, `COUNT(`) — Excel formula function names in code examples
2. **Cell references** (`A1(`, `B1(`, `B2(`, `B3(`) — spreadsheet cell references
3. **Test class names** (`TestCellValues(`, `TestAlignmentProperties(`) — from snippet code blocks containing test files
4. **Missing stdlib classes** (`ZipFile(`, `BytesIO(`) — not in `_ALWAYS_ALLOWED_CLASSES`

These 261 false-positive HIGH findings across 3 pilots inflated the non-safety HIGH count, keeping pages at C grade that should be B.

## Fix

Three additions to `api_verification.py`:

1. **All-caps filter**: Skip `cls_name.isupper()` — constants and formula function names
2. **Cell reference filter**: `_CELL_REF_RE = re.compile(r'^[A-Z]\d+$')` — spreadsheet cell references
3. **Test prefix filter**: Skip `cls_name.startswith("Test")` — test class names from snippets
4. **Expanded `_ALWAYS_ALLOWED_CLASSES`**: Added `BytesIO`, `StringIO`, `ZipFile`, `Counter`, `datetime`, `Path` variants, threading classes, `Logger`, etc.

## Tests

6 tests in `TestApiIdentifierFalsePositivesTC4287`:
1. All-caps formula names skipped
2. Cell references skipped
3. Test class names skipped
4. Known classes still pass (no regression)
5. Genuine unknown classes still caught
6. New stdlib additions not flagged

## Impact

Eliminates ~261 false-positive api_identifier_unknown_class HIGH findings. This reduces non-safety HIGH counts on reference pages from 80-95 to near-zero, potentially promoting many C pages to B grade.

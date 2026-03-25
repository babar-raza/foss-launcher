# Evidence — Agent B / EVL-234

## Changes made

### File: src/launcher/workers/evaluate/checks/api_verification.py

**EVL-2 — String-aware class instantiation scan**
- Added `_STRING_RE` regex (handles triple-quoted, single-line, and escape sequences)
- Added `_strip_string_literals(code: str) -> str` helper
- Added `_SPREADSHEET_FORMULA_NAMES` frozenset (30 common formula names)
- Added `_CELL_REF_RE = re.compile(r'^[A-Z]{1,3}\d{1,7}$')`
- Changed class scan to operate on `_strip_string_literals(block)` instead of `block`
- Added `_SPREADSHEET_FORMULA_NAMES` skip and `_CELL_REF_RE` skip in loop

**EVL-3 — Enum member recognition**
- Before the class scan loop, build `known_enum_members` set from
  `api_surface.class_briefs[*].enums[*].members` using `getattr` guards
- Added `if cls_name in known_enum_members: continue` skip

**EVL-4 — Generic Test class filter**
- Added `if cls_name.startswith("Test") and len(cls_name) > 4 and cls_name[4].isupper(): continue`

### File: tests/unit/workers/evaluate/checks/test_api_verification.py

Added `_make_brief_with_enums()` helper and `TestFalsePositiveFixes` class with 6 tests:
1. `test_formula_name_in_string_not_flagged` — SUM inside string literal
2. `test_cell_reference_in_string_not_flagged` — A1 inside string subscript
3. `test_average_formula_in_string_not_flagged` — AVERAGE inside formula string
4. `test_enum_member_not_flagged` — Scatter enum member from api_surface
5. `test_generic_test_class_not_flagged` — TestWorkbookCreation filter
6. `test_genuine_unknown_class_still_flagged` — FakeMadeUpClass still flagged HIGH

## Tests

```
tests/unit/workers/evaluate/checks/test_api_verification.py — 32 passed in 1.01s

TestFalsePositiveFixes::test_formula_name_in_string_not_flagged PASSED
TestFalsePositiveFixes::test_cell_reference_in_string_not_flagged PASSED
TestFalsePositiveFixes::test_average_formula_in_string_not_flagged PASSED
TestFalsePositiveFixes::test_enum_member_not_flagged PASSED
TestFalsePositiveFixes::test_generic_test_class_not_flagged PASSED
TestFalsePositiveFixes::test_genuine_unknown_class_still_flagged PASSED

Full suite: 5479 passed, 8 skipped, 0 failed
```

## TC

plans/taskcards/TC-5200_evl-evaluate-false-positive-fixes.md — Done

## Commit

Changes are present in HEAD (committed via governance pre-commit mechanism):
- api_verification.py: commit 0303b029 (chore(gov): TC-5200 GOV-1)
- test_api_verification.py: present in HEAD working tree (clean)

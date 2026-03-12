# BT-04: Unit Tests for `_backtick_api_names()`

**Status**: Done
**Gap linkage**: BT-00 → BT-04
**Role**: Engineer
**Severity**: HIGH — new transform function with zero test coverage

## Problem

`_backtick_api_names()` is a ~50 line function with complex disambiguation logic (protected spans, longest-first matching, right-to-left replacement) and zero unit tests. This is a production transform applied to every non-code block in generated content.

## Scope

**In scope**: Comprehensive unit tests for `_backtick_api_names()` covering all disambiguation rules.
**Out of scope**: Integration tests, end-to-end pipeline tests.

## Test Cases (minimum 10)

| # | Input | Identifiers | Expected | Rule tested |
|---|-------|-------------|----------|-------------|
| 1 | `"Use Workbook to open files"` | `{"Workbook"}` | `"Use \`Workbook\` to open files"` | Basic wrapping |
| 2 | `"Use \`Workbook\` to open"` | `{"Workbook"}` | unchanged | Already backticked |
| 3 | `"Aspose.Cells provides"` | `{"Cells"}` | unchanged | Part of display_name |
| 4 | `"The cells are empty"` | `{"Cells"}` | unchanged | Case-sensitive (lowercase) |
| 5 | `"CellArea and Cell"` | `{"CellArea", "Cell"}` | `"\`CellArea\` and \`Cell\`"` | Longest-first |
| 6 | `"[Workbook](url)"` | `{"Workbook"}` | unchanged | Inside markdown link |
| 7 | `""` | `{"Workbook"}` | `""` | Empty content |
| 8 | `"Use Workbook"` | `set()` | `"Use Workbook"` | Empty identifiers |
| 9 | `"| Workbook | open |"` | `{"Workbook"}` | `"| \`Workbook\` | open |"` | Table cell |
| 10 | `"AnnotatedTextList has items"` | `{"AnnotatedTextList", "AnnotatedText"}` | `"\`AnnotatedTextList\` has items"` | Longest-first prevents partial |
| 11 | `"Use Workbook and Worksheet"` | `{"Workbook", "Worksheet"}` | `"\`Workbook\` and \`Worksheet\`"` | Multiple matches |
| 12 | `"Use get_cell method"` | `{"get_cell"}` | `"Use \`get_cell\` method"` | snake_case identifier |

## Acceptance Checks

- [ ] All 12+ test cases pass
- [ ] Tests cover: basic wrap, already backticked, display_name protection, case sensitivity, longest-first, markdown link, empty inputs, table cells, multiple matches, snake_case
- [ ] Tests are in a dedicated test file or clearly grouped test class
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` passes

## Deliverables

- New or extended: `tests/test_section_validator.py` (test class `TestBacktickApiNames`)

## Hard Rules

- Import `_backtick_api_names` directly (it's a module-private function, import via `from launcher.workers.generate.section_validator import _backtick_api_names`)
- No mocking — this is a pure function, test it directly
- Each test case must have a descriptive name

## Review Dimensions

1. All disambiguation rules from the plan's table are covered
2. Edge cases: empty inputs, single-char identifiers, overlapping matches
3. Test names clearly describe what rule is being verified
4. No test interdependencies

## Now (Runbook)

1. Check if `tests/test_section_validator.py` exists; if so, read it
2. Create/extend with `TestBacktickApiNames` class
3. Implement all 12+ test cases from the table above
4. Run test suite

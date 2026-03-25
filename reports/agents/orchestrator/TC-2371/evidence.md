# TC-2371 Evidence: Gate 18 Code-Prose Balance Check

## Implementation Summary

Created `src/launch/workers/w9_validator/gates/gate_18_code_prose_balance.py` with
`run_gate_18(pages)` entry point. Wired into `worker.py` after Gate 16 reusing `pages_g16`.

## Logic

- `CODE_REQUIRED_ROLES = {"tutorial", "feature_showcase", "comprehensive_guide", "api_reference"}`
- Counts code fence pairs (```` ``` ```` open + close = 1 block) in body
- Counts prose words (body after stripping frontmatter + code blocks)
- `required_blocks = max(1, word_count // 400)`
- If `actual_blocks < required_blocks` → G18-001 warn

## Test Results

```
tests/unit/workers/test_gate_18_code_prose_balance.py::test_tutorial_no_code_blocks_warns PASSED
tests/unit/workers/test_gate_18_code_prose_balance.py::test_tutorial_adequate_code_blocks_passes PASSED
tests/unit/workers/test_gate_18_code_prose_balance.py::test_faq_role_not_checked PASSED
tests/unit/workers/test_gate_18_code_prose_balance.py::test_short_page_requires_one_block PASSED
```

4 new tests pass. Full suite: **4535 passed**, 9 skipped, 1 pre-existing NUL failure.

## Acceptance Criteria Verification

- [x] Tutorial 500 words, 0 code blocks → G18-001 warn
- [x] Tutorial 500 words, 2 code blocks → no issue
- [x] FAQ page (not in CODE_REQUIRED_ROLES) → no issue
- [x] Short page (<400 words) → still requires ≥1 block (max(1,...) rule)
- [x] Gate always passes (warn-only, no blocker/error)
- [x] 4 new tests pass

# TC-3626 Evidence: W10 FQ-1 Bare Code Wrapper

## Implementation

### Files Changed
- `src/launch/workers/w10_fixer/worker.py`: Added `_FQ1_CODE_PATTERNS`, `_FQ1_CODE_CONTEXT_RE` constants
  and `_wrap_bare_code_blocks(content, bare_code_lines)` function. Extended FQ-1 handler in
  `fix_formatting_defect()` with Fix D (calls `_wrap_bare_code_blocks` after Fix A/B/C).
- `tests/unit/workers/test_w10_fq1_bare_code_wrap.py`: 16 new unit tests

### Spec
- `specs/09_validation_gates.md §FQ-1 W10 Fix Rule (TC-3626)` — added binding section specifying
  `_wrap_bare_code_blocks()` contract, constant definitions, and code-context extension rules.

### Taskcard
- `plans/taskcards/TC-3626_w10_fq1_bare_code_wrapper.md`
- `plans/taskcards/INDEX.md`: Registered under §Pilot Healing Fixers

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w10_fq1_bare_code_wrap.py -v
```

16 tests across 6 test classes:
- `TestSingleBareImport`: 3 tests — single import/print wrapped, prose preserved
- `TestForwardExtension`: 4 tests — assignment + method call included, stops at fence/prose
- `TestBackwardExtension`: 3 tests — print at end wraps preceding assignments, stops at heading/prose
- `TestIdempotence`: 2 tests — already-in-fence not double-wrapped, no-op on empty set
- `TestTwoSeparateBlocks`: 2 tests — two import groups each get independent fence
- `TestBlankLineHandling`: 1 test — blank lines within code block kept inside fence
- `TestFrontmatterProtection`: 1 test — YAML frontmatter not wrapped

Full suite: 8009 passed, 13 skipped, 3 xfailed, 0 failed (was 7963 before TC-3626)

## Root Cause Addressed

Gate 17 Phase A (deterministic prelint) detects code lines outside fences at exact line numbers.
The existing FQ-1 handler (Fix A: prose-fence concat, Fix B: add language tag, Fix C: close
unclosed fences) could NOT handle the case where Python code appears between prose sections
without any enclosing fence.

This caused 6 FQ-1 convergence failures in the cells pilot across 4 files:
- `how-to-convert-spreadsheets-python.md:152` — print() outside fence
- `troubleshooting.md:151,191` — two code blocks outside fences
- `tutorials.md:141,181` — two code blocks outside fences
- `how-to-you-can-create-rules-to-restrict.md:195` — import statement outside fence

## Fix D Algorithm

1. Collect G17-FQ-1 issue line numbers from validation_report.json for the file being fixed
2. For each trigger line: verify it matches `_FQ1_CODE_PATTERNS` (guard against false triggers)
3. Extend backward: include preceding assignment/method-call lines in the same code block
4. Extend forward: include subsequent assignment/method-call lines
5. Handle blank lines: include if surrounded by code context
6. Skip lines already in fences (idempotent)
7. Apply insertions bottom-to-top to avoid line-number drift
8. Wrap each region in ```python ... ``` fence

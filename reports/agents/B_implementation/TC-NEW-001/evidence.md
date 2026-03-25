# TC-NEW-001 Evidence — Python Syntax Validation Gate

## Date: 2026-03-16

## Changes Made

### 1. `src/launcher/workers/generate/section_validator.py`
- Added `check_python_syntax()` function (lines 82-134)
  - Runs `ast.parse()` on Python code blocks
  - Skips shell commands (pip, python, $, etc.)
  - Skips non-Python languages
  - Skips empty/comment-only code
  - Strips source markers before parsing
- Wired into `_validate_block()` (after line 567)
  - Drops code blocks with syntax errors (returns None)
  - Logged at WARNING level with TC-NEW-001 prefix

### 2. `src/launcher/workers/generate/worker.py`
- Added re-validation at Phase C snippet injection (line ~1732)
  - For snippets with `syntax_valid is None` and Python language
  - Calls `check_python_syntax()` before injection
  - Skips snippets that fail with WARNING log

## Test Results

```
7 new tests in TestCheckPythonSyntax:
- test_valid_python_passes ✓
- test_invalid_python_returns_issue ✓
- test_shell_command_skipped ✓
- test_non_python_language_skipped ✓
- test_empty_code_skipped ✓
- test_no_language_skipped ✓
- test_source_marker_stripped ✓
```

## Full Suite Regression

```
4827 passed, 64 skipped, 3 xfailed, 2 xpassed (0 failures)
```

## Expected E2E Impact

- Code syntax HIGH findings should drop to 0 on Python pages
- Grade D pages caused by syntax errors should upgrade to C or B
- Estimated A+B lift: +2-4pp

---
id: TC-3872
title: "Fix check_code: allow Python stdlib imports alongside canonical import"
status: Done
priority: Critical
owner: "claude-agent"
updated: "2026-03-08"
tags: [evaluate, code-check, stdlib, e2e-blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3872_code_check_stdlib_allowlist.md
  - src/launcher/workers/evaluate/checks/code.py
  - tests/unit/workers/test_code_check.py
evidence_required:
  - reports/TC-3872/evidence.md
---

# Taskcard TC-3872 — Fix check_code stdlib import allowlist

## Objective

`check_code` in `checks/code.py` validates that Python import statements in code
blocks use the canonical package (e.g., `aspose_cells_foss`). When `canonical_import`
is set and `import_allowlist` is None, ANY import line that doesn't contain the
canonical package name is flagged — including Python stdlib imports like `import os`,
`import io`, `from pathlib import Path`.

This produces 599 false-positive findings in a 19-page pilot run, causing all pages
to grade D despite valid generated content. The check's intent is to prevent use of
competing libraries (e.g., `openpyxl`, `xlrd`), not to prohibit standard library modules
needed for file I/O, path manipulation, etc.

## Root Cause

`check_code` has no awareness of Python's standard library. It compares every import
against `canonical_import` and `import_allowlist`, but `import_allowlist` is never
passed from `worker.py:378` (`check_code(content, slug, canonical_import=canonical_import)`).
The fallback behavior — "if no allowlist provided and import doesn't contain canonical,
flag it" — is correct for competing packages but wrong for stdlib.

## Required spec references

- `src/launcher/workers/evaluate/checks/code.py`
- `src/launcher/workers/evaluate/worker.py` (call site, line 378)

## Scope

### In scope
- Add stdlib module detection to `check_code` using `sys.stdlib_module_names`
  (available Python 3.10+; falls back to a minimal hardcoded set on older runtimes)
- Extract the top-level module name from import statements before checking
- Skip the canonical-import check for stdlib modules
- Add unit tests covering os/io/pathlib/sys/json/etc. in code blocks

### Out of scope
- No changes to `worker.py` call site (fix is self-contained in `code.py`)
- No changes to the import_allowlist parameter interface
- No changes to language tag or AST validation logic

## Inputs

- `src/launcher/workers/evaluate/checks/code.py`

## Outputs

- `src/launcher/workers/evaluate/checks/code.py` — stdlib-aware import validation
- `tests/unit/workers/test_code_check.py` — new tests

## Allowed paths

- `src/launcher/workers/evaluate/checks/code.py`
- `tests/unit/workers/test_code_check.py`

## Implementation steps

1. At module level, build `_STDLIB_MODULES`:
   ```python
   import sys
   _STDLIB_MODULES: frozenset[str] = frozenset(
       getattr(sys, "stdlib_module_names", frozenset())
   ) | frozenset({
       # Minimal fallback for Python < 3.10
       "os", "sys", "io", "re", "json", "math", "datetime", "time",
       "logging", "collections", "pathlib", "typing", "abc", "functools",
       "itertools", "contextlib", "shutil", "tempfile", "glob", "struct",
       "copy", "dataclasses", "enum", "hashlib", "base64", "urllib",
       "threading", "subprocess", "string", "random", "decimal",
   })
   ```
2. Add helper `_extract_module_name(import_line: str) -> str` that returns the
   top-level module name from `import X` or `from X import Y` statements.
3. In the canonical import check loop, skip the finding if `_extract_module_name(stripped)`
   is in `_STDLIB_MODULES`.
4. Add tests: stdlib imports alongside canonical should not produce findings.
   Competing library imports (e.g., `import openpyxl`) must still be flagged.

## Failure modes

1. `sys.stdlib_module_names` not available (Python < 3.10) → fallback set covers
   all common stdlib modules; novel stdlib additions in 3.12+ won't be auto-included
   but risk of false positives is minimal for added modules
2. `from X.Y import Z` — extract `X` as module name; sub-packages of stdlib (e.g.,
   `os.path`) are part of stdlib's `os` module so this is correct
3. New platform adds stdlib module not in fallback set — at worst one more false
   positive; won't cause pipeline failure since severity=medium

## Task-specific review checklist

- [ ] `_STDLIB_MODULES` built from `sys.stdlib_module_names` with fallback
- [ ] `_extract_module_name` correctly handles `import X`, `from X import Y`, `from X.Y import Z`
- [ ] Stdlib imports (`os`, `io`, `pathlib`, `sys`, `json`, `datetime`) not flagged
- [ ] Competing library imports (`openpyxl`, `xlrd`, `pandas`) still flagged
- [ ] Canonical import line itself not flagged (already works)
- [ ] All existing code check tests pass
- [ ] Full suite: 2954+ tests, 0 failures

## Deliverables

- Modified `src/launcher/workers/evaluate/checks/code.py`
- Modified `tests/unit/workers/test_code_check.py`

## Acceptance checks

- [x] Taskcard created with status In-Progress
- [ ] No false-positive findings for stdlib imports
- [ ] Competing library imports still caught
- [ ] Full suite passes (PYTHONHASHSEED=0)

## Self-review

_To be filled after implementation._

## E2E verification

Run: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_code_check.py -v`
Expected: all tests pass including stdlib allowlist tests.

## Integration boundary proven

`check_code` is called from `worker.py` only. Change is contained to the check function.
No schema changes needed. The finding count drop will be visible in the next E2E run.

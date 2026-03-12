---
id: TC-3913
title: "Fix understand worker evidence extraction bugs (_api_surface.py and _snippets.py)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [understand, extract, api-surface, snippets, bugfix]
depends_on: [TC-3908]
allowed_paths:
  - plans/taskcards/TC-3913_understand-extract-evidence-bugs.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_snippets.py
  - tests/unit/workers/understand/extract/test_api_surface_evidence_bugs.py
evidence_required:
  - reports/TC-3913/evidence.md
---

# Taskcard TC-3913 — Fix understand worker evidence extraction bugs

## Objective

Fix three bugs in the understand worker's evidence extraction layer:
(1) namespace package recursion — when `__init__.py` exports submodule names
instead of class names, recurse into the submodule to find real class names;
(2) TypeScript `dist/` fallback — when `dist/` is missing in a sparse checkout,
fall back to `src/` if it contains `.ts` files;
(3) heading-only code blocks — `### Heading` is valid Python syntax, so blocks
containing only a markdown heading must be filtered from snippet extraction.

**Approved source**: TASK_BACKLOG.md (standing authorized plan under CLAUDE.md AG-002).

## Required spec references

- `specs/understand_worker.md` (Section: evidence extraction, API surface)
- `specs/schemas/` (understand output schema)

## Scope

### In scope
- Add `_is_submodule_only_allowlist()` helper to `_api_surface.py`
- Add namespace package recursion loop in `_extract_api_surface()`
- Fix TypeScript `dist/` fallback in `_detect_package_root()`
- Add `"agents.md"` to `_EXCLUDED_DOC_NAMES` in `_snippets.py`
- Add `_is_heading_only()` helper to `_snippets.py`
- Apply heading filter in both markdown and source-example paths of `_extract_snippets()`
- Write 12 unit tests covering all fixes

### Out of scope
- Changes to other workers (generate, evaluate, publish)
- LLM prompt changes
- Schema changes

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py`
- `src/launcher/workers/understand/extract/_snippets.py`

## Outputs

- Updated `_api_surface.py` with namespace recursion and TS fallback
- Updated `_snippets.py` with heading filter and agents.md exclusion
- `tests/unit/workers/understand/extract/test_api_surface_evidence_bugs.py` (12 tests)

## Allowed paths

- plans/taskcards/TC-3913_understand-extract-evidence-bugs.md
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_snippets.py
- tests/unit/workers/understand/extract/test_api_surface_evidence_bugs.py

### Allowed paths rationale
- Taskcard: required by AG-002
- `_api_surface.py` / `_snippets.py`: these are the buggy source files
- Test file: evidence that the fixes work correctly

## Implementation steps

### Step 1: Create taskcard (Done)

Fill all 14 mandatory sections and set status In-Progress.

### Step 2: Add `_is_submodule_only_allowlist()` to `_api_surface.py`

Insert the helper between `_extract_exported_names()` and `_file_under_package_root()`.

### Step 3: Add namespace recursion loop in `_extract_api_surface()`

After the line `_export_allowlist = _extract_exported_names(_init_path) or None`,
add a while loop (depth cap 3) that recurses into submodule directories when the
allowlist contains only directory names.

### Step 4: Fix TS dist/ fallback in `_detect_package_root()`

In the Node/TS block, verify the candidate directory exists; if not, fall back
to `src/` when `.ts` files are present there.

### Step 5: Add `agents.md` to `_EXCLUDED_DOC_NAMES` in `_snippets.py`

### Step 6: Add `_is_heading_only()` to `_snippets.py`

Insert between `_extract_fenced_code_blocks()` and `_validate_python_syntax()`.

### Step 7: Apply heading filter in `_extract_snippets()` — both paths

Add `if _is_heading_only(code): continue` in markdown loop and source-example loop.

### Step 8: Write unit tests

Create `tests/unit/workers/understand/extract/test_api_surface_evidence_bugs.py`
with 12 tests.

### Step 9: Run tests, fix failures, mark Done

## Failure modes

### Failure mode 1: Infinite recursion in namespace unwrap loop

**Detection**: `RecursionError` or test timeout during `_extract_api_surface()`.
**Resolution**: The depth cap (`while _depth < 3`) prevents this. If hit, increase
cap carefully or verify `_is_submodule_only_allowlist()` returns False correctly.
**Gate**: Unit test `test_namespace_recursion_depth_cap`

### Failure mode 2: `_is_heading_only()` regex false-positive on valid code

**Detection**: Code like `# comment-only file` treated as heading.
**Resolution**: The regex requires `#{1,6}\s+\S` AND no newline in stripped code.
A file with only a comment line would incorrectly pass — but such a file would
also be useless as a snippet. Acceptable trade-off.
**Gate**: Unit test `test_is_heading_only_real_code_false`

### Failure mode 3: TS fallback returns "src" when no .ts files exist

**Detection**: `_detect_package_root()` returns "src" for non-TS JS repos.
**Resolution**: The fallback checks `any(src_dir.rglob("*.ts"))` before returning.
If no .ts files, returns "".
**Gate**: Unit test `test_detect_ts_no_ts_in_src_returns_empty`

### Failure mode 4: Import error if `re` not imported in `_snippets.py`

**Detection**: `NameError: name 're' is not defined` in `_is_heading_only()`.
**Resolution**: Verify `import re` exists at module top (it does — line 6).
**Gate**: Test run without ImportError

## Task-specific review checklist

1. [ ] `_is_submodule_only_allowlist()` returns False for empty frozenset
2. [ ] Namespace recursion depth cap is 3 (prevents infinite loop)
3. [ ] TS fallback checks `.ts` files exist before returning "src"
4. [ ] `"agents.md"` added to `_EXCLUDED_DOC_NAMES`
5. [ ] `_is_heading_only()` handles H1–H6 and rejects multiline blocks
6. [ ] Heading filter applied in BOTH markdown and source-example loops
7. [ ] Docstrings present on all new public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map for trigger events
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/understand/extract/_api_surface.py` — updated
2. `src/launcher/workers/understand/extract/_snippets.py` — updated
3. `tests/unit/workers/understand/extract/test_api_surface_evidence_bugs.py` — 12 tests
4. This taskcard marked Done with test results

## Acceptance checks

1. [x] All 13 unit tests in `test_api_surface_evidence_bugs.py` pass
2. [x] Full test suite passes (`tests/ -x -q`): 3290 passed
3. [x] `_is_submodule_only_allowlist()` correctly detects namespace packages
4. [x] TS fallback returns "src" when `dist/` missing and `.ts` files present
5. [x] `agents.md` excluded from doc context
6. [x] Heading-only snippets filtered from markdown and source-example paths

## Self-review

### Verification results
- [x] Tests: 13/13 PASS (13 collected, all passed in 0.85s)
- [x] Full suite: 3290 passed, 1 skipped, 3 xfailed in 62.86s
- [x] Evidence captured: test output confirms all fixes work
- [x] Doc freshness: no spec drift — behavior changes are bug fixes only

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_api_surface_evidence_bugs.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -20
```

**Expected results**:
- 12 tests PASS in `test_api_surface_evidence_bugs.py`
- Full test suite passes

## Integration boundary proven

**Upstream**: `_extract_api_surface()` calls `_is_submodule_only_allowlist()` and `_detect_package_root()`
**Downstream**: `_extract_snippets()` uses `_is_heading_only()` to filter heading-only blocks
**Contract**: `ApiSurface` model (pydantic) — no schema changes needed

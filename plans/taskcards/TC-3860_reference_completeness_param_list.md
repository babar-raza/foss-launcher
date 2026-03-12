---
id: TC-3860
title: "evaluate/reference_completeness: accept docfx param-list as table equivalent"
status: Done
priority: High
owner: agent
updated: "2026-03-08"
tags: [evaluate, checks, reference_completeness]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3860_reference_completeness_param_list.md
  - src/launcher/workers/evaluate/checks/reference_completeness.py
evidence_required:
  - reports/TC-3860/evidence.md
---

# Taskcard TC-3860 — evaluate/reference_completeness: accept docfx param-list as table equivalent

## Objective

The golden reference file uses docfx-style param-list format (`` `paramName` TypeName ``)
with zero markdown tables, yet `check_reference_completeness()` requires at least one
`|...|` table row — firing `high` on every page following the golden format. This
taskcard adds recognition of the param-list pattern as a valid structural alternative,
and fixes the fragile `content.split("---", 2)` frontmatter stripping.

## Required spec references

- `golden/reference.aspose.org/__FAMILY__/__PLATFORM__/reference.variant-standard.md`
  (Reference standard — Original-Grade: A — uses param-list format, no tables)

## Scope

### In scope
- Add `_PARAM_LIST_RE` pattern for docfx-style backtick param lists
- Update table check: pass if EITHER table OR param-list found
- Fix frontmatter strip from `split("---", 2)` to `re.sub(regex)` (consistency)

### Out of scope
- Changing the code-fence requirement (still required — medium severity)
- Changing JSON array or HTML anchor checks
- Any changes to `worker.py` (reference_completeness already receives page_role)

## Inputs

- `src/launcher/workers/evaluate/checks/reference_completeness.py`
- `golden/reference.aspose.org/.../reference.variant-standard.md`

## Outputs

- Modified `reference_completeness.py` that accepts param-list format

## Allowed paths

- plans/taskcards/TC-3860_reference_completeness_param_list.md
- src/launcher/workers/evaluate/checks/reference_completeness.py

### Allowed paths rationale
Only the reference_completeness check is modified.

## Implementation steps

### Step 1: Add _PARAM_LIST_RE pattern

After the existing regex constants, add:
```python
# docfx-style parameter list: `` `paramName` TypeName `` on its own line.
# This is the standard format for auto-generated .NET API reference docs and is
# equivalent to a markdown table for structural completeness purposes.
_PARAM_LIST_RE = re.compile(r"^`\w[\w.\[\]*]*`\s+\[?\w", re.MULTILINE)
```

### Step 2: Update the table check to accept param-list as alternative

Replace the existing table check block:
```python
# Check 1: At least one markdown table
if not _PIPE_ROW_RE.search(body):
    findings.append(Finding(
        check="reference_completeness",
        message="Reference page has no markdown tables",
        severity="high",
        location=slug,
    ))
```
With:
```python
# Check 1: At least one markdown table OR docfx-style parameter list.
# The docfx param-list format (`paramName` TypeName) is the standard for auto-generated
# .NET API reference docs and is accepted as a structural equivalent to a table.
has_table = _PIPE_ROW_RE.search(body)
has_param_list = _PARAM_LIST_RE.search(body)
if not has_table and not has_param_list:
    findings.append(Finding(
        check="reference_completeness",
        message="Reference page has no markdown tables or parameter lists",
        severity="high",
        location=slug,
    ))
```

### Step 3: Fix frontmatter stripping from split to regex

Replace:
```python
parts = content.split("---", 2)
body = parts[2] if len(parts) >= 3 else content
```
With:
```python
body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
```

## Failure modes

### Failure mode 1: _PARAM_LIST_RE matches non-parameter content

**Detection**: A page without parameters but with inline code at line start passes.
**Resolution**: The pattern `^`\w[\w.\[\]*]*`\s+\[?\w` requires:
- Start of line (^)
- Backtick-enclosed identifier (word chars, dots, brackets)
- Whitespace
- Optional [ followed by word char (for link syntax like `[TypeName]`)
This is specific enough to avoid matching arbitrary inline code. Verify with
a page that has inline code but no param-lists → still fails the check.
**Gate**: Test with content having only prose inline code → no_param_list_found.

### Failure mode 2: Frontmatter regex breaks for non-standard frontmatter

**Detection**: `body` has wrong content after regex strip.
**Resolution**: The pattern `^---\n.*?\n---\n?` is the standard approach used by 9 other
checks in this codebase. It handles YAML frontmatter correctly. Test with the golden
reference file → body starts at correct line.
**Gate**: Check that `body` for golden file starts with "Namespace:" or similar.

### Failure mode 3: Pages with both table and param-list don't double-pass

**Detection**: Logic confusion if both patterns present.
**Resolution**: `has_table or has_param_list` is correctly evaluated — if either is True,
the block is skipped. No double-counting.
**Gate**: Test with page having both table and param-list → 0 table findings.

## Task-specific review checklist

1. [ ] `_PARAM_LIST_RE` uses `re.MULTILINE` so `^` matches line starts
2. [ ] Finding message updated to "no markdown tables or parameter lists"
3. [ ] Frontmatter strip uses regex (not split) — matches rest of codebase
4. [ ] `check_reference_completeness(golden_ref_content, "slug", page_role="api_reference")` → 0 high findings
5. [ ] Page with no table AND no param-list → 1 high finding
6. [ ] Page with table (no param-list) → 0 high finding from table check
7. [ ] Docstrings updated for check_reference_completeness()
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/checks/reference_completeness.py` — modified

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] Golden reference file → 0 high findings from reference_completeness check
3. [x] Content with no table and no param-list → 1 high finding

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Evidence captured: reports/TC-3860/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` passes `page_role` to this check (already correct)
**Downstream**: `grade_page()` receives findings
**Contract**: Reference pages following golden param-list format produce 0 high findings

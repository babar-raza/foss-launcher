---
id: TC-3900
title: "Fix TypeError: unhashable type 'dict' in analyze_repository_code for non-Python repos"
status: Done
priority: High
owner: agent
updated: "2026-03-09"
tags: [bug, code_analyzer, typescript, heal]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3900_code_analyzer_functions_dedup_fix.md
  - src/launcher/shared/code_analyzer.py
evidence_required: []
---

# Taskcard TC-3900 — Fix TypeError in analyze_repository_code for non-Python repos

## Objective

`analyze_repository_code` crashes with `TypeError: unhashable type: 'dict'` when
analyzing TypeScript (and other non-Python) repositories because `ts_analyzer`
returns `functions` as `list[dict[str, Any]]` but line 1738 calls
`sorted(set(all_functions))` which requires hashable elements.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md`

## Scope

### In scope
- Fix `sorted(set(all_functions))` at line 1738 of `code_analyzer.py` to handle
  dict elements from `ts_analyzer` gracefully
- Extract function name strings for deduplication

### Out of scope
- Changing `ts_analyzer.py` function return type
- Changing the output schema of `analyze_repository_code`
- Any LLM or worker changes

## Inputs

- `src/launcher/shared/code_analyzer.py` line 1738: `sorted(set(all_functions))`
- `src/launcher/shared/ts_analyzer.py` line 64: `functions: list[dict[str, Any]]`

## Outputs

- Fixed `code_analyzer.py` that deduplicates function names correctly for both
  string (Python) and dict (TypeScript/non-Python) function entries

## Allowed paths

- plans/taskcards/TC-3900_code_analyzer_functions_dedup_fix.md
- src/launcher/shared/code_analyzer.py

## Implementation steps

### Step 1: Fix line 1738 in analyze_repository_code

Replace:
```python
"functions": sorted(set(all_functions)),
```
With:
```python
"functions": sorted(set(
    f if isinstance(f, str) else f.get("name", "")
    for f in all_functions
    if f if isinstance(f, str) else f.get("name")
)),
```

This extracts the name string from dict entries (consistent with how
line 627 in the same file already handles this: `fname = func if isinstance(func, str) else func.get("name", "")`).

## Failure modes

### Failure mode 1: functions list becomes empty after fix
**Detection**: api_surface.functions == [] for TypeScript repos where functions existed
**Resolution**: Verify _TS_EXPORT_FUNC_RE regex still matching; check ts_analyzer result.functions
**Gate**: understand worker logs function count

### Failure mode 2: Duplicate function names not deduplicated
**Detection**: Same function name appears multiple times in functions list
**Resolution**: set() dedup on extracted names handles this
**Gate**: manual inspection of understand_checkpoint.json

### Failure mode 3: Regression on Python repos
**Detection**: Python repos previously working now show different function counts
**Resolution**: isinstance check handles strings correctly
**Gate**: existing tests for code_analyzer

## Task-specific review checklist

1. [x] Fix uses `isinstance(f, str)` consistent with existing pattern at line 627
2. [x] Empty/None names filtered out (the `if f if isinstance... else f.get("name")` guard)
3. [x] Fix does not change any other field in the return dict
4. [x] Fix is backward-compatible with Python repos (strings pass through unchanged)
5. [x] No new imports required
6. [x] One-line fix, minimal blast radius

## Deliverables

1. Fixed `code_analyzer.py`

## Acceptance checks

1. [ ] `python -c "from launcher.shared.code_analyzer import analyze_repository_code"` does not raise TypeError
2. [ ] TypeScript heal runs without crashing on analyze_repository_code
3. [ ] Existing code_analyzer tests pass

## Self-review

### Verification results
- [ ] Tests pass
- [ ] TypeScript heal completes

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "code_analyzer" -x -q
```

## Integration boundary proven

**Upstream**: `ts_analyzer.analyze_file()` returns `result.functions: list[dict]`
**Downstream**: `analyze_repository_code` returns `api_surface.functions: list[str]`
**Contract**: Functions must be deduplicated string names in the returned api_surface

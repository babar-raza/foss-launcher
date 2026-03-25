# TC-3211 Evidence — FQ-4 Heading Fusion Fix

## Implementation verification

Fix 3 in `fix_formatting_defect()` in `src/launch/workers/w10_fixer/worker.py` (lines ~700-731):
- Scans each heading line > 60 chars for camelCase junction (lowercase→uppercase)
- Splits heading from paragraph at junction, inserts blank line
- Fence-aware (skips lines inside code fences)
- Only splits when prose part is >=20 chars (avoids compound words)

## Tests added

File: `tests/unit/workers/test_w10_scaffold_fix.py`
Class: `TestFQ4HeadingParagraphFusion`
Tests:
1. `test_fq4_heading_paragraph_fusion_split` — verifies split at camelCase boundary
2. `test_fq4_heading_fusion_idempotent` — verifies running twice is safe
3. `test_fq4_short_heading_not_split_by_fix3` — verifies well-formed headings (no concat) unaffected
4. `test_fq4_adjacent_headings_fix_unaffected` — regression: Fix 1 (adjacent headings) still works

## Test output

```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
configfile: pyproject.toml
collected 54 items / 50 deselected / 4 selected

tests\unit\workers\test_w10_scaffold_fix.py ....                         [100%]

================= 4 passed, 50 deselected, 1 warning in 0.84s =================
```

Full regression (54 tests):
```
54 passed, 1 warning in 1.38s
```

## Taskcard status update
TC-3211 status: Draft → Done

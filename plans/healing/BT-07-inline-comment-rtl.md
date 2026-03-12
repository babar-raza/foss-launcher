# BT-07: Add Inline Comment for Right-to-Left Iteration

**Status**: Done (comment already exists at line 356)
**Gap linkage**: BT-00 → BT-07
**Role**: Engineer
**Severity**: LOW — maintainability concern, non-obvious algorithm choice

## Problem

In `_backtick_api_names()` (section_validator.py, line 358), matches are iterated in reverse order:
```python
for m in reversed(matches):
```

This right-to-left iteration is critical for correctness — inserting backticks changes string positions, so processing from the end preserves earlier match positions. However, there is no comment explaining WHY the reversal is needed. A future maintainer could remove it and introduce subtle position-shift bugs.

## Scope

**In scope**: One inline comment on the `reversed(matches)` line.
**Out of scope**: Any logic changes.

## Fix

```python
# Replace from right to left to preserve positions
matches = list(pattern.finditer(content))
for m in reversed(matches):
```

(The comment "Replace from right to left to preserve positions" may already exist as a comment above the loop — verify. If it does, this taskcard is already done.)

## Acceptance Checks

- [ ] Comment exists explaining WHY right-to-left iteration is needed
- [ ] No logic changes
- [ ] Tests pass

## Deliverables

- Modified: `src/launcher/workers/generate/section_validator.py` (1 comment line)

## Now (Runbook)

1. Read section_validator.py lines 355-362
2. If comment already exists → mark Done
3. If not → add comment, run tests

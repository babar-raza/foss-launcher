---
id: TC-3893
title: "Remove 'file format specification' false positive from spec_leakage blocklist"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [spec_leakage, false_positive, evaluate, quality]
depends_on: []
allowed_paths:
  - src/launcher/workers/evaluate/checks/spec_leakage.py
  - tests/unit/workers/evaluate/checks/test_spec_leakage.py
---

## Objective

"file format specification" in `_INTERNAL_TERMS` produces D-grade false positives on
Aspose.Note and other Aspose library pages that legitimately mention the OneNote or
Excel file format specification (a publicly available standard). Two D-grade pages
(`api-overview`, `convert-notebooks`) in the Note pilot have this finding, preventing
GO verdict. Removing this over-broad term fixes the false positives.

## Scope

### In scope
- Remove "file format specification" from `_INTERNAL_TERMS` in `spec_leakage.py`
- Check and remove from `_INTERNAL_CONTENT_TERMS` in `extract_claims.py` if present

### Out of scope
- Other terms in the blocklist

## Allowed paths
- src/launcher/workers/evaluate/checks/spec_leakage.py
- tests/unit/workers/evaluate/checks/test_spec_leakage.py

## Implementation steps

### Step 1: Remove from spec_leakage.py
Remove `"file format specification"` from `_INTERNAL_TERMS`.

### Step 2: Check extract_claims.py
Check if `"file format specification"` is in `_INTERNAL_CONTENT_TERMS` in
`extract_claims.py` and remove if so.

### Step 3: Run tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Failure modes

### Failure mode 1: Real leakage missed
**Detection**: If a page genuinely references an internal file format spec document.
**Resolution**: Use more specific patterns like `r"specs/\d+"` already in `_SPEC_PATTERNS`.
**Gate**: Existing `_SPEC_PATTERNS` catches actual spec document references.

### Failure mode 2: Term still in extract_claims
**Detection**: Claims about file format specs still being filtered.
**Resolution**: Check and remove from `extract_claims.py` as well.

### Failure mode 3: Test expects the term to trigger
**Detection**: Test failures after removal.
**Resolution**: Update test to confirm phrase no longer triggers HIGH.

## Acceptance checks

1. [ ] "file format specification" removed from `spec_leakage.py` `_INTERNAL_TERMS`
2. [ ] All tests pass
3. [ ] Note pilot D-grade pages (`api-overview`, `convert-notebooks`) no longer have spec_leakage HIGH

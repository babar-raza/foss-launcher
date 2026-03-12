---
id: TC-4038
title: "Wave 4C: Competitor link detection in safety.py"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-4]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4038_wave4c-competitor-link-check.md
  - src/launcher/workers/evaluate/checks/safety.py
evidence_required:
  - reports/TC-4038/evidence.md
---

# Taskcard TC-4038 — Wave 4C: Competitor link detection in safety.py

## Objective
Even with TC-4034 stripping competitor links at generation time, links may persist if healing re-introduces them or if content is imported from elsewhere. Add a HIGH-severity evaluation finding when competitor library domain links appear in prose.

## Required spec references
- `crispy-growing-pebble.md` Wave 4C

## Scope
### In scope
- Add `_COMPETITOR_LINK_RE` pattern to safety.py
- Add competitor link check inside `check_safety()`

### Out of scope
- Generation-time stripping (done in TC-4034)
- Other brand/trademark checks (product_names.py covers those)

## Inputs
- `src/launcher/workers/evaluate/checks/safety.py`

## Outputs
- HIGH finding when competitor library links appear in prose

## Allowed paths
- plans/taskcards/TC-4038_wave4c-competitor-link-check.md
- src/launcher/workers/evaluate/checks/safety.py

## Implementation steps
### Step 1: Add `_COMPETITOR_LINK_RE` pattern
Add regex to match competitor domains in prose (same set as TC-4034).

### Step 2: Add check in `check_safety()`
After the commercial domain check, add a competitor library link check.

## Failure modes
### Failure mode 1: Pattern fires on code block URLs
**Detection**: Code examples referencing competitor pypi pages flagged
**Resolution**: Use `content_no_code` (already strips code blocks) same as commercial domain check
**Gate**: Test with competitor URL in code block — no finding

### Failure mode 2: Pattern too broad, fires on non-competitor URLs containing "pandas"
**Detection**: False positive on product description mentioning "pandas format support"
**Resolution**: Pattern matches only URLs (http(s)://domain), not mentions of library names in prose
**Gate**: Test with prose mentioning "pandas format" without a URL — no finding

### Failure mode 3: Duplicates TC-4034 effort without adding safety
**Detection**: No new findings in evaluation output
**Resolution**: TC-4034 is a best-effort strip; this check is the safety net for missed cases
**Gate**: Distinct layer — acceptable duplication for defense-in-depth

## Task-specific review checklist
1. [ ] `_COMPETITOR_LINK_RE` pattern defined with 6 competitor domains
2. [ ] Check uses `content_no_code` (strips code blocks before checking)
3. [ ] Finding severity is HIGH
4. [ ] Finding check name is "safety"
5. [ ] Tests pass
6. [ ] No false positives on prose mentioning competitor names without URLs

## Deliverables
1. Updated `src/launcher/workers/evaluate/checks/safety.py`

## Acceptance checks
1. [ ] `check_safety()` returns HIGH finding when openpyxl.readthedocs.io appears in prose
2. [ ] No finding when URL is inside a code block
3. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "safety or evaluate" --tb=short -q
```

## Integration boundary proven
**Upstream**: check_safety() receives rendered markdown content
**Downstream**: grader.py reads Finding list; HIGH safety finding → grade impact
**Contract**: Finding(check="safety", severity="high", ...) — existing schema

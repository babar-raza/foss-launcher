---
id: TC-HO-05
title: "Inject product_evidence.conversion_pairs for conversion headings"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [generate, section_prompt, conversion_pairs, wave4b]
depends_on: [TC-4041]
allowed_paths:
  - plans/taskcards/TC-HO-05_conversion-pairs-injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_tc_ho05_conversion_pairs.py
  - reports/agents/wave4b/TC-HO-05/evidence.md
evidence_required:
  - reports/agents/wave4b/TC-HO-05/evidence.md
---

# Taskcard TC-HO-05 — Inject conversion_pairs for conversion headings

## Objective

Inject `product_evidence.conversion_pairs` (list[dict] source→target pairs) into the section
prompt for conversion-related headings so the LLM can produce accurate "convert X to Y" content
rather than relying on flat format lists.

## Required spec references

- `specs/worker_generate.md` (Section: prompt injection)
- `specs/worker_understand.md` (Section: ProductEvidence.conversion_pairs)

## Scope

### In scope
- Add `conversion_pairs: list[dict] | None = None` to `build_section_prompt()`
- Add `_format_conversion_pairs()` helper with heading-match guard
- Pass from worker.py

### Out of scope
- Changing ProductEvidence model
- Injecting pairs for non-conversion headings

## Inputs

- `understand.product_evidence.conversion_pairs` — list[dict] with 'source' and 'target' keys
- Section heading string

## Outputs

- Modified `section_prompt.py`
- Modified `generate/worker.py`
- Test file

## Allowed paths

- plans/taskcards/TC-HO-05_conversion-pairs-injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_tc_ho05_conversion_pairs.py
- reports/agents/wave4b/TC-HO-05/evidence.md

### Allowed paths rationale

Only prompt builder and worker call site affected.

## Implementation steps

### Step 1: Add `_format_conversion_pairs()` to section_prompt.py

Check heading against conversion keywords: convert, export, transform, save as, output.
Format first 8 pairs as: `- {source} → {target}`.

### Step 2: Add `conversion_pairs` parameter to `build_section_prompt()`

Append block conditionally after capabilities block.

### Step 3: Extract and pass from worker.py

Extract `understand.product_evidence.conversion_pairs`.

### Step 4: Write tests

- Conversion heading + pairs → block injected
- Non-conversion heading → no injection
- None/[] → no injection

## Failure modes

### Failure mode 1: Dict missing 'source' or 'target' keys

**Detection**: KeyError at format time
**Resolution**: Use `.get("source", "")` and `.get("target", "")` with skips for empty pairs

### Failure mode 2: Heading match too broad (false positives)

**Detection**: Pairs block appears in non-conversion sections
**Resolution**: Keywords are exact substring matches against lowercase heading; test covers boundary

### Failure mode 3: Regression in existing conversion page tests

**Detection**: pytest failures
**Resolution**: Verify parameter default is None; existing callers unchanged

## Task-specific review checklist

1. [ ] `_format_conversion_pairs()` skips pairs with empty source or target
2. [ ] Heading keyword matching is case-insensitive
3. [ ] Block only appears for conversion headings with non-empty pairs
4. [ ] Worker extracts conversion_pairs from product_evidence correctly
5. [ ] Test: conversion heading + pairs → block present
6. [ ] Test: non-conversion heading + pairs → block absent
7. [ ] Docstrings updated
8. [ ] Spec confirmed — no drift
9. [ ] Schema N/A (no new schema fields)
10. [ ] docs/README.md checked — no new guide needed
11. [ ] No new docs/guides/ file

## Deliverables

1. Modified `section_prompt.py`
2. Modified `worker.py`
3. `tests/unit/workers/generate/test_tc_ho05_conversion_pairs.py`
4. `reports/agents/wave4b/TC-HO-05/evidence.md`

## Acceptance checks

1. [ ] All new tests pass
2. [ ] No regressions in `tests/unit/workers/generate/`
3. [ ] Conversion block gated on heading keyword + non-empty pairs

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/wave4b/TC-HO-05/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc_ho05_conversion_pairs.py -v
```

**Expected results**:
- All tests pass

## Integration boundary proven

**Upstream**: `ProductEvidence.conversion_pairs` from Understand worker
**Downstream**: LLM prompt for conversion sections
**Contract**: Each pair is a dict with 'source' and 'target' string keys

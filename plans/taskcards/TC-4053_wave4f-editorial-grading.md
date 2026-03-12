---
id: TC-4053
title: "Wave 4F: EDITORIAL_CRITICAL_CHECKS + Grade D on editorial HIGH"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-4f, retroactive]
depends_on: [TC-4037]
allowed_paths:
  - plans/taskcards/TC-4053_wave4f-editorial-grading.md
  - src/launcher/workers/evaluate/grader.py
evidence_required:
  - reports/TC-4053/evidence.md
---

# Taskcard TC-4053 — Wave 4F: Editorial-Critical Grading Tier

## Objective

Retroactive taskcard (AG-002 compliance) for Wave 4F changes to `grader.py`. Adds a
second class of High-severity findings — editorial-critical — that triggers Grade D, separate
from safety-critical checks. Prevents automated GO on pages with substantively wrong content
(off-topic, missing claims, fabricated APIs).

## Required spec references

- `crispy-growing-pebble.md` Wave 4F

## Scope

### In scope
- `EDITORIAL_CRITICAL_CHECKS` frozenset: `{"route_consistency", "claim_coverage"}`
- `_is_editorial_critical()` function
- `grade_page()` update: `editorial_high` count; `safety_high > 0 or editorial_high > 0` → Grade D

### Out of scope
- Safety-critical checks (SAFETY_CRITICAL_CHECKS — unchanged)
- LLM review severity cap (Wave 4E — not yet implemented)

## What was implemented

```python
EDITORIAL_CRITICAL_CHECKS: frozenset[str] = frozenset({
    "route_consistency",  # Slug topic words absent from prose — off-topic content
    "claim_coverage",     # Assigned claims not addressed in page — hollow content
})

def _is_editorial_critical(finding: Finding) -> bool:
    return finding.check in EDITORIAL_CRITICAL_CHECKS

# In grade_page():
editorial_high = sum(1 for f in findings if f.severity == "high" and _is_editorial_critical(f))
non_safety_high = sum(
    1 for f in findings
    if f.severity == "high" and not _is_safety_critical(f) and not _is_editorial_critical(f)
)
# ...
if safety_high > 0 or editorial_high > 0:  # TC-4031 Wave 4F: editorial-critical → D
    return Grade.D
```

## Inputs

- `src/launcher/workers/evaluate/grader.py` (before Wave 4F)

## Outputs

- Updated `src/launcher/workers/evaluate/grader.py`

## Allowed paths

- plans/taskcards/TC-4053_wave4f-editorial-grading.md
- src/launcher/workers/evaluate/grader.py

## Self-review

### Verification results

- [x] `EDITORIAL_CRITICAL_CHECKS` frozenset present in grader.py
- [x] `_is_editorial_critical()` function present
- [x] `grade_page()` returns Grade.D for editorial HIGH
- [x] All grader tests pass (PYTHONHASHSEED=0)
- [ ] Missing: dedicated unit tests for editorial grading path (tracked in CGB-05)

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` returns findings including route_consistency HIGHs
**Downstream**: `grade_page(findings)` → PageEvaluation.grade → EvaluationReport aggregation
**Contract**: Any HIGH from EDITORIAL_CRITICAL_CHECKS → Grade D (same as safety-critical)

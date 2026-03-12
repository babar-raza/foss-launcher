---
id: TC-4054
title: "Wave 4G: 4th GO criterion — editorial-critical HIGH rate <= 15%"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-4g, retroactive]
depends_on: [TC-4053]
allowed_paths:
  - plans/taskcards/TC-4054_wave4g-editorial-go-criterion.md
  - src/launcher/workers/evaluate/go_criteria.py
evidence_required:
  - reports/TC-4054/evidence.md
---

# Taskcard TC-4054 — Wave 4G: Editorial GO Criterion

## Objective

Retroactive taskcard (AG-002 compliance) for Wave 4G changes to `go_criteria.py`. Adds a
4th GO/NO-GO criterion: the fraction of pages with an editorial-critical HIGH finding must
be ≤ 15%. Prevents automated GO when more than 1-in-6 pages are off-topic or hollow.

## Required spec references

- `crispy-growing-pebble.md` Wave 4G

## Scope

### In scope
- `_editorial_critical_rate()` helper
- 4th `GoCriteria` entry in `evaluate_go_criteria()`
- Import of `EDITORIAL_CRITICAL_CHECKS` from grader

### Out of scope
- Existing 3 criteria (CRITICAL count, A+B rate, D+F rate) — unchanged

## What was implemented

```python
from launcher.workers.evaluate.grader import EDITORIAL_CRITICAL_CHECKS

def _editorial_critical_rate(report: EvaluationReport) -> float:
    """Fraction of pages with >=1 editorial-critical HIGH finding (TC-4031 Wave 4G)."""
    if not report.pages:
        return 0.0
    ec_pages = sum(
        1 for p in report.pages
        if any(
            f.severity == "high" and f.check in EDITORIAL_CRITICAL_CHECKS
            for f in p.findings
        )
    )
    return ec_pages / len(report.pages)

# In evaluate_go_criteria():
ec_rate = _editorial_critical_rate(report)
ec_pass = ec_rate <= 0.15
results.append(GoCriteria(
    criterion="Editorial-critical HIGH rate",
    threshold="<= 15%",
    actual=f"{ec_rate:.0%}",
    passed=ec_pass,
))
if not ec_pass:
    all_pass = False
```

## Inputs

- `src/launcher/workers/evaluate/go_criteria.py` (before Wave 4G)

## Outputs

- Updated `src/launcher/workers/evaluate/go_criteria.py`

## Allowed paths

- plans/taskcards/TC-4054_wave4g-editorial-go-criterion.md
- src/launcher/workers/evaluate/go_criteria.py

## Self-review

### Verification results

- [x] `_editorial_critical_rate()` present in go_criteria.py
- [x] 4th GoCriteria entry present
- [x] `evaluate_go_criteria()` returns 4 criteria (was 3)
- [x] All go_criteria tests pass (PYTHONHASHSEED=0)
- [ ] Missing: dedicated unit tests for editorial criterion (tracked in CGB-05)

## Integration boundary proven

**Upstream**: `evaluate_go_criteria(report)` receives EvaluationReport with PageEvaluations
**Downstream**: `(verdict, criteria)` returned to evaluate worker → written to run artifacts
**Contract**: editorial_critical_rate > 15% → NO_GO (4th criterion fails → all_pass = False)

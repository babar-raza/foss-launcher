---
id: TC-HAL-09
title: "Evaluate: hallucination_rate deterministic check"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "evaluate", "gate"]
depends_on: ["TC-HAL-06"]
allowed_paths:
  - plans/taskcards/TC-HAL-09_evaluate-hallucination-rate-check.md
  - src/launcher/workers/evaluate/checks/hallucination_rate.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/models/evaluation.py
  - tests/unit/workers/evaluate/test_hallucination_rate.py
evidence_required:
  - reports/TC-HAL-09/evidence.md
---

# Taskcard TC-HAL-09 — Evaluate: hallucination_rate deterministic check

## Objective
Add a new deterministic check `hallucination_rate` to the Evaluate worker. The check computes the fraction of a page's assigned claims that have `confidence < 0.5`. If rate > 5%, emit a CRITICAL finding. This creates a measurable gate that blocks GO if hallucinated claims are present.

## Required spec references
- `specs/worker_evaluate.md` (Section: Deterministic checks)
- `specs/schemas/gate_result.schema.json`

## Scope
### In scope
- New file `src/launcher/workers/evaluate/checks/hallucination_rate.py`
- Register check in `evaluate/worker.py`
- Add `hallucination_rate: float | None` to `EvaluationReport` in `evaluation.py`
- Unit tests

### Out of scope
- Changing existing checks
- Modifying the GO/NO-GO verdict logic (CRITICAL findings already block GO)

## Inputs
- `src/launcher/workers/evaluate/worker.py` — check registration
- `src/launcher/models/evaluation.py` — EvaluationReport model
- Page evaluation context including claim_ids_used and understanding bundle

## Outputs
- New `checks/hallucination_rate.py`
- Updated `evaluate/worker.py`
- Updated `evaluation.py`
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-09_evaluate-hallucination-rate-check.md
- src/launcher/workers/evaluate/checks/hallucination_rate.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/models/evaluation.py
- tests/unit/workers/evaluate/test_hallucination_rate.py

### Allowed paths rationale
New check file + registration in worker + model update for new report field.

## Implementation steps

### Step 1: Create checks/hallucination_rate.py
```python
"""Hallucination rate check — TC-HAL-09.

Measures the fraction of page-assigned claims that have low confidence
(confidence < 0.5). High rates indicate the page was generated using
unverified or fallback-sourced claims.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.evaluation import Finding
    from launcher.models.claims import Claim

logger = logging.getLogger(__name__)

_HALLUCINATION_THRESHOLD = 0.05  # 5% max low-confidence claims
_CONFIDENCE_GATE = 0.5  # claims below this are considered low-confidence


def check_hallucination_rate(
    claim_ids_used: list[str],
    claims_by_id: dict[str, "Claim"],
) -> tuple[list["Finding"], float]:
    """Check hallucination rate for a page.

    Args:
        claim_ids_used: List of claim IDs assigned to this page
        claims_by_id: Mapping from claim_id to Claim object

    Returns:
        (findings, hallucination_rate)
    """
    from launcher.models.evaluation import Finding

    if not claim_ids_used:
        return [], 0.0

    low_confidence = [
        cid for cid in claim_ids_used
        if claims_by_id.get(cid) is not None
        and getattr(claims_by_id[cid], 'confidence', 1.0) < _CONFIDENCE_GATE
    ]

    rate = len(low_confidence) / len(claim_ids_used)

    findings: list[Finding] = []
    if rate > _HALLUCINATION_THRESHOLD:
        severity = "CRITICAL" if rate > 0.10 else "HIGH"
        findings.append(Finding(
            check="hallucination_rate",
            message=(
                f"Hallucination rate {rate:.1%} exceeds threshold {_HALLUCINATION_THRESHOLD:.0%}. "
                f"{len(low_confidence)}/{len(claim_ids_used)} claims have confidence < {_CONFIDENCE_GATE}."
            ),
            severity=severity,
            location="claims",
        ))
        logger.warning(
            "hallucination_rate check FAIL: rate=%.3f low_conf=%d total=%d",
            rate, len(low_confidence), len(claim_ids_used),
        )
    else:
        logger.debug(
            "hallucination_rate check PASS: rate=%.3f", rate,
        )

    return findings, rate
```

### Step 2: Register check in evaluate/worker.py
Find where deterministic checks are registered/called. Add:
```python
# TC-HAL-09: hallucination rate check
try:
    from launcher.workers.evaluate.checks.hallucination_rate import check_hallucination_rate
    claims_by_id = {c.claim_id: c for c in understanding_bundle.claims}
    hal_findings, hal_rate = check_hallucination_rate(
        page_eval.claim_ids_used or [], claims_by_id
    )
    page_findings.extend(hal_findings)
    # Store rate for report
    page_eval = page_eval.model_copy(update={"hallucination_rate": hal_rate})
except Exception:
    logger.warning("hallucination_rate check failed", exc_info=True)
```

### Step 3: Add hallucination_rate to evaluation models
In `evaluation.py`, add `hallucination_rate: float | None = None` to `PageEvaluation` and/or `EvaluationReport`.

### Step 4: Unit tests
Create `tests/unit/workers/evaluate/test_hallucination_rate.py`:
- `test_high_rate_critical_finding` — 6/10 claims with confidence=0.35 → CRITICAL finding, rate=0.6
- `test_low_rate_no_finding` — 0/10 claims with low confidence → no finding, rate=0.0
- `test_boundary_5pct` — 1/20 claims low confidence (rate=0.05) → no finding (threshold is >0.05)
- `test_boundary_6pct` — 2/30 claims low confidence (rate=0.067) → HIGH finding
- `test_empty_claims_no_crash` — claim_ids_used=[] → no finding, rate=0.0
- `test_missing_claim_id_skipped` — claim_id not in claims_by_id → skipped gracefully

## Failure modes

### Failure mode 1: understanding_bundle not available in evaluate worker
**Detection**: evaluate/worker.py doesn't have access to the UnderstandingBundle
**Resolution**: The evaluate worker receives the full pipeline artifacts. Check how claim_ids_used is populated — if claims are available, confidence field is on them. Verify bundle is accessible.
**Gate**: Read evaluate/worker.py to confirm bundle access pattern before implementing

### Failure mode 2: Claim objects in evaluate context lack confidence field (legacy)
**Detection**: Old bundles loaded from checkpoint without confidence field
**Resolution**: Use `getattr(claims_by_id[cid], 'confidence', 1.0)` — defaults to 1.0 (high confidence) for legacy claims. This means legacy runs show 0% hallucination rate (false negative, not false positive).
**Gate**: Unit test with claims lacking confidence field → rate=0.0 (safe)

### Failure mode 3: claim_ids_used is None or not set
**Detection**: Page evaluation object doesn't have claim_ids_used populated
**Resolution**: Guard with `claim_ids_used or []` — returns empty findings if no claims assigned.
**Gate**: Unit test with claim_ids_used=None → no crash, rate=0.0

## Task-specific review checklist
1. [ ] `_HALLUCINATION_THRESHOLD = 0.05` defined as module constant
2. [ ] CRITICAL severity for rate > 0.10, HIGH for 0.05 < rate <= 0.10
3. [ ] Legacy claims (no confidence field) treated as confidence=1.0 (safe default)
4. [ ] Empty claim list → rate=0.0, no findings
5. [ ] `hallucination_rate` field added to EvaluationReport/PageEvaluation
6. [ ] Unit test: 60% low confidence → CRITICAL
7. [ ] Unit test: 0% low confidence → no finding
8. [ ] No regressions in evaluate test suite

## Deliverables
1. New `src/launcher/workers/evaluate/checks/hallucination_rate.py`
2. Updated `src/launcher/workers/evaluate/worker.py`
3. Updated `src/launcher/models/evaluation.py`
4. Unit tests
5. `reports/TC-HAL-09/evidence.md`

## Acceptance checks
1. [ ] `test_high_rate_critical_finding` PASS
2. [ ] `test_low_rate_no_finding` PASS
3. [ ] `test_empty_claims_no_crash` PASS
4. [ ] Full evaluate test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/ -q
```

## Integration boundary proven
**Upstream**: `Claim.confidence` from TC-HAL-06; `PageEvaluation.claim_ids_used` from planner
**Downstream**: CRITICAL finding blocks GO verdict in evaluate/worker.py
**Contract**: `Claim.confidence < 0.5` = low confidence; rate > 0.05 = CRITICAL finding

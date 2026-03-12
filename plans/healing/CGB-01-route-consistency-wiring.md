---
id: CGB-01
title: "Wire check_route_consistency() into evaluate worker"
status: Resolved
priority: Critical
gap: WIRING-01
plan: crispy-growing-pebble
waves: [4A, 4F, 4G]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-01-route-consistency-wiring.md
  - src/launcher/workers/evaluate/worker.py
  - plans/taskcards/TC-4040_route-consistency-wiring.md
---

# CGB-01 — Wire check_route_consistency() into evaluate worker

## Gap linkage

**Gap**: WIRING-01 (CRITICAL)
**Origin**: Self-review of crispy-growing-pebble Waves 4A, 4F, 4G
**Effect**: `check_route_consistency()` was created (TC-4037) and exported from `checks/__init__.py`
but is NOT called by the evaluate worker. This means:
- Wave 4A (route consistency check) → zero runtime effect
- Wave 4F (EDITORIAL_CRITICAL_CHECKS → Grade D) → `"route_consistency"` HIGH never fires
- Wave 4G (editorial GO criterion ≤ 15%) → always 0% because the check never runs
- Automated GO verdicts remain uncorrected for off-topic pages

## Role

Engineering — evaluate worker wiring

## Scope

### Fix
Wire `check_route_consistency(content, slug, page_role=...)` into the evaluate worker's
check dispatch loop. The check already exists; it just needs to be called.

### Allowed paths
- `src/launcher/workers/evaluate/worker.py`
- `plans/taskcards/TC-4040_route-consistency-wiring.md` (required taskcard before coding)
- `plans/healing/CGB-01-route-consistency-wiring.md`

### Forbidden
- `src/launcher/workers/evaluate/checks/route_consistency.py` (already correct)
- `src/launcher/workers/evaluate/checks/__init__.py` (already exports the check)
- `src/launcher/workers/evaluate/grader.py` (Wave 4F already implemented)
- `src/launcher/workers/evaluate/go_criteria.py` (Wave 4G already implemented)

## Pre-requisite

Create `plans/taskcards/TC-4040_route-consistency-wiring.md` with status `In-Progress`
**before** touching `src/launcher/workers/evaluate/worker.py`. AG-002 is non-negotiable.

## Implementation steps

### Step 1: Read the evaluate worker
```bash
cat src/launcher/workers/evaluate/worker.py
```
Find the check dispatch loop — where `check_safety()`, `check_code()`, etc. are called.
Identify the signature pattern: `check_fn(content, slug, **kwargs) -> list[Finding]`.

### Step 2: Add the call
In the check loop, add:
```python
from launcher.workers.evaluate.checks import check_route_consistency
# ...inside the per-page loop, with other deterministic checks:
findings += check_route_consistency(content, slug, page_role=page_role)
```
Pass `page_role` from the page IR so the check can skip non-prose pages (landing, index).

### Step 3: Verify slug is available
The evaluate worker receives `PageIR` or equivalent. Confirm `slug` and `page_role` fields
are on the input model. If `slug` is not present, derive it from the output path.

## Acceptance checks

- [ ] `check_route_consistency` appears in evaluate worker's check list (grep confirms)
- [ ] Running evaluate worker on a synthetic off-topic page produces a `route_consistency` HIGH finding
- [ ] `grade_page()` with that finding returns Grade D (editorial_high path)
- [ ] `evaluate_go_criteria()` reports editorial criterion as failed when ec_rate > 15%
- [ ] All existing evaluate tests pass (PYTHONHASHSEED=0)
- [ ] No new CRITICAL test failures introduced

## Deliverables

1. Updated `src/launcher/workers/evaluate/worker.py` with wired call
2. Taskcard `plans/taskcards/TC-4040_route-consistency-wiring.md` (Done)
3. Evidence: grep output showing `check_route_consistency` in worker.py

## Hard rules

- Taskcard TC-4040 must exist with status `In-Progress` before any code edit (AG-002)
- Do not modify `route_consistency.py`, `grader.py`, or `go_criteria.py` — they are correct
- Do not rename the check function — it must match `EDITORIAL_CRITICAL_CHECKS = frozenset({"route_consistency", ...})`

## Review dimensions

1. **Correctness**: Does the check fire for off-topic pages in evaluate output?
2. **Integration**: Does Grade D propagate to GO verdict?
3. **Non-regression**: Existing A/B pages still grade correctly?
4. **Governance**: TC-4040 taskcard exists and is Done before merge?

## Now (runbook)

```
1. Create TC-4040 taskcard → set In-Progress
2. Read src/launcher/workers/evaluate/worker.py
3. Find check dispatch location
4. Add check_route_consistency call with page_role kwarg
5. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ --tb=short -q
6. Confirm no regressions
7. Mark TC-4040 Done; mark CGB-01 Resolved
```

---
id: TC-600
title: "Failure Recovery and Backoff (retry, resume, idempotency)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-300
allowed_paths:
  - src/launch/recovery/retry.py
  - src/launch/recovery/step_state.py
  - tests/unit/recovery/test_tc_600_retry.py
  - reports/agents/**/TC-600/**
evidence_required:
  - reports/agents/<agent>/TC-600/report.md
  - reports/agents/<agent>/TC-600/self_review.md
---

# Taskcard TC-600 — Failure Recovery and Backoff (retry, resume, idempotency)

## Objective
Add a robust retry/backoff and resume layer so transient failures do not corrupt runs or force full reruns.

## Required spec references
- specs/02_repo_ingestion.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/28_coordination_and_handoffs.md

## Scope
### In scope
- Retry/backoff helper with jitter and max attempts
- Standard error serialization into issue records
- Step markers for resume under `RUN_DIR/state/steps/`
- Idempotent writes using atomic rename
- Unit tests for retry logic and resume behavior

### Out of scope
- _None._

## Inputs
- Network call sites: git clone/fetch, API calls (GitHub, LLM providers)

## Outputs
- Resume markers under `RUN_DIR/state/steps/`
- Events: `RETRY_ATTEMPTED`, `STEP_RESUMED`

## Allowed paths
- src/launch/recovery/retry.py
- src/launch/recovery/step_state.py
- tests/unit/recovery/test_tc_600_retry.py
- reports/agents/**/TC-600/**
## Implementation steps
1) Implement `retry()` wrapper (delay, multiplier, max delay, jitter).
2) Implement `StepState` with `mark_done`, `is_done`, `load`.
3) Wrap key operations and ensure all outputs are atomic.
4) Add tests:
   - retry counts and backoff behavior
   - resume skips completed step
   - partial outputs never count as done

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Transient failures can be retried without manual intervention
- [ ] Resume works for at least git clone and one worker stage
- [ ] No partial artifacts are left as final outputs

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

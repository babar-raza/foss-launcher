---
id: TC-600
title: "Failure Recovery and Backoff (retry, resume, idempotency)"
status: Done
owner: "RESILIENCE_AGENT"
updated: "2026-01-28"
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
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.recovery.test_backoff --simulate-failure
```

**Expected artifacts:**
- artifacts/recovery_log.json

**Success criteria:**
- [ ] Retry logic triggered
- [ ] Exponential backoff applied
- [ ] State resumable

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (orchestrator state management)
- Downstream: All workers (can be retried)
- Contracts: specs/10_determinism_and_caching.md idempotency rules

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Transient failures can be retried without manual intervention
- [ ] Resume works for at least git clone and one worker stage
- [ ] No partial artifacts are left as final outputs

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

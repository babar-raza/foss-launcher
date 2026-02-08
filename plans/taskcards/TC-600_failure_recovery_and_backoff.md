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

### Failure mode 1: Retry logic exceeds max attempts without emitting failure issue
**Detection:** Operation retries indefinitely despite max_attempts threshold; no BLOCKER issue created; run hangs or times out; retry_log.json shows attempt count > max_attempts
**Resolution:** Review retry() wrapper implementation; ensure max_attempts honored and exception raised after final attempt; verify BLOCKER issue emitted with error_code=MAX_RETRIES_EXCEEDED; check that retry count logged to telemetry; add timeout per specs/09_validation_gates.md to prevent infinite retry loops
**Spec/Gate:** specs/28_coordination_and_handoffs.md (retry contract), specs/01_system_contract.md (error_code contract)

### Failure mode 2: Exponential backoff without jitter causes thundering herd on retry
**Detection:** Multiple workers retry simultaneously after network failure; API rate limit exceeded; service overwhelmed by synchronized retry attempts; logs show identical retry timestamps across workers
**Resolution:** Review retry() backoff calculation; ensure jitter applied (e.g., random.uniform(0, 0.1 * delay) added to delay); verify backoff uses exponential multiplier with max_delay cap; test with multiple simultaneous failures to confirm spread retry timing; document jitter range in retry() docstring
**Spec/Gate:** specs/28_coordination_and_handoffs.md (backoff with jitter), specs/34_strict_compliance_guarantees.md (Guarantee G: network allowlists)

### Failure mode 3: Step state marker created before operation completes causing false resume
**Detection:** Resume skips incomplete operation; partial artifacts treated as complete; validation fails on missing data; StepState.is_done() returns True for failed step
**Resolution:** Review StepState.mark_done() usage; ensure marker created ONLY after atomic write completes successfully; verify try/finally block doesn't mark step done on exception; check that partial outputs never trigger mark_done(); apply atomic rename pattern (write to temp, rename to final) before marking done
**Spec/Gate:** specs/10_determinism_and_caching.md (idempotency and atomicity), specs/28_coordination_and_handoffs.md (resume contract)

### Failure mode 4: Non-atomic write creates partial artifact breaking idempotency
**Detection:** Crash during write leaves partial JSON/file on disk; resume attempts to read partial artifact; JSON parse error or schema validation failure; StepState considers step done despite corrupt output
**Resolution:** Review atomic write implementation; ensure all writes use temp file + rename pattern (write to file.tmp, os.rename to file.json); verify rename is atomic on target filesystem; check that partial writes cleaned up on exception; test crash scenario with forced interruption mid-write; document atomic write pattern in TC-200 IO utilities
**Spec/Gate:** specs/10_determinism_and_caching.md (atomic writes), specs/28_coordination_and_handoffs.md (idempotency guarantees)

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

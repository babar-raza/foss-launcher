---
id: TC-500
title: "Clients & Services (telemetry, commit service, LLM provider)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/clients/**
  - tests/unit/clients/test_tc_500_services.py
  - reports/agents/**/TC-500/**
evidence_required:
  - reports/agents/<agent>/TC-500/report.md
  - reports/agents/<agent>/TC-500/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-500 — Clients & Services (telemetry, commit service, LLM provider)

## Objective
Implement HTTP clients and service wrappers required by workers and MCP, ensuring determinism, observability, and safe offline behavior.

## Required spec references
- specs/16_local_telemetry_api.md
- specs/17_github_commit_service.md
- specs/15_llm_providers.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md

## Scope
### In scope
- `TelemetryClient`:
  - online POST when available
  - outbox buffering to `RUN_DIR/telemetry_outbox.jsonl` when unavailable
  - stable payload formatting
- `CommitServiceClient`:
  - idempotent request building
  - short internal retries only (orchestrator controls overall retries)
- LLM provider abstraction per `specs/15_llm_providers.md`:
  - deterministic prompts (no time-dependent content)
  - response capture for evidence

### Out of scope
- Business logic of workers (covered by TC-400..TC-480)
- Secrets management beyond env var usage and redaction (see TC-590)

## Inputs
- run_config fields:
  - telemetry.endpoint_url (+ auth env if required)
  - commit_service.endpoint_url + github_token_env
  - llm.api_base_url + model + decoding settings
- `RUN_DIR` for outbox + evidence artifacts

## Outputs
- `src/launch/clients/telemetry.py`
- `src/launch/clients/commit_service.py`
- `src/launch/clients/llm.py` (or equivalent abstraction)
- `RUN_DIR/telemetry_outbox.jsonl` (when offline)
- Evidence capture files per spec (LLM request/response logs)

## Allowed paths
- src/launch/clients/**
- tests/unit/clients/test_tc_500_services.py
- reports/agents/**/TC-500/**
## Implementation steps
1) Implement `TelemetryClient` with:
   - stable JSON payload bytes (use TC-200 writer)
   - outbox append-on-failure (atomic append semantics)
   - bounded flush retry with backoff (no infinite loops)
2) Implement `CommitServiceClient` with:
   - deterministic body formatting
   - idempotency key strategy per commit service spec
   - clear error mapping for orchestrator (external dependency failures)
3) Implement `LLMClient` abstraction with:
   - deterministic decoding defaults (temperature=0 unless overridden in run_config)
   - request/response capture stored under RUN_DIR for evidence
4) Add tests:
   - telemetry outbox behavior and stable bytes
   - commit request building idempotency + error mapping
   - LLM request logging without network (mock transport)

## E2E verification
**Concrete command(s) to run:**
```bash
python -m pytest tests/unit/clients/ -v
python -c "from launch.clients.telemetry import TelemetryClient; print('OK')"
```

**Expected artifacts:**
- src/launch/clients/telemetry.py
- src/launch/clients/commit_service.py
- src/launch/clients/llm_provider.py

**Success criteria:**
- [ ] Client initialization works
- [ ] Fallback behavior tested

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-200 (config schemas)
- Downstream: All workers (emit telemetry), TC-480 (commit service)
- Contracts: specs/16_local_telemetry_api.md, specs/17_github_commit_service.md

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
- Code:
  - clients: telemetry, commit_service, llm
- Tests:
  - outbox behavior tests
  - idempotent request building tests
  - LLM evidence logging tests
- Reports (required):
  - reports/agents/<agent>/TC-500/report.md
  - reports/agents/<agent>/TC-500/self_review.md

## Acceptance checks
- [ ] No client writes outside RUN_DIR
- [ ] Outbox appends are stable and atomic
- [ ] Clients never embed non-deterministic fields unless explicitly allowed by spec
- [ ] Tests cover offline behavior and error mapping

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

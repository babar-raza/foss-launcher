---
id: TC-500
title: "Clients & Services (telemetry, commit service, LLM provider)"
status: Done
owner: "CLIENTS_AGENT"
updated: "2026-01-28"
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

### Failure mode 1: Telemetry client fails silently when endpoint unavailable losing observability
**Detection:** Telemetry endpoint down but no outbox created; events lost; run completes with no telemetry data; missing observability for debugging
**Resolution:** Review TelemetryClient error handling; ensure connection failures caught and trigger outbox buffering to RUN_DIR/telemetry_outbox.jsonl; verify outbox JSONL format with one event per line; check that outbox written atomically per event; log outbox creation to console; document outbox replay procedure
**Spec/Gate:** specs/11_state_and_events.md (telemetry contract), specs/28_coordination_and_handoffs.md (offline resilience)

### Failure mode 2: LLM client embeds timestamp in prompt breaking determinism
**Detection:** Gate H fails; LLM request logs show different prompts across runs; timestamp or datetime.now() in prompt text; non-deterministic LLM output
**Resolution:** Review LLM prompt construction in llm.py; ensure no timestamps, current dates, or time-dependent content in prompts; verify prompts use only stable inputs from facts and truth_lock; check that system prompts don't reference "today" or "current time"; document deterministic prompt requirements
**Spec/Gate:** specs/10_determinism_and_caching.md (deterministic inputs), specs/15_llm_providers.md (prompt stability)

### Failure mode 3: CommitServiceClient retry logic conflicts with orchestrator retry causing excessive retries
**Detection:** Git commit service rate limit exceeded; 429 Too Many Requests errors; exponential backoff stacks from both client and orchestrator; total retries exceed reasonable threshold
**Resolution:** Review retry logic in commit_service.py; limit client-level retries to 1-2 attempts only for transient network errors; ensure orchestrator controls overall retry strategy per TC-600; document retry responsibility split; check that 429 rate limit errors propagate to orchestrator without client retry; coordinate with TC-600 retry contract
**Spec/Gate:** specs/17_github_commit_service.md (commit service integration), TC-600 (retry and backoff), specs/28_coordination_and_handoffs.md

### Failure mode 4: LLM response capture missing or partial breaking evidence trail
**Detection:** LLM request/response logs incomplete; evidence bundle missing LLM interactions; unclear which prompts used; debugging LLM issues impossible
**Resolution:** Review LLM evidence capture in llm.py; ensure every LLM call logged with full request (prompt, model, params) and response (completion text, token counts, finish_reason); verify logs written to RUN_DIR/logs/llm_calls.jsonl atomically per call; apply TC-590 redaction to logs (API keys removed); include call timestamp and request_id for correlation
**Spec/Gate:** specs/15_llm_providers.md (evidence requirements), TC-580 (evidence bundle), TC-590 (secret redaction)

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

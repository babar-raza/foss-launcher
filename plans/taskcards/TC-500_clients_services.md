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

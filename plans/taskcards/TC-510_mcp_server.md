---
id: TC-510
title: "MCP server"
status: Done
owner: "MCP_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-300
allowed_paths:
  - src/launch/mcp/**
  - src/launch/orchestrator/mcp_adapter.py
  - tests/unit/mcp/test_tc_510_server.py
  - reports/agents/**/TC-510/**
evidence_required:
  - reports/agents/<agent>/TC-510/report.md
  - reports/agents/<agent>/TC-510/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-510 — MCP server

## Objective
Implement the MCP server surface (tools + transport) so external orchestrators/clients can trigger runs, inspect artifacts, and validate outputs via stable, schema-backed endpoints.

## Required spec references
- specs/14_mcp_endpoints.md
- specs/24_mcp_tool_schemas.md
- specs/11_state_and_events.md
- specs/19_toolchain_and_ci.md

## Scope
### In scope
- MCP server entrypoint and routing
- Tool registration and schema-backed request/response validation
- Read-only artifact access APIs (no file mutation outside RUN_DIR)
- Auth token handling via env var (if configured)

### Out of scope
- Business logic of workers (MCP delegates to orchestrator runner)
- UI/Frontend

## Inputs
- MCP config from run_config (`mcp.enabled`, host/port, auth token env)
- Schemas for MCP tool payloads (`specs/24_mcp_tool_schemas.md`)
- Orchestrator runner callable (from TC-300)

## Outputs
- MCP server module(s) under `src/launch/mcp/**`
- Tool implementations matching the documented endpoint contracts
- Tests for tool schema validation and auth behavior

## Allowed paths

- `src/launch/mcp/**`
- `src/launch/orchestrator/mcp_adapter.py`
- `tests/unit/mcp/test_tc_510_server.py`
- `reports/agents/**/TC-510/**`## Implementation steps
1) Implement server bootstrap (host/port, lifecycle, logging).
2) Implement tool registration with schema validation:
   - validate input payloads
   - validate output payloads (where defined)
3) Implement minimum tools:
   - start run
   - get run status
   - fetch artifact
   - validate run outputs
4) Auth:
   - if auth env configured: require token header
   - otherwise run unauthenticated for local-only use
5) Tests:
   - schema validation for each tool
   - auth-required vs not-required behavior

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.mcp.server --port 8787 &
curl http://localhost:8787/health
```

**Expected artifacts:**
- src/launch/mcp/server.py
- src/launch/mcp/tools/*.py

**Success criteria:**
- [ ] Server starts
- [ ] Health endpoint responds
- [ ] Tools registered

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (orchestrator run_loop)
- Downstream: MCP clients (Claude, etc.)
- Contracts: specs/14_mcp_endpoints.md, specs/24_mcp_tool_schemas.md

## Failure modes

### Failure mode 1: Service initialization fails due to missing dependencies
**Detection:** ImportError on service startup; required packages not installed; version conflicts
**Resolution:** Verify dependencies in pyproject.toml; check lockfile; install missing packages
**Spec/Gate:** specs/19_toolchain_and_ci.md, specs/25_frameworks_and_dependencies.md

### Failure mode 2: Service endpoint returns errors or timeouts
**Detection:** HTTP 500 errors from endpoints; request timeouts; connection refused
**Resolution:** Check service logs; verify endpoint routing; test with curl or pytest
**Spec/Gate:** specs/16_local_telemetry_api.md, specs/21_worker_contracts.md

### Failure mode 3: Service state is not persisted correctly
**Detection:** Service restart loses state; database writes fail; state inconsistencies
**Resolution:** Verify atomic writes; check database transactions commit; test recovery scenarios
**Spec/Gate:** specs/11_state_and_events.md, specs/10_determinism_and_caching.md


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
  - MCP server + tools
- Tests:
  - schema + auth tests
- Reports (required):
  - reports/agents/<agent>/TC-510/report.md
  - reports/agents/<agent>/TC-510/self_review.md

## Acceptance checks
- [ ] MCP tools match `specs/14_mcp_endpoints.md` and schemas
- [ ] Tool input validation rejects unknown keys
- [ ] Artifact fetch is read-only and constrained to RUN_DIR
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

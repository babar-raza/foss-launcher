---
id: TC-510
title: "MCP server"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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
- src/launch/mcp/**
- src/launch/orchestrator/mcp_adapter.py
- tests/unit/mcp/test_tc_510_server.py
- reports/agents/**/TC-510/**
## Implementation steps
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

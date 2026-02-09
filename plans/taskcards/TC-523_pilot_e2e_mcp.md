---
id: TC-523
title: "Pilot E2E MCP execution and determinism verification"
status: Done
owner: "TELEMETRY_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-520
  - TC-510
  - TC-560
allowed_paths:
  - scripts/run_pilot_e2e_mcp.py
  - tests/e2e/test_tc_523_pilot_mcp.py
  - reports/agents/**/TC-523/**
evidence_required:
  - reports/agents/<agent>/TC-523/report.md
  - reports/agents/<agent>/TC-523/self_review.md
  - artifacts/pilot_e2e_mcp_report.json
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-523 — Pilot E2E MCP execution and determinism verification

## Objective
Implement and execute a complete end-to-end pilot run via MCP tools, comparing outputs to expected artifacts and verifying determinism through repeated execution.

## Required spec references
- specs/13_pilots.md
- specs/14_mcp_endpoints.md
- specs/24_mcp_tool_schemas.md
- specs/10_determinism_and_caching.md

## Scope
### In scope
- MCP-based pilot execution script
- Calling MCP tools: launch_start_run, launch_get_status, launch_get_artifact
- Expected artifact comparison
- Determinism verification (run twice via MCP, compare checksums)

### Out of scope
- CLI-based execution (see TC-522)
- MCP server implementation (see TC-510)
- New pilot creation

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue and stop.
- **Write fence:** MAY ONLY change files under Allowed paths.
- **Determinism:** MCP outputs MUST be identical across runs.
- **Evidence:** MCP call/response logs must be recorded.

## Preconditions / dependencies
- TC-520: Pilot infrastructure exists
- TC-510: MCP server running with all tools
- TC-560: Determinism harness available
- Pinned pilot configs exist

## Inputs
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`
- `specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json`
- `specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json`
- MCP server endpoint (default: `http://localhost:8787`)

## Outputs
- `scripts/run_pilot_e2e_mcp.py` — MCP pilot execution script
- `tests/e2e/test_tc_523_pilot_mcp.py` — E2E test
- `artifacts/pilot_e2e_mcp_report.json` — execution report

## Allowed paths

- `scripts/run_pilot_e2e_mcp.py`
- `tests/e2e/test_tc_523_pilot_mcp.py`
- `reports/agents/**/TC-523/**`## Implementation steps
1) Create `scripts/run_pilot_e2e_mcp.py`:
   - Accept `--pilot`, `--mcp-url` arguments
   - Load run_config from pilot directory
   - Call `launch_start_run` MCP tool
   - Poll `launch_get_status` until completion
   - Call `launch_get_artifact` for page_plan.json and validation_report.json
   - Compare to expected artifacts
   - Run twice and compare checksums
   - Generate JSON report

2) Create E2E test `tests/e2e/test_tc_523_pilot_mcp.py`:
   - Start MCP server (or use existing)
   - Call `run_pilot_e2e_mcp.py`
   - Assert artifact comparison passes
   - Assert determinism passes

3) Document MCP call sequence in agent report

## Test plan
- Unit tests: N/A (E2E test taskcard)
- Integration tests: `tests/e2e/test_tc_523_pilot_mcp.py`
- Determinism proof: Two MCP-based runs produce identical artifacts

## E2E verification
**Concrete command(s) to run:**
```bash
# Start MCP server in background
python -m launch.mcp.server --port 8787 &
# Execute pilot via MCP tools
python scripts/run_pilot_e2e_mcp.py --pilot pilot-aspose-3d-foss-python --mcp-url http://localhost:8787 --output artifacts/pilot_e2e_mcp_report.json
python -m pytest tests/e2e/test_tc_523_pilot_mcp.py -v
```

**Expected artifacts:**
- artifacts/pilot_e2e_mcp_report.json (pass/fail, MCP call log, checksums)
- MCP response for page_plan.json matches expected
- MCP response for validation_report.json matches expected

**Success criteria:**
- [ ] MCP server responds to all required tools
- [ ] Pilot runs to completion via MCP
- [ ] Artifacts match expected (page_plan, validation_report)
- [ ] Two consecutive MCP runs produce identical outputs

> This taskcard IS the E2E harness for MCP execution.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-510 (MCP server tools invoke orchestrator)
- Downstream: MCP clients can execute full pipeline
- Contracts: specs/24_mcp_tool_schemas.md response shapes

## Failure modes

### Failure mode 1: MCP server not running causing pilot script to hang or timeout
**Detection:** run_pilot_e2e_mcp.py hangs indefinitely; connection timeout to localhost:8787; no MCP response; script doesn't fail gracefully
**Resolution:** Add MCP server health check before pilot execution; verify HTTP GET to /health or /status endpoint succeeds; implement connection timeout (e.g., 5s); emit clear error message if MCP server unreachable; document MCP server startup requirement in script help; suggest `python -m launch.mcp.server --port 8787 &` in error message
**Spec/Gate:** specs/14_mcp_endpoints.md (MCP server contract), TC-510 (MCP server implementation)

### Failure mode 2: MCP tool schema mismatch causing pilot execution to fail
**Detection:** launch_start_run MCP tool returns error; schema validation fails; pilot run aborts with MCP tool invocation error; response doesn't match specs/24_mcp_tool_schemas.md
**Resolution:** Review MCP tool schemas in specs/24_mcp_tool_schemas.md; verify run_pilot_e2e_mcp.py sends request matching tool input schema; check MCP server response validates against tool output schema; ensure run_config fields match expected structure; update MCP client code if schema evolved; test with schema validator before MCP call
**Spec/Gate:** specs/24_mcp_tool_schemas.md (tool schemas), specs/14_mcp_endpoints.md (MCP protocol), Gate C (schema validation)

### Failure mode 3: MCP call log missing or incomplete breaking audit trail
**Detection:** pilot_e2e_mcp_report.json doesn't include MCP call/response log; unable to debug MCP failures; unclear which tools called in what order; audit trail incomplete
**Resolution:** Review MCP call logging in run_pilot_e2e_mcp.py; ensure each MCP tool invocation logged with timestamp, tool name, input params, response body, and status code; verify call log included in pilot_e2e_mcp_report.json; apply json.dumps(sort_keys=True) for deterministic log formatting; document MCP call log structure
**Spec/Gate:** specs/14_mcp_endpoints.md (observability requirements), specs/11_state_and_events.md (event logging), TC-580 (evidence bundle)

### Failure mode 4: MCP polling for run completion doesn't timeout causing infinite loop
**Detection:** launch_get_status polled indefinitely; run never reaches terminal state (completed/failed); script hangs; no timeout enforced; CI job times out
**Resolution:** Add polling timeout to run_pilot_e2e_mcp.py (e.g., 300s max); implement backoff delay between status polls (e.g., 1s, 2s, 4s up to 10s); check for terminal states (completed, failed, aborted); emit BLOCKER issue if timeout exceeded; log polling attempts and status transitions; fail gracefully with clear timeout error message
**Spec/Gate:** specs/14_mcp_endpoints.md (async execution contract), specs/28_coordination_and_handoffs.md (polling patterns), TC-600 (retry and backoff)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Tests include positive and negative cases
- [ ] E2E verification command documented and tested
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code: `scripts/run_pilot_e2e_mcp.py`
- Tests: `tests/e2e/test_tc_523_pilot_mcp.py`
- Docs/specs/plans: None
- Reports (required):
  - reports/agents/__AGENT__/TC-523/report.md
  - reports/agents/__AGENT__/TC-523/self_review.md

## Acceptance checks
- [ ] MCP E2E script exists
- [ ] Script calls MCP tools correctly
- [ ] Artifact comparison works
- [ ] Determinism verified
- [ ] E2E test passes

## Self-review
Use `reports/templates/self_review_12d.md`.

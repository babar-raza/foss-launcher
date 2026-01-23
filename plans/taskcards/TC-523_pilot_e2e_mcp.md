---
id: TC-523
title: "Pilot E2E MCP execution and determinism verification"
status: Ready
owner: "unassigned"
updated: "2026-01-23"
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
- scripts/run_pilot_e2e_mcp.py
- tests/e2e/test_tc_523_pilot_mcp.py
- reports/agents/**/TC-523/**

## Implementation steps
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

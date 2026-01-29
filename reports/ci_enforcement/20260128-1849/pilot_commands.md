# Step 4 Pilot Commands — 20260128-1849

## Overview
This document contains the exact commands to execute TC-522 and TC-523 pilots.
DO NOT run these commands now — they are documented for Step 4 execution.

## TC-522: Pilot E2E CLI Execution

### Purpose
Validate complete end-to-end pilot execution via CLI with determinism proof.

### Commands
```bash
# Run pilot E2E via CLI
python scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python --output artifacts/pilot_e2e_cli_report.json

# Run E2E test
python -m pytest tests/e2e/test_tc_522_pilot_cli.py -v
```

### Expected Artifacts
- `artifacts/pilot_e2e_cli_report.json` — Pass/fail status, checksums
- `artifacts/page_plan.json` — Must match `specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json`
- `artifacts/validation_report.json` — Must match `specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json`

### Success Criteria
- [ ] Pilot runs to completion
- [ ] Actual page_plan.json matches expected_page_plan.json
- [ ] Actual validation_report.json matches expected_validation_report.json
- [ ] Two consecutive runs produce identical outputs (determinism)

### Source Taskcard
[TC-522_pilot_e2e_cli.md](../../../plans/taskcards/TC-522_pilot_e2e_cli.md)

---

## TC-523: Pilot E2E MCP Execution

### Purpose
Validate complete end-to-end pilot execution via MCP tools with determinism proof.

### Commands
```bash
# Start MCP server in background
python -m launch.mcp.server --port 8787 &

# Execute pilot via MCP tools
python scripts/run_pilot_e2e_mcp.py --pilot pilot-aspose-3d-foss-python --mcp-url http://localhost:8787 --output artifacts/pilot_e2e_mcp_report.json

# Run E2E test
python -m pytest tests/e2e/test_tc_523_pilot_mcp.py -v
```

### Expected Artifacts
- `artifacts/pilot_e2e_mcp_report.json` — Pass/fail, MCP call log, checksums
- MCP response for `page_plan.json` matches expected
- MCP response for `validation_report.json` matches expected

### Success Criteria
- [ ] MCP server responds to all required tools
- [ ] Pilot runs to completion via MCP
- [ ] Artifacts match expected (page_plan, validation_report)
- [ ] Two consecutive MCP runs produce identical outputs

### Source Taskcard
[TC-523_pilot_e2e_mcp.md](../../../plans/taskcards/TC-523_pilot_e2e_mcp.md)

---

## Execution Order (When Step 4 Begins)
1. **First**: Run TC-522 CLI pilot
2. **Second**: Run TC-523 MCP pilot
3. **Third**: Validate both reports show 100% determinism and artifact matching

## Notes
- Both pilots use the same pinned config: `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`
- Determinism is verified by running each pilot twice and comparing checksums
- All outputs must be bitwise identical across runs
- MCP server must be started before TC-523 execution

## Prerequisites
- [x] CI enforcement complete (this step)
- [x] Main branch at 21/21 gates + 0 test failures
- [ ] Ready to execute pilots (Step 4)

## Report Location
Results from pilot execution should be written to:
- `reports/pilot_execution/<TIMESTAMP>/tc522_results.md`
- `reports/pilot_execution/<TIMESTAMP>/tc523_results.md`

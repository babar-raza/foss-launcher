# Taskcard Evidence Audit Report

## Summary

- **Total Done taskcards**: 46
- **Complete evidence**: 36
- **Incomplete evidence**: 10
- **Compliance rate**: 78.3%
- **Orphaned evidence dirs**: 11

## Incomplete Evidence

### TC-100: Bootstrap repo for deterministic implementation
**Missing**: Test output: python -m pytest -q, Import check: python -c 'import launch'

### TC-200: Schemas and IO foundations
**Missing**: Test output: stable JSON bytes test, Test output: run_config validation tests

### TC-250: Shared libraries governance and single-writer enforcement
**Missing**: Test output: model validation tests

### TC-511: MCP quickstart from product URL (launch_start_run_from_product_url)
**Missing**: Test output: MCP tool responds with run_id for valid product URL

### TC-512: MCP quickstart from GitHub repo URL (launch_start_run_from_github_repo_url)
**Missing**: Test output: MCP tool responds with run_id for valid GitHub repo URL, Test output: MCP tool returns INVALID_INPUT with missing_fields for ambiguous repo

### TC-522: Pilot E2E CLI execution and determinism verification
**Missing**: pilot_e2e_cli_report.json

### TC-523: Pilot E2E MCP execution and determinism verification
**Missing**: pilot_e2e_mcp_report.json

### TC-601: Windows Reserved Names Validation Gate
**Missing**: directory TC-601/ not found

### TC-602: Specs README Navigation Update
**Missing**: directory TC-602/ not found

### TC-709: Fix time-sensitive test in test_tc_523_metadata_endpoints
**Missing**: directory TC-709/ not found

## Orphaned Evidence

The following evidence directories have no matching taskcard:

- `TELEMETRY_AGENT/TC-521`
- `VSCODE_AGENT/TC-634`
- `VSCODE_AGENT/TC-636`
- `VSCODE_AGENT/TC-638`
- `VSCODE_AGENT/TC-639`
- `VSCODE_AGENT/TC-640`
- `VSCODE_AGENT/TC-642`
- `VSCODE_AGENT/TC-643`
- `VSCODE_AGENT/TC-670`
- `VSCODE_AGENT/TC-671`
- `VSCODE_AGENT/TC-672`

## Detailed Results

| Taskcard | Status | Owner | Missing |
|---|---|---|---|
| TC-100 | [FAIL] Incomplete | FOUNDATION_AGENT | Test output: python -m pytest -q, Import check: python -c 'import launch' |
| TC-200 | [FAIL] Incomplete | FOUNDATION_AGENT | Test output: stable JSON bytes test, Test output: run_config validation tests |
| TC-201 | [OK] Complete | FOUNDATION_AGENT | - |
| TC-250 | [FAIL] Incomplete | MODELS_AGENT | Test output: model validation tests |
| TC-300 | [OK] Complete | ORCHESTRATOR_AGENT | - |
| TC-400 | [OK] Complete | W1_AGENT | - |
| TC-401 | [OK] Complete | W1_AGENT | - |
| TC-402 | [OK] Complete | W1_AGENT | - |
| TC-403 | [OK] Complete | W1_AGENT | - |
| TC-404 | [OK] Complete | W1_AGENT | - |
| TC-410 | [OK] Complete | W2_AGENT | - |
| TC-411 | [OK] Complete | W2_AGENT | - |
| TC-412 | [OK] Complete | W2_AGENT | - |
| TC-413 | [OK] Complete | W2_AGENT | - |
| TC-420 | [OK] Complete | W3_AGENT | - |
| TC-421 | [OK] Complete | W3_AGENT | - |
| TC-422 | [OK] Complete | W3_AGENT | - |
| TC-430 | [OK] Complete | W4_AGENT | - |
| TC-440 | [OK] Complete | W5_AGENT | - |
| TC-450 | [OK] Complete | W6_AGENT | - |
| TC-460 | [OK] Complete | W7_AGENT | - |
| TC-470 | [OK] Complete | W8_AGENT | - |
| TC-480 | [OK] Complete | W9_AGENT | - |
| TC-500 | [OK] Complete | CLIENTS_AGENT | - |
| TC-510 | [OK] Complete | MCP_AGENT | - |
| TC-511 | [FAIL] Incomplete | MCP_AGENT | Test output: MCP tool responds with run_id for valid product URL |
| TC-512 | [FAIL] Incomplete | MCP_AGENT | Test output: MCP tool responds with run_id for valid GitHub repo URL, Test output: MCP tool returns INVALID_INPUT with missing_fields for ambiguous repo |
| TC-520 | [OK] Complete | TELEMETRY_AGENT | - |
| TC-522 | [FAIL] Incomplete | TELEMETRY_AGENT | pilot_e2e_cli_report.json |
| TC-523 | [FAIL] Incomplete | TELEMETRY_AGENT | pilot_e2e_mcp_report.json |
| TC-530 | [OK] Complete | CLI_AGENT | - |
| TC-540 | [OK] Complete | CONTENT_AGENT | - |
| TC-550 | [OK] Complete | CONTENT_AGENT | - |
| TC-560 | [OK] Complete | DETERMINISM_AGENT | - |
| TC-570 | [OK] Complete | W7_AGENT | - |
| TC-571 | [OK] Complete | W7_AGENT | - |
| TC-580 | [OK] Complete | OBSERVABILITY_AGENT | - |
| TC-590 | [OK] Complete | SECURITY_AGENT | - |
| TC-600 | [OK] Complete | RESILIENCE_AGENT | - |
| TC-601 | [FAIL] Incomplete | hygiene-agent | directory TC-601/ not found |
| TC-602 | [FAIL] Incomplete | docs-agent | directory TC-602/ not found |
| TC-700 | [OK] Complete | TEMPLATES_AGENT | - |
| TC-701 | [OK] Complete | PLANNER_AGENT | - |
| TC-702 | [OK] Complete | VALIDATOR_AGENT | - |
| TC-703 | [OK] Complete | PILOT_OPS_AGENT | - |
| TC-709 | [FAIL] Incomplete | HYGIENE_AGENT | directory TC-709/ not found |


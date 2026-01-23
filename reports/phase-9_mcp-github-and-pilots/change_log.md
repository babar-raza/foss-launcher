# Phase 9 — Change Log

> **Purpose**: Track all changes made during Phase 9: MCP GitHub Quickstart + Pilot Canonicalization
> **Started**: 2026-01-23

## Summary

Two blockers addressed:
1. MCP must support GitHub repo URL-only quickstart (public repo URL)
2. Pilots must be canonicalized to `specs/pilots/**` everywhere

---

## Work Item A — Pilots Canonicalization

### A1: Canonicalize pilots to specs/pilots/**

| File | Change |
|------|--------|
| `specs/pilot-blueprint.md` | Updated repo layout section to use `specs/pilots/` as canonical |
| `plans/taskcards/TC-520_pilots_and_regression.md` | Updated to reference `specs/pilots/**` as canonical source |
| `plans/implementation_master_checklist.md` | Fixed pilot config path from `configs/pilots/` to `specs/pilots/` |

### A2: Fix TC-520 vs TC-522/523 mismatch

| File | Change |
|------|--------|
| `plans/taskcards/TC-520_pilots_and_regression.md` | Added `specs/pilots/**` to allowed_paths, clarified it reads from there |

### A3: Add pilots contract validator

| File | Change |
|------|--------|
| `tools/validate_pilots_contract.py` | NEW: Validates pilots canonical path consistency |
| `tools/validate_swarm_ready.py` | Added Gate G for pilots contract validation |

---

## Work Item B — MCP GitHub Quickstart

### B1: Rename existing quickstart tool

| File | Change |
|------|--------|
| `specs/14_mcp_endpoints.md` | Renamed `launch_start_run_from_url` to `launch_start_run_from_product_url` |
| `specs/24_mcp_tool_schemas.md` | Renamed tool + added backward-compatible alias note |
| `plans/taskcards/TC-511_mcp_quickstart_url.md` | Updated to use new explicit name |
| `plans/taskcards/INDEX.md` | Updated TC-511 description |
| `plans/traceability_matrix.md` | Updated to include TC-512 |

### B2: Add GitHub repo URL quickstart

| File | Change |
|------|--------|
| `specs/14_mcp_endpoints.md` | Added `launch_start_run_from_github_repo_url` tool spec |
| `specs/24_mcp_tool_schemas.md` | Added full schema for GitHub quickstart tool |

### B3: Create TC-512 taskcard

| File | Change |
|------|--------|
| `plans/taskcards/TC-512_mcp_quickstart_github_repo_url.md` | NEW: Taskcard for GitHub URL quickstart |
| `plans/taskcards/INDEX.md` | Added TC-512 entry |
| `plans/traceability_matrix.md` | Added TC-512 to MCP implementation coverage |

### B4: Add MCP schema validation

| File | Change |
|------|--------|
| `tools/validate_mcp_contract.py` | NEW: Validates both MCP quickstart tools exist in specs |
| `tools/validate_swarm_ready.py` | Added Gate H for MCP contract validation |

---

## Work Item C — Fix Master Checklist

| File | Change |
|------|--------|
| `plans/implementation_master_checklist.md` | Fixed `tools/validate_spec_pack.py` → `scripts/validate_spec_pack.py` |
| `plans/implementation_master_checklist.md` | Fixed `configs/pilots/` → `specs/pilots/` |

---

## Gates Run

All gates passed. See `gate_outputs/` for raw output.

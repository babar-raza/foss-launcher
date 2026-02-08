# Duplicate Branch Detection

## Summary

Detected **1 duplicate pair** with identical tip SHA:

| Branch | Tip SHA | Status |
|--------|---------|--------|
| `feat/pilot-e2e-golden-3d-20260129` | `c666914` | **KEEP** (better name: feat prefix) |
| `fix/pilot1-w4-ia-planner-20260130` | `c666914` | **DELETE** (duplicate) |

## All Branch Tips

| Branch | Tip SHA | Subject |
|--------|---------|---------|
| `feat/golden-2pilots-20260130` | `d582eca` | fix: Handle example_inventory as list or dict in W4 |
| `feat/pilot-e2e-golden-3d-20260129` | `c666914` | feat: Phase N0 taskcard hygiene + golden capture prep (TC-633) |
| `feat/pilot1-hardening-vfv-20260130` | `4bed867` | TC-681: Fix W4 path construction (family + subdomain) |
| `fix/pilot1-w4-ia-planner-20260130` | `c666914` | feat: Phase N0 taskcard hygiene + golden capture prep (TC-633) |

## Decision

- We will **NOT merge both** branches with SHA `c666914`
- Will keep `feat/pilot-e2e-golden-3d-20260129` (feat prefix is better naming convention)
- Will mark `fix/pilot1-w4-ia-planner-20260130` for deletion

## Unique Branches to Analyze (3 branches)

1. `feat/golden-2pilots-20260130` (d582eca)
2. `feat/pilot-e2e-golden-3d-20260129` (c666914)
3. `feat/pilot1-hardening-vfv-20260130` (4bed867)

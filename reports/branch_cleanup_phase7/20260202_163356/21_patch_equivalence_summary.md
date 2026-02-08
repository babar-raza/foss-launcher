# Patch Equivalence Analysis Summary

## Result

**All 3 unique branches contain work NOT in main** - all are candidates for integration.

| Branch | PlusCount | MinusCount | Decision |
|--------|-----------|------------|----------|
| `feat/golden-2pilots-20260130` | 12 | 0 | **MERGE** - Contains unique W4 fixes and golden process work |
| `feat/pilot-e2e-golden-3d-20260129` | 2 | 0 | **MERGE** - Contains offline PR manager and taskcard hygiene |
| `feat/pilot1-hardening-vfv-20260130` | 1 | 0 | **MERGE** - Contains TC-681 W4 path fix |
| `fix/pilot1-w4-ia-planner-20260130` | N/A | N/A | **DELETE** - Duplicate of feat/pilot-e2e-golden-3d-20260129 |

## Interpretation

- **PlusCount = 0** → Branch is patch-equivalent to main → Safe to delete
- **PlusCount > 0** → Branch has real unique work → Candidate for integration

## Analysis Details

### feat/golden-2pilots-20260130 (12 unique commits)
- Contains W4 fixes (path construction, run_config handling, inventory handling)
- Golden process foundation work
- FOSS repo clone workarounds
- Taskcard formalization (TC-700-703)

### feat/pilot-e2e-golden-3d-20260129 (2 unique commits)
- Offline-safe PR manager for pilot E2E (TC-631)
- Phase N0 taskcard hygiene and golden capture prep (TC-633)

### feat/pilot1-hardening-vfv-20260130 (1 unique commit)
- TC-681: W4 path construction fix (family + subdomain)

## Next Steps

All 3 branches require detailed inspection (Step 3) to understand their changes before integration.

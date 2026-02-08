# Integration Strategy

## TC-681 Overlap Detected

**CRITICAL**: Two branches both address TC-681 with DIFFERENT implementations:
- `feat/pilot1-hardening-vfv-20260130` commit `4bed867`: "TC-681: Fix W4 path construction (family + subdomain)"
- `feat/golden-2pilots-20260130` commit `ccf1cf4`: "TC-681: Fix W4 path construction (family + subdomain)"

Git cherry shows both as unique patches (`+`), meaning different implementations of the same fix.

## Proposed Integration Order

### Phase 1: Integrate pilot1-hardening (Most Focused)
- **Branch**: `feat/pilot1-hardening-vfv-20260130`
- **Commits**: 1 (`4bed867`)
- **Method**: Cherry-pick
- **Rationale**: Single focused commit for TC-681, easiest to integrate first

### Phase 2: Integrate pilot-e2e (No TC-681 Overlap)
- **Branch**: `feat/pilot-e2e-golden-3d-20260129`
- **Commits**: 2 (`795ef77`, `c666914`)
  - `795ef77`: TC-631 offline-safe PR manager
  - `c666914`: TC-633 taskcard hygiene
- **Method**: Cherry-pick
- **Rationale**: No overlap with TC-681, adds W9 PR manager feature

### Phase 3: Integrate golden-2pilots (Handle TC-681 Conflict)
- **Branch**: `feat/golden-2pilots-20260130`
- **Commits**: 12 (including `ccf1cf4` TC-681)
- **Method**: Cherry-pick, but skip `ccf1cf4` if it conflicts (already have TC-681 from pilot1-hardening)
- **Rationale**: Largest branch, includes template packs and golden process foundation

## Alternative: Analyze TC-681 Commits First

Before proceeding, we could:
1. Compare patches between `4bed867` and `ccf1cf4` to understand which is the better fix
2. Choose one implementation and skip the other

## Decision: Proceed with Order Above

Integrate pilot1-hardening → pilot-e2e → golden-2pilots (handling TC-681 conflict)

If golden-2pilots `ccf1cf4` cherry-pick fails due to TC-681 conflict:
- **Action**: Skip `ccf1cf4` commit (already have TC-681 fix)
- **Justification**: pilot1-hardening TC-681 fix applied first
- **Document**: Note skipped commit in apply log

# Evidence Bundle Manifest — 20260128-1849

## Bundle Information
- **Bundle Name**: main_ci_evidence_20260128-1849.tar.gz
- **Created**: 2026-01-28 18:49 (Asia/Karachi)
- **Purpose**: Complete evidence chain for main branch greenness and CI enforcement

## Included Evidence Folders

### 1. Clean-Room Green Proof
**Path**: `reports/main_env_green/20260128-1615/`
**Purpose**: Proves main is green in a completely fresh environment

**Key Files**:
- `clean_room_steps.md` — Step-by-step procedure
- `gate_outputs.txt` — Full 21/21 gates output
- `gate_outputs.md` — Gates summary
- `test_outputs.txt` — Full pytest output (0 failures)
- `test_outputs.md` — Test summary
- `fixes.md` — Any fixes applied
- `final_claim.md` — Green certification claim

**Validation Timestamp**: 2026-01-28 16:15 (Asia/Karachi)

### 2. Integration Merge Proof
**Path**: `reports/merge_to_main/20260128-0837/`
**Purpose**: Proves fix/env-gates branch successfully merged to main with full greenness

**Key Files**:
- `summary.md` — Complete merge report
- `baseline_sync.md` — Pre-merge synchronization
- `gate_outputs.md` — Post-merge gate validation
- `conflicts_and_fixes.md` — Conflict resolution log
- `final_main_e2e.md` — Final E2E validation
- `wave_merge_log.md` — Wave merge execution log
- `state.json` — Machine-readable merge state
- `checkpoints/` — Incremental validation checkpoints

**Merge Timestamp**: 2026-01-28 08:37 (Asia/Karachi)
**Merge Commit**: 4b5efc1 (Merge fix/env-gates-20260128-1615: Achieve full main greenness)

### 3. CI Enforcement
**Path**: `reports/ci_enforcement/20260128-1849/`
**Purpose**: Documents GitHub Actions CI workflow that enforces main greenness

**Key Files**:
- `plan.md` — CI enforcement plan and timeline
- `workflow_diff.md` — Complete diff of CI workflow changes
- `workflow_paths.md` — CI workflow structure and file paths
- `pilot_commands.md` — TC-522 and TC-523 pilot commands (prepared for Step 4)
- `bundle_manifest.md` — This file

**CI Enforcement Timestamp**: 2026-01-28 18:49 (Asia/Karachi)
**Workflow File**: `.github/workflows/ci.yml`

## Evidence Chain

This bundle represents a complete evidence chain:

1. **Step 1** (20260128-1615): Clean-room validation proves main is green
2. **Step 2** (20260128-0837): Integration merge proves branch merge maintains greenness
3. **Step 3** (20260128-1849): CI enforcement ensures main cannot regress

## Bundle Contents Summary

### Total Files
```
reports/main_env_green/20260128-1615/
  - clean_room_steps.md
  - final_claim.md
  - fixes.md
  - gate_outputs.md
  - gate_outputs.txt (58KB)
  - test_outputs.md
  - test_outputs.txt (14KB)

reports/merge_to_main/20260128-0837/
  - summary.md
  - baseline_sync.md
  - gate_outputs.md
  - conflicts_and_fixes.md
  - final_main_e2e.md
  - wave_merge_log.md
  - state.json
  - checkpoints/ (directory with incremental validation)

reports/ci_enforcement/20260128-1849/
  - plan.md
  - workflow_diff.md
  - workflow_paths.md
  - pilot_commands.md
  - bundle_manifest.md
```

### Verification Checksums
```bash
# Verify bundle integrity after extraction
find reports/main_env_green/20260128-1615/ -type f -exec sha256sum {} \;
find reports/merge_to_main/20260128-0837/ -type f -exec sha256sum {} \;
find reports/ci_enforcement/20260128-1849/ -type f -exec sha256sum {} \;
```

## Usage

### Extract Bundle
```bash
tar -xzf main_ci_evidence_20260128-1849.tar.gz
```

### Verify Evidence Chain
```bash
# 1. Review clean-room proof
cat reports/main_env_green/20260128-1615/final_claim.md

# 2. Review integration merge
cat reports/merge_to_main/20260128-0837/summary.md

# 3. Review CI enforcement
cat reports/ci_enforcement/20260128-1849/plan.md
```

## Next Steps (Not in Bundle)
After CI enforcement, Step 4 will execute:
- TC-522: CLI pilot E2E execution
- TC-523: MCP pilot E2E execution

Commands documented in: `reports/ci_enforcement/20260128-1849/pilot_commands.md`

## Bundle Location
**Relative Path**: `reports/bundles/20260128-1849/main_ci_evidence_20260128-1849.tar.gz`
**Absolute Path**: (will be printed after bundle creation)

## Certification
This evidence bundle certifies:
- ✅ Main branch passes 21/21 gates (clean-room validated)
- ✅ Main branch passes all tests with 0 failures
- ✅ Integration merge maintained greenness
- ✅ CI workflow enforces gates + tests on all main pushes/PRs
- ✅ Complete audit trail from validation to enforcement

Created by: CI Enforcement Supervisor
Date: 2026-01-28 18:49 (Asia/Karachi)

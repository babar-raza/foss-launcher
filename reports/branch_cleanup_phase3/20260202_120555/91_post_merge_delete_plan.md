# Post-Merge Branch Deletion Plan (Phase 3)

**Generated:** 2026-02-02
**Status:** READY TO EXECUTE (after merge completion + tests pass)

---

## ⚠️ CRITICAL PRECONDITIONS

**DO NOT execute any deletions until ALL of these are true:**

- [ ] All merge conflicts resolved (16/16)
- [ ] Consolidation merge committed
- [ ] All tests pass on consolidation branch
- [ ] impl/tc300 merged to consolidation
- [ ] feat/golden-2pilots-20260201 merged to consolidation
- [ ] All tests pass on final consolidation
- [ ] Consolidation branch merged to main
- [ ] All tests pass on main
- [ ] Main pushed to remote (if using remote)
- [ ] Backups verified (Phase 1 bundle + tags)

**ONLY proceed when ALL checkboxes are checked.**

---

## Deletion Summary

**Total branches to delete:** 47
**Branches to keep:** 5

**Deletion strategy:** Progressive (start safe, end comprehensive)

---

## Stage 1: Duplicates (Safest - 2 branches)

These are exact copies by SHA, safe to delete even before merge:

```bash
# Group 1: SHA d1d440f
# KEEP: feat/tc902_hygiene_20260201
git branch -D feat/tc902_w4_impl_20260201

# Group 2: SHA c666914
# KEEP: feat/pilot-e2e-golden-3d-20260129
git branch -D fix/pilot1-w4-ia-planner-20260130
```

**Risk:** NONE (exact duplicates)
**Timing:** Can delete anytime, but recommend waiting until after merge for consistency

---

## Stage 2: Contained in fix/env-gates (42 branches)

These branches have 0 unique patches vs fix/env-gates (proven by Phase 2 analysis).
Safe to delete AFTER fix/env-gates is merged to main.

### TC-* Feature Branches (40)

```bash
git branch -D \
  feat/TC-100-bootstrap-repo \
  feat/TC-200-schemas-and-io \
  feat/TC-201-emergency-mode \
  feat/TC-250-shared-libs-governance \
  feat/TC-300-orchestrator-langgraph \
  feat/TC-400-repo-scout \
  feat/TC-401-clone-resolve-shas \
  feat/TC-402-fingerprint \
  feat/TC-403-discover-docs \
  feat/TC-404-discover-examples \
  feat/TC-410-facts-builder \
  feat/TC-411-extract-claims \
  feat/TC-412-map-evidence \
  feat/TC-413-detect-contradictions \
  feat/TC-420-snippet-curator \
  feat/TC-421-extract-doc-snippets \
  feat/TC-422-extract-code-snippets \
  feat/TC-430-ia-planner \
  feat/TC-440-section-writer \
  feat/TC-450-linker-and-patcher \
  feat/TC-460-validator \
  feat/TC-470-fixer \
  feat/TC-480-pr-manager \
  feat/TC-500-clients-services \
  feat/TC-510-mcp-server-setup \
  feat/TC-511-mcp-tool-registration \
  feat/TC-512-mcp-tool-handlers \
  feat/TC-520-telemetry-api-setup \
  feat/TC-521-telemetry-run-endpoints \
  feat/TC-522-telemetry-batch-upload \
  feat/TC-523-telemetry-metadata-endpoints \
  feat/TC-530-cli-entrypoints \
  feat/TC-540-content-path-resolver \
  feat/TC-550-hugo-config \
  feat/TC-560-determinism-harness \
  feat/TC-570-extended-gates \
  feat/TC-571-perf-security-gates \
  feat/TC-580-observability \
  feat/TC-590-security-handling \
  feat/TC-600-failure-recovery
```

### Integration Branches (2)

```bash
git branch -D \
  integrate/main-e2e-20260128-0837 \
  fix/main-green-20260128-1505
```

**Risk:** LOW (patch-proven containment via Phase 2 analysis)
**Evidence:** `reports/branch_cleanup_phase2/20260202_183400/22_allbranches_vs_candidates.csv`

---

## Stage 3: The Merged Coverage Set (3 branches)

After the consolidation is in main, delete the feature branches themselves:

```bash
# Delete after fix/env-gates merged to main
git branch -D fix/env-gates-20260128-1615

# Delete after impl/tc300 merged to main
git branch -D impl/tc300-wire-orchestrator-20260128

# Delete after current work merged to main (if work is complete)
git branch -D feat/golden-2pilots-20260201
```

**Risk:** NONE (work is in main)

---

## Stage 4: Consolidation Branch (1 branch)

After merging consolidation to main:

```bash
# Delete the consolidation branch itself
git branch -D integrate/consolidation_20260202_120555
```

**Risk:** NONE (work is in main)

---

## Branches to KEEP (5-9 branches)

### Always Keep

1. **main** - NEVER DELETE

### Evaluate Separately (4 uncovered pilot branches)

2. **feat/golden-2pilots-20260130** (12 patches different from current)
   - Decision: Compare with current (20260201), delete if superseded

3. **feat/pilot1-hardening-vfv-20260130** (1 patch different)
   - Decision: Cherry-pick if needed, then delete

4. **feat/pilot-e2e-golden-3d-20260129** (2 patches different)
   - Decision: Cherry-pick if needed, then delete

5. **feat/tc902_hygiene_20260201** (duplicate group - keep one)
   - Decision: Keep if contains unique hygiene work, else delete

### Potentially Keep (if work incomplete)

6. **feat/golden-2pilots-20260201** - Keep if still active development
7. **integrate/consolidation_20260202_120555** - Keep temporarily during validation

---

## Complete Deletion Script (All Stages)

**Only run after ALL preconditions met:**

```bash
#!/bin/bash

echo "=== Branch Cleanup - Full Deletion Script ==="
echo ""
echo "⚠️  WARNING: This will delete 47 branches!"
echo "    Only proceed if:"
echo "    - All merges complete"
echo "    - All tests pass"
echo "    - Consolidation merged to main"
echo ""
read -p "Are you ABSOLUTELY SURE? (type 'yes' to continue): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted. No branches deleted."
    exit 1
fi

echo ""
echo "=== Stage 1: Duplicates (2) ==="
git branch -D feat/tc902_w4_impl_20260201
git branch -D fix/pilot1-w4-ia-planner-20260130
echo "Deleted 2 duplicates"

echo ""
echo "=== Stage 2: TC-* branches (40) ==="
git branch -D \
  feat/TC-100-bootstrap-repo \
  feat/TC-200-schemas-and-io \
  feat/TC-201-emergency-mode \
  feat/TC-250-shared-libs-governance \
  feat/TC-300-orchestrator-langgraph \
  feat/TC-400-repo-scout \
  feat/TC-401-clone-resolve-shas \
  feat/TC-402-fingerprint \
  feat/TC-403-discover-docs \
  feat/TC-404-discover-examples \
  feat/TC-410-facts-builder \
  feat/TC-411-extract-claims \
  feat/TC-412-map-evidence \
  feat/TC-413-detect-contradictions \
  feat/TC-420-snippet-curator \
  feat/TC-421-extract-doc-snippets \
  feat/TC-422-extract-code-snippets \
  feat/TC-430-ia-planner \
  feat/TC-440-section-writer \
  feat/TC-450-linker-and-patcher \
  feat/TC-460-validator \
  feat/TC-470-fixer \
  feat/TC-480-pr-manager \
  feat/TC-500-clients-services \
  feat/TC-510-mcp-server-setup \
  feat/TC-511-mcp-tool-registration \
  feat/TC-512-mcp-tool-handlers \
  feat/TC-520-telemetry-api-setup \
  feat/TC-521-telemetry-run-endpoints \
  feat/TC-522-telemetry-batch-upload \
  feat/TC-523-telemetry-metadata-endpoints \
  feat/TC-530-cli-entrypoints \
  feat/TC-540-content-path-resolver \
  feat/TC-550-hugo-config \
  feat/TC-560-determinism-harness \
  feat/TC-570-extended-gates \
  feat/TC-571-perf-security-gates \
  feat/TC-580-observability \
  feat/TC-590-security-handling \
  feat/TC-600-failure-recovery
echo "Deleted 40 TC-* branches"

echo ""
echo "=== Stage 2: Integration branches (2) ==="
git branch -D integrate/main-e2e-20260128-0837
git branch -D fix/main-green-20260128-1505
echo "Deleted 2 integration branches"

echo ""
echo "=== Stage 3: Coverage set branches (3) ==="
git branch -D fix/env-gates-20260128-1615
git branch -D impl/tc300-wire-orchestrator-20260128
# Optionally delete current if work complete:
# git branch -D feat/golden-2pilots-20260201
echo "Deleted 3 coverage set branches"

echo ""
echo "=== Stage 4: Consolidation branch (1) ==="
git branch -D integrate/consolidation_20260202_120555
echo "Deleted 1 consolidation branch"

echo ""
echo "=== Cleanup Complete ==="
echo "Deleted: 48 branches (47 + consolidation)"
echo "Remaining: $(git branch | wc -l) branches"
echo ""
echo "Verify final state:"
git branch
```

---

## Verification After Deletion

```bash
# Count remaining branches
git branch | wc -l
# Should show ~5-9 branches

# List remaining branches
git branch
# Should show: main + 4 uncovered pilots (+ maybe current if kept)

# Verify no branches are merged
git branch --merged main
# Should only show main

# Check for any stray branches
git branch --no-merged main
# Should show only uncovered pilots (if kept)
```

---

## Recovery (If Needed)

All deleted branches can be recovered from Phase 1 backups:

### From Backup Tags

```bash
# List available backups
git tag -l "backup/branches/20260201/*"

# Restore a specific branch
git branch <branch-name> backup/branches/20260201/<branch-name>
```

### From Bundle

```bash
# Verify bundle
git bundle verify reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle

# Restore specific branch
git fetch reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle \
  refs/heads/<branch-name>:refs/heads/<branch-name>
```

### From Checkpoint Tags (Phase 3)

If consolidation needs to be restarted:

```bash
# List checkpoints
git tag -l "checkpoint/consolidation_*"

# Reset to checkpoint
git reset --hard checkpoint/consolidation_before_fix-env-gates_20260202_120555
```

---

## Final State Target

**Before cleanup:** 52 branches
**After cleanup:** 5-9 branches (90-83% reduction)

**Remaining branches:**
1. main (production)
2. feat/golden-2pilots-20260130 (evaluate separately)
3. feat/pilot1-hardening-vfv-20260130 (evaluate separately)
4. feat/pilot-e2e-golden-3d-20260129 (evaluate separately)
5. feat/tc902_hygiene_20260201 (evaluate separately)
6-9. Any active WIP branches

**Deleted branches:** 47
- 2 exact duplicates
- 40 TC-* feature branches (contained in fix/env-gates)
- 2 integration branches (contained in fix/env-gates)
- 3 coverage set branches (merged to main)
- 1 consolidation branch (merged to main)

---

## Timeline

**Deletion execution time:** 5 minutes (script runs fast)
**Prerequisites time:** 6-8 hours (merge completion + testing)

**Recommended execution:**
- Complete all merges and tests
- Push main to remote
- Run deletion script in one go
- Verify final state
- Archive Phase 3 evidence

---

**Generated:** 2026-02-02
**Ready for execution:** After merge completion
**Script location:** Copy from this document

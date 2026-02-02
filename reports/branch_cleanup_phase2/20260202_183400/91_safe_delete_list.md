# Safe Delete List (Post-Merge Only)

**Generated:** 2026-02-02
**CRITICAL:** Only execute these deletions AFTER successful merge and test validation

---

## Deletion Preconditions ⚠️

**ALL of these must be true before deleting ANY branch:**

- [x] Backups exist (52 tags + git bundle verified ✅)
- [ ] fix/env-gates-20260128-1615 merged to main
- [ ] impl/tc300-wire-orchestrator-20260128 merged to main
- [ ] feat/golden-2pilots-20260201 merged to main
- [ ] All merge conflicts resolved
- [ ] All tests pass on merged main
- [ ] Main branch pushed to remote (if applicable)

**DO NOT PROCEED** until ALL checkboxes above are checked.

---

## Category 1: Exact Duplicates (Safe Delete Immediately After Merge)

These branches point to identical commits as other branches:

### Group 1: SHA d1d440f
```bash
# KEEP: feat/tc902_hygiene_20260201 (or delete both if work is in current)
# DELETE:
git branch -D feat/tc902_w4_impl_20260201
```

### Group 2: SHA c666914
```bash
# KEEP: feat/pilot-e2e-golden-3d-20260129
# DELETE:
git branch -D fix/pilot1-w4-ia-planner-20260130
```

**Total:** 2 duplicates

**Risk:** NONE (exact copies)

---

## Category 2: Fully Contained in fix/env-gates (43 branches)

These branches have **0 unique patches** compared to fix/env-gates-20260128-1615.
Once fix/env-gates is merged to main, these are redundant.

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

**Total:** 42 branches contained in fix/env-gates

**Evidence:** `22_allbranches_vs_candidates.csv` shows PlusCount=0 for all these branches vs fix/env-gates

**Risk:** LOW (patch-proven containment)

---

## Category 3: The Merged Branches Themselves (3)

After successful merge to main, the feature branches themselves become redundant:

```bash
# Delete after fix/env-gates is in main
git branch -D fix/env-gates-20260128-1615

# Delete after impl/tc300 is in main
git branch -D impl/tc300-wire-orchestrator-20260128

# Delete after current work is in main (and no longer active)
git branch -D feat/golden-2pilots-20260201
```

**Total:** 3 branches

**Risk:** NONE (work is in main)

---

## Category 4: KEEP (Do NOT Delete)

These branches are NOT covered and should be reviewed separately:

### Uncovered Pilot Branches (4)

| Branch | Status | Recommendation |
|--------|--------|----------------|
| feat/golden-2pilots-20260130 | 12 patches different | Review if superseded by 20260201 |
| feat/pilot-e2e-golden-3d-20260129 | 2 patches different | Evaluate if needed |
| feat/pilot1-hardening-vfv-20260130 | 1 patch different | Evaluate if needed |
| feat/tc902_hygiene_20260201 | Duplicate SHA | Keep one of the tc902 pair |

### Main Branch

| Branch | Status | Recommendation |
|--------|--------|----------------|
| main | - | NEVER DELETE |

**Total to keep:** 5 branches

---

## Summary Statistics

| Category | Count | Action Timing |
|----------|-------|---------------|
| Duplicates | 2 | Delete post-merge |
| Contained in fix/env-gates | 42 | Delete post-merge |
| The merged branches | 3 | Delete post-merge |
| **Total Deletable** | **47** | **Post-merge only** |
| Uncovered pilots | 4 | KEEP for review |
| Main | 1 | NEVER DELETE |
| **Total Remaining** | **5** | **After cleanup** |

**Reduction:** 52 branches → 5 branches (90% reduction)

---

## Deletion Sequence (Post-Merge)

### Step 1: Verify merge complete
```bash
# Check main has the merged work
git log main --oneline -10

# Verify tests pass
python -m pytest -v

# Confirm no uncommitted changes
git status
```

### Step 2: Delete duplicates (safest first)
```bash
git branch -D feat/tc902_w4_impl_20260201 fix/pilot1-w4-ia-planner-20260130
echo "Deleted 2 duplicates"
```

### Step 3: Delete TC-* branches (largest group)
```bash
# Run the large delete command for all 40 TC branches
# (See Category 2 above)
echo "Deleted 40 TC feature branches"
```

### Step 4: Delete integration branches
```bash
git branch -D integrate/main-e2e-20260128-0837 fix/main-green-20260128-1505
echo "Deleted 2 integration branches"
```

### Step 5: Delete the merged coverage set branches
```bash
git branch -D fix/env-gates-20260128-1615 impl/tc300-wire-orchestrator-20260128
# Optionally delete current if work is complete:
# git branch -D feat/golden-2pilots-20260201
echo "Deleted merged superset branches"
```

### Step 6: Verify final state
```bash
git branch
# Should show ~5 branches: main + 4 pilot branches (+ current if kept active)

git branch --merged main
# Should show only main (if current branch is not merged yet)
```

---

## Recovery Instructions (If Needed)

If any deleted branch is needed later:

### Restore from backup tag
```bash
# Find the backup
git tag -l "backup/branches/20260201/<branch-name>"

# Restore
git branch <branch-name> backup/branches/20260201/<branch-name>
```

### Restore from bundle
```bash
# Verify bundle
git bundle verify reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle

# Restore specific branch
git fetch reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle \
  refs/heads/<branch-name>:refs/heads/<branch-name>
```

---

## Checklist for Safe Deletion

Before deleting, confirm:

- [ ] All tests pass on main
- [ ] Git log shows merge commits for fix/env-gates, impl/tc300, and current
- [ ] No one else is working on these branches (if shared repo)
- [ ] Backup bundle is accessible
- [ ] You have at least one other copy of the repo (remote or local clone)

If ALL checked, proceed with deletion sequence above.

---

**FINAL WARNING:** These deletions are based on Phase 2 patch containment analysis. Do NOT delete before:
1. Completing the 3-branch merge
2. Resolving all conflicts
3. Passing all tests
4. Verifying work is in main

**Generated:** 2026-02-02
**Safe delete list complete**

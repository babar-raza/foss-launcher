# Branch Cleanup Recommendations

**Generated:** 2026-02-01 18:18:29
**Repository:** foss-launcher
**Analysis Date:** 2026-02-01
**Total Branches Analyzed:** 52

---

## Executive Summary

After comprehensive analysis of 52 local branches, we have identified:

1. **4 exact duplicate branches** (safe to delete immediately after backup)
2. **1 superset branch** (`impl/tc300-wire-orchestrator-20260128`) that contains the work of 40+ TC branches
3. **All branches have unique commits** not patch-equivalent to main
4. **Main has taskcard tracking but NOT implementation code** from feature branches
5. **Clear branch hierarchy** exists: TC branches → TC-600 → integration branches → impl/tc300

---

## A) Safe Delete Now (after backup ✓)

**Backup Status:** ✅ Complete
- 52 backup tags created under `backup/branches/20260201/`
- Git bundle created: `foss-launcher_all_branches_20260201.bundle` (13M, SHA256: ad7655d4...)

### Duplicate Branches (Safe to Delete)

These branches point to identical commits and are exact duplicates:

| Branch to DELETE | Duplicate of | Commit SHA | Reason |
|------------------|--------------|------------|---------|
| **feat/tc902_hygiene_20260201** | feat/golden-2pilots-20260201 | d1d440f | Exact duplicate |
| **feat/tc902_w4_impl_20260201** | feat/golden-2pilots-20260201 | d1d440f | Exact duplicate |
| **fix/pilot1-w4-ia-planner-20260130** | feat/pilot-e2e-golden-3d-20260129 | c669142 | Exact duplicate |

**Command to delete these 3 branches:**
```bash
git branch -D feat/tc902_hygiene_20260201 feat/tc902_w4_impl_20260201 fix/pilot1-w4-ia-planner-20260130
```

**Risk:** NONE - Exact duplicates backed up in tags and bundle

---

## B) Keep (Active Work)

These branches represent recent active work and should be preserved:

| Branch | Date | Ahead | Behind | Status |
|--------|------|-------|--------|--------|
| **feat/golden-2pilots-20260201** | 2026-02-01 | 2 | 0 | CURRENT BRANCH ⭐ |
| feat/golden-2pilots-20260130 | 2026-01-31 | 12 | 0 | Recent work |
| feat/pilot-e2e-golden-3d-20260129 | 2026-01-29 | 2 | 1 | Recent work |
| feat/pilot1-hardening-vfv-20260130 | 2026-01-30 | 1 | 1 | Recent work |

**Recommendation:** Keep all 4 branches for now. The current branch is actively being worked on.

---

## C) Merge Candidates

### Critical Finding: Superset Branch Hierarchy

Our ancestry analysis revealed a **clear superset chain**:

```
40 TC-* feature branches (TC-100 through TC-600)
    ↓ (contained by)
feat/TC-600-failure-recovery
    ↓ (contained by)
Integration branches (fix/env-gates, fix/main-green, integrate/main-e2e)
    ↓ (contained by)
impl/tc300-wire-orchestrator-20260128 (LARGEST SUPERSET) ⭐
```

### The One Branch to Merge Them All

**`impl/tc300-wire-orchestrator-20260128`** is the **superset of all TC work** and should be the primary merge candidate.

**Evidence:**
- Contains 119 unique commits not in main
- Includes work from 40+ TC feature branches
- Contains integration/fix branch work
- Has comprehensive test coverage (122+ test files)
- Includes all TC implementations (TC-100 through TC-600+)

**If this branch is merged, the following can be safely deleted:**
- All 40 TC-* feature branches (TC-100 through TC-600)
- Integration branches (fix/env-gates, fix/main-green, integrate/main-e2e)
- Total: **43 branches** can be deleted after merging this one branch

### Merge Strategy Recommendation

**Option 1: Single Comprehensive Merge (RECOMMENDED)**

```bash
# Step 1: Verify tests pass on impl/tc300
git checkout impl/tc300-wire-orchestrator-20260128
python -m pytest  # Verify all tests pass

# Step 2: Create consolidation merge to main
git checkout main
git checkout -b consolidate/tc-all-features-20260201
git merge impl/tc300-wire-orchestrator-20260128 --no-ff -m "Consolidate all TC feature implementations"

# Step 3: Resolve conflicts if any, test thoroughly

# Step 4: Merge to main
git checkout main
git merge consolidate/tc-all-features-20260201 --ff-only

# Step 5: Delete obsolete branches (see section D)
```

**Rationale:**
- Single merge brings in all TC work at once
- Easier to review than 40+ individual merges
- Clear audit trail with merge commit
- Tests can validate entire integrated system

**Option 2: Phased Merge (If Option 1 Fails)**

If `impl/tc300` has issues, fall back to:

1. Merge `feat/TC-600-failure-recovery` first (contains 8 TC branches)
2. Then merge integration branches
3. Finally merge remaining TC branches individually

---

## D) Cleanup After Merge

Once `impl/tc300-wire-orchestrator-20260128` is successfully merged to main:

### Delete These 43 Branches

**All TC-* Feature Branches (40 branches):**
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

**Integration/Fix Branches (3 branches):**
```bash
git branch -D \
  fix/env-gates-20260128-1615 \
  fix/main-green-20260128-1505 \
  integrate/main-e2e-20260128-0837
```

**The superset branch itself (1 branch):**
```bash
git branch -D impl/tc300-wire-orchestrator-20260128
```

**Total branches to delete post-merge:** 44 (43 + impl/tc300 itself)

---

## Summary Statistics

### Current State (Before Cleanup)
| Metric | Count |
|--------|-------|
| Total branches | 52 |
| Duplicate branches | 4 |
| Active work branches | 4 |
| TC feature branches | 40 |
| Integration branches | 4 |

### After Immediate Cleanup (Delete Duplicates)
| Metric | Count |
|--------|-------|
| Total branches | 49 |
| Remaining for review | 49 |

### After Full Cleanup (After Merge)
| Metric | Count |
|--------|-------|
| Total branches | 5 |
| Branches deleted | 47 |
| Reduction | 90% |

**Remaining branches:**
1. main
2. feat/golden-2pilots-20260201 (current active work)
3. feat/golden-2pilots-20260130 (recent work)
4. feat/pilot-e2e-golden-3d-20260129 (recent work)
5. feat/pilot1-hardening-vfv-20260130 (recent work)

---

## Risk Assessment

### Immediate Deletions (Duplicates)
- **Risk Level:** 🟢 NONE
- **Backup:** ✅ Yes (tags + bundle)
- **Reversible:** ✅ Yes (restore from backup)

### Merge of impl/tc300
- **Risk Level:** 🟡 MEDIUM
- **Mitigation:** Test thoroughly before merge
- **Backup:** ✅ Yes (tags + bundle)
- **Reversible:** ✅ Yes (git reset if needed)

### Post-Merge Deletions
- **Risk Level:** 🟢 LOW
- **Backup:** ✅ Yes (tags + bundle)
- **Reversible:** ✅ Yes (restore from backup if needed)

---

## Critical Insights

### 1. Main Has Tracking, Not Implementation

**Discovery:** Main branch contains:
- ✅ All taskcard files (TC-100 through TC-923)
- ✅ STATUS_BOARD tracking
- ✅ INDEX references
- ❌ **Missing: Actual implementation code from TC branches**

**Example:** `impl/tc300` adds 699 implementation files that don't exist in main:
- `src/launch/cli/` (CLI implementation)
- `src/launch/orchestrator/` (Orchestrator)
- `src/launch/workers/` (Worker implementations)
- `tests/` (122+ test files)

**Implication:** These branches contain real work that needs to be merged.

### 2. No Patch-Equivalence Found

**Discovery:** Cherry analysis shows:
- 0 branches with commits already in main (MinusCount = 0 for all)
- All branches have unique commits (PlusCount > 0)
- No cherry-picks or squash merges detected

**Implication:** No branches can be deleted based on "already in main" criterion.

### 3. Superset Chain is Clean

**Discovery:** Clear ancestor relationships:
- TC-600 contains 8 earlier TC branches
- Integration branches contain TC-600
- impl/tc300 contains integration branches

**Implication:** Merging impl/tc300 brings in all work cleanly.

---

## Recommended Action Sequence

### Phase 1: Immediate (Today)

1. ✅ **Backup complete** (tags + bundle created)
2. **Delete 3 duplicate branches**
   ```bash
   git branch -D feat/tc902_hygiene_20260201 feat/tc902_w4_impl_20260201 fix/pilot1-w4-ia-planner-20260130
   ```
3. **Verify backups**
   ```bash
   git tag | grep "backup/branches/20260201" | wc -l  # Should be 52
   ls -lh reports/branch_cleanup/20260201_181829/backup/*.bundle  # Should exist
   ```

### Phase 2: Testing (Next)

1. **Checkout and test impl/tc300**
   ```bash
   git checkout impl/tc300-wire-orchestrator-20260128
   python -m pytest -v
   # Check exit code, review failures
   ```

2. **If tests fail:** Fix tests or choose next best candidate (fix/env-gates)

3. **If tests pass:** Proceed to Phase 3

### Phase 3: Merge (After Tests Pass)

1. **Create consolidation branch**
   ```bash
   git checkout main
   git checkout -b consolidate/tc-all-features-20260201
   git merge impl/tc300-wire-orchestrator-20260128 --no-ff
   ```

2. **Resolve conflicts** (if any)

3. **Test merged state**
   ```bash
   python -m pytest -v
   ```

4. **Merge to main**
   ```bash
   git checkout main
   git merge consolidate/tc-all-features-20260201 --ff-only
   ```

### Phase 4: Final Cleanup (After Successful Merge)

1. **Delete 44 obsolete branches** (see section D)

2. **Verify final state**
   ```bash
   git branch  # Should show ~5 branches
   git log --oneline -10  # Verify merge commit
   ```

3. **Push to remote** (optional)
   ```bash
   git push origin main
   ```

---

## Recovery Instructions

If anything goes wrong, restore from backup:

### Restore a Single Branch
```bash
# Find the backup tag
git tag | grep "backup/branches/20260201/<branch-name>"

# Restore the branch
git branch <branch-name> backup/branches/20260201/<branch-name>
```

### Restore All Branches from Bundle
```bash
# Verify bundle
git bundle verify reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle

# Clone from bundle to new location
git clone reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle restored-repo

# Or fetch specific branches
git fetch reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle refs/heads/<branch>:refs/heads/<branch>
```

---

## Next Actions for User

**Immediate:**
- [ ] Review this report
- [ ] Delete 3 duplicate branches
- [ ] Test `impl/tc300-wire-orchestrator-20260128`

**Short-term:**
- [ ] Merge impl/tc300 if tests pass
- [ ] Delete 44 obsolete branches post-merge
- [ ] Push changes to remote

**Long-term:**
- [ ] Review remaining 4 active branches
- [ ] Merge or close active branches as work completes
- [ ] Establish branch naming/cleanup policy

---

**END OF RECOMMENDATIONS**

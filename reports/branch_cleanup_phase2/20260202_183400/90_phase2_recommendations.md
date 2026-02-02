# Phase 2: Branch Cleanup Decision Report

**Generated:** 2026-02-02
**Analysis Type:** Patch Containment Proof + Trial Merge
**Repository:** foss-launcher

---

## Executive Summary

Phase 2 patch containment analysis **CONTRADICTS Phase 1's key finding**. Rigorous patch-equivalence testing reveals:

1. **`impl/tc300` is NOT the superset** - it contains only unique work for itself
2. **`fix/env-gates-20260128-1615` IS the true superset** - contains patches from 43 branches
3. **Minimum coverage requires 3 branches** (not 1): fix/env-gates + impl/tc300 + current
4. **4 recent pilot branches remain uncovered** and need separate handling
5. **Trial merge shows 16 conflicts** - manageable but requires careful resolution

---

## 1. Is `impl/tc300` Truly a Superset? **NO ❌**

### Phase 1 Claim (INCORRECT)
- Phase 1 stated: "`impl/tc300-wire-orchestrator-20260128` is THE superset containing ALL 40+ TC branches"
- Recommended: "Merge this ONE branch instead of 40+ individual branches"

### Phase 2 Patch Analysis (TRUTH)

**Pairwise Containment Matrix Results:**

| Branch X | Branch Y | Patches X NOT in Y |
|----------|----------|-------------------|
| **impl/tc300** | integrate/main-e2e | **63 unique** ❌ |
| **impl/tc300** | fix/main-green | **60 unique** ❌ |
| **impl/tc300** | fix/env-gates | **58 unique** ❌ |
| **impl/tc300** | feat/TC-600 | **68 unique** ❌ |
| feat/TC-600 | integrate/main-e2e | **0** ✅ fully contained |
| feat/TC-600 | fix/main-green | **0** ✅ fully contained |
| feat/TC-600 | fix/env-gates | **0** ✅ fully contained |

**Interpretation:**
- `impl/tc300` has 58-68 patches NOT in integration branches
- This proves impl/tc300 is a **separate development line**, not a superset
- `feat/TC-600` IS contained in all integration branches (0 unique patches)

### Why Phase 1 Was Wrong

Phase 1 used **ancestry relationships** (`git merge-base --is-ancestor`), which found:
- Phase 1 ancestry: "impl/tc300 vs TC-600 → neither"
- This should have been a red flag!

Phase 2 uses **patch equivalence** (`git cherry`), which is the correct method for detecting:
- Cherry-picks
- Squash merges
- Work done differently but achieving same result

---

## 2. What IS the Coverage Set?

### Greedy Coverage Algorithm Results

**Minimum set to cover all 52 branches:**

1. **fix/env-gates-20260128-1615** → covers **43 branches** ⭐
   - All TC-100 through TC-600 branches (40 branches)
   - Integration branches (integrate/main-e2e, fix/main-green, itself)

2. **impl/tc300-wire-orchestrator-20260128** → covers **1 branch** (itself)
   - Has unique implementation work not in any other branch

3. **feat/golden-2pilots-20260201** → covers **4 branches**
   - Itself (current work)
   - main (0 patches difference)
   - feat/tc902_hygiene_20260201 (duplicate)
   - feat/tc902_w4_impl_20260201 (duplicate)

**Total coverage:** 48/52 branches (92%)

### Uncovered Branches (4)

These branches have unique work NOT covered by any candidate:

| Branch | Closest Match | Patches Different |
|--------|---------------|-------------------|
| **feat/golden-2pilots-20260130** | current (20260201) | 12 patches |
| **feat/pilot-e2e-golden-3d-20260129** | current | 2 patches |
| **feat/pilot1-hardening-vfv-20260130** | current | 1 patch |
| **fix/pilot1-w4-ia-planner-20260130** | current | 2 patches (duplicate) |

**Note:** These are recent pilot/experimental branches from Jan 29-31.

---

## 3. Trial Merge Outcome

### Merge Strategy Tested

**Order:**
1. main → fix/env-gates-20260128-1615

**Result:** ❌ **16 conflicts**

### Conflict Breakdown

| Category | Files | Conflict Type | Severity |
|----------|-------|---------------|----------|
| Tracking/Docs | 5 | Content (UU) | LOW - auto-resolvable |
| Implementation | 11 | Add/Add (AA) | MEDIUM - need review |

**Conflicted Files:**

**Tracking (5) - Accept "theirs" (fix/env-gates):**
- `plans/taskcards/STATUS_BOARD.md`
- `plans/taskcards/TC-520_pilots_and_regression.md`
- `plans/taskcards/TC-522_pilot_e2e_cli.md`
- `reports/swarm_allowed_paths_audit.md`
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`

**Implementation (11) - Requires manual review:**
- `src/launch/clients/commit_service.py`
- `src/launch/orchestrator/graph.py`
- `src/launch/orchestrator/run_loop.py`
- `src/launch/orchestrator/worker_invoker.py`
- `src/launch/workers/_git/clone_helpers.py`
- `src/launch/workers/_shared/policy_check.py`
- `src/launch/workers/w1_repo_scout/worker.py`
- `tests/integration/test_tc_300_run_loop.py`
- `tests/unit/cli/test_tc_530_cli_entrypoints.py`
- `tests/unit/orchestrator/test_tc_300_graph.py`
- `tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py`

### Conflict Resolution Strategy

**Phase 1 (Easy - 5 files):**
```bash
# Accept theirs for tracking files
git checkout --theirs plans/taskcards/STATUS_BOARD.md
git checkout --theirs plans/taskcards/TC-520_pilots_and_regression.md
git checkout --theirs plans/taskcards/TC-522_pilot_e2e_cli.md
git checkout --theirs reports/swarm_allowed_paths_audit.md
git checkout --theirs specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
git add <resolved-files>
```

**Phase 2 (Careful - 11 files):**
- Add/Add conflicts mean both branches independently added these files
- Need to:
  1. Compare implementations
  2. Identify if they're truly different or just different paths to same goal
  3. Merge logic from both if different
  4. Choose one if functionally equivalent

**Estimated resolution time:** 2-4 hours for careful review

---

## 4. Test Outcome Summary

### Tests NOT Run

**Reason:** Trial merge was aborted after conflict analysis to focus on decision-making.

**CI Test Plan Extracted:**

From `.github/workflows/ci.yml`:
```yaml
# CI runs:
- Python setup (3.11)
- pip install -e .
- pytest tests/ -v
- Various gates (validation, lint, etc.)
```

**Recommendation for next phase:**
1. Complete merge conflict resolution
2. Run full test suite on merged scratch branch
3. Compare results against main baseline

---

## 5. Recommended Next Action

### ❌ STOP: Do NOT follow Phase 1 recommendation

**Phase 1 said:** Merge `impl/tc300` as the superset branch.

**Phase 2 proves:** This would MISS 43 branches of work that are in `fix/env-gates` but NOT in `impl/tc300`.

### ✅ CORRECT Strategy: 3-Branch Consolidation

**Step 1: Merge fix/env-gates (THE REAL SUPERSET)**
```bash
git checkout main
git checkout -b consolidate/phase2-validated

# Merge the real superset
git merge fix/env-gates-20260128-1615 --no-ff -m "Consolidate 43 TC branches via fix/env-gates"

# Resolve 16 conflicts (2-4 hours)
# - Auto-resolve 5 tracking files (accept theirs)
# - Manually resolve 11 implementation files
git add <resolved-files>
git commit

# Test
python -m pytest -v
```

**Step 2: Add impl/tc300's unique work**
```bash
# Merge impl/tc300 for its unique implementation
git merge impl/tc300-wire-orchestrator-20260128 --no-ff -m "Add impl/tc300 unique work"

# Resolve any conflicts
# Test again
python -m pytest -v
```

**Step 3: Add current work**
```bash
# Merge current active work
git merge feat/golden-2pilots-20260201 --no-ff -m "Add current active work"

# Resolve conflicts
# Test again
```

**Step 4: Decide on 4 uncovered branches**

For each of these recent pilot branches:
- feat/golden-2pilots-20260130 (12 patches)
- feat/pilot-e2e-golden-3d-20260129 (2 patches)
- feat/pilot1-hardening-vfv-20260130 (1 patch)

**Options:**
a) Merge individually if work is needed
b) Delete if superseded by current (20260201)
c) Keep for future investigation

---

## Critical Decision Matrix

| Approach | Branches Merged | Work Captured | Conflicts | Risk | Status |
|----------|----------------|---------------|-----------|------|--------|
| **Phase 1** (impl/tc300 only) | 1 | **INCOMPLETE** ❌ | Unknown | HIGH | ⛔ REJECTED |
| **Phase 2** (fix/env-gates + impl/tc300 + current) | 3 | Complete (48/52) | 16 (manageable) | MEDIUM | ✅ RECOMMENDED |
| **Phased** (43 individual TC merges) | 43+ | Complete | Many | VERY HIGH | ❌ NOT RECOMMENDED |

---

## Evidence Files Generated

| File | Description |
|------|-------------|
| `00_repo_path.txt` | Repository absolute path |
| `01_git_status.txt` | Git status at start |
| `02_branch_vv.txt` | All branches verbose |
| `03_main_head.txt` | Main branch HEAD |
| `04_backup_tags_list.txt` | Verified backup tags (52) |
| `05_backup_bundle_check.txt` | Verified git bundle |
| `10_branch_tips.csv` | Current branch SHAs |
| `11_duplicates_revalidated.md` | Re-validated duplicates (4) |
| `20_patch_containment_matrix.csv` | Pairwise patch containment (30 comparisons) |
| `21_all_branches.txt` | Complete branch list (52) |
| `22_allbranches_vs_candidates.csv` | Full coverage analysis (312 comparisons) |
| `23_coverage_set.md` | Minimum coverage set (3 branches) |
| `30_merge1_fix-env-gates.log` | Trial merge log |
| `30_conflicts_fix-env-gates.txt` | Conflict list (16 files) |
| `31_partial_resolution_status.txt` | Post-resolution status |
| `COMMANDS.log` | All commands executed |

---

## Safe Delete List (POST-merge only)

**After successfully merging the 3-branch coverage set**, these can be safely deleted:

### Duplicates (2)
- `feat/tc902_w4_impl_20260201` (duplicate of hygiene branch)
- `fix/pilot1-w4-ia-planner-20260130` (duplicate of pilot-e2e branch)

### Covered by fix/env-gates (40)
All TC-* branches from TC-100 through TC-600:
```bash
git branch -D \
  feat/TC-100-bootstrap-repo \
  feat/TC-200-schemas-and-io \
  feat/TC-201-emergency-mode \
  # ... (37 more TC branches)
  feat/TC-600-failure-recovery
```

### Covered by fix/env-gates (integration branches - 2)
```bash
git branch -D \
  integrate/main-e2e-20260128-0837 \
  fix/main-green-20260128-1505
```

### The merged branches themselves (3)
```bash
git branch -D \
  fix/env-gates-20260128-1615 \
  impl/tc300-wire-orchestrator-20260128 \
  feat/golden-2pilots-20260201  # If current work is complete
```

**Total deletable after merge:** 47 branches

**Remaining:** 5 branches (main + 4 uncovered pilot branches)

---

## GO / NO-GO Recommendation

### Current Status: ⚠️ GO WITH CAUTION

**GO IF:**
✅ User has 4-6 hours for careful conflict resolution
✅ Tests can be run after merge (pytest available)
✅ Rollback plan accepted (bundle + tags)
✅ User understands Phase 1 recommendation was incorrect

**NO-GO IF:**
❌ Time-constrained (need quick merge)
❌ Cannot run tests to validate
❌ Risk-averse (conflicts make user uncomfortable)
❌ Still want to follow Phase 1 plan (would lose work!)

### Alternative: Phased Approach

If 3-branch merge is too risky:

**Week 1:** Merge fix/env-gates only (43 branches consolidated)
**Week 2:** Merge impl/tc300 (add unique work)
**Week 3:** Merge current work + decide on 4 pilot branches

---

## Key Learnings

1. **Ancestry ≠ Containment**: Git ancestry relationships don't capture cherry-picks, squashes, or parallel development
2. **Patch equivalence is truth**: `git cherry` is the correct tool for determining what work is truly unique
3. **Bigger isn't always superset**: impl/tc300 has 117 commits but only covers itself
4. **Integration branches are consolidation points**: fix/env-gates contains work from 43 branches despite being older
5. **Always validate with patch analysis**: Phase 1's logical deduction was wrong; Phase 2's empirical measurement is correct

---

## Final Recommendation Summary

**DO:**
1. ✅ Merge fix/env-gates (real superset, 43 branches)
2. ✅ Merge impl/tc300 (unique work)
3. ✅ Merge feat/golden-2pilots-20260201 (current)
4. ✅ Resolve 16 conflicts carefully (4-6 hours)
5. ✅ Test thoroughly at each step
6. ✅ Delete 47 branches post-merge
7. ✅ Review 4 uncovered pilot branches separately

**DO NOT:**
1. ❌ Merge only impl/tc300 (Phase 1 plan)
2. ❌ Skip conflict resolution
3. ❌ Delete branches before merge completes
4. ❌ Assume ancestry = containment

---

**CRITICAL:** Phase 1 recommendations must be revised based on Phase 2 findings.

**Generated:** 2026-02-02 11:34:00
**Analysis Complete**

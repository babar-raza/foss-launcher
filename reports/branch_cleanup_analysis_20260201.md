# Branch Cleanup Analysis Report
**Generated:** 2026-02-01
**Repository:** foss-launcher
**Remote:** https://github.com/babar-raza/foss-launcher.git
**Current Branch:** feat/golden-2pilots-20260201
**Main Branch HEAD:** c78c3ff (fix: TC-709 - Fix time-sensitive test in test_tc_523_metadata_endpoints)

---

## Executive Summary

This report analyzes **51 unmerged branches** in the foss-launcher repository to guide safe merging and deletion decisions. The analysis reveals:

- **5 duplicate branches** pointing to identical commits (candidates for immediate deletion)
- **40 feature branches** (feat/TC-*) representing individual task card implementations
- **3 active work branches** from the last 3 days
- **8 older integration/fix branches** from late January that may be superseded

**CRITICAL FINDING:** Three branches (`feat/golden-2pilots-20260201`, `feat/tc902_hygiene_20260201`, `feat/tc902_w4_impl_20260201`) point to the exact same commit and appear to be duplicates.

---

## Repository Status

| Metric | Value |
|--------|-------|
| Total Local Branches | 52 |
| Merged with Main | 0 (already cleaned) |
| Unmerged Branches | 51 |
| Main is Ahead of Origin | Yes (1 commit) |
| Branches with Remote Tracking | 0 |

**Note:** ALL unmerged branches have `HasRemote: none`, meaning they are local-only and have not been pushed to the remote repository.

---

## Branch Categories

### Category 1: DUPLICATE BRANCHES (Safe to Delete)

These branches point to identical commits and are redundant:

| Branch Name | Commit Hash | Can Delete? | Notes |
|-------------|-------------|-------------|-------|
| feat/tc902_hygiene_20260201 | d1d440f | **YES** | Duplicate of feat/golden-2pilots-20260201 |
| feat/tc902_w4_impl_20260201 | d1d440f | **YES** | Duplicate of feat/golden-2pilots-20260201 |
| fix/pilot1-w4-ia-planner-20260130 | c669142 | **YES** | Duplicate of feat/pilot-e2e-golden-3d-20260129 |

**Recommendation:** Delete these 3 branches immediately - they are exact duplicates.

---

### Category 2: CURRENT ACTIVE WORK (Keep)

Recent branches from the last 3 days that represent active work:

| Branch | Date | Ahead | Behind | Files | Insertions | Deletions |
|--------|------|-------|--------|-------|------------|-----------|
| **feat/golden-2pilots-20260201** | 2026-02-01 | 2 | 0 | 26 | 4,537 | 23 |
| feat/golden-2pilots-20260130 | 2026-01-31 | 12 | 0 | 413 | 282,643 | 534 |
| feat/pilot1-hardening-vfv-20260130 | 2026-01-30 | 1 | 1 | 4 | 227 | 8 |
| feat/pilot-e2e-golden-3d-20260129 | 2026-01-29 | 2 | 1 | 12 | 1,528 | 11 |

**Current Branch:** feat/golden-2pilots-20260201 (marked with **)

**Notes:**
- `feat/golden-2pilots-20260201` is the active branch (2 commits ahead of main, 0 behind)
- `feat/golden-2pilots-20260130` has significant changes (282K insertions) and may need merging
- All are 0-1 commits behind main, indicating they're relatively up-to-date

---

### Category 3: TASK CARD FEATURE BRANCHES (Review Required)

40 branches representing individual task card (TC-*) implementations. All are 2 commits behind main.

#### High Impact Branches (85+ commits ahead)
| Branch | Ahead | Files | Insertions | Deletions | Last Commit |
|--------|-------|-------|------------|-----------|-------------|
| feat/TC-600-failure-recovery | 85 | 587 | 206,681 | 1,908 | chore: save work in progress before merge operation |

#### Large Branches (60-84 commits ahead)
| Branch | Ahead | Files | Insertions | Deletions | Last Commit |
|--------|-------|-------|------------|-----------|-------------|
| feat/TC-590-security-handling | 80 | 556 | 201,331 | 1,856 | chore(TC-590): mark complete on STATUS_BOARD |
| feat/TC-580-observability | 77 | 544 | 198,196 | 1,856 | chore(TC-580): mark complete on STATUS_BOARD |
| feat/TC-560-determinism-harness | 74 | 535 | 195,446 | 1,856 | chore(TC-560): mark complete on STATUS_BOARD |
| feat/TC-550-hugo-config | 71 | 527 | 192,743 | 1,852 | chore(TC-550): update taskcard status to Done |
| feat/TC-540-content-path-resolver | 69 | 522 | 190,992 | 1,831 | chore(TC-540): update STATUS_BOARD (Done: 26/41) |
| feat/TC-523-telemetry-metadata-endpoints | 66 | 516 | 188,933 | 1,830 | feat: implement telemetry metadata and metrics endpoints (TC-523) |
| feat/TC-522-telemetry-batch-upload | 65 | 512 | 187,827 | 1,830 | feat: implement TC-522 - Telemetry API batch upload endpoints |
| feat/TC-521-telemetry-run-endpoints | 64 | 506 | 186,267 | 1,830 | feat: implement telemetry API run endpoints (TC-521) |
| feat/TC-520-telemetry-api-setup | 63 | 499 | 184,098 | 1,830 | feat: implement TC-520 local telemetry API setup |
| feat/TC-530-cli-entrypoints | 62 | 493 | 182,936 | 1,830 | chore: mark TC-530 as Done (update taskcard status) |
| feat/TC-512-mcp-tool-handlers | 60 | 486 | 181,655 | 1,759 | feat: implement MCP tool handlers (TC-512) |

#### Medium Branches (40-59 commits ahead)
| Branch | Ahead | Files | Insertions | Deletions | Last Commit |
|--------|-------|-------|------------|-----------|-------------|
| feat/TC-511-mcp-tool-registration | 59 | 482 | 179,861 | 1,759 | feat: implement TC-511 MCP tool registration |
| feat/TC-510-mcp-server-setup | 58 | 477 | 178,279 | 1,745 | feat(TC-510): Implement MCP server setup and initialization |
| feat/TC-480-pr-manager | 57 | 470 | 177,368 | 1,727 | chore: mark TC-480 as Done and regenerate STATUS_BOARD |
| feat/TC-470-fixer | 55 | 465 | 175,324 | 1,717 | chore: update TC-470 status to Done in STATUS_BOARD |
| feat/TC-571-perf-security-gates | 53 | 459 | 173,300 | 1,707 | feat: implement TC-571 performance and security validation gates |
| feat/TC-570-extended-gates | 52 | 450 | 171,731 | 1,707 | chore: update TC-570 status to Done |
| feat/TC-460-validator | 50 | 436 | 169,140 | 1,704 | chore: mark TC-460 complete and update STATUS_BOARD |
| feat/TC-450-linker-and-patcher | 47 | 430 | 167,178 | 1,693 | chore: mark TC-450 as Done (W6_AGENT) |
| feat/TC-440-section-writer | 45 | 424 | 164,631 | 1,683 | chore: update TC-440 status to Done in STATUS_BOARD |
| feat/TC-430-ia-planner | 43 | 418 | 162,525 | 1,675 | chore: mark TC-430 as Done in taskcard |
| feat/TC-420-snippet-curator | 41 | 412 | 160,235 | 1,669 | chore: mark TC-420 complete in STATUS_BOARD |

#### Smaller Branches (2-39 commits ahead)
| Branch | Ahead | Files | Insertions | Deletions | Last Commit |
|--------|-------|-------|------------|-----------|-------------|
| feat/TC-422-extract-code-snippets | 39 | 406 | 158,327 | 1,661 | chore(TC-422): update taskcard status to Done |
| feat/TC-421-extract-doc-snippets | 37 | 401 | 155,864 | 1,655 | chore: mark TC-421 complete and update STATUS_BOARD |
| feat/TC-410-facts-builder | 34 | 396 | 153,546 | 1,648 | chore(TC-410): mark W2 FactsBuilder integrator as Done in STATUS_BOARD |
| feat/TC-413-detect-contradictions | 32 | 391 | 151,485 | 1,641 | chore: update TC-413 taskcard and regenerate STATUS_BOARD |
| feat/TC-412-map-evidence | 30 | 386 | 149,668 | 1,631 | chore: mark TC-412 as Done in taskcard and regenerate STATUS_BOARD |
| feat/TC-411-extract-claims | 28 | 381 | 147,588 | 1,625 | chore(TC-411): Update taskcard status to Done and regenerate STATUS_BOARD |
| feat/TC-400-repo-scout | 26 | 375 | 145,598 | 1,614 | chore: mark TC-400 as Done in STATUS_BOARD |
| feat/TC-404-discover-examples | 24 | 369 | 143,692 | 1,607 | feat: implement TC-404 example discovery worker |
| feat/TC-403-discover-docs | 22 | 365 | 141,576 | 1,607 | feat(TC-403): implement documentation discovery in W1 RepoScout |
| feat/TC-402-fingerprint | 21 | 361 | 139,567 | 1,607 | chore: mark TC-402 complete on STATUS_BOARD |
| feat/TC-401-clone-resolve-shas | 18 | 355 | 137,481 | 1,603 | feat: implement TC-401 (W1.1 Clone inputs and resolve SHAs) |
| feat/TC-500-clients-services | 16 | 347 | 135,880 | 1,599 | fix: correct base model test to accept alphabetical key ordering with sort_keys= |
| feat/TC-300-orchestrator-langgraph | 12 | 338 | 133,524 | 1,593 | feat: implement TC-300 (Orchestrator graph wiring and run loop) |
| feat/TC-250-shared-libs-governance | 10 | 327 | 131,590 | 1,588 | feat: implement shared data models (TC-250) |
| feat/TC-201-emergency-mode | 8 | 312 | 129,268 | 1,583 | done: TC-201 implementation complete with evidence |
| feat/TC-200-schemas-and-io | 5 | 302 | 127,429 | 1,579 | chore(TC-200): mark taskcard as Done |
| feat/TC-100-bootstrap-repo | 2 | 289 | 125,577 | 1,575 | done: TC-100 implementation complete with evidence |

**Pattern Analysis:**
- Many branches have commit messages like "chore: mark TC-XXX as Done" or "Done in STATUS_BOARD"
- This suggests these features were completed but never merged to main
- ALL are exactly 2 commits behind main (same divergence point)
- Most have substantial code changes (100K+ insertions)

---

### Category 4: INTEGRATION & FIX BRANCHES (Review Required)

Older branches from late January that may contain work already incorporated into main:

| Branch | Date | Ahead | Behind | Files | Insertions | Deletions | Last Commit |
|--------|------|-------|--------|-------|------------|-----------|-------------|
| fix/env-gates-20260128-1615 | 2026-01-28 | 132 | 2 | 614 | 211,507 | 1,926 | fix: make main fully green (clean-room validation + all tests passing) |
| fix/main-green-20260128-1505 | 2026-01-28 | 129 | 2 | 597 | 206,928 | 1,926 | fix: correct broken markdown links in historical reports (Gate D) |
| integrate/main-e2e-20260128-0837 | 2026-01-28 | 125 | 2 | 596 | 206,911 | 1,908 | chore: final staging state before landing to main |
| impl/tc300-wire-orchestrator-20260128 | 2026-01-29 | 117 | 2 | 699 | 248,010 | 2,007 | fix: strip ANSI codes in CLI help tests for cross-platform compatibility |

**Notes:**
- These branches have commit messages suggesting they were preparation for main merges
- `integrate/main-e2e-20260128-0837` suggests it was a staging branch
- High commit counts (117-132) and massive changes
- All 2 commits behind main - same divergence point as TC-* branches

---

## Critical Findings

### 🔴 DUPLICATE BRANCHES FOUND

**Group 1:** Three branches pointing to commit `d1d440f`
- `feat/golden-2pilots-20260201` (CURRENT BRANCH - KEEP)
- `feat/tc902_hygiene_20260201` (DELETE)
- `feat/tc902_w4_impl_20260201` (DELETE)

**Group 2:** Two branches pointing to commit `c669142`
- `feat/pilot-e2e-golden-3d-20260129` (KEEP - older, might have context)
- `fix/pilot1-w4-ia-planner-20260130` (DELETE - redundant)

### 🟡 ALL BRANCHES ARE LOCAL-ONLY

**Risk Level:** MEDIUM
- No branches have remote tracking
- No backup exists on remote if deleted
- Safe to delete duplicates, but unique branches should be reviewed carefully

### 🟡 COMMON DIVERGENCE POINT

**Observation:** 40 TC-* branches and 4 integration branches are all exactly **2 commits behind main**

This suggests:
1. They all branched from a common ancestor
2. Main has moved forward by 2 commits since then
3. These might represent a development snapshot before a major merge

**Main's last 5 commits:**
```
d1d440f fix: Add TC-900 to INDEX.md
6f82d6d feat: Integrate TC-900, TC-901, TC-903 (TC-902 incomplete)
c78c3ff fix: TC-709 - Fix time-sensitive test in test_tc_523_metadata_endpoints (CURRENT MAIN)
d420b76 TC-300: Make pipeline real + Mock E2E offline pilot (#1)
c8dab0c chore: finalize Phase 5 evidence in pre-implementation report
```

### 🟡 TASK CARDS MARKED "DONE" BUT NOT MERGED

**Observation:** Many TC-* branches have final commits like:
- "chore: mark TC-XXX as Done in STATUS_BOARD"
- "chore(TC-XXX): update taskcard status to Done"

**Implication:** These features appear complete but were never merged. Possible reasons:
1. Work was completed on branches but consolidation happened elsewhere
2. Work was cherry-picked or manually integrated
3. Branches represent an abandoned development approach
4. Work is waiting for a bulk merge

---

## Recommended Action Plan

### Phase 1: IMMEDIATE (Safe Deletions)

Delete duplicate branches that provide no unique value:

```bash
git branch -D feat/tc902_hygiene_20260201
git branch -D feat/tc902_w4_impl_20260201
git branch -D fix/pilot1-w4-ia-planner-20260130
```

**Risk:** NONE - these are exact duplicates

---

### Phase 2: INVESTIGATION REQUIRED

Before proceeding with merges or deletions, answer these questions:

#### Question 1: TC-* Branch Strategy
**What to investigate:**
- Are all TC-* features already incorporated into main through a different mechanism?
- Check `STATUS_BOARD.md` or project documentation for task card status
- Compare TC-* branch content with current main to see if work exists

**How to check:**
```bash
# Example: Check if TC-100 work exists in main
git diff feat/TC-100-bootstrap-repo main --stat
git log main --all --grep="TC-100"
```

**Possible outcomes:**
- ✅ Work is in main → Delete branches
- ❌ Work is not in main → Merge or consolidate
- ⚠️ Partial overlap → Needs manual review

#### Question 2: Integration Branch Purpose
**What to investigate:**
- Were `fix/env-gates-*`, `fix/main-green-*`, `integrate/main-e2e-*` superseded?
- Check if commit messages indicate these were merged via another path

**How to check:**
```bash
# Check if commits from integration branches exist in main
git log main --all --grep="clean-room validation"
git log main --all --grep="final staging state"
```

#### Question 3: Golden Pilot Strategy
**What to investigate:**
- Which golden pilot branch should be canonical?
- Should `feat/golden-2pilots-20260130` (12 commits, 282K insertions) be merged?
- Is the current branch `feat/golden-2pilots-20260201` the continuation?

**How to check:**
```bash
# See relationship between the two
git log feat/golden-2pilots-20260130..feat/golden-2pilots-20260201 --oneline
git log feat/golden-2pilots-20260201..feat/golden-2pilots-20260130 --oneline
```

---

### Phase 3: BULK OPERATIONS (After Investigation)

Once investigations are complete, you may need to:

#### Option A: Merge All TC-* Branches (If Work Is Missing)
```bash
# Create a consolidation branch
git checkout -b consolidate/tc-features main

# Merge all TC branches (example)
for branch in feat/TC-{100,200,201,250,300}*; do
  git merge "$branch" --no-ff -m "Merge $branch"
done
```

#### Option B: Delete All TC-* Branches (If Work Exists in Main)
```bash
# Only do this if confirmed work is in main!
git branch | grep 'feat/TC-' | xargs git branch -D
```

#### Option C: Selective Merge (Hybrid Approach)
- Merge branches with unique work not in main
- Delete branches with duplicate/obsolete work

---

## Decision Matrix for LLM

Use this matrix to guide merge/delete decisions:

| Condition | Action | Risk Level |
|-----------|--------|------------|
| Branch is duplicate (same commit hash) | **DELETE** | 🟢 NONE |
| Branch is current work (last 3 days) | **KEEP** | 🟢 NONE |
| Branch commits exist in main (cherry-picked) | **DELETE** | 🟡 LOW |
| Branch has unique commits not in main | **INVESTIGATE** → Merge or Keep | 🔴 HIGH |
| Branch is behind main >10 commits | **REBASE** before merge | 🟡 MEDIUM |
| Branch name contains "integrate" or "staging" | **DELETE** if already merged | 🟡 LOW |
| Branch marked "Done" but not merged | **INVESTIGATE** | 🟡 MEDIUM |

---

## Commands Reference

### Diagnostic Commands

```bash
# Check if branch work exists in main
git log main --all --grep="<search-term>"
git diff <branch> main --stat

# Find common ancestor
git merge-base <branch> main

# See unique commits on branch
git log main..<branch> --oneline

# See unique commits on main
git log <branch>..main --oneline

# Check if specific file changes are in main
git diff <branch> main -- <file-path>
```

### Safe Deletion Commands

```bash
# Delete merged branch (safe - git will prevent if unmerged)
git branch -d <branch>

# Force delete unmerged branch (CAREFUL!)
git branch -D <branch>

# Delete multiple branches matching pattern
git branch | grep '<pattern>' | xargs git branch -D
```

### Merge Commands

```bash
# Merge with explicit merge commit
git merge <branch> --no-ff -m "Merge <branch>"

# Rebase branch onto main first (if behind)
git checkout <branch>
git rebase main
git checkout main
git merge <branch> --ff-only
```

---

## Summary Statistics

| Category | Count | Total Commits Ahead | Total Insertions | Total Deletions |
|----------|-------|---------------------|------------------|-----------------|
| Duplicate Branches | 3 | 0 (duplicates) | 0 | 0 |
| Active Work Branches | 4 | 17 | 284,935 | 576 |
| TC-* Feature Branches | 40 | 1,847 | 6,388,465 | 67,636 |
| Integration/Fix Branches | 4 | 503 | 873,356 | 7,861 |
| **TOTAL** | **51** | **2,367** | **7,546,756** | **76,073** |

---

## Next Steps for LLM Assistant

When guiding branch cleanup, follow this sequence:

1. **Execute Phase 1 (Immediate Deletions)**
   - Delete the 3 confirmed duplicate branches
   - Report success

2. **Execute Phase 2 (Investigation)**
   - Check if TC-* work exists in main
   - Check if integration branch work was merged
   - Determine golden pilot branch strategy
   - Report findings with recommendations

3. **Execute Phase 3 (Bulk Operations)**
   - Based on investigation, propose merge or delete operations
   - Get user confirmation before bulk operations
   - Execute confirmed operations
   - Verify main branch integrity after merges

4. **Cleanup Verification**
   - Run final `git branch` to show remaining branches
   - Ensure main branch tests still pass
   - Document any branches kept and why

---

## Appendix A: Full Branch Inventory

<details>
<summary>Click to expand complete branch data (CSV format)</summary>

```csv
Branch,Ahead,Behind,FilesChanged,Insertions,Deletions,LastCommitDate,LastCommitMsg,Author,HasRemote
feat/TC-100-bootstrap-repo,2,2,289,125577,1575,2026-01-27,done: TC-100 implementation complete with evidence,Babar Raza,none
feat/TC-200-schemas-and-io,5,2,302,127429,1579,2026-01-27,chore(TC-200): mark taskcard as Done,Babar Raza,none
feat/TC-201-emergency-mode,8,2,312,129268,1583,2026-01-28,done: TC-201 implementation complete with evidence,Babar Raza,none
feat/TC-250-shared-libs-governance,10,2,327,131590,1588,2026-01-28,feat: implement shared data models (TC-250),Babar Raza,none
feat/TC-300-orchestrator-langgraph,12,2,338,133524,1593,2026-01-28,feat: implement TC-300 (Orchestrator graph wiring and run loop),Babar Raza,none
feat/TC-400-repo-scout,26,2,375,145598,1614,2026-01-28,chore: mark TC-400 as Done in STATUS_BOARD,Babar Raza,none
feat/TC-401-clone-resolve-shas,18,2,355,137481,1603,2026-01-28,feat: implement TC-401 (W1.1 Clone inputs and resolve SHAs),Babar Raza,none
feat/TC-402-fingerprint,21,2,361,139567,1607,2026-01-28,chore: mark TC-402 complete on STATUS_BOARD,Babar Raza,none
feat/TC-403-discover-docs,22,2,365,141576,1607,2026-01-28,feat(TC-403): implement documentation discovery in W1 RepoScout,Babar Raza,none
feat/TC-404-discover-examples,24,2,369,143692,1607,2026-01-28,feat: implement TC-404 example discovery worker,Babar Raza,none
feat/TC-410-facts-builder,34,2,396,153546,1648,2026-01-28,chore(TC-410): mark W2 FactsBuilder integrator as Done in STATUS_BOARD,Babar Raza,none
feat/TC-411-extract-claims,28,2,381,147588,1625,2026-01-28,chore(TC-411): Update taskcard status to Done and regenerate STATUS_BOARD,Babar Raza,none
feat/TC-412-map-evidence,30,2,386,149668,1631,2026-01-28,chore: mark TC-412 as Done in taskcard and regenerate STATUS_BOARD,Babar Raza,none
feat/TC-413-detect-contradictions,32,2,391,151485,1641,2026-01-28,chore: update TC-413 taskcard and regenerate STATUS_BOARD,Babar Raza,none
feat/TC-420-snippet-curator,41,2,412,160235,1669,2026-01-28,chore: mark TC-420 complete in STATUS_BOARD,Babar Raza,none
feat/TC-421-extract-doc-snippets,37,2,401,155864,1655,2026-01-28,chore: mark TC-421 complete and update STATUS_BOARD,Babar Raza,none
feat/TC-422-extract-code-snippets,39,2,406,158327,1661,2026-01-28,chore(TC-422): update taskcard status to Done,Babar Raza,none
feat/TC-430-ia-planner,43,2,418,162525,1675,2026-01-28,chore: mark TC-430 as Done in taskcard,Babar Raza,none
feat/TC-440-section-writer,45,2,424,164631,1683,2026-01-28,chore: update TC-440 status to Done in STATUS_BOARD,Babar Raza,none
feat/TC-450-linker-and-patcher,47,2,430,167178,1693,2026-01-28,chore: mark TC-450 as Done (W6_AGENT),Babar Raza,none
feat/TC-460-validator,50,2,436,169140,1704,2026-01-28,chore: mark TC-460 complete and update STATUS_BOARD,Babar Raza,none
feat/TC-470-fixer,55,2,465,175324,1717,2026-01-28,chore: update TC-470 status to Done in STATUS_BOARD,Babar Raza,none
feat/TC-480-pr-manager,57,2,470,177368,1727,2026-01-28,chore: mark TC-480 as Done and regenerate STATUS_BOARD,Babar Raza,none
feat/TC-500-clients-services,16,2,347,135880,1599,2026-01-28,fix: correct base model test to accept alphabetical key ordering with sort_keys=,Babar Raza,none
feat/TC-510-mcp-server-setup,58,2,477,178279,1745,2026-01-28,feat(TC-510): Implement MCP server setup and initialization,Babar Raza,none
feat/TC-511-mcp-tool-registration,59,2,482,179861,1759,2026-01-28,feat: implement TC-511 MCP tool registration,Babar Raza,none
feat/TC-512-mcp-tool-handlers,60,2,486,181655,1759,2026-01-28,feat: implement MCP tool handlers (TC-512),Babar Raza,none
feat/TC-520-telemetry-api-setup,63,2,499,184098,1830,2026-01-28,feat: implement TC-520 local telemetry API setup,Babar Raza,none
feat/TC-521-telemetry-run-endpoints,64,2,506,186267,1830,2026-01-28,feat: implement telemetry API run endpoints (TC-521),Babar Raza,none
feat/TC-522-telemetry-batch-upload,65,2,512,187827,1830,2026-01-28,feat: implement TC-522 - Telemetry API batch upload endpoints,Babar Raza,none
feat/TC-523-telemetry-metadata-endpoints,66,2,516,188933,1830,2026-01-28,feat: implement telemetry metadata and metrics endpoints (TC-523),Babar Raza,none
feat/TC-530-cli-entrypoints,62,2,493,182936,1830,2026-01-28,chore: mark TC-530 as Done (update taskcard status),Babar Raza,none
feat/TC-540-content-path-resolver,69,2,522,190992,1831,2026-01-28,chore(TC-540): update STATUS_BOARD (Done: 26/41),Babar Raza,none
feat/TC-550-hugo-config,71,2,527,192743,1852,2026-01-28,chore(TC-550): update taskcard status to Done and mark acceptance checks complet,Babar Raza,none
feat/TC-560-determinism-harness,74,2,535,195446,1856,2026-01-28,chore(TC-560): mark complete on STATUS_BOARD,Babar Raza,none
feat/TC-570-extended-gates,52,2,450,171731,1707,2026-01-28,chore: update TC-570 status to Done,Babar Raza,none
feat/TC-571-perf-security-gates,53,2,459,173300,1707,2026-01-28,feat: implement TC-571 performance and security validation gates,Babar Raza,none
feat/TC-580-observability,77,2,544,198196,1856,2026-01-28,chore(TC-580): mark complete on STATUS_BOARD,Babar Raza,none
feat/TC-590-security-handling,80,2,556,201331,1856,2026-01-28,chore(TC-590): mark complete on STATUS_BOARD,Babar Raza,none
feat/TC-600-failure-recovery,85,2,587,206681,1908,2026-01-28,chore: save work in progress before merge operation,Babar Raza,none
feat/golden-2pilots-20260130,12,0,413,282643,534,2026-01-31,fix: Handle example_inventory as list or dict in W4,Babar Raza,none
feat/golden-2pilots-20260201,2,0,26,4537,23,2026-02-01,fix: Add TC-900 to INDEX.md,Babar Raza,none
feat/pilot-e2e-golden-3d-20260129,2,1,12,1528,11,2026-01-29,feat: Phase N0 taskcard hygiene + golden capture prep (TC-633),Babar Raza,none
feat/pilot1-hardening-vfv-20260130,1,1,4,227,8,2026-01-30,TC-681: Fix W4 path construction (family + subdomain),Babar Raza,none
feat/tc902_hygiene_20260201,2,0,26,4537,23,2026-02-01,fix: Add TC-900 to INDEX.md,Babar Raza,none
feat/tc902_w4_impl_20260201,2,0,26,4537,23,2026-02-01,fix: Add TC-900 to INDEX.md,Babar Raza,none
fix/env-gates-20260128-1615,132,2,614,211507,1926,2026-01-28,fix: make main fully green (clean-room validation + all tests passing),Babar Raza,none
fix/main-green-20260128-1505,129,2,597,206928,1926,2026-01-28,fix: correct broken markdown links in historical reports (Gate D),Babar Raza,none
fix/pilot1-w4-ia-planner-20260130,2,1,12,1528,11,2026-01-29,feat: Phase N0 taskcard hygiene + golden capture prep (TC-633),Babar Raza,none
impl/tc300-wire-orchestrator-20260128,117,2,699,248010,2007,2026-01-29,fix: strip ANSI codes in CLI help tests for cross-platform compatibility,Babar Raza,none
integrate/main-e2e-20260128-0837,125,2,596,206911,1908,2026-01-28,chore: final staging state before landing to main,Babar Raza,none
```

</details>

---

## Report Metadata

- **Generated by:** Branch analysis script
- **Total branches analyzed:** 51
- **Total commits analyzed:** 2,367+
- **Total code changes:** 7.5M insertions, 76K deletions
- **Duplicate branches found:** 3
- **Safe immediate deletions:** 3
- **Branches requiring investigation:** 48

---

**END OF REPORT**

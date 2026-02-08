# Merge Order Proposal

**Generated:** 2026-02-01
**Strategy:** Single Superset Merge (Recommended)

---

## Recommended Merge Strategy: Single Comprehensive Merge

### Why This Strategy?

1. **impl/tc300-wire-orchestrator-20260128 contains ALL TC work**
   - Superset of 40+ TC feature branches
   - Superset of 3 integration branches
   - 119 unique commits with comprehensive implementation

2. **Simpler than 40+ individual merges**
   - Single merge commit for audit trail
   - One conflict resolution session
   - One test validation

3. **Lower risk than incremental merges**
   - Tested as integrated system
   - Avoids partial integration bugs
   - Clear rollback point

---

## Merge Plan: Primary Path

### Step 1: Pre-Merge Validation

```bash
# Switch to candidate branch
git checkout impl/tc300-wire-orchestrator-20260128

# Verify it's up to date with backup
git rev-parse HEAD
# Should match backup tag: backup/branches/20260201/impl/tc300-wire-orchestrator-20260128

# Run full test suite
python -m pytest -v --tb=short

# Check for test failures
# If tests fail, document failures and decide:
#   - Fix tests and retry
#   - OR switch to fallback strategy (see below)
```

### Step 2: Create Consolidation Branch

```bash
# Return to main
git checkout main

# Ensure main is clean
git status

# Create consolidation branch from main
git checkout -b consolidate/tc-all-features-20260201

# Verify we're on new branch
git branch --show-current  # Should show: consolidate/tc-all-features-20260201
```

### Step 3: Perform Merge

```bash
# Merge impl/tc300 into consolidation branch
git merge impl/tc300-wire-orchestrator-20260128 --no-ff -m "$(cat <<'EOF'
Consolidate all TC feature implementations (TC-100 through TC-600+)

This merge brings in the complete implementation of all task cards
from the impl/tc300-wire-orchestrator-20260128 superset branch.

Includes:
- All TC-* feature implementations (40 task cards)
- Integration work from fix/env-gates and fix/main-green
- E2E integration from integrate/main-e2e
- Orchestrator wiring and workers
- Comprehensive test suite (122+ test files)
- CLI, MCP server, telemetry, and all supporting infrastructure

Branch hierarchy merged:
  TC-100..TC-600 → TC-600 → integration branches → impl/tc300

This consolidation replaces 44 individual feature branches.

Merged-branch: impl/tc300-wire-orchestrator-20260128
Merge-type: superset-consolidation
TC-range: TC-100 to TC-600
EOF
)"

# Note: Merge commit message provides full audit trail
```

### Step 4: Resolve Conflicts (if any)

```bash
# Check for conflicts
git status

# If conflicts exist:
# 1. Review each conflict file
git diff --name-only --diff-filter=U

# 2. Resolve conflicts manually
# 3. Stage resolved files
git add <resolved-files>

# 4. Complete merge
git commit  # Will use message from Step 3
```

### Step 5: Post-Merge Validation

```bash
# Run full test suite on merged code
python -m pytest -v --tb=short

# Check test results
# - All tests should pass
# - If failures, investigate and fix

# Review merge commit
git log -1 --stat

# Verify file count changes
git diff --stat main

# Should see ~700 files changed (matches impl/tc300 stats)
```

### Step 6: Fast-Forward Main

```bash
# Only proceed if tests pass!

# Switch to main
git checkout main

# Fast-forward merge (clean, linear history)
git merge consolidate/tc-all-features-20260201 --ff-only

# Verify main now has the merge
git log -1 --oneline
# Should show the consolidation merge commit
```

### Step 7: Cleanup Obsolete Branches

```bash
# Delete the consolidation branch (no longer needed)
git branch -d consolidate/tc-all-features-20260201

# Delete duplicate branches (already identified)
git branch -D feat/tc902_hygiene_20260201 feat/tc902_w4_impl_20260201 fix/pilot1-w4-ia-planner-20260130

# Delete all TC-* feature branches (now in main via impl/tc300)
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

# Delete integration branches (now in main via impl/tc300)
git branch -D \
  fix/env-gates-20260128-1615 \
  fix/main-green-20260128-1505 \
  integrate/main-e2e-20260128-0837

# Delete the superset branch itself (now in main)
git branch -D impl/tc300-wire-orchestrator-20260128

# Verify final branch count
git branch
# Should show ~5 branches remaining (main + 4 recent active branches)
```

### Step 8: Optional - Push to Remote

```bash
# Push updated main
git push origin main

# Push backup tags (for safety)
git push origin --tags
```

---

## Fallback Strategy: Phased Merge

**Use this if impl/tc300 tests fail or merge is too complex**

### Phase 1: Merge TC-600 (Consolidation Point)

```bash
git checkout main
git checkout -b consolidate/tc-600-and-ancestors
git merge feat/TC-600-failure-recovery --no-ff -m "Merge TC-600 (contains TC-512 through TC-590)"

# Test
python -m pytest -v

# If pass, merge to main
git checkout main
git merge consolidate/tc-600-and-ancestors --ff-only
```

**This brings in 8 TC branches at once.**

### Phase 2: Merge Integration Branches

```bash
git checkout main
git checkout -b consolidate/integration-fixes
git merge fix/env-gates-20260128-1615 --no-ff
git merge fix/main-green-20260128-1505 --no-ff
git merge integrate/main-e2e-20260128-0837 --no-ff

# Test
python -m pytest -v

# If pass, merge to main
git checkout main
git merge consolidate/integration-fixes --ff-only
```

### Phase 3: Merge Remaining TC Branches

For each remaining TC branch (TC-100 through TC-571 not in TC-600):

```bash
# Sort by commit count (smallest first for easier conflict resolution)
# Merge one at a time

git checkout main
git merge feat/TC-100-bootstrap-repo --no-ff -m "Merge TC-100: Bootstrap repo"
python -m pytest -v  # Test after each merge

# Repeat for each branch
```

**Note:** This is labor-intensive (30+ merges) and error-prone. Only use if primary strategy fails.

---

## Alternative Strategy: Cherry-Pick Approach

**Use this if merge conflicts are severe**

### When to Use

- impl/tc300 has insurmountable merge conflicts with main
- Only specific features from impl/tc300 are needed
- Main has diverged significantly

### Process

```bash
# 1. Identify specific commits to cherry-pick
git log main..impl/tc300-wire-orchestrator-20260128 --oneline > /tmp/commits.txt

# 2. Review commit list and select needed commits

# 3. Cherry-pick selected commits
git checkout main
git checkout -b consolidate/cherry-picked-features

# Cherry-pick in order (oldest first)
git cherry-pick <commit-sha-1>
git cherry-pick <commit-sha-2>
# ... continue for needed commits

# 4. Test and merge
python -m pytest -v
git checkout main
git merge consolidate/cherry-picked-features --ff-only
```

**Warning:** This loses the complete history and may miss dependencies between commits.

---

## Conflict Resolution Guidelines

### Expected Conflict Areas

Based on file analysis, expect conflicts in:

1. **plans/taskcards/STATUS_BOARD.md** - Both main and impl/tc300 update this
2. **plans/taskcards/INDEX.md** - Task card registrations
3. **pyproject.toml** - Dependencies may differ
4. **src/launch/** - Core implementation files

### Resolution Strategy

For **STATUS_BOARD.md** and **INDEX.md**:
- Accept impl/tc300 version (has full TC tracking)
- Verify no TCs are lost from main

For **source files**:
- Review carefully - impl/tc300 likely has more complete implementation
- Run tests to verify functionality

For **dependencies (pyproject.toml)**:
- Merge both sets of dependencies
- Use newer versions where conflicts exist
- Test thoroughly after resolution

### Conflict Resolution Commands

```bash
# Accept their version (impl/tc300)
git checkout --theirs <file>
git add <file>

# Accept our version (main)
git checkout --ours <file>
git add <file>

# Manual resolution (open in editor)
# Edit file, resolve markers (<<<<<<, ======, >>>>>>)
git add <file>

# Verify no unresolved conflicts
git status | grep "both modified"
```

---

## Post-Merge Verification Checklist

After merging, verify:

- [ ] All tests pass (`python -m pytest -v`)
- [ ] No new test failures introduced
- [ ] Key functionality works:
  - [ ] CLI entrypoint runs
  - [ ] Orchestrator can be imported
  - [ ] Workers are available
- [ ] Documentation is intact:
  - [ ] STATUS_BOARD reflects merged TCs
  - [ ] INDEX.md lists all TCs
  - [ ] README is current
- [ ] No files accidentally deleted
- [ ] Commit history is clean (check `git log --graph`)

---

## Rollback Plan

If merge creates problems:

### Before Pushing to Remote

```bash
# Reset main to before merge
git checkout main
git reset --hard HEAD~1  # Undo last merge commit

# Or reset to specific commit
git reset --hard <commit-before-merge>

# Restore from backup if needed
git branch <branch-name> backup/branches/20260201/<branch-name>
```

### After Pushing to Remote

```bash
# Create revert commit (safer for shared repos)
git revert -m 1 <merge-commit-sha>

# Or force push (DANGEROUS - coordinate with team)
git reset --hard <commit-before-merge>
git push origin main --force  # Only if sole developer
```

---

## Timeline Estimate

**Primary Strategy (Single Merge):**
- Pre-merge validation: 30 minutes
- Merge operation: 10 minutes
- Conflict resolution: 1-2 hours (if conflicts)
- Post-merge testing: 1 hour
- Cleanup: 15 minutes
- **Total: 2-4 hours**

**Fallback Strategy (Phased Merge):**
- Phase 1 (TC-600): 1-2 hours
- Phase 2 (Integration): 1-2 hours
- Phase 3 (Remaining TCs): 4-8 hours
- **Total: 6-12 hours**

**Recommendation:** Attempt primary strategy first. Much faster if successful.

---

## Success Criteria

Merge is successful when:

1. ✅ All tests pass on merged main
2. ✅ No functionality regression
3. ✅ All TC implementations present in main
4. ✅ Branch count reduced by 90% (47 deleted)
5. ✅ Clean git history (no broken commits)
6. ✅ Backup available for rollback
7. ✅ Documentation updated

---

**END OF MERGE ORDER PROPOSAL**

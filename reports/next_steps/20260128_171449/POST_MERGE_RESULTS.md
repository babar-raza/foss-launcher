# POST-MERGE VERIFICATION RESULTS
**Branch:** impl/tc300-wire-orchestrator-20260128
**Base commit SHA:** c4dad34ccdee7358b34f434d23fdb4b1b8b96539
**Timestamp:** 2026-01-28

## Stage 0: Safety Checks

### 0.1 Branch and Clean Tree
```bash
$ git rev-parse --abbrev-ref HEAD
impl/tc300-wire-orchestrator-20260128

$ git status --porcelain
?? reports/bundles/20260128_171449_emergency_changes.patch

$ git rev-parse HEAD
c4dad34ccdee7358b34f434d23fdb4b1b8b96539
```
**Status:** ✅ PASS - Working tree clean (one untracked .patch file, not pushed)

### 0.2 Large Artifacts Check
```bash
$ git ls-files | grep -E '\.(zip|exe|dll|so|dylib)$|^runs/|launcher\.zip'
runs/.gitkeep
```
**Status:** ✅ PASS - No large artifacts tracked (only expected .gitkeep)

---

## Stage 1: Push + PR Creation

### 1.1 Push Branch
```bash
$ git push origin impl/tc300-wire-orchestrator-20260128
To https://github.com/babar-raza/foss-launcher.git
 * [new branch]      impl/tc300-wire-orchestrator-20260128 -> impl/tc300-wire-orchestrator-20260128
```
**Status:** ✅ PASS

### 1.2 Create PR
```bash
$ gh pr create --base main --head impl/tc300-wire-orchestrator-20260128 \
  --title "TC-300: Make pipeline real + Mock E2E offline pilot" \
  --body "$(cat reports/next_steps/20260128_171449/02_pr_description.md)"
```
**PR URL:** https://github.com/babar-raza/foss-launcher/pull/1
**Status:** ✅ PASS

### 1.3 PR Checks Status
**Initial Status:** IN_PROGRESS → FAILED

**Gate Failures (2/21):**

**❌ Gate D: Markdown link integrity**
- 76 broken links found across multiple markdown files
- Key broken links:
  - `reports/ci_enforcement/20260128-1849/completion_summary.md:13` → `.github/workflows/ci.yml`
  - `reports/impl/20260128_162921/FINAL_SUMMARY.md:16,49` → `specs/state-graph.md`
  - `reports/next_steps/20260128_171449/02_pr_description.md:155-156` → pre_merge_gates files
  - `reports/next_steps/20260128_171449/03_mock_e2e_design.md:98,148,215` → various missing files
  - Multiple broken links in `reports/post_impl/20260128_205133_e2e_hardening/` directory

**❌ Gate Q: CI parity (Guarantee H: canonical commands)**
- Missing canonical install command in `.github/workflows/ci.yml`
- Required: `make install-uv` or `make install`

---

## Stage 1B: Gate Fixes (Pre-Merge)


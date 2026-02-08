# Golden Branch Manual Review Summary
## Branch: feat/golden-2pilots-20260130

**Review Date:** 2026-02-02
**Baseline:** main @ a5f8720

---

## Commit Overview

Total commits to review: **12**

### Commit List (in chronological order):

1. `ccf1cf4` - TC-681: Fix W4 path construction (family + subdomain)
2. `3e51cd3` - feat: Golden process foundation - templates + VFV + approved repos
3. `7c2dba9` - temp: revert to working 3d repo (FOSS repo clone fails)
4. `581682a` - fix: Use approved FOSS repo with 'master' branch ref
5. `9e6d87b` - fix: Use placeholder SHA to trigger HEAD resolution
6. `fc60462` - fix: Use placeholders for all refs (clone --branch bug)
7. `a0e605d` - chore: formalize TC-700-703 taskcards and promote evidence
8. `2442a54` - fix: W4 pass repo_root to load_and_validate_run_config
9. `5b5b601` - fix: W4 handle run_config_obj as dict or object
10. `dafc20c` - debug: Add logging to find list.get() error in W4
11. `c118b0b` - debug: Wrap determine_launch_tier call
12. `d582eca` - fix: Handle example_inventory as list or dict in W4

---

## Key Observations

### Critical Issue: ccf1cf4 vs main's 882a7f6

Both commits have the same message ("TC-681: Fix W4 path construction"), BUT:
- main's `882a7f6` keeps all governance docs, workflows, audit files
- golden's `ccf1cf4` DELETES ~70K lines including:
  - `.claude_code_rules`
  - `.github/workflows/ai-governance-check.yml`
  - `docs/_audit/*` (11K+ lines of docs inventory)
  - `hooks/*` (pre-push, prepare-commit-msg)
  - TC-900 series taskcards
  - Phase 2 branch cleanup evidence
  - `specs/36_repository_url_policy.md`
  - `src/launch/workers/_git/repo_url_validator.py` (615 lines)
  - Many reports and work summaries

**Functional diff in src/tests:** 3382 lines

### Massive Template Commit: 3e51cd3

This commit adds:
- Template families for 3d and note (5 subdomains each)
- VFV automation scripts (run_pilot_vfv.py, run_multi_pilot_vfv.py)
- Pilot config fixes (pinned SHA updates)
- ~3000+ lines of template files

### Debug Commits: dafc20c, c118b0b

These add debug logging that should be EXCLUDED or converted to guarded logging.

### Temp/Workaround Commits: 7c2dba9, 581682a, 9e6d87b, fc60462

These are fixes/workarounds for clone issues with SHA refs.

---

## Integration Strategy

### Phase 1: Reconcile TC-681 (ccf1cf4 vs 882a7f6)

**Decision Required:**
- Main already has TC-681 functional fixes (882a7f6)
- Golden's ccf1cf4 has the same fixes PLUS massive deletions
- Need to decide: keep main's governance files or accept golden's cleanup?

**Recommendation:** SKIP ccf1cf4 entirely OR extract only the 3382-line functional diff if needed.

### Phase 2: Templates (3e51cd3) - Path-Scoped Import

**INCLUDE (path-scoped):**
- `specs/templates/blog.aspose.org/3d/` (all)
- `specs/templates/blog.aspose.org/note/` (all)
- `specs/templates/docs.aspose.org/3d/` (all)
- `specs/templates/docs.aspose.org/note/` (all)
- `specs/templates/kb.aspose.org/3d/` (all)
- `specs/templates/kb.aspose.org/note/` (all)
- `specs/templates/products.aspose.org/3d/` (all)
- `specs/templates/products.aspose.org/note/` (all)
- `specs/templates/releases.aspose.org/3d/` (all)
- `specs/templates/releases.aspose.org/note/` (all)
- `scripts/run_pilot_vfv.py`
- `scripts/run_multi_pilot_vfv.py`
- Pilot config pinned SHA updates (if valuable)

**EXCLUDE:**
- Deletions of existing files (TC-681 taskcard, any governance deletions)
- Any artifacts/reports noise

### Phase 3: Clone Fixes (7c2dba9 through fc60462)

**Decision:** Need to check if these fix real bugs or are just workarounds.

### Phase 4: Formalize Taskcards (a0e605d)

**Decision:** Include if adds valuable taskcards; skip if just moves reports around.

### Phase 5: W4 Fixes (2442a54, 5b5b601, d582eca)

**INCLUDE:** Functional W4 fixes (repo_root, config object handling, example_inventory).

### Phase 6: Debug Commits (dafc20c, c118b0b)

**EXCLUDE:** Pure debug logging commits.

---

## Next Steps

1. Create detailed per-commit review files
2. Extract functional diffs for analysis
3. Decide on governance file deletions (ccf1cf4)
4. Prepare path-scoped import manifest for 3e51cd3
5. Test W4 fixes against current main

---

## Test Requirements

After integration, MUST verify:
- All 1558+ tests still pass
- TC-681 tests (7 tests in test_tc_681_w4_template_enumeration.py)
- TC-430 tests (37 tests in test_tc_430_ia_planner.py)
- No regressions from governance file deletions (if accepted)
- Template enumeration works with new templates

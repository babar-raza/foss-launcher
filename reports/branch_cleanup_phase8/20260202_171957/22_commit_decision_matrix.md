# Golden Branch Commit Decision Matrix
## Integration Plan for feat/golden-2pilots-20260130

**Date:** 2026-02-02
**Main baseline:** a5f8720
**Strategy:** Manual, selective integration

---

| SHA | Slug | Category | Decision | Rationale | Integration Method |
|-----|------|----------|----------|-----------|-------------------|
| ccf1cf4 | TC-681-w4-path-fix | Functional+Cleanup | **EXCLUDE** | Main already has TC-681 @ 882a7f6. Golden version deletes ~70K lines of governance/docs/workflows. Accept main's version to preserve governance. | N/A - skip entirely |
| 3e51cd3 | golden-templates-vfv | Assets+Scripts | **PARTIAL** | Template packs (3d/note) and VFV scripts are valuable. Must import via path-scoped checkout. | Path-scoped: `git checkout 3e51cd3 -- <paths>` |
| 7c2dba9 | temp-revert-3d-repo | Workaround | **EXCLUDE** | Temporary revert/workaround for clone issues. Not needed if clone bugs are fixed. | N/A |
| 581682a | fix-foss-master-ref | Bug Fix | **EVALUATE** | Clone fix for 'master' branch ref. Check if bug still exists on main. | Cherry-pick if needed |
| 9e6d87b | fix-placeholder-sha | Bug Fix | **EVALUATE** | Placeholder SHA workaround. Check if bug still exists on main. | Cherry-pick if needed |
| fc60462 | fix-all-refs-placeholder | Bug Fix | **EVALUATE** | Extended placeholder workaround. Check if bug still exists on main. | Cherry-pick if needed |
| a0e605d | formalize-tc700-703 | Documentation | **PARTIAL** | Adds TC-700-703 taskcards and evidence. Include taskcards only; skip evidence bundles. | Path-scoped: taskcard files only |
| 2442a54 | w4-repo-root-fix | Functional Fix | **INCLUDE** | W4 bug fix: pass repo_root to load_and_validate_run_config. Small, safe. | Cherry-pick |
| 5b5b601 | w4-config-dict-fix | Functional Fix | **INCLUDE** | W4 bug fix: handle run_config_obj as dict or object. Small, safe. | Cherry-pick |
| dafc20c | debug-logging-w4 | Debug | **EXCLUDE** | Debug logging. Not needed in production code. | N/A |
| c118b0b | debug-wrap-tier | Debug | **EXCLUDE** | Debug logging + large artifact files (fl.zip, reports). Skip entirely. | N/A |
| d582eca | w4-example-inventory | Functional Fix | **INCLUDE** | W4 bug fix: handle example_inventory as list or dict. Small, safe. | Cherry-pick |

---

## Summary Statistics

| Decision | Count | Commits |
|----------|-------|---------|
| INCLUDE (cherry-pick) | 3 | 2442a54, 5b5b601, d582eca |
| PARTIAL (path-scoped) | 2 | 3e51cd3, a0e605d |
| EVALUATE (conditional) | 3 | 581682a, 9e6d87b, fc60462 |
| EXCLUDE | 4 | ccf1cf4, 7c2dba9, dafc20c, c118b0b |

---

## Path-Scoped Import Manifest

### From 3e51cd3 (templates + VFV):

**INCLUDE:**
```
specs/templates/blog.aspose.org/3d/
specs/templates/blog.aspose.org/note/
specs/templates/docs.aspose.org/3d/
specs/templates/docs.aspose.org/note/
specs/templates/kb.aspose.org/3d/
specs/templates/kb.aspose.org/note/
specs/templates/products.aspose.org/3d/
specs/templates/products.aspose.org/note/
specs/templates/releases.aspose.org/3d/
specs/templates/releases.aspose.org/note/
scripts/run_pilot_vfv.py
scripts/run_multi_pilot_vfv.py
```

**MAYBE (if config changes are valuable):**
```
specs/pilot-repos/pilot-aspose-3d-foss-python/run_config.pinned.yaml
specs/pilot-repos/pilot-aspose-note-foss-python/run_config.pinned.yaml
```

**EXCLUDE (explicitly skip):**
- Any deletions (e.g., plans/taskcards/TC-681_* if deleted)
- Any artifacts/ or reports/ additions from this commit

### From a0e605d (taskcards):

**INCLUDE:**
```
plans/taskcards/TC-700_template_packs_3d_note.md
plans/taskcards/TC-701_w4_family_aware_paths.md
plans/taskcards/TC-702_validation_report_determinism.md
plans/taskcards/TC-703_pilot_vfv_harness.md
plans/taskcards/STATUS_BOARD.md (update only)
```

**EXCLUDE:**
```
reports/agents/PILOT_OPS_AGENT/TC-703/
reports/agents/PLANNER_AGENT/TC-701/
reports/agents/TEMPLATES_AGENT/TC-700/
reports/agents/VALIDATOR_AGENT/TC-702/
```

---

## Clone Fix Evaluation (581682a, 9e6d87b, fc60462)

**Test procedure:**
1. Check if pilot configs on main use SHA refs or branch names
2. Run a test clone with current main's clone logic
3. If clone succeeds, skip these commits
4. If clone fails with same error, cherry-pick the fixes

**Expected outcome:** SKIP - main likely already has working clone logic from Phase 7 consolidation.

---

## Integration Order

1. **Path-scoped import** (3e51cd3): Templates + scripts
2. **Path-scoped import** (a0e605d): Taskcard files only
3. **Cherry-pick** (2442a54): W4 repo_root fix
4. **Cherry-pick** (5b5b601): W4 config dict fix
5. **Cherry-pick** (d582eca): W4 example_inventory fix
6. *(Conditional)* Evaluate and possibly cherry-pick clone fixes (581682a, 9e6d87b, fc60462)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Template import conflicts with existing templates | LOW | Path-scoped import to family-specific dirs (3d, note) |
| W4 fixes conflict with main | MEDIUM | Review each fix diff before cherry-pick; run TC-681 + TC-430 tests |
| Missing governance files (ccf1cf4 deletion) | HIGH | SKIP ccf1cf4 entirely - keep main's governance intact |
| Clone fixes break existing logic | MEDIUM | Test clone on main first; only apply if needed |
| Test failures after integration | HIGH | Full pytest suite required after each change |

---

## Success Criteria

- [ ] All 1558+ tests pass on staging branch
- [ ] TC-681 tests pass (7 tests in test_tc_681_w4_template_enumeration.py)
- [ ] TC-430 tests pass (37 tests in test_tc_430_ia_planner.py)
- [ ] Templates accessible in specs/templates/<domain>/{3d,note}/
- [ ] VFV scripts executable and functional
- [ ] No governance/workflow files deleted
- [ ] Clean git history with clear commit messages

---

## Rejection Rationale

### ccf1cf4 (TC-681 + massive deletions)
- Main already has functional TC-681 fix (882a7f6)
- Deletes critical governance: .claude_code_rules, AI governance workflow, hooks
- Deletes 11K+ lines of docs audit
- Deletes repo URL validator (615 lines)
- Risk >> benefit

### Debug commits (dafc20c, c118b0b)
- Pure debug/logging additions
- c118b0b adds 1MB+ fl.zip artifact
- No production value
- Easy to exclude

### Temp workarounds (7c2dba9)
- Explicitly marked "temp: revert"
- Not a permanent solution
- Exclude by design

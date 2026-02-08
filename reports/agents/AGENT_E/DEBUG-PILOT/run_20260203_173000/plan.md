# AGENT E (Observability & Ops): DEBUG-PILOT - Investigation Plan

**Date**: 2026-02-03
**Agent**: Agent E (Observability & Ops)
**Task**: Investigate why pilot VFV execution is failing (exit_code=2, no output)

---

## Investigation Plan

### Phase 1: Initial Assessment
1. **Verify pilot configuration exists**
   - Check: `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`
   - Verify config can be loaded and validated

2. **Test VFV script components**
   - Test: Script help (`--help`)
   - Test: Preflight check in isolation
   - Test: Import statements

### Phase 2: Root Cause Analysis
3. **Isolate preflight check**
   - Run preflight_check() function directly
   - Inspect config structure returned by loader
   - Compare expected vs actual field names

4. **Trace execution path**
   - Review run_pilot.py execution logic
   - Check CLI invocation command
   - Examine error messages and diagnostics

### Phase 3: Identify Bugs
5. **Compare config schema to code expectations**
   - Config uses: `github_repo_url`, `site_repo_url`, `workflows_repo_url`
   - VFV script expects: `target_repo`, `source_docs_repo` (MISMATCH!)

6. **Check path resolution**
   - Verify repo_root calculation in workers
   - Check if specs/ resources are found correctly

### Phase 4: Fix and Validate
7. **Fix identified bugs**
   - Update VFV preflight to use correct field names
   - Fix repo_root path resolution (4 parents -> 5 parents)

8. **Re-run VFV with fixes**
   - Execute full 2-run harness
   - Capture detailed diagnostics
   - Document any remaining issues

### Phase 5: Documentation
9. **Create comprehensive evidence**
   - Document root causes
   - Document fixes applied
   - Document remaining blockers
   - Provide clear recommendations

---

## Expected Outcomes

### Success Criteria
- [ ] Root cause of initial VFV failure identified
- [ ] Critical bugs fixed (preflight check, path resolution)
- [ ] VFV runs to completion (even if pilot fails for other reasons)
- [ ] Full diagnostic evidence captured
- [ ] Clear documentation of remaining issues

### Artifacts to Produce
- `plan.md` - This investigation plan
- `evidence.md` - Detailed findings with command outputs
- `self_review.md` - 12-dimension self-scoring
- `commands.sh` - All commands executed during investigation

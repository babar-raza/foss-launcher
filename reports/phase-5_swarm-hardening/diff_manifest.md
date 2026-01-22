# Phase 5 Swarm Hardening - Diff Manifest

**Date**: 2026-01-22
**Phase**: Phase 5 Swarm Hardening

---

## Files Modified

### Binding Documents (1 file)

1. **plans/taskcards/00_TASKCARD_CONTRACT.md**
   - Added: Frontmatter/body consistency rule (lines 32-37)
   - Modified: Preflight validation section (lines 39-44)
   - Removed: "Gate A1 may fail" acceptable failure language
   - Impact: Binding rule changes, affects all taskcard implementations

### Taskcards (35 files)

All taskcards updated to have matching body `## Allowed paths` sections:

1. plans/taskcards/TC-100_bootstrap_repo.md - **MAJOR**: Also removed overlaps (README.md, __main__.py)
2. plans/taskcards/TC-200_schemas_and_io.md
3. plans/taskcards/TC-201_emergency_mode_manual_edits.md
4. plans/taskcards/TC-250_shared_libs_governance.md
5. plans/taskcards/TC-300_orchestrator_langgraph.md
6. plans/taskcards/TC-400_repo_scout_w1.md
7. plans/taskcards/TC-401_clone_and_resolve_shas.md
8. plans/taskcards/TC-402_repo_fingerprint_and_inventory.md
9. plans/taskcards/TC-403_frontmatter_contract_discovery.md
10. plans/taskcards/TC-404_hugo_site_context_build_matrix.md
11. plans/taskcards/TC-410_facts_builder_w2.md
12. plans/taskcards/TC-411_facts_extract_catalog.md
13. plans/taskcards/TC-412_evidence_map_linking.md
14. plans/taskcards/TC-413_truth_lock_compile_minimal.md
15. plans/taskcards/TC-420_snippet_curator_w3.md
16. plans/taskcards/TC-421_snippet_inventory_tagging.md
17. plans/taskcards/TC-422_snippet_selection_rules.md
18. plans/taskcards/TC-430_ia_planner_w4.md
19. plans/taskcards/TC-440_section_writer_w5.md
20. plans/taskcards/TC-450_linker_and_patcher_w6.md
21. plans/taskcards/TC-460_validator_w7.md
22. plans/taskcards/TC-470_fixer_w8.md
23. plans/taskcards/TC-480_pr_manager_w9.md
24. plans/taskcards/TC-500_clients_services.md
25. plans/taskcards/TC-510_mcp_server.md
26. plans/taskcards/TC-520_pilots_and_regression.md
27. plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md
28. plans/taskcards/TC-540_content_path_resolver.md
29. plans/taskcards/TC-550_hugo_config_awareness_ext.md
30. plans/taskcards/TC-560_determinism_harness.md
31. plans/taskcards/TC-570_validation_gates_ext.md
32. plans/taskcards/TC-571_policy_gate_no_manual_edits.md
33. plans/taskcards/TC-580_observability_and_evidence_bundle.md
34. plans/taskcards/TC-590_security_and_secrets.md
35. plans/taskcards/TC-600_failure_recovery_and_backoff.md

**Change Type**: Body `## Allowed paths` section rewritten to match frontmatter
**Lines Changed**: ~5-10 lines per file
**Total Lines Changed**: ~175-350 lines across all taskcards

### Templates (1 file)

36. **plans/_templates/taskcard.md**
    - Added: YAML frontmatter section (lines 1-15)
    - Modified: `## Allowed paths` section with instruction comment (lines 50-56)
    - Impact: Future taskcards will have correct structure by default

### Validation Tools (3 files)

37. **tools/validate_taskcards.py**
    - Added: `extract_body_allowed_paths()` function (~25 lines)
    - Added: `validate_body_allowed_paths_match()` function (~40 lines)
    - Modified: `extract_frontmatter()` signature (returns body now)
    - Modified: `validate_taskcard_file()` to call new validation
    - Lines added: ~65 lines
    - Lines modified: ~10 lines

38. **tools/audit_allowed_paths.py**
    - Added: `is_critical_path()` function (~15 lines)
    - Added: `check_critical_overlaps()` function (~10 lines)
    - Modified: `analyze_overlap()` to track critical overlaps
    - Modified: `generate_report()` to add critical overlap section (~30 lines)
    - Modified: `main()` to fail on critical overlaps (~20 lines modified)
    - Lines added: ~75 lines
    - Lines modified: ~20 lines

39. **tools/validate_swarm_ready.py**
    - Modified: Docstring to document Gate F (lines 8-15)
    - Modified: Gate E description (line 189)
    - Lines modified: ~10 lines

---

## Files Created

### Phase 5 Reports (10 files)

1. reports/phase-5_swarm-hardening/change_log.md (this file)
2. reports/phase-5_swarm-hardening/diff_manifest.md
3. reports/phase-5_swarm-hardening/self_review_12d.md
4. reports/phase-5_swarm-hardening/errata.md
5. reports/phase-5_swarm-hardening/audit_mismatches.py
6. reports/phase-5_swarm-hardening/fix_taskcards.py
7. reports/phase-5_swarm-hardening/gate_outputs/gate_b_validate_taskcards.txt
8. reports/phase-5_swarm-hardening/gate_outputs/gate_e_audit_allowed_paths.txt
9. reports/phase-5_swarm-hardening/gate_outputs/validate_swarm_ready_full.txt
10. reports/phase-5_swarm-hardening/gate_outputs/GATE_SUMMARY.md

---

## Change Statistics

| Category | Files Modified | Files Created | Lines Added | Lines Modified | Lines Deleted |
|----------|---------------|---------------|-------------|----------------|---------------|
| Binding Docs | 1 | 0 | ~10 | ~15 | ~5 |
| Taskcards | 35 | 0 | ~175 | ~175 | ~175 |
| Templates | 1 | 0 | ~15 | ~5 | 0 |
| Validation Tools | 3 | 0 | ~155 | ~40 | 0 |
| Reports | 0 | 10 | ~2500 | 0 | 0 |
| **TOTAL** | **40** | **10** | **~2855** | **~235** | **~180** |

---

## Critical Changes Detail

### TC-100 Overlap Elimination

**File**: plans/taskcards/TC-100_bootstrap_repo.md

**Frontmatter Changes**:
```yaml
# REMOVED from allowed_paths:
- src/launch/__main__.py
- README.md
```

**Body Changes**:
- Removed `src/launch/__main__.py` from `## Allowed paths`
- Removed `README.md` from `## Allowed paths`
- Updated Implementation steps (line ~71-73)
- Updated Outputs section (line ~52)
- Updated Deliverables (line ~87)
- Updated Acceptance checks (line ~97)

**Rationale**: Eliminate critical overlaps with TC-530 (zero tolerance for src/** and repo-root files)

---

## Verification Status

All changes verified by:
- ✅ Gate B: validate_taskcards.py (exit code 0)
- ✅ Gate E: audit_allowed_paths.py (exit code 0)
- ✅ Manual review of all modified files
- ✅ Audit script confirms 0 mismatches, 0 critical overlaps

---

## Rollback Information

**Not applicable** - These are documentation and validation hardening changes only. No code functionality changed. Changes are strictly additive in terms of validation strictness.

To "rollback" would mean:
- Re-introducing mismatches (undesirable)
- Re-introducing critical overlaps (violates swarm safety)
- Re-introducing "acceptable failure" language (misleading to swarm)

**Conclusion**: Changes are permanent improvements, not experimental.

---

## Related Documents

- [change_log.md](change_log.md) - Narrative description of changes
- [errata.md](errata.md) - Policy corrections
- [self_review_12d.md](self_review_12d.md) - Quality assessment
- [gate_outputs/GATE_SUMMARY.md](gate_outputs/GATE_SUMMARY.md) - Validation evidence

---

**Status**: ✅ COMPLETE - All changes documented and verified

# Gaps and Blockers Report

**Date**: 2026-01-24
**Agent**: PRE-IMPLEMENTATION GAP-FILLING AGENT
**Run ID**: 20260124-134932
**Repository**: foss-launcher

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| **PHASE 1 Blockers** | 4 | ✅ ALL RESOLVED |
| **Open Blockers** | 1 | ⚠️ REQ-024 (TC-480 dependency) |
| **Deferred Work** | 1 | ℹ️ PHASE 2 (non-blocking) |

---

## PHASE 1 Blockers (All RESOLVED)

### BLOCKER-1: Worker Package Structure Drift
**Status**: ✅ RESOLVED
**Priority**: HIGH
**Category**: Structural / File Permissions

#### Description
TC-400, TC-410, TC-420 only listed `__init__.py` in allowed_paths, but DEC-005 requires both `__init__.py` and `__main__.py` for each worker package. This would block creation of module entrypoints.

#### Impact if Unresolved
- Agents blocked from creating `__main__.py` files
- E2E commands using `python -m launch.workers.wX_name` would fail
- W1, W2, W3 workers unable to run

#### Root Cause
TC-430 through TC-480 used `/**` pattern (covers all files), but TC-400/410/420 used explicit file lists and omitted `__main__.py` during initial taskcard creation.

#### Resolution
**Files Modified**:
- [plans/taskcards/TC-400_repo_scout_w1.md](../../../plans/taskcards/TC-400_repo_scout_w1.md) - Added `src/launch/workers/w1_repo_scout/__main__.py`
- [plans/taskcards/TC-410_facts_builder_w2.md](../../../plans/taskcards/TC-410_facts_builder_w2.md) - Added `src/launch/workers/w2_facts_builder/__main__.py`
- [plans/taskcards/TC-420_snippet_curator_w3.md](../../../plans/taskcards/TC-420_snippet_curator_w3.md) - Added `src/launch/workers/w3_snippet_curator/__main__.py`

**Verification**:
- ✅ Taskcard validation passed
- ✅ Allowed paths audit passed (no violations)
- ✅ Status board regenerated successfully

#### Binding Spec Reference
- DECISIONS.md (DEC-005): "Each worker is a package with `__init__.py` and `__main__.py`"

---

### BLOCKER-2: Repo_profile Artifact Drift
**Status**: ✅ RESOLVED
**Priority**: HIGH
**Category**: Naming / Contract Alignment

#### Description
Multiple taskcards and scripts referenced legacy artifact name `repo_profile.json`, but W1 contract defines three separate outputs: `repo_inventory.json`, `frontmatter_contract.json`, `site_context.json`.

#### Impact if Unresolved
- CLI argument errors: `--repo-profile` flag doesn't exist
- Schema validation failures: Looking for wrong .schema.json file
- Inter-worker communication failures: W2 can't find W1 outputs
- E2E verification commands would fail

#### Affected Locations
- TC-411: E2E command used `--repo-profile`
- TC-402: Contract reference pointed to `repo_profile.schema.json`
- scripts/add_e2e_sections.py: 5 taskcard entries with wrong artifact names

#### Resolution
**Files Modified**:
- [plans/taskcards/TC-411_facts_extract_catalog.md](../../../plans/taskcards/TC-411_facts_extract_catalog.md)
  - Changed E2E command: `--repo-profile artifacts/repo_profile.json` → `--repo-inventory artifacts/repo_inventory.json`
  - Updated integration boundary: "TC-402 (repo_inventory)"

- [plans/taskcards/TC-402_repo_fingerprint_and_inventory.md](../../../plans/taskcards/TC-402_repo_fingerprint_and_inventory.md)
  - Updated contract reference: `repo_inventory.schema.json`

- [scripts/add_e2e_sections.py](../../../scripts/add_e2e_sections.py)
  - TC-400: Updated to `repo_inventory.json`, `frontmatter_contract.json`, `site_context.json`
  - TC-402: Updated to `repo_inventory.json`
  - TC-410, TC-411, TC-420: Updated upstream references

**Verification**:
- ✅ All taskcard validations passed
- ✅ Schema references point to existing files (specs/schemas/)
- ✅ E2E commands use correct artifact paths

#### Binding Spec Reference
- specs/21_worker_contracts.md: W1 contract defines exact output artifact names

---

### BLOCKER-3: Gate Letter and Script Mismatches
**Status**: ✅ RESOLVED
**Priority**: HIGH
**Category**: Documentation / Validation Alignment

#### Description
specs/34_strict_compliance_guarantees.md had incorrect gate letter assignments and script names that didn't match actual implementation in tools/validate_swarm_ready.py.

#### Impact if Unresolved
- Agents looking for non-existent validation scripts
- Confusion about which gate enforces which guarantee
- Traceability matrix inconsistencies
- False failures when trying to run validation gates

#### Specific Mismatches Found
1. **Guarantee D (Network Allowlist)**: Listed as "Gate M", actually "Gate N"
2. **Guarantee F (Budgets)**: Script listed as `validate_budgets.py`, actually `validate_budgets_config.py`
3. **Guarantee G (Change Budget)**: Listed as "Gate P validates", but Gate P actually validates taskcard version locks

#### Resolution
**Files Modified**:
- [specs/34_strict_compliance_guarantees.md](../../../specs/34_strict_compliance_guarantees.md)
  - Guarantee D: Changed Gate M → Gate N (network allowlist)
  - Guarantee F: Changed script name to `validate_budgets_config.py`
  - Guarantee G: Removed Gate P reference, clarified runtime-only enforcement

**Actual Gate Mapping** (from tools/validate_swarm_ready.py):
```
Gate J → validate_pinned_refs.py (Guarantee A)
Gate K → validate_supply_chain_pinning.py (Guarantee C)
Gate L → validate_secrets_hygiene.py (Guarantee E)
Gate M → validate_no_placeholders_production.py
Gate N → validate_network_allowlist.py (Guarantee D)
Gate O → validate_budgets_config.py (Guarantee F)
Gate P → validate_taskcard_version_locks.py (Guarantee K)
Gate Q → validate_ci_parity.py (Guarantee H)
Gate R → validate_untrusted_code_policy.py (Guarantee J)
```

**Verification**:
- ✅ Spec pack validation passed
- ✅ All gate letter references match validate_swarm_ready.py
- ✅ All script names exist in tools/ directory

#### Binding Spec Reference
- tools/validate_swarm_ready.py: Source of truth for gate letter assignments

---

### BLOCKER-4: TRACEABILITY_MATRIX.md Outdated Evidence
**Status**: ✅ RESOLVED
**Priority**: MEDIUM
**Category**: Documentation / Evidence

#### Description
TRACEABILITY_MATRIX.md listed "to be created" for tests and validation gates that actually exist and are passing. This created false impression of missing implementations.

#### Impact if Unresolved
- Agents might reimplement existing validation scripts
- No visibility into actual implementation status
- Cannot distinguish real gaps (REQ-024) from documentation lag
- Swarm might waste time on already-completed work

#### Requirements Updated
Updated REQ-013 through REQ-024 (Guarantees A-L) with actual implementation status:

| REQ | Guarantee | Before | After |
|-----|-----------|--------|-------|
| REQ-013 | A - Pinned Refs | "to be created" | ✅ tools/validate_pinned_refs.py (Gate J) |
| REQ-014 | B - Path Validation | "to be created" | ✅ src/launch/util/path_validation.py + tests |
| REQ-015 | C - Supply Chain | "to be created" | ✅ tools/validate_supply_chain_pinning.py (Gate K) |
| REQ-016 | D - Network Allowlist | "to be created" | ✅ tools/validate_network_allowlist.py (Gate N) + src/launch/clients/http.py + tests |
| REQ-017 | E - Secrets Scanning | "to be created" | ✅ tools/validate_secrets_hygiene.py (Gate L) |
| REQ-018 | F - Budgets Config | Already ✅ | ✅ No change |
| REQ-019 | G - Change Budget | Already ✅ | ✅ No change |
| REQ-020 | H - CI Parity | "to be created" | ✅ tools/validate_ci_parity.py (Gate Q) |
| REQ-021 | I - Windows Names | Already ✅ | ✅ No change |
| REQ-022 | J - Untrusted Code | "to be created" | ✅ tools/validate_untrusted_code_policy.py (Gate R) + src/launch/util/subprocess.py + tests |
| REQ-023 | K - Taskcard Versioning | "to be created" | ✅ tools/validate_taskcards.py (Gate B) + tools/validate_taskcard_version_locks.py (Gate P) |
| REQ-024 | L - Rollback Contract | "to be created" | ⚠️ BLOCKER - Still pending (see below) |

#### Resolution
**Files Modified**:
- [TRACEABILITY_MATRIX.md](../../../TRACEABILITY_MATRIX.md) - Updated all 12 guarantee entries with actual implementation paths

**Verification**:
- ✅ All listed scripts exist and pass validation
- ✅ All listed test files exist and pass pytest
- ✅ Accurate representation of implementation status

#### Binding Spec Reference
- TRACEABILITY_MATRIX.md itself is the source of truth for requirements mapping

---

## Open Blockers

### BLOCKER-5: REQ-024 (Guarantee L - Rollback Contract)
**Status**: ⚠️ OPEN
**Priority**: MEDIUM (Does not block W1-W8)
**Category**: Missing Implementation

#### Description
Guarantee L requires a rollback contract for PR rejection scenarios. No implementation or tests exist yet.

#### Impact
- Cannot implement TC-480 (W9 PRManager) until this is resolved
- No defined behavior for handling failed PR merges
- Incomplete compliance guarantee coverage (11/12 implemented)

#### Dependency Chain
- **Blocked taskcard**: TC-480 (W9 PRManager)
- **Blocking workers**: W1-W8 can proceed independently
- **Timing**: Must be resolved before TC-480 implementation begins

#### Required Deliverables
1. Rollback contract specification in specs/ (new spec or extend existing)
2. Runtime enforcement in src/launch/workers/w9_pr_manager/
3. Validation gate (if applicable)
4. Unit tests for rollback behavior
5. E2E test for PR rejection scenario

#### Mitigation Strategy
- **Short-term**: Implement W1 through W8 workers (no dependency on rollback)
- **Medium-term**: Design rollback contract before starting TC-480
- **Long-term**: Add rollback E2E test to TC-523 (pilot MCP execution)

#### Action Required
- [ ] Create issue: "Design and implement Guarantee L rollback contract (REQ-024)"
- [ ] Assign to: Architecture review
- [ ] Deadline: Before TC-480 implementation begins

#### Binding Spec Reference
- specs/34_strict_compliance_guarantees.md: Guarantee L defines requirement
- TRACEABILITY_MATRIX.md (REQ-024): Marked as BLOCKER

---

## Deferred Work (Non-Blocking)

### DEFERRED-1: PHASE 2 Taskcard Hardening
**Status**: ℹ️ DEFERRED
**Priority**: LOW (Quality improvement, not blocker)
**Category**: Taskcard Enhancement

#### Description
Add failure modes and review checklists to all 41 taskcards to improve implementation quality and agent guidance.

#### Scope
For each taskcard (TC-100 through TC-602):
1. Add "Failure Modes" section documenting edge cases and error scenarios
2. Add "Review Checklist" section for agent self-verification
3. Ensure consistency with TC-000 CONTRACT template

#### Rationale for Deferral
1. PHASE 1 structural blockers were higher priority
2. Current taskcard contracts are complete per TC-000 template (all required sections present)
3. Failure modes enhance quality but don't block implementation start
4. Can be added iteratively as agents implement workers

#### Impact
- **Low**: Swarm can begin implementation with current contracts
- Agents have sufficient guidance from existing contract sections
- Missing failure modes may result in edge cases being discovered during implementation rather than upfront

#### Recommended Approach
1. Start PHASE 2 in parallel with W1 subtaskcard implementation (TC-401, TC-402, TC-403, TC-404)
2. Use first few taskcards as templates (TC-401, TC-402)
3. Refine failure mode patterns before mid-stage workers (W4-W6)
4. Complete all 41 taskcards before W9 implementation

#### Timeline
- **Week 1**: Add failure modes to TC-401, TC-402 (W1 subtaskcards)
- **Week 2**: Extend to TC-403, TC-404, TC-411, TC-412, TC-413 (complete W1 and W2 subtaskcards)
- **Week 3**: Extend to TC-421, TC-422, TC-430, TC-440 (W3-W5)
- **Week 4**: Complete remaining taskcards (TC-450 through TC-602)

#### Action Required
- [ ] Create issue: "PHASE 2: Add failure modes and review checklists to all taskcards"
- [ ] Assign to: Documentation/Planning track (parallel with swarm implementation)

---

## Gap Analysis Summary

### Gaps Closed (PHASE 1)
- ✅ Worker package structure alignment (3 taskcards)
- ✅ Artifact naming consistency (5 files)
- ✅ Gate letter synchronization (1 spec)
- ✅ Traceability evidence accuracy (1 matrix, 11 requirements)

### Remaining Gaps
- ⚠️ REQ-024 (Guarantee L) - BLOCKER for TC-480 only
- ℹ️ PHASE 2 taskcard hardening - Non-blocking quality improvement

### Risk Assessment
- **High Risk**: None
- **Medium Risk**: REQ-024 must be resolved before TC-480 (managed by dependency ordering)
- **Low Risk**: PHASE 2 deferral (mitigated by iterative addition)

---

## Evidence Files

All blockers verified resolved via validation outputs in:
`reports/pre_impl_review/20260124-134932/final_*.txt`

- ✅ final_validate_spec_pack.txt
- ✅ final_validate_plans.txt
- ✅ final_validate_taskcards.txt (41/41 valid)
- ✅ final_check_markdown_links.txt (270 files, 0 broken)
- ✅ final_audit_allowed_paths.txt (0 violations)
- ✅ final_generate_status_board.txt (39 Ready, 2 Done, 0 Blocked)

---

## Conclusion

**PHASE 1 Blockers**: 4/4 RESOLVED ✅
**Open Blockers**: 1 (REQ-024, does not block W1-W8)
**Deferred Work**: 1 (PHASE 2, non-blocking)

**Repository Status**: READY for swarm implementation

---

**Report Date**: 2026-01-24
**Report Author**: PRE-IMPLEMENTATION GAP-FILLING AGENT
**Evidence Location**: reports/pre_impl_review/20260124-134932/

# Taskcard Remediation Plan — Fix 74 Incomplete Taskcards

**Generated:** 2026-02-03
**Type:** Chat-derived remediation plan
**Parent Plan:** [20260203_taskcard_validation_prevention.md](20260203_taskcard_validation_prevention.md)
**Source:** User request "A) Taskcard Remediation"
**Validation Report:** [reports/taskcard_validation_summary_20260203.md](../../reports/taskcard_validation_summary_20260203.md)

---

## Context

The enhanced validator (TC-PREVENT-INCOMPLETE) identified 74/82 taskcards as incomplete, missing mandatory sections required by the Taskcard Contract ([plans/taskcards/00_TASKCARD_CONTRACT.md](../taskcards/00_TASKCARD_CONTRACT.md)).

**Prevention System Status:** ✅ DEPLOYED (blocks new incomplete taskcards)
**Remediation Target:** Fix existing 74 incomplete taskcards using priority-based approach

---

## Goals

1. **Priority 1 (CRITICAL):** Fix 6 taskcards with no YAML frontmatter (100% blocking)
2. **Priority 2 (HIGH):** Fix 14 taskcards with multiple missing sections (3+ gaps each)
3. **Priority 3 (MEDIUM):** Fix 54 taskcards missing only failure modes (1 gap each)
4. **Verify:** All 82 taskcards pass validation after remediation
5. **Evidence:** Comprehensive before/after validation reports

---

## Priority Breakdown

### Priority 1: CRITICAL (6 taskcards) - NO FRONTMATTER
**Severity:** CRITICAL - Cannot be processed without YAML frontmatter
**Impact:** Breaks all taskcard tooling, validation, and tracking

**Affected Taskcards:**
1. TC-950_fix_vfv_status_truthfulness.md
2. TC-951_pilot_approval_gate_controlled_override.md
3. TC-952_export_content_preview_or_apply_patches.md
4. TC-953_page_inventory_contract_and_quotas.md
5. TC-954_absolute_cross_subdomain_links.md
6. TC-955_storage_model_spec.md

**Remediation Strategy:**
- Read each taskcard to extract title and context
- Generate YAML frontmatter with proper fields (id, title, status, owner, etc.)
- Prepend frontmatter to existing content
- Add any missing mandatory sections if discovered during review

---

### Priority 2: HIGH (14 taskcards) - MULTIPLE MISSING SECTIONS
**Severity:** HIGH - Multiple compliance gaps (3+ missing sections per taskcard)
**Impact:** Cannot track completion criteria, failure modes, or implementation verification

**Affected Taskcards:**
1. TC-921_tc401_clone_sha_used_by_pilots.md (Missing: checklist + failure modes)
2. TC-924_add_legacy_foss_pattern_to_validator.md (Missing: checklist + failure modes)
3. TC-925_fix_w4_load_and_validate_run_config_signature.md (Missing: checklist + failure modes)
4. TC-926_fix_w4_path_construction_blog_and_subdomains.md (Missing: checklist + failure modes)
5. TC-928_taskcard_hygiene_tc924_tc925.md (Missing: checklist + failure modes)
6. TC-930_fix_pilot1_3d_pinned_shas.md (Missing: checklist + failure modes + scope subsections)
7. TC-931_fix_taskcards_index_and_version_locks.md (Missing: checklist + failure modes + scope subsections)
8. TC-932_fix_gate_e_overlaps.md (Missing: checklist + failure modes + scope subsections)
9. TC-934_fix_gate_r_subprocess.md (Missing: checklist + failure modes + scope subsections)
10. TC-938_absolute_cross_subdomain_links.md (Missing: checklist + failure modes + scope subsections)
11. TC-939_storage_model_audit.md (Missing: checklist + failure modes + scope subsections)
12. TC-940_page_inventory_policy.md (Missing: checklist + failure modes + scope subsections)

**Remediation Strategy:**
- Add `## Task-specific review checklist` with 6+ implementation-specific items
- Add `## Failure modes` with 3+ failure modes (detection, resolution, spec ref)
- Restructure `## Scope` to include `### In scope` and `### Out of scope` subsections

---

### Priority 3: MEDIUM (54 taskcards) - MISSING FAILURE MODES ONLY
**Severity:** MEDIUM - Single compliance gap (missing failure modes)
**Impact:** Cannot systematically detect/resolve failures

**Affected Taskcards (by series):**
- **100-series (5):** TC-100, TC-200, TC-201, TC-250, TC-300
- **400-series (13):** TC-400, TC-401, TC-402, TC-403, TC-404, TC-410, TC-411, TC-412, TC-413, TC-420, TC-421, TC-422, TC-430
- **440-480 series (4):** TC-440, TC-450, TC-460, TC-470, TC-480
- **500-series (10):** TC-500, TC-510, TC-511, TC-512, TC-520, TC-522, TC-523, TC-530, TC-540, TC-550
- **560-590 series (4):** TC-560, TC-570, TC-571, TC-580, TC-590
- **600-series (15):** TC-600, TC-610, TC-611, TC-612, TC-620, TC-621, TC-622, TC-630, TC-640, TC-641, TC-642, TC-643, TC-650, TC-660, TC-670
- **700-series (9):** TC-700, TC-701, TC-702, TC-703, TC-704, TC-705, TC-706, TC-707, TC-708
- **900-series (4):** TC-900, TC-901, TC-902, TC-910

**Remediation Strategy:**
- Add `## Failure modes` section with 3+ failure modes
- Each failure mode must include:
  - **Detection:** How to detect this failure (error message, gate failure, test failure)
  - **Resolution:** Steps to resolve the issue
  - **Spec/Gate:** Reference to relevant spec or validation gate

---

## Workstream Breakdown

### Workstream 1: P1 Critical Frontmatter (6 taskcards)
**Owner:** Agent B (Implementation) or Agent D (Docs & Specs)
**Estimated:** 1-2 hours
**Dependencies:** None (can start immediately)
**Parallelizable:** Yes (6 taskcards can be fixed by 2-3 agents in parallel)

**Tasks:**
1. FIX-P1-950: Add frontmatter to TC-950
2. FIX-P1-951: Add frontmatter to TC-951
3. FIX-P1-952: Add frontmatter to TC-952
4. FIX-P1-953: Add frontmatter to TC-953
5. FIX-P1-954: Add frontmatter to TC-954
6. FIX-P1-955: Add frontmatter to TC-955

**Acceptance Criteria:**
- [ ] All 6 taskcards have valid YAML frontmatter
- [ ] Frontmatter includes all required fields (id, title, status, owner, tags, etc.)
- [ ] Taskcards pass frontmatter validation
- [ ] No content loss (existing sections preserved)

---

### Workstream 2: P2 High Multiple Gaps (14 taskcards)
**Owner:** Agent B (Implementation) or Agent D (Docs & Specs)
**Estimated:** 3-4 hours
**Dependencies:** None (can run in parallel with WS1)
**Parallelizable:** Yes (14 taskcards can be split across 2-3 agents)

**Tasks:**
1. FIX-P2-921: Add checklist + failure modes to TC-921
2. FIX-P2-924: Add checklist + failure modes to TC-924
3. FIX-P2-925: Add checklist + failure modes to TC-925
4. FIX-P2-926: Add checklist + failure modes to TC-926
5. FIX-P2-928: Add checklist + failure modes to TC-928
6. FIX-P2-930: Add checklist + failure modes + scope subsections to TC-930
7. FIX-P2-931: Add checklist + failure modes + scope subsections to TC-931
8. FIX-P2-932: Add checklist + failure modes + scope subsections to TC-932
9. FIX-P2-934: Add checklist + failure modes + scope subsections to TC-934
10. FIX-P2-938: Add checklist + failure modes + scope subsections to TC-938
11. FIX-P2-939: Add checklist + failure modes + scope subsections to TC-939
12. FIX-P2-940: Add checklist + failure modes + scope subsections to TC-940

**Acceptance Criteria:**
- [ ] All 14 taskcards have `## Task-specific review checklist` with 6+ items
- [ ] All 14 taskcards have `## Failure modes` with 3+ failure modes
- [ ] 7 taskcards (TC-930 through TC-940) have proper `## Scope` subsections
- [ ] Checklists are implementation-specific (not generic)
- [ ] Failure modes include detection/resolution/spec references

---

### Workstream 3: P3 Medium Failure Modes Only (54 taskcards)
**Owner:** Agent B (Implementation) or Agent D (Docs & Specs)
**Estimated:** 6-8 hours
**Dependencies:** None (can run in parallel with WS1 and WS2)
**Parallelizable:** Yes (54 taskcards can be split across 3-4 agents by series)

**Tasks (grouped by series):**
1. FIX-P3-100s: Add failure modes to 5 taskcards (TC-100, TC-200, TC-201, TC-250, TC-300)
2. FIX-P3-400s: Add failure modes to 13 taskcards (TC-400 through TC-430)
3. FIX-P3-440s: Add failure modes to 4 taskcards (TC-440, TC-450, TC-460, TC-470, TC-480)
4. FIX-P3-500s: Add failure modes to 10 taskcards (TC-500 through TC-550)
5. FIX-P3-560s: Add failure modes to 4 taskcards (TC-560, TC-570, TC-571, TC-580, TC-590)
6. FIX-P3-600s: Add failure modes to 15 taskcards (TC-600 through TC-670)
7. FIX-P3-700s: Add failure modes to 9 taskcards (TC-700 through TC-708)
8. FIX-P3-900s: Add failure modes to 4 taskcards (TC-900, TC-901, TC-902, TC-910)

**Acceptance Criteria:**
- [ ] All 54 taskcards have `## Failure modes` section
- [ ] Each has 3+ failure modes with detection/resolution/spec refs
- [ ] Failure modes are specific to taskcard scope (not generic)
- [ ] All taskcards pass validation

---

### Workstream 4: Verification & Final Report
**Owner:** Agent C (Tests & Verification)
**Estimated:** 30 minutes
**Dependencies:** WS1, WS2, WS3 complete
**Parallelizable:** No (must run after all fixes)

**Tasks:**
1. V-FINAL-1: Run full validator on all 82 taskcards
2. V-FINAL-2: Compare before/after validation reports
3. V-FINAL-3: Create remediation completion report
4. V-FINAL-4: Update STATUS.md with remediation results

**Acceptance Criteria:**
- [ ] Validator shows 82/82 taskcards passing (100%)
- [ ] Before/after comparison shows 74 → 0 incomplete taskcards
- [ ] Remediation report documents all changes
- [ ] STATUS.md updated with completion evidence

---

## Parallel Execution Strategy

### Phase 1: Parallel Remediation (All Priorities) - 6-8 hours
**Execute ALL THREE workstreams in parallel:**
- **WS1 (P1 Critical):** Agent B or D - 6 taskcards, 1-2 hours
- **WS2 (P2 High):** Agent B or D - 14 taskcards, 3-4 hours
- **WS3 (P3 Medium):** Agent B/D/E - 54 taskcards, 6-8 hours (split across agents)

**Rationale:**
- All three priorities are independent (no cross-dependencies)
- Parallelization reduces critical path from 10-14 hours to 6-8 hours
- Multiple agents can work on different priority tiers simultaneously

### Phase 2: Verification & Reporting - 30 minutes
**Execute after Phase 1 complete:**
- **WS4 (Verification):** Agent C - Final validation and reporting

---

## Agent Assignment Strategy

**Option A: Single-Agent Sequential (10-14 hours total)**
- Agent B or D handles all 74 taskcards sequentially
- Advantage: Consistent style and approach
- Disadvantage: Long critical path

**Option B: Multi-Agent Parallel (6-8 hours total) - RECOMMENDED**
- **Agent B:** P1 Critical (6 taskcards) + P2 High (7 taskcards) = 13 taskcards, 4-5 hours
- **Agent D:** P2 High (7 taskcards) + P3 Medium (27 taskcards) = 34 taskcards, 5-6 hours
- **Agent E:** P3 Medium (27 taskcards) = 27 taskcards, 4-5 hours
- **Agent C:** Final verification (all 82 taskcards) = 30 minutes

**Rationale for Option B:**
- Reduces critical path by 40-50%
- P1 (CRITICAL) handled by experienced Agent B for quality
- P2 and P3 split across multiple agents for speed
- Agent C provides independent verification

---

## Success Metrics

**Immediate (Post-Remediation):**
- ✅ 82/82 taskcards pass validation (100%)
- ✅ 0 taskcards with missing YAML frontmatter
- ✅ 0 taskcards with missing failure modes
- ✅ 0 taskcards with missing review checklists
- ✅ All scope sections have proper subsections

**Quality Metrics:**
- Failure modes are specific and actionable (not generic)
- Review checklists are implementation-specific (not boilerplate)
- No content loss during remediation
- All existing sections preserved and enhanced

**3-Month Target:**
- Sustained 100% validation pass rate
- New taskcards blocked by pre-commit hook (0 incomplete merges)
- Remediated taskcards serve as quality examples

---

## Evidence Requirements

### Per-Workstream Evidence
Each workstream must produce:
- `reports/agents/<agent>/REMEDIATION-WS<N>/plan.md`
- `reports/agents/<agent>/REMEDIATION-WS<N>/evidence.md`
- `reports/agents/<agent>/REMEDIATION-WS<N>/self_review.md`
- `reports/agents/<agent>/REMEDIATION-WS<N>/changes_summary.txt` (list of modified files)

### Final Evidence Bundle
`runs/taskcard_remediation_20260203/evidence.zip` containing:
- Before validation report (74 incomplete)
- After validation report (0 incomplete)
- Per-taskcard change summaries
- Self-review reports from all agents
- Final remediation completion report

---

## Acceptance Criteria

**Phase 1 (Remediation):**
1. ✅ All 6 P1 (CRITICAL) taskcards have valid YAML frontmatter
2. ✅ All 14 P2 (HIGH) taskcards have all missing sections added
3. ✅ All 54 P3 (MEDIUM) taskcards have failure modes sections
4. ✅ All sections meet quality standards (specific, not generic)
5. ✅ No content loss or regression in existing sections

**Phase 2 (Verification):**
1. ✅ Validator shows 82/82 taskcards passing (100%)
2. ✅ Before/after comparison shows 74 → 0 incomplete
3. ✅ All 12 self-review dimensions ≥4/5 for each workstream
4. ✅ Remediation completion report generated
5. ✅ STATUS.md updated with final results

---

## Risk Assessment

| Risk | Severity | Mitigation | Owner |
|------|----------|------------|-------|
| Content loss during editing | HIGH | Use Edit tool (not Write), verify diffs | All agents |
| Generic/boilerplate sections | MEDIUM | Review for specificity before marking complete | Self-review |
| Inconsistent quality across agents | MEDIUM | Provide detailed templates and examples | Orchestrator |
| Validator regression | LOW | Test validator before starting remediation | Agent C |
| Time overrun (>8 hours) | MEDIUM | Prioritize P1 and P2, defer P3 if needed | Orchestrator |

---

## Rollback Strategy

If remediation introduces errors or breaks existing taskcards:
1. Git revert all remediation commits
2. Identify problematic changes via git diff
3. Create hardening plan for failed workstreams
4. Re-attempt with refined approach

---

## Next Steps

1. ⏳ **USER APPROVAL:** Proceed with Multi-Agent Parallel execution (Option B)?
2. ⏳ Spawn Agent B for WS1 (P1 Critical - 6 taskcards)
3. ⏳ Spawn Agent B for WS2-part1 (P2 High - 7 taskcards)
4. ⏳ Spawn Agent D for WS2-part2 (P2 High - 7 taskcards)
5. ⏳ Spawn Agent D and Agent E for WS3 (P3 Medium - 54 taskcards split)
6. ⏳ Collect self-reviews from all agents (need 4+/5 on all 12 dimensions)
7. ⏳ Route for hardening if any dimension <4/5
8. ⏳ Spawn Agent C for WS4 (Final Verification)
9. ⏳ Update STATUS.md and PLAN_INDEX.md with completion results
10. ⏳ Create git commit with all remediation changes

---

**Plan Status:** READY FOR USER APPROVAL
**Estimated Duration:** 6-8 hours total (parallel execution)
**Critical Path:** WS3 (P3 Medium) = 6-8 hours
**Risks:** Low (clear validation criteria, prevention system already deployed)

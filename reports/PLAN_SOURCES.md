# Plan Sources Analysis

**Generated:** 2026-01-27
**Orchestrator Run:** Pre-Implementation Hardening (Spec-Level Gaps)

---

## ChatExtractedSteps

From user message: "fix the gaps that do not need implementation since this is pre-implementation hardening"

From assistant gap analysis response:
1. Identified 41 BLOCKER gaps total
2. Determined ~12 gaps are spec-level (can be fixed without code implementation)
3. Remaining ~29 gaps require code implementation (deferred to implementation phase)

From HEALING_PROMPT.md (opened in IDE):
- PHASE 1: 1 gap (implementation required)
- PHASE 2: 5 gaps (all implementation required)
- PHASE 3: 23 gaps (12 spec-level, 11 implementation-level)
- PHASE 4: 12 WARNING gaps (mostly spec-level)

---

## ChatExtractedGapsAndFixes

### Spec-Level BLOCKER Gaps (12 total - can fix now)

#### Spec Quality Gaps (8 gaps)
1. **S-GAP-001**: Add error code `SECTION_WRITER_UNFILLED_TOKENS` to specs/01
2. **S-GAP-003**: Add `spec_ref` field definition to specs/01
3. **S-GAP-006**: Document `validation_profile` field in specs/01 (schema already exists)
4. **S-GAP-010**: Add empty repository edge case to specs/02 + error code `REPO_EMPTY`
5. **S-GAP-013**: Add error code `GATE_DETERMINISM_VARIANCE` to specs/01
6. **S-GAP-016**: Add repository fingerprinting algorithm to specs/02
7. **S-GAP-020**: Add GET /telemetry/{run_id} endpoint to specs/16 + tool schema to specs/24
8. **S-GAP-023**: Create specs/35_test_harness_contract.md

#### Requirements Gaps (4 gaps)
9. **R-GAP-001**: Add REQ-EDGE-001 (empty input handling) to specs/03
10. **R-GAP-002**: Add REQ-GUARD-001 (floating ref detection) to specs/34
11. **R-GAP-003**: Add REQ-HUGO-FP-001 (Hugo config fingerprinting) to specs/09
12. **R-GAP-004**: Add REQ-TMPL-001 (template resolution order) to specs/20

### Implementation-Required Gaps (29 total - deferred)
- 13 runtime validation gates (G-GAP-001 to G-GAP-013)
- 3 feature implementations (F-GAP-021, 022, 023 - require TC-300, TC-480, TC-590)
- 13+ remaining spec quality gaps that require code changes

---

## ChatMentionedFiles

### Primary Plan Source
- `reports/pre_impl_verification/20260127-1724/HEALING_PROMPT.md` (opened in IDE)

### Evidence Sources
- `reports/pre_impl_verification/20260127-1724/GAPS.md` (consolidated gap catalog)
- `reports/pre_impl_verification/20260127-1724/INDEX.md` (navigation)
- `reports/pre_impl_verification/20260127-1724/VERIFICATION_SUMMARY.md` (executive summary)

### Target Files for Fixes
- `specs/01_system_contract.md` (error codes + field definitions)
- `specs/02_repo_ingestion.md` (empty repo edge case + fingerprinting)
- `specs/03_product_facts_and_evidence.md` (empty input handling)
- `specs/09_validation_gates.md` (Hugo config fingerprinting)
- `specs/16_local_telemetry_api.md` (GET endpoint)
- `specs/20_rulesets_and_templates_registry.md` (template resolution)
- `specs/24_mcp_tool_schemas.md` (telemetry tool schema)
- `specs/34_strict_compliance_guarantees.md` (floating ref detection)
- `specs/35_test_harness_contract.md` (NEW FILE - create)

---

## SubstantialityCheck

**Result: SUBSTANTIAL**

**Reasoning:**
- ✅ >= 5 actionable steps: 12 distinct gap fixes identified
- ✅ >= 3 concrete gaps/problems with plausible fixes: 12 gaps with detailed proposed fixes
- ✅ Clear acceptance criteria: HEALING_PROMPT.md provides detailed acceptance criteria for each gap

**Evidence:**
- HEALING_PROMPT.md contains 41 gaps with:
  - Proposed fixes (step-by-step)
  - Acceptance criteria (checkboxes)
  - Evidence requirements (file:line citations)
  - Validation protocol (python tools/validate_swarm_ready.py)

---

## ResolutionStrategy

### Strategy: Create Chat-Derived Hardening Plan

**Action:** Create `plans/from_chat/20260127_preimpl_hardening_spec_gaps.md`

**Scope:** Fix 12 spec-level BLOCKER gaps that do not require code implementation

**Phases:**
1. **Phase 1: Error Codes** (4 gaps) - Add missing error codes to specs/01
2. **Phase 2: Algorithms & Edge Cases** (3 gaps) - Document algorithms and edge cases in specs
3. **Phase 3: Field Definitions** (2 gaps) - Define missing fields in specs/01
4. **Phase 4: New Endpoints & Specs** (3 gaps) - Add endpoint specs and create specs/35

**Parallel Execution:**
- Phase 1-2 can run in parallel (different files)
- Phase 3-4 depend on Phase 1 (error codes must exist first)

**Agents:**
- Agent D (Docs & Specs) will own all spec modifications
- No Agent B (Implementation) or Agent C (Tests) needed for this phase

**Validation:**
- After each phase: `python tools/validate_swarm_ready.py`
- After each phase: `python scripts/validate_spec_pack.py`
- After all phases: Manual review of trace matrices consistency

---

## Plan Source Selection

### PrimaryPlanSource
- **Path:** `plans/from_chat/20260127_preimpl_hardening_spec_gaps.md` (to be created)
- **Type:** Chat-derived hardening plan
- **Why:** User explicitly requested "fix gaps that do not need implementation" - this is a specific, scoped hardening task derived from the verification report

### SecondarySources
1. `reports/pre_impl_verification/20260127-1724/HEALING_PROMPT.md`
   - **Type:** Verification report with gap remediation guidance
   - **Why:** Contains detailed proposed fixes, acceptance criteria, and evidence requirements for all 41 gaps

2. `reports/pre_impl_verification/20260127-1724/GAPS.md`
   - **Type:** Consolidated gap catalog with evidence
   - **Why:** Full gap details with file:line citations for each issue

### MissingCandidates
- None (primary plan will be created from chat + HEALING_PROMPT.md)

---

## Why This Selection Is Correct

1. **Chat is substantial** (12 actionable gap fixes with detailed guidance)
2. **HEALING_PROMPT.md provides implementation guidance** (proposed fixes, acceptance criteria)
3. **User scope is clear** ("gaps that do not need implementation" = spec-level only)
4. **Filtering is required** (12 of 41 gaps are spec-level, rest need code)
5. **Evidence-based** (gap analysis already identified which gaps are spec-level vs implementation)

**Next Steps:**
1. Create chat-derived plan: `plans/from_chat/20260127_preimpl_hardening_spec_gaps.md`
2. Add to PLAN_INDEX.md
3. Create TASK_BACKLOG.md with 4 phases
4. Spawn Agent D for spec modifications
5. Execute with self-review per phase

---
---

# Plan Sources Analysis - Run 2

**Generated:** 2026-02-02
**Orchestrator Run:** Governance Gates Strengthening

---

## ChatExtractedSteps (Run 2)

From approved plan file: `C:\Users\prora\.claude\plans\linear-beaming-plum.md`

**Extracted Phases:**
1. **Phase 1: AG-001 Branch Creation Gate Strengthening**
   - 1.1 Automate hook installation
   - 1.2 Remove hook bypass mechanism
   - 1.3 Add commit service AG-001 validation

2. **Phase 2: Taskcard Requirement Enforcement (4-Layer Defense)**
   - 2.1 Foundation: Schema and loader
   - 2.2 Layer 3: Atomic write enforcement (STRONGEST)
   - 2.3 Layer 1: Run initialization validation
   - 2.4 Layer 4: Gate U post-run audit

3. **Phase 3: Repository Cloning Verification**
   - 3.1 Verify existing implementation
   - 3.2 Minor documentation fixes

---

## SubstantialityCheck (Run 2)

**Assessment**: SUBSTANTIAL ✅ (Plan Mode Approved)

**Evidence**:
- User approved plan in plan mode
- 10+ concrete implementation steps
- 6 gaps identified with fixes
- Clear verification steps per gate
- 3-week timeline defined

---

## PrimaryPlanSource (Run 2)

**File**: `C:\Users\prora\.claude\plans\linear-beaming-plum.md`
**Type**: Implementation Plan (Plan Mode Output - USER APPROVED)
**Status**: ✅ APPROVED and ready for execution

---

## ResolutionStrategy (Run 2)

**Status**: Plan approved, proceeding to task decomposition

**Next Actions:**
1. ✅ Plan file approved
2. Update PLAN_INDEX.md with new run
3. Create TASK_BACKLOG.md with 3 workstreams
4. Spawn agents A/B/C for parallel execution
5. Collect self-reviews and route for hardening

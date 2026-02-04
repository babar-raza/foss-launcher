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

---
---

# Plan Sources Analysis - Run 3

**Generated:** 2026-02-03
**Orchestrator Run:** Taskcard Validation Prevention System

---

## ChatExtractedSteps (Run 3)

From user's initial message: "Review if following issues still exist" + detailed prevention plan

**Extracted Implementation Layers:**

1. **Layer 1: Enhanced Validator** (HIGH PRIORITY)
   - Add MANDATORY_BODY_SECTIONS constant (14 sections)
   - Add validate_mandatory_sections() function
   - Add validate_section_content_quality() function
   - Add --staged-only mode for pre-commit hook
   - Update validate_taskcard_file() to call new validators
   - Test against all 82 existing taskcards

2. **Layer 2: Pre-Commit Hook** (HIGH PRIORITY)
   - Create hooks/pre-commit script
   - Update scripts/install_hooks.py to install it
   - Test hook with valid and invalid taskcards

3. **Layer 3: Developer Tools** (MEDIUM PRIORITY)
   - Create plans/taskcards/00_TEMPLATE.md with all 14 sections
   - Create scripts/create_taskcard.py for interactive creation
   - Test creation workflow

4. **Layer 4: Documentation** (LOW PRIORITY)
   - Update specs/30_ai_agent_governance.md with AG-002 gate
   - Create taskcard creation quickstart guide

**Verification Plan:**
- V1: Enhanced validator catches missing sections on TC-935/936
- V2: Test against intentionally incomplete taskcard
- V3: Pre-commit hook blocks invalid commits

---

## ChatExtractedGapsAndFixes (Run 3)

From assistant's status review response:

### Gap 1: Enhanced Validator Incomplete
**Current State:**
- Validator checks: frontmatter, E2E verification, Integration boundary, allowed paths
- Missing: 10 of 14 mandatory sections NOT validated

**Fix:**
- Add MANDATORY_BODY_SECTIONS list
- Implement validate_mandatory_sections() function
- Call from validate_taskcard_file()

**Files:**
- `tools/validate_taskcards.py` (modify ~100 lines)

### Gap 2: Pre-Commit Hook Missing
**Current State:**
- hooks/pre-push exists (AG-003, AG-004 gates)
- hooks/prepare-commit-msg exists
- No hooks/pre-commit for taskcard validation

**Fix:**
- Create hooks/pre-commit bash script
- Add --staged-only mode to validator
- Update scripts/install_hooks.py

**Files:**
- `hooks/pre-commit` (NEW, ~30 lines bash)
- `tools/validate_taskcards.py` (add --staged-only flag)
- `scripts/install_hooks.py` (~5 lines)

### Gap 3: Developer Tools Missing
**Current State:**
- 00_TASKCARD_CONTRACT.md exists (contract, not template)
- No creation script

**Fix:**
- Create complete template with all sections pre-filled
- Create interactive creation script

**Files:**
- `plans/taskcards/00_TEMPLATE.md` (NEW, ~250 lines)
- `scripts/create_taskcard.py` (NEW, ~100 lines Python)

---

## ChatMentionedFiles (Run 3)

### Files from User's Plan
- `tools/validate_taskcards.py` (enhance)
- `scripts/install_hooks.py` (update)
- `specs/30_ai_agent_governance.md` (document AG-002)
- `hooks/pre-commit` (create)
- `plans/taskcards/00_TEMPLATE.md` (create)
- `scripts/create_taskcard.py` (create)

### Files from IDE Open
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` (context only)
- `reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/plan.md` (different task - pilot debugging)

### Existing Files Referenced
- `plans/taskcards/TC-935_make_validation_report_deterministic.md` (RESOLVED - now complete)
- `plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md` (RESOLVED - now complete)
- `plans/taskcards/TC-937_taskcard_compliance_tc935_tc936.md` (fixed TC-935/936)
- `plans/taskcards/00_TASKCARD_CONTRACT.md` (contract definition)

---

## SubstantialityCheck (Run 3)

**Assessment**: SUBSTANTIAL ✅

**Reasoning:**
- ✅ >= 5 actionable steps: 4 layers × multiple steps each = 10+ total steps
- ✅ >= 3 concrete gaps/problems with plausible fixes: 3 gaps identified with detailed fixes
- ✅ Clear acceptance criteria:
  - V1: Validator catches missing sections
  - V2: Test against incomplete taskcard
  - V3: Hook blocks invalid commits
  - Success metrics defined (0 incomplete taskcards, >95% prevention rate)

**Evidence:**
- User provided 6-8 hour implementation plan with:
  - 5 defense layers
  - 3 verification tests
  - Success criteria (immediate + 3-month metrics)
  - Risk mitigation strategies
  - 6 critical files identified

---

## ResolutionStrategy (Run 3)

### Strategy: Create Chat-Derived Prevention System Plan

**Action:** Create `plans/from_chat/20260203_taskcard_validation_prevention.md`

**Scope:** Implement 4-layer prevention system to prevent incomplete taskcards from being merged

**Priority Breakdown:**
- **High Priority (Layers 1-2):** Enhanced validator + pre-commit hook (3 hours)
- **Medium Priority (Layer 3):** Developer tools (2 hours)
- **Low Priority (Layer 4):** Documentation (1 hour)

**Parallel Execution:**
- Layer 1 and 2 can be developed in parallel (different files)
- Layer 3 depends on Layer 1 (needs validator contract)
- Layer 4 can be done anytime

**Agents:**
- Agent B (Implementation): Validator enhancement, hook creation
- Agent C (Tests & Verification): V1-V3 verification tests
- Agent D (Docs & Specs): Templates, documentation

**Validation Commands:**
```bash
# V1: Enhanced validator
.venv\Scripts\python.exe tools\validate_taskcards.py

# V2: Test incomplete taskcard
echo "---\nid: TC-999\n---\n## Objective\nTest" > plans\taskcards\TC-999_test.md
.venv\Scripts\python.exe tools\validate_taskcards.py
rm plans\taskcards\TC-999_test.md

# V3: Pre-commit hook
git add plans\taskcards\TC-999_test.md
git commit -m "test"
# Should block with validation errors
```

---

## Plan Source Selection (Run 3)

### PrimaryPlanSource
- **Path:** `plans/from_chat/20260203_taskcard_validation_prevention.md` (to be created)
- **Type:** Chat-derived prevention system plan
- **Why:** User provided detailed prevention plan in initial message; assistant confirmed 3 gaps still exist; substantiality check passes

### SecondarySources
1. User's initial message (prevention plan with 5 layers, verification, success criteria)
2. Assistant's status review (confirmed TC-935/936 resolved, 3 gaps remain)
3. `plans/taskcards/00_TASKCARD_CONTRACT.md` (defines 14 mandatory sections)
4. `tools/validate_taskcards.py` (current validator implementation)

### MissingCandidates
- None (plan sources are comprehensive)

---

## Why This Selection Is Correct

1. **Chat is substantial** (4 layers, 10+ steps, 3 verification tests, clear acceptance criteria)
2. **Problem is confirmed** (assistant verified 3 gaps still exist via repo inspection)
3. **User intent is clear** ("Review if following issues still exist" → implied "fix if they do")
4. **Evidence-based gaps** (validator code inspected, hooks directory checked, scripts scanned)
5. **Scope is well-defined** (prevention system only, not fixing existing taskcards)
6. **Success metrics provided** (0 incomplete taskcards, >95% prevention rate, <5s validation)

**Next Steps:**
1. Create chat-derived plan: `plans/from_chat/20260203_taskcard_validation_prevention.md`
2. Update PLAN_INDEX.md with Run 3
3. Create TASK_BACKLOG.md with 4 workstreams (Layers 1-4)
4. Spawn agents B/C/D for parallel execution
5. Execute with V1-V3 verification after each layer
6. Collect self-reviews (need 4+/5 on all 12 dimensions)

---
---

# Plan Sources Analysis - Run 4

**Generated:** 2026-02-04
**Orchestrator Run:** IAPlanner VFV Readiness - Template Path Migration Completion

---

## ChatExtractedSteps (Run 4)

From plan file created in plan mode: `C:\Users\prora\.claude\plans\woolly-stargazing-pumpkin.md`

**Investigation Findings:**
- TC-957, 958, 959, 960: Already correctly implemented (architectural healing fixes)
- TC-950: VFV exit code check already implemented
- User mentioned "blog.aspose.net" but actual work is on "blog.aspose.org"

**Identified Issues:**
1. README content errors in blog.aspose.org/3d and note (say "reference.aspose.org")
2. Obsolete templates in blog.aspose.org/note/__LOCALE__/ (21 files to delete)
3. Need end-to-end VFV verification

**Extracted Phases:**
- **Phase 1**: Fix README content errors (2 files)
- **Phase 2**: Delete obsolete blog templates (21 files)
- **Phase 3**: Verify IAPlanner implementation (read/verify code)
- **Phase 4**: VFV end-to-end verification (run on both pilots)
- **Phase 5**: Run validation gates

---

## ChatExtractedGapsAndFixes (Run 4)

| Gap/Problem | Fix | Evidence | Priority |
|-------------|-----|----------|----------|
| README files claim wrong subdomain | Edit 2 files: "reference.aspose.org" → "blog.aspose.org" | git diff, file content | HIGH |
| 21 obsolete __LOCALE__ templates | Delete specs/templates/blog.aspose.org/note/__LOCALE__/ directory | git status showing 21 deleted files | HIGH |
| VFV determinism unverified | Run VFV on both pilots | VFV JSON reports with status=PASS | HIGH |
| URL paths format unverified | Inspect compute_url_path() at lines 376-416 | Code inspection evidence | MEDIUM |
| Template filter unverified | Inspect TC-957 filter at lines 877-884 | Code inspection evidence | MEDIUM |

---

## ChatMentionedFiles (Run 4)

**Primary Plan File:**
- `C:\Users\prora\.claude\plans\woolly-stargazing-pumpkin.md`

**Files to Edit:**
- `specs/templates/blog.aspose.org/3d/README.md`
- `specs/templates/blog.aspose.org/note/README.md`

**Files to Delete:**
- `specs/templates/blog.aspose.org/note/__LOCALE__/` (entire directory, 21 files)

**Files to Verify (Read-Only):**
- `src/launch/workers/w4_ia_planner/worker.py` (lines 877-884, 376-416, 941-982, 438-489)
- `scripts/run_pilot_vfv.py` (lines 492-506)
- `specs/07_section_templates.md` (lines 194-234)
- `specs/33_public_url_mapping.md`
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`
- `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml`

**Test Files:**
- `tests/unit/workers/test_tc_902_w4_template_enumeration.py`
- `tests/e2e/test_tc_903_vfv.py`

**Validation Scripts:**
- `tools/validate_taskcards.py`

---

## SubstantialityCheck (Run 4)

**Assessment**: SUBSTANTIAL ✅ (Plan Mode Approved - Comprehensive Investigation)

**Criteria:**
- ✅ >= 5 actionable steps: 5 phases with 15+ concrete steps
- ✅ >= 3 concrete gaps/problems: 3 main issues with detailed fixes
- ✅ Clear acceptance criteria: 7 success criteria defined
- ✅ Evidence commands: VFV commands, pytest, git status

**Evidence:**
- Plan file created after thorough 3-agent exploration
- Specific file paths and line numbers identified
- TC references with implementation locations
- Clear before/after states documented
- Risk mitigations provided

---

## ResolutionStrategy (Run 4)

**Strategy**: Execute existing plan file (no chat-derived plan needed)

**Primary Plan Source**: `C:\Users\prora\.claude\plans\woolly-stargazing-pumpkin.md`

**Why this is correct:**
- Plan already exists from plan mode session
- Contains complete implementation guidance
- All file paths, line numbers, commands specified
- No need to create duplicate chat-derived plan

**Execution Approach:**
1. Use existing plan file as PRIMARY source
2. Create TASK_BACKLOG.md from plan phases
3. Spawn agents per phase (D for README/cleanup, A for verification, E for VFV)
4. Execute with evidence-based self-review
5. Route back for hardening if any score <4/5

---

## Plan Source Selection (Run 4)

### PrimaryPlanSource
- **Path**: `C:\Users\prora\.claude\plans\woolly-stargazing-pumpkin.md`
- **Type**: Plan Mode Output (Comprehensive Investigation Plan)
- **Status**: ✅ READY FOR EXECUTION
- **Why**: Created during systematic plan mode investigation with 3 explore agents; contains all implementation details

### SecondarySources
1. `plans/taskcards/TC-957_*.md` - Blog template filter implementation
2. `plans/taskcards/TC-958_*.md` - URL path generation fix
3. `plans/taskcards/TC-959_*.md` - Index page deduplication
4. `plans/taskcards/TC-960_*.md` - Cross-links integration
5. `plans/taskcards/TC-950_fix_vfv_status_truthfulness.md` - VFV exit code check
6. `specs/07_section_templates.md` - Template structure requirements (binding)
7. `specs/33_public_url_mapping.md` - URL path format spec

### MissingCandidates
- None (all plan sources identified and available)

---

## Why This Selection Is Correct

1. **Plan mode approved** - Plan created through systematic investigation
2. **Evidence-based** - 3 explore agents gathered comprehensive context
3. **Complete** - All phases, steps, acceptance criteria, files specified
4. **Verified** - Investigation confirmed TC-957-960 already working
5. **Actionable** - Concrete file edits, deletions, verification steps
6. **Safe** - Cleanup mirrors blog.aspose.org/3d pattern (proven safe)

**Next Actions:**
1. ✅ Plan file ready (no creation needed)
2. Create TASK_BACKLOG.md with workstreams
3. Spawn agents (D: README/cleanup, A: code verification, E: VFV testing)
4. Execute with self-review (12 dimensions, need 4+/5)
5. Collect evidence artifacts

---
---

# Plan Sources Analysis - Orchestrator Run 5 (VFV W4 Template Enumeration Fix)

**Generated:** 2026-02-04  
**Orchestrator Mode:** Multi-Agent Evidence-Based Execution  
**User Directive:** "follow all repo rules including creating and registering all task cards, and executing them with self review"

---

## ChatExtractedSteps (Run 5)

**Last User Request**: ORCHESTRATOR invocation + "follow all repo rules including creating and registering all task cards"

**Last Assistant Discovery**: Found CRITICAL bug in W4 `enumerate_templates()` preventing docs/products/reference/kb from using templates

**Extracted Steps**:
1. Create TC-966 - Fix W4 template enumeration to search placeholder directories
2. Register TC-966 in plans/taskcards/INDEX.md
3. Execute TC-965 (Gate 11 fix) + TC-966 (W4 fix) in parallel
4. Spawn Agent B for both taskcards with 12-D self-review
5. Re-run VFV to verify all 5 sections use templates
6. Validate template_path non-null for all sections in page_plan.json

---

## ChatExtractedGapsAndFixes (Run 5)

| Gap/Problem | Root Cause | Fix | Priority |
|-------------|-----------|-----|----------|
| 4/5 pilot sections have empty/minimal .md content | W4 searches literal `en/python/` dirs that don't exist | TC-966: Fix lines 859-867 to search `__LOCALE__/__PLATFORM__/` | CRITICAL (P0) |
| W4 returns empty template list for docs/products/reference/kb | `enumerate_templates()` hardcodes locale/platform substitution | Search for placeholder directories, then enumerate templates within | CRITICAL (P0) |
| Blog works, others fail | Blog fallback (line 865) finds placeholders by accident | Make all sections use same placeholder discovery pattern | CRITICAL (P0) |
| Gate 11 shows 28 blocker false positives | Scans JSON metadata files, flags `token_mappings` dict keys | TC-965: Add EXCLUDED_PATHS for `artifacts/*.json` | HIGH (P1) |

---

## ChatMentionedFiles (Run 5)

**Critical Bug Location**:
- `src/launch/workers/w4_ia_planner/worker.py`:859-867 (template search paths)

**Template Directories** (verified exist, only placeholders):
- `specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/`
- `specs/templates/docs.aspose.org/3d/__POST_SLUG__/` (6 .md templates found)
- `specs/templates/products.aspose.org/`
- `specs/templates/reference.aspose.org/`
- `specs/templates/kb.aspose.org/`

**Evidence Files**:
- `runs/r_20260204T094825Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5/artifacts/page_plan.json` (template_path=null for 4/5 sections)
- `runs/.../drafts/reference/api-overview.md` (15 lines, empty sections)
- `runs/.../drafts/docs/getting-started.md` (23 lines, repetitive claim fragments)

**Taskcards**:
- `plans/taskcards/TC-965_fix_gate11_json_metadata_false_positives.md` (created, ready)
- `plans/taskcards/TC-966_fix_w4_template_enumeration_placeholder_dirs.md` (needs creation)

---

## SubstantialityCheck (Run 5)

**Assessment**: ✅ **SUBSTANTIAL** (Critical Bug + Clear Fix)

**Criteria Met**:
- ✅ >= 5 actionable steps (create TC, fix bug, test, VFV, validate)
- ✅ >= 3 concrete gaps (W4 enum bug, Gate 11 FP, minimal content)
- ✅ Clear acceptance (all sections have template_path, VFV passes)

**Evidence**:
- Bug location pinpointed (lines 859-867)
- Directory listing proves only placeholder dirs exist
- Blog section demonstrates working pattern
- 4/5 sections broken = 80% impact

---

## ResolutionStrategy (Run 5)

**Strategy**: Create TC-966, spawn Agent B for parallel execution (TC-965 + TC-966), verify with VFV

**Primary Plan Source**: TC-966 (will create next)

**Why This Is Correct**:
1. **Severity**: CRITICAL - 80% of sections unusable
2. **Root Cause**: Confirmed via code inspection + directory verification
3. **Proven Fix**: Blog demonstrates template-driven works
4. **User Directive**: "creating and registering all task cards" - must create TC-966

**Execution**: Multi-agent parallel with 12-D self-review (need 4+/5 all dimensions)

---

## Plan Source Selection (Run 5)

### PrimaryPlanSource
- **Path**: `plans/taskcards/TC-966_fix_w4_template_enumeration_placeholder_dirs.md` (creating next)
- **Type**: Taskcard (critical bug fix)
- **Status**: ⏳ CREATING
- **Why**: CRITICAL P0 bug blocks 80% of pilot content generation

### SecondarySources
1. `plans/taskcards/TC-965_fix_gate11_json_metadata_false_positives.md` (parallel execution)
2. `plans/taskcards/TC-964_fix_w5_blog_template_token_rendering.md` (template pattern reference)
3. `specs/07_section_templates.md` (template structure binding spec)

### MissingCandidates
- None

---

## Why This Selection Is Correct

1. **User Directive**: Explicitly requested taskcard creation + self-review
2. **Severity**: CRITICAL bug affecting 4/5 sections
3. **Evidence**: Bug confirmed via code + directory verification
4. **Proven Pattern**: Blog template enumeration works, extend to all sections
5. **Repo Rules**: Follow taskcard contract, register in INDEX, spawn agents with 12-D review

**Next Actions**:
1. ✅ Plan sources documented
2. ⏳ Create TC-966 taskcard
3. ⏳ Register TC-966 in INDEX.md
4. ⏳ Spawn Agent B for TC-966 + TC-965
5. ⏳ Route back if any dimension <4/5

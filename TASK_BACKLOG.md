# TASK_BACKLOG — Pre-Implementation Hardening

**Repo:** foss-launcher
**Scope:** Pre-implementation hardening (specs/schemas/docs/links/traceability)
**NO IMPLEMENTATION:** This backlog contains ONLY hardening tasks. No feature/validator implementation.
**Source:** [open_issues.md](open_issues.md) + [Pre-Implementation Verification Report](reports/pre_impl_verification/20260126_154500/INDEX.md)
**Created:** 2026-01-27T16:15:00 PKT
**Last Updated:** 2026-01-27T16:15:00 PKT

---

## Task Status Legend
- 🔴 BLOCKED (dependencies not met)
- 🟡 READY (can start now)
- 🟢 IN_PROGRESS (agent working)
- ✅ DONE (evidence verified)
- ⏸️ DEFERRED (postponed)

---

## Workstream 1: Documentation & Templates (Agent D)
**Priority:** P0 (Blockers)
**Dependencies:** None

### TASK-D1: Create missing self-review template (LT-001)
**Status:** 🟡 READY
**Risk:** High (breaks Gate D, blocks taskcards)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** Template file exists, validates, links work
**Affected Paths:**
- reports/templates/self_review_12d.md (CREATE)
- TRACEABILITY_MATRIX.md (links to template)
- plans/taskcards/00_TASKCARD_CONTRACT.md (references template)
- plans/prompts/agent_self_review.md (defines 12 dimensions)

**Acceptance Criteria:**
- [ ] File reports/templates/self_review_12d.md exists
- [ ] Contains all 12 dimensions from plans/prompts/agent_self_review.md
- [ ] No placeholders (violates Gate M)
- [ ] `python tools/check_markdown_links.py` passes (Gate D)
- [ ] Template is usable by agents (clear headings, scoring rubric)

**Required Tests:**
- Run link checker: `python tools/check_markdown_links.py`
- Verify Gate D passes: `python tools/validate_swarm_ready.py` (Gate D only)

**Required Docs/Specs:**
- None (this task creates docs)

**12 Dimensions for Template:**
1. Spec Adherence
2. Determinism
3. Test Coverage
4. Write Fence Compliance
5. Error Handling
6. Documentation
7. Code Quality
8. Security
9. Performance
10. Integration
11. Evidence Quality
12. Acceptance Criteria

---

### TASK-D2: Document .venv + uv flow for preflight (LT-002)
**Status:** 🟡 READY
**Risk:** High (blocks local preflight runs)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** Updated docs, verified fresh clone works
**Affected Paths:**
- README.md (UPDATE - add "Quick Start" section)
- DEVELOPMENT.md (UPDATE or CREATE - detailed setup)
- docs/cli_usage.md (UPDATE - add preflight instructions)

**Acceptance Criteria:**
- [ ] README.md has canonical "Quick Start" section with:
  - `make install-uv` (creates .venv, installs uv, runs uv sync)
  - `.venv/bin/python tools/validate_swarm_ready.py` (runs preflight)
- [ ] DEVELOPMENT.md (or equivalent) explains:
  - .venv = runtime environment location
  - uv.lock = dependency lockfile for deterministic installs
  - Expected failures when not in .venv (Gate 0, Gate K)
- [ ] Fresh clone can follow docs and get green preflight run

**Required Tests:**
- Fresh clone test: `git clone <repo> /tmp/test-clone && cd /tmp/test-clone && make install-uv && .venv/bin/python tools/validate_swarm_ready.py`
- Verify exit 0 when run from .venv

**Required Docs/Specs:**
- Update README.md (MERGE, don't overwrite)
- Update/Create DEVELOPMENT.md
- Update docs/cli_usage.md

---

### TASK-D3: Create missing READMEs (LT-038)
**Status:** 🟡 READY
**Risk:** Medium (reduces navigability)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** 4 READMEs exist and are comprehensive
**Affected Paths:**
- specs/schemas/README.md (CREATE)
- reports/README.md (CREATE)
- docs/README.md (CREATE)
- CONTRIBUTING.md (UPDATE - expand from 3 lines)

**Acceptance Criteria:**
- [ ] specs/schemas/README.md exists with:
  - Schema naming convention
  - Where to add new schemas
  - How to validate schemas (`python scripts/validate_spec_pack.py`)
- [ ] reports/README.md exists with:
  - Directory structure (reports/agents/, reports/pre_impl_verification/, etc.)
  - Naming conventions (timestamps, agent names)
  - What goes where (evidence, self-reviews, artifacts)
- [ ] docs/README.md exists with:
  - Index of all docs
  - When to use each doc
  - How to add new docs
- [ ] CONTRIBUTING.md expanded with:
  - How to add specs
  - How to add taskcards
  - How to run validators
  - PR process

**Required Tests:**
- Verify all links work: `python tools/check_markdown_links.py`

**Required Docs/Specs:**
- None (this task creates docs)

**Estimated Effort:** 4-6 hours total

---

## Workstream 2: Links & Consistency (Agent D)
**Priority:** P0 (Blocker)
**Dependencies:** None

### TASK-D4: Fix 184 broken internal links (LT-030)
**Status:** 🟡 READY
**Risk:** Critical (20.6% link failure rate)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** Link health = 100% (0 broken links)
**Affected Paths:**
- 335 markdown files across repo (see temp_broken_links_categorized.json)

**Breakdown:**
- 129 absolute path links (70%): Convert `/specs/file.md` → `../specs/file.md` (relative)
- 40 directory links (22%): Add file targets `/specs/` → `/specs/README.md`
- 8 broken anchors (4%): Fix heading format mismatches
- 4 line number anchors (2%): Remove `#L123` or replace with section links
- 3 missing relative files (2%): Fix or remove links

**Acceptance Criteria:**
- [ ] `python temp_link_checker.py` exits 0 (0 broken links)
- [ ] Link health = 100%
- [ ] All 184 broken links resolved

**Required Tests:**
- Run link checker: `python temp_link_checker.py`
- Verify output: 0 broken links

**Required Docs/Specs:**
- Update 335 markdown files (use automated link fixer where possible)

**Automation Available:**
- temp_link_checker.py (created by AGENT_L)
- temp_analyze_broken_links.py (created by AGENT_L)
- temp_broken_links_categorized.json (categorized breakdown)

**Estimated Effort:** 9-15 hours

---

## Workstream 3: Specs Quality (Agent D)
**Priority:** P0 (Blocker) + P1 (High)
**Dependencies:** None

### TASK-D5: Add 19 missing algorithms/specs (LT-033)
**Status:** 🟡 READY
**Risk:** Critical (blocks implementation)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** All 19 BLOCKER gaps resolved with spec additions
**Affected Paths:**
- specs/08_patch_engine.md (ADD conflict resolution algorithm)
- specs/11_state_and_events.md (ADD replay algorithm)
- specs/14_mcp_endpoints.md (ADD endpoint specifications for 11 tools)
- specs/24_mcp_tool_schemas.md (ADD error handling specs)
- specs/26_adapter_creation.md (ADD adapter interface)
- specs/27_pilot_execution.md (ADD execution contract)
- specs/28_telemetry.md (ADD failure handling)
- specs/29_tool_version.md (ADD version verification)
- specs/30_navigation.md (ADD update algorithm)
- specs/31_handoff.md (ADD failure recovery)
- And 9 more (see reports/pre_impl_verification/20260126_154500/agents/AGENT_S/GAPS.md)

**Acceptance Criteria (Per Gap):**
- [ ] Algorithm/spec added to target file
- [ ] Contains pseudocode or step-by-step description
- [ ] Uses SHALL/MUST/MUST_NOT (not should/may)
- [ ] Defines failure modes
- [ ] Includes acceptance criteria
- [ ] No placeholders

**Full Gap List:** See reports/pre_impl_verification/20260126_154500/agents/AGENT_S/GAPS.md (S-GAP-008-001 through S-GAP-026-001)

**Required Tests:**
- Validate spec pack: `python scripts/validate_spec_pack.py`

**Required Docs/Specs:**
- Update 10+ spec files (MERGE sections, don't overwrite)

**Estimated Effort:** 2-4 days

---

### TASK-D6: Address 38 MAJOR spec quality gaps (LT-036)
**Status:** 🟡 READY
**Risk:** High (creates ambiguity)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** All 38 MAJOR gaps resolved
**Affected Paths:**
- Multiple spec files (see reports/pre_impl_verification/20260126_154500/agents/AGENT_S/GAPS.md)

**Categories:**
- Vague language ("should/may" without SHALL/MUST alternatives) (7 gaps)
- Missing edge case handling in worker specs (12 gaps)
- Incomplete failure mode specifications (10 gaps)
- Missing best practices (auth, toolchain verification, adapter guide) (9 gaps)

**Acceptance Criteria:**
- [ ] Replace all "should/may" with SHALL/MUST in binding specs
- [ ] Add edge case handling to worker specs (W1-W9)
- [ ] Add failure mode specifications to all worker specs
- [ ] Add best practices sections for authentication, toolchain verification, adapter creation
- [ ] All 38 MAJOR gaps in AGENT_S/GAPS.md resolved

**Full Gap List:** See reports/pre_impl_verification/20260126_154500/agents/AGENT_S/GAPS.md

**Required Tests:**
- Validate spec pack: `python scripts/validate_spec_pack.py`

**Required Docs/Specs:**
- Update multiple spec files (MERGE sections, don't overwrite)

**Estimated Effort:** 1-2 weeks

---

## Workstream 4: Schemas (Agent D)
**Priority:** P0 (Blocker) + P1 (High)
**Dependencies:** None

### TASK-D7: Fix ruleset contract mismatch (LT-023)
**Status:** 🟡 READY
**Risk:** Critical (spec pack internally inconsistent)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** ruleset.v1.yaml validates against schema
**Affected Paths:**
- specs/schemas/ruleset.schema.json (UPDATE - add missing keys)
- specs/20_rulesets_and_templates_registry.md (UPDATE - align with schema)
- specs/rulesets/ruleset.v1.yaml (validate against schema)
- scripts/validate_spec_pack.py (EXTEND - add ruleset validation)

**Acceptance Criteria:**
- [ ] specs/schemas/ruleset.schema.json includes all keys from ruleset.v1.yaml:
  - style, truth, editing, hugo, claims, sections (with proper structure)
- [ ] ruleset.v1.yaml validates against ruleset.schema.json
- [ ] specs/20_rulesets_and_templates_registry.md defines all ruleset keys normatively
- [ ] scripts/validate_spec_pack.py validates rulesets and exits 0
- [ ] No schema validation errors

**Required Tests:**
- Validate spec pack: `python scripts/validate_spec_pack.py`
- Manually validate: `jsonschema -i specs/rulesets/ruleset.v1.yaml specs/schemas/ruleset.schema.json`

**Required Docs/Specs:**
- Update specs/schemas/ruleset.schema.json (MERGE, preserve existing fields)
- Update specs/20_rulesets_and_templates_registry.md (MERGE, add missing sections)

**Estimated Effort:** 2-3 hours

---

### TASK-D8: Fix ProductFacts schema missing field (LT-035)
**Status:** 🟡 READY
**Risk:** High (blocks W2 FactsBuilder)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** Schema validates, includes who_it_is_for field
**Affected Paths:**
- specs/schemas/product_facts.schema.json (UPDATE - add who_it_is_for)

**Acceptance Criteria:**
- [ ] specs/schemas/product_facts.schema.json includes:
  ```json
  "positioning": {
    "type": "object",
    "properties": {
      "who_it_is_for": {
        "type": "string",
        "description": "Target audience description"
      }
    }
  }
  ```
- [ ] Schema validates against spec examples from specs/03_product_facts_and_evidence.md:78-85
- [ ] No schema validation errors

**Required Tests:**
- Validate spec pack: `python scripts/validate_spec_pack.py`

**Required Docs/Specs:**
- Update specs/schemas/product_facts.schema.json (MERGE, preserve existing fields)

**Estimated Effort:** 5 minutes

---

## Workstream 5: Traceability & Consistency (Agent D)
**Priority:** P0 (Blocker) + P1 (High)
**Dependencies:** None

### TASK-D9: Eliminate duplicate REQ-011 (LT-022)
**Status:** 🟡 READY
**Risk:** Critical (breaks deterministic traceability)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** No duplicate REQ headings, links work
**Affected Paths:**
- TRACEABILITY_MATRIX.md (UPDATE - rename duplicate REQ-011)
- specs/reference/system-requirements.md (UPDATE if references exist)

**Acceptance Criteria:**
- [ ] TRACEABILITY_MATRIX.md has no duplicate REQ headings
- [ ] Keep REQ-011 = "Idempotent patch engine"
- [ ] Rename "Two pilot projects" to REQ-011a
- [ ] Update all internal references to use REQ-011a for "Two pilot projects"
- [ ] `python tools/check_markdown_links.py` passes

**Required Tests:**
- Run link checker: `python tools/check_markdown_links.py`
- Grep for duplicate IDs: `grep -E "^## REQ-[0-9]+" TRACEABILITY_MATRIX.md | sort | uniq -d` (should be empty)

**Required Docs/Specs:**
- Update TRACEABILITY_MATRIX.md (MERGE, rename duplicate)

**Estimated Effort:** 30 minutes

---

### TASK-D10: Make plans/traceability_matrix.md complete (LT-024)
**Status:** 🟡 READY
**Risk:** High (eliminates guesswork paths)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** All BINDING specs covered in traceability
**Affected Paths:**
- plans/traceability_matrix.md (UPDATE - add missing BINDING specs)
- specs/README.md (reference for BINDING specs list)

**Acceptance Criteria:**
- [ ] Every BINDING spec from specs/README.md appears in plans/traceability_matrix.md
- [ ] For each BINDING spec entry, include:
  - Implementing taskcards
  - Validating taskcards and/or explicit gate coverage
- [ ] No BINDING spec is missing from traceability
- [ ] Internal consistency maintained

**Required Tests:**
- Cross-check: Compare specs/README.md BINDING list vs plans/traceability_matrix.md entries
- Manual review: Verify each entry has implementing + validating taskcards

**Required Docs/Specs:**
- Update plans/traceability_matrix.md (MERGE, add missing specs)

**Estimated Effort:** 2-3 hours

---

### TASK-D11: Audit TRACEABILITY_MATRIX enforcement claims (LT-027)
**Status:** 🟡 READY
**Risk:** High (prevents false traceability)
**Owner:** Agent D (Docs & Specs)
**Evidence Required:** Enforcement claims are accurate and verifiable
**Affected Paths:**
- TRACEABILITY_MATRIX.md (UPDATE - correct enforcement statements)
- tools/validate_swarm_ready.py (reference for gate list)
- Gate scripts in src/launch/validators/ (reference for actual enforcement)

**Acceptance Criteria:**
- [ ] Audit TRACEABILITY_MATRIX.md enforcement mapping against:
  - tools/validate_swarm_ready.py gate list
  - Actual gate scripts in src/launch/validators/
- [ ] Correct gate IDs and enforcement descriptions
- [ ] For any "runtime enforces X" statement:
  - If runtime does not enforce it yet: mark "NOT YET IMPLEMENTED" and link to implementing taskcard
  - OR implement in launch_validate scaffolding if within non-feature scope
- [ ] Enforcement claims are accurate and verifiable

**Required Tests:**
- Manual audit: Compare TRACEABILITY_MATRIX.md vs tools/validate_swarm_ready.py
- For each gate claim, verify gate script exists and implements check

**Required Docs/Specs:**
- Update TRACEABILITY_MATRIX.md (MERGE, correct enforcement claims)

**Estimated Effort:** 3-4 hours

---

## Deferred Tasks (Require Implementation)

### DEFERRED-1: Implement missing runtime validators (LT-031)
**Status:** ⏸️ DEFERRED (requires implementation)
**Reason:** This is a P0 blocker but requires IMPLEMENTATION (code), not pre-implementation hardening.
**Action:** Move to implementation phase after pre-implementation hardening complete.
**Reference:** reports/pre_impl_verification/20260126_154500/agents/AGENT_G/GAPS.md

### DEFERRED-2: Implement batch execution feature (LT-032)
**Status:** ⏸️ DEFERRED (requires implementation)
**Reason:** This is a P0 blocker but requires IMPLEMENTATION (code + spec creation), not just spec updates.
**Action:** Move to implementation phase after pre-implementation hardening complete.
**Reference:** reports/pre_impl_verification/20260126_154500/agents/AGENT_F/GAPS.md

### DEFERRED-3: Fix validator exit codes + determinism (LT-034)
**Status:** ⏸️ DEFERRED (requires implementation)
**Reason:** This is a P1 high priority but requires CODE CHANGES to validators.
**Action:** Move to implementation phase.
**Reference:** reports/pre_impl_verification/20260126_154500/agents/AGENT_G/GAPS.md

### DEFERRED-4: Address 18 MAJOR feature gaps (LT-037)
**Status:** ⏸️ DEFERRED (requires implementation)
**Reason:** This is a P1 high priority but requires FEATURE IMPLEMENTATION.
**Action:** Move to implementation phase.
**Reference:** reports/pre_impl_verification/20260126_154500/agents/AGENT_F/GAPS.md

---

## Task Assignment Summary

**Agent D (Docs & Specs):**
- TASK-D1: Create self-review template (P0, 1-2 hours)
- TASK-D2: Document .venv + uv flow (P0, 2-3 hours)
- TASK-D3: Create missing READMEs (P1, 4-6 hours)
- TASK-D4: Fix 184 broken links (P0, 9-15 hours)
- TASK-D5: Add 19 missing algorithms/specs (P0, 2-4 days)
- TASK-D6: Address 38 MAJOR spec quality gaps (P1, 1-2 weeks)
- TASK-D7: Fix ruleset contract mismatch (P0, 2-3 hours)
- TASK-D8: Fix ProductFacts schema missing field (P1, 5 minutes)
- TASK-D9: Eliminate duplicate REQ-011 (P0, 30 minutes)
- TASK-D10: Complete plans/traceability_matrix.md (P1, 2-3 hours)
- TASK-D11: Audit TRACEABILITY_MATRIX enforcement (P1, 3-4 hours)

**Total Estimated Effort:** 3-4 weeks (all tasks)

**Parallel Workstreams (First Wave - Quick Wins):**
1. **Quick Fixes (1-2 days):**
   - TASK-D1: Self-review template (1-2 hours)
   - TASK-D2: Document .venv flow (2-3 hours)
   - TASK-D8: ProductFacts schema (5 minutes)
   - TASK-D9: Duplicate REQ-011 (30 minutes)
   - TASK-D7: Ruleset contract (2-3 hours)

2. **Links & READMEs (2-3 days):**
   - TASK-D4: Fix 184 broken links (9-15 hours)
   - TASK-D3: Create READMEs (4-6 hours)

3. **Traceability (1-2 days):**
   - TASK-D10: Complete traceability matrix (2-3 hours)
   - TASK-D11: Audit enforcement claims (3-4 hours)

4. **Specs (2-3 weeks):**
   - TASK-D5: Add 19 missing algorithms (2-4 days)
   - TASK-D6: Address 38 MAJOR gaps (1-2 weeks)

---

## Evidence Requirements (Per Task)

Every task MUST produce:
1. **plan.md**: Assumptions, steps, rollback plan, tests, acceptance checklist
2. **changes.md**: List of files changed with diffs/excerpts
3. **evidence.md**: Commands run + outputs (stdout/stderr)
4. **self_review.md**: 12-dimension scoring (all ≥4/5 required for PASS)
5. **commands.sh** (or .ps1): Exact commands used (append-only)
6. **artifacts/**: Logs, outputs, screenshots

**Output Location:** reports/agents/<agent_name>/<task_id>/run_<timestamp>/

---

## Orchestrator Routing Rules

- **PASS Criteria:** ALL 12 dimensions ≥ 4/5
- **HARDENING Loop:** If ANY dimension <4, create HARDENING_TICKET.md and route back to agent
- **Escalation:** If stuck twice, escalate to different agent
- **Gate:** Merge only when acceptance checklist complete, tests green, evidence present, specs/docs updated

---

## Cross-References

**Source Documents:**
- [open_issues.md](open_issues.md) - Living task list (37 LT issues)
- [Pre-Implementation Verification Report](reports/pre_impl_verification/20260126_154500/INDEX.md) - Full verification results
- [Consolidated Gaps](reports/pre_impl_verification/20260126_154500/GAPS.md) - 176 gaps (30 BLOCKER, 71 MAJOR, 75 MINOR)
- [Healing Instructions](reports/pre_impl_verification/20260126_154500/HEALING_PROMPT.md) - Step-by-step gap remediation

**Agent Reports:**
- [AGENT_R Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_R/REPORT.md) - Requirements extraction
- [AGENT_F Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_F/REPORT.md) - Feature validation
- [AGENT_S Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_S/REPORT.md) - Specs quality audit
- [AGENT_C Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_C/REPORT.md) - Schemas verification
- [AGENT_G Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_G/REPORT.md) - Gates/validators audit
- [AGENT_P Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_P/REPORT.md) - Plans/taskcards audit
- [AGENT_L Report](reports/pre_impl_verification/20260126_154500/agents/AGENT_L/REPORT.md) - Links/consistency audit

---

## Update Log

### 2026-01-27T16:15:00 PKT - Initial Creation
- Created TASK_BACKLOG.md from open_issues.md + pre-implementation verification report
- Identified 11 pre-implementation hardening tasks (no implementation required)
- Deferred 4 tasks requiring implementation to implementation phase
- Assigned all tasks to Agent D (Docs & Specs)
- Organized into 4 parallel workstreams for first wave execution

### 2026-01-27 (Later) - Add Verification Run 20260127-1724 Spec-Level Gaps
- Added new workstream: Spec-Level BLOCKER Gaps from verification run 20260127-1724
- Focus: 12 spec-level gaps that can be fixed without code implementation
- Source: reports/pre_impl_verification/20260127-1724/HEALING_PROMPT.md
- Plan: plans/from_chat/20260127_preimpl_hardening_spec_gaps.md
- These tasks complement the existing workstreams (different verification run, different gaps)

---

## Workstream 6: Spec-Level BLOCKER Gaps (Verification Run 20260127-1724)

**Source:** [Pre-Implementation Verification 20260127-1724](reports/pre_impl_verification/20260127-1724/INDEX.md)
**Plan:** [plans/from_chat/20260127_preimpl_hardening_spec_gaps.md](plans/from_chat/20260127_preimpl_hardening_spec_gaps.md)
**Priority:** P0 (BLOCKER gaps)
**Owner:** Agent D (Docs & Specs)
**Scope:** 12 spec-level BLOCKER gaps (no code implementation required)

### Phase 1: Error Codes (4 tasks)

#### TASK-SPEC-1A: Add SECTION_WRITER_UNFILLED_TOKENS
**Status:** 🟡 READY
**Gap ID:** S-GAP-001
**Risk:** BLOCKER (missing error code)
**Owner:** Agent D
**Affected Paths:** specs/01_system_contract.md
**Acceptance Criteria:**
- [ ] Error code added with severity, when, action
- [ ] specs/21:223 reference is now valid
- [ ] Validation passes: `python tools/validate_swarm_ready.py`

#### TASK-SPEC-1B: Add spec_ref error codes
**Status:** 🟡 READY
**Gap ID:** S-GAP-003
**Risk:** BLOCKER (missing error codes for Guarantee K)
**Owner:** Agent D
**Affected Paths:** specs/01_system_contract.md
**Acceptance Criteria:**
- [ ] SPEC_REF_INVALID and SPEC_REF_MISSING added
- [ ] specs/34:377-385 can reference these codes
- [ ] Validation passes

#### TASK-SPEC-1C: Add REPO_EMPTY error code
**Status:** 🟡 READY
**Gap ID:** S-GAP-010 (partial)
**Risk:** BLOCKER (missing error code)
**Owner:** Agent D
**Affected Paths:** specs/01_system_contract.md
**Acceptance Criteria:**
- [ ] Error code added
- [ ] specs/02 edge case can reference this code
- [ ] Validation passes

#### TASK-SPEC-1D: Add GATE_DETERMINISM_VARIANCE error code
**Status:** 🟡 READY
**Gap ID:** S-GAP-013
**Risk:** BLOCKER (missing error code for Gate T)
**Owner:** Agent D
**Affected Paths:** specs/01_system_contract.md
**Acceptance Criteria:**
- [ ] Error code added
- [ ] specs/09:471-495 reference is now valid
- [ ] Validation passes

**Phase 1 Tests:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
grep -n "SECTION_WRITER_UNFILLED_TOKENS\|SPEC_REF_\|REPO_EMPTY\|GATE_DETERMINISM_VARIANCE" specs/01_system_contract.md
```

---

### Phase 2: Algorithms & Edge Cases (3 tasks)

#### TASK-SPEC-2A: Add repository fingerprinting algorithm
**Status:** 🔴 BLOCKED (depends on TASK-SPEC-1C)
**Gap ID:** S-GAP-016
**Risk:** BLOCKER (breaks caching/validation)
**Owner:** Agent D
**Affected Paths:** specs/02_repo_ingestion.md (after line 145)
**Acceptance Criteria:**
- [ ] 6-step SHA-256 algorithm documented
- [ ] Determinism guaranteed
- [ ] Example JSON included
- [ ] Validation passes

#### TASK-SPEC-2B: Add empty repository edge case
**Status:** 🔴 BLOCKED (depends on TASK-SPEC-1C)
**Gap ID:** S-GAP-010
**Risk:** BLOCKER (undefined behavior)
**Owner:** Agent D
**Affected Paths:** specs/02_repo_ingestion.md (after line 60)
**Acceptance Criteria:**
- [ ] Detection + behavior documented
- [ ] References REPO_EMPTY error code
- [ ] Validation passes

#### TASK-SPEC-2C: Add Hugo config fingerprinting algorithm
**Status:** 🟡 READY
**Gap ID:** R-GAP-003
**Risk:** BLOCKER (breaks determinism)
**Owner:** Agent D
**Affected Paths:** specs/09_validation_gates.md (after line 115)
**Acceptance Criteria:**
- [ ] 5-step canonicalization + SHA-256 algorithm
- [ ] Determinism guaranteed
- [ ] Error cases documented
- [ ] Validation passes

**Phase 2 Tests:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
grep -n "Repository Fingerprinting Algorithm\|Edge Case: Empty Repository\|REQ-HUGO-FP-001" specs/02_repo_ingestion.md specs/09_validation_gates.md
```

---

### Phase 3: Field Definitions (2 tasks)

#### TASK-SPEC-3A: Add spec_ref field definition
**Status:** 🔴 BLOCKED (depends on TASK-SPEC-1B)
**Gap ID:** S-GAP-003
**Risk:** BLOCKER (Guarantee K undefined)
**Owner:** Agent D
**Affected Paths:** specs/01_system_contract.md (field definitions section)
**Acceptance Criteria:**
- [ ] Field definition with type, validation, purpose, example
- [ ] References error codes
- [ ] References Guarantee K
- [ ] Validation passes

#### TASK-SPEC-3B: Document validation_profile field
**Status:** 🟡 READY
**Gap ID:** S-GAP-006
**Risk:** BLOCKER (schema exists but not documented)
**Owner:** Agent D
**Affected Paths:** specs/01_system_contract.md (field definitions section)
**Acceptance Criteria:**
- [ ] 3 enum values explained
- [ ] References run_config.schema.json:458
- [ ] Example included
- [ ] Validation passes

**Phase 3 Tests:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
grep -n "### spec_ref Field\|### validation_profile Field" specs/01_system_contract.md
```

---

### Phase 4: New Endpoints & Specs (5 tasks)

#### TASK-SPEC-4A: Add telemetry GET endpoint
**Status:** 🟡 READY
**Gap ID:** S-GAP-020
**Risk:** BLOCKER (missing endpoint spec)
**Owner:** Agent D
**Affected Paths:** specs/16_local_telemetry_api.md, specs/24_mcp_tool_schemas.md
**Acceptance Criteria:**
- [ ] GET /telemetry/{run_id} endpoint spec'd
- [ ] MCP tool schema added
- [ ] Validation passes

#### TASK-SPEC-4B: Add template resolution order
**Status:** 🟡 READY
**Gap ID:** R-GAP-004
**Risk:** BLOCKER (ambiguous template selection)
**Owner:** Agent D
**Affected Paths:** specs/20_rulesets_and_templates_registry.md (after line 72)
**Acceptance Criteria:**
- [ ] 4-level resolution order
- [ ] Tie-breaking rules
- [ ] Determinism guaranteed
- [ ] Validation passes

#### TASK-SPEC-4C: Create test harness contract spec
**Status:** 🟡 READY
**Gap ID:** S-GAP-023
**Risk:** BLOCKER (Gate T undefined)
**Owner:** Agent D
**Affected Paths:** specs/35_test_harness_contract.md (NEW FILE)
**Acceptance Criteria:**
- [ ] CLI interface documented
- [ ] Comparison rules documented
- [ ] Output format with examples
- [ ] Determinism guaranteed
- [ ] Validation passes

#### TASK-SPEC-4D: Add empty input handling requirement
**Status:** 🟡 READY
**Gap ID:** R-GAP-001
**Risk:** BLOCKER (undefined behavior for empty inputs)
**Owner:** Agent D
**Affected Paths:** specs/03_product_facts_and_evidence.md (after line 183)
**Acceptance Criteria:**
- [ ] REQ-EDGE-001 with 5 acceptance criteria
- [ ] References FACTS_INSUFFICIENT_EVIDENCE
- [ ] Minimum evidence threshold defined
- [ ] Validation passes

#### TASK-SPEC-4E: Add floating ref detection requirement
**Status:** 🟡 READY
**Gap ID:** R-GAP-002
**Risk:** BLOCKER (runtime floating refs not caught)
**Owner:** Agent D
**Affected Paths:** specs/34_strict_compliance_guarantees.md (after line 85)
**Acceptance Criteria:**
- [ ] Preflight vs runtime distinction
- [ ] 4 enforcement rules
- [ ] Floating vs valid patterns
- [ ] Error codes defined
- [ ] Validation passes

**Phase 4 Tests:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
test -f specs/35_test_harness_contract.md && echo "EXISTS" || echo "MISSING"
grep -n "GET /telemetry/\|get_telemetry\|REQ-TMPL-001\|REQ-EDGE-001\|REQ-GUARD-001" specs/16_local_telemetry_api.md specs/24_mcp_tool_schemas.md specs/20_rulesets_and_templates_registry.md specs/03_product_facts_and_evidence.md specs/34_strict_compliance_guarantees.md
```

---

### Workstream 6 Summary

**Total Tasks:** 14 (covering 12 distinct gaps)
**Estimated Duration:** 2-4 hours (all phases sequential)
**Dependencies:** Phase 2-3 depend on Phase 1 error codes

**Execution Order:**
1. Phase 1 → Validate
2. Phase 2 → Validate
3. Phase 3 → Validate
4. Phase 4 → Validate

**Overall Acceptance:** All 12 spec-level BLOCKER gaps from verification 20260127-1724 resolved

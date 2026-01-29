# Pre-Implementation Hardening: Spec-Level BLOCKER Gaps

**Plan ID:** 20260127_preimpl_hardening_spec_gaps
**Created:** 2026-01-27
**Orchestrator:** Pre-Implementation Hardening
**Scope:** Fix 12 spec-level BLOCKER gaps (no code implementation required)

---

## Context

User requested: "fix the gaps that do not need implementation since this is pre-implementation hardening"

Source: Pre-implementation verification run 20260127-1724 identified 41 BLOCKER gaps. Of these:
- **12 gaps are spec-level** (missing definitions, algorithms, edge cases, error codes)
- **29 gaps require implementation** (runtime gates, feature code) - deferred to implementation phase

This plan addresses ONLY the 12 spec-level gaps that can be resolved by updating specs without writing production code.

---

## Goals

1. ✅ Resolve 12 spec-level BLOCKER gaps by updating spec documentation
2. ✅ Add missing error codes to error code registry (specs/01)
3. ✅ Document missing algorithms (fingerprinting, template resolution)
4. ✅ Define missing field definitions (spec_ref, validation_profile)
5. ✅ Add missing edge case handling specifications
6. ✅ Create new spec file (specs/35) for test harness contract
7. ✅ Maintain spec authority and determinism guarantees
8. ✅ Pass all preflight validation gates after each change

---

## Assumptions (VERIFIED)

- ✅ VERIFIED: All 12 gaps have detailed proposed fixes in HEALING_PROMPT.md
- ✅ VERIFIED: Specs are markdown files that can be updated without breaking builds
- ✅ VERIFIED: Preflight validation gates exist to verify spec changes (validate_swarm_ready.py, validate_spec_pack.py)
- ✅ VERIFIED: No runtime gates need to pass for spec-only changes
- ✅ VERIFIED: Schemas are already aligned (AGENT_C found 100% alignment)
- ✅ VERIFIED: Current branch is gpt-reviewed (confirmed via git branch --show-current)

---

## Steps

### Phase 1: Error Codes (4 gaps - HIGH PRIORITY)

Add missing error codes to `specs/01_system_contract.md` error code registry.

#### TASK-1A: Add SECTION_WRITER_UNFILLED_TOKENS (S-GAP-001)
**Files:** specs/01_system_contract.md
**Changes:**
```markdown
SECTION_WRITER_UNFILLED_TOKENS
- Severity: ERROR
- When: LLM output contains unfilled template tokens like {{PRODUCT_NAME}}
- Action: Fail validation, require manual review or re-generation
```
**Evidence:** Grep for "SECTION_WRITER_UNFILLED_TOKENS" in specs/01 after change
**Acceptance:**
- [ ] Error code added to specs/01 with line citation
- [ ] specs/21:223 reference is now valid
- [ ] Validation passes

#### TASK-1B: Add spec_ref field error codes (S-GAP-003)
**Files:** specs/01_system_contract.md
**Changes:** Add error codes related to spec_ref validation
```markdown
SPEC_REF_INVALID
- Severity: ERROR
- When: spec_ref field is not a valid 40-character Git SHA
- Action: Fail validation, require valid commit SHA from foss-launcher repo

SPEC_REF_MISSING
- Severity: ERROR
- When: spec_ref field is required but not present in run_config/page_plan/pr
- Action: Fail validation per Guarantee K
```
**Evidence:** Grep for "SPEC_REF_" in specs/01 after change
**Acceptance:**
- [ ] Error codes added to specs/01
- [ ] specs/34:377-385 can reference these codes

#### TASK-1C: Add REPO_EMPTY error code (S-GAP-010)
**Files:** specs/01_system_contract.md
**Changes:**
```markdown
REPO_EMPTY
- Severity: ERROR
- When: Repository has zero files after clone (excluding .git/ directory)
- Action: Exit with non-zero status, do NOT generate repo_inventory.json
```
**Evidence:** Grep for "REPO_EMPTY" in specs/01 after change
**Acceptance:**
- [ ] Error code added to specs/01
- [ ] Edge case spec in specs/02 can reference this code

#### TASK-1D: Add GATE_DETERMINISM_VARIANCE error code (S-GAP-013)
**Files:** specs/01_system_contract.md
**Changes:**
```markdown
GATE_DETERMINISM_VARIANCE
- Severity: ERROR
- When: Re-running with identical inputs produces different outputs
- Action: Fail Gate T (Test Determinism), block release
- Debug: Compare run artifacts with reference run (use SHA-256 hash diff)
```
**Evidence:** Grep for "GATE_DETERMINISM_VARIANCE" in specs/01 after change
**Acceptance:**
- [ ] Error code added to specs/01
- [ ] specs/09:471-495 reference is now valid

**Phase 1 Validation:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
grep -n "SECTION_WRITER_UNFILLED_TOKENS\|SPEC_REF_\|REPO_EMPTY\|GATE_DETERMINISM_VARIANCE" specs/01_system_contract.md
```

---

### Phase 2: Algorithms & Edge Cases (3 gaps - HIGH PRIORITY)

Document missing algorithms and edge case handling.

#### TASK-2A: Add repository fingerprinting algorithm (S-GAP-016)
**Files:** specs/02_repo_ingestion.md
**Location:** After line 145
**Changes:**
```markdown
### Repository Fingerprinting Algorithm

**Purpose:** Deterministic repo_fingerprint for caching and validation

**Algorithm:**
1. List all non-phantom files (exclude paths in phantom_paths)
2. For each file: Compute `SHA-256(file_path + "|" + file_content)`
3. Sort file hashes lexicographically (C locale, byte-by-byte)
4. Concatenate sorted hashes (no delimiters)
5. Compute `SHA-256(concatenated_hashes)` → **repo_fingerprint**
6. Store in repo_inventory.json field: `repo_fingerprint` (string, 64-char hex)

**Determinism:** Guaranteed (SHA-256 is deterministic, sorting is deterministic)

**Example:**
```json
{
  "repo_fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
}
```
```

**Evidence:** Read specs/02 lines 145-180 after change
**Acceptance:**
- [ ] Algorithm added to specs/02
- [ ] Determinism guarantees documented

#### TASK-2B: Add empty repository edge case (S-GAP-010)
**Files:** specs/02_repo_ingestion.md
**Location:** After line 60
**Changes:**
```markdown
### Edge Case: Empty Repository

**Detection:** Repository has zero files after clone (excluding .git/ directory)

**Behavior:**
1. Emit ERROR with code: `REPO_EMPTY` (see specs/01)
2. Do NOT generate repo_inventory.json (validation fails before artifact creation)
3. Exit with non-zero status code

**Rationale:** Cannot proceed without any content to document. User must provide repository with at least one file.

**Test Case:** See `pilots/pilot-empty-repo/` (TO BE CREATED during implementation phase)
```

**Evidence:** Read specs/02 lines 60-75 after change
**Acceptance:**
- [ ] Edge case documented in specs/02
- [ ] References REPO_EMPTY error code from specs/01

#### TASK-2C: Add Hugo config fingerprinting algorithm (R-GAP-003)
**Files:** specs/09_validation_gates.md
**Location:** After line 115
**Changes:**
```markdown
### REQ-HUGO-FP-001: Hugo Config Fingerprinting Algorithm

**Purpose:** Deterministic fingerprint for Hugo configuration files

**Algorithm:**
1. Load hugo.toml or config.toml (whichever exists, prefer hugo.toml if both)
2. Canonicalize:
   - Sort all keys lexicographically (including nested keys)
   - Normalize booleans (true/false lowercase)
   - Strip comments (lines starting with #)
   - Normalize whitespace (single space after colons)
3. Compute SHA-256 hash of canonical form → **hugo_config_fingerprint**
4. Store in site_context.json field: `hugo_config_fingerprint` (string, 64-char hex)
5. Gate 3 validates fingerprint matches expected value from run_config

**Determinism:** Guaranteed (canonicalization is deterministic, SHA-256 is deterministic)

**Error Cases:**
- No hugo.toml or config.toml found → ERROR: HUGO_CONFIG_MISSING
- Multiple config files with conflicting values → ERROR: HUGO_CONFIG_AMBIGUOUS

**Example:**
```json
{
  "hugo_config_fingerprint": "b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3g4"
}
```
```

**Evidence:** Read specs/09 lines 115-150 after change
**Acceptance:**
- [ ] Algorithm added to specs/09
- [ ] Gate 3 can reference this algorithm

**Phase 2 Validation:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
grep -n "Repository Fingerprinting Algorithm\|Edge Case: Empty Repository\|REQ-HUGO-FP-001" specs/02_repo_ingestion.md specs/09_validation_gates.md
```

---

### Phase 3: Field Definitions (2 gaps - MEDIUM PRIORITY)

Define missing field definitions in specs/01.

#### TASK-3A: Add spec_ref field definition (S-GAP-003)
**Files:** specs/01_system_contract.md
**Location:** In field definitions section (search for existing field definitions)
**Changes:**
```markdown
### spec_ref Field

**Type:** string (required in run_config.json, page_plan.json, pr.json)

**Definition:** Git commit SHA (40-character hex) of the foss-launcher repository containing specs used for this run.

**Validation:**
- Must be exactly 40 hexadecimal characters
- Must resolve to actual commit in github.com/anthropics/foss-launcher
- Enforced by error codes: SPEC_REF_MISSING, SPEC_REF_INVALID (see error registry)

**Purpose:** Version locking for reproducibility (Guarantee K per specs/34:377-385)

**Example:** `"spec_ref": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"`

**Schema Enforcement:** Defined in run_config.schema.json, page_plan.schema.json, pr.schema.json
```

**Evidence:** Read specs/01 field definitions section after change
**Acceptance:**
- [ ] spec_ref definition added to specs/01
- [ ] specs/34:377-385 reference is now unambiguous

#### TASK-3B: Document validation_profile field (S-GAP-006)
**Files:** specs/01_system_contract.md
**Location:** In field definitions section, after spec_ref
**Changes:**
```markdown
### validation_profile Field

**Type:** string (enum: "strict", "standard", "permissive") (optional in run_config.json, default: "standard")

**Definition:** Controls gate enforcement strength per specs/09:14-18

**Values:**
- **strict**: All gates must pass, warnings treated as errors
- **standard**: All gates must pass, warnings are warnings (default)
- **permissive**: Only BLOCKER-severity gates must pass, warnings ignored

**Validation:**
- Must be one of: "strict", "standard", "permissive"
- Enforced by run_config.schema.json enum constraint

**Purpose:** Allows flexible enforcement for different contexts (CI vs local dev vs experimentation)

**Example:** `"validation_profile": "strict"`

**Schema Enforcement:** Defined in run_config.schema.json:458 (already implemented)
```

**Evidence:** Read specs/01 field definitions section + run_config.schema.json:458
**Acceptance:**
- [ ] validation_profile documented in specs/01
- [ ] References existing schema definition (run_config.schema.json:458)

**Phase 3 Validation:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
grep -n "### spec_ref Field\|### validation_profile Field" specs/01_system_contract.md
```

---

### Phase 4: New Endpoints & Specs (3 gaps - MEDIUM PRIORITY)

Add missing endpoint specifications and create new spec file.

#### TASK-4A: Add telemetry GET endpoint (S-GAP-020)
**Files:** specs/16_local_telemetry_api.md, specs/24_mcp_tool_schemas.md
**Changes to specs/16 (after line 35):**
```markdown
### GET /telemetry/{run_id}

**Purpose:** Retrieve snapshot for a specific run

**Request:**
- Method: GET
- Path parameter: run_id (optional, defaults to latest run)
- Example: `GET http://localhost:8765/telemetry/run_20260127_1430`

**Response:**
- Status: 200 OK
- Body: snapshot.json (validates against specs/schemas/snapshot.schema.json)
- Content-Type: application/json

**Error Cases:**
- 404 NOT FOUND: run_id does not exist
- 500 INTERNAL SERVER ERROR: snapshot file corrupted or unreadable

**Example Response:**
```json
{
  "schema_version": "1.0",
  "run_id": "run_20260127_1430",
  "run_state": "completed",
  ...
}
```
```

**Changes to specs/24 (add new tool schema):**
```markdown
### get_telemetry Tool

**Purpose:** MCP tool to retrieve telemetry snapshot for a specific run

**Schema:**
```json
{
  "name": "get_telemetry",
  "description": "Get telemetry snapshot for a run. Returns snapshot.json for the specified run_id (or latest run if not specified).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "run_id": {
        "type": "string",
        "description": "Run ID (optional, defaults to latest run). Example: run_20260127_1430"
      }
    }
  }
}
```

**Returns:** snapshot.json object (see specs/schemas/snapshot.schema.json)
```

**Evidence:** Read specs/16 lines 35-65 + specs/24 after changes
**Acceptance:**
- [ ] GET /telemetry/{run_id} endpoint spec'd in specs/16
- [ ] get_telemetry tool schema added to specs/24

#### TASK-4B: Add template resolution order (R-GAP-004)
**Files:** specs/20_rulesets_and_templates_registry.md
**Location:** After line 72
**Changes:**
```markdown
### REQ-TMPL-001: Template Resolution Order

**Purpose:** Unambiguous template selection when multiple templates could match

**Resolution Order (highest to lowest priority):**
1. **Exact name match**: Template name exactly matches `template_name` field in page_plan.json
2. **Tier match**: Template tier matches `launch_tier` field in page_plan.json
3. **Fallback**: Default template for content type (e.g., default_api_reference.md)
4. **Error**: If no match found, emit ERROR with code TEMPLATE_NOT_FOUND

**Tie-Breaking Rules:**
- If multiple templates match at same priority level:
  - Sort by template name lexicographically (ascending, C locale)
  - Select first template in sorted order
  - Log WARNING: TEMPLATE_AMBIGUOUS_MATCH with all candidates

**Determinism:** Guaranteed (lexicographic sort is deterministic)

**Example Scenario:**
```
Available templates: ["api_basic.md", "api_advanced.md", "api_default.md"]
page_plan.launch_tier: "basic"
page_plan.template_name: null

Resolution:
1. No exact name match (template_name is null)
2. Tier match: ["api_basic.md"] (tier="basic")
3. Select: "api_basic.md"
```

**Error Codes:**
- TEMPLATE_NOT_FOUND: No template matches any rule
- TEMPLATE_AMBIGUOUS_MATCH: Multiple templates at same priority (warning, not error)
```

**Evidence:** Read specs/20 lines 72-110 after change
**Acceptance:**
- [ ] Resolution order added to specs/20
- [ ] Tie-breaking rules documented
- [ ] Determinism guaranteed

#### TASK-4C: Create test harness contract spec (S-GAP-023)
**Files:** specs/35_test_harness_contract.md (NEW FILE)
**Changes:** Create complete spec per HEALING_PROMPT.md:385-489
**Content:** (see HEALING_PROMPT.md for full content)
- CLI interface
- Comparison rules
- Output format
- Determinism guarantees

**Evidence:** File exists at specs/35_test_harness_contract.md
**Acceptance:**
- [ ] specs/35 created with complete test harness contract
- [ ] specs/09:471-495 now has complete spec reference

#### TASK-4D: Add empty input handling requirement (R-GAP-001)
**Files:** specs/03_product_facts_and_evidence.md
**Location:** After line 183
**Changes:**
```markdown
### REQ-EDGE-001: Empty Input Handling for ProductFacts

**Scenario:** Repository has no README, no code files, or insufficient evidence for fact extraction

**Behavior:**
1. **Detection**: After scanning repository, zero facts can be extracted (all fact fields are empty/null)
2. **Validation**: Check minimum evidence threshold:
   - Require at least 1 claim with evidence citation
   - If threshold not met, emit ERROR with code: FACTS_INSUFFICIENT_EVIDENCE
3. **Output**: Do NOT generate product_facts.json (validation fails before artifact creation)
4. **Exit**: Exit with non-zero status code

**Minimum Evidence Threshold:**
- At least 1 claim with file:line evidence citation
- Claims without evidence do NOT count toward threshold

**Rationale:** Cannot generate meaningful documentation without any factual basis. User must provide repository with documentable content.

**Error Code:** FACTS_INSUFFICIENT_EVIDENCE (see specs/01)

**Test Case:** See `pilots/pilot-empty-facts/` (TO BE CREATED during implementation phase)

**Acceptance Criteria:**
1. Empty repository → REPO_EMPTY error (see specs/02)
2. Repository with files but no extractable facts → FACTS_INSUFFICIENT_EVIDENCE error
3. Repository with at least 1 valid claim → product_facts.json generated
4. All generated claims have evidence citations (no orphan claims)
5. Pilot test demonstrates behavior
```

**Evidence:** Read specs/03 lines 183-220 after change
**Acceptance:**
- [ ] REQ-EDGE-001 added to specs/03
- [ ] 5 acceptance criteria documented
- [ ] References FACTS_INSUFFICIENT_EVIDENCE error code

#### TASK-4E: Add floating ref detection requirement (R-GAP-002)
**Files:** specs/34_strict_compliance_guarantees.md
**Location:** After line 85
**Changes:**
```markdown
### REQ-GUARD-001: Floating Reference Detection (Preflight + Runtime)

**Purpose:** Prevent floating Git references (branches, tags) that could produce non-deterministic results

**Preflight Detection (Gate J):**
Scans configuration files BEFORE pipeline execution:
- run_config.json: repo_url, spec_ref
- pilots/*.json: repo_url
- taskcards/*.md: repo references in allowed_paths

**Runtime Detection (NEW):**
Scans generated content DURING pipeline execution:
- LLM-generated patches: Git URLs in imports, submodules, dependencies
- Evidence citations: Git references in product_facts.json, truth_lock_report.json
- Page content: Git URLs embedded in generated markdown

**Enforcement Rules:**
1. Preflight check is mandatory (Gate J must pass to start pipeline)
2. Runtime check supplements (not duplicates) preflight
3. Runtime check catches floating refs introduced by LLM generation
4. Runtime floating ref → ERROR: GUARD_FLOATING_REF_RUNTIME

**Floating Reference Patterns (BLOCK):**
- Branch names: `refs/heads/main`, `origin/develop`
- Tag names without SHA: `v1.0.0` (without commit SHA)
- HEAD references: `HEAD`, `@{upstream}`
- Relative references: `HEAD~1`, `main~5`

**Valid Reference Patterns (ALLOW):**
- Full commit SHA (40 hex chars): `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0`
- Short SHA with pin: `a1b2c3d` (only if accompanied by full SHA in metadata)

**Error Codes:**
- GUARD_FLOATING_REF_PREFLIGHT: Detected during Gate J (preflight)
- GUARD_FLOATING_REF_RUNTIME: Detected during pipeline execution (new)

**Test Cases:**
- Preflight: run_config with branch name → blocked before pipeline starts
- Runtime: LLM generates patch with `import from github.com/user/repo/main` → blocked before patch written
```

**Evidence:** Read specs/34 lines 85-135 after change
**Acceptance:**
- [ ] REQ-GUARD-001 added to specs/34
- [ ] Preflight vs runtime distinction clear
- [ ] 4 enforcement rules documented
- [ ] Error codes defined

**Phase 4 Validation:**
```bash
python tools/validate_swarm_ready.py
python scripts/validate_spec_pack.py
test -f specs/35_test_harness_contract.md && echo "specs/35 exists" || echo "specs/35 missing"
grep -n "GET /telemetry/" specs/16_local_telemetry_api.md
grep -n "get_telemetry" specs/24_mcp_tool_schemas.md
grep -n "REQ-TMPL-001\|REQ-EDGE-001\|REQ-GUARD-001" specs/20_rulesets_and_templates_registry.md specs/03_product_facts_and_evidence.md specs/34_strict_compliance_guarantees.md
```

---

## Acceptance Criteria

### Per-Task Acceptance
- [ ] Phase 1: All 4 error codes added to specs/01 and findable via grep
- [ ] Phase 2: All 3 algorithms/edge cases documented with determinism guarantees
- [ ] Phase 3: Both field definitions added to specs/01 with examples
- [ ] Phase 4: All endpoints, requirements, and specs/35 created

### Overall Acceptance
- [ ] All 12 spec-level BLOCKER gaps resolved
- [ ] All preflight validation gates pass: `python tools/validate_swarm_ready.py`
- [ ] Spec pack validation passes: `python scripts/validate_spec_pack.py`
- [ ] No new gaps introduced (manual review of changes)
- [ ] All changes have evidence citations (file:line in self-review)
- [ ] Trace matrices remain consistent (no broken references)

### Evidence Requirements
For each task:
1. Before: Quote from gap report showing the issue
2. After: File path and line range where changes were made
3. Validation: Output from validation commands showing pass

---

## Risks + Rollback

### Risks
1. **Risk:** Spec changes create inconsistencies with existing schemas
   - **Mitigation:** Schemas already 100% aligned (AGENT_C verified), only adding missing definitions
   - **Rollback:** `git checkout -- specs/*` (restore from git)

2. **Risk:** New error codes conflict with existing codes
   - **Mitigation:** Grep existing error codes before adding new ones
   - **Rollback:** Remove added error codes from specs/01

3. **Risk:** Validation gates fail after spec changes
   - **Mitigation:** Run validation after each phase (not just at end)
   - **Rollback:** Revert specs to last known good state

4. **Risk:** Breaking references in other specs
   - **Mitigation:** Only add new content, don't modify existing content
   - **Rollback:** `git diff specs/` to identify and revert changes

### Rollback Commands
```bash
# Rollback single file
git checkout -- specs/01_system_contract.md

# Rollback all specs
git checkout -- specs/

# Rollback entire phase (if committed)
git revert <commit-sha>
```

---

## Evidence Commands

### Validation Commands (run after each phase)
```bash
# Preflight gates
python tools/validate_swarm_ready.py

# Spec pack validation
python scripts/validate_spec_pack.py

# Schema validation (if schemas were modified)
python scripts/validate_schemas.py
```

### Evidence Grep Commands
```bash
# Phase 1: Error codes
grep -n "SECTION_WRITER_UNFILLED_TOKENS\|SPEC_REF_\|REPO_EMPTY\|GATE_DETERMINISM_VARIANCE" specs/01_system_contract.md

# Phase 2: Algorithms
grep -n "Repository Fingerprinting Algorithm\|Edge Case: Empty Repository\|REQ-HUGO-FP-001" specs/02_repo_ingestion.md specs/09_validation_gates.md

# Phase 3: Field definitions
grep -n "### spec_ref Field\|### validation_profile Field" specs/01_system_contract.md

# Phase 4: New specs
test -f specs/35_test_harness_contract.md && echo "EXISTS" || echo "MISSING"
grep -n "GET /telemetry/\|get_telemetry\|REQ-TMPL-001\|REQ-EDGE-001\|REQ-GUARD-001" specs/16_local_telemetry_api.md specs/24_mcp_tool_schemas.md specs/20_rulesets_and_templates_registry.md specs/03_product_facts_and_evidence.md specs/34_strict_compliance_guarantees.md
```

### Git Commands
```bash
# Show changes
git diff specs/

# Show changed files
git status specs/

# Show line-by-line changes
git diff --unified=3 specs/
```

---

## Open Questions

**None.** All 12 gaps have detailed proposed fixes in HEALING_PROMPT.md with acceptance criteria.

---

## Plan Status

**Status:** READY FOR EXECUTION
**Owner:** Agent D (Docs & Specs)
**Estimated Duration:** 2-4 hours (all phases can be executed sequentially with validation between)
**Dependencies:** None (all gaps are independent spec additions)
**Validation:** Automated (validate_swarm_ready.py, validate_spec_pack.py)

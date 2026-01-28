# GAP HEALING PROMPT

**Run ID:** `20260127-1724`
**Generated:** 2026-01-27 18:30 UTC
**Purpose:** Systematic remediation of 41 BLOCKER gaps identified in pre-implementation verification

---

## MISSION

You are a **Gap Remediation Agent** tasked with fixing **41 BLOCKER gaps** in the foss-launcher repository specs, schemas, and plans. Your mission is to:

1. **Work ONLY in repository tree** (`c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher`)
2. **Fix gaps in priority order** (HIGHEST → HIGH → MEDIUM → LOW)
3. **Maintain spec authority** (specs are primary source of truth)
4. **Provide evidence for all changes** (cite `file:lineStart-lineEnd` for every fix)
5. **Create no new gaps** (all fixes must be complete, unambiguous, deterministic)
6. **Validate after each fix** (run preflight gates: `python tools/validate_swarm_ready.py`)

---

## HARD RULES

### Rule 1: Work Only in Repository Tree
- ✅ Modify files in `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher`
- ❌ DO NOT create files outside repository
- ❌ DO NOT use external resources or web searches

### Rule 2: Evidence is MANDATORY
- Every fix MUST cite evidence:
  - Before: `specs/03:178-183` (quote from verification report)
  - After: `specs/03:185-195` (new lines added with your fix)
- Use `file:lineStart-lineEnd` format for all citations

### Rule 3: No Improvisation
- Follow proposed fixes EXACTLY as documented in [GAPS.md](GAPS.md)
- If proposed fix is ambiguous, ask for clarification (do not guess)
- All changes must be grounded in existing spec patterns

### Rule 4: Maintain Determinism
- All specifications must support deterministic implementation
- No random UUIDs, no timestamps in logic, no non-deterministic algorithms
- LLM-dependent features must document temperature=0, seed=fixed requirements

### Rule 5: Validate After Each Fix
After EVERY gap fix:
```bash
python tools/validate_swarm_ready.py
```
If validation fails, rollback your change and fix the issue before proceeding.

---

## GAP REMEDIATION ORDER

Fix gaps in this exact order (prioritized by impact):

---

## PHASE 1: HIGHEST PRIORITY (1 gap)

### G-GAP-008 | HIGHEST | Gate 9 (TruthLock Compilation) not implemented

**Why HIGHEST:** Critical for Guarantee: all claims must trace to evidence

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/truth_lock.py`
   ```python
   # Load truth_lock_report.json and evidence_map.json
   # For each claim in generated markdown: Verify claim_id exists in evidence_map
   # Check claim text matches evidence_map.claims[].claim_text
   # Validate citations point to valid evidence files
   # Emit GATE_TRUTH_LOCK_VIOLATION for unlinked claims
   ```

2. **Update CLI:** Modify `src/launch/validators/cli.py:217-227`
   - Remove NOT_IMPLEMENTED stub for Gate 9
   - Add call to truth_lock.validate()

3. **Add error code:** Update `specs/01_system_contract.md` error registry
   ```markdown
   GATE_TRUTH_LOCK_VIOLATION
   - Severity: ERROR
   - When: Claim in generated content not linked to evidence_map
   - Action: Fail validation, require evidence for all claims
   ```

4. **Validation:** Run `python tools/validate_swarm_ready.py` (should pass)

**Acceptance Criteria:**
- [ ] truth_lock.py exists and implements validation logic
- [ ] cli.py no longer shows NOT_IMPLEMENTED for Gate 9
- [ ] Error code GATE_TRUTH_LOCK_VIOLATION documented in specs/01
- [ ] Preflight validation passes

---

## PHASE 2: HIGH PRIORITY (5 gaps)

### G-GAP-002 | HIGH | Gate 3 (Hugo Config Compatibility) not implemented

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/hugo_config.py`
2. **Update CLI:** Remove NOT_IMPLEMENTED stub for Gate 3
3. **Add error code:** GATE_HUGO_CONFIG_ERROR to specs/01

**Acceptance Criteria:**
- [ ] hugo_config.py implements validation per specs/09:86-116
- [ ] cli.py calls hugo_config.validate()
- [ ] Error code documented
- [ ] Validation passes

---

### G-GAP-004 | HIGH | Gate 5 (Hugo Build Validation) not implemented

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/hugo_build.py`
   - Run `hugo --gc` in hermetic environment
   - Check exit code, parse stderr
2. **Update CLI:** Remove NOT_IMPLEMENTED stub for Gate 5
3. **Add error code:** GATE_HUGO_BUILD_ERROR to specs/01

**Acceptance Criteria:**
- [ ] hugo_build.py runs Hugo in hermetic environment
- [ ] cli.py calls hugo_build.validate()
- [ ] Error code documented
- [ ] Validation passes

---

### G-GAP-005 | HIGH | Gate 6 (Internal Links Check) not implemented

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/internal_links.py`
2. **Update CLI:** Remove NOT_IMPLEMENTED stub for Gate 6
3. **Add error code:** GATE_INTERNAL_LINK_BROKEN to specs/01

**Acceptance Criteria:**
- [ ] internal_links.py checks all markdown links
- [ ] cli.py calls internal_links.validate()
- [ ] Error code documented
- [ ] Validation passes

---

### G-GAP-009 | HIGH | Gate 10 (Consistency Checks) not implemented

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/consistency.py`
2. **Update CLI:** Remove NOT_IMPLEMENTED stub for Gate 10
3. **Add error code:** GATE_CONSISTENCY_ERROR to specs/01

**Acceptance Criteria:**
- [ ] consistency.py checks for duplicates, contradictions
- [ ] cli.py calls consistency.validate()
- [ ] Error code documented
- [ ] Validation passes

---

### G-GAP-010 | HIGH | Gate 11 (Template Token Lint) not implemented

**Proposed Fix:**
1. **Create validator:** `src/launch/validators/template_token_lint.py`
2. **Update CLI:** Remove NOT_IMPLEMENTED stub for Gate 11
3. **Add error code:** GATE_TEMPLATE_TOKEN_UNFILLED to specs/01

**Acceptance Criteria:**
- [ ] template_token_lint.py detects unfilled tokens like {{PRODUCT_NAME}}
- [ ] cli.py calls template_token_lint.validate()
- [ ] Error code documented
- [ ] Validation passes

---

## PHASE 3: MEDIUM PRIORITY (23 gaps)

### S-GAP-001 | MEDIUM | Missing error code SECTION_WRITER_UNFILLED_TOKENS

**Proposed Fix:**
Add to `specs/01_system_contract.md` error code registry:
```markdown
SECTION_WRITER_UNFILLED_TOKENS
- Severity: ERROR
- When: LLM output contains unfilled template tokens like {{PRODUCT_NAME}}
- Action: Fail validation, require manual review or re-generation
```

**Acceptance Criteria:**
- [ ] Error code added to specs/01 with line citation
- [ ] specs/21:223 reference is now valid
- [ ] Validation passes

---

### S-GAP-003 | MEDIUM | Missing spec_ref field definition (Guarantee K)

**Proposed Fix:**
Add to `specs/01_system_contract.md` field definition section:
```markdown
### spec_ref Field

**Type:** string (required in run_config.json, page_plan.json, pr.json)

**Definition:** Git commit SHA (40-character hex) of the foss-launcher repository containing specs used for this run.

**Validation:** Must resolve to actual commit in github.com/anthropics/foss-launcher

**Purpose:** Version locking for reproducibility (Guarantee K per specs/34:377-385)

**Example:** `"spec_ref": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"`
```

**Acceptance Criteria:**
- [ ] spec_ref definition added to specs/01
- [ ] specs/34:377-385 reference is now unambiguous
- [ ] Validation passes

---

### S-GAP-006 | MEDIUM | Missing validation_profile field in run_config

**Proposed Fix:**
1. **Update schema:** Add to `specs/schemas/run_config.schema.json`:
   ```json
   "validation_profile": {
     "type": "string",
     "enum": ["strict", "standard", "permissive"],
     "description": "Controls gate enforcement strength per specs/09:14-18"
   }
   ```

2. **Update spec:** Document field in `specs/01_system_contract.md:28-39`:
   ```markdown
   - validation_profile (string, enum: strict|standard|permissive): Gate enforcement level
   ```

**Acceptance Criteria:**
- [ ] validation_profile added to run_config.schema.json
- [ ] Field documented in specs/01
- [ ] Schema validation passes
- [ ] Preflight validation passes

---

### S-GAP-010 | MEDIUM | Missing empty repository edge case handling

**Proposed Fix:**
Add to `specs/02_repo_ingestion.md` after line 60:
```markdown
### Edge Case: Empty Repository

**Detection:** Repository has zero files after clone (excluding .git/ directory)

**Behavior:**
1. Emit ERROR with code: `REPO_EMPTY`
2. Do NOT generate repo_inventory.json (validation fails before artifact creation)
3. Exit with non-zero status code

**Rationale:** Cannot proceed without any content to document. User must provide repository with at least one file.

**Test Case:** See `pilots/pilot-empty-repo/` (TO BE CREATED)
```

**Acceptance Criteria:**
- [ ] Edge case documented in specs/02
- [ ] Error code REPO_EMPTY added to specs/01
- [ ] Validation passes

---

### S-GAP-013 | MEDIUM | Missing error code GATE_DETERMINISM_VARIANCE

**Proposed Fix:**
Add to `specs/01_system_contract.md` error code registry:
```markdown
GATE_DETERMINISM_VARIANCE
- Severity: ERROR
- When: Re-running with identical inputs produces different outputs
- Action: Fail Gate T (Test Determinism), block release
- Debug: Compare run artifacts with reference run (use SHA-256 hash diff)
```

**Acceptance Criteria:**
- [ ] Error code added to specs/01
- [ ] specs/09:471-495 reference is now valid
- [ ] Validation passes

---

### S-GAP-016 | MEDIUM | Missing repository fingerprint hash algorithm

**Proposed Fix:**
Add to `specs/02_repo_ingestion.md` after line 145:
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

**Acceptance Criteria:**
- [ ] Algorithm added to specs/02
- [ ] Determinism guarantees documented
- [ ] Validation passes

---

### S-GAP-020 | MEDIUM | Missing spec for telemetry get endpoint

**Proposed Fix:**
Add to `specs/16_local_telemetry_api.md` after line 35:
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

**Update `specs/24_mcp_tool_schemas.md`:**
Add get_telemetry tool schema:
```json
{
  "name": "get_telemetry",
  "description": "Get telemetry snapshot for a run",
  "inputSchema": {
    "type": "object",
    "properties": {
      "run_id": {
        "type": "string",
        "description": "Run ID (optional, defaults to latest)"
      }
    }
  }
}
```

**Acceptance Criteria:**
- [ ] GET /telemetry/{run_id} endpoint spec'd in specs/16
- [ ] get_telemetry tool schema added to specs/24
- [ ] Validation passes

---

### S-GAP-023 | MEDIUM | Missing spec for Markdown test harness contract

**Proposed Fix:**
Create `specs/35_test_harness_contract.md`:
```markdown
# Test Harness Contract (Gate T: Determinism Verification)

**Spec ID:** 35
**Purpose:** Define interface for determinism test harness used by Gate T

## Overview

The test harness executes the full pipeline twice with identical inputs and verifies byte-identical outputs.

## CLI Interface

```bash
python -m launch.harness.determinism_test \
  --run_config path/to/run_config.json \
  --reference_run_dir path/to/reference_run \
  --test_run_dir path/to/test_run
```

**Arguments:**
- `--run_config`: Path to run configuration (must be identical for both runs)
- `--reference_run_dir`: Directory for first run artifacts
- `--test_run_dir`: Directory for second run artifacts

**Exit Codes:**
- 0: Runs are identical (determinism verified)
- 1: Runs differ (GATE_DETERMINISM_VARIANCE detected)
- 2: Test harness error (invalid arguments, missing files)

## Comparison Rules

**Artifacts to Compare:**
- All JSON files in run_dir (except snapshot.json)
- All markdown files in run_dir
- All patch files in patch_bundle/

**Ignored Fields:**
- `run_start_time`, `run_end_time` (timestamps)
- `run_id` (if different between runs)
- `event_id` in event log (UUIDs)

**Comparison Method:**
1. Canonicalize JSON (sort keys, remove ignored fields)
2. Compute SHA-256 hash of canonicalized content
3. Compare hashes (must match exactly)

## Output Format

**Success:**
```json
{
  "schema_version": "1.0",
  "ok": true,
  "profile": "determinism_test",
  "gates": [
    {"gate": "T", "ok": true, "issues": []}
  ],
  "issues": []
}
```

**Failure:**
```json
{
  "schema_version": "1.0",
  "ok": false,
  "profile": "determinism_test",
  "gates": [
    {"gate": "T", "ok": false, "issues": [
      {
        "severity": "error",
        "category": "determinism",
        "message": "Artifact mismatch: product_facts.json hash differs",
        "error_code": "GATE_DETERMINISM_VARIANCE"
      }
    ]}
  ]
}
```

## Determinism Guarantees

**Guaranteed Deterministic:**
- JSON artifact schemas (no random fields)
- Markdown generation (LLM temperature=0, seed=fixed)
- Patch generation (content-addressed)

**Non-Deterministic (Acceptable):**
- Timestamps (ignored in comparison)
- Event IDs (ignored in comparison)

**References:**
- specs/09:471-495 (Gate T specification)
- specs/10_determinism_and_caching.md (determinism guarantees)
```

**Acceptance Criteria:**
- [ ] specs/35 created with complete test harness contract
- [ ] specs/09:471-495 now has complete spec reference
- [ ] Validation passes

---

### R-GAP-001, R-GAP-002, R-GAP-003, R-GAP-004 | MEDIUM | Requirements gaps

(See [GAPS.md](GAPS.md) for detailed proposed fixes for each requirement gap)

**Batch Acceptance Criteria:**
- [ ] All 4 requirement gaps resolved in specs
- [ ] All proposed requirements added to specs with REQ-* IDs
- [ ] Validation passes

---

### G-GAP-001, G-GAP-003, G-GAP-006, G-GAP-007, G-GAP-011, G-GAP-012, G-GAP-013 | MEDIUM | Remaining runtime gates

(See [GAPS.md](GAPS.md) for detailed proposed fixes for each gate)

**Batch Acceptance Criteria:**
- [ ] All 7 remaining runtime gates implemented
- [ ] cli.py updated to call all validators
- [ ] Error codes documented in specs/01
- [ ] Validation passes

---

### F-GAP-021, F-GAP-022, F-GAP-023 | MEDIUM | Feature implementation gaps

**Note:** These gaps require taskcard implementation (TC-300, TC-480, TC-590), not spec changes.

**Action:** Document gap resolution dependencies in [GAPS.md](GAPS.md):
- F-GAP-021: Blocked by TC-590 (Secret Redaction Runtime)
- F-GAP-022: Blocked by TC-480 (PRManager)
- F-GAP-023: Blocked by TC-300 (Orchestrator)

**Acceptance Criteria:**
- [ ] Gap dependencies documented
- [ ] Taskcards remain in "Ready" status (implementation pending)
- [ ] No spec changes required (specs are complete)

---

## PHASE 4: LOW PRIORITY (12 gaps)

### WARNING Gaps (37 total)

**Action:** Address WARNING gaps after all BLOCKER gaps resolved.

**Proposed Approach:**
1. Replace all "best effort", "minimal", "reasonable", "appropriate" language with quantifiable criteria
2. Add missing timeout specifications
3. Define all edge case behaviors
4. Standardize error code naming conventions

(See [GAPS.md](GAPS.md) for detailed WARNING gap list and proposed fixes)

**Acceptance Criteria:**
- [ ] All vague language replaced with quantifiable specifications
- [ ] All missing thresholds defined
- [ ] All edge cases documented
- [ ] Validation passes

---

## VALIDATION PROTOCOL

After EVERY gap fix:

```bash
# Step 1: Validate preflight gates
python tools/validate_swarm_ready.py

# Step 2: Validate spec pack
python scripts/validate_spec_pack.py

# Step 3: Validate schemas
python scripts/validate_schemas.py

# Step 4: Check for new gaps
# Re-read specs/01, specs/09, specs/schemas/* to verify fixes
```

**If any validation fails:**
1. Rollback your change: `git checkout -- <file>`
2. Analyze failure: Read error message, identify issue
3. Fix issue: Correct your change
4. Re-validate: Run validation again

**Never proceed to next gap if validation fails.**

---

## EVIDENCE REQUIREMENTS

For EVERY gap fix, provide:

1. **Before Evidence:**
   - Quote from verification report showing the gap
   - Example: "AGENT_G found: Gate 9 not implemented (specs/09:284-317)"

2. **After Evidence:**
   - File path and line range where you made changes
   - Example: "Added truth_lock.py at src/launch/validators/truth_lock.py:1-150"
   - Validation output: "✅ All preflight gates passed"

3. **Acceptance Criteria Checklist:**
   - [ ] Proposed fix implemented exactly as documented
   - [ ] All required files created or modified
   - [ ] All error codes documented
   - [ ] Validation passes

---

## SUCCESS CRITERIA

Gap healing is complete when:

1. ✅ All 41 BLOCKER gaps resolved
2. ✅ All preflight validation gates pass
3. ✅ All spec schemas validate
4. ✅ All trace matrices remain consistent
5. ✅ No new gaps introduced (verified by spot-checking)

**Final Deliverable:** Git commit with message:
```
fix: resolve 41 BLOCKER gaps from pre-implementation verification

- Implemented 13 runtime validation gates (G-GAP-001 to G-GAP-013)
- Added 8 missing spec definitions (S-GAP-001, 003, 006, 010, 013, 016, 020, 023)
- Defined 4 missing algorithms (R-GAP-001 to R-GAP-004)
- Documented 3 feature implementation dependencies (F-GAP-021, 022, 023)

Verification Run: 20260127-1724
All preflight gates: PASS
Schema validation: PASS
Spec pack validation: PASS

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

**Healing Prompt Generated:** 2026-01-27 18:30 UTC
**Total BLOCKER Gaps to Resolve:** 41
**Estimated Effort:** 10-15 days (assumes parallel work on independent gaps)
**Status:** Ready for gap remediation agent

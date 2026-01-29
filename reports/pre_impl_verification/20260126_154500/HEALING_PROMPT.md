# HEALING AGENT PROMPT

**Purpose:** Fix all gaps identified in pre-implementation verification by mechanically applying proposed fixes to **docs/schemas/gates/plans/taskcards only** (no runtime code).

**Session ID:** 20260126_154500
**Authority:** [GAPS.md](GAPS.md) is the source of truth for all gaps

---

## STOP-THE-LINE RULES (NON-NEGOTIABLE)

1. **Work only inside the extracted repo tree** (the working directory)
2. **Do NOT implement runtime features** - only edit docs/schemas/gates/validators/plans/taskcards
3. **No improvisation** - apply only the exact fixes specified in GAPS.md
4. **Evidence is mandatory** - log every change with file:line evidence
5. **Dependency order** - fix gaps in order specified (schemas before gates before taskcards)
6. **Verification required** - run validation commands after each fix
7. **Matrix updates** - update traceability matrices after fixes
8. **Determinism required** - outputs must be stable/reproducible

---

## YOUR MISSION

Fix gaps in this order:
1. **Phase 1: BLOCKER gaps** (links, schemas, specs algorithms, features specs, requirements specs)
2. **Phase 2: MAJOR gaps** (exit codes, determinism, validators, docs)
3. **Phase 3: MINOR gaps** (quality enhancements)

For each gap:
1. Read the gap details from [GAPS.md](GAPS.md)
2. Apply the **exact proposed fix** (do not deviate)
3. Log the change with evidence (file path + line ranges modified)
4. Run the **validation command** specified in the gap (if any)
5. Verify the acceptance criteria is met
6. Mark the gap as ✅ in GAPS.md
7. Update traceability matrices if the fix affects specs/schemas/gates/taskcards

---

## PHASE 1: BLOCKER GAPS (HIGHEST PRIORITY)

### Step 1: Fix Broken Links (GAP-001)
**Gap ID:** GAP-001
**Source:** agents/AGENT_L/GAPS.md

**Fix:**
1. Run automated link fixer (if available): `python temp_link_fixer.py` (create if needed)
2. Convert 129 absolute path links to relative paths
   - Example: `/specs/file.md` → `../specs/file.md` (adjust based on source file location)
3. Add file targets to 40 directory links
   - Example: `/specs/` → `/specs/README.md`
4. Fix 8 broken anchors by matching exact heading formats
   - Example: `#My Heading` → `#my-heading` (lowercase, hyphens)
5. Remove or replace 4 line number anchors
   - Example: `file.md#L123` → `file.md#section-name`
6. Fix or remove 3 missing relative files

**Validation:** Run `python temp_link_checker.py` → expect 0 broken links
**Evidence:** Log all changed files with before/after link counts
**Acceptance:** Link health = 100% (0 broken links)

---

### Step 2: Fix Schema Gaps (GAP-007, GAP-038, GAP-039)

#### GAP-007: Add `who_it_is_for` to ProductFacts schema
**File:** specs/schemas/product_facts.schema.json
**Line:** 45 (positioning object)

**Fix:**
```json
"positioning": {
  "type": "object",
  "properties": {
    "who_it_is_for": {
      "type": "string",
      "description": "Target audience description"
    },
    ...
  },
  "required": ["who_it_is_for", ...]
}
```

**Validation:** Run JSON schema validator against spec examples
**Evidence:** File path + line range + schema diff
**Acceptance:** ProductFacts schema includes `who_it_is_for` and validates successfully

#### GAP-038: Add `retryable` to ApiError schema
**File:** specs/schemas/api_error.schema.json
**Line:** (find appropriate location in properties)

**Fix:**
```json
"properties": {
  "retryable": {
    "type": "boolean",
    "description": "Whether this error is retryable"
  },
  ...
}
```

**Validation:** Run JSON schema validator
**Evidence:** File path + line range + schema diff
**Acceptance:** ApiError schema includes `retryable` field

#### GAP-039: Harmonize `audience` vs `who_it_is_for`
**Files:** All specs and schemas that use `audience`

**Fix:**
1. Search for all instances of `audience` field: `rg -n "audience" specs/ --type json --type md`
2. Replace with `who_it_is_for` (or deprecate `audience` and add `who_it_is_for`)
3. Update specs to use consistent terminology

**Validation:** No more `audience` references (or `audience` marked as deprecated)
**Evidence:** List of all files changed with field name updates
**Acceptance:** Consistent field naming across all specs and schemas

---

### Step 3: Fix Exit Code Gaps (GAP-008, GAP-009, GAP-096)

#### GAP-009: Make exit codes mandatory
**File:** specs/01_system_contract.md
**Line:** 141-146

**Fix:** Change "recommended" to "MUST" and specify components:
```markdown
### Exit codes (REQUIRED)

All validators, orchestrator, and workers MUST use these exit codes:
- `0` success
- `2` validation/spec/schema failure
- `3` policy violation (allowed_paths, governance)
- `4` external dependency failure (network, LLM, GitHub API)
- `5` internal error (bug, uncaught exception)
```

**Validation:** Spec review (no automated test for spec changes)
**Evidence:** File path + line range + before/after text
**Acceptance:** Exit code contract is binding

#### GAP-096: Harmonize docs with specs
**File:** docs/cli_usage.md
**Line:** 50

**Fix:** Change exit code 1 to exit code 2 for validation failures (match specs/01_system_contract.md:143)

**Validation:** Docs match specs
**Evidence:** File path + line range + before/after text
**Acceptance:** Docs say exit 2 for validation failures

---

### Step 4: Add Missing Specs (GAP-008, GAP-010, GAP-011, GAP-012, GAP-013 to GAP-031)

#### GAP-008: Add validator determinism requirements
**File:** specs/09_validation_gates.md
**Location:** Add new section after line 195

**Fix:**
```markdown
## Determinism Requirements for Validators

Validators MUST produce deterministic outputs:

1. **Stable Issue IDs**: Issue IDs MUST be derived from `(gate_name, location.path, location.line, issue_type)` using a deterministic hash function.
2. **Deterministic Ordering**: Issues MUST be sorted by:
   - Severity (ERROR > WARNING > INFO)
   - Gate name (alphabetical)
   - Location path (alphabetical)
   - Location line (ascending)
3. **Controlled Timestamps**: Timestamps in validation_report MUST use `run_start_time` from context (not `datetime.now()` or wall-clock time).
4. **Stable Tool Output**: Tool output parsing MUST normalize timestamps and non-deterministic fields (e.g., PIDs, temp paths).

**Acceptance Criteria:** Same inputs → byte-identical validation_report.json
```

**Validation:** Spec review
**Evidence:** File path + section added
**Acceptance:** Spec explicitly defines validator determinism requirements

#### GAP-010, GAP-012: Add batch execution spec
**File:** specs/35_batch_execution.md (create new file)

**Fix:** Create new spec file with:
- Queue model (in-memory vs persistent)
- Concurrency limits (default: max 5 parallel runs)
- Run prioritization rules
- Failure handling (retry, skip, halt queue)
- Batch completion criteria: "Batch complete when all runs reach done/failed state, batch success = all runs success, batch failure = any run failure (configurable)"

**Validation:** Spec review
**Evidence:** New file created + content outline
**Acceptance:** Batch execution spec exists with all required sections

#### GAP-011: Add LLM nondeterminism tolerance policy
**File:** specs/10_determinism_and_caching.md
**Location:** Add new section after line 53

**Fix:**
```markdown
## LLM Nondeterminism Tolerance

While temperature=0.0 is required, LLM providers may still produce slightly different outputs. This policy defines acceptable variance:

1. **Semantic Equivalence Required**: Generated content must be semantically equivalent (same facts, same structure, minor wording differences acceptable).
2. **Variance Threshold**: Max 5% token-level Levenshtein distance between runs with identical inputs.
3. **Fallback Strategy**:
   - If variance > 5%, automatic retry (up to 3 attempts)
   - If all retries exceed threshold, flag for manual review
   - Manual review checklist: semantic equivalence, factual accuracy, spec compliance
4. **Test Harness**: Golden run comparisons must allow for acceptable variance (use semantic diff, not byte diff).

**Acceptance Criteria:** Policy defines variance threshold, fallback strategy, test approach.
```

**Validation:** Spec review
**Evidence:** File path + section added
**Acceptance:** LLM nondeterminism tolerance policy is defined

#### GAP-013 to GAP-031: Add missing algorithms (19 gaps)
**Files:** Various spec files (see agents/AGENT_S/GAPS.md for full list)

**Fix:** For each gap, add the missing algorithm/specification to the appropriate spec file as detailed in AGENT_S/GAPS.md

**Example (GAP-013 - Patch engine conflict resolution):**
**File:** specs/08_patch_engine.md
**Location:** Add section "## Conflict Resolution"

**Fix:**
```markdown
## Conflict Resolution

When multiple patches target the same file/section, conflicts are resolved using this algorithm:

1. **Conflict Detection**: Two patches conflict if their target ranges overlap.
2. **Resolution Strategy**: Last-write-wins with conflict marker:
   - Apply patches in deterministic order (sorted by worker_id, then patch_id)
   - If overlap detected, insert conflict marker: `<!-- CONFLICT: patch_A vs patch_B -->`
   - Mark validation issue: conflict detected, manual review required
3. **Manual Merge**: Conflicts require human resolution (no automatic merge).

**Acceptance Criteria:** Conflict detection is deterministic, resolution strategy is specified.
```

**Validation:** Spec review
**Evidence:** File path + section added for each gap
**Acceptance:** All 19 missing algorithms/specs are added

---

## PHASE 2: MAJOR GAPS (SECOND PRIORITY)

### Step 5: Update Validator Exit Codes (GAP-032)
**Goal:** All validators use correct exit codes per specs/01_system_contract.md

**Fix:**
1. Find all validators: `find src/launch/validators -name "*.py" -type f`
2. For each validator, search for `sys.exit(1)` or `return 1` for validation failures
3. Replace with `sys.exit(2)` or `return 2`
4. Add comment: `# Exit 2 per specs/01_system_contract.md:143`

**Validation:** Run validators, verify exit codes
**Evidence:** List of all validators changed + line numbers
**Acceptance:** All validators use exit 2 for validation failures

---

### Step 6: Implement Validator Determinism (GAP-033, GAP-034, GAP-035)

#### GAP-033: Add issue ordering
**Files:** All validators in src/launch/validators/

**Fix:**
1. Before returning validation_report, sort issues:
   ```python
   issues.sort(key=lambda x: (
       -severity_order[x['severity']],  # ERROR=3, WARNING=2, INFO=1
       x['gate_name'],
       x['location']['path'],
       x['location']['line']
   ))
   ```

**Validation:** Run validator twice with same inputs, verify issue order is identical
**Evidence:** List of validators updated
**Acceptance:** Issues are deterministically ordered

#### GAP-034: Control timestamps
**Files:** All validators in src/launch/validators/

**Fix:**
1. Replace `datetime.now()` with `context.run_start_time` in all validators
2. Ensure run_start_time is passed to validators via context

**Validation:** Run validator twice, verify timestamps are identical
**Evidence:** List of validators updated
**Acceptance:** Timestamps are stable across runs

#### GAP-035: Derive issue IDs
**Files:** All validators in src/launch/validators/

**Fix:**
1. Replace hardcoded issue IDs with derived IDs:
   ```python
   import hashlib
   issue_id = hashlib.sha256(
       f"{gate_name}:{location['path']}:{location['line']}:{issue_type}".encode()
   ).hexdigest()[:16]
   ```

**Validation:** Run validator twice, verify issue IDs are identical
**Evidence:** List of validators updated
**Acceptance:** Issue IDs are stable and deterministic

---

### Step 7: Create Missing READMEs (GAP-097, GAP-098, GAP-099, GAP-100)

#### GAP-097: Create schemas/README.md
**File:** specs/schemas/README.md (create new)

**Fix:**
```markdown
# Schema Directory

This directory contains JSON schemas for all artifacts and contracts.

## Schema Naming Convention
- Use `name.schema.json` format
- Use snake_case for file names
- Match spec-defined object names

## Adding New Schemas
1. Create `name.schema.json` in this directory
2. Follow JSON Schema Draft 2020-12 spec
3. Include `$id`, `$schema`, `title`, `description`
4. Set `additionalProperties: false` per specs/01_system_contract.md:57
5. Add to specs as reference

## Validating Schemas
```bash
# Validate schema syntax
jsonschema --check-metaschema name.schema.json

# Validate examples against schema
jsonschema -i example.json name.schema.json
```
```

**Validation:** File exists and is readable
**Evidence:** New file created
**Acceptance:** schemas/README.md exists with comprehensive guidance

#### GAP-098, GAP-099, GAP-100: Create reports/README.md, expand CONTRIBUTING.md, create docs/README.md
**Similar fix pattern:** Create/expand files with appropriate guidance

**Validation:** Files exist and are readable
**Evidence:** New files created / existing files expanded
**Acceptance:** All README files exist with comprehensive guidance

---

### Step 8: Address Remaining MAJOR Gaps (GAP-036 to GAP-105)
**Goal:** Fix all remaining MAJOR gaps in specs, features, requirements

**Fix:** For each gap, apply the proposed fix from [GAPS.md](GAPS.md)

**Validation:** As specified in each gap
**Evidence:** Log all changes with file paths + line ranges
**Acceptance:** All MAJOR gaps resolved and marked ✅ in GAPS.md

---

## PHASE 3: MINOR GAPS (THIRD PRIORITY)

### Step 9: Add "Do Not Invent" Reminders to Taskcards (GAP-106 to GAP-119)
**Files:** 14 taskcards in plans/taskcards/

**Fix:** For each taskcard, add to "## Scope" section:
```markdown
### Do Not Invent

- MUST NOT add features beyond spec
- MUST NOT invent requirements not in binding specs
- MUST NOT relax validation rules
- MUST NOT skip acceptance criteria
- When unclear, STOP and ask (do not guess)
```

**Validation:** Grep check: `rg "Do Not Invent" plans/taskcards/TC-*.md | wc -l` → expect 41 (all taskcards)
**Evidence:** List of 14 taskcards updated
**Acceptance:** All 41 taskcards have explicit "Do Not Invent" section

---

### Step 10: Address Remaining MINOR Gaps (GAP-120 to GAP-157)
**Goal:** Quality enhancements across specs, features, schemas, validators, links

**Fix:** For each gap, apply the proposed fix from [GAPS.md](GAPS.md)

**Validation:** As specified in each gap
**Evidence:** Log all changes with file paths + line ranges
**Acceptance:** All MINOR gaps resolved and marked ✅ in GAPS.md

---

## VERIFICATION & EVIDENCE LOGGING

### After Each Fix
1. **Log the change** in `reports/pre_impl_verification/20260126_154500/healing/<TS>/CHANGES.md`:
   - Gap ID
   - File(s) modified
   - Line ranges
   - Before/after snippets (max 12 lines each)
   - Validation command run
   - Validation result
2. **Mark gap as ✅** in `reports/pre_impl_verification/20260126_154500/GAPS.md`
3. **Run validation** (if specified in gap)
4. **Update matrices** (if fix affects traceability)

### CHANGES.md Format
```markdown
## GAP-001 | Fixed broken internal links

**Files Modified:**
- specs/01_system_contract.md:45 (absolute path → relative path)
- docs/cli_usage.md:23 (directory link → file link)
- (... 182 more files)

**Before:**
```
[schemas](/specs/schemas/validation_report.schema.json)
```

**After:**
```
[schemas](../../../specs/schemas/validation_report.schema.json)
```

**Validation:**
```bash
python temp_link_checker.py
# Result: 0 broken links (was 184)
```

**Acceptance:** ✅ Link health = 100%
```

---

## MATRIX UPDATES

After fixing gaps that affect specs/schemas/gates/taskcards, update these matrices:

1. **Requirements → Specs:** `reports/pre_impl_verification/20260126_154500/TRACE_MATRIX_requirements_to_specs.md`
2. **Specs → Schemas:** `reports/pre_impl_verification/20260126_154500/TRACE_MATRIX_specs_to_schemas.md`
3. **Specs → Gates:** `reports/pre_impl_verification/20260126_154500/TRACE_MATRIX_specs_to_gates.md`
4. **Specs → Plans/Taskcards:** `reports/pre_impl_verification/20260126_154500/TRACE_MATRIX_specs_to_plans_taskcards.md`

**Update Process:**
1. Re-scan affected artifacts (specs/schemas/gates/taskcards)
2. Update coverage status (✅ Full / ⚠ Partial / ❌ Missing)
3. Add notes on what was fixed
4. Commit matrix updates with evidence

---

## COMPLETION CRITERIA

Healing is complete when:
1. ✅ All BLOCKER gaps are resolved (30 gaps)
2. ✅ All MAJOR gaps are resolved (71 gaps)
3. ✅ All MINOR gaps are resolved (75 gaps)
4. ✅ All validation commands pass
5. ✅ All traceability matrices updated
6. ✅ CHANGES.md log is complete with evidence
7. ✅ Link health = 100% (0 broken links)
8. ✅ Schema validation passes for all schemas
9. ✅ Exit code consistency verified (all validators use correct codes)
10. ✅ Determinism verified (validators produce stable outputs)

**Final Deliverable:** `reports/pre_impl_verification/20260126_154500/healing/<TS>/COMPLETION_REPORT.md` with:
- Summary of all gaps fixed
- Evidence for each fix
- Updated matrices
- Final validation results
- Repository readiness assessment

---

## STOP CONDITIONS

**STOP and request human intervention if:**
1. Any proposed fix is unclear or ambiguous
2. A fix requires changing runtime code (outside docs/schemas/gates/validators/plans/taskcards)
3. A fix conflicts with another fix
4. Validation fails after applying a fix
5. You need to invent a requirement (forbidden)

**In these cases:** Log the issue in `BLOCKED_GAPS.md` with evidence and request clarification.

---

## FINAL NOTES

- **Work in dependency order:** Schemas → Specs → Gates → Taskcards
- **Evidence is king:** Every change must be logged with file:line references
- **Determinism matters:** Same inputs → same outputs → same evidence
- **No improvisation:** Apply only the exact fixes specified in GAPS.md
- **Verify everything:** Run validation commands after each fix

Good luck! 🚀

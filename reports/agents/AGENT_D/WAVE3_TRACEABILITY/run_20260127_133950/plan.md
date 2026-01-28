# AGENT_D Wave 3 Execution Plan: Traceability Hardening

**Agent**: AGENT_D (Docs & Specs)
**Mission**: Execute Wave 3 pre-implementation hardening tasks (Traceability)
**Timestamp**: 2026-01-27T13:39:50Z
**Working Directory**: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
**Artifact Directory**: reports/agents/AGENT_D/WAVE3_TRACEABILITY/run_20260127_133950/

---

## Executive Summary

This plan addresses two critical traceability gaps identified in the pre-implementation phase:
1. **TASK-D10**: Complete traceability matrix for ALL binding specs (missing mappings)
2. **TASK-D11**: Audit enforcement claims for correctness (validate claimed validators exist)

**Risk Level**: MEDIUM
- Risk: Incomplete traceability could lead to implementation gaps
- Risk: False enforcement claims could create false confidence in validation coverage
- Mitigation: Systematic verification with evidence for all claims

---

## Task Breakdown

### TASK-D10: Complete Traceability Matrix for ALL Binding Specs (P1, 2-3h)

**Source**: LT-024, GAP-140

**Current State Analysis**:
- Two traceability files exist:
  - `TRACEABILITY_MATRIX.md` (root): High-level requirement → spec → plan mapping
  - `plans/traceability_matrix.md`: Detailed spec → taskcard mapping
- Root file has 24 requirement entries (REQ-001 through REQ-024)
- Plans file has spec-to-taskcard mappings but appears incomplete

**Binding Specs Identified** (from git status and file scan):
- `specs/32_platform_aware_content_layout.md` — **BINDING** (explicit in REQ-010)
- `specs/34_strict_compliance_guarantees.md` — **BINDING** (Guarantees A-L)
- `specs/00_environment_policy.md` — **BINDING** (mandatory .venv policy)
- `specs/09_validation_gates.md` — **BINDING** (gate definitions)
- All schemas under `specs/schemas/*.json` — **BINDING** (validation contracts)

**Missing Mappings to Add**:
1. Schema-to-gate mappings (which gates validate which schemas)
2. Gate-to-validator mappings (which validator files implement which gates)
3. Taskcard-to-gate mappings (which taskcards implement gate infrastructure)
4. Complete binding spec coverage (ensure all binding specs have taskcard links)

**Steps**:
1. Read both traceability files to understand current structure
2. Extract all BINDING specs from specs/ directory
3. For each BINDING spec, verify:
   - Spec → Schema mapping (if applicable)
   - Spec → Gate mapping (which gates validate this spec's requirements)
   - Spec → Taskcard mapping (which taskcards implement this spec)
   - Spec → Validator mapping (which validators enforce this spec)
4. Add missing mappings to appropriate traceability file(s)
5. Ensure no placeholders (violates Gate M)

**Affected Files**:
- `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\TRACEABILITY_MATRIX.md` (EXPAND - read first, merge)
- `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\plans\traceability_matrix.md` (EXPAND - read first, merge)

**Evidence Required**:
- List of all BINDING specs with evidence (grep/file content)
- Complete traceability chain for each BINDING spec
- Grep command showing all specs have taskcard references
- Verification that no placeholders exist in production paths

---

### TASK-D11: Audit Enforcement Claims for Correctness (P1, 3-4h)

**Source**: LT-025, GAP-141

**Current State Analysis**:
- Root TRACEABILITY_MATRIX.md makes enforcement claims like:
  - "Preflight: tools/validate_pinned_refs.py (Gate J) — ✅ IMPLEMENTED"
  - "Runtime: launch_validate rejects floating refs in prod profile"
- Need to verify these claims against actual validator existence

**Enforcement Claims to Verify**:
From TRACEABILITY_MATRIX.md (REQ-013 through REQ-024):
1. Gate J: `tools/validate_pinned_refs.py` — Pinned refs policy
2. Gate K: `tools/validate_supply_chain_pinning.py` — Lock file integrity
3. Gate L: `tools/validate_secrets_hygiene.py` — Secrets scan
4. Gate M: `tools/validate_no_placeholders_production.py` — No placeholders
5. Gate N: `tools/validate_network_allowlist.py` — Network allowlist
6. Gate O: `tools/validate_budgets_config.py` — Budget validation
7. Gate P: `tools/validate_taskcard_version_locks.py` — Version locks
8. Gate Q: `tools/validate_ci_parity.py` — CI parity
9. Gate R: `tools/validate_untrusted_code_policy.py` — Untrusted code policy
10. Runtime validators: `src/launch/validators/cli.py` and related
11. Runtime enforcers: `src/launch/util/path_validation.py`, `src/launch/util/budget_tracker.py`, etc.

**Verification Method**:
1. Extract all "enforced by" or "validated by" claims from TRACEABILITY_MATRIX.md
2. For each claim:
   - Check if file exists (using ls or file read)
   - If file exists: verify it has entry point (grep for main/execute function)
   - If file exists: verify behavior matches spec (read implementation)
   - If file does NOT exist: mark "NOT YET IMPLEMENTED" + link to taskcard
   - If file exists but doesn't match spec: document mismatch + add to gaps
3. Update all claims to be accurate with current implementation status

**Steps**:
1. Parse TRACEABILITY_MATRIX.md and extract all enforcement claims
2. Create verification checklist (claim → file → exists? → matches spec?)
3. For each validator file claimed:
   - Verify file exists in tools/ or src/launch/validators/ or src/launch/util/
   - Read file to verify entry point and behavior
   - Compare to spec requirements in specs/09_validation_gates.md and specs/34_strict_compliance_guarantees.md
4. For claims where validator doesn't exist:
   - Mark "NOT YET IMPLEMENTED"
   - Link to implementing taskcard (e.g., TC-460, TC-570, etc.)
5. For mismatches: document and consider adding to open_issues.md
6. Update TRACEABILITY_MATRIX.md with accurate enforcement status

**Affected Files**:
- `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\TRACEABILITY_MATRIX.md` (EDIT - read first, patch)
- Possibly `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\open_issues.md` (APPEND if new gaps found)

**Evidence Required**:
- List of all enforcement claims extracted (with line numbers)
- Verification results table (claim | file | exists | entry_point_found | matches_spec)
- Updated claims with "NOT YET IMPLEMENTED" markers where applicable
- Grep/ls commands showing validator files exist
- File read snippets showing validator entry points

---

## Execution Order

**Phase 1: Setup and Discovery (15 minutes)**
1. Create artifact directory structure
2. Read all traceability files
3. Read validation gates spec (specs/09_validation_gates.md)
4. Read compliance guarantees spec (specs/34_strict_compliance_guarantees.md)
5. Scan specs/ directory for binding specs
6. List all validator files in tools/ and src/launch/validators/

**Phase 2: TASK-D10 - Complete Traceability Matrix (2-3 hours)**
1. Identify all BINDING specs (grep for "BINDING" or status indicators)
2. For each BINDING spec:
   - Extract requirements (or reference AGENT_R report)
   - Map to schemas (if applicable)
   - Map to gates (which gates validate this spec)
   - Map to taskcards (which taskcards implement this spec)
   - Map to validators (which validators enforce this spec)
3. Compare against current traceability matrices
4. Identify missing mappings
5. Add missing mappings to appropriate traceability file(s)
6. Verify no placeholders in mappings
7. Run grep to verify all specs have taskcard references

**Phase 3: TASK-D11 - Audit Enforcement Claims (3-4 hours)**
1. Extract all enforcement claims from TRACEABILITY_MATRIX.md
2. Create verification checklist
3. For each claimed validator:
   - Check file existence (ls or glob)
   - Read file to verify entry point
   - Compare to spec requirements
   - Record verification result
4. Update claims with accurate status:
   - "✅ IMPLEMENTED" (if verified)
   - "NOT YET IMPLEMENTED - See TC-XXX" (if missing)
   - "⚠️ PARTIAL - [describe mismatch]" (if mismatch)
5. Patch TRACEABILITY_MATRIX.md with updates
6. Document any new gaps in open_issues.md

**Phase 4: Validation (30 minutes)**
1. Grep for all BINDING specs and verify each has traceability entry
2. Grep for all "enforced by" / "validated by" claims
3. Verify validator files exist for each ✅ IMPLEMENTED claim
4. Run `python scripts/validate_spec_pack.py` to ensure no breakage
5. Run link checker on updated traceability files

**Phase 5: Documentation (30 minutes)**
1. Create changes.md with all file modifications
2. Create evidence.md with all verification results
3. Create commands.sh with all commands run
4. Create self_review.md using 12-dimension template

---

## Risk Assessment

### High Risks
1. **Incomplete validator discovery**: Some validators may exist in non-standard locations
   - Mitigation: Use glob patterns to search entire src/ and tools/ trees
2. **Ambiguous enforcement claims**: Claims may not clearly map to specific validators
   - Mitigation: Document ambiguity and flag for clarification

### Medium Risks
1. **Traceability file divergence**: Two traceability files may have conflicting information
   - Mitigation: Document conflicts and maintain both with cross-references
2. **Missing taskcard linkage**: Some specs may not yet have implementing taskcards
   - Mitigation: Mark as "PENDING - No taskcard yet" rather than inventing placeholders

### Low Risks
1. **Schema validation breakage**: Editing traceability files won't break schemas
2. **Merge conflicts**: Files are in modified state but we're appending, not rewriting

---

## Rollback Strategy

**All operations are read-mostly with targeted patches:**
1. Keep backup copies of original files (git tracks this)
2. Use Edit tool (not Write) for all modifications
3. All additions are timestamped and clearly marked
4. If validation fails, revert changes via git restore

**Rollback commands** (if needed):
```bash
git restore TRACEABILITY_MATRIX.md
git restore plans/traceability_matrix.md
git restore open_issues.md  # if modified
```

---

## Success Criteria

**TASK-D10 Success**:
- [ ] All BINDING specs identified with evidence
- [ ] Each BINDING spec has complete traceability entry (spec → schema → gate → taskcard → validator)
- [ ] No placeholders in traceability entries (all entries have actual file paths or explicit "NOT YET IMPLEMENTED")
- [ ] Grep verification shows all specs have taskcard references
- [ ] No duplicate or conflicting entries

**TASK-D11 Success**:
- [ ] All enforcement claims extracted and verified
- [ ] Each claim has verification result (exists/not exists/mismatch)
- [ ] All ✅ IMPLEMENTED claims verified with file existence + entry point check
- [ ] All NOT YET IMPLEMENTED claims linked to implementing taskcard
- [ ] Any mismatches documented in gaps/open issues
- [ ] Updated traceability matrix passes validation

**Overall Success**:
- [ ] 12-dimension self-review completed with all dimensions ≥ 4/5
- [ ] All evidence captured in evidence.md
- [ ] All commands captured in commands.sh (copy-pasteable)
- [ ] All changes documented in changes.md with before/after excerpts
- [ ] No validation breakage (validate_spec_pack.py passes)

---

## Tools and Commands

**Discovery Commands**:
```bash
# Find all BINDING specs
rg -i "binding|status.*binding" specs/

# List all validator files
ls -la tools/validate_*.py
ls -la src/launch/validators/
ls -la src/launch/util/

# Extract enforcement claims
rg "enforced by|validated by|IMPLEMENTED|Gate [A-Z]:" TRACEABILITY_MATRIX.md
```

**Verification Commands**:
```bash
# Verify validator file exists
ls tools/validate_pinned_refs.py

# Check for entry point
rg "def main|if __name__.*__main__|def execute" tools/validate_pinned_refs.py

# Verify spec coverage
rg -l "TC-[0-9]+" specs/*.md | wc -l
```

**Validation Commands**:
```bash
# Run spec pack validation
python scripts/validate_spec_pack.py

# Check markdown links
python tools/check_markdown_links.py TRACEABILITY_MATRIX.md
python tools/check_markdown_links.py plans/traceability_matrix.md
```

---

## Notes

**File Safety Protocol**:
- ALWAYS read files before editing
- Use Edit tool (not Write) for existing files
- Merge/patch existing content, never overwrite
- Timestamp all additions
- Idempotent operations (re-running adds value without duplication)

**Evidence Trail**:
- All commands logged to commands.sh
- All outputs captured in evidence.md
- All file modifications documented in changes.md
- All verification results in evidence.md

**NO IMPLEMENTATION ALLOWED**:
- This is PRE-IMPLEMENTATION HARDENING ONLY
- NO code implementation, NO feature building
- ONLY documentation, specs, traceability updates

---

**Plan approved. Ready for execution.**

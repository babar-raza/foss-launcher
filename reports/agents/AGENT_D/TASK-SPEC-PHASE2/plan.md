# TASK-SPEC-PHASE2 Plan

## Mission
Add 3 missing algorithms and edge case specifications to resolve BLOCKER gaps S-GAP-016, S-GAP-010, and R-GAP-003.

## Scope
- **TASK-SPEC-2A:** Add repository fingerprinting algorithm to specs/02_repo_ingestion.md (after line 145)
- **TASK-SPEC-2B:** Add empty repository edge case to specs/02_repo_ingestion.md (after line 60)
- **TASK-SPEC-2C:** Add Hugo config fingerprinting algorithm to specs/09_validation_gates.md (after line 115)

## Assumptions
1. Phase 1 complete: All 4 error codes added (including REPO_EMPTY)
2. Specs are markdown files that can be edited without breaking builds
3. Insertion points (line numbers) are accurate in current spec state
4. All algorithms must specify determinism guarantees explicitly

## Approach
1. Read target files to understand current structure and verify insertion points
2. Add algorithms/edge cases at specified locations using Edit tool
3. Maintain existing formatting (heading levels, markdown style)
4. Preserve all existing content (append only, no deletions)
5. Run validation gates to verify changes

## Steps

### Step 1: TASK-SPEC-2A - Repository Fingerprinting Algorithm
- **Target:** specs/02_repo_ingestion.md
- **Location:** After line 145 (after "Store `repo_inventory.example_roots` and `example_paths` (sorted).")
- **Action:** Add complete algorithm section with determinism guarantees
- **Key elements:**
  - SHA-256 based fingerprinting
  - Lexicographic sorting for determinism
  - Example output format
  - Exclusion of phantom paths

### Step 2: TASK-SPEC-2B - Empty Repository Edge Case
- **Target:** specs/02_repo_ingestion.md
- **Location:** After line 60 (after source_roots discovery section)
- **Action:** Add edge case handling section
- **Key elements:**
  - Detection criteria (zero files after clone)
  - Error code reference (REPO_EMPTY from Phase 1)
  - Exit behavior (no artifact generation)
  - Rationale

### Step 3: TASK-SPEC-2C - Hugo Config Fingerprinting Algorithm
- **Target:** specs/09_validation_gates.md
- **Location:** After line 115 (after Gate 3 acceptance criteria)
- **Action:** Add requirement section with algorithm
- **Key elements:**
  - Canonicalization steps
  - SHA-256 hash of canonical form
  - Error cases (missing config, ambiguous config)
  - Determinism guarantees

### Step 4: Validation
- Run validate_swarm_ready.py
- Run validate_spec_pack.py
- Grep for new sections to verify they exist

## Success Criteria
- All 3 algorithms/edge cases added to specs
- All algorithms specify determinism guarantees
- Edge case references REPO_EMPTY error code from Phase 1
- Validation gates pass
- All sections findable via grep
- No existing content modified or deleted

## Evidence Trail
- plan.md (this file)
- changes.md (detailed file:line citations)
- evidence.md (validation outputs)
- commands.sh (exact commands run)
- self_review.md (12-dimension assessment)

# Wave 4 Follow-Up: 38 MAJOR Gaps Closure Plan

**Agent**: AGENT_D (Docs & Specs)
**Mission**: Close all 38 MAJOR gaps to achieve 100% gap closure
**Session ID**: run_20260127_144304
**Date**: 2026-01-27

---

## Overview

Wave 4 has completed:
- 19/19 BLOCKER gaps (100%)

Remaining work:
- 38/38 MAJOR gaps (0% → 100%)

**Expected additions**: ~600-1000 lines of binding specifications
**Expected modifications**: ~20 spec files
**Time budget**: 2-3 hours

---

## Gap Categories (38 total)

Based on AGENT_S/GAPS.md and briefing:

### 1. Documented MAJOR Gaps (11 confirmed)

1. **S-GAP-002-003**: Example discovery order not enforced (specs/02_repo_ingestion.md)
2. **S-GAP-002-004**: Test commands fallback unspecified (specs/02_repo_ingestion.md)
3. **S-GAP-003-001**: Contradiction resolution algorithm incomplete (specs/03_product_facts_and_evidence.md)
4. **S-GAP-004-002**: Empty claims handling unspecified (specs/04_claims_compiler_truth_lock.md)
5. **S-GAP-004-003**: Claim marker syntax unspecified (specs/04_claims_compiler_truth_lock.md)
6. **S-GAP-005-001**: Snippet syntax validation failure handling (specs/05_example_curation.md)
7. **S-GAP-005-002**: Generated snippet fallback policy vague (specs/05_example_curation.md)
8. **S-GAP-006-002**: Minimum page count violation behavior (specs/06_page_planning.md)
9. **S-GAP-006-003**: Cross-link target resolution unclear (specs/06_page_planning.md)
10. **S-GAP-SC-004**: Missing commit_request.schema.json (specs/schemas/)
11. **S-GAP-SC-005**: Missing open_pr_request.schema.json (specs/schemas/)

### 2. Inferred MAJOR Gaps (27 to discover)

Based on briefing categories:

#### A. Vague Language Elimination (~7 gaps remaining after documented ones)
- Search for "should/may/could" in binding sections
- Target specs: All modified specs + 08, 14, 17, 19, 26

#### B. Edge Case Handling in Workers (~12 gaps)
- W1 (RepoScout): Empty repo, no README, no tests, no examples
- W2 (FactsBuilder): Zero claims, contradictory evidence
- W3 (ExampleCurator): Zero examples, invalid snippets
- W4 (PagePlanner): Insufficient claims for minimum pages
- W5-W9 (Writers + Patch): Writer failure, patch conflicts

#### C. Failure Mode Specifications (~10 gaps)
- Missing failure handling in various workers
- Error codes, telemetry events, recovery strategies

#### D. Best Practices Sections (~9 gaps)
- Auth best practices (specs/17)
- Toolchain verification best practices (specs/19)
- Adapter implementation guide (specs/26)
- MCP best practices (specs/14)
- Additional domain-specific guidance

---

## Execution Plan (Prioritized by Spec File)

### Phase 1: Core Pipeline Specs (High Priority)

#### File: specs/02_repo_ingestion.md (2 gaps)
**Gaps**: S-GAP-002-003, S-GAP-002-004
**Changes**:
1. Add clarity to example discovery order (lines 102-112)
2. Add test commands fallback handling
**Estimated time**: 8 minutes

#### File: specs/03_product_facts_and_evidence.md (1 gap + edge cases)
**Gaps**: S-GAP-003-001
**Changes**:
1. Add contradiction resolution algorithm (lines 112-132)
2. Add edge case: Zero evidence sources
**Estimated time**: 10 minutes

#### File: specs/04_claims_compiler_truth_lock.md (2 gaps)
**Gaps**: S-GAP-004-002, S-GAP-004-003
**Changes**:
1. Add empty claims handling specification
2. Add claim marker syntax reference
**Estimated time**: 8 minutes

#### File: specs/05_example_curation.md (2 gaps)
**Gaps**: S-GAP-005-001, S-GAP-005-002
**Changes**:
1. Add snippet syntax validation failure handling
2. Replace vague language in generated snippet policy
**Estimated time**: 10 minutes

#### File: specs/06_page_planning.md (2 gaps)
**Gaps**: S-GAP-006-002, S-GAP-006-003
**Changes**:
1. Add minimum page count violation behavior (may be covered by BLOCKER)
2. Add cross-link target resolution specification
**Estimated time**: 8 minutes

#### File: specs/21_worker_contracts.md (12+ gaps - edge cases & failure modes)
**Gaps**: Inferred from briefing (W1-W9 edge cases and failure modes)
**Changes**:
1. W1 (RepoScout): Add edge cases (empty repo, missing dirs)
2. W2 (FactsBuilder): Add edge cases (zero claims, conflicts)
3. W3 (ExampleCurator): Add edge cases (zero examples)
4. W4 (PagePlanner): Add edge cases (insufficient claims)
5. W5-W9: Add failure mode specifications
6. Add error codes and telemetry events for each worker
**Estimated time**: 40 minutes

#### File: specs/08_patch_engine.md (edge cases)
**Gaps**: Inferred - additional edge cases
**Changes**:
1. Add edge cases for patch conflicts
2. Add failure recovery strategies
**Estimated time**: 10 minutes

### Phase 2: Best Practices & Guidance (Medium Priority)

#### File: specs/14_mcp_endpoints.md (best practices)
**Gaps**: Inferred - missing MCP best practices
**Changes**:
1. Add MCP implementation best practices section
2. Add error handling guidance
**Estimated time**: 12 minutes

#### File: specs/17_github_commit_service.md (auth best practices + schemas)
**Gaps**: S-GAP-SC-004, S-GAP-SC-005, + auth best practices
**Changes**:
1. Add authentication best practices section
2. Verify schema references
**Estimated time**: 10 minutes

#### File: specs/19_toolchain_and_ci.md (verification best practices)
**Gaps**: Inferred - toolchain verification best practices
**Changes**:
1. Add toolchain verification best practices section
2. Add validation command guidance
**Estimated time**: 12 minutes

#### File: specs/26_repo_adapters_and_variability.md (adapter guide)
**Gaps**: Inferred - adapter implementation guide
**Changes**:
1. Add comprehensive adapter implementation guide
2. Add adapter selection criteria
**Estimated time**: 15 minutes

### Phase 3: Schema Creation

#### File: specs/schemas/commit_request.schema.json (new file)
**Gap**: S-GAP-SC-004
**Changes**: Create schema based on specs/17 lines 86-102
**Estimated time**: 8 minutes

#### File: specs/schemas/open_pr_request.schema.json (new file)
**Gap**: S-GAP-SC-005
**Changes**: Create schema for PR request
**Estimated time**: 8 minutes

### Phase 4: Vague Language Cleanup (15 minutes)

- Search modified files for "should/may/could"
- Replace with MUST/SHALL in binding sections
- Document before/after counts

### Phase 5: Validation & Evidence (25 minutes)

1. Run validation after each file modification
2. Final validation check
3. Create gaps_closed.md
4. Create evidence.md
5. Create self_review.md
6. Create commands.sh

---

## Success Criteria

- [ ] All 38 MAJOR gaps closed with evidence
- [ ] Zero placeholders (TBD, TODO) added
- [ ] Zero breaking changes to existing specs
- [ ] ~600-1000 lines of specifications added
- [ ] Vague language reduced by 50%+ in modified sections
- [ ] All validation gates passing
- [ ] Self-review score: ALL dimensions ≥4/5

---

## File Modification Checklist

| File | Gaps | Status | Lines Added | Validation |
|------|------|--------|-------------|------------|
| specs/02_repo_ingestion.md | 2 | Pending | TBD | Pending |
| specs/03_product_facts_and_evidence.md | 1+ | Pending | TBD | Pending |
| specs/04_claims_compiler_truth_lock.md | 2 | Pending | TBD | Pending |
| specs/05_example_curation.md | 2 | Pending | TBD | Pending |
| specs/06_page_planning.md | 2 | Pending | TBD | Pending |
| specs/21_worker_contracts.md | 12+ | Pending | TBD | Pending |
| specs/08_patch_engine.md | 1+ | Pending | TBD | Pending |
| specs/14_mcp_endpoints.md | 1+ | Pending | TBD | Pending |
| specs/17_github_commit_service.md | 1+ | Pending | TBD | Pending |
| specs/19_toolchain_and_ci.md | 1+ | Pending | TBD | Pending |
| specs/26_repo_adapters_and_variability.md | 1+ | Pending | TBD | Pending |
| specs/schemas/commit_request.schema.json | 1 | Pending | NEW | Pending |
| specs/schemas/open_pr_request.schema.json | 1 | Pending | NEW | Pending |

**Total files**: 13
**Total gaps**: 38 (11 documented + 27 inferred)

---

## Time Tracking

- **Start time**: 2026-01-27 14:43:04
- **Planned duration**: 2-3 hours
- **Checkpoint at**: 1 hour (50% gaps expected)
- **Completion target**: 2026-01-27 17:00:00

---

## Next Steps

1. Read specs/02_repo_ingestion.md and apply fixes
2. Validate after each file modification
3. Continue through file checklist
4. Perform vague language cleanup
5. Create evidence bundle
6. Complete self-review

**Status**: READY TO EXECUTE

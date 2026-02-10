---
id: TC-1110
title: "Fix TC-1106 Regression (1.6MB Bullet Points)"
status: Done
owner: "Agent B"
updated: "2026-02-10"
depends_on:
  - TC-1106
allowed_paths:
  - src/launch/workers/w5_section_writer/worker.py
  - tests/unit/workers/test_w5_specialized_generators.py
  - reports/agents/agent_b/TC-1110_fix_tc1106_regression/**
evidence_required:
  - reports/agents/agent_b/TC-1110_fix_tc1106_regression/evidence.md
  - reports/agents/agent_b/TC-1110_fix_tc1106_regression/self_review.md
spec_ref: bb0df68a8cc573a27e7fb3a8006e8a820385f194
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-1110 — Fix TC-1106 Regression (1.6MB Bullet Points)

## Objective
Fix critical regression introduced by TC-1106 where naive claim_text appending created 32 new bullet point quality errors, including a 1.6MB bullet point on line 30 of developer-guide.md. Implement hybrid filtering/truncation to eliminate regression while preserving Limitations section functionality.

## Required spec references
- specs/21_worker_contracts.md (W5 SectionWriter contract)
- specs/08_section_writer.md (content generation)
- specs/05_product_facts.md (claim_groups structure)
- C:\Users\prora\.claude\plans\enchanted-drifting-naur.md (Track 3.1 section)
- reports/agents/agent_b/TC-1106_developer_guide_limitations/evidence.md (original implementation)

## Scope
### In scope
- Implement Option C (hybrid approach): Pre-filter >1KB claims, truncate remaining to 200 chars
- Update generate_comprehensive_guide_content() in BOTH code paths (lines ~470 and ~580)
- Add module-level constants: MAX_CLAIM_TEXT_LENGTH, MAX_CLAIM_FILTER_LENGTH, MAX_LIMITATION_CLAIMS
- Add warning logs for filtering and truncation operations
- Update 4 existing TC-1106 tests with realistic claim lengths
- Add 2 new tests for edge cases (long claims, extremely long claims)
- Evidence package generation
- 12D self-review with ≥4/5 on all dimensions

### Out of scope
- W2 FactsBuilder enrichment logic (root cause of 1.6MB claims)
- LLM summarization of long claims
- Separate Limitations page generation
- Changes to other page types beyond comprehensive_guide
- W4 IAPlanner modifications
- W5.5 ContentReviewer modifications

## Inputs
- src/launch/workers/w5_section_writer/worker.py (TC-1106 implementation with regression)
- tests/unit/workers/test_w5_specialized_generators.py (4 TC-1106 tests)
- C:\Users\prora\.claude\plans\enchanted-drifting-naur.md (Track 3.1 approved fix strategy)
- Product facts with 52 limitation claims (lengths: 1.6MB, 29KB, 12KB, median 153 chars)
- Review report showing 32 bullet point errors in developer-guide.md

## Outputs
- Updated W5 worker.py with hybrid filtering/truncation (2 locations)
- Module-level constants for length thresholds
- Warning logs for filtered/truncated claims
- 52 passing tests (46 existing + 6 new/updated)
- Evidence package demonstrating regression elimination
- 12D self-review scoring ≥48/60

## Allowed paths
- src/launch/workers/w5_section_writer/worker.py
- tests/unit/workers/test_w5_specialized_generators.py
- reports/agents/agent_b/TC-1110_fix_tc1106_regression/**

## Preconditions / dependencies
- TC-1106 (Developer Guide Limitations Section Gap) must be complete
- Track 3 Wave 1 + Wave 2 complete (all 4 agents executed)
- TC-1106 regression root cause identified (1.6MB bullet points from naive append)
- Approved fix strategy: Option C (hybrid filtering + truncation)

## Implementation steps

1. **Read TC-1106 implementation**:
   - Read src/launch/workers/w5_section_writer/worker.py
   - Locate BOTH code paths with limitation generation (lines ~470 and ~580)
   - Document current naive append logic
   - Confirm both locations need update

2. **Add module-level constants**:
   - Add constants after imports in worker.py:
     ```python
     MAX_CLAIM_TEXT_LENGTH = 200  # Display limit
     MAX_CLAIM_FILTER_LENGTH = 1000  # Pre-filter limit
     MAX_LIMITATION_CLAIMS = 10
     ```

3. **Update first code path (no-workflows, lines ~470)**:
   - Replace naive limitation generation logic
   - Implement Option C hybrid approach:
     - Pre-filter claims >1KB
     - Truncate remaining claims to 200 chars at word boundary
     - Limit to 10 claims maximum
     - Add warning logs for filtering/truncation
   - Preserve claim_id markers

4. **Update second code path (normal-workflows, lines ~580)**:
   - Apply identical hybrid approach as step 3
   - Ensure consistency between both code paths
   - Verify warning logs in both locations

5. **Update existing TC-1106 tests**:
   - Read tests/unit/workers/test_w5_specialized_generators.py
   - Update 4 existing TC-1106 tests with realistic claim lengths (50-300 chars)
   - Replace synthetic 40-char examples with production-like data
   - Verify tests still pass

6. **Add new edge case tests**:
   - Add test_comprehensive_guide_limitations_long_claims:
     - Claim with 300 chars → verify truncated to ~200 with "..."
     - Verify word boundary truncation (no mid-word cuts)
     - Verify claim_id marker preserved
   - Add test_comprehensive_guide_limitations_extremely_long:
     - Claim with 2000 chars (>1KB) → verify filtered out
     - Verify logger.warning called with correct message
     - Verify other claims still included

7. **Run all tests**:
   - Execute: set PYTHONHASHSEED=0 && .venv\Scripts\python.exe -m pytest tests/unit/workers/test_w5_specialized_generators.py -v
   - Expected: 52/52 tests pass (46 existing + 6 new/updated)
   - Verify 0 failures, 0 regressions

8. **Generate evidence package**:
   - Create evidence.md with:
     - Root cause summary (TC-1106 naive append)
     - Fix implementation (Option C hybrid approach)
     - Code changes (both code paths, lines ~470 and ~580)
     - Test results (52/52 pass)
     - Before/after comparison (32 errors → 0 errors expected)
     - Verification: all bullet points <200 chars

9. **Create 12D self-review**:
   - Use reports/templates/self_review_12d.md template
   - Target: ≥4/5 on ALL 12 dimensions (≥48/60 total)
   - Document any dimension <4 with concrete fix plan
   - Include test coverage, code quality, specification alignment

10. **Update taskcard status**:
    - Update status to "Done"
    - Update updated field to completion timestamp
    - Verify all acceptance checks satisfied

## Test plan
- Unit test: Truncation of 300-char claim to ~200 chars at word boundary
- Unit test: Filtering of 2000-char claim (>1KB)
- Unit test: Warning log emission for filtered claims
- Unit test: Warning log emission for truncated claims
- Unit test: Preservation of claim_id markers after truncation
- Unit test: Limit enforcement (10 claims maximum)
- Regression test: All 46 existing tests still pass
- Integration test: developer-guide.md has Limitations section with all bullets <200 chars

## E2E verification
**Concrete command(s) to run:**
```bash
cd C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
set PYTHONHASHSEED=0
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w5_specialized_generators.py -v
```

**Expected artifacts:**
- Test output showing 52/52 tests pass
- All TC-1106 tests pass with realistic claim lengths
- New edge case tests pass (long claims, extremely long claims)
- No regressions in existing test suite

**Success criteria:**
- [ ] All 52 tests pass (0 failures)
- [ ] Both code paths updated (lines ~470 and ~580)
- [ ] Module-level constants added
- [ ] Warning logs verified in tests
- [ ] Pilot run: developer-guide.md has Limitations section
- [ ] Pilot run: All bullet points <200 chars
- [ ] Track 3.1 metrics: errors ≤6 (vs Track 3: 35 errors)

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-1106 (W5 SectionWriter) added Limitations generation to comprehensive_guide
- Regression: TC-1106 implementation created 32 new bullet point errors (1.6MB longest)
- Fix: Hybrid filtering/truncation eliminates regression while preserving functionality
- Downstream: W5.5 ContentReviewer consumes generated content with <200 char bullets
- Contracts: specs/08_section_writer.md (W5 contract), specs/05_product_facts.md (claim structure)
- Data source: W2 FactsBuilder enriches limitation claims (may over-enrich to 1.6MB)
- Follow-up: Investigate W2 enrichment logic to prevent pathological cases at source

## Failure modes

### Failure mode 1: Fix applied to only one code path
**Detection:** Tests pass but pilot run still shows long bullets in developer-guide.md; evidence shows only one location updated
**Resolution:** Review both code paths in worker.py (lines ~470 and ~580); ensure BOTH locations have identical hybrid logic; add test to verify both paths
**Spec/Gate:** specs/08_section_writer.md (W5 contract), TC-1106 implementation analysis

### Failure mode 2: Word boundary truncation breaks mid-word
**Detection:** Test output shows truncated claims ending with partial words (e.g., "Cannot pro..."); readability degraded
**Resolution:** Review rsplit(' ', 1)[0] logic; ensure it finds last space before MAX_CLAIM_TEXT_LENGTH; add test case verifying word boundary preservation
**Spec/Gate:** Python string handling, unit test coverage

### Failure mode 3: Warning logs not emitted
**Detection:** Tests don't verify logger.warning calls; pilot run shows no telemetry for filtered/truncated claims
**Resolution:** Add mock logger tests; verify warning message format includes claim_id and character counts; ensure logs visible in pipeline output
**Spec/Gate:** Python logging best practices, telemetry requirements

### Failure mode 4: Filter threshold too aggressive
**Detection:** Most claims filtered out (e.g., >40 of 52 claims exceed 1KB); Limitations section nearly empty
**Resolution:** Analyze product_facts claim length distribution; adjust MAX_CLAIM_FILTER_LENGTH if needed (e.g., 2KB instead of 1KB); prioritize claims by truth_status or importance
**Spec/Gate:** Product facts analysis, user experience requirements

### Failure mode 5: Tests use synthetic data, miss edge cases
**Detection:** Tests pass but pilot run fails; synthetic test claims don't match production data characteristics
**Resolution:** Update test fixtures with realistic claim lengths from actual product_facts; include edge cases (1 char, 10KB, empty string); use property-based testing
**Spec/Gate:** Test data quality, TC-1106 lessons learned

### Failure mode 6: Truncation loses critical information
**Detection:** User feedback shows truncated claims missing essential details; "..." ellipsis cuts off key limitations
**Resolution:** Consider LLM summarization for long claims instead of simple truncation; or increase MAX_CLAIM_TEXT_LENGTH to 300 chars; or create separate detailed Limitations page
**Spec/Gate:** User experience requirements, content quality standards

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Both code paths updated with identical hybrid logic (lines ~470, ~580)
- [ ] Module-level constants defined with clear names and comments
- [ ] Pre-filter removes claims >1KB before truncation loop
- [ ] Truncation preserves word boundaries (no mid-word cuts)
- [ ] Claim markers [claim: claim_id] preserved after truncation
- [ ] Warning logs include claim_id and character counts
- [ ] Tests cover edge cases: 1 char, 300 chars, 2000 chars, empty string
- [ ] Tests verify logger.warning calls with correct messages
- [ ] All 52 tests pass with 0 failures
- [ ] Evidence package includes before/after bullet point comparison
- [ ] 12D self-review addresses test coverage gap lesson learned
- [ ] Git commit message references TC-1110 and Co-Authored-By

## Deliverables
- Code:
  - Updated W5 worker.py with hybrid filtering/truncation (2 locations)
  - Module-level constants for thresholds
  - Warning logs for filtering/truncation
- Tests:
  - Updated 4 existing TC-1106 tests with realistic claim lengths
  - New test for long claim truncation (300 chars)
  - New test for extremely long claim filtering (2000 chars)
  - Total: 52 tests (46 + 6)
- Reports (required):
  - reports/agents/agent_b/TC-1110_fix_tc1106_regression/evidence.md
  - reports/agents/agent_b/TC-1110_fix_tc1106_regression/self_review.md

## Acceptance checks
- [ ] Both code paths updated (lines ~470, ~580) with identical logic
- [ ] Module-level constants added: MAX_CLAIM_TEXT_LENGTH, MAX_CLAIM_FILTER_LENGTH, MAX_LIMITATION_CLAIMS
- [ ] Pre-filter logic removes claims >1KB
- [ ] Truncation logic preserves word boundaries and adds "..."
- [ ] Warning logs emit for filtered and truncated claims
- [ ] All 52 tests pass (46 existing + 6 new/updated)
- [ ] No regressions in existing test suite
- [ ] Evidence package complete with before/after comparison
- [ ] Self-review scores ≥4/5 on all 12 dimensions (≥48/60 total)
- [ ] Git commit with Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
- [ ] Pilot run: developer-guide.md has Limitations section
- [ ] Pilot run: All bullet points <200 chars
- [ ] Track 3.1 metrics: errors ≤6 (eliminate 29+ regression errors)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

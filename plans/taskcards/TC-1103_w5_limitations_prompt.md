---
id: TC-1103
title: W5 LLM Prompt Update for Limitations + W5.5 Check Refinement
status: Done
agent: Agent-D
owner: Agent-D
priority: P1
created: "2026-02-10"
updated: "2026-02-10"
depends_on: []
spec_ref: 96c46ffde5a48121122da7a7a3d23f3cd3563b99
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w5_section_writer/worker.py
  - src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py
  - tests/unit/workers/test_tc_440_section_writer.py
  - tests/unit/workers/w5_5_content_reviewer/test_checks.py
  - reports/agents/agent_d/TC-CREV-D-TRACK2/**
evidence_required:
  - reports/agents/agent_d/TC-CREV-D-TRACK2/plan.md
  - reports/agents/agent_d/TC-CREV-D-TRACK2/changes.md
  - reports/agents/agent_d/TC-CREV-D-TRACK2/evidence.md
  - reports/agents/agent_d/TC-CREV-D-TRACK2/self_review.md
---

# TC-1103 — W5 LLM Prompt Update for Limitations + W5.5 Check Refinement

## Objective
Enhance W5 SectionWriter's LLM prompt to explicitly instruct creation of Limitations sections when required, and refine W5.5 ContentReviewer's limitation honesty check to be page-type specific, reducing false positives from 18 to ~3-5.

## Required spec references
- `specs/07_ia_planner.md` — required_headings and page templates
- `specs/08_section_writer.md` — LLM content generation
- `specs/03_facts_builder.md` — claim_groups structure and limitations claims
- `specs/35_w5_5_content_reviewer.md` — ContentReviewer checks and severity levels
- `specs/schemas/product_facts.schema.json` — claim_groups data model

## Scope

### In scope
- **D-101**: Update W5 SectionWriter LLM prompt to include Limitations instruction when "Limitations" is in required_headings
- **D-101**: Filter limitation claims from product_facts.claim_groups and pass to LLM context
- **D-102**: Refine W5.5 technical_accuracy.py check_7_limitation_honesty to be page-type specific
- **D-102**: ERROR severity only for pages that should have limitations (overview, comprehensive_guide, api_overview)
- **D-102**: Skip check entirely for pages where limitations are not expected (index, toc, getting_started, installation, faq, troubleshooting, how_to)
- Test coverage for both prompt logic and check refinement
- Evidence package with implementation details and test results

### Out of scope
- Changes to W4 IAPlanner's required_headings logic
- Changes to template files or required_headings configuration
- Other W5.5 checks beyond check_7_limitation_honesty
- W6 LinkerPatcher or downstream workers
- Changes to claim_groups structure in product_facts.json

## Inputs
- `src/launch/workers/w5_section_writer/worker.py` — W5 worker with LLM generation logic
- `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py` — W5.5 technical accuracy checks
- `product_facts.json` — claim_groups.limitations list
- `page_plan.json` — required_headings per page
- Existing test files for W5 and W5.5

## Outputs
- Modified W5 worker with dynamic Limitations instruction in LLM prompt
- Modified W5 worker with limitation claims filtering and context injection
- Modified W5.5 technical_accuracy check with page-type specific severity
- New/updated test cases for prompt logic and check refinement
- Evidence package in `reports/agents/agent_d/TC-CREV-D-TRACK2/`

## Allowed paths
- src/launch/workers/w5_section_writer/worker.py
- src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py
- tests/unit/workers/test_tc_440_section_writer.py
- tests/unit/workers/w5_5_content_reviewer/test_checks.py
- reports/agents/agent_d/TC-CREV-D-TRACK2/**

## Implementation steps

### Step 1: Analyze existing W5 LLM generation logic
- Read `src/launch/workers/w5_section_writer/worker.py`
- Locate `_generate_content_with_llm()` function
- Identify where LLM prompt is constructed
- Understand how required_headings are passed and used

### Step 2: Implement D-101 (W5 LLM Prompt Update)
- Add conditional Limitations instruction logic:
  - Check if "Limitations" in required_headings
  - If present, add explicit instruction to create Limitations section
  - Instruction should emphasize honesty and clarity about constraints
- Filter limitation claims:
  - Extract limitation_claim_ids from product_facts.claim_groups.limitations
  - Filter all_claims to get limitation-specific claims
  - Add to claims_context for LLM
- Ensure instruction is well-formatted and integrated into existing prompt structure

### Step 3: Analyze existing W5.5 limitation check
- Read `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py`
- Locate `_check_7_limitation_honesty()` function
- Understand current severity logic and page_role usage

### Step 4: Implement D-102 (W5.5 Check Refinement)
- Update `_check_7_limitation_honesty()`:
  - For page_role in ['overview', 'comprehensive_guide', 'api_overview']: severity = "error"
  - For page_role in ['index', 'toc', 'getting_started', 'installation', 'faq', 'troubleshooting', 'how_to']: return [] (skip check)
  - For other page roles: severity = "warn"
- Add comment explaining rationale for page-type specific logic

### Step 5: Add test coverage
- Create/update `tests/unit/workers/test_w5_llm_generation.py`:
  - Test LLM prompt WITH "Limitations" in required_headings → instruction present
  - Test LLM prompt WITHOUT "Limitations" in required_headings → instruction absent
  - Test limitation claims filtered correctly from claim_groups
- Create/update `tests/unit/workers/w5_5_content_reviewer/test_checks.py`:
  - Test check returns error for overview/comprehensive_guide/api_overview pages
  - Test check returns empty list for index/toc/getting_started/installation/faq/troubleshooting/how_to pages
  - Test check returns warning for other page types

### Step 6: Run tests and verify
- Run pytest on modified test files
- Run full test suite to ensure no regressions
- Verify test pass rate and coverage

### Step 7: Create evidence package
- Generate `plan.md` — implementation approach for D-101 and D-102
- Generate `changes.md` — file-by-file changes with code snippets
- Generate `evidence.md` — test results, sample LLM prompts, check behavior
- Generate `self_review.md` — 12D self-review (target ≥48/60)

### Step 8: Update taskcard status
- Update taskcard status from Draft → In-Progress → Done
- Update updated timestamp

## Failure modes

### FM-1: LLM prompt instruction not triggering
**Detection**: Test coverage shows instruction absent when Limitations in required_headings
**Resolution**: Debug conditional logic, ensure exact string match for "Limitations" heading
**Spec/Gate**: Spec 08 (W5 SectionWriter), test failure in test_w5_llm_generation.py

### FM-2: Limitation claims not filtered correctly
**Detection**: Test shows empty or incorrect limitation claims passed to LLM
**Resolution**: Verify claim_groups.limitations structure, ensure claim_id lookup logic correct
**Spec/Gate**: Spec 03 (FactsBuilder), product_facts.schema.json

### FM-3: W5.5 check still produces false positives
**Detection**: Pilot run shows >5 limitation check errors, many on index/toc pages
**Resolution**: Review page_role values in pilot output, adjust skip list if needed
**Spec/Gate**: Spec 35 (W5.5 ContentReviewer), Gate 15 (ContentReviewer)

### FM-4: Test coverage insufficient
**Detection**: pytest coverage report shows <80% coverage for modified functions
**Resolution**: Add edge case tests (empty claim_groups, unknown page_role, etc.)
**Spec/Gate**: Spec 30 (AI Agent Governance), taskcard contract requirement

### FM-5: Regression in existing W5/W5.5 behavior
**Detection**: Full test suite shows failures in unrelated tests
**Resolution**: Isolate change, ensure no side effects on existing prompt logic or checks
**Spec/Gate**: CI/CD gate (test pass requirement)

## Task-specific review checklist

1. LLM prompt includes Limitations instruction ONLY when "Limitations" in required_headings
2. LLM prompt does NOT include Limitations instruction when heading not required
3. Limitation claims correctly filtered from claim_groups.limitations
4. Limitation claims passed to LLM context in claims_context variable
5. W5.5 check returns error severity for overview/comprehensive_guide/api_overview pages
6. W5.5 check returns empty list for index/toc/getting_started/installation/faq/troubleshooting/how_to pages
7. W5.5 check returns warn severity for other page types not in explicit lists
8. Test coverage includes positive and negative cases for prompt logic
9. Test coverage includes all three page type categories for check refinement
10. Evidence package includes sample LLM prompts showing instruction presence/absence
11. Evidence package includes check behavior examples for each page type category
12. Full test suite passes with no regressions

## Deliverables
- Modified `src/launch/workers/w5_section_writer/worker.py` with LLM prompt update and claim filtering
- Modified `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py` with page-type specific check
- Test file `tests/unit/workers/test_w5_llm_generation.py` with prompt logic tests
- Test file `tests/unit/workers/w5_5_content_reviewer/test_checks.py` with check refinement tests
- Evidence package:
  - `reports/agents/agent_d/TC-CREV-D-TRACK2/plan.md`
  - `reports/agents/agent_d/TC-CREV-D-TRACK2/changes.md`
  - `reports/agents/agent_d/TC-CREV-D-TRACK2/evidence.md`
  - `reports/agents/agent_d/TC-CREV-D-TRACK2/self_review.md`

## Acceptance checks
- [ ] LLM prompt dynamically includes Limitations instruction when required_headings contains "Limitations"
- [ ] Limitation claims correctly filtered and passed to LLM context
- [ ] W5.5 check page-type specific (error/skip/warn based on page_role)
- [ ] Test coverage ≥4 new tests (2 for W5 prompt, 2+ for W5.5 check)
- [ ] All tests pass (pytest exit code 0)
- [ ] No regressions in existing test suite
- [ ] Evidence package complete with all 4 required files
- [ ] Self-review score ≥48/60 (≥4/5 on all 12 dimensions)
- [ ] Git commit with Co-Authored-By: Claude Sonnet 4.5

## Preconditions / dependencies
- W5 SectionWriter operational (TC-440)
- W5.5 ContentReviewer operational (TC-1100)
- Product facts with claim_groups structure (TC-410)
- Test infrastructure for W5 and W5.5 workers

## Test plan
1. Unit tests for W5 LLM prompt:
   - Test prompt WITH "Limitations" → instruction present
   - Test prompt WITHOUT "Limitations" → instruction absent
   - Test limitation claims filtering logic
2. Unit tests for W5.5 check refinement:
   - Test error severity for overview/comprehensive_guide/api_overview
   - Test skip (empty return) for index/toc/getting_started/installation/faq/troubleshooting/how_to
   - Test warn severity for other page types
3. Integration test:
   - Run W5 on sample page with Limitations required → verify LLM receives instruction
   - Run W5.5 on sample pages → verify check behavior matches expected severity
4. Regression test:
   - Run full pytest suite → ensure no failures

## E2E verification

**Verification command**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_440_section_writer.py tests/unit/workers/w5_5_content_reviewer/test_checks.py -xvs
```

**Expected artifacts**:
- All tests pass
- Test coverage report shows 100% on modified functions
- No regressions in existing test suite

**Integration verification**:
- Run W5 SectionWriter with page that has "Limitations" in required_headings
- Verify LLM prompt includes Limitations instruction
- Verify generated content includes Limitations section
- Run W5.5 ContentReviewer on drafts with missing Limitations
- Verify ERROR only for overview/comprehensive_guide/api_overview pages
- Verify SKIP for index/toc/getting_started/installation/faq/troubleshooting/how_to pages
- Verify WARN for other page types
- Run full pilot to confirm error reduction from ~18 to ~3-5

## Integration boundary proven

**Upstream integration**:
- Input: page_plan.json with required_headings, product_facts.json with claim_groups.limitations
- Contract: JSON schema per specs/schemas/page_plan.schema.json and specs/schemas/product_facts.schema.json

**Downstream integration**:
- Output: W5 draft_sections with enhanced LLM-generated content, W5.5 review results with page-type specific checks
- Contract: draft_section.schema.json with frontmatter and content, review_result.schema.json with dimension scores

**Verification**:
- Integration tests pass
- Contract compliance verified
- W5 SectionWriter generates content with LLM prompt enhancements
- W5.5 ContentReviewer consumes W5 drafts and applies page-type specific checks
- No changes to artifact schemas (page_plan.json, product_facts.json)
- No changes to W4 → W5 → W5.5 → W6 pipeline flow
- Backward compatible: optional parameters with None defaults
- Test suite validates integration: 93 tests pass (W5 + W5.5)

## Self-review
See: `reports/agents/agent_d/TC-CREV-D-TRACK2/self_review.md`

**Score**: 59/60 (98.3%)
- All dimensions ≥4/5
- Ship: YES

**Status**: Done

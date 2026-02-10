---
id: TC-1106
title: "Developer Guide Limitations Section Gap"
status: In-Progress
owner: "Agent B"
updated: "2026-02-10"
depends_on:
  - TC-1102
  - TC-1103
allowed_paths:
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_tc_430_ia_planner.py
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/**
evidence_required:
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/investigation.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/decision.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/changes.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/evidence.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/self_review.md
spec_ref: 60acd31b02cb92674179b7582af6810a1eb33ac1
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-1106 — Developer Guide Limitations Section Gap

## Objective
Fix missing Limitations section in developer-guide.md despite product having 52 limitations. Identify root cause in W4 IAPlanner or W5 SectionWriter logic and implement fix to ensure comprehensive_guide page role receives Limitations in required_headings.

## Required spec references
- specs/21_worker_contracts.md (W4 IA Planner contract, W5 SectionWriter contract)
- specs/06_page_planning.md (page types and heading structure)
- specs/07_ia_planner.md (page role assignments)
- specs/08_section_writer.md (content generation)
- specs/05_product_facts.md (claim_groups structure)
- specs/schemas/page_plan.schema.json

## Scope
### In scope
- Root cause analysis: Why developer-guide (comprehensive_guide) missing Limitations
- Investigate W4 IAPlanner logic for comprehensive_guide page role
- Investigate W5 SectionWriter handling of comprehensive_guide
- Fix W4 to add Limitations for comprehensive_guide when product has limitations
- Test coverage for comprehensive_guide with limitations
- Evidence package generation

### Out of scope
- Changes to other page types beyond comprehensive_guide
- Template modifications
- Changes to claim_groups structure or product_facts schema
- W5.5 ContentReviewer modifications
- Changes to other workers (W6, W7, W8)

## Inputs
- runs/track2_final_validation/artifacts/page_plan.json (developer-guide page_role)
- runs/track2_final_validation/drafts/docs/developer-guide.md (current content)
- src/launch/workers/w4_ia_planner/worker.py (TC-1102 fixes)
- src/launch/workers/w5_section_writer/worker.py (TC-1103 fixes)
- product_facts.json with 52 limitations

## Outputs
- Root cause documentation in investigation.md
- Decision documentation for fix location (W4 or W5)
- Updated W4 worker.py with comprehensive_guide support (if W4 issue)
- Test coverage for comprehensive_guide + limitations
- Evidence package in reports/agents/agent_b/TC-1106_developer_guide_limitations/

## Allowed paths
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_tc_430_ia_planner.py
- reports/agents/agent_b/TC-1106_developer_guide_limitations/**

## Preconditions / dependencies
- TC-1102 (W4 Limitations Heading Integration) must be complete
- TC-1103 (W5 LLM Prompt Update for Limitations) must be complete
- Track 2 pilot run artifacts must be available

## Implementation steps

1. **Create evidence directory structure**:
   - Create reports/agents/agent_b/TC-1106_developer_guide_limitations/
   - Prepare investigation.md for findings

2. **Investigate page_plan.json**:
   - Read runs/track2_final_validation/artifacts/page_plan.json
   - Find developer-guide entry
   - Document page_role value
   - Document required_headings list
   - Check if "Limitations" is present or absent

3. **Investigate TC-1102 fix in W4**:
   - Read src/launch/workers/w4_ia_planner/worker.py
   - Find _has_limitations() function
   - Find where Limitations heading is added to required_headings
   - Check which page_role values trigger Limitations addition
   - Document if comprehensive_guide is included or missing

4. **Investigate TC-1103 fix in W5**:
   - Read src/launch/workers/w5_section_writer/worker.py
   - Find LLM prompt generation logic
   - Check if comprehensive_guide has special handling
   - Document any comprehensive_guide-specific logic

5. **Read developer-guide.md draft**:
   - Read runs/track2_final_validation/drafts/docs/developer-guide.md
   - Verify Limitations section presence/absence
   - Document current content structure

6. **Root cause analysis**:
   - Synthesize findings from steps 2-5
   - Identify exact gap (W4 missing comprehensive_guide in condition)
   - Document in investigation.md

7. **Design fix**:
   - Write decision.md with fix approach
   - Specify exact code change location and logic
   - Identify test cases needed

8. **Implement fix**:
   - Update W4 worker.py to add comprehensive_guide to page_role condition
   - Expected location: Line ~45-50 in worker.py
   - Expected change: Add 'comprehensive_guide' to page_role check

9. **Add test coverage**:
   - Add test_comprehensive_guide_with_limitations to test file
   - Test product WITH limitations + comprehensive_guide → "Limitations" present
   - Test product WITHOUT limitations + comprehensive_guide → "Limitations" absent
   - Run pytest to verify

10. **Generate evidence package**:
    - investigation.md: Root cause findings with artifact paths
    - decision.md: Fix location and rationale
    - changes.md: File-by-file change documentation with code snippets
    - evidence.md: Test results and page_plan validation output
    - self_review.md: 12D self-review with ≥4/5 on all dimensions

## Test plan
- Unit test: comprehensive_guide with limitations → "Limitations" in required_headings
- Unit test: comprehensive_guide without limitations → "Limitations" not in required_headings
- Integration test: Run W4 on pilot product_facts → verify page_plan has Limitations for developer-guide
- Regression test: All existing W4 tests still pass
- Pilot verification: Re-run track2 pilot → developer-guide.md has Limitations section

## E2E verification
**Concrete command(s) to run:**
```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
set PYTHONHASHSEED=0
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v -k comprehensive_guide
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v
```

**Expected artifacts:**
- Test output showing new comprehensive_guide tests pass
- All existing W4 tests pass (55 tests total → 57 tests with new additions)
- page_plan.json from pilot runs shows "Limitations" in required_headings for developer-guide

**Success criteria:**
- [ ] New comprehensive_guide tests pass
- [ ] All W4 tests pass (0 failures)
- [ ] Developer-guide gets "Limitations" heading in page_plan
- [ ] Pilot run produces developer-guide.md with Limitations section
- [ ] 1 error eliminated from track2 error report

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-1102 (W4 IAPlanner) establishes pattern for adding Limitations to required_headings
- Upstream: TC-1103 (W5 SectionWriter) handles Limitations generation when heading present
- Downstream: W5 SectionWriter consumes required_headings and generates Limitations sections
- Contracts: specs/06_page_planning.md (page types), specs/21_worker_contracts.md (W4 contract)
- Gap: comprehensive_guide not included in TC-1102 page_role condition
- Fix: Extend TC-1102 logic to include comprehensive_guide

## Failure modes

### Failure mode 1: comprehensive_guide not actually missing from TC-1102
**Detection:** Investigation shows comprehensive_guide already in page_role condition; developer-guide still missing Limitations
**Resolution:** Expand investigation to check page_plan.json page_role assignment; verify developer-guide is assigned comprehensive_guide role; check for alternate root causes (e.g., _has_limitations() not detecting limitations)
**Spec/Gate:** specs/07_ia_planner.md (page role assignment), specs/05_product_facts.md (claim_groups structure)

### Failure mode 2: Fix causes duplicate Limitations headings
**Detection:** page_plan.json shows multiple "Limitations" entries in required_headings; W5 generates duplicate sections
**Resolution:** Ensure TC-1102 logic already has duplicate prevention check `if 'Limitations' not in required_headings`; add test for duplicate prevention
**Spec/Gate:** specs/schemas/page_plan.schema.json (unique headings requirement)

### Failure mode 3: Fix breaks other page types
**Detection:** Existing W4 tests fail after change; page types like overview or api_overview lose Limitations heading
**Resolution:** Review conditional logic carefully; ensure comprehensive_guide is added to condition, not replacing existing page_role values; run full test suite to catch regressions
**Spec/Gate:** CI/CD gate (test pass requirement), specs/06_page_planning.md (all page types)

### Failure mode 4: W5 doesn't generate Limitations for comprehensive_guide
**Detection:** developer-guide has "Limitations" in page_plan required_headings, but W5 doesn't generate the section
**Resolution:** Verify TC-1103 fix applies to comprehensive_guide; check W5 LLM prompt includes Limitations instruction; may require W5 fix in addition to W4 fix
**Spec/Gate:** specs/08_section_writer.md (W5 contract), TC-1103 scope

### Failure mode 5: Test coverage insufficient
**Detection:** pytest coverage report shows <80% coverage for modified functions; edge cases not tested
**Resolution:** Add comprehensive_guide test with no limitations; add comprehensive_guide test with empty claim_groups; add test for comprehensive_guide + multiple page types
**Spec/Gate:** Spec 30 (AI Agent Governance), taskcard contract requirement

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Root cause correctly identified with evidence from artifacts
- [ ] comprehensive_guide added to page_role condition in W4
- [ ] No duplicate Limitations headings in any page_plan
- [ ] comprehensive_guide receives Limitations only when product has limitations
- [ ] Test coverage includes comprehensive_guide with/without limitations
- [ ] All existing W4 tests still pass (no regressions)
- [ ] Evidence package includes before/after page_plan comparison
- [ ] investigation.md cites specific artifact paths and line numbers
- [ ] decision.md justifies W4 vs W5 fix location
- [ ] changes.md includes exact code snippets with context

## Deliverables
- Code:
  - Updated W4 worker.py with comprehensive_guide in page_role condition
- Tests:
  - Unit test for comprehensive_guide with limitations
  - Unit test for comprehensive_guide without limitations
  - Integration test with pilot product_facts
- Reports (required):
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/investigation.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/decision.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/changes.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/evidence.md
  - reports/agents/agent_b/TC-1106_developer_guide_limitations/self_review.md

## Acceptance checks
- [ ] Root cause identified and documented in investigation.md
- [ ] comprehensive_guide added to W4 page_role condition for Limitations
- [ ] Test coverage includes comprehensive_guide with/without limitations (2+ new tests)
- [ ] All W4 tests pass (pytest exit code 0)
- [ ] No regressions in existing test suite
- [ ] Evidence package complete with all 5 required files
- [ ] Self-review scores ≥4/5 on all 12 dimensions (≥48/60 total)
- [ ] Git commit with Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
- [ ] developer-guide.md has Limitations section in next pilot run
- [ ] 1 error eliminated from track2 error report

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

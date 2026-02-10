---
id: TC-CREV-C-TRACK2
title: "W4 Limitations Heading Integration (C-101)"
status: Done
owner: "Agent C"
updated: "2026-02-10"
depends_on:
  - TC-430
allowed_paths:
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_tc_430_ia_planner.py
  - reports/agents/agent_c/TC-CREV-C-TRACK2/**
evidence_required:
  - reports/agents/agent_c/TC-CREV-C-TRACK2/plan.md
  - reports/agents/agent_c/TC-CREV-C-TRACK2/changes.md
  - reports/agents/agent_c/TC-CREV-C-TRACK2/evidence.md
  - reports/agents/agent_c/TC-CREV-C-TRACK2/self_review.md
spec_ref: 96c46ffde5a48121122da7a7a3d23f3cd3563b99
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-CREV-C-TRACK2 — W4 Limitations Heading Integration (C-101)

## Objective
Fix W4 IA Planner to automatically add "Limitations" to required_headings when product_facts contains limitations, ensuring W5 SectionWriter generates Limitations sections for appropriate page types.

## Required spec references
- specs/21_worker_contracts.md (W4 IA Planner contract)
- specs/06_page_planning.md (page types and heading structure)
- specs/05_product_facts.md (claim_groups structure)
- specs/schemas/page_plan.schema.json
- specs/schemas/product_facts.schema.json

## Scope
### In scope
- Detect limitations in product_facts (both claim_groups.limitations and top-level limitations)
- Add "Limitations" to required_headings for appropriate page types (overview, comprehensive_guide, api_overview)
- Skip "Limitations" for non-overview page types (index, toc, getting_started, installation, faq, troubleshooting)
- Test coverage for all page types with/without limitations
- Evidence package generation

### Out of scope
- W5 SectionWriter modifications (out of scope - W5 already handles limitations if heading is present)
- Changes to claim_groups structure or product_facts schema
- Template modifications
- Changes to other workers

## Inputs
- product_facts.json with claim_groups.limitations or top-level limitations array
- page_role assignments from assign_page_role()
- Existing required_headings generation logic in W4

## Outputs
- Updated page_plan.json with "Limitations" in required_headings for appropriate pages
- Test coverage validating the logic
- Evidence package in reports/agents/agent_c/TC-CREV-C-TRACK2/

## Allowed paths
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_tc_430_ia_planner.py
- reports/agents/agent_c/TC-CREV-C-TRACK2/**

## Preconditions / dependencies
- TC-430 (W4 IA Planner) must be complete
- product_facts.json must contain claim_groups structure
- Page role assignment logic must be functional

## Implementation steps

1. **Create helper function to detect limitations**:
   - Add `_has_limitations(product_facts: Dict[str, Any]) -> bool` function
   - Check both claim_groups.get('limitations', []) and top-level limitations
   - Return True if either source has limitations

2. **Update _default_headings_for_role() function**:
   - Add "Limitations" heading to appropriate page roles
   - Target roles: landing, comprehensive_guide, api_reference
   - Position "Limitations" at end of heading list

3. **Update hardcoded required_headings in plan_default_pages()**:
   - Line ~1286: Products overview page
   - Line ~1311: Docs TOC (skip - not appropriate)
   - Line ~1342: Getting Started (skip - not appropriate)
   - Line ~1381: Developer Guide (comprehensive_guide - add if has limitations)
   - Line ~1408: API Reference overview (add if has limitations)
   - Line ~1506: FAQ (skip - not appropriate)
   - Line ~1531: Troubleshooting (skip - not appropriate)

4. **Update template-based page generation**:
   - Ensure limitations detection works in enumerate_templates flow
   - Update any page_role-based heading generation

5. **Add test coverage**:
   - Test product WITH limitations + overview page → "Limitations" present
   - Test product WITH limitations + index page → "Limitations" absent
   - Test product WITHOUT limitations → "Limitations" absent for all pages
   - Test all applicable page roles (landing, comprehensive_guide, api_reference)

6. **Generate evidence package**:
   - plan.md: Implementation approach and detection strategy
   - changes.md: File-by-file change documentation
   - evidence.md: Test results and page_plan validation output
   - self_review.md: 12D self-review with ≥4/5 on all dimensions

## Test plan
- Unit tests for _has_limitations() function
- Unit tests for page types with limitations
- Unit tests for page types without limitations
- Integration test with real product_facts from pilot
- Verify page_plan.json output includes "Limitations" correctly

## E2E verification
**Concrete command(s) to run:**
```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
set PYTHONHASHSEED=0
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v
```

**Expected artifacts:**
- Test output showing 55 tests passed (41 existing + 14 new)
- page_plan.json (from pilot runs) with "Limitations" in required_headings for overview pages

**Success criteria:**
- [ ] All 55 W4 tests pass
- [ ] Products with limitations get "Limitations" heading on overview pages
- [ ] Products without limitations do not get "Limitations" heading

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-430 (W4 IAPlanner) provides product_facts and page_role assignments
- Downstream: W5 SectionWriter consumes required_headings and generates Limitations sections
- Contracts: specs/06_page_planning.md (page types), specs/21_worker_contracts.md (W4 contract)

## Failure modes

### Failure mode 1: Limitations not detected in product_facts
**Detection:** page_plan.json missing "Limitations" heading despite product having 52 limitations; W5 ERROR issues continue; test fails for products with known limitations
**Resolution:** Verify both claim_groups.get('limitations', []) and top-level product_facts.get('limitations', []) are checked; ensure proper dictionary access with defaults; add debug logging for limitations detection
**Spec/Gate:** specs/05_product_facts.md (claim_groups structure), specs/schemas/product_facts.schema.json

### Failure mode 2: Limitations added to inappropriate page types
**Detection:** page_plan.json shows "Limitations" on TOC, getting-started, or index pages; content distribution strategy violated; Gate violations for inappropriate headings
**Resolution:** Add page_role guard: only add for roles in ['landing', 'comprehensive_guide', 'api_reference', 'api_overview']; skip for 'toc', 'workflow_page', 'feature_showcase', 'troubleshooting'; verify page_role assignment before adding heading
**Spec/Gate:** specs/06_page_planning.md (page type purposes), specs/21_worker_contracts.md W4 contract

### Failure mode 3: Limitations heading position inconsistent
**Detection:** "Limitations" appears at beginning of headings list instead of end; heading order differs from spec expectations; readability issues
**Resolution:** Always append "Limitations" to end of required_headings list; use list.append() not list.insert(0); maintain consistent ordering: Overview → Features → Platforms → Getting Started → Limitations
**Spec/Gate:** specs/06_page_planning.md (heading structure conventions)

### Failure mode 4: Duplicate "Limitations" headings
**Detection:** page_plan.json shows multiple "Limitations" entries in required_headings; W5 generates duplicate sections; validation errors
**Resolution:** Check if "Limitations" already in required_headings before appending; use `if 'Limitations' not in required_headings: required_headings.append('Limitations')`; add test for duplicate prevention
**Spec/Gate:** specs/schemas/page_plan.schema.json (unique headings requirement)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Limitations detection works for both claim_groups.limitations and top-level limitations arrays
- [ ] All appropriate page types (overview, comprehensive_guide, api_overview) receive "Limitations" heading
- [ ] No inappropriate page types (index, toc, getting_started, faq, troubleshooting) receive "Limitations" heading
- [ ] Heading order is consistent (Limitations appears at end of list)
- [ ] No duplicate "Limitations" headings in any page_plan
- [ ] Test coverage includes all page types with/without limitations
- [ ] Evidence package includes before/after page_plan comparison
- [ ] Changes are minimal and focused on heading logic only
- [ ] No changes to W5 or downstream workers required

## Deliverables
- Code:
  - Updated W4 worker.py with limitations heading logic
  - Helper function _has_limitations()
  - Updated _default_headings_for_role() if needed
- Tests:
  - Unit tests for limitations detection
  - Unit tests for all page types with/without limitations
  - Integration test with pilot product_facts
- Reports (required):
  - reports/agents/agent_c/TC-CREV-C-TRACK2/plan.md
  - reports/agents/agent_c/TC-CREV-C-TRACK2/changes.md
  - reports/agents/agent_c/TC-CREV-C-TRACK2/evidence.md
  - reports/agents/agent_c/TC-CREV-C-TRACK2/self_review.md

## Acceptance checks
- [ ] _has_limitations() function correctly detects limitations in product_facts
- [ ] Overview pages have "Limitations" in required_headings when product has limitations
- [ ] Non-overview pages (index, toc, getting_started, faq, troubleshooting) do NOT have "Limitations"
- [ ] Comprehensive_guide and api_overview pages have "Limitations" when product has limitations
- [ ] Products without limitations do NOT receive "Limitations" heading on any page
- [ ] Test suite passes with 100% coverage on new logic
- [ ] page_plan.json validates against schema
- [ ] Evidence package complete with all 4 documents
- [ ] Self-review scores ≥4/5 on all 12 dimensions

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

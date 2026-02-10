---
id: TC-1104
title: Fix Products/Index.md Missing Frontmatter Blocker (F-101)
status: Done
created: "2026-02-10"
updated: "2026-02-10"
owner: Agent-F
priority: P1
depends_on: []
tags: [w5, w5.5, contentreviewer, blocker, frontmatter, index-page]
spec_ref: 09c3d8b
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w5_section_writer/worker.py
  - tests/unit/workers/test_w5_specialized_generators.py
  - reports/agents/agent_f/TC-CREV-F-TRACK2/**
evidence_required:
  - reports/agents/agent_f/TC-CREV-F-TRACK2/investigation.md
  - reports/agents/agent_f/TC-CREV-F-TRACK2/decision.md
  - reports/agents/agent_f/TC-CREV-F-TRACK2/changes.md
  - reports/agents/agent_f/TC-CREV-F-TRACK2/evidence.md
  - reports/agents/agent_f/TC-CREV-F-TRACK2/self_review.md
---

# TC-1104 — Fix Products/Index.md Missing Frontmatter Blocker (F-101)

## Objective

Fix the W5 index page generator to ensure products/index.md is generated with complete YAML frontmatter, eliminating the 1 BLOCKER error causing 100% page rejection in W5.5 ContentReviewer quality gate.

## Required spec references

- `specs/09_w5_sectionwriter.md` — W5 specialized page generators including index pages
- `specs/31_frontmatter_contract.md` — Frontmatter field requirements and validation
- `specs/32_platform_aware_content_layout.md` — Content path structure (V1-only)
- `specs/schemas/page_plan.schema.json` — Page metadata structure
- `specs/schemas/draft_section.schema.json` — Draft section with frontmatter requirements

## Scope

### In scope

- Root cause analysis of why products/index.md generates without frontmatter
- Fix W5 index page generator to emit frontmatter for all index page types
- Test coverage for index page frontmatter generation (products, docs, kb, reference)
- Verification that fix resolves W5.5 ContentReviewer BLOCKER

### Out of scope

- Other ContentReviewer issues (handled by other agents)
- Index page content quality improvements (beyond frontmatter)
- Non-index page types (feature pages, comparison pages, etc.)
- W4 IAPlanner page_plan generation (assumed correct)

## Inputs

1. Latest pilot run artifacts:
   - `runs/r_20260210T083043Z_.../drafts/products/index.md` — Generated page with missing frontmatter
   - `runs/r_20260210T083043Z_.../artifacts/page_plan.json` — Page metadata from W4
   - `runs/r_20260210T083043Z_.../events.ndjson` — Execution telemetry

2. Source code:
   - `src/launch/workers/w5_section_writer/worker.py` — W5 specialized generators including index page logic
   - `tests/unit/workers/test_w5_specialized_generators.py` — Existing test suite

3. Specifications:
   - Frontmatter contract and field requirements
   - W5 specialized generator behavior specs

## Outputs

1. Fixed W5 index page generator:
   - `src/launch/workers/w5_section_writer/worker.py` — Updated with frontmatter generation

2. Test coverage:
   - `tests/unit/workers/test_w5_specialized_generators.py` — Tests for index page frontmatter

3. Evidence package in `reports/agents/agent_f/TC-CREV-F-TRACK2/`:
   - `investigation.md` — Root cause analysis with findings from all investigation steps
   - `decision.md` — Fix approach rationale
   - `changes.md` — File-by-file change documentation
   - `evidence.md` — Test results and pilot run validation
   - `self_review.md` — 12D self-review (≥4/5 on ALL dimensions)

## Allowed paths

- src/launch/workers/w5_section_writer/worker.py
- tests/unit/workers/test_w5_specialized_generators.py
- reports/agents/agent_f/TC-CREV-F-TRACK2/**

## Preconditions / dependencies

- W5.5 ContentReviewer implementation complete (TC-1100)
- Pilot run completed with ContentReviewer enabled showing BLOCKER error
- W4 IAPlanner generating correct page_plan metadata for index pages

## Implementation steps

1. **Investigation Phase**:
   - Read actual generated products/index.md from latest pilot run
   - Examine W5 worker.py to locate index page generation logic
   - Check W4 page_plan for products/index.md metadata structure
   - Compare products/index.md with other index pages (docs, kb, reference)
   - Identify conditional logic or code paths that skip frontmatter generation

2. **Root Cause Analysis**:
   - Document why frontmatter is not being generated for products/index.md
   - Determine if issue affects all index types or only products
   - Identify specific function or code block responsible for omission
   - Write findings to `reports/agents/agent_f/TC-CREV-F-TRACK2/investigation.md`

3. **Fix Design**:
   - Design minimal fix to ensure frontmatter generation for all index pages
   - Consider edge cases (missing metadata, optional fields, error handling)
   - Document fix approach and rationale in `reports/agents/agent_f/TC-CREV-F-TRACK2/decision.md`

4. **Implementation**:
   - Implement fix in `src/launch/workers/w5_section_writer/worker.py`
   - Ensure fix handles all index page types (products, docs, kb, reference)
   - Add defensive checks for missing metadata fields

5. **Test Coverage**:
   - Add test for products/index.md frontmatter generation
   - Add tests for other index types (docs, kb, reference) if not already covered
   - Verify frontmatter contains all required fields (title, description, url_path/permalink, etc.)
   - Run full test suite to ensure no regressions

6. **Verification**:
   - Run pilot with ContentReviewer enabled
   - Verify products/index.md now has frontmatter
   - Verify 0 frontmatter BLOCKER errors in ContentReviewer output
   - Document test results in `reports/agents/agent_f/TC-CREV-F-TRACK2/evidence.md`

7. **Evidence Package**:
   - Complete all evidence documents (investigation, decision, changes, evidence)
   - Perform 12D self-review and document in `self_review.md`
   - Ensure all dimensions score ≥4/5

8. **Git Commit**:
   - Commit changes with descriptive message
   - Include Co-Authored-By tag for Claude

## Failure modes

### FM-1: Frontmatter generation function missing

**Detection signal**: Index page content generated but no frontmatter block at all

**Resolution steps**:
1. Locate frontmatter generation helper function in W5 worker
2. Ensure index page generator calls frontmatter generation function
3. Pass correct metadata from page_plan to frontmatter generator

**Spec/Gate link**: specs/31_frontmatter_contract.md § Frontmatter Generation Requirements

### FM-2: Metadata mapping incorrect

**Detection signal**: Frontmatter present but missing required fields (title, description, url_path)

**Resolution steps**:
1. Check page_plan schema for index page metadata structure
2. Verify field name mapping between page_plan and frontmatter
3. Add defensive checks for missing optional fields

**Spec/Gate link**: specs/schemas/page_plan.schema.json, specs/31_frontmatter_contract.md

### FM-3: Conditional logic skipping index pages

**Detection signal**: Other page types have frontmatter, but index pages don't

**Resolution steps**:
1. Search for conditional branches that treat index pages differently
2. Remove or fix condition that skips frontmatter for index pages
3. Ensure all page types follow same frontmatter generation path

**Spec/Gate link**: specs/09_w5_sectionwriter.md § Index Page Generation

### FM-4: Template override missing frontmatter section

**Detection signal**: Template-based index pages render without frontmatter section

**Resolution steps**:
1. Check if index page uses template override
2. Verify template includes frontmatter section
3. If template missing, fix generator to inject frontmatter before content

**Spec/Gate link**: specs/09_w5_sectionwriter.md § Template-Driven Generation

### FM-5: Exception silently caught during generation

**Detection signal**: No error logged but frontmatter missing in output

**Resolution steps**:
1. Search for broad exception handlers in index generation path
2. Add logging for caught exceptions
3. Remove silent exception swallowing or re-raise after logging

**Spec/Gate link**: specs/09_w5_sectionwriter.md § Error Handling

## Task-specific review checklist

- [ ] products/index.md frontmatter includes all required fields (title, description, url_path or permalink)
- [ ] All index page types (products, docs, kb, reference) generate with frontmatter
- [ ] Test coverage added for index page frontmatter generation
- [ ] No regressions in existing W5 tests (2653 tests still pass)
- [ ] Pilot run with ContentReviewer shows 0 frontmatter BLOCKER errors
- [ ] Fix handles edge cases (missing metadata, optional fields)
- [ ] Code change minimal and focused on root cause
- [ ] Evidence package complete with all 5 required documents
- [ ] 12D self-review scores ≥4/5 on all dimensions (total ≥48/60)
- [ ] Git commit includes Co-Authored-By tag

## Test plan

### Unit Tests

1. **test_products_index_has_frontmatter**:
   - Generate products/index.md with mock page_plan
   - Assert frontmatter block present
   - Assert required fields present (title, description, url_path/permalink)

2. **test_docs_index_has_frontmatter**:
   - Generate docs/index.md with mock page_plan
   - Assert frontmatter block present

3. **test_kb_index_has_frontmatter**:
   - Generate kb/index.md with mock page_plan
   - Assert frontmatter block present

4. **test_reference_index_has_frontmatter**:
   - Generate reference/index.md with mock page_plan
   - Assert frontmatter block present

5. **test_index_frontmatter_missing_optional_fields**:
   - Generate index with minimal page_plan (missing optional fields)
   - Assert frontmatter still generated with available fields
   - Assert no exceptions raised

### Integration Test

1. **Run pilot with ContentReviewer enabled**:
   - Execute `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/test_f101`
   - Verify products/index.md has frontmatter
   - Verify ContentReviewer shows 0 BLOCKER errors

## E2E verification

**Verification command**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w5_specialized_generators.py -xvs
```

**Expected artifacts**:
- All tests pass
- Test coverage report shows 100% on modified functions
- No regressions in existing test suite

**Integration verification**:
- Run pilot with ContentReviewer enabled
- Verify products/index.md has frontmatter
- Verify ContentReviewer shows 0 BLOCKER errors

## Integration boundary proven

**Upstream integration**:
- Input: page_plan.json from W4 IAPlanner with index page metadata
- Contract: JSON schema per specs/schemas/page_plan.schema.json

**Downstream integration**:
- Output: draft_sections with complete frontmatter for index pages
- Contract: draft_section.schema.json with required frontmatter fields (title, description, url_path/permalink)

**Verification**:
- Integration tests pass
- Contract compliance verified
- W5 index page generator emits frontmatter for all index page types
- W5.5 ContentReviewer validates frontmatter and shows 0 BLOCKER errors
- No changes to page_plan schema or W4 → W5 → W5.5 pipeline flow

## Deliverables

1. Fixed W5 index page generator in `src/launch/workers/w5_section_writer/worker.py`
2. Test coverage in `tests/unit/workers/test_w5_specialized_generators.py`
3. Evidence package:
   - `reports/agents/agent_f/TC-CREV-F-TRACK2/investigation.md`
   - `reports/agents/agent_f/TC-CREV-F-TRACK2/decision.md`
   - `reports/agents/agent_f/TC-CREV-F-TRACK2/changes.md`
   - `reports/agents/agent_f/TC-CREV-F-TRACK2/evidence.md`
   - `reports/agents/agent_f/TC-CREV-F-TRACK2/self_review.md`
4. Git commit with Co-Authored-By tag

## Acceptance checks

- [ ] Taskcard created and registered in INDEX.md
- [ ] Root cause identified and documented in investigation.md
- [ ] Fix implemented in src/launch/workers/w5_section_writer/worker.py
- [ ] Test coverage added (≥4 tests for different index page types)
- [ ] All unit tests pass (pytest exit code 0)
- [ ] Pilot run shows products/index.md with frontmatter
- [ ] ContentReviewer shows 0 frontmatter BLOCKER errors
- [ ] Evidence package complete (5 documents)
- [ ] 12D self-review scores ≥48/60 (≥4/5 on all dimensions)
- [ ] Git commit created with Co-Authored-By tag
- [ ] No regressions (existing test suite still passes)

## Self-review

Status: Pending (will be completed after implementation)

Expected completion criteria:
- All 12 dimensions score ≥4/5
- Total score ≥48/60
- Evidence documents support all scores

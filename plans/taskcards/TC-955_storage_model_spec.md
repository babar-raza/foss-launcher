---
id: TC-955
title: "Storage Model Spec Verification"
status: Draft
priority: Critical
owner: "STORAGE_VERIFIER"
updated: "2026-02-03"
tags: ["storage-model", "verification", "traceability", "retention", "tc-939", "specs"]
depends_on: ["TC-939"]
allowed_paths:
  - plans/taskcards/TC-955_storage_model_spec.md
  - specs/40_storage_model.md
  - reports/agents/**/TC-955/**
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
evidence_required:
  - reports/agents/<agent>/TC-955/report.md
  - reports/agents/<agent>/TC-955/self_review.md
  - reports/agents/<agent>/TC-955/spec_audit.txt
  - reports/agents/<agent>/TC-955/traceability_test.txt
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-955: Storage Model Spec Verification

## Objective
Verify that specs/40_storage_model.md accurately documents the current storage implementation and answers key questions about data storage, retention, and traceability.

## Problem Statement
**NOTE:** TC-939 already created [specs/40_storage_model.md](specs/40_storage_model.md) with comprehensive storage documentation. TC-955 is a verification taskcard to ensure the spec accurately reflects the current system and answers key questions about data storage and retrievability.

Users need clear answers to:
1. Where are repo facts/snippets/evidence stored? (Files vs DB)
2. What retention policy is required for production runs?
3. How to trace from generated pages back to source files?
4. What data is needed to reproduce a run deterministically?

## Required spec references
- specs/40_storage_model.md (Storage model specification - TC-939 deliverable)
- specs/10_determinism_and_caching.md (Deterministic reproduction requirements)
- TC-939 (Storage Model Audit and Documentation)

## Scope

### In scope
- Review specs/40_storage_model.md for completeness and accuracy
- Verify all artifact locations documented (artifacts/*.json)
- Verify event log, snapshot, and database scope correctly described
- Verify retention policy (90/30/7 days) is documented
- Test traceability procedures with 1 page example
- Answer 5 key questions about storage (facts, snippets, evidence, DB, retention)
- Document findings in spec_audit.txt

### Out of scope
- Modifying storage implementation code
- Changing retention policies
- Adding new artifacts or storage mechanisms
- Implementing traceability tools (verification only)

## Inputs
- specs/40_storage_model.md (TC-939 deliverable)
- Pilot run directory structure (runs/<run_id>/)
- Artifact files (artifacts/*.json)
- Source code implementing storage (src/launch/io/, src/launch/state/)

## Outputs
- reports/agents/<agent>/TC-955/spec_audit.txt (completeness review)
- reports/agents/<agent>/TC-955/traceability_test.txt (manual trace of 1 page)
- reports/agents/<agent>/TC-955/report.md (verification findings)
- reports/agents/<agent>/TC-955/self_review.md
- Updated specs/40_storage_model.md (if gaps found)

## Allowed paths

- `plans/taskcards/TC-955_storage_model_spec.md`
- `specs/40_storage_model.md`
- `reports/agents/**/TC-955/**`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`## Implementation steps

### Step 1: Review specs/40_storage_model.md
Read entire spec to understand documented storage model

### Step 2: Verify artifact locations
Check that all artifacts/*.json files are documented with producer and purpose

### Step 3: Verify database scope
Confirm spec clearly states SQLite is telemetry-only, not operational

### Step 4: Verify retention policy
Check that 90/30/7 day tiers are documented with file lists

### Step 5: Test traceability
Pick getting-started.md from pilot content_preview and trace:
1. Find in page_plan.json
2. Extract claim_ids
3. Look up in evidence_map.json
4. Find source files in repo_inventory.json
5. Verify source files in work/repo/
Document each step in traceability_test.txt

### Step 6: Answer key questions
Document answers to all 5 questions in spec_audit.txt

### Step 7: Document findings
Create report.md summarizing verification results and any gaps found

## Task-specific review checklist
1. [ ] All 8 artifacts documented in registry table (repo_inventory, product_facts, evidence_map, snippet_catalog, page_plan, patch_bundle, validation_report, pr.json)
2. [ ] Event log (events.ndjson) and snapshot (snapshot.json) documented
3. [ ] SQLite database scope clearly states "telemetry ONLY, not operational"
4. [ ] Retention policy has 3 tiers: minimal (90d), debugging (30d), short-term (7d)
5. [ ] Forward traceability chain documented (source → page)
6. [ ] Backward traceability chain documented (page → source)
7. [ ] All 5 key questions answered with artifact paths and schemas
8. [ ] Traceability test completed for 1 page example
9. [ ] Retention requirements verified as feasible for pilots
10. [ ] Spec audit findings documented

## Failure modes

### Failure mode 1: Traceability chain broken (missing links)
**Detection:** Cannot trace from getting-started.md back to source file; claim_ids not found in evidence_map.json or source files missing from repo_inventory.json
**Resolution:** Verify all artifacts exist in pilot run directory; check that page_plan.json includes claim_ids; ensure evidence_map.json and repo_inventory.json were generated; review W1/W2/W4 outputs; document gaps in spec if missing from specs/40_storage_model.md
**Spec/Gate:** specs/40_storage_model.md (Traceability procedures), specs/10_determinism_and_caching.md

### Failure mode 2: Spec inaccuracies (documented paths don't match actual)
**Detection:** Spec says artifacts at artifacts/*.json but actual files in different location; schema paths incorrect; retention tiers don't match implementation
**Resolution:** Inspect actual pilot run directory structure; compare with spec documentation; update specs/40_storage_model.md with corrections; note implementation mismatches for future taskcards
**Spec/Gate:** TC-939 (Storage Model Audit), specs/40_storage_model.md

### Failure mode 3: Key questions unanswered or ambiguous
**Detection:** Spec doesn't clearly state where facts/snippets/evidence stored; database scope unclear; retention policy missing or vague
**Resolution:** Search spec for explicit answers to 5 key questions; check if information is scattered across multiple sections; consolidate answers in one section; update spec with clear Q&A format if needed
**Spec/Gate:** specs/40_storage_model.md (Completeness requirement)

## Deliverables
- reports/agents/<agent>/TC-955/spec_audit.txt
- reports/agents/<agent>/TC-955/traceability_test.txt
- reports/agents/<agent>/TC-955/report.md
- reports/agents/<agent>/TC-955/self_review.md
- Updated specs/40_storage_model.md (if corrections needed)

## Acceptance checks
1. Review [specs/40_storage_model.md](specs/40_storage_model.md) for completeness
2. Verify the spec accurately documents:
   - All artifact locations (artifacts/*.json)
   - Event log and snapshot model
   - SQLite database scope (telemetry ONLY, not operational)
   - Retention policy (minimal 90 days, debugging 30 days, short-term 7 days)
   - Traceability procedures (forward and backward)
   - Debugging procedures for common scenarios
3. Test traceability procedures by following the documented chains:
   - Forward: source file → repo_inventory → evidence_map → page_plan → draft → site
   - Backward: generated page → page_plan → evidence_map → repo_inventory → source file
4. Verify retention requirements are feasible for pilots
5. Document any gaps or inaccuracies found
6. All 5 key questions answered clearly
7. Traceability test successful (page → source chain intact)
8. Retention policy verified as feasible
9. Spec corrections applied if needed
10. Verification report complete

## E2E verification
Review spec and test traceability:
```bash
# Read spec
cat specs/40_storage_model.md | grep -A 5 "Artifacts Registry"

# Test traceability with pilot run
cd runs/<run_id>/
jq '.pages[0].output_path' artifacts/page_plan.json
jq '.pages[0].claim_ids' artifacts/page_plan.json
jq '.claims[0]' artifacts/evidence_map.json
jq '.files[0]' artifacts/repo_inventory.json
ls work/repo/<source_file>
```

Expected artifacts:
- specs/40_storage_model.md exists and documents all 8 artifacts
- Traceability chain complete (page → plan → evidence → inventory → source)
- All 5 key questions answered in spec
- Retention policy clearly documented
- spec_audit.txt documents verification findings

## Integration boundary proven
**Upstream:** TC-939 created specs/40_storage_model.md documenting storage design
**Downstream:** TC-955 verifies spec accuracy for pilot runs; spec used by developers and operators
**Contract:** Spec must accurately document all artifacts, retention tiers, and traceability procedures; spec must answer key storage questions clearly

## Self-review
- [ ] specs/40_storage_model.md reviewed for completeness
- [ ] All 8 artifacts verified in registry table
- [ ] Database scope confirmed as "telemetry only"
- [ ] Retention policy 3-tier structure verified
- [ ] Traceability test completed for 1 page example
- [ ] All 5 key questions answered
- [ ] Findings documented in spec_audit.txt and report.md
- [ ] All required sections present per taskcard contract
- [ ] Verification-only scope maintained (no implementation changes)

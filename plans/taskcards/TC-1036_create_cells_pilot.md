---
id: TC-1036
title: "Create cells Pilot (pilot-aspose-cells-foss-python)"
status: Done
priority: Normal
owner: agent-h
updated: "2026-02-07"
tags: ["pilot", "cells", "verification", "phase-5"]
depends_on: ["TC-1011", "TC-1012"]
allowed_paths:
  - "configs/pilots/pilot-aspose-cells-foss-python*"
  - "specs/pilots/pilot-aspose-cells-foss-python/**"
  - "plans/taskcards/TC-1036_*"
  - "reports/agents/agent_h/TC-1036/**"
evidence_required:
  - reports/agents/agent_h/TC-1036/evidence.md
  - reports/agents/agent_h/TC-1036/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1036 — Create cells Pilot (pilot-aspose-cells-foss-python)

## Objective
Create a new pilot `pilot-aspose-cells-foss-python` to verify template parity and family_overrides for the cells product family. This is the third pilot alongside existing `pilot-aspose-3d-foss-python` and `pilot-aspose-note-foss-python`.

## Problem Statement
The cells product family has family_overrides in ruleset.v1.yaml (added by TC-1011) specifying mandatory pages `spreadsheet-operations` and `formula-calculation`. A dedicated pilot is needed to verify that template enumeration, page planning, and content generation work correctly for cells, ensuring full product family parity across 3D, Note, and Cells.

## Required spec references
- specs/rulesets/ruleset.v1.yaml (cells family_overrides section)
- specs/schemas/page_plan.schema.json (page plan structure)
- specs/pilots/README.md (pilot folder layout requirements)
- plans/taskcards/00_TASKCARD_CONTRACT.md (taskcard format requirements)

## Scope

### In scope
- Create `configs/pilots/pilot-aspose-cells-foss-python.yaml` base config
- Create `configs/pilots/pilot-aspose-cells-foss-python.resolved.yaml` resolved config
- Create `specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml` pinned run config
- Create `specs/pilots/pilot-aspose-cells-foss-python/expected_page_plan.json` expected output
- Create `specs/pilots/pilot-aspose-cells-foss-python/notes.md` pilot notes
- Verify cells family_overrides in ruleset
- Run tests to verify no regressions

### Out of scope
- Running the actual pilot pipeline (that is TC-1037)
- Modifying existing pilot configs
- Changing the ruleset or template packs
- Creating expected_validation_report.json (deferred to golden run)

## Inputs
- Existing pilot configs (note and 3d) as pattern reference
- specs/rulesets/ruleset.v1.yaml with cells family_overrides
- specs/templates/docs.aspose.org/cells/ template pack
- page_plan.schema.json schema definition

## Outputs
- Complete cells pilot config set (4 files + notes.md)
- expected_page_plan.json with cells-specific mandatory pages
- All cross_links as absolute URLs
- Evidence bundle and self-review

## Allowed paths
- configs/pilots/pilot-aspose-cells-foss-python*
- specs/pilots/pilot-aspose-cells-foss-python/**
- plans/taskcards/TC-1036_*
- reports/agents/agent_h/TC-1036/**

### Allowed paths rationale
TC-1036 creates new pilot configuration files and evidence artifacts only. No existing files are modified.

## Implementation steps

### Step 1: Study existing pilots
Read note and 3d pilot configs to understand the exact pattern for config files, resolved configs, pinned run configs, and expected page plans.

### Step 2: Verify cells family_overrides
Confirm that ruleset.v1.yaml contains cells family_overrides with `spreadsheet-operations` and `formula-calculation` mandatory pages.

### Step 3: Create pilot config files
Create all 4 config files following the exact pattern of the note pilot, substituting cells-specific values.

### Step 4: Create expected_page_plan.json
Build expected page plan with cells-specific mandatory pages, absolute cross_links, and proper output paths.

### Step 5: Run tests
Verify no regressions with `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`.

### Step 6: Write evidence and self-review
Document all artifacts created and verification results.

## Failure modes

### Failure mode 1: Page plan schema validation fails
**Detection:** pytest or W7 Gate 1 reports schema validation errors for expected_page_plan.json
**Resolution:** Compare against page_plan.schema.json; fix missing required fields or incorrect enum values
**Spec/Gate:** specs/schemas/page_plan.schema.json, Gate 1

### Failure mode 2: Cross-links not absolute
**Detection:** Gate 5 or manual inspection finds relative cross_links instead of absolute URLs
**Resolution:** Ensure all cross_links use `https://<subdomain>/<family>/<platform>/<slug>/` format
**Spec/Gate:** TC-1012 absolute cross_links requirement

### Failure mode 3: Cells mandatory pages missing from expected plan
**Detection:** Gate 14 or manual inspection finds missing spreadsheet-operations or formula-calculation pages
**Resolution:** Add mandatory pages from ruleset.v1.yaml cells family_overrides to expected_page_plan.json
**Spec/Gate:** specs/rulesets/ruleset.v1.yaml cells section

## Task-specific review checklist
1. [ ] Base config uses correct `family: "cells"` and `product_slug: "pilot-aspose-cells-foss-python"`
2. [ ] Resolved config has all defaults filled in matching note pilot pattern
3. [ ] Pinned config uses FOSS repo URL pattern `aspose-cells-foss/Aspose.Cells-FOSS-for-Python`
4. [ ] Expected page plan includes cells-specific mandatory pages (spreadsheet-operations, formula-calculation)
5. [ ] All cross_links are absolute URLs with correct subdomain mapping
6. [ ] allowed_paths use `cells` family with V2 platform-aware paths
7. [ ] All tests pass with no regressions
8. [ ] Notes.md documents the pilot setup

## Deliverables
- configs/pilots/pilot-aspose-cells-foss-python.yaml
- configs/pilots/pilot-aspose-cells-foss-python.resolved.yaml
- specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml
- specs/pilots/pilot-aspose-cells-foss-python/expected_page_plan.json
- specs/pilots/pilot-aspose-cells-foss-python/notes.md
- reports/agents/agent_h/TC-1036/evidence.md
- reports/agents/agent_h/TC-1036/self_review.md

## Acceptance checks
1. [ ] All 5 pilot files created and syntactically valid
2. [ ] expected_page_plan.json validates against page_plan.schema.json
3. [ ] Cells mandatory pages present in page plan
4. [ ] All cross_links are absolute URLs
5. [ ] All existing tests pass (no regressions)
6. [ ] Evidence and self-review written

## Preconditions / dependencies
- TC-1011 (cells family_overrides in ruleset) must be COMPLETE
- TC-1012 (cross_links absolute) must be COMPLETE
- Python virtual environment available
- Cells template packs exist in specs/templates/

## Test plan
1. Verify all config files are valid YAML
2. Verify expected_page_plan.json is valid JSON and matches schema
3. Run full test suite to confirm no regressions
4. Manual inspection of cross_links for absolute URL format

## Self-review
(To be completed after implementation)

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

## Integration boundary proven
**Upstream:** TC-1011 provides cells family_overrides in ruleset.v1.yaml. TC-1012 ensures cross_links are absolute.
**Downstream:** TC-1037 will use this pilot for E2E verification of the full pipeline.
**Contract:** Pilot config files follow the established pattern; expected_page_plan.json validates against page_plan.schema.json.

## Evidence Location
`reports/agents/agent_h/TC-1036/`

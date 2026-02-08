---
id: TC-1011
title: "Add cells/note family_overrides to ruleset.v1.yaml"
status: Complete
priority: Normal
owner: Agent-B
updated: "2026-02-07"
tags: ["ruleset", "family_overrides"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1011*.md
  - specs/rulesets/ruleset.v1.yaml
  - tests/unit/workers/test_tc_430_ia_planner.py
  - reports/agents/agent_b/TC-1011/**
evidence_required: true
spec_ref: "46d7ac2be0e1e3f1096f5d45ac1493d621436a99"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1011 --- Add cells/note family_overrides to ruleset.v1.yaml

## Objective
Add product-family-specific mandatory page overrides for "cells" and "note" families in `specs/rulesets/ruleset.v1.yaml`, matching the existing "3d" family override pattern introduced by TC-983.

## Problem Statement
The `family_overrides` section in `ruleset.v1.yaml` only defines overrides for the "3d" family. The "cells" and "note" families lack product-specific mandatory pages, which means the W4 IAPlanner cannot generate family-appropriate page plans for these products.

## Required spec references
- specs/rulesets/ruleset.v1.yaml (family_overrides section, lines 117-128)
- specs/06_page_planning.md (mandatory page definitions)
- plans/taskcards/00_TASKCARD_CONTRACT.md (taskcard format requirements)

## Scope

### In scope
- Add "cells" family_overrides with mandatory pages: spreadsheet-operations, formula-calculation
- Add "note" family_overrides with mandatory pages: notebook-manipulation, document-conversion
- Verify existing tests still pass after the change

### Out of scope
- Modifying W4 IAPlanner logic (it already supports family_overrides)
- Updating expected_page_plan.json for pilots (separate concern)
- Adding optional_page_policies overrides

## Inputs
- Existing `specs/rulesets/ruleset.v1.yaml` with "3d" family_overrides only
- TC-983 merge strategy: family mandatory_pages are UNIONED with global mandatory_pages

## Outputs
- Updated `specs/rulesets/ruleset.v1.yaml` with "cells" and "note" family_overrides
- Evidence report at `reports/agents/agent_b/TC-1011/evidence.md`

## Allowed paths
- plans/taskcards/TC-1011*.md
- specs/rulesets/ruleset.v1.yaml
- tests/unit/workers/test_tc_430_ia_planner.py
- reports/agents/agent_b/TC-1011/**

### Allowed paths rationale
TC-1011 modifies the ruleset to add family-specific overrides for cells and note products. The test file is included in case assertions need updating.

## Implementation steps

### Step 1: Get current git SHA
```bash
git rev-parse HEAD
```
Result: `46d7ac2be0e1e3f1096f5d45ac1493d621436a99`

### Step 2: Edit ruleset.v1.yaml
After the "3d" family_overrides block (line 128), add cells and note overrides:
```yaml
  "cells":
    sections:
      docs:
        mandatory_pages:
          - slug: "spreadsheet-operations"
            page_role: "workflow_page"
          - slug: "formula-calculation"
            page_role: "workflow_page"
  "note":
    sections:
      docs:
        mandatory_pages:
          - slug: "notebook-manipulation"
            page_role: "workflow_page"
          - slug: "document-conversion"
            page_role: "workflow_page"
```

### Step 3: Run tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -x -v
```

### Step 4: Write evidence
Capture test results and file diff in evidence report.

## Failure modes

### Failure mode 1: YAML syntax error breaks ruleset loading
**Detection:** pytest fails with YAML parse error when loading ruleset
**Resolution:** Check indentation (2-space YAML); validate with `python -c "import yaml; yaml.safe_load(open('specs/rulesets/ruleset.v1.yaml'))"`
**Spec/Gate:** Gate B taskcard validation

### Failure mode 2: W4 IAPlanner fails to merge family overrides
**Detection:** W4 plan_pages_for_section raises KeyError or produces wrong page count
**Resolution:** Verify merge strategy matches TC-983 UNION logic; check slug uniqueness
**Spec/Gate:** specs/06_page_planning.md mandatory page definitions

### Failure mode 3: Duplicate slug collision with global mandatory_pages
**Detection:** Plan contains duplicate pages for same slug
**Resolution:** Ensure family override slugs are unique relative to global mandatory_pages (no "installation" or "getting-started" duplicates)
**Spec/Gate:** TC-983 merge strategy comment in ruleset.v1.yaml

## Task-specific review checklist
1. [ ] YAML indentation is consistent (2 spaces)
2. [ ] Both cells and note entries follow exact same structure as 3d
3. [ ] Slug names are hyphenated lowercase
4. [ ] page_role values are valid ("workflow_page")
5. [ ] No duplicate slugs with global mandatory_pages
6. [ ] Frontmatter allowed_paths matches body Allowed paths section
7. [ ] spec_ref SHA matches current HEAD
8. [ ] Tests pass after edit

## Deliverables
- Modified `specs/rulesets/ruleset.v1.yaml` with cells and note family_overrides
- Evidence report at `reports/agents/agent_b/TC-1011/evidence.md`

## Acceptance checks
1. [ ] ruleset.v1.yaml parses without error
2. [ ] "cells" family_overrides has 2 mandatory_pages (spreadsheet-operations, formula-calculation)
3. [ ] "note" family_overrides has 2 mandatory_pages (notebook-manipulation, document-conversion)
4. [ ] All existing tests pass
5. [ ] Evidence report written

## Preconditions / dependencies
- Python virtual environment activated (.venv)
- TC-983 merge strategy already implemented in W4

## Test plan
1. Run `test_tc_430_ia_planner.py` to verify no regressions
2. Verify YAML loads correctly with python yaml module

## Self-review

### 12D Checklist
1. **Determinism:** YAML is static config; no runtime nondeterminism
2. **Dependencies:** No new dependencies; only config change
3. **Documentation:** TC-1011 taskcard documents the change
4. **Data preservation:** Existing 3d overrides unchanged; additive only
5. **Deliberate design:** Slugs chosen to reflect product-specific workflows
6. **Detection:** YAML parse errors caught by existing test infrastructure
7. **Diagnostics:** N/A (static config)
8. **Defensive coding:** N/A (static config)
9. **Direct testing:** pytest test_tc_430_ia_planner.py
10. **Deployment safety:** Additive change; fully backward compatible
11. **Delta tracking:** Only ruleset.v1.yaml modified
12. **Downstream impact:** W4 will pick up new overrides for cells/note pilots

### Verification results
- [ ] Tests: PENDING
- [ ] YAML parse: PENDING
- [ ] Evidence captured: reports/agents/agent_b/TC-1011/evidence.md

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -x -v
```

## Integration boundary proven
**Upstream:** ruleset.v1.yaml is loaded by W4 IAPlanner during plan_pages_for_section()
**Downstream:** W4 merges family_overrides mandatory_pages with global mandatory_pages using UNION strategy
**Contract:** family mandatory_pages are UNIONED with global mandatory_pages (not replaced). If a slug already exists in the global list, the family entry is skipped.

## Evidence Location
`reports/agents/agent_b/TC-1011/evidence.md`

# TC-1011 Evidence: Add cells/note family_overrides to ruleset.v1.yaml

## Date
2026-02-07

## Agent
Agent-B

## Summary
Added product-family-specific mandatory page overrides for "cells" and "note" families in `specs/rulesets/ruleset.v1.yaml`.

## Files Changed
- `specs/rulesets/ruleset.v1.yaml` -- Added cells and note family_overrides blocks (lines 129-144)
- `plans/taskcards/TC-1011_add_cells_note_family_overrides.md` -- Created taskcard

## Changes Detail

### ruleset.v1.yaml (lines 129-144 added)
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

## Commands Run

### YAML validation
```
.venv/Scripts/python.exe -c "import yaml; data = yaml.safe_load(open('specs/rulesets/ruleset.v1.yaml')); print('YAML valid'); fo = data.get('family_overrides', {}); print(f'Families: {list(fo.keys())}')"
```
Output:
```
YAML valid
Families: ['3d', 'cells', 'note']
```

### Test run
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -x -v
```
Result: 33 passed, 0 failed

## Deterministic Verification
- YAML is static configuration; no runtime nondeterminism
- Slugs are lowercase hyphenated strings (consistent with existing patterns)
- page_role values match existing "workflow_page" usage
- Family override structure matches existing "3d" pattern exactly

## Test Results
- tests/unit/workers/test_tc_430_ia_planner.py: 33/33 PASSED
- Full test suite: 1916 passed, 12 skipped, 0 failures
